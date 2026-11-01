"""Orthographic preview render of a built-in unit cube. Reads no mesh files."""
import math

import torch

CAT = "ParametricStudio/FBX"

RENDER_MODES = ("clay", "shaded")


def _clamp01(x):
    return torch.clamp(x, 0.0, 1.0)


def _default_mesh():
    """Return the built-in unit cube mesh (vertices, faces)."""
    # 8 vertices of a unit cube centered at origin
    verts = [
        (-0.5, -0.5, -0.5),
        (0.5, -0.5, -0.5),
        (0.5, 0.5, -0.5),
        (-0.5, 0.5, -0.5),
        (-0.5, -0.5, 0.5),
        (0.5, -0.5, 0.5),
        (0.5, 0.5, 0.5),
        (-0.5, 0.5, 0.5),
    ]
    faces = [
        (0, 1, 2, 3),  # back
        (4, 5, 6, 7),  # front
        (0, 1, 5, 4),  # bottom
        (2, 3, 7, 6),  # top
        (0, 3, 7, 4),  # left
        (1, 2, 6, 5),  # right
    ]
    return verts, faces


def _render_mesh(verts, faces, render_mode, camera_angle, width=256, height=256):
    """
    Render a simple orthographic projection of the mesh onto a 2D image.
    Uses torch for the image tensor. Returns a float tensor [1, H, W, 3] in 0..1.
    """
    device = torch.device("cpu")
    img = torch.zeros((1, height, width, 3), dtype=torch.float32, device=device)

    # Background
    if render_mode == "clay":
        bg = torch.tensor([0.15, 0.15, 0.15], dtype=torch.float32, device=device)
    else:  # shaded
        bg = torch.tensor([0.05, 0.05, 0.10], dtype=torch.float32, device=device)
    img[:, :, :] = bg

    # Camera: rotate around Y axis by camera_angle (radians)
    angle = float(camera_angle)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    # Project vertices: simple orthographic, x->right, y->up, z->depth
    # After rotation: x' = x*cos + z*sin, y' = y, z' = -x*sin + z*cos
    projected = []
    for (x, y, z) in verts:
        x2 = x * cos_a + z * sin_a
        y2 = y
        z2 = -x * sin_a + z * cos_a
        projected.append((x2, y2, z2))

    # Normalize projected coords to image space
    xs = [p[0] for p in projected]
    ys = [p[1] for p in projected]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x if max_x > min_x else 1.0
    span_y = max_y - min_y if max_y > min_y else 1.0
    span = max(span_x, span_y)
    if span < 1e-6:
        span = 1.0

    margin = 0.15
    scale = (1.0 - 2.0 * margin) / span
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0

    def to_px(x2, y2):
        px = int(round((x2 - cx) * scale * (width / 2.0) + width / 2.0))
        py = int(round(-(y2 - cy) * scale * (height / 2.0) + height / 2.0))
        return max(0, min(width - 1, px)), max(0, min(height - 1, py))

    # Draw faces as filled polygons using a simple scanline approach
    face_colors = []
    if render_mode == "clay":
        base = torch.tensor([0.85, 0.85, 0.85], dtype=torch.float32, device=device)
    else:
        base = torch.tensor([0.4, 0.6, 0.9], dtype=torch.float32, device=device)

    for fi, face in enumerate(faces):
        # Compute face normal for shading (shaded mode)
        if len(face) >= 3:
            v0 = projected[face[0]]
            v1 = projected[face[1]]
            v2 = projected[face[2]]
            # Cross product for normal
            ax = v1[0] - v0[0]; ay = v1[1] - v0[1]; az = v1[2] - v0[2]
            bx = v2[0] - v0[0]; by = v2[1] - v0[1]; bz = v2[2] - v0[2]
            nx = ay * bz - az * by
            ny = az * bx - ax * bz
            nz = ax * by - ay * bx
            norm = math.sqrt(nx * nx + ny * ny + nz * nz)
            if norm > 1e-8:
                nz /= norm
            else:
                nz = 1.0
            # Simple lighting: brightness based on z-component of normal
            brightness = 0.5 + 0.5 * max(0.0, nz)
        else:
            brightness = 1.0

        color = base * brightness
        face_colors.append(color)

        # Rasterize polygon (simple: fill bounding box, test point-in-polygon)
        pts = [to_px(projected[vi][0], projected[vi][1]) for vi in face]
        min_px = min(p[0] for p in pts)
        max_px = max(p[0] for p in pts)
        min_py = min(p[1] for p in pts)
        max_py = max(p[1] for p in pts)

        for py in range(min_py, max_py + 1):
            for px in range(min_px, max_px + 1):
                if _point_in_polygon(px, py, pts):
                    img[0, py, px, :] = color

    return _clamp01(img)


def _point_in_polygon(x, y, polygon):
    """Ray casting point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


class PSN_Cube_Preview_Render:
    """Render a built-in unit cube orthographically at a camera angle.

    Reads no FBX or other mesh file; the cube is the only geometry.
    """

    DESCRIPTION = (
        "Renders a built-in unit cube orthographically (clay or shaded) at a "
        "camera angle around the Y axis. It does not read FBX or any other "
        "mesh file."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "render_mode": (RENDER_MODES,),
                "camera_angle": ("FLOAT", {"default": 0.0, "min": -6.2832, "max": 6.2832}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("rendered_image", "mesh_description")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, render_mode, camera_angle):
        if render_mode not in RENDER_MODES:
            render_mode = "clay"

        verts, faces = _default_mesh()
        img = _render_mesh(verts, faces, render_mode, camera_angle)
        desc = "built-in unit cube (%d vertices, %d faces)" % (len(verts), len(faces))
        return (img, desc)


NODE_CLASS_MAPPINGS = {
    "PSN_Cube_Preview_Render": PSN_Cube_Preview_Render,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Cube_Preview_Render": "Cube Preview Render",
}
