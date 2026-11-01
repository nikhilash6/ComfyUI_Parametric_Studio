"""ParametricStudio - Point Cloud to Mesh Pipeline.

Two nodes:
  * PSN_Depth_To_PointCloud : back-project an IMAGE + DEPTH_MAP through camera
    intrinsics into a 3D point cloud (with per-point RGB colors).
  * PSN_PointCloud_To_Mesh  : build a triangle mesh from the point cloud with
    one of three methods (convex_hull / ball_pivoting / delaunay). convex_hull
    and delaunay are plain geometry, not surface reconstruction.

Heavy libraries (trimesh, open3d) are imported lazily inside the mesh node so
that the depth->point cloud node keeps working in minimal environments.
"""

import math

import torch

CAT = "ParametricStudio/PointCloud"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _as_float_tensor(x):
    """Coerce a tensor-like input to a float32 CPU tensor (no in-place ops)."""
    if isinstance(x, torch.Tensor):
        t = x.detach().clone()
    else:
        t = torch.as_tensor(x)
    if t.is_floating_point():
        return t.float()
    return t.float()


def _validate_image(image):
    """Validate a ComfyUI IMAGE tensor [B,H,W,C] in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("IMAGE must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError(f"IMAGE must be 4D [B,H,W,C], got {image.dim()}D")
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError(f"IMAGE last dim must be 1/3/4 channels, got {image.shape[-1]}")
    if image.shape[0] != 1:
        raise ValueError("Only batch size 1 is supported for depth back-projection")
    return image.float()


def _validate_depth(depth):
    """Validate a ComfyUI MASK tensor [B,H,W] in 0..1."""
    if not isinstance(depth, torch.Tensor):
        raise TypeError("DEPTH_MAP must be a torch.Tensor")
    if depth.dim() != 3:
        raise ValueError(f"DEPTH_MAP must be 3D [B,H,W], got {depth.dim()}D")
    if depth.shape[0] != 1:
        raise ValueError("Only batch size 1 is supported for depth back-projection")
    return depth.float()


def _validate_intrinsics(intr):
    """Validate a 3x3 camera intrinsic matrix (torch tensor or nested list)."""
    t = _as_float_tensor(intr)
    if t.dim() != 2 or t.shape != (3, 3):
        raise ValueError(f"CAMERA_INTRINSICS must be a 3x3 matrix, got shape {tuple(t.shape)}")
    if not torch.isfinite(t).all():
        raise ValueError("CAMERA_INTRINSICS contains non-finite values")
    if t[0, 0] <= 0 or t[1, 1] <= 0:
        raise ValueError("CAMERA_INTRINSICS focal lengths (fx, fy) must be positive")
    return t


def _validate_point_cloud(points):
    """Validate a [N,3] point cloud tensor."""
    t = _as_float_tensor(points)
    if t.dim() != 2 or t.shape[1] != 3:
        raise ValueError(f"POINT_CLOUD must be [N,3], got shape {tuple(t.shape)}")
    if t.shape[0] < 3:
        raise ValueError("POINT_CLOUD needs at least 3 points")
    if not torch.isfinite(t).all():
        raise ValueError("POINT_CLOUD contains non-finite values")
    return t


def _validate_colors(colors, n):
    """Validate a [N,3] color tensor matching the point count."""
    t = _as_float_tensor(colors)
    if t.dim() != 2 or t.shape[1] != 3:
        raise ValueError(f"COLORS must be [N,3], got shape {tuple(t.shape)}")
    if t.shape[0] != n:
        raise ValueError(f"COLORS row count {t.shape[0]} != POINT_CLOUD row count {n}")
    return t


# ---------------------------------------------------------------------------
# Node 1: depth -> point cloud
# ---------------------------------------------------------------------------

class PSN_Depth_To_PointCloud:
    """Back-project an IMAGE + DEPTH_MAP through camera intrinsics into a 3D
    point cloud.  Pixels with depth <= 0 are skipped.

    Outputs:
      POINT_CLOUD : float tensor [N, 3]  (x, y, z in camera space)
      COLORS      : float tensor [N, 3]  (r, g, b in 0..1)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "IMAGE": ("IMAGE",),
                "DEPTH_MAP": ("MASK",),
                "CAMERA_INTRINSICS": ("TENSOR",),
            }
        }

    RETURN_TYPES = ("TENSOR", "TENSOR")
    RETURN_NAMES = ("POINT_CLOUD", "COLORS")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, IMAGE, DEPTH_MAP, CAMERA_INTRINSICS):
        image = _validate_image(IMAGE)
        depth = _validate_depth(DEPTH_MAP)
        K = _validate_intrinsics(CAMERA_INTRINSICS)

        if image.shape[1:3] != depth.shape[1:3]:
            raise ValueError(
                f"IMAGE spatial size {tuple(image.shape[1:3])} != "
                f"DEPTH_MAP spatial size {tuple(depth.shape[1:3])}"
            )

        h, w = depth.shape[1], depth.shape[2]
        fx, fy = K[0, 0].item(), K[1, 1].item()
        cx, cy = K[0, 2].item(), K[1, 2].item()

        # pixel grid (column-major: x = col, y = row)
        cols = torch.arange(w, dtype=torch.float32)
        rows = torch.arange(h, dtype=torch.float32)
        gx, gy = torch.meshgrid(cols, rows, indexing="xy")

        valid = depth[0] > 0.0
        if not valid.any():
            empty = torch.zeros((0, 3), dtype=torch.float32)
            return (empty, empty)

        xs = gx[valid]
        ys = gy[valid]
        zs = depth[0][valid]

        # back-projection: X = (u - cx) * z / fx, Y = (v - cy) * z / fy
        px = (xs - cx) * zs / fx
        py = (ys - cy) * zs / fy
        points = torch.stack((px, py, zs), dim=1)

        # colors: take RGB (first 3 channels) of the image at valid pixels
        rgb = image[0, :, :, :3]
        colors = rgb[valid].float()

        return (points.contiguous(), colors.contiguous())


