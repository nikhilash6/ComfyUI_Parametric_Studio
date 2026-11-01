"""The Music goal's style library: the data the build leaves in this edition, the API, and what a picked card puts in the prompt. No ComfyUI, no live port, no render."""
import importlib.util, json, re, shutil, subprocess, tempfile
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from studio import music_styles as M, sfw
from studio.goals import GOALS, values_for

ROOT = Path(__file__).resolve().parent.parent; DATA = json.loads((ROOT / "studio" / "music3_styles.json").read_text(encoding="utf-8")); BUILDER = ROOT / "scripts" / "build_music3_styles.py"
STYLES = [(f, s) for f in DATA["families"] for s in f["styles"]]; CARDS = [(s, c) for _, s in STYLES for c in s["cards"]]
needs_builder = pytest.mark.skipif(not BUILDER.exists(), reason="the build script is not part of a public release")

def builder():
    spec = importlib.util.spec_from_file_location("build_music3_styles", BUILDER); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b); return b

@pytest.fixture
def client():
    app = FastAPI(); app.include_router(M.router); return TestClient(app)

# ---- the data
def test_counts_add_up():
    c = DATA["counts"]
    assert c["families"] == len(DATA["families"]) and c["styles"] == len(STYLES) and c["cards"] == len(CARDS)
    assert c["official"]["styles"] + c["studio_authored"]["styles"] == c["styles"] and c["official"]["cards"] + c["studio_authored"]["cards"] == c["cards"]
    assert c["styles"] > 600 and all(s["cards"] for _, s in STYLES)

def test_ids_are_unique_and_every_card_has_a_tempo():
    assert len({s["id"] for _, s in STYLES}) == len(STYLES) and len({c["id"] for _, c in CARDS}) == len(CARDS)
    for _, c in CARDS: assert isinstance(c["bpm"], int) and 30 <= c["bpm"] <= 300, c["id"]

def test_nothing_shipped_hits_the_guide_scan_or_the_sfw_check():
    path = ROOT / "scripts" / "build_processes.py"
    if not path.exists(): pytest.skip("the scan is not part of a public release")
    spec = importlib.util.spec_from_file_location("bp", path); bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
    def texts(v):
        if isinstance(v, str): yield v
        elif isinstance(v, dict):
            for k, x in v.items(): yield k; yield from texts(x)
        elif isinstance(v, list):
            for x in v: yield from texts(x)
    for t in texts({k: v for k, v in DATA.items() if k != "source"}):
        assert not sfw.flagged(t), t[:80]
        for rx in (bp.PAID, bp.BRAND, bp.PRIVATE, bp.LOCAL): assert not rx.search(t), t[:80]
        assert not [m for m in bp.NSFW.finditer(t) if m.group(0).lower() != "minor"], t[:80]        # "minor" is the musical key

def test_no_private_notes_or_fields_left():
    raw = (ROOT / "studio" / "music3_styles.json").read_text(encoding="utf-8")
    for bad in ("comfy" + "_copilot", "docs/research", "/home/", "owner", "the author", "tools/build_"): assert bad not in raw, bad
    for _, c in CARDS:
        for field in ("scene", "caption", "secondary", "kids", "studio_made"): assert field not in c, field

def test_no_kids_or_children_style_is_in_this_edition():
    for _, s in STYLES: assert not re.search(r"kids?\b|child", f"{s['id']} {s['label']}", re.I), s["id"]
    assert "kids-family" not in {f["id"] for f in DATA["families"]}

def test_studio_authored_stays_marked_and_official_stays_unmarked():
    note = "Studio-authored recipe, not an official Music 3 template, untested (nothing has been rendered from it yet)."
    assert DATA["note"] == note
    for _, s in STYLES:
        if s["id"].startswith("studio-"):
            assert s["source"] == "studio" and s["proof"] == "recipe" and s["note"] == note, s["id"]
            for c in s["cards"]: assert c["source"] == "studio" and c["proof"] == "recipe", c["id"]
        else:
            assert "source" not in s and "note" not in s, s["id"]
            for c in s["cards"]: assert "source" not in c and "proof" not in c, c["id"]
    dub = [s for _, s in STYLES if s["id"].startswith("studio-dubstep-")]
    assert len(dub) == 15 and sum(len(s["cards"]) for s in dub) == 42

def test_upstream_licence_travels_with_the_data():
    assert "MiniMax-Music3 Community License" in DATA["source"]["licence"] and re.fullmatch(r"[0-9a-f]{40}", DATA["source"]["commit"])
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "studio/music3_styles.json" in notices and "MiniMax-Music3 Community License" in notices

