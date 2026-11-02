"""The Motion page's routes and what guards them, stubbed: no ComfyUI, no GPU, no live port, no real picture check."""
import json
from pathlib import Path
import pytest
from fastapi import HTTPException
from studio import feature_motion as M, graph_registry as G, likeness as L
from studio.worldkit import steps as S

PERSON = next(r for r in M.ROUTES if r["id"] == "latentsync"); WORDS = next(r for r in M.ROUTES if r["id"] == "kimodo_soma")
GOOD = {"ok": True, "why": []}


def test_every_route_says_its_licence_group_and_how_it_runs():
    groups = {g["id"] for g in M.GROUPS}
    for r in M.ROUTES:
        assert r["group"] in groups and r["licence"] and r["commercial"] in (True, False, "conditional") and r["via"] in ("tool", "runner", "family") and r["does"] and r["model_files"]
        if r["via"] == "family": assert r["family"] and r["template"] and set(r["slots"]) == set(r["needs"])


def test_a_route_that_can_show_a_person_is_marked():
    for r in M.ROUTES:
        if {"image", "video"} & set(r["needs"]): assert r["person"], r["id"]


def test_every_person_template_is_guarded():
    for r in M.ROUTES:
        if r["via"] == "family" and r["person"]: assert r["template"] in L.TEMPLATES


@pytest.mark.parametrize("words", ["a nude dance", "make it look like the president", "in the style of a celebrity", "a deepfake of her", "a schoolgirl waves", "a child dances", "swap to my wife"])
def test_words_are_refused(words):
    assert L.words_problem(words)
    with pytest.raises(HTTPException) as e: L.guard(WORDS, {"text": words}, {})
    assert e.value.status_code == 400


def test_plain_words_pass():
    assert L.words_problem("a person walks forward, stops, and waves") == ""
    L.guard(WORDS, {"text": "a person waves"}, {})


def test_a_person_route_wants_the_confirmation_as_true(tmp_path):
    for b in ({}, {"permission": False}, {"permission": "yes"}, {"permission": 1}):
        with pytest.raises(HTTPException) as e: L.guard(PERSON, b, {}, check=lambda p: GOOD)
        assert "permission" in e.value.detail
    L.guard(PERSON, {"permission": True}, {}, check=lambda p: GOOD)


def test_a_picture_that_fails_the_check_stops_the_run(tmp_path):
    with pytest.raises(HTTPException) as e: L.guard(PERSON, {"permission": True}, {"image": tmp_path / "a.png"}, check=lambda p: {"ok": False, "why": ["a face reads as under 20"]})
    assert "under 20" in e.value.detail


def test_a_check_that_cannot_run_does_not_pass(tmp_path):
    with pytest.raises(HTTPException): L.guard(PERSON, {"permission": True}, {"image": tmp_path / "a.png"}, check=lambda p: {"ok": False, "why": []})


def test_a_clip_needs_one_readable_adult_face_and_nothing_else_wrong(tmp_path):
    f = [tmp_path / "1.jpg", tmp_path / "2.jpg"]; frames = lambda p: f
    noface = {"ok": False, "why": ["no face it can read, so it cannot say the character is an adult"]}
    assert "cannot say" in L.video_problem("c.mp4", check=lambda p: noface, frames=frames)
    assert L.video_problem("c.mp4", check=lambda p: GOOD if p == f[0] else noface, frames=frames) == ""
    assert "under 20" in L.video_problem("c.mp4", check=lambda p: {"ok": False, "why": ["a face reads as under 20"]} if p == f[1] else GOOD, frames=frames)
    assert L.video_problem("c.mp4", frames=lambda p: [])


def test_audio_is_not_sent_to_the_picture_check(tmp_path):
    seen = []
    L.guard(PERSON, {"permission": True}, {"audio": tmp_path / "a.wav"}, check=lambda p: seen.append(p) or GOOD); assert not seen


def test_the_family_route_to_the_same_graph_asks_the_same():
    with pytest.raises(HTTPException): L.template_guard("video_wan_animate2_distilled", {"values": {}})
    with pytest.raises(HTTPException): L.template_guard("motion_liveportrait", {"values": {"t": "a nude"}, "permission": True})
    L.template_guard("motion_liveportrait", {"values": {"t": "a calm talk"}, "permission": True}); L.template_guard("some_other_graph", {})


def test_family_template_run_and_apps_run_call_the_guard():
    src = (Path(M.__file__).parent / "families_api.py").read_text(); assert "likeness.template_guard(tid, b)" in src
    assert "likeness.template_guard(aid" in (Path(M.__file__).parent / "apps.py").read_text()


def test_the_receipt_keeps_the_word_and_no_picture(tmp_path):
    a = tmp_path / "in.png"; a.write_bytes(b"x"); out = tmp_path / "o.mp4"
    d = json.loads(L.receipt(out, PERSON, {"permission": True}, {"image": a}, seed=3, seconds=9.0).read_text())
    assert d["permission_confirmed"] is True and d["ai_generated"] is True and d["seed"] == 3 and d["licence"] == PERSON["licence"] and len(d["inputs_sha256"]["image"]) == 64


