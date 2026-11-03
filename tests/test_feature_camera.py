"""Camera Paths: the checker on synthetic camera moves (no clips from the test set), the drawn-path maths, the page's routes and graphs. No ComfyUI, no GPU, no live ports."""
import json, math
from pathlib import Path
import numpy as np
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from psn_nodes import camera_path as CP
from studio import camera_verify as V, feature_camera as F

REPO = Path(__file__).resolve().parents[1]


def _texture(h=360, w=640, seed=0):
    import cv2
    rng = np.random.default_rng(seed); t = rng.integers(0, 255, (h, w), dtype=np.uint8)
    return cv2.GaussianBlur(t, (0, 0), 2.0)


def _frames(kind, n=40, step=3.0, w=384, h=216):
    """A big texture seen through a moving window: a known camera move, made here."""
    import cv2
    big = _texture(h * 3, w * 3); cy, cx = big.shape[0] / 2, big.shape[1] / 2; out = []
    for i in range(n):
        dx = dy = 0.0; s = 1.0
        if kind == "pan_left": dx = -step * i              # the window moves left, so the picture slides right
        if kind == "tilt_up": dy = -step * i
        if kind == "zoom_in": s = 1.0 + 0.006 * i
        M = np.float32([[s, 0, (1 - s) * cx + dx * 0], [0, s, (1 - s) * cy]]); M[0, 2] -= dx; M[1, 2] -= dy
        warped = cv2.warpAffine(big, M, (big.shape[1], big.shape[0]))
        out.append(np.ascontiguousarray(warped[int(cy - h / 2):int(cy + h / 2), int(cx - w / 2):int(cx + w / 2)]))
    return out


def test_a_pan_left_matches_pan_left_and_contradicts_pan_right():
    fr = _frames("pan_left")
    assert V.verify(None, "pan_left", frames=fr)["verdict"] == "MATCH"
    assert V.verify(None, "pan_right", frames=fr)["verdict"] == "MISMATCH"
    m = V.measure(None, fr); assert m["x"] > 0.2 and abs(m["y"]) < 0.02


def test_a_tilt_up_slides_the_picture_down():
    fr = _frames("tilt_up"); r = V.verify(None, "tilt_up", frames=fr)
    assert r["verdict"] == "MATCH" and r["measured"]["y"] > 0.2
    assert V.verify(None, "pan_left", frames=fr)["verdict"] in ("MISMATCH", "INCONCLUSIVE")


def test_a_zoom_reads_as_a_dolly_in_not_a_dolly_out():
    fr = _frames("zoom_in")
    assert V.verify(None, "dolly_in", frames=fr)["verdict"] == "MATCH"
    assert V.verify(None, "dolly_out", frames=fr)["verdict"] == "MISMATCH"


def test_a_still_shot_is_locked_and_not_a_move():
    fr = _frames("none")
    assert V.verify(None, "locked", frames=fr)["verdict"] == "MATCH"
    for mv in ("pan_left", "dolly_in", "orbit_right"): assert V.verify(None, mv, frames=fr)["verdict"] == "MISMATCH"


def test_flat_frames_are_inconclusive_never_a_pass():
    fr = [np.full((216, 384), 128, np.uint8)] * 30
    for mv in ("locked", "pan_left", "dolly_in"): assert V.verify(None, mv, frames=fr)["verdict"] == "INCONCLUSIVE"


def test_unrelated_frames_read_as_cuts():
    fr = [_texture(216, 384, seed=i) for i in range(20)]
    assert V.verify(None, "pan_left", frames=fr)["verdict"] == "INCONCLUSIVE"


def test_a_move_flow_cannot_read_is_always_inconclusive():
    assert V.verify(None, "dolly_zoom", frames=_frames("zoom_in"))["verdict"] == "INCONCLUSIVE"
    assert V.judge({}, "no_such_move")["verdict"] == "INCONCLUSIVE"


def test_a_crane_going_the_other_way_is_inconclusive_not_mismatch():
    m = {"pairs_read": 30, "points_median": 200, "cuts": 0, "inliers_mean": 0.9, "x": 0.0, "y": -0.2, "scale": 0.0, "roll": 0.0, "centre": [0, -0.02], "edge": [0, -0.25], "shake": 0.0}
    assert V.judge(m, "crane_up")["verdict"] == "INCONCLUSIVE" and V.judge(m, "tilt_up")["verdict"] == "MISMATCH"


