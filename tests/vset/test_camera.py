import math

import pytest

from studio import vset
from studio.vset import camera as C


def _dist(k, p):
    return math.dist(k["pos"], p)


def test_root_follows_the_env(tmp_path):
    assert vset.root() == tmp_path / "vset"


def test_ease_endpoints_and_shape():
    for name in C.EASINGS:
        assert C.ease(name, 0) == 0 and C.ease(name, 1) == 1
    assert C.ease("ease_in", 0.5) < 0.5 < C.ease("ease_out", 0.5) and C.ease("ease_in_out", 0.5) == 0.5
    with pytest.raises(ValueError):
        C.ease("wobble", 0.3)


def test_the_cast_walks_its_marks_at_constant_speed_and_faces_where_it_walks():
    path = C.along([[0, 0], [2, 0], [4, 0]], 5)
    assert [round(x, 6) for x, _ in path] == [0, 1, 2, 3, 4]
    assert C.along([[1, 2]], 3) == [(1.0, 2.0)] * 3
    assert C.headings(path)[0] == (1.0, 0.0) and C.headings([(0, 0)] * 3)[0] == (0.0, -1.0)


def test_push_in_closes_in_on_the_chest():
    ks = C.keys({"preset": "push_in"}, [[0, 0]], 25)
    d = [_dist(k, (0, 0, k["pos"][2])) for k in ks]
    assert abs(d[0] - 4.0) < 1e-6 and abs(d[-1] - 1.8) < 1e-6 and all(a >= b for a, b in zip(d, d[1:]))
    assert ks[0]["look"] == [0.0, 0.0, C.CHEST_M] and ks[0]["pos"][1] < 0       # in front: the -Y side
    assert ks[0]["lens_mm"] == C.LENS_MM


def test_orbit_keeps_its_radius_and_sweeps_its_angle():
    ks = C.keys({"preset": "orbit", "params": {"sweep_deg": 90}}, [[0, 0]], 11)
    assert all(abs(math.hypot(k["pos"][0], k["pos"][1]) - 2.6) < 1e-4 for k in ks)      # keys are rounded to 0.01 mm
    a0 = math.atan2(ks[0]["pos"][1], ks[0]["pos"][0])
    a1 = math.atan2(ks[-1]["pos"][1], ks[-1]["pos"][0])
    assert abs(abs(math.degrees(a1 - a0)) - 90) < 1e-3


def test_walk_along_stays_on_the_walkers_left():
    ks = C.keys({"preset": "walk_along"}, [[0, 0], [0, -5]], 11)          # walking towards -Y: the left is +X
    assert all(abs(k["pos"][0] - 2.2) < 1e-6 for k in ks)
    assert ks[-1]["look"][1] == pytest.approx(-5.0)


def test_pov_looks_ahead_from_the_eyes_and_static_never_moves():
    ks = C.keys({"preset": "pov"}, [[0, 0], [5, 0]], 6)
    assert ks[0]["pos"][2] == 1.6 and ks[0]["look"][0] > ks[0]["pos"][0]
    st = C.keys({"preset": "static"}, [[0, 0], [3, 0]], 6)
    assert all(k == st[0] for k in st)


def test_handheld_wobble_is_seeded_and_small():
    a = C.keys({"preset": "handheld"}, [[0, 0]], 30, seed=1)
    b = C.keys({"preset": "handheld"}, [[0, 0]], 30, seed=1)
    c = C.keys({"preset": "handheld"}, [[0, 0]], 30, seed=2)
    assert a == b and a != c
    base = C.keys({"preset": "static", "params": {"dist_m": 2.6}}, [[0, 0]], 1)[0]["pos"]
    assert all(math.dist(k["pos"], base) <= 0.02 * math.sqrt(3) + 1e-9 and abs(k["roll_deg"]) <= 0.6 for k in a)


def test_custom_path_runs_from_start_to_end():
    cam = {"preset": "custom", "lens_mm": 35,
           "path": {"start": {"pos": [0, -6, 1.6], "look": [0, 0, 1.3]}, "end": {"pos": [3, -3, 1.8], "look": [0, 0, 1]},
                    "easing": "linear"}}
    ks = C.keys(cam, [[0, 0]], 5)
    assert ks[0]["pos"] == [0, -6, 1.6] and ks[-1]["pos"] == [3, -3, 1.8] and ks[2]["pos"] == [1.5, -4.5, 1.7]
    assert ks[0]["lens_mm"] == 35


def test_problems_name_every_bad_camera():
    assert C.problems({"preset": "push_in"}) == []
    assert "preset" in C.problems({"preset": "dolly_zoom"})[0]
    bad = " | ".join(C.problems({"preset": "orbit", "params": {"radius_m": "far", "spin": 2, "easing": "bouncy"},
                                 "lens_mm": 500}))
    assert "radius_m" in bad and "spin" in bad and "easing" in bad and "lens_mm" in bad
    assert "path.start" in C.problems({"preset": "custom"})[0]
    with pytest.raises(ValueError):
        C.keys({"preset": "custom"}, [[0, 0]], 3)


def test_project_is_a_pinhole_that_matches_blenders_camera():
    key = {"pos": [0, -5, 1.3], "look": [0, 0, 1.3], "lens_mm": 36.0, "roll_deg": 0.0}
    w, h = 480, 832
    x, y, z = C.project((0, 0, 1.3), key, (w, h))
    assert (round(x, 6), round(y, 6), round(z, 6)) == (240.0, 416.0, 5.0)
    x, y, _ = C.project((1, 0, 2.3), key, (w, h))
    assert round(x, 3) == round(240 + 832 * 1 / 5, 3) and round(y, 3) == round(416 - 832 * 1 / 5, 3)
    assert C.project((0, -6, 1.3), key, (w, h)) is None                        # behind the camera
