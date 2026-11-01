"""Passes post-processing and the scene payload, with a fake Blender (no GPU, no Blender)."""
import json
import math
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from studio.vset import camera, passes as P, shot as SH
from studio.worldkit import library as L
from tests.vset.helpers import cast_of, good_shot, make_set


def test_depth_range_covers_the_set_from_every_camera_position():
    keys = [{"pos": [0, -5, 1.5]}, {"pos": [0, -2, 1.5]}]
    near, far = P.depth_range(keys, [-6, -6, 0], [6, 6, 3])
    assert near == P.NEAR_M and far >= math.dist((0, -5, 1.5), (6, 6, 3)) - 1e-9


def _person(x=0.0):
    pts = {"hips": [[x, 0, 0.95], [x, 0, 1.05]], "neck": [[x, 0, 1.42], [x, 0, 1.52]], "head": [[x, 0, 1.52], [x, 0, 1.69]],
           "l_upperarm": [[x + 0.17, 0, 1.4], [x + 0.45, 0, 1.4]], "l_forearm": [[x + 0.45, 0, 1.4], [x + 0.7, 0, 1.4]],
           "l_hand": [[x + 0.7, 0, 1.4], [x + 0.8, 0, 1.4]], "r_upperarm": [[x - 0.17, 0, 1.4], [x - 0.45, 0, 1.4]],
           "r_forearm": [[x - 0.45, 0, 1.4], [x - 0.7, 0, 1.4]], "r_hand": [[x - 0.7, 0, 1.4], [x - 0.8, 0, 1.4]],
           "l_thigh": [[x + 0.1, 0, 0.95], [x + 0.1, 0, 0.52]], "l_shin": [[x + 0.1, 0, 0.52], [x + 0.1, 0, 0.09]],
           "l_foot": [[x + 0.1, 0, 0.09], [x + 0.1, -0.12, 0.02]], "r_thigh": [[x - 0.1, 0, 0.95], [x - 0.1, 0, 0.52]],
           "r_shin": [[x - 0.1, 0, 0.52], [x - 0.1, 0, 0.09]], "r_foot": [[x - 0.1, 0, 0.09], [x - 0.1, -0.12, 0.02]]}
    return {"slots": pts, "forward": [0, -1, 0]}


def test_keypoints_follow_openpose_order_and_put_the_face_in_front():
    k = P.keypoints3d(_person())
    assert len(k) == 18 and k[1] == (0, 0, 1.42) and k[2] == (-0.17, 0, 1.4) and k[5] == (0.17, 0, 1.4)
    assert k[0][1] < 0 and k[14][0] < 0 < k[15][0]                      # nose forward; right eye on the right (-X)
    key = {"pos": [0, -4, 1.3], "look": [0, 0, 1.3], "lens_mm": 35.0, "roll_deg": 0.0}
    people = P.project_people({"cast": [_person(), None]}, key, (480, 832))
    assert len(people) == 1 and people[0][2][0] < people[0][5][0]      # the right shoulder is on screen left


def test_draw_pose_paints_limbs_on_black():
    key = {"pos": [0, -4, 1.3], "look": [0, 0, 1.3], "lens_mm": 35.0, "roll_deg": 0.0}
    img = np.asarray(P.draw_pose(P.project_people({"cast": [_person()]}, key, (240, 416)), (240, 416)))
    assert img.shape == (416, 240, 3) and img.sum() > 0 and img[0, 0].sum() == 0


def test_edges_mark_depth_steps_and_object_borders():
    depth = np.zeros((10, 10), np.uint8)
    depth[:, 5:] = 200
    ids = np.zeros((10, 10, 3), np.uint8)
    ids[7:, :] = (255, 0, 0)
    e = P.edges_from(depth, ids)
    assert e[2, 5] == 255 and e[7, 2] == 255 and e[2, 2] == 0 and set(np.unique(e)) <= {0, 255}


def test_scene_payload_loops_a_clip_shorter_than_the_shot():
    lib = L.Library()
    ids = make_set(lib, character=True, clips=[{"name": "walk", "frames": 24, "fps": 24}])
    s = good_shot(ids, cast=cast_of(ids), camera={"preset": "walk_along"}, mode="C", format={"aspect": "9:16", "seconds": 5})
    pl = P.scene_payload(s, library=lib)
    member = pl["cast"][0]
    assert pl["frames"] == 124 and member["repeat"] * 24 >= 124 and member["clip"] == "walk"
    assert len(member["positions"]) == 124 and member["positions"][-1] == [0.0, -3.0]
    assert member["yaw_deg"][0] == 0.0                                  # walking towards -Y: the model's own facing
    east = P.scene_payload(good_shot(ids, cast=cast_of(ids, [[0, 0], [3, 0]])), library=lib)
    assert east["cast"][0]["yaw_deg"][0] == 90.0                        # yaw = atan2(hx, -hy)
    assert pl["camera"] == camera.keys(s["camera"], s["cast"][0]["marks"], 124, seed=s["seed"])
    assert pl["look"]["preset"] == "golden_hour" and pl["props"][0]["rot_deg"] == [0, 0, 30]
    assert pl["size"] == list(SH.size(s)) and pl["depth_range"][0] == P.NEAR_M and not member["hidden"]
    pov = P.scene_payload(good_shot(ids, cast=cast_of(ids), camera={"preset": "pov"}), library=lib)
    assert pov["cast"][0]["hidden"] is True