def test_orbit_needs_the_centre_held_and_the_background_moving_with_the_turn():
    base = {"pairs_read": 30, "points_median": 200, "cuts": 0, "inliers_mean": 0.9, "y": 0.0, "scale": 0.0, "roll": 0.0, "shake": 0.0}
    assert V.judge(base | {"x": 0.12, "centre": [0.01, 0], "edge": [0.2, 0]}, "orbit_right")["verdict"] == "MATCH"
    assert V.judge(base | {"x": -0.12, "centre": [0.01, 0], "edge": [-0.2, 0]}, "orbit_right")["verdict"] == "MISMATCH"
    assert V.judge(base | {"x": 0.2, "centre": [0.2, 0], "edge": [0.2, 0]}, "orbit_right")["verdict"] == "INCONCLUSIVE"     # reads like a pan


def test_pick_takes_the_clearest_match_and_never_an_inconclusive(monkeypatch):
    fake = {"a": {"verdict": "INCONCLUSIVE", "strength": 0.0}, "b": {"verdict": "MATCH", "strength": 0.05}, "c": {"verdict": "MATCH", "strength": 0.2}, "d": {"verdict": "MISMATCH", "strength": 0.0}}
    monkeypatch.setattr(V, "verify", lambda p, mv, frames=None: {"move": mv, "why": "", "said": "", "measured": {}, **fake[p]})
    assert V.pick([("a", "a"), ("b", "b"), ("c", "c"), ("d", "d")], "pan_left")["picked"] == "c"
    r = V.pick([("a", "a"), ("d", "d")], "pan_left"); assert r["picked"] is None and "could not be read" in r["why"]


def test_frames_are_read_from_a_real_file(tmp_path):
    import cv2
    p = tmp_path / "pan.mp4"; fr = _frames("pan_left", n=24); w = cv2.VideoWriter(str(p), cv2.VideoWriter_fourcc(*"mp4v"), 24, (fr[0].shape[1], fr[0].shape[0]))
    for f in fr: w.write(cv2.cvtColor(f, cv2.COLOR_GRAY2BGR))
    w.release(); got, fps = V.read_frames(p)
    assert len(got) == 24 and got[0].shape[1] == V.WIDTH and fps == pytest.approx(24, abs=0.5)


# ---------- the drawn path
def test_a_path_starts_at_the_first_camera_and_passes_through_its_keys():
    m = CP.poses(json.dumps({"keys": [{"t": 0, "pos": [1, 0, 0]}, {"t": 1, "pos": [1, 0, 2]}], "look_at": None}), 9)
    assert np.allclose(m[0], np.eye(4)) and np.allclose(m[-1][:3, 3], [0, 0, 2])


def test_an_orbit_keeps_the_subject_centred_and_moves_the_background_right():
    m = CP.poses(json.dumps(F.PRESETS["orbit_right"]["path"]), 81)
    near, far = CP.screen_motion(m, F.SUBJECT_DEPTH), CP.screen_motion(m, F.SUBJECT_DEPTH * 4)
    assert abs(near["dx"]) < 1e-3 and far["dx"] > 0.3 and F.path_plan(F.PRESETS["orbit_right"]["path"])["expect"] == "orbit_right"


def test_positive_yaw_turns_right_so_the_picture_slides_left():
    m = CP.poses(json.dumps({"keys": [{"t": 0, "pos": [0, 0, 0], "yaw": 0}, {"t": 1, "pos": [0, 0, 0], "yaw": 20}]}), 5)
    assert CP.screen_motion(m)["dx"] < 0


@pytest.mark.parametrize("pid", list(F.PRESETS))
def test_every_preset_expects_a_move_the_checker_can_read(pid):
    exp = F.path_plan(F.PRESETS[pid]["path"])["expect"]
    assert exp in V.MOVES and V.MOVES[exp]["kind"] != "unreadable"


