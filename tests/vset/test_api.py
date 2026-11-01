"""The route logic with fakes, then the router through a TestClient."""
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from studio.vset import api, needs, shot as SH
from studio.worldkit import library as L
from tests.vset.helpers import good_shot, make_set

@pytest.fixture(autouse=True)
def _blender_here(monkeypatch):
    """Route logic does not need a real Blender; the integration tests do."""
    monkeypatch.setattr(api.C, "blender_problem", lambda: "")


READY = lambda shot: []                                                            # noqa: E731
NOT_RUNNING = lambda k: False                                                      # noqa: E731


def test_meta_lists_modes_presets_and_looks():
    code, body = api.meta_payload()
    assert code == 200 and set(body["modes"]) == {"A", "B", "C", "D"} and "selfie_arm" not in body["presets"]
    assert body["lens_mm"] == 35.0 and any(x["id"] == "golden_hour" for x in body["looks"]) and body["engines"] == ["h3", "wan", "ltx"]


def test_camera_preview_returns_keys_the_subject_path_and_the_set():
    lib = L.Library()
    s = good_shot(make_set(lib), mode="B")
    code, body = api.camera_preview({"shot": s}, library=lib)
    assert code == 200 and body["frames"] == 124 and len(body["keys"]) == 124 and len(body["subject"]) == 124 and body["cast"] == []
    assert body["bounds"] == {"lo": [-6, -6, 0], "hi": [6, 6, 3]} and body["size"] == [1344, 768]
    assert api.camera_preview({"shot": {**s, "camera": {"preset": "drone"}}}, library=lib)[0] == 400
    assert api.camera_preview({"shot": {**s, "marks": "nowhere"}}, library=lib)[0] == 400
    assert api.camera_preview({}, library=lib)[0] == 400


def test_save_validates_and_an_edit_resets_the_render_state():
    lib = L.Library()
    s = good_shot(make_set(lib))
    code, body = api.save_shot({"shot": s}, library=lib, is_running=NOT_RUNNING)
    assert code == 200
    sid = body["shot"]["id"]
    SH.save_state(sid, {"state": "done", "steps": []})
    code, _ = api.save_shot({"shot": {"id": sid, "prompt": "rain starts to fall"}}, library=lib, is_running=NOT_RUNNING)
    assert code == 200 and SH.load(sid)["prompt"] == "rain starts to fall" and SH.load_state(sid) == {}
    assert api.save_shot({"shot": {**s, "seed": -4}}, library=lib, is_running=NOT_RUNNING)[0] == 400
    assert api.save_shot({"shot": {"id": sid}}, library=lib, is_running=lambda k: True)[0] == 409
    code, body = api.save_shot({"shot": {**s, "id": sid, "prompt": "a nude figure walks by"}}, library=lib, is_running=NOT_RUNNING)
    assert code == 400 and "safe-for-work" in body["error"]


def test_render_refuses_a_missing_model_in_plain_words_and_passes_only_does_not_care(monkeypatch):
    lib, started = L.Library(), []
    sid = SH.save(good_shot(make_set(lib)))["id"]
    code, body = api.render_shot(sid, library=lib, start=lambda s, p=False: started.append(s), is_running=NOT_RUNNING, capability=lambda shot: ["MiniMax H3 first and last frame: model still downloading or missing"])
    assert code == 409 and "still downloading or missing" in body["error"] and started == []
    code, _ = api.render_shot(sid, library=lib, start=lambda s, p=False: started.append((s, p)), is_running=NOT_RUNNING, passes_only=True)
    assert code == 200 and started == [(sid, True)]


def test_the_real_file_check_says_what_is_missing(monkeypatch, tmp_path):
    """No weights under the test's models folder: every mode says so. A marker file does not count."""
    models = tmp_path / "models"
    d = models / "diffusion_models"
    d.mkdir(parents=True)
    (d / "minimax_h3_fl2va_pruned_int8_convrot.safetensors.sha256-ok").write_text("abc")
    (d / "minimax_h3_fl2va_pruned_int8_convrot.md").write_text("notes")
    r = needs.report()
    assert all(not v["ready"] for v in r["routes"].values())
    assert any("MiniMax H3 first and last frame" in p for p in r["routes"]["C_raw"]["problems"])
    assert any("Wan 2.2 Fun Control" in p for p in r["routes"]["A_wan"]["problems"])
    (d / "minimax_h3_fl2va_pruned_int8_convrot.safetensors").write_bytes(b"x" * 10)      # too small to be the model
    assert any("MiniMax H3 first and last frame" in p for p in needs.report()["routes"]["C_raw"]["problems"])


def test_each_route_names_only_what_it_uses():
    s = SH.new_shot(mode="C", mode_settings={"keyframes": "raw"})
    assert needs.route_name(s) == "C_raw" and "qwen21" not in needs.ROUTES["C_raw"]
    assert needs.route_name(SH.new_shot(mode="A", mode_settings={"engine": "wan"})) == "A_wan"
    assert needs.route_name(SH.new_shot(mode="B")) == "B"


