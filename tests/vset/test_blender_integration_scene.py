"""vs_scene.py on the CPU at a tiny size, 3 frames: every pass has the right frame count, depth has a real range and gets brighter as the camera closes in, the camera really moves, and the pose pass draws the fixture character where the camera maths says it is."""
import numpy as np
from PIL import Image

from studio.vset import camera, passes as P, qc
from studio.worldkit import blender as B, library as L, media, rigmap
from tests.vset.helpers import cast_of, good_shot, make_set
from tests.worldkit.conftest import needs_blender

pytestmark = needs_blender


def _frame(work, name, i, mode="L"):
    return np.asarray(Image.open(work / "frames" / name / f"{i:04d}.png").convert(mode))


def test_a_shot_on_ltx_also_gets_a_grey_clay_pass(wk_fixtures, tmp_path):
    lib = L.Library()
    ids = make_set(lib, place_glb=wk_fixtures / "place.glb", prop_glb=wk_fixtures / "prop.glb")
    s = good_shot(ids, mode="A", mode_settings={"engine": "ltx"}, camera={"preset": "push_in", "params": {"from_m": 5.0, "to_m": 2.0, "easing": "linear"}}, marks=[[0, 0]], look={"preset": "day_clear"})
    work = tmp_path / "w"
    files, _ = P.render_scene(s, library=lib, work=work, frames=3, size=(320, 180), samples=2)
    assert media.frame_count(files["clay"]) == 3
    rgb = _frame(work, "clay", 2, "RGB").astype(float)
    assert abs(rgb[..., 0] - rgb[..., 2]).mean() < 8 and rgb.mean() > 15          # grey, and lit


def test_a_place_and_a_prop_alone_render_every_pass_with_a_real_camera_move(wk_fixtures, tmp_path):
    lib = L.Library()
    ids = make_set(lib, place_glb=wk_fixtures / "place.glb", prop_glb=wk_fixtures / "prop.glb")
    s = good_shot(ids, camera={"preset": "push_in", "params": {"from_m": 5.0, "to_m": 2.0, "easing": "linear"}}, marks=[[0, 0]], look={"preset": "day_clear"})
    work = tmp_path / "w"
    files, res = P.render_scene(s, library=lib, work=work, frames=3, size=(320, 180), samples=4)
    assert res["engine"] == "cycles"
    for name in P.PASSES:
        assert media.frame_count(files[name]) == 3, name
    first, last = _frame(work, "depth", 1), _frame(work, "depth", 3)
    assert first.max() > first.min() and first.shape == (180, 320)
    assert (first != last).mean() > 0.2                                      # the camera moved
    assert last.mean() > first.mean()                                        # closer means brighter
    assert _frame(work, "shaded", 2, "RGB").mean() > 5 and _frame(work, "ids", 2, "RGB").sum() > 0
    assert _frame(work, "pose", 2, "RGB").sum() == 0                         # no cast: an empty pose pass
    assert files["first"].is_file() and files["last"].is_file()
    assert len(np.unique(_frame(work, "ids", 2, "RGB").reshape(-1, 3), axis=0)) <= 8     # flat colours, one per object: no dither, no blended border
    assert 0 < (_frame(work, "edges", 2) > 0).mean() < 0.25                  # lines, not noise
    judged = qc.judge(files["shaded"], work=tmp_path / "qc", edges=str(files["edges"]))
    assert judged["face"] is None and judged["layout"] > 0                  # the lines reach the score. This fixture is a low-contrast box, so the number is small (flicker means nothing over three far-apart frames)


def test_the_depth_pass_matches_the_camera_maths(wk_fixtures, tmp_path):
    """The bright end of the range is near: a pixel on the floor in the middle of the frame maps through the same range the script was given."""
    lib = L.Library()
    ids = make_set(lib, place_glb=wk_fixtures / "place.glb", prop_glb=wk_fixtures / "prop.glb")
    s = good_shot(ids, set={"place": ids["place"], "props": []}, camera={"preset": "custom", "lens_mm": 35, "path": {"start": {"pos": [0, -3, 2.0], "look": [0, 0, 0]}, "end": {"pos": [0, -3, 2.0], "look": [0, 0, 0]}}}, marks=[[0, 0]])
    work = tmp_path / "w"
    P.render_scene(s, library=lib, work=work, frames=1, size=(64, 64), samples=1, encode=lambda d, f, o: o)
    near, far = P.depth_range(camera.keys(s["camera"], [[0, 0]], 1), lib.get(ids["place"])["inspect"]["lo"], lib.get(ids["place"])["inspect"]["hi"])
    z = np.linalg.norm([3.0, 2.0])
    want = 255 * (1 - (z - near) / (far - near))
    assert abs(float(_frame(work, "depth", 1)[32, 32]) - want) <= 6


def test_a_cast_member_renders_and_draws_a_pose_when_a_rig_is_there(wk_fixtures, tmp_path):
    lib = L.Library()
    bones = B.inspect(wk_fixtures / "char.glb", work=tmp_path)["bones"]
    ids = make_set(lib, character=True, char_glb=wk_fixtures / "char.glb", place_glb=wk_fixtures / "place.glb", slots=rigmap.slots(bones))
    s = good_shot(ids, camera={"preset": "static"}, cast=cast_of(ids, [[0, 0]]), set={"place": ids["place"], "props": []})
    work = tmp_path / "w"
    files, _ = P.render_scene(s, library=lib, work=work, frames=3, size=(64, 112), samples=1)
    for name in P.PASSES:
        assert media.frame_count(files[name]) == 3, name
    assert _frame(work, "pose", 2, "RGB").sum() > 0
    key = camera.keys(s["camera"], [[0, 0]], 3)[1]
    x, y, _ = camera.project((0, 0, 1.2), key, (64, 112))
    assert _frame(work, "ids", 2, "RGB")[int(y), int(x)].sum() > 0            # the chest is where we project it
