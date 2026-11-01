"""Tests for PSN_MultiView_Shift_Preview."""

import inspect
import json
import sys

import torch

sys.path.insert(0, ".")

from n_10_multi_view_consistent_image_generatio import (
    PSN_MultiView_Shift_Preview,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _validate_image,
    _parse_angles,
    _apply_rotation_2d,
    _apply_shift,
    _make_view,
)


def test_node_class_mappings():
    """Test that NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS are correct."""
    assert "PSN_MultiView_Shift_Preview" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_MultiView_Shift_Preview"] is PSN_MultiView_Shift_Preview
    assert "PSN_MultiView_Shift_Preview" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_MultiView_Shift_Preview"] == "Multi-View 2D Shift Preview"


def test_input_types():
    """Test that INPUT_TYPES has the required fields."""
    it = PSN_MultiView_Shift_Preview.INPUT_TYPES()
    assert "required" in it
    assert "image" in it["required"]
    assert "num_views" in it["required"]
    assert "angles" in it["required"]
    assert it["required"]["image"] == ("IMAGE",)
    assert it["required"]["num_views"][0] == "INT"
    assert it["required"]["angles"][0] == "STRING"
    assert "optional" not in it  # unused vae input removed


def test_return_types():
    """Test RETURN_TYPES and RETURN_NAMES."""
    assert PSN_MultiView_Shift_Preview.RETURN_TYPES == ("IMAGE",)
    assert PSN_MultiView_Shift_Preview.RETURN_NAMES == ("shifted_copies",)
    assert PSN_MultiView_Shift_Preview.FUNCTION == "run"
    assert PSN_MultiView_Shift_Preview.CATEGORY == "ParametricStudio/MultiView"


def test_basic_generation():
    """Test basic generation with 4 views."""
    node = PSN_MultiView_Shift_Preview()
    # Create a small test image [1, 32, 32, 3]
    img = torch.rand(1, 32, 32, 3)
    angles = json.dumps([{"yaw": 0}, {"yaw": 90}, {"yaw": 180}, {"yaw": 270}])
    result = node.run(img, 4, angles)
    assert len(result) == 1
    views = result[0]
    assert views.shape == (4, 32, 32, 3)
    assert views.min() >= 0.0
    assert views.max() <= 1.0


def test_single_view():
    """Test generation with num_views=1."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(1, 16, 16, 3)
    angles = json.dumps([{"yaw": 45}])
    result = node.run(img, 1, angles)
    views = result[0]
    assert views.shape == (1, 16, 16, 3)


def test_batch_input():
    """Test with batch input [2, 32, 32, 3] and 3 views -> [6, 32, 32, 3]."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(2, 32, 32, 3)
    angles = json.dumps([{"yaw": 0}, {"yaw": 90}, {"yaw": 180}])
    result = node.run(img, 3, angles)
    views = result[0]
    assert views.shape == (6, 32, 32, 3)


def test_empty_angles():
    """Test with empty angles list - should use default distribution."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(1, 32, 32, 3)
    angles = json.dumps([])
    result = node.run(img, 4, angles)
    views = result[0]
    assert views.shape == (4, 32, 32, 3)


def test_single_angle_dict():
    """Test with a single angle dict (not a list)."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(1, 32, 32, 3)
    angles = json.dumps({"yaw": 30, "pitch": 10})
    result = node.run(img, 3, angles)
    views = result[0]
    assert views.shape == (3, 32, 32, 3)


def test_invalid_image_dim():
    """Test that invalid image dimensions raise an error."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(32, 32, 3)  # 3D, not 4D
    angles = json.dumps([])
    try:
        node.run(img, 4, angles)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "4D" in str(e)


def test_invalid_image_range():
    """Test that image values outside [0,1] raise an error."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(1, 32, 32, 3) * 2.0  # Values in [0, 2]
    angles = json.dumps([])
    try:
        node.run(img, 4, angles)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "[0, 1]" in str(e)


def test_invalid_json():
    """Test that invalid JSON raises an error."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(1, 32, 32, 3)
    angles = "not valid json"
    try:
        node.run(img, 4, angles)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid JSON" in str(e)


def test_invalid_num_views():
    """Test that num_views < 1 raises an error."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(1, 32, 32, 3)
    angles = json.dumps([])
    try:
        node.run(img, 0, angles)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert ">= 1" in str(e)