def test_render_and_retry_start_the_runner(tmp_path):
    lib, started = L.Library(), []
    start = lambda s, p=False: started.append(s)                                   # noqa: E731
    sid = SH.save(good_shot(make_set(lib)))["id"]
    assert api.render_shot(sid, library=lib, start=start, is_running=NOT_RUNNING, capability=READY)[0] == 200
    assert started == [sid] and api.render_shot(sid, library=lib, start=start, is_running=lambda k: True, capability=READY)[0] == 409
    assert api.retry_shot(sid, start=start, is_running=NOT_RUNNING)[0] == 400       # never rendered
    SH.save_state(sid, {"state": "failed", "steps": [{"name": "video", "status": "failed", "job_id": "j", "outputs": {}, "error": "x", "note": "", "attempts": 1, "updated": 0}]})
    assert api.retry_shot(sid, start=start, is_running=NOT_RUNNING)[0] == 200
    assert SH.load_state(sid)["steps"][0]["status"] == "pending" and started[-1] == sid
    assert api.render_shot("abcdefghijkl", library=lib, start=start, is_running=NOT_RUNNING, capability=READY)[0] == 404


def test_a_render_keeps_finished_passes_only_when_their_files_are_there(tmp_path):
    lib = L.Library()
    sid = SH.save(good_shot(make_set(lib)))["id"]
    f = tmp_path / "depth.mp4"
    f.write_bytes(b"x")
    rec = {"name": "scene", "status": "done", "job_id": "", "outputs": {"depth": {"path": str(f)}}, "error": "", "note": "", "attempts": 0, "updated": 0}
    SH.save_state(sid, {"state": "done", "steps": [rec, {**rec, "name": "video", "outputs": {"main": {"path": str(f)}}}]})
    api.render_shot(sid, library=lib, start=lambda s, p=False: None, is_running=NOT_RUNNING, capability=READY)
    assert [r["name"] for r in SH.load_state(sid)["steps"]] == ["scene"]
    f.unlink()
    SH.save_state(sid, {"state": "done", "steps": [rec]})
    api.render_shot(sid, library=lib, start=lambda s, p=False: None, is_running=NOT_RUNNING, capability=READY)
    assert SH.load_state(sid) == {}


def test_shot_files_come_from_the_state_by_a_fixed_name(tmp_path):
    lib = L.Library()
    sid = SH.save(good_shot(make_set(lib)))["id"]
    f = tmp_path / "depth.mp4"
    f.write_bytes(b"x")
    SH.save_state(sid, {"state": "done", "steps": [{"name": "scene", "status": "done", "job_id": "", "outputs": {"depth": {"path": str(f)}}, "error": "", "note": "", "attempts": 0, "updated": 0}]})
    assert api.shot_file(sid, "depth") == (f, "video/mp4")
    assert api.shot_file(sid, "../../etc/passwd") is None and api.shot_file(sid, "shaded") is None and api.shot_file("../..", "depth") is None


def test_the_clay_pass_the_summary_links_is_served(tmp_path):
    lib = L.Library()
    sid = SH.save(good_shot(make_set(lib)))["id"]
    f = tmp_path / "clay.mp4"
    f.write_bytes(b"x")
    state = {"state": "done", "steps": [{"name": "scene", "status": "done", "job_id": "", "outputs": {"clay": {"path": str(f)}}, "error": "", "note": "", "attempts": 0, "updated": 0}]}
    SH.save_state(sid, state)
    assert api.summary(SH.load(sid), state, False)["passes"]["clay"].endswith("/file/clay")
    assert api.shot_file(sid, "clay") == (f, "video/mp4")


def test_create_list_from_a_script_then_order_and_render_it():
    lib, started = L.Library(), []
    base = {k: v for k, v in good_shot(make_set(lib)).items() if k not in ("id", "prompt", "camera", "name")}
    code, body = api.create_list({"name": "Cafe", "script": "the door opens\norbit the counter", "base": base}, library=lib)
    assert code == 200 and len(body["list"]["shots"]) == 2
    lid = body["list"]["id"]
    ids = body["list"]["shots"]
    assert api.order_list(lid, list(reversed(ids)))[1]["list"]["shots"] == list(reversed(ids))
    assert api.order_list(lid, ids[:1])[0] == 400
    assert api.render_list(lid, library=lib, start_list=started.append, is_running=NOT_RUNNING, capability=READY)[0] == 200 and started == [lid]
    code, body = api.get_list(lid, is_running=NOT_RUNNING)
    assert code == 200 and [s["id"] for s in body["shots"]] == list(reversed(ids))
    bad = api.create_list({"name": "x", "script": "one", "base": {**base, "mode": "A", "mode_settings": {"engine": "wan"}, "format": {"aspect": "1:1", "seconds": 5}}}, library=lib)
    assert bad[0] == 400 and "shot 1" in bad[1]["error"]
    bad = api.create_list({"name": "x", "script": "a nude figure", "base": base}, library=lib)
    assert bad[0] == 400 and "safe-for-work" in bad[1]["error"]