@pytest.mark.parametrize("bad", ["not json", '{"keys": []}', '{"keys": [{"pos": [0,0,0]}]}', '{"keys": [{"t":0,"pos":[0,0,0]},{"t":0,"pos":[0,0,1]}]}', '{"keys": [{"t":0,"pos":[0,0,0]},{"t":1,"pos":[99,0,0]}]}', '{"keys": [{"t":0,"pos":[0,0,0]},{"t":1,"pos":[0,0,4]}], "look_at": [0,0,4]}'])
def test_a_bad_path_says_why(bad):
    with pytest.raises(ValueError): CP.poses(bad, 9)


def test_the_node_wants_wan_lengths():
    with pytest.raises(ValueError): CP.PSN_CameraPathEmbedding().run('{"keys": [{"t":0,"pos":[0,0,0]},{"t":1,"pos":[0,0,1]}]}', 832, 480, 80)
    assert CP.PSN_CameraPathEmbedding.RETURN_TYPES == ("WAN_CAMERA_EMBEDDING", "INT", "INT", "INT")


def test_the_pack_registers_the_node():
    src = (REPO / "__init__.py").read_text()
    assert "camera_path" in src and "PSN_CameraPathEmbedding" in CP.NODE_CLASS_MAPPINGS


# ---------- object lines
def test_a_drawn_line_becomes_one_point_per_frame_in_pixels():
    t = json.loads(F.tracks_json([[[0, 0.5], [1, 0.5]]], frames=11, size=(101, 51)))
    assert len(t) == 1 and len(t[0]) == 11 and t[0][0] == {"x": 0.0, "y": 25.0} and t[0][-1]["x"] == pytest.approx(100.0) and t[0][5]["x"] == pytest.approx(50.0)


@pytest.mark.parametrize("bad", [[], [[[0.1, 0.1]]], [[[0.5, 0.5], [0.5, 0.5]]], [[["a", 1], [0, 0]]], "x"])
def test_a_bad_line_is_refused(bad):
    with pytest.raises(HTTPException): F.tracks_json(bad)


def test_follow_error_is_measured_in_pixels_per_frame():
    drawn = [{"x": 10.0 * i, "y": 50.0} for i in range(5)]
    e = F.follow_error([(10.0 * i / 100, 0.5) for i in range(5)], drawn, (100, 100))
    assert e["mean_px"] == 0.0 and e["frames"] == 5
    e = F.follow_error([(10.0 * i / 100, 0.53) for i in range(4)] + [None], drawn, (100, 100))
    assert e["mean_px"] == pytest.approx(3.0) and e["lost_at"] == 4


# ---------- graphs and page
def test_graphs_take_exactly_what_the_page_fills():
    from studio.graph_template import placeholders
    assert placeholders(json.loads((REPO / "workflows" / F.WAN["graph"]).read_text())) == set(F.wan_values("x.png", F.PRESETS["dolly_in"]["path"], "p", 1))
    assert placeholders(json.loads((REPO / "workflows" / F.LTX["graph"]).read_text())) == set(F.ltx_values("x.png", "[]", "p", 1))


def test_graphs_use_open_weights_and_the_motion_track_lora():
    ltx = json.loads((REPO / "workflows" / F.LTX["graph"]).read_text()); wan = json.loads((REPO / "workflows" / F.WAN["graph"]).read_text())
    assert ltx["lora"]["inputs"]["lora_name"] == "ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors" and ltx["tracks"]["class_type"] == "LTXVDrawTracks"
    assert wan["cam"]["class_type"] == "PSN_CameraPathEmbedding" and wan["i2v"]["inputs"]["camera_conditions"] == ["cam", 0]


def test_page_is_self_registering_and_its_files_exist():
    assert F.PAGE["module"] == "camerapath.js" and F.PAGE["export"] == "CameraPaths"
    web = REPO / "studio" / "web"; js = (web / "camerapath.js").read_text()
    assert "export function CameraPaths" in js and (web / F.PAGE["css"]).exists() and "</${" not in js
    css = (web / "camerapath.css").read_text(); assert "40px" in css or "44px" in css


def _client():
    app = FastAPI(); app.include_router(F.router); return TestClient(app)


