"""World Kit route logic and the build runner with fakes (no server, no ComfyUI, no GPU), then the router through a TestClient."""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from studio.worldkit import api, characters as CS, library as L, preview, runner, steps as S
from tests.worldkit.helpers import glb_file

READY = lambda name: {"ready": True, "problems": []}                               # noqa: E731
OK = dict(capability=READY)


def _char(tmp_path, status="ready"):
    d = tmp_path / "worldkit" / "_characters" / "savedchar"
    d.mkdir(parents=True, exist_ok=True)
    (d / "body_front.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    from studio.worldkit import picturecheck as PC
    rec = {"ok": True, "version": PC.VERSION, "sha256": PC.sha256(d / "body_front.png")}
    (d / "character.json").write_text(json.dumps({"name": "Ada", "description": "tall, auburn hair", "status": status, "check": rec}))
    return CS.get("savedchar")


def test_build_steps_per_type():
    names = lambda m: [s.name for s in runner.build_steps(m)]                       # noqa: E731
    look = L.new_meta("look", "Night", source={"kind": "preset", "preset": "night_city"}, look={"preset": "night_city"})
    assert names(look) == ["preview", "ingest"]
    p = L.new_meta("prop", "Chair", source={"kind": "text", "prompt": "chair"})
    assert names(p) == ["image", "cutout", "mesh", "cleanup", "preview", "ingest"]


def test_create_each_type_and_refuse_bad_requests(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")
    lib, started = L.Library(), []
    ok = lambda payload, ch=None: api.create(lib, payload, get_character=lambda cid: ch, start=started.append, **OK)  # noqa
    code, body = ok({"type": "character", "source": {"character_id": "savedchar"}}, _char(tmp_path))
    assert code == 200 and body["asset"]["name"] == "Ada" and started == [body["asset"]["id"]]
    meta = lib.get(body["asset"]["id"])
    assert meta["source"]["description"] == "tall, auburn hair" and meta["build"]["steps"][0]["name"] == "sheet" and "TRELLIS.2" in meta["licence_note"]
    assert ok({"type": "character", "source": {"character_id": "x"}}, _char(tmp_path, "failed"))[0] == 400
    assert ok({"type": "prop", "source": {"prompt": "a red chair"}})[0] == 200
    code, body = ok({"type": "place", "source": {"brief": "rainy downtown block"}})
    assert code == 200 and lib.get(body["asset"]["id"])["recipe"]["kit"] == "street"
    assert ok({"type": "look", "source": {"preset": "golden_hour", "weather": "rain"}})[0] == 200
    for bad in ({"type": "dragon"}, {"type": "place", "source": {}}, {"type": "look", "source": {"preset": "x"}},
                {"type": "prop", "session_id": "../x", "source": {"prompt": "x"}}, {"type": "prop", "source": {}}):
        assert ok(bad)[0] == 400, bad


def test_the_character_maker_refuses_while_off_even_for_a_good_sheet(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "0")
    lib = L.Library()
    code, body = api.create(lib, {"type": "character", "source": {"character_id": "savedchar"}}, get_character=lambda c: _char(tmp_path), start=lambda a: None, **OK)
    assert code == 403 and "off" in body["error"] and lib.list() == []


def test_a_character_is_only_ever_a_saved_id_never_an_upload(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")
    lib = L.Library()
    code, body = api.create(lib, {"type": "character", "source": {"image": "someone.png"}}, get_character=lambda c: None, start=lambda a: None, **OK)
    assert code == 400 and "saved character" in body["error"]


def test_a_blocked_maker_is_refused_up_front_with_the_plain_reason():
    lib = L.Library()
    blocked = lambda name: {"ready": False, "problems": ["SAM 3D Objects: model still downloading or missing (ss_generator.ckpt)"]}  # noqa
    code, body = api.create(lib, {"type": "prop", "source": {"prompt": "a chair"}}, get_character=None, start=lambda a: None, capability=blocked)
    assert code == 409 and "still downloading or missing" in body["error"] and lib.list() == []


def test_a_place_and_a_look_need_no_model_at_all(tmp_path):
    from studio.worldkit import capabilities as C
    assert C.route("place")["ready"] and C.route("look")["ready"] and C.route("prop_mesh")["ready"]
    assert not C.route("prop_text")["ready"] and not C.route("character")["ready"]


def _preview_only(tmp_path):
    def fake(ctx, **kw):
        mp4, jpg = tmp_path / "t.mp4", tmp_path / "t.jpg"
        mp4.write_bytes(b"mp4")
        Image.new("RGB", (8, 8)).save(jpg)
        return {"turntable": {"path": str(mp4)}, "thumb": {"path": str(jpg)}}
    return fake


def test_run_build_of_a_look_ingests_its_previews_and_can_be_approved(tmp_path, monkeypatch):
    lib = L.Library()
    _, body = api.create(lib, {"type": "look", "source": {"preset": "night_city"}}, get_character=None, start=lambda a: None)
    aid = body["asset"]["id"]
    monkeypatch.setattr(preview, "render", _preview_only(tmp_path))
    state = runner.run_build(aid, library=lib, seams_={"submit": None, "wait": None})
    meta = lib.get(aid)
    assert state["state"] == "done" and meta["build"]["state"] == "done"
    assert sorted(meta["files"]) == ["preview.mp4", "thumb.jpg"] and lib.path(aid, "thumb.jpg").is_file()
    assert lib.approve(aid)["status"] == "approved"


def test_a_build_that_was_interrupted_shows_as_building_and_retry_resumes_it(tmp_path, monkeypatch):
    lib = L.Library()
    _, body = api.create(lib, {"type": "look", "source": {"preset": "night_city"}}, get_character=None, start=lambda a: None)
    aid = body["asset"]["id"]
    meta = lib.get(aid)
    meta["build"]["steps"][0].update(status="running")
    lib.update(aid, build={**meta["build"], "state": "building"})
    started = []
    assert api.action(lib, aid, "retry", {}, start=started.append, is_running=lambda a: False)[0] == 200
    assert lib.get(aid)["build"]["steps"][0]["status"] == "pending" and started == [aid]


def test_actions_retry_approve_archive_and_running_refusals(tmp_path):
    lib, started = L.Library(), []
    _, body = api.create(lib, {"type": "prop", "source": {"prompt": "chair"}}, get_character=None, start=started.append, **OK)
    aid = body["asset"]["id"]
    assert api.action(lib, aid, "retry", {}, start=started.append, is_running=lambda a: True)[0] == 409
    meta = lib.get(aid)
    meta["build"]["steps"][1].update(status="failed", error="busy")
    lib.update(aid, build={**meta["build"], "state": "failed"})
    assert api.action(lib, aid, "retry", {}, start=started.append, is_running=lambda a: False)[0] == 200
    assert lib.get(aid)["build"]["steps"][1]["status"] == "pending" and started[-1] == aid
    code, body = api.action(lib, aid, "approve", {}, start=None, is_running=lambda a: False)
    assert code == 400 and "still building" in body["error"]
    assert api.action(lib, aid, "cancel", {}, start=None, is_running=lambda a: False)[0] == 409
    assert api.action(lib, aid, "archive", {}, start=None, is_running=lambda a: False)[0] == 200
    assert lib.get(aid) is None
    assert api.action(lib, aid, "approve", {}, start=None, is_running=lambda a: False)[0] == 404
    assert api.action(lib, "abcdefghijkl", "teleport", {}, start=None, is_running=lambda a: False)[0] == 404


def test_a_character_whose_rig_failed_becomes_a_static_prop(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")
    lib, started = L.Library(), []
    _, body = api.create(lib, {"type": "character", "source": {"character_id": "c"}}, get_character=lambda cid: _char(tmp_path), start=started.append, **OK)
    aid = body["asset"]["id"]
    meta = lib.get(aid)
    steps = {r["name"]: r for r in meta["build"]["steps"]}
    steps["mesh"].update(status="done", outputs={"main": {"path": glb_file(tmp_path / "wk_work" / "lod0.glb")}})
    steps["rig"].update(status="failed", error="SkinTokens failed")
    lib.update(aid, build={**meta["build"], "state": "failed"})
    code, body = api.action(lib, aid, "as-prop", {}, start=started.append, is_running=lambda a: False, capability=READY)
    assert code == 200, body
    p = lib.get(body["asset"]["id"])
    assert p["type"] == "prop" and p["source"]["kind"] == "mesh" and p["source"]["mesh"].startswith("lib:character/") and p["recipe"]["size_m"] == 1.7
    from studio.worldkit.makers import prop
    assert prop.mesh_path(p["source"]["mesh"], lib).name == "kept_mesh.glb"


def test_adding_a_clip_makes_assemble_and_later_steps_stale(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")
    lib = L.Library()
    _, body = api.create(lib, {"type": "character", "source": {"character_id": "c"}}, get_character=lambda cid: _char(tmp_path), start=lambda a: None, **OK)
    aid = body["asset"]["id"]
    meta = lib.get(aid)
    for r in meta["build"]["steps"]:
        r.update(status="done", outputs={"main": {"path": "/x"}})
    lib.update(aid, build={**meta["build"], "state": "done"}, status="approved")
    clips = [{"name": "idle", "text": "stands"}, {"name": "dance", "text": "dances happily"}]
    assert api.action(lib, aid, "clips", {"clips": clips}, start=lambda a: None, is_running=lambda a: False)[0] == 200
    m = lib.get(aid)
    st = {r["name"]: r["status"] for r in m["build"]["steps"]}
    assert st["rig"] == "done" and st["motion_dance"] == "pending" and st["assemble"] == "pending" and m["status"] == "draft"


def test_characters_payload_says_who_can_become_3d(tmp_path, monkeypatch):
    code, body = api.characters_payload([_char(tmp_path)])
    assert body["enabled"] and body["characters"][0]["ok"]
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "0")
    code, body = api.characters_payload([_char(tmp_path)])
    assert not body["enabled"] and not body["characters"][0]["ok"] and "off" in body["characters"][0]["why"]


# ---------- the router
def _client():
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _no_builds(monkeypatch):
    monkeypatch.setattr(runner, "start", lambda aid, **k: None)


def test_routes_list_create_get_and_refuse(tmp_path, monkeypatch):
    _no_builds(monkeypatch)
    c = _client()
    assert c.get("/api/worldkit/assets").json() == {"assets": []}
    r = c.post("/api/worldkit/assets", json={"type": "place", "source": {"brief": "a rainy street"}})
    assert r.status_code == 200
    aid = r.json()["asset"]["id"]
    assert c.get(f"/api/worldkit/assets/{aid}").json()["recipe"]["kit"] == "street"
    assert c.get("/api/worldkit/assets?type=place").json()["assets"][0]["id"] == aid
    assert c.get("/api/worldkit/assets?type=dragon").status_code == 400
    assert c.get("/api/worldkit/assets/nosuchassetx").status_code == 404
    assert c.get(f"/api/worldkit/assets/{aid}/file/asset.glb").status_code == 404
    assert c.get(f"/api/worldkit/assets/{aid}/file/meta.json").status_code == 404
    assert "looks" in c.get("/api/worldkit/looks").json() and c.get("/api/worldkit/exports").json() == {"exports": []}
    assert c.get("/api/worldkit/exports/../x.zip").status_code == 404
    assert c.get("/api/worldkit/characters").json()["enabled"] is True


def test_a_refused_word_stops_at_the_door_in_every_field(monkeypatch):
    _no_builds(monkeypatch)
    c = _client()
    for payload in ({"type": "place", "source": {"brief": "a nude beach"}}, {"type": "place", "name": "explicit", "source": {"brief": "a street"}},
                    {"type": "prop", "source": {"prompt": "a naked statue"}}, {"type": "place", "tags": ["erotic"], "source": {"brief": "a street"}},
                    {"type": "prop", "source": {"prompt": "a child in a bikini"}}):
        r = c.post("/api/worldkit/assets", json=payload)
        assert r.status_code == 400 and "safe-for-work" in r.json()["detail"], payload
    assert c.get("/api/worldkit/assets").json() == {"assets": []}


def test_capabilities_are_read_from_the_disk_each_time(tmp_path, monkeypatch):
    c = _client()
    d = c.get("/api/worldkit/capabilities").json()
    assert d["makers"]["place"]["ready"] is True or d["blender"]
    assert not d["makers"]["prop_text"]["ready"] and any("still downloading or missing" in p for p in d["makers"]["prop_text"]["problems"])
    assert not d["makers"]["character"]["ready"] and d["characters_on"] is True and d["gpu"] is False
    assert not any(" off " in p for p in d["makers"]["character"]["problems"]) and any("Krea 2" in p for p in d["makers"]["character_sheet"]["problems"])
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "0")
    d = c.get("/api/worldkit/capabilities").json()
    assert d["characters_on"] is False and "off" in d["makers"]["character"]["problems"][0] and "off" in d["makers"]["character_sheet"]["problems"][0]


def test_files_are_served_from_the_library(tmp_path):
    lib = L.Library()
    meta = lib.create(L.new_meta("prop", "chair", source={"kind": "text", "prompt": "chair"}))
    lib.path(meta["id"], "thumb.jpg").write_bytes(b"\xff\xd8jpeg")
    r = _client().get(f"/api/worldkit/assets/{meta['id']}/file/thumb.jpg")
    assert r.status_code == 200 and r.content == b"\xff\xd8jpeg" and r.headers["content-type"] == "image/jpeg"


def test_the_studio_mounts_the_router_and_the_page_is_wired():
    from studio import server as SV
    assert "/api/worldkit/assets" in SV.app.openapi()["paths"]
    app = Path(SV.WEB / "app.js").read_text(encoding="utf-8")
    assert '["worldkit", "World Kit"]' in app and "WorldKit" in app and (SV.WEB / "worldkit.js").is_file()
    assert "colonly" in (SV.WEB / "viewer3d.js").read_text(encoding="utf-8")