def test_the_routes(monkeypatch):
    lib = L.Library()
    s = good_shot(make_set(lib))
    started = []
    monkeypatch.setattr(api.runner, "start_shot", lambda sid, **kw: started.append((sid, kw.get("passes_only"))))
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    assert c.get("/api/vset/meta").status_code == 200
    caps = c.get("/api/vset/capabilities").json()
    assert caps["comfyui"] is False and caps["routes"]["A_wan"]["ready"] is False and caps["characters_on"] is False
    assert len(c.post("/api/vset/camera", json={"shot": s}).json()["keys"]) == 124
    sid = c.post("/api/vset/shots", json={"shot": s}).json()["shot"]["id"]
    assert c.get(f"/api/vset/shots/{sid}").json()["shot"]["prompt"] == s["prompt"]
    assert [x["id"] for x in c.get("/api/vset/shots").json()["shots"]] == [sid]
    assert c.post(f"/api/vset/shots/{sid}/passes").status_code == 200 and started[-1] == (sid, True)
    r = c.post(f"/api/vset/shots/{sid}/render")
    assert r.status_code == 409 and "missing" in r.json()["detail"]                 # no weights under the test's models folder
    assert c.post(f"/api/vset/shots/{sid}/cancel").status_code == 409
    assert c.post(f"/api/vset/shots/{sid}/dance").status_code == 404
    assert c.get(f"/api/vset/shots/{sid}/file/depth").status_code == 404 and c.get("/api/vset/shots/abcdefghijkl").status_code == 404
    assert Path(SH.shot_dir(sid) / "shot.json").is_file() and c.get("/api/vset/lists").json() == {"lists": []}


def _shot_on_disk(root, sid, mode, settings, state):
    d = SH.shot_dir(sid, root); d.mkdir(parents=True)
    (d / "shot.json").write_text(json.dumps({"id": sid, "mode": mode, "mode_settings": settings, "created": 1}))
    (d / "state.json").write_text(json.dumps(state))
    return d


def _video_state(path, **extra):
    return {"steps": [{"name": "video", "status": "done", "outputs": {"main": {"path": str(path)}}}], **extra}


def test_route_of_names_the_route_a_shot_used():
    assert api.route_of({"mode": "A", "mode_settings": {"engine": "wan"}}) == "A_wan" and api.route_of({"mode": "A", "mode_settings": {"engine": "ltx", "keyframes": "raw"}}) == "A_ltx_raw"
    assert api.route_of({"mode": "A", "mode_settings": {"engine": "ltx", "keyframes": "qwen"}}) == "A_ltx" and api.route_of({"mode": "A", "mode_settings": {"engine": "h3"}}) == "A"
    assert api.route_of({"mode": "C", "mode_settings": {"keyframes": "raw"}}) == "C_raw" and api.route_of({"mode": "B"}) == "B"


def test_proof_comes_from_shots_on_disk_and_says_only_what_they_show(tmp_path):
    vid = tmp_path / "v.mp4"; vid.write_bytes(b"x")
    _shot_on_disk(tmp_path, "aaaaaaaaaaaa", "B", {}, _video_state(vid, state="done", qc={"ok": True}))
    _shot_on_disk(tmp_path, "bbbbbbbbbbbb", "D", {}, _video_state(vid, state="review", qc={"ok": False}))
    _shot_on_disk(tmp_path, "cccccccccccc", "C", {"keyframes": "raw"}, {"state": "failed"})
    _shot_on_disk(tmp_path, "dddddddddddd", "A", {"engine": "wan"}, {"state": "done", "scope": "passes"})
    _shot_on_disk(tmp_path, "eeeeeeeeeeee", "C", {"keyframes": "qwen"}, _video_state(tmp_path / "missing.mp4", state="done", qc={"ok": True}))
    _shot_on_disk(tmp_path, "ffffffffffff", "A", {"engine": "h3"}, {"state": "pending"})
    _shot_on_disk(tmp_path, "gggggggggggg", "A", {"engine": "ltx", "keyframes": "raw"}, {"state": "building"})
    got = api.route_proofs(is_running=lambda k: k == "shot:gggggggggggg", root=tmp_path)
    assert got["B"]["state"] == "passed" and got["B"]["shot"] == "aaaaaaaaaaaa" and got["D"]["state"] == "review" and got["C_raw"]["state"] == "failed" and got["A_ltx_raw"]["state"] == "running"
    assert "A_wan" not in got and "A" not in got           # passes alone and a shot that has not started prove nothing about a video route
    assert "C" not in got                                  # the run said done, but its video is gone from disk


def test_every_route_reports_a_proof_even_with_no_shots():
    out = api.with_proof({"blender": "", "routes": {"A": {"ready": True}, "B": {"ready": True}}}, {"B": {"state": "passed", "shot": "x"}})
    assert out["routes"]["A"]["proof"]["state"] == "none" and out["routes"]["B"]["proof"]["shot"] == "x" and out["routes"]["A"]["ready"] is True and out["blender"] == ""