# ---- the build's filter, on fixtures
def _src():
    card = lambda i, **k: {"id": i, "bpm": 100, "key": "A minor", "mood": "Warm.", "vocal": "A voice.", "palette": "Piano.", "scene": "A runway show.", "language": "English", "gender": "female", "rap": False, "slow": False, "secondary": [], **k}
    main = {"source": {"repo": "r", "path": "p", "commit": "c", "licence": "l"}, "families": [
        {"id": "a", "label": "Aa", "cues": "x", "styles": [{"id": "ok", "label": "Ok", "cards": [card("ok_0001")]}, {"id": "adult-thing", "label": "Adult Thing", "cards": [card("adult-thing_0001"), card("adult-thing_0002")]},
                                                            {"id": "mixed", "label": "Mixed", "cards": [card("mixed_0001"), card("mixed_0002", mood="A seductive groove.")]}, {"id": "gone", "label": "Gone", "cards": [card("gone_0001", vocal="A children's choir.")]}]}]}
    extra = {"families": [{"id": "kids", "label": "Kids", "kids": True, "styles": [{"id": "k", "label": "K", "kids": True, "cards": [card("k_0001", kids=True)]}]}, {"id": "n", "label": "Novelty", "styles": [{"id": "studio-n", "label": "Polka", "studio_made": True, "cards": [card("studio-n_0001", studio_made=True)]}]}]}
    studio = {"families": [{"id": "a", "merge": True, "styles": [{"id": "ok", "label": "Clash", "cards": [card("ok_0009")]}, {"id": "studio-b", "label": "Bass", "aliases": ["wub"], "research": "docs/research/x.md", "cards": [card("studio-b_0001", caption="Global Metadata", felt_bpm=50, tempo_line="t")]}]}, {"id": "zz", "merge": True, "styles": [{"id": "studio-z", "label": "Z", "cards": [card("studio-z_0001")]}]}]}
    return main, extra, studio

@needs_builder
def test_filter_removes_by_reason_and_reports_counts_only():
    d, rep = builder().build(*_src())
    assert [s["id"] for f in d["families"] for s in f["styles"]] == ["studio-b", "mixed", "ok", "studio-n"]
    assert [c["id"] for f in d["families"] for s in f["styles"] if s["id"] == "mixed" for c in s["cards"]] == ["mixed_0001"]
    assert rep["removed"]["families"] == {"children": 1} and rep["removed"]["styles"] == {"adult": 1, "children": 1, "no card left": 1}
    assert "Adult" not in json.dumps(rep) and "seductive" not in json.dumps(rep)
    assert rep["source"] == {"families": 3, "styles": 7, "cards": 9} and rep["kept"]["styles"] == 4

@needs_builder
def test_merge_never_replaces_an_official_id_or_invents_a_family_and_marks_studio_styles():
    d, _ = builder().build(*_src()); by = {s["id"]: s for f in d["families"] for s in f["styles"]}
    assert by["ok"]["label"] == "Ok" and "source" not in by["ok"] and "studio-z" not in by
    assert by["studio-b"]["source"] == "studio" and by["studio-n"]["source"] == "studio" and by["studio-n"]["cards"][0]["proof"] == "recipe"
    c = by["studio-b"]["cards"][0]
    assert c["felt_bpm"] == 50 and "caption" not in c and "scene" not in c and "research" not in by["studio-b"]

@needs_builder
def test_minor_as_a_key_is_not_a_hit_but_the_other_words_are():
    r = builder().reason
    assert r("A minor, sparse minor chords") == "" and r("Adult Contemporary") == "adult" and r("children's choir") == "children" and r("a sultry mood") == "suggestive" and r("fashion runway") == "paid"

# ---- the API
def test_list_is_small_and_marks_studio_styles(client):
    j = client.get("/api/music-styles").json()
    assert j["counts"] == DATA["counts"] and len(j["families"]) == len(DATA["families"])
    rows = {s["id"]: s for f in j["families"] for s in f["styles"]}
    assert rows["studio-dubstep-riddim"]["source"] == "studio" and rows["studio-dubstep-riddim"]["note"] == DATA["note"] and "cards" in rows["hip-hop-trap"]
    assert rows["hip-hop-trap"].get("source") is None and isinstance(rows["hip-hop-trap"]["cards"], int)
    assert "mood" not in json.dumps(j)

def test_detail_has_the_cards_and_family(client):
    j = client.get("/api/music-styles/studio-dubstep-riddim").json()
    assert j["family"] == "club-edm-house-trance" and j["cards"][0]["source"] == "studio" and j["cards"][0]["bpm"] and j["note"]

@pytest.mark.parametrize("sid,code", [("nope", 404), ("BAD..ID", 400), ("a%2Fb", 404)])
def test_detail_refuses_bad_ids(client, sid, code): assert client.get("/api/music-styles/" + sid).status_code == code

