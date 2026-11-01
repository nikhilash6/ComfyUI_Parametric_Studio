import json
import math

import pytest
import torch

from psn_nodes.gen.n_2_deterministic_camera_motion import (
    PSN_Camera_Path_Definer,
    PSN_Camera_Apply,
    _parse_keyframes,
    _interp_dim,
    _catmull_rom,
)


def _img(h=8, w=8):
    # unique value per pixel so shifts and rotations are exactly checkable
    return torch.arange(h * w, dtype=torch.float32).reshape(1, h, w, 1).repeat(1, 1, 1, 3)


def _curve(**kw):
    d = {"frame": 0, "x": 0, "y": 0, "z": 1, "rot": 0}
    d.update(kw)
    c, _ = PSN_Camera_Path_Definer().run(json.dumps([d]), "linear", 10)
    return c


def _two_kf():
    return json.dumps([
        {"frame": 0, "x": 0, "y": 0, "z": 1, "rot": 0},
        {"frame": 10, "x": 10, "y": 10, "z": 1, "rot": 0},
    ])


def test_linear_midpoint():
    node = PSN_Camera_Path_Definer()
    curve, _ = node.run(_two_kf(), "linear", 100)
    assert curve["type"] == "KEYFRAMED_CURVE"
    assert "error" not in curve
    app = PSN_Camera_Apply()
    _, px, py, _, _ = app.run(curve, 5, _img())
    assert math.isclose(px, 5.0, abs_tol=1e-9)
    assert math.isclose(py, 5.0, abs_tol=1e-9)


def test_step_holds_until_next_keyframe():
    node = PSN_Camera_Path_Definer()
    curve, _ = node.run(_two_kf(), "step", 100)
    app = PSN_Camera_Apply()
    _, px, _, _, _ = app.run(curve, 9, _img())
    assert math.isclose(px, 0.0, abs_tol=1e-9)
    _, px2, _, _, _ = app.run(curve, 10, _img())
    assert math.isclose(px2, 10.0, abs_tol=1e-9)


def test_cubic_endpoints_match_keyframes():
    node = PSN_Camera_Path_Definer()
    curve, _ = node.run(_two_kf(), "cubic", 100)
    app = PSN_Camera_Apply()
    _, px0, _, _, _ = app.run(curve, 0, _img())
    _, px10, _, _, _ = app.run(curve, 10, _img())
    assert math.isclose(px0, 0.0, abs_tol=1e-9)
    assert math.isclose(px10, 10.0, abs_tol=1e-9)


def test_smoke_no_nans_over_100_frames():
    node = PSN_Camera_Path_Definer()
    kfs = json.dumps([
        {"frame": 0, "x": 0, "y": 0, "z": 1, "rot": 0},
        {"frame": 50, "x": 20, "y": -10, "z": 2, "rot": 90},
        {"frame": 100, "x": 5, "y": 5, "z": 1, "rot": 180},
    ])
    curve, _ = node.run(kfs, "cubic", 100)
    app = PSN_Camera_Apply()
    for f in range(100):
        _, px, py, zoom, rot = app.run(curve, f, _img())
        for v in (px, py, zoom, rot):
            assert not math.isnan(v)
            assert not math.isinf(v)


def test_invalid_json_returns_error_curve():
    node = PSN_Camera_Path_Definer()
    curve, preview = node.run("not json {", "linear", 10)
    assert curve["type"] == "KEYFRAMED_CURVE"
    assert "error" in curve
    assert preview.startswith("ERROR:")


def test_bad_input_non_numeric_dim():
    bad = json.dumps([{"frame": 0, "x": "ten", "y": 0, "z": 1, "rot": 0}])
    parsed, err = _parse_keyframes(bad)
    assert parsed is None
    assert err is not None
    assert "number" in err


def test_duplicate_frames_rejected():
    bad = json.dumps([
        {"frame": 0, "x": 0, "y": 0, "z": 1, "rot": 0},
        {"frame": 0, "x": 1, "y": 1, "z": 1, "rot": 0},
    ])
    parsed, err = _parse_keyframes(bad)
    assert parsed is None
    assert "duplicate" in err


def test_catmull_rom_midpoint_equals_linear_for_collinear():
    # For equally spaced collinear points, Catmull-Rom at t=0.5 equals linear.
    val = _catmull_rom(0.0, 1.0, 2.0, 3.0, 0.5)
    assert math.isclose(val, 1.5, abs_tol=1e-9)


def test_interp_dim_clamps_out_of_range():
    values = [0.0, 10.0]
    frames = [0, 10]
    assert _interp_dim(values, frames, -5, "linear") == 0.0
    assert _interp_dim(values, frames, 99, "linear") == 10.0


def test_apply_invalid_curve():
    app = PSN_Camera_Apply()
    with pytest.raises(ValueError, match="invalid camera_curve"):
        app.run({"type": "WRONG"}, 0, _img())


def test_identity_returns_same_pixels():
    img = _img()
    out, px, py, zoom, rot = PSN_Camera_Apply().run(_curve(), 0, img)
    assert out.shape == img.shape
    assert torch.allclose(out, img, atol=1e-4)


def test_pan_shifts_pixels_right_and_down():
    img = _img()
    out, *_ = PSN_Camera_Apply().run(_curve(x=2, y=1), 0, img)
    # content moves +2 px right, +1 px down: out[y, x] == img[y-1, x-2]
    assert torch.allclose(out[0, 1:, 2:, :], img[0, :-1, :-2, :], atol=1e-4)
    assert torch.all(out[0, 0, :, :] == 0) and torch.all(out[0, :, :2, :] == 0), "uncovered area is black"


def test_zoom_two_enlarges_centre():
    img = _img(4, 4)
    out, *_ = PSN_Camera_Apply().run(_curve(z=2), 0, img)
    assert out.shape == img.shape
    # centre crop of a ramp is enlarged: outer values leave the frame, range shrinks
    assert out.max() < img.max() and out.min() > img.min()
    assert torch.allclose(out[0, 1:3, 1:3, 0].mean(), img[0, 1:3, 1:3, 0].mean(), atol=1e-4)


def test_rotation_90_matches_rot90_clockwise():
    img = _img()
    out, *_ = PSN_Camera_Apply().run(_curve(rot=90), 0, img)
    expect = torch.rot90(img[0], k=-1, dims=(0, 1)).unsqueeze(0)  # clockwise as seen on screen
    assert torch.allclose(out, expect, atol=1e-3)


def test_non_square_pan_and_rotation_shape():
    img = _img(4, 8)
    out, *_ = PSN_Camera_Apply().run(_curve(x=1), 0, img)
    assert out.shape == img.shape
    assert torch.allclose(out[0, :, 1:, :], img[0, :, :-1, :], atol=1e-4)


def test_output_is_image_not_json_string():
    assert PSN_Camera_Apply.RETURN_TYPES[0] == "IMAGE"
    out = PSN_Camera_Apply().run(_curve(), 0, _img())[0]
    assert isinstance(out, torch.Tensor), "transformed_image must be pixels, not a JSON string"


def test_negative_zoom_and_bad_image_rejected():
    with pytest.raises(ValueError, match="zoom"):
        PSN_Camera_Apply().run(_curve(z=-1), 0, _img())
    with pytest.raises(ValueError, match="IMAGE"):
        PSN_Camera_Apply().run(_curve(), 0, torch.zeros(3, 3))
