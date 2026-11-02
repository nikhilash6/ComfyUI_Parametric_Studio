"""The Music page tells the truth: real files, recorded measurements, a licence for every model, and no pack code here. No test reaches a real ComfyUI."""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from studio import feature_music as M, graph_registry as G, server as S

ROOT = Path(__file__).parent.parent
WEB = ROOT / "studio" / "web"
CAT = json.loads((ROOT / "studio" / "music_models.json").read_text(encoding="utf-8"))
PROOF = json.loads((ROOT / "studio" / "music_proof.json").read_text(encoding="utf-8"))
MODELS = CAT["models"]
BOX = ["/" + "mnt/", "/" + "home/"]
NEW_FILES = ["studio/feature_music.py", "studio/music_models.json", "studio/web/music.js", "studio/web/music_logic.js", "studio/web/music.css", "scripts/build_music_page.py", *[f"workflows/{n}" for n in M.RUNNABLE]]


@pytest.fixture()
def client(): return TestClient(S.app)


def test_the_page_is_wired_into_the_shell(client):
    assert M.PAGE["tab"] == "music" and M.PAGE["label"] == "Music" and (WEB / M.PAGE["module"]).exists() and (WEB / M.PAGE["css"]).exists()
    assert any(p["tab"] == "music" for p in client.get("/api/feature-pages").json()["pages"])
    assert "music:" in (WEB / "app.js").read_text(encoding="utf-8")


def test_every_model_has_a_sourced_licence_and_a_job():
    assert len({m["id"] for m in MODELS}) == len(MODELS)
    for m in MODELS:
        assert m["job"] and m["does"] and m["maker"] and m["runs"] in ("core", "pack", "own tool"), m["id"]
        assert m["licence"]["name"] and m["licence"]["url"].startswith("https://") and m["licence"]["commercial"] in ("yes", "conditional", "no", "unknown"), m["id"]
        assert m["links"], m["id"]


def test_non_commercial_weights_say_so():
    by = {m["id"]: m for m in MODELS}
    for i in ("yue2_int8", "yue2_bf16", "mulacover", "tangoflux", "musicgen_small"): assert by[i]["licence"]["commercial"] == "no", i
    assert "MiniMax-Music3" in by["music3"]["licence"]["use"]


def test_every_model_graph_is_in_the_one_list(client):
    rows = client.get("/api/all-graphs").json()["rows"]; ids = {r["id"] for r in rows}
    for m in MODELS:
        if m.get("goal"): assert m["goal"] in ids, m["id"]
        elif m.get("graph"): assert m["graph"] in ids and m["graph"] in M.RUNNABLE, m["id"]
    for n in M.RUNNABLE:
        if n != "music3_api.json": assert n in G.WORKFLOWS and G.WORKFLOWS[n][1] == "music" and n in G.workflow_files(), n
    assert {r["id"] for r in rows if r.get("sub") == "Music" and r["kind"] == "workflow"} == {n for n in M.RUNNABLE if n != "music3_api.json"}


def test_a_registry_call_is_a_real_body_for_this_page():
    for n, (_, page, call) in G.WORKFLOWS.items():
        if page != "music": continue
        assert call["path"] == "/api/music/run" and call["body"]["graph"] == n
        assert isinstance(M.build(n, call["body"]), dict)


def test_only_real_files_count_as_rendered():
    assert PROOF["renders"], "the page needs at least one real render"
    for key, r in PROOF["renders"].items():
        f = WEB / r["audio"]
        assert r["status"] == "success" and f.exists() and f.suffix == ".m4a" and f.stat().st_size == r["bytes"] and f.stat().st_size < 1_600_000, key
        assert r["seconds"] > 5 and r["lufs"] is not None and r["centroid_hz"] > 0 and len(r["peaks"]) == 240 and r["peak_gib"] > 0 and r["secs"] > 0, key
        assert r["silent_pct"] < 60, key
        assert key in {m["id"] for m in MODELS}, key
    for r in PROOF["extras"]["change"]:
        assert ("audio" in r and (WEB / r["audio"]).exists()) or r.get("problem"), r["id"]


def test_vocals_were_checked_against_the_lyrics():
    by = {m["id"]: m for m in MODELS}
    for key, r in PROOF["renders"].items():
        if by[key]["lyrics"]: assert r["lyrics"]["lines_total"] > 0 and r["heard"], key


def test_it_says_nobody_listened():
    assert "Nobody has listened" in (WEB / "music.js").read_text(encoding="utf-8") and "No person has listened" in M.PAGE["title"][2] and "listened" in PROOF["note"]


def test_the_brief_is_original_and_safe():
    from studio import sfw
    b = PROOF["brief"]; assert not sfw.flagged(b["style"], b["lyrics"], b["caption"], b["instrumental"])
    for line in b["lyrics"].splitlines(): assert not re.match(r"^\s*\[[^\]]+\]\s*\S", line), line      # Music 3 doesn't sing words after a tag on the same line