def test_angles_not_string():
    """Test that non-string angles raise an error."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(1, 32, 32, 3)
    try:
        node.run(img, 4, [1, 2, 3])  # List, not string
        assert False, "Should have raised TypeError"
    except TypeError as e:
        assert "JSON string" in str(e)


def test_rotation_2d():
    """Test 2D rotation function."""
    img = torch.rand(32, 32, 3)
    rotated = _apply_rotation_2d(img, 90.0)
    assert rotated.shape == (32, 32, 3)
    assert rotated.min() >= 0.0
    assert rotated.max() <= 1.0


def test_perspective_shift():
    """Test perspective shift function."""
    img = torch.rand(32, 32, 3)
    shifted = _apply_shift(img, 0.5, 0.0)
    assert shifted.shape == (32, 32, 3)
    assert shifted.min() >= 0.0
    assert shifted.max() <= 1.0


def test_parse_angles_list():
    """Test parsing angles as a list."""
    angles = json.dumps([{"yaw": 0}, {"yaw": 90}])
    specs = _parse_angles(angles)
    assert len(specs) == 2
    assert specs[0]["yaw"] == 0
    assert specs[1]["yaw"] == 90


def test_parse_angles_dict():
    """Test parsing angles as a single dict."""
    angles = json.dumps({"yaw": 45})
    specs = _parse_angles(angles)
    assert len(specs) == 1
    assert specs[0]["yaw"] == 45


def test_no_in_place_modification():
    """Test that the input image is not modified in place."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(1, 32, 32, 3)
    img_copy = img.clone()
    angles = json.dumps([{"yaw": 45}])
    node.run(img, 2, angles)
    assert torch.equal(img, img_copy), "Input image was modified in place!"


def test_grayscale_image():
    """Test with grayscale image [B, H, W, 1]."""
    node = PSN_MultiView_Shift_Preview()
    img = torch.rand(1, 32, 32, 1)
    angles = json.dumps([{"yaw": 0}, {"yaw": 90}])
    result = node.run(img, 2, angles)
    views = result[0]
    assert views.shape == (2, 32, 32, 1)


def test_old_generator_name_gone():
    """The node no longer claims to generate views."""
    import n_10_multi_view_consistent_image_generatio as mod
    assert "PSN_MultiView_Generator" not in NODE_CLASS_MAPPINGS
    assert not hasattr(mod, "PSN_MultiView_Generator")
    assert "not new camera views" in PSN_MultiView_Shift_Preview.DESCRIPTION
    assert "vae" not in inspect.signature(PSN_MultiView_Shift_Preview.run).parameters


def test_yaw_shifts_by_known_pixels():
    """yaw=90 shifts the sampling grid by 0.15 (normalized) = 2.325 px on 32 px width."""
    W = 32
    ramp = (torch.arange(W, dtype=torch.float32) / (W - 1)).view(1, 1, W, 1).expand(1, 8, W, 3).contiguous()
    out = PSN_MultiView_Shift_Preview().run(ramp, 1, json.dumps([{"yaw": 90}]))[0]
    expected = (torch.arange(W, dtype=torch.float32) + 2.325) / (W - 1)
    # interior columns sample inside the image, so they follow the ramp exactly
    assert torch.allclose(out[0, 3, :28, 0], expected[:28], atol=1e-4)
    # last columns sample beyond the edge and are blended with the zero border
    assert out[0, 3, -1, 0] < 0.2
    # rows are not shifted vertically
    assert torch.allclose(out[0, 0], out[0, 7])


def test_roll_90_rotates_pixels_exactly():
    """roll=90 maps out[y, x] = in[W-1-x, y] on a square image."""
    n = 8
    img = (torch.arange(n * n, dtype=torch.float32) / (n * n)).view(1, n, n, 1)
    out = PSN_MultiView_Shift_Preview().run(img, 1, json.dumps([{"roll": 90}]))[0]
    for y in range(n):
        for x in range(n):
            assert abs(out[0, y, x, 0].item() - img[0, n - 1 - x, y, 0].item()) < 1e-4


def test_zero_angle_view_is_identical_copy():
    img = torch.rand(1, 16, 16, 3)
    out = PSN_MultiView_Shift_Preview().run(img, 1, json.dumps([{}]))[0]
    assert torch.equal(out, img)


def test_views_differ_when_angles_differ():
    img = torch.rand(1, 16, 16, 3)
    out = PSN_MultiView_Shift_Preview().run(img, 2, json.dumps([{"yaw": 0}, {"yaw": 90}]))[0]
    assert torch.equal(out[0], img[0])
    assert not torch.allclose(out[0], out[1])


def main():
    test_node_class_mappings()
    test_input_types()
    test_return_types()
    test_basic_generation()
    test_single_view()
    test_batch_input()
    test_empty_angles()
    test_single_angle_dict()
    test_invalid_image_dim()
    test_invalid_image_range()
    test_invalid_json()
    test_invalid_num_views()
    test_angles_not_string()
    test_rotation_2d()
    test_perspective_shift()
    test_parse_angles_list()
    test_parse_angles_dict()
    test_no_in_place_modification()
    test_grayscale_image()
    test_old_generator_name_gone()
    test_yaw_shifts_by_known_pixels()
    test_roll_90_rotates_pixels_exactly()
    test_zero_angle_view_is_identical_copy()
    test_views_differ_when_angles_differ()
    print("ok")


if __name__ == "__main__":
    main()