def test_scene_payload_with_a_place_and_props_alone_follows_the_shots_own_marks():
    lib = L.Library()
    s = good_shot(make_set(lib))
    pl = P.scene_payload(s, library=lib, frames=9, size=(64, 36))
    assert pl["cast"] == [] and pl["frames"] == 9 and pl["size"] == [64, 36]
    assert pl["camera"] == camera.keys(s["camera"], s["marks"], 9, seed=s["seed"])


class FakeBlender:
    """Writes what vs_scene.py writes: shaded/depth/ids frames and pose3d.json."""
    def __init__(self):
        self.payloads = []

    def render(self, script, payload, *, work, **kw):
        self.payloads.append(payload)
        out, n, (w, h) = Path(payload["out_dir"]), payload["frames"], payload["size"]
        for name in ("shaded", "depth", "ids"):
            (out / name).mkdir(parents=True, exist_ok=True)
            for i in range(1, n + 1):
                Image.new("RGB" if name != "depth" else "L", (w, h), 40 * i % 255).save(out / name / f"{i:04d}.png")
        frame = {"cast": [_person()] if payload["cast"] else []}
        (out / "pose3d.json").write_text(json.dumps({"frames": [frame] * n}))
        return {"ok": True, "engine": "cycles", "fallback_note": "EEVEE failed"}


def test_render_scene_writes_every_pass_and_both_stills(tmp_path):
    lib = L.Library()
    ids = make_set(lib, character=True)
    s = good_shot(ids, camera={"preset": "static"}, cast=cast_of(ids))
    encoded = []

    def encode(frames_dir, fps, out):
        encoded.append((Path(frames_dir).name, fps, len(list(Path(frames_dir).glob("*.png")))))
        Path(out).write_bytes(b"mp4")
        return Path(out)

    fb = FakeBlender()
    files, res = P.render_scene(s, library=lib, work=tmp_path / "w", blender=fb, frames=3, size=(64, 112), encode=encode)
    assert sorted(files) == sorted([*P.PASSES, *P.STILLS])
    assert sorted(encoded) == [("depth", 24, 3), ("edges", 24, 3), ("pose", 24, 3), ("shaded", 24, 3)]
    assert files["first"].read_bytes() == (tmp_path / "w" / "frames" / "shaded" / "0001.png").read_bytes()
    assert json.loads((tmp_path / "w" / "camera.json").read_text())[0]["lens_mm"] == camera.LENS_MM
    pose0 = np.asarray(Image.open(tmp_path / "w" / "frames" / "pose" / "0001.png"))
    assert pose0.sum() > 0 and res["fallback_note"] == "EEVEE failed"
    assert fb.payloads[0]["cast"][0]["slots"]["head"] == "bone_4"


def test_a_short_pass_fails_the_step(tmp_path):
    lib = L.Library()

    class Short(FakeBlender):
        def render(self, script, payload, **kw):
            res = super().render(script, payload, **kw)
            next(iter(sorted((Path(payload["out_dir"]) / "depth").glob("*.png")))).unlink()
            return res
    with pytest.raises(RuntimeError, match="of 3 frames"):
        P.render_scene(good_shot(make_set(lib)), library=lib, work=tmp_path / "w", blender=Short(), frames=3, size=(64, 36), encode=lambda d, f, o: Path(o))


def test_the_scene_step_keeps_the_passes_with_the_shot(tmp_path):
    lib = L.Library()
    s = SH.save(good_shot(make_set(lib)))
    called = {}

    def fake(shot, *, library, work, blender=None, **kw):
        called["work"] = work
        return {k: Path(work) / f"{k}.mp4" for k in (*P.PASSES, *P.STILLS)}, {"engine": "cycles"}
    import studio.vset.passes as mod
    orig, mod.render_scene = mod.render_scene, fake
    try:
        out = P.scene_step_outputs(s, {"library": lib})
    finally:
        mod.render_scene = orig
    assert Path(called["work"]) == SH.shot_dir(s["id"]) / "passes" and out["shaded"]["engine"] == "cycles" and out["depth"]["path"].endswith("depth.mp4")