def test_the_author_is_credited_and_none_of_his_code_is_here():
    r = CAT["roti"]; page = (WEB / "music.js").read_text(encoding="utf-8")
    assert r["author"] == "RyanOnTheInside" and r["pack"] == "https://github.com/ryanontheinside/ComfyUI_RyanOnTheInside" and "RyanOnTheInside" in page and r["install"].startswith("cd ComfyUI/custom_nodes")
    assert next(p for p in r["packs"] if p["name"] == "ComfyUI_RyanOnTheInside")["licence"] == "MIT"
    assert not (ROOT / "ComfyUI_RyanOnTheInside").exists() and not (WEB / "ComfyUI_RyanOnTheInside").exists()
    notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8"); prov = (ROOT / "PROVENANCE.md").read_text(encoding="utf-8")
    assert "RyanOnTheInside" in notice and "RyanOnTheInside" in prov
    assert not any(p["licence"].startswith("No licence") and p["verdict"] == "Used" for p in r["packs"])


def test_nothing_points_at_this_machine():
    for f in NEW_FILES:
        t = (ROOT / f).read_text(encoding="utf-8"); assert not any(x in t for x in BOX), f
    assert not any(x in json.dumps(PROOF) for x in BOX)


def test_state_reads_the_disk(tmp_path):
    (tmp_path / "text_encoders").mkdir(); (tmp_path / "text_encoders" / "t5gemma_b_b_ul2.safetensors.sha256-ok").write_text("x")
    m = {"id": "x", "need": ["t5gemma_b_b_ul2.safetensors"]}
    assert M.state(m, [str(tmp_path)])["state"] == "missing"                                       # a checksum marker is not the weights
    (tmp_path / "text_encoders" / "gemma").mkdir(); (tmp_path / "text_encoders" / "gemma" / "t5gemma_b_b_ul2.safetensors").write_text("x")
    assert M.state(m, [str(tmp_path)]) == {"state": "unproven", "missing": []}
    assert M.state({"id": "x", "need": ["a__b/c.safetensors"]}, [str(tmp_path)])["state"] == "missing"
    assert M.state(m, [])["state"] == "unknown"


def test_build_fills_and_checks():
    g = M.build("music_ace15_turbo_api.json", {"style": "calm", "lyrics": "[Verse]\nHello", "seconds": 9999, "seed": 3, "bpm": 72, "key": "G major"})
    t = g["94"]["inputs"]; assert t["tags"] == "calm" and t["duration"] == 300 and t["seed"] == 3 and t["keyscale"] == "G major" and g["98"]["inputs"]["seconds"] == 300
    assert M.build("music_ace15_turbo_api.json", {"style": "calm", "key": "not a key"})["94"]["inputs"]["keyscale"] == "C major"
    assert "${" not in json.dumps(g)
    with pytest.raises(HTTPException): M.build("music_ace15_turbo_api.json", {"style": ""})
    with pytest.raises(HTTPException): M.build("nope.json", {"style": "calm"})
    with pytest.raises(HTTPException): M.build("music_roti_ace_cover_api.json", {"style": "calm"})             # a cover needs its source
    assert M.build("music_roti_ace_cover_api.json", {"style": "calm", "source": "../../secret.flac"})["4"]["inputs"]["audio"] == "secret.flac"
    with pytest.raises(HTTPException) as e: M.build("music_ace15_turbo_api.json", {"style": "a nude song"})
    assert e.value.status_code == 400


def test_a_pack_graph_tells_you_to_install(client, monkeypatch):
    monkeypatch.setattr(M, "_has_pack_nodes", lambda: False)
    r = client.post("/api/music/run", json={"graph": "music_roti_ace_cover_api.json", "style": "calm", "source": "a.flac"})
    assert r.status_code == 409 and "RyanOnTheInside" in r.json()["detail"] and "install" in r.json()["detail"]


def test_run_queues_on_comfyui(client, monkeypatch):
    sent = {}
    monkeypatch.setattr(S, "comfy_up", lambda: True)
    monkeypatch.setattr(S, "comfy", lambda path, body=None, **k: sent.update(path=path, body=body) or {"prompt_id": "abc"})
    r = client.post("/api/music/run", json={"graph": "music_stable_open_api.json", "style": "calm piano", "seconds": 40, "seed": 5})
    assert r.status_code == 200 and r.json() == {"job": "abc"} and sent["path"] == "/prompt" and sent["body"]["prompt"]["6"]["inputs"]["text"] == "calm piano"
    S.JOBS.pop("abc", None)


def test_run_without_comfyui_says_so(client, monkeypatch):
    monkeypatch.setattr(S, "comfy_up", lambda: False)
    assert client.post("/api/music/run", json={"graph": "music_stable_open_api.json", "style": "calm"}).status_code == 503


def test_styles_really_are_reused():
    page = (WEB / "music.js").read_text(encoding="utf-8"); assert "music_styles_logic.js" in page and '"/api/music-styles"' in page