def test_missing_or_broken_file_says_so(client, tmp_path, monkeypatch):
    monkeypatch.setattr(M, "_cache", {}); monkeypatch.setattr(M, "DATA", tmp_path / "none.json"); assert client.get("/api/music-styles").status_code == 503
    (tmp_path / "bad.json").write_text("{"); monkeypatch.setattr(M, "DATA", tmp_path / "bad.json"); assert client.get("/api/music-styles").status_code == 503

def test_server_mounts_the_router_and_the_create_page_uses_it():
    assert '"music_styles"' in (ROOT / "studio" / "server.py").read_text(encoding="utf-8")
    app = (ROOT / "studio" / "web" / "app.js").read_text(encoding="utf-8")
    assert 'import { MusicStyles } from "./music_styles.js"' in app and 'goal === "music" && html`<${MusicStyles}' in app

# ---- a real card through the real JS, the SFW check and the goal
@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_every_card_fills_tags_that_pass_the_check_and_reach_the_graph_value():
    code = 'import { cardTags, applyCard } from "./music_styles_logic.js"; import { readFileSync } from "node:fs"; const d = JSON.parse(readFileSync(process.argv[2], "utf8")); const out = []; for (const f of d.families) for (const s of f.styles) for (const c of s.cards) out.push({ id: c.id, bpm: c.bpm, prompt: applyCard("my own tag, rain", cardTags(s, c)).prompt }); console.log(JSON.stringify(out));'
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(ROOT / "studio" / "web" / "music_styles_logic.js", t); (Path(t) / "x.mjs").write_text(code)
        p = subprocess.run(["node", str(Path(t) / "x.mjs"), str(ROOT / "studio" / "music3_styles.json")], cwd=t, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    rows = json.loads(p.stdout); assert len(rows) == len(CARDS)
    for r in rows:
        assert r["prompt"].endswith("my own tag, rain") and f"{r['bpm']} BPM" in r["prompt"], r["id"]
        assert not sfw.flagged(r["prompt"]), r["id"]
    v, _ = values_for("music", {"prompt": rows[0]["prompt"], "lyrics": "", "seed": 1, "options": {"seconds": 60}})
    assert v["caption"] == rows[0]["prompt"] and v["prompt"] == rows[0]["prompt"]

def test_the_music_default_guidance_was_not_changed():
    g = json.loads((ROOT / "workflows" / "music3_api.json").read_text(encoding="utf-8"))
    enc = next(n for n in g.values() if n["class_type"] == "MiniMaxMusic3TextEncode")
    assert enc["inputs"]["cfg_scale"] == 1.7 and GOALS["music"]["template"] == "music3_api.json"

# ---- the two guides say what is true
GUIDES = [ROOT / "studio" / "processes" / n for n in ("music-engines.md", "music-video.md")]

@pytest.mark.parametrize("guide", GUIDES, ids=lambda p: p.stem)
def test_every_file_a_guide_names_exists(guide):
    text = guide.read_text(encoding="utf-8")
    for link in re.findall(r"\]\(([^)#]+\.md)", text): assert (guide.parent / link).exists(), link
    named = [t.split()[0] for t in re.findall(r"`([^`\n]+)`", text) if re.search(r"\.(py|js|mjs|json|md|sh)\b", t) and not t.startswith(("[", "<"))]
    assert named, "the guide should name its files"
    for n in named: assert (ROOT / n).exists(), n

@pytest.mark.parametrize("guide", GUIDES, ids=lambda p: p.stem)
def test_guides_do_not_point_at_the_earlier_tree(guide):
    text = guide.read_text(encoding="utf-8")
    for bad in ("config/", "tools/build", "comfy" + "_copilot", "scripts/chatbox", "tests/studio/", "tests/chatbox", "../research", "studio/music3_caption", "Composer.js", "COMFY_MUSIC3", "COMFY_STUDIO_MUSIC", "scrub.publish", "realism-4k", "design-picks-everywhere", "wan22-deliverables", "moe_"): assert bad not in text, bad

def test_guide_counts_match_the_data():
    t = GUIDES[1].read_text(encoding="utf-8"); c = DATA["counts"]; o, s = c["official"], c["studio_authored"]
    assert f"{c['families']} families, {c['styles']} styles, {c['cards']:,} cards" in t and f"{c['families'] - 1} families, {o['styles']} styles and {o['cards']} cards" in t and f"{s['styles']} styles and {s['cards']} cards" in t

def test_guide_says_what_the_live_default_is_and_that_nothing_was_rendered():
    e, v = (p.read_text(encoding="utf-8") for p in GUIDES)
    assert "AR `cfg_scale` 1.7" in e and "No song has been rendered" in e and "No song has been rendered" in v.replace("**", "") and "studio-authored, untested" in v