def test_overview_lists_moves_presets_and_says_inconclusive_is_not_a_pass():
    r = _client().get("/api/campath").json()
    assert {m["id"] for m in r["moves"]} == set(V.MOVES) and "never counted as a pass" in r["verdicts"]["INCONCLUSIVE"]
    assert r["presets"]["orbit_right"]["plan"]["expect"] == "orbit_right"


def test_routes_refuse_before_touching_comfyui(monkeypatch, tmp_path):
    monkeypatch.setattr(F.paths, "comfy_input", lambda *a: str(tmp_path)); monkeypatch.setattr(F.paths, "output_dir", lambda *a: str(tmp_path))
    monkeypatch.setattr(F.Comfy, "_req", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ComfyUI was called")))
    c = _client()
    assert c.post("/api/campath/render", json={"kind": "nope"}).status_code == 400
    assert c.post("/api/campath/render", json={"kind": "wan_path", "path": {"keys": []}, "image": "a.png", "prompt": "x"}).status_code == 400
    assert c.post("/api/campath/render", json={"kind": "ltx_track", "tracks": [[[0.1, 0.1], [0.9, 0.9]]], "image": "../../etc/passwd.png", "prompt": "x"}).status_code in (400, 404)
    assert c.post("/api/campath/verify", json={"clip": "missing.mp4", "move": "pan_left"}).status_code == 404
    assert c.post("/api/campath/verify", json={"clip": "a.mp4", "move": "warp"}).status_code == 400
    assert c.post("/api/campath/pick", json={"clips": ["a.mp4"], "move": "pan_left"}).status_code == 400


def test_verify_route_reads_a_clip_from_the_output_folder(monkeypatch, tmp_path):
    import cv2
    monkeypatch.setattr(F.paths, "comfy_input", lambda *a: str(tmp_path / "in")); monkeypatch.setattr(F.paths, "output_dir", lambda *a: str(tmp_path))
    (tmp_path / "in").mkdir(); p = tmp_path / "take.mp4"; fr = _frames("pan_left", n=24)
    w = cv2.VideoWriter(str(p), cv2.VideoWriter_fourcc(*"mp4v"), 24, (fr[0].shape[1], fr[0].shape[0]))
    for f in fr: w.write(cv2.cvtColor(f, cv2.COLOR_GRAY2BGR))
    w.release()
    r = _client().post("/api/campath/verify", json={"clip": "take.mp4", "move": "pan_left"}).json()
    assert r["verdict"] == "MATCH" and r["clip"] == "take.mp4"


def test_the_proof_only_holds_real_runs():
    p = REPO / "studio" / "camera_proof.json"
    if not p.exists(): pytest.skip("no proof yet")
    d = json.loads(p.read_text())
    shown = ([d["track"]] if "track" in d else []) + list((d.get("wanpath") or {}).values()) + list((d.get("director") or {}).values()) + list((d.get("pick") or {}).get("takes", []))
    for r in shown: assert r["peak_vram_gib"] > 0 and r["seconds"] > 0 and (REPO / "studio" / "web" / r["src"]).exists()
    for r in (d.get("wanpath") or {}).values(): assert r["verdict"] in V.VERDICTS and r["expect"] in V.MOVES
    if d.get("pick", {}).get("picked"): assert next(x for x in d["pick"]["results"] if x["take"] == d["pick"]["picked"])["verdict"] == "MATCH"
    for r in (d.get("confusion") or {}).get("rows", []): assert r["verdict"] in V.VERDICTS


def test_a_take_set_is_read_through_the_takes_package(tmp_path):
    class T:
        @staticmethod
        def get(sid): return {"id": sid, "takes": [{"i": 0, "status": "done", "kind": "video", "file": "take0.mp4"}, {"i": 1, "status": "done", "kind": "video", "file": "take1.mp4"}, {"i": 2, "status": "error"}]} if sid == "abc" else None
        @staticmethod
        def _dir(sid): return tmp_path
    for n in ("take0.mp4", "take1.mp4"): (tmp_path / n).write_bytes(b"x")
    assert [n for n, _ in F.take_set_files("abc", T)] == ["take 1", "take 2"]
    with pytest.raises(HTTPException): F.take_set_files("nope", T)