def test_accessible_and_small_screen_rules_are_there():
    css = (WEB / "music.css").read_text(encoding="utf-8"); page = (WEB / "music.js").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css and "max-width:760px" in css and "#f5c518" in css and "var(--display)" in css
    assert 'role="slider"' in page and "aria-valuetext" in page and "prefers-reduced-motion" in page and "ArrowRight" in page
    assert not re.search(r"https?://|@import", css)


def test_every_unrendered_model_says_why():
    for m in MODELS:
        if m["id"] not in PROOF["renders"]: assert m.get("why_not"), m["id"]


def test_weights_outside_the_library_are_not_claimed():
    # nothing on the page may read as rendered without a recorded render
    for m in MODELS:
        if m["id"] not in PROOF["renders"]: assert not re.search(r"\b(we rendered|proved|sounds)\b", m["does"], re.I), m["id"]


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_the_page_logic():
    code = r'''
import * as L from "./music_logic.js"; import assert from "node:assert";
assert.equal(L.clock(75), "1:15"); assert.equal(L.clock(-3), "0:00");
assert.deepEqual(L.bars([0, 1, 0.5, 0.2], 2), [1, 0.5]); assert.deepEqual(L.bars([], 4), []); assert.equal(L.bars([0.2], 3).length, 3);
assert.equal(L.featureAt([0, 1], 1, 0.5), 0.5); assert.equal(L.featureAt([0, 1], 1, 5), 0); assert.equal(L.featureAt([1, 1], 1, -1), 0); assert.equal(L.featureAt(null, 1, 1), 0);
assert.equal(L.sungLines("[Verse]\nOne\nTwo\n\n[Chorus]\nThree"), 3); assert.equal(L.seconds("[Verse]\nOne"), 30); assert.equal(L.seconds(""), 60); assert.equal(L.seconds(Array(100).fill("x").join("\n")), 300);
assert.equal(L.sameLineTags("[Verse] words\n[Chorus]\nok").length, 1);
assert.ok(L.captionFrom("calm").includes("Global Metadata")); const full = "Global Metadata: a\nVocal Details: b\nArrangement: c"; assert.equal(L.captionFrom(full), full);
const cap = L.runBody({ graph: "g", takes: "caption", lyrics: true, id: "music3" }, { style: "calm", lyrics: "la", seconds: 30 }); assert.ok(cap.caption.includes("calm")); assert.equal(cap.lyrics, "la");
const open = L.runBody({ graph: "g", takes: "prompt", lyrics: false, id: "stable_open" }, { style: "calm", lyrics: "la", seconds: 300 }); assert.equal(open.seconds, 47); assert.equal(open.lyrics, "");
assert.deepEqual(L.counts([{ state: "proven" }, { state: "missing" }]).proven, 1); assert.equal(L.sortModels([{ state: "missing" }, { state: "proven" }])[0].state, "proven");
assert.equal(L.rendered([{ state: "proven", render: { audio: "a" } }, { state: "proven" }]).length, 1);
assert.ok(L.curlFor({ a: "it's" }, "http://x").includes("http://x/api/music/run")); assert.equal(L.versus(1, 1), "same");
for (const f of L.FORMS) assert.equal(L.sameLineTags(f.text).length, 0, f.id);
console.log("ok");
'''
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(WEB / "music_logic.js", t); (Path(t) / "x.mjs").write_text(code)
        p = subprocess.run(["node", str(Path(t) / "x.mjs")], cwd=t, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and "ok" in p.stdout, p.stderr


def test_the_music_specialist_knows_this_page():
    from studio import crew
    notes = ROOT / "studio" / "crew_notes"; now = notes / "model_families" / "17-Music-song-models" / "dossier" / "NOW.md"; t = now.read_text(encoding="utf-8")
    assert "Nobody has listened" in t and "RyanOnTheInside" in t and "Paper Boats" in t and "/api/music/run" in t
    members = crew.roster(str(notes)); me = next(m for m in members if m["id"] == "music-song-models"); assert str(now) in me["files"]
    for q in ("How do I use the music page?", "Who is RyanOnTheInside?", "Can I sell a song from ACE-Step?", "What does the extract guider do?"):
        assert crew.route(q, members) == "music-song-models", q


def test_no_merge_leftovers_in_the_shell():
    # A template literal happily renders a conflict marker as text, and a doubled line renders every page twice.
    for f in WEB.glob("*.js"):
        t = f.read_text(encoding="utf-8"); assert not re.search(r"^(<{7}|={7}|>{7})( |$)", t, re.M), f.name
    app = (WEB / "app.js").read_text(encoding="utf-8"); assert app.count('${t === "pipelines" && html') == 1


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_every_page_script_parses():
    # One doubled declaration in any module the shell imports leaves the whole studio blank.
    for f in WEB.glob("*.js"):
        p = subprocess.run(["node", "--check", "--input-type=module"], input=f.read_text(encoding="utf-8"), capture_output=True, text=True, timeout=60)
        assert p.returncode == 0, (f.name, p.stderr[-300:])