def test_a_listing_says_why_one_cannot_run():
    rows = M.listing(lambda r: "waiting for x" if r["id"] == "scail2" else ""); s = next(r for r in rows if r["id"] == "scail2")
    assert not s["ready"] and s["why_not"] == "waiting for x"


def test_need_names_a_missing_weight(tmp_path):
    assert "wan_animate_2_distill" in M.need(next(r for r in M.ROUTES if r["id"] == "wan_animate2"), root=tmp_path)


def test_run_refuses_before_starting_anything(monkeypatch):
    monkeypatch.setattr(M, "need", lambda r: ""); monkeypatch.setattr(M.threading, "Thread", lambda **k: pytest.fail("a job started"))
    with pytest.raises(HTTPException): M.run_post({"route": "kimodo_soma", "text": "  "})
    with pytest.raises(HTTPException): M.run_post({"route": "kimodo_soma", "text": "a nude dance"})
    with pytest.raises(HTTPException): M.run_post({"route": "nope"})
    with pytest.raises(HTTPException): M.run_post({"route": "latentsync", "video": "../../etc/passwd", "audio": "x.wav", "permission": True})


def test_execute_marks_a_person_and_writes_a_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(M.paths, "output_dir", lambda *a: str(tmp_path))
    raw = tmp_path / "raw.mp4"; raw.write_bytes(b"v"); seen = []
    out = M.execute(PERSON, {"permission": True}, {}, tmp_path, runner=lambda *a: raw, mark=lambda s, d: (seen.append(s), Path(d).write_bytes(b"m")))
    assert seen == [raw] and Path(str(out) + ".json").is_file() and out.parent.name == "motion"


def test_motion_routes_are_listed_where_pro_api_and_apps_read(monkeypatch):
    rows = G.all_rows(); got = {r["id"] for r in rows if r.get("section") == "motion"}; assert got == {r["id"] for r in M.ROUTES}
    for r in rows:
        if r.get("section") != "motion": continue
        assert r["call"]["path"] == "/api/motion/run" and r["licence"]; m = M.route(r["id"])
        assert ("permission" in r["call"]["body"]) == m["person"] and bool(r["graph_url"]) == (m["via"] == "family")


def test_only_real_results_are_in_the_proof():
    pr = M.proof().get("routes", {}); web = Path(M.__file__).parent / "web"
    for rid, got in pr.items():
        M.route(rid)
        for s in got.get("samples") or []:
            assert (web / s["src"]).is_file() and (web / s["poster"]).is_file() and s["seconds"] and s["peak_vram_gib"] is not None and s["checked"]


def test_page_is_in_the_rail_and_asks():
    assert M.PAGE["tab"] == "motion" and M.PAGE["module"] == "motion.js"; js = (Path(M.__file__).parent / "web" / "motion.js").read_text()
    assert "permission" in js and "ask" in js and "motion:" in (Path(M.__file__).parent / "web" / "app.js").read_text()


def test_every_family_route_fills_nodes_its_template_really_has():
    T = Path(M.__file__).parent / "family_templates"
    idx = {t["name"]: t for t in json.load(open(T / "index.json"))["templates"]}
    for r in M.ROUTES:
        if r["via"] != "family": continue
        g = json.load(open(T / (r["template"] + ".json")))
        for slot in r["slots"].values():
            n, w = slot.split("|"); assert n in g and w in g[n]["inputs"], (r["id"], slot)
        for slot in [*([r["seed_slot"]] if r.get("seed_slot") else []), *r.get("size_slots", [])]:
            n, w = slot.split("|"); assert n in g and w in g[n]["inputs"], (r["id"], slot)
        assert r["template"] in idx and idx[r["template"]]["family"] == r["family"]


def test_no_template_ships_a_sample_person_or_a_box_path():
    T = Path(M.__file__).parent / "family_templates"
    for r in M.ROUTES:
        if r["via"] != "family": continue
        s = (T / (r["template"] + ".json")).read_text()
        for bad in ("/mnt/", "/home/", "girl", "doll", "asian_model"): assert bad not in s, (r["id"], bad)


def test_a_clip_keeps_its_shape():
    assert M.fit_size(512, 768) == (544, 832) and M.fit_size(1280, 720) == (832, 480) and M.fit_size(704, 704) == (832, 832)


def test_a_capture_keeps_its_motion_file_beside_the_film(tmp_path, monkeypatch):
    monkeypatch.setattr(M.paths, "output_dir", lambda *a: str(tmp_path))
    raw = tmp_path / "raw.mp4"; raw.write_bytes(b"v"); bvh = tmp_path / "cap.bvh"; bvh.write_text("HIERARCHY")
    r = M.route("sam3d_capture")
    out = M.execute(r, {"permission": True}, {}, tmp_path, family=lambda *a: (raw, [bvh]), mark=lambda s, d: Path(d).write_bytes(b"m"))
    assert out.with_suffix(".bvh").read_text() == "HIERARCHY"
