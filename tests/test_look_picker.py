"""The look library behind the Create page's look picker: every fragment is safe for work, grouped, and obeys the one-camera-move rule; apply() stacks one per group."""
import json, re, shutil, subprocess, tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from psn.camera import camera_moves
from studio import presets, sfw

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "studio" / "web"
LIB = json.loads((ROOT / "studio" / "look_library.json").read_text(encoding="utf-8"))
app = FastAPI(); app.include_router(presets.router); client = TestClient(app)


def test_counts_and_shape():
    by = {}
    for e in LIB["looks"]: by.setdefault(e["group"], []).append(e)
    assert len(LIB["looks"]) == len({e["id"] for e in LIB["looks"]}) == 461
    assert {g["id"] for g in LIB["groups"]} == set(by)
    assert len(by["style_image"]) == 100 and len(by["style_video"]) == 100
    dk = [e for e in LIB["looks"] if e["id"].startswith("dk-")]
    assert len(dk) == 101, len(dk)  # all 101 director-kit fragments are in
    sections = {s["id"] for s in LIB["sections"]}
    for g in LIB["groups"]: assert g["section"] in sections and g["kind"] in ("both", "image", "video") and g["label"] and g["blurb"]
    for e in LIB["looks"]:
        assert e["label"].strip() and e["phrase"].strip() and e["kind"] in ("both", "image", "video"), e


def test_every_fragment_is_safe_for_work():
    bad = re.compile(r"\b(sexy|sensual|seduct\w*|flirt\w*|bedroom|upskirt|voyeur\w*|submissive|lips? parted|biting|cleavage|bikini|thirst)\b", re.I)
    for e in LIB["looks"]:
        assert not sfw.flagged(e["phrase"], e["label"]), e["id"]
        assert not bad.search(e["phrase"] + " " + e["label"]), e["id"]


def test_only_motion_entries_carry_a_camera_move():
    for e in LIB["looks"]:
        moves = camera_moves(e["phrase"])
        if e["kind"] != "video" and e["group"] != "style_image": assert moves == [], (e["id"], moves)
        if e["group"] == "move": assert e.get("move") is True
        if e["kind"] == "video" and moves and not e["phrase"].startswith("Tilt-shift"): assert e.get("move") is True, e["id"]


def test_library_route_lists_groups_with_counts():
    d = client.get("/api/presets/library").json()
    assert d["total"] == 461 and sum(g["count"] for g in d["groups"]) == 461
    assert client.get("/api/presets").json()["looks"] == presets.LOOKS  # the 24 starters are untouched


def test_apply_stacks_one_per_group_in_order():
    text, notes = presets.apply("a red fox in snow", adds=["lighting-golden-hour", "lighting-blue-hour", "grade-teal-and-orange"], kind="image")
    assert text.startswith("a red fox in snow")
    assert "blue-hour twilight" in text and "golden-hour sun" not in text and "teal and orange colour grading" in text
    assert any("replaces 'Golden hour'" in n for n in notes)


def test_video_only_fragments_skip_pictures():
    text, notes = presets.apply("a lighthouse", adds=["dk-move-crane-up"], kind="image")
    assert text == "a lighthouse" and "video only" in notes[0]


def test_one_camera_move_per_clip():
    text, notes = presets.apply("a lighthouse at dusk", adds=["dk-move-crane-up", "stv-slow-push-in-on-the-subject"], kind="video")
    assert camera_moves(text) == ["crane"] or "cranes up" in text
    assert "push-in" not in text and any("One camera move per clip" in n for n in notes)
    text, notes = presets.apply("pan across the harbour", adds=["dk-move-crane-up"], kind="video")
    assert "cranes up" not in text and any("already present" in n for n in notes)
    text, notes = presets.apply("a harbour", camera="orbit", adds=["dk-move-crane-up"], kind="video")
    assert "cranes up" not in text and "orbit" in text and any("camera preset" in n for n in notes)


def test_a_library_id_works_as_the_look():
    assert "Kodak Portra" in presets.apply("a portrait", look="grade-portra-film", kind="image")


def test_apply_route_takes_adds_and_still_checks_the_prompt():
    r = client.post("/api/presets/apply", json={"prompt": "a city", "kind": "video", "adds": ["dk-era-1980s", "dk-move-whip-pan"]}).json()
    assert "1980s period look" in r["prompt"] and "whip pan" in r["prompt"] and r["notes"] == []
    assert client.post("/api/presets/apply", json={"prompt": "nude", "adds": ["dk-era-1980s"]}).status_code == 400


def test_create_page_shows_the_picker_for_pictures_and_video():
    app_js = (WEB / "app.js").read_text()
    assert 'import { LookPicker } from "./look_picker.js";' in app_js
    assert '<${LookPicker} prompt=${prompt} setPrompt=${setPrompt} kind=${g.kind}/>' in app_js
    assert "/api/presets/library" in (WEB / "look_picker.js").read_text()


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_picker_logic_in_node():
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(WEB / "look_picker_logic.js", t); shutil.copy(ROOT / "tests" / "studio_lanes" / "test_look_picker.mjs", t)
        p = subprocess.run(["node", str(Path(t) / "test_look_picker.mjs")], cwd=t, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and p.stdout.strip() == "ok", p.stderr


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_every_real_entry_applies_and_comes_back_out():
    code = ('import { applyLooks } from "./look_picker_logic.js"; import { readFileSync } from "node:fs"; const d = JSON.parse(readFileSync(process.argv[2], "utf8")); '
            'let bad = []; for (const e of d.looks) { const a = applyLooks("my own words", [], [e.phrase]); const b = applyLooks(a, [e.phrase], []); if (b !== "my own words") bad.push(e.id); } console.log(JSON.stringify(bad));')
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(WEB / "look_picker_logic.js", t); (Path(t) / "x.mjs").write_text(code)
        p = subprocess.run(["node", str(Path(t) / "x.mjs"), str(ROOT / "studio" / "look_library.json")], cwd=t, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout) == []
