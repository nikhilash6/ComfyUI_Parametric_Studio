"""The turntable's framing maths (blender_scripts/_fit.py): the bounding sphere and the field of view give the distance."""
import importlib.util
import math
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "studio" / "worldkit" / "blender_scripts" / "_fit.py"
_spec = importlib.util.spec_from_file_location("wk_fit", _SRC)
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)

FOV35 = 2 * math.atan(18 / 35)          # 35 mm lens, 36 mm sensor, square frame


def test_view_angle_is_the_narrower_side():
    assert F.view_angle(35, 36, 512, 512) == pytest.approx(FOV35)
    wide = F.view_angle(35, 36, 1920, 1080)
    assert wide == pytest.approx(2 * math.atan(math.tan(FOV35 / 2) * 1080 / 1920))
    assert F.view_angle(35, 36, 1080, 1920) == pytest.approx(wide)


def test_distance_puts_the_sphere_tangent_to_the_view_cone():
    d = F.fit_distance(1.0, FOV35, margin=1.0)
    assert math.sin(FOV35 / 2) == pytest.approx(1.0 / d)
    assert F.fit_distance(1.0, FOV35) == pytest.approx(d * F.FIT_MARGIN)
    assert 1.10 <= F.FIT_MARGIN <= 1.15


def test_distance_scales_with_size_so_every_asset_fills_the_frame():
    ring, anchor = F.fit_distance(0.025, FOV35), F.fit_distance(0.8, FOV35)
    assert anchor / ring == pytest.approx(0.8 / 0.025)
    # the sphere's outline, seen head on, spans the same share of the frame for both, inside the margin
    fill = lambda r, d: math.tan(math.asin(r / d)) / math.tan(FOV35 / 2)
    assert fill(0.025, ring) == pytest.approx(fill(0.8, anchor))
    assert 1 / F.FIT_MARGIN - 0.05 < fill(0.8, anchor) < 1 / F.FIT_MARGIN


def test_orbit_keeps_the_distance_at_every_turn_and_height():
    c = (1.0, -2.0, 0.09)
    want = F.fit_distance(0.14, FOV35)
    for turn in (0.0, 1.0, math.pi, 5.0):
        for elev in (0.0, 0.08, 0.35, 3.0):
            pos, _, _ = F.orbit(c, 0.14, (0.16, 0.15, 0.18), FOV35, turn, elev)
            assert math.dist(pos, c) == pytest.approx(want)
            assert pos[2] >= c[2]


def test_orbit_height_follows_the_elevation():
    pos, _, _ = F.orbit((0, 0, 0), 1.0, (1, 1, 2), FOV35, 0.0, 0.35)
    assert pos[2] / math.hypot(pos[0], pos[1]) == pytest.approx(0.35)
    assert pos[0] == pytest.approx(0.0) and pos[1] < 0      # turn 0 looks from -Y, as before


def test_flat_assets_are_looked_down_on():
    assert F.rise((2.0, 1.4, 0.012), 0.35) == F.FLAT_RISE
    assert F.rise((2.0, 1.4, 0.012), 1.5) == 1.5             # a steeper ask is kept
    assert F.rise((0.3, 0.3, 1.8), 0.08) == 0.08             # tall: untouched
    assert F.rise((1.0, 1.0, 1.0), 0.35) == 0.35


def test_tiny_and_degenerate_assets_are_not_clipped():
    pos, near, far = F.orbit((0, 0, 0.025), 0.025, (0.05, 0.007, 0.05), FOV35, 0.0, 0.35)
    d = math.dist(pos, (0, 0, 0.025))
    assert near < d - 0.025 and far > d + 0.025
    assert near < 0.1                                         # Blender's default would hide the whole ring
    pos, near, _ = F.orbit((0, 0, 0), 0.0, (0, 0, 0), FOV35, 0.0, 0.35)
    assert math.dist(pos, (0, 0, 0)) == pytest.approx(F.fit_distance(F.MIN_RADIUS, FOV35)) and near > 0


def test_big_assets_keep_the_far_clip():
    pos, near, far = F.orbit((0, 0, 10), 30.0, (40, 25, 22), FOV35, 0.0, 0.35)
    assert near == 0.1 and far >= F.CLIP_END and far > math.dist(pos, (0, 0, 10)) + 30