# ---------------------------------------------------------------------------
# Node 2: point cloud -> mesh
# ---------------------------------------------------------------------------

def _mesh_convex_hull(points, colors):
    """Convex hull of the points via trimesh (a closed hull, not a surface fit)."""
    import trimesh

    mesh = trimesh.convex.convex_hull(points)
    if colors is not None and len(colors) == len(points):
        mesh.vertex_colors = colors
    return mesh


def _mesh_ball_pivoting(points, colors):
    """Ball Pivoting Method via open3d (CPU)."""
    import open3d as o3d

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    if colors is not None and len(colors) == len(points):
        pcd.colors = o3d.utility.Vector3dVector(colors)
    pcd.estimate_normals()  # ball pivoting needs normals

    # estimate a reasonable radius from the point cloud scale
    extent = float((pcd.get_max_bound() - pcd.get_min_bound()).max())
    n = max(len(points), 1)
    radius = max(extent / max(math.sqrt(n), 1.0) * 1.5, 1e-6)

    mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
        pcd, o3d.utility.DoubleVector([radius, radius * 0.5])
    )
    return mesh


def _mesh_delaunay(points, colors):
    """Raw 3D Delaunay tetrahedralisation (scipy), returned as its unique
    triangles (interior faces included). Errors from degenerate input
    (e.g. coplanar points) are raised, not hidden."""
    import numpy as np
    import trimesh
    from scipy.spatial import Delaunay

    s = Delaunay(points).simplices
    tris = np.concatenate([s[:, [0, 1, 2]], s[:, [0, 1, 3]], s[:, [0, 2, 3]], s[:, [1, 2, 3]]])
    faces = np.unique(np.sort(tris, axis=1), axis=0)
    mesh = trimesh.Trimesh(vertices=points, faces=faces, process=False)
    if colors is not None and len(colors) == len(points):
        mesh.vertex_colors = colors
    return mesh


_METHODS = {
    "convex_hull": _mesh_convex_hull,
    "ball_pivoting": _mesh_ball_pivoting,
    "delaunay": _mesh_delaunay,
}


class PSN_PointCloud_To_Mesh:
    """Build a triangle mesh from a 3D point cloud.

    Methods:
      convex_hull   - trimesh convex hull (closed, ignores concavities)
      ball_pivoting - open3d ball pivoting (normals are estimated first)
      delaunay      - unique triangles of the scipy 3D Delaunay tetrahedralisation

    Output: MESH (a trimesh.Trimesh object, or an open3d TriangleMesh for
    ball_pivoting; downstream nodes should handle both).
    """

    DESCRIPTION = (
        "Builds a triangle mesh from a point cloud by convex hull, open3d "
        "ball pivoting, or the raw 3D Delaunay triangulation. It does not do "
        "Poisson or alpha-shape surface reconstruction."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "POINT_CLOUD": ("TENSOR",),
                "COLORS": ("TENSOR",),
                "METHOD": (["convex_hull", "ball_pivoting", "delaunay"],),
            }
        }

    RETURN_TYPES = ("TRIMESH",)
    RETURN_NAMES = ("MESH",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, POINT_CLOUD, COLORS, METHOD):
        points = _validate_point_cloud(POINT_CLOUD)
        colors = _validate_colors(COLORS, points.shape[0])

        if METHOD not in _METHODS:
            raise ValueError(f"Unknown METHOD '{METHOD}', expected one of {list(_METHODS)}")

        pts_np = points.numpy()
        col_np = colors.numpy()

        mesh = _METHODS[METHOD](pts_np, col_np)
        return (mesh,)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Depth_To_PointCloud": PSN_Depth_To_PointCloud,
    "PSN_PointCloud_To_Mesh": PSN_PointCloud_To_Mesh,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Depth_To_PointCloud": "PSN Depth To Point Cloud",
    "PSN_PointCloud_To_Mesh": "PSN Point Cloud To Mesh",
}
