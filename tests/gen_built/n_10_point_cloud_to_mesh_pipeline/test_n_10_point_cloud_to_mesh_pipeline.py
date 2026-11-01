"""Tests for n_10_point_cloud_to_mesh_pipeline.py"""

import torch

from n_10_point_cloud_to_mesh_pipeline import (
    PSN_Depth_To_PointCloud,
    PSN_PointCloud_To_Mesh,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------

def test_node_registration():
    assert "PSN_Depth_To_PointCloud" in NODE_CLASS_MAPPINGS
    assert "PSN_PointCloud_To_Mesh" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Depth_To_PointCloud"] == "PSN Depth To Point Cloud"
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_PointCloud_To_Mesh"] == "PSN Point Cloud To Mesh"


# ---------------------------------------------------------------------------
# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
# ---------------------------------------------------------------------------

def test_input_types():
    it = PSN_Depth_To_PointCloud.INPUT_TYPES()
    assert "required" in it
    assert "IMAGE" in it["required"]
    assert "DEPTH_MAP" in it["required"]
    assert "CAMERA_INTRINSICS" in it["required"]

    it2 = PSN_PointCloud_To_Mesh.INPUT_TYPES()
    assert "required" in it2
    assert "POINT_CLOUD" in it2["required"]
    assert "COLORS" in it2["required"]
    assert "METHOD" in it2["required"]
    assert "DETAIL" not in it2["required"]  # was ignored, removed
    assert it2["required"]["METHOD"][0] == ["convex_hull", "ball_pivoting", "delaunay"]

    assert PSN_Depth_To_PointCloud.RETURN_TYPES == ("TENSOR", "TENSOR")
    assert PSN_Depth_To_PointCloud.RETURN_NAMES == ("POINT_CLOUD", "COLORS")
    assert PSN_Depth_To_PointCloud.FUNCTION == "run"
    assert PSN_Depth_To_PointCloud.CATEGORY == "ParametricStudio/PointCloud"

    assert PSN_PointCloud_To_Mesh.RETURN_TYPES == ("TRIMESH",)
    assert PSN_PointCloud_To_Mesh.RETURN_NAMES == ("MESH",)
    assert PSN_PointCloud_To_Mesh.FUNCTION == "run"
    assert PSN_PointCloud_To_Mesh.CATEGORY == "ParametricStudio/PointCloud"


# ---------------------------------------------------------------------------
# 3. Depth -> Point Cloud: basic back-projection
# ---------------------------------------------------------------------------

def test_depth_to_pointcloud_basic():
    node = PSN_Depth_To_PointCloud()
    # 4x4 image, all white
    image = torch.ones((1, 4, 4, 3), dtype=torch.float32)
    # depth: all 2.0 (uniform plane at z=2)
    depth = torch.full((1, 4, 4), 2.0, dtype=torch.float32)
    # intrinsics: fx=fy=100, cx=1.5, cy=1.5 (center of 4x4 grid)
    K = torch.tensor([[100.0, 0.0, 1.5],
                      [0.0, 100.0, 1.5],
                      [0.0, 0.0, 1.0]], dtype=torch.float32)

    points, colors = node.run(image, depth, K)

    assert points.shape == (16, 3), f"expected 16 points, got {points.shape}"
    assert colors.shape == (16, 3), f"expected 16 colors, got {colors.shape}"
    # all z should be 2.0
    assert torch.allclose(points[:, 2], torch.full((16,), 2.0)), "z should all be 2.0"
    # pixel (row=1, col=1) is at index 1*4+1 = 5
    # x = (1 - 1.5) * 2 / 100 = -0.01, y = (1 - 1.5) * 2 / 100 = -0.01
    assert torch.allclose(points[5, :2], torch.tensor([-0.01, -0.01]), atol=1e-5), \
        f"pixel (1,1) should project to (-0.01, -0.01), got {points[5]}"
    # colors should all be white
    assert torch.allclose(colors, torch.ones((16, 3))), "colors should be white"


# ---------------------------------------------------------------------------
# 4. Depth -> Point Cloud: zero depth pixels are skipped
# ---------------------------------------------------------------------------

def test_depth_to_pointcloud_zero_depth():
    node = PSN_Depth_To_PointCloud()
    image = torch.ones((1, 3, 3, 3), dtype=torch.float32)
    depth = torch.zeros((1, 3, 3), dtype=torch.float32)
    depth[0, 1, 1] = 1.0  # only center pixel has depth
    K = torch.tensor([[50.0, 0.0, 1.0],
                      [0.0, 50.0, 1.0],
                      [0.0, 0.0, 1.0]], dtype=torch.float32)

    points, colors = node.run(image, depth, K)
    assert points.shape == (1, 3), f"expected 1 point, got {points.shape}"
    assert colors.shape == (1, 3)
    assert torch.allclose(points[0, 2], torch.tensor(1.0)), "z should be 1.0"


# ---------------------------------------------------------------------------
# 5. Depth -> Point Cloud: all-zero depth returns empty
# ---------------------------------------------------------------------------

def test_depth_to_pointcloud_all_zero():
    node = PSN_Depth_To_PointCloud()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    depth = torch.zeros((1, 2, 2), dtype=torch.float32)
    K = torch.eye(3, dtype=torch.float32)

    points, colors = node.run(image, depth, K)
    assert points.shape == (0, 3)
    assert colors.shape == (0, 3)


# ---------------------------------------------------------------------------
# 6. Depth -> Point Cloud: bad input (wrong image dims)
# ---------------------------------------------------------------------------

def test_depth_to_pointcloud_bad_image():
    node = PSN_Depth_To_PointCloud()
    image = torch.ones((1, 4, 4), dtype=torch.float32)  # 3D, not 4D
    depth = torch.ones((1, 4, 4), dtype=torch.float32)
    K = torch.eye(3, dtype=torch.float32)
    try:
        node.run(image, depth, K)
        assert False, "should have raised ValueError"
    except (ValueError, TypeError):
        pass


CUBE = torch.tensor([
    [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
    [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
], dtype=torch.float32)


def test_pointcloud_to_mesh_convex_hull():
    node = PSN_PointCloud_To_Mesh()
    colors = torch.ones((8, 3), dtype=torch.float32)

    mesh = node.run(CUBE, colors, "convex_hull")[0]
    assert len(mesh.vertices) == 8
    assert len(mesh.faces) == 12  # 6 quads, 2 triangles each
    assert abs(mesh.volume - 1.0) < 1e-6
    assert abs(mesh.area - 6.0) < 1e-6


def test_old_method_names_rejected():
    node = PSN_PointCloud_To_Mesh()
    colors = torch.ones((8, 3), dtype=torch.float32)
    for old in ("poisson", "alpha_shape"):
        try:
            node.run(CUBE, colors, old)
            assert False, old + " should be rejected"
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# 8. Point Cloud -> Mesh: delaunay method
# ---------------------------------------------------------------------------

def test_pointcloud_to_mesh_delaunay():
    node = PSN_PointCloud_To_Mesh()
    # one tetrahedron: exactly its 4 triangles
    tet = torch.tensor([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=torch.float32)
    mesh = node.run(tet, torch.ones((4, 3)), "delaunay")[0]
    assert len(mesh.faces) == 4
    assert sorted(tuple(sorted(f)) for f in mesh.faces.tolist()) == [
        (0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]

    # cube: every face is a real triangle on 3 distinct cube corners, and the
    # triangulation includes the 12 hull triangles at least
    mesh = node.run(CUBE, torch.ones((8, 3)), "delaunay")[0]
    assert len(mesh.vertices) == 8
    assert len(mesh.faces) >= 12
    assert all(len(set(f)) == 3 for f in mesh.faces.tolist())


def test_delaunay_coplanar_raises_instead_of_hiding():
    node = PSN_PointCloud_To_Mesh()
    flat = torch.tensor([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=torch.float32)
    try:
        node.run(flat, torch.ones((4, 3)), "delaunay")
        assert False, "coplanar input must raise, not fall back to a hull"
    except Exception as e:
        assert not isinstance(e, AssertionError)


def test_ball_pivoting_runs_on_sphere():
    import numpy as np
    rng = np.random.default_rng(0)
    v = rng.normal(size=(400, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    pts = torch.from_numpy(v).float()
    mesh = PSN_PointCloud_To_Mesh().run(pts, torch.ones((400, 3)), "ball_pivoting")[0]
    assert len(mesh.triangles) > 100  # extent was a 3-vector float() TypeError before


# ---------------------------------------------------------------------------
# 9. Point Cloud -> Mesh: bad input (too few points)
# ---------------------------------------------------------------------------

def test_pointcloud_to_mesh_too_few_points():
    node = PSN_PointCloud_To_Mesh()
    pts = torch.tensor([[0, 0, 0], [1, 0, 0]], dtype=torch.float32)  # only 2 points
    colors = torch.ones((2, 3), dtype=torch.float32)
    try:
        node.run(pts, colors, "convex_hull")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 10. Point Cloud -> Mesh: bad input (color count mismatch)
# ---------------------------------------------------------------------------

def test_pointcloud_to_mesh_color_mismatch():
    node = PSN_PointCloud_To_Mesh()
    pts = torch.tensor([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
    ], dtype=torch.float32)
    colors = torch.ones((3, 3), dtype=torch.float32)  # wrong count
    try:
        node.run(pts, colors, "convex_hull")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 11. Point Cloud -> Mesh: bad method
# ---------------------------------------------------------------------------

def test_pointcloud_to_mesh_bad_method():
    node = PSN_PointCloud_To_Mesh()
    pts = torch.tensor([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
    ], dtype=torch.float32)
    colors = torch.ones((8, 3), dtype=torch.float32)
    try:
        node.run(pts, colors, "invalid_method")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 12. End-to-end: depth -> point cloud -> mesh
# ---------------------------------------------------------------------------

def test_end_to_end():
    depth_node = PSN_Depth_To_PointCloud()
    mesh_node = PSN_PointCloud_To_Mesh()

    image = torch.rand((1, 8, 8, 3), dtype=torch.float32)
    depth = torch.rand((1, 8, 8), dtype=torch.float32) * 3.0 + 0.5
    K = torch.tensor([[100.0, 0.0, 3.5],
                      [0.0, 100.0, 3.5],
                      [0.0, 0.0, 1.0]], dtype=torch.float32)

    points, colors = depth_node.run(image, depth, K)
    assert points.shape[0] > 0
    assert points.shape[1] == 3
    assert colors.shape == points.shape

    mesh = mesh_node.run(points, colors, "convex_hull")[0]
    assert mesh is not None
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0


# ---------------------------------------------------------------------------
# run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_node_registration()
    test_input_types()
    test_depth_to_pointcloud_basic()
    test_depth_to_pointcloud_zero_depth()
    test_depth_to_pointcloud_all_zero()
    test_depth_to_pointcloud_bad_image()
    test_pointcloud_to_mesh_convex_hull()
    test_old_method_names_rejected()
    test_pointcloud_to_mesh_delaunay()
    test_delaunay_coplanar_raises_instead_of_hiding()
    test_ball_pivoting_runs_on_sphere()
    test_pointcloud_to_mesh_too_few_points()
    test_pointcloud_to_mesh_color_mismatch()
    test_pointcloud_to_mesh_bad_method()
    test_end_to_end()
    print("ok")
