"""ComfyUniversity page: browser maths match ComfyUI's own numbers, the browser validator matches execution.py, every graph validated, every embed real, every count computed, nothing private."""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from studio.university import build as B
from psn import paths
WEB = ROOT / "studio" / "web"; FIX = ROOT / "tests" / "fixtures"; SRC = Path(paths.setting("COMFYUI_SRC", default=paths.home("ComfyUI")))
node = pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
hascomfy = pytest.mark.skipif(not (SRC / "execution.py").exists(), reason="no ComfyUI checkout here")
FILES = [f"university{x}.js" for x in ("", "_logic", "_maths", "_parts", "_plays", "_play_data")] + ["university.css"]

def run_js(body):
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        for f in FILES: (d / f).write_bytes((WEB / f).read_bytes())
        (d / "x.mjs").write_text(body); p = subprocess.run(["node", str(d / "x.mjs")], cwd=d, capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-800:]
    return json.loads(p.stdout)

# ---------- the ports hold to ComfyUI
@node
def test_schedulers_match_comfyui_to_float_precision():
    r = json.loads((FIX / "university_refs.json").read_text())
    out = run_js('import * as M from "./university_maths.js"; const d=M.discreteModel(),f=M.flowModel(3); const R=%s; const o={}; for(const k of R){const [mn,sc,n]=k.split("/"); o[k]=M.schedule(sc,mn==="discrete"?d:f,+n);} console.log(JSON.stringify(o));' % json.dumps(list(r["schedules"])))
    for k, want in r["schedules"].items():
        got = out[k]; assert len(got) == len(want), k
        for a, b in zip(got, want): assert abs(a - b) <= 2e-5 * (abs(b) + 1e-2), (k, a, b)

@node
def test_denoise_percent_solvers_and_weights_match_comfyui():
    r = json.loads((FIX / "university_refs.json").read_text())
    out = run_js('''import * as M from "./university_maths.js"; const R=%s; const d=M.discreteModel(),f=M.flowModel(3); const o={denoise:{},percent:{},solvers:{},weights:{},anc:[]};
    for(const k in R.denoise){const [s,st,dn]=k.split("/"); const w=M.denoiseWindow(s,d,+st,+dn); o.denoise[k]={built:w.built,sigmas:w.sigmas};}
    for(const k in R.percent){const [mn,p]=k.split("/"); o.percent[k]=(mn==="discrete"?d:f).percent(+p);}
    for(const n in R.solvers){const s=M.solve(n,[3,-4],R.sigmas_solver,(a,b,t)=>M.denoiser(a,b,t)); o.solvers[n]=[s.x,s.y];}
    for(const t in R.weights) o.weights[t]=M.tokenWeights(t); for(const a of R.ancestral) o.anc.push(M.ancestralStep(a[0],a[1])); console.log(JSON.stringify(o));''' % json.dumps(r))
    for k, w in r["denoise"].items():
        assert out["denoise"][k]["built"] == w["built"]; assert all(abs(a - b) < 1e-5 for a, b in zip(out["denoise"][k]["sigmas"], w["sigmas"]))
    for k, w in r["percent"].items(): assert abs(out["percent"][k] - w) < 1e-5, k
    for k, w in r["solvers"].items(): assert all(abs(a - b) < 1e-9 for a, b in zip(out["solvers"][k], w)), k
    assert {k: [[a, round(b, 6)] for a, b in v] for k, v in out["weights"].items()} == {k: [[a, round(b, 6)] for a, b in v] for k, v in r["weights"].items()}
    for a, w in zip(out["anc"], r["ancestral"]): assert abs(a[0] - w[2]) < 1e-9 and abs(a[1] - w[3]) < 1e-9

@hascomfy
def test_latent_table_and_frame_rules_match_the_source():
    """The numbers the shape labs use, compared with the zeros() call or rule of each node's source."""
    t = (WEB / "university_maths.js").read_text(); rows = re.findall(r'(\w+): \{ label: "[^"]+", node: "(\w+)", ch: (\d+), sf: (\d+)(?:, tf: (\d+))?, source: "([^"]+)"', t); assert len(rows) >= 5
    for key, nd, ch, sf, tf, src in rows:
        text = (SRC / src).read_text(); i = text.index(("class " + nd)); body = text[i:i + 4000]; assert f"height // {sf}" in body and f"width // {sf}" in body, key
        if tf: assert f"(length - 1) // {tf}" in body, key
        assert re.search(rf"\[(?:batch_size|1), {ch}\b", body) or (key == "sd15" and "4, height" in body), key
    h3 = (SRC / "comfy_extras" / "nodes_minimax_h3.py").read_text(); assert "n % 17 != 5" in h3 and "24, latent_t, height // 16, width // 16" in h3
    mm = (SRC / "comfy" / "model_management.py").read_text(); assert "EXTRA_RESERVED_VRAM = 400 * 1024 * 1024" in mm

@hascomfy
def test_node_template_shape_exists_in_this_comfyui():
    io = (SRC / "comfy_api" / "latest" / "_io.py").read_text()
    for w in ("def fingerprint_inputs", "def define_schema", "class Schema", "def validate_inputs"): assert w in io, w
    assert "class ComfyExtension" in (SRC / "comfy_api" / "latest" / "__init__.py").read_text()
    assert "IS_CHANGED" in (SRC / "nodes.py").read_text()

@node
def test_browser_validator_agrees_with_comfyui_on_broken_graphs():
    real = json.loads((FIX / "university_broken_real.json").read_text()); data = json.loads((FIX / "university_broken.json").read_text()); assert len(real) == len(data) >= 6
    out = run_js('''import { validateGraph } from "./university_logic.js"; import { WIRE_LAB, BROKEN } from "./university_play_data.js"; console.log(JSON.stringify(BROKEN.map((b)=>({name:b.name,types:[...new Set(validateGraph(b.graph,WIRE_LAB).map((e)=>e.type))].sort()}))));''')
    for o, r in zip(out, real):
        assert o["name"] == r["name"]; want = sorted(set(r["types"]) | ({r["top"]} if r["top"] and not r["types"] else set())); want = [w for w in want if w != "prompt_outputs_failed_validation"]
        assert o["types"] == want, (o, r)

@node
def test_browser_validator_passes_the_good_graph_and_the_wire_lab_is_copied_from_node_defs():
    out = run_js('''import { validateGraph } from "./university_logic.js"; import { WIRE_LAB, DEFAULT_GRAPH } from "./university_play_data.js"; console.log(JSON.stringify({e:validateGraph(DEFAULT_GRAPH,WIRE_LAB),defs:WIRE_LAB}));''')
    assert out["e"] == []; defs = json.loads((B.HERE / "node_defs.json").read_text())
    big = lambda d: json.loads(json.dumps(d), parse_int=lambda x: float(x))
    for k, v in out["defs"].items(): assert big(v) == big(defs[k]), k

@node
def test_page_logic():
    out = run_js('''import * as L from "./university_logic.js"; import { DEFAULT_GRAPH as G, WIRE_LAB as W } from "./university_play_data.js";
    const mem=new Map(); const store={getItem:(k)=>mem.get(k)||null,setItem:(k,v)=>mem.set(k,v)}; let p=L.loadProgress(store); p=L.markLesson(p,"CU-100",{read:true}); p=L.markLesson(p,"CU-100",{plays:{wire:true}}); L.saveProgress(p,store);
    const broken={getItem(){throw new Error("denied")},setItem(){throw new Error("denied")}}; const c={plays:["wire"]};
    const doc=L.parseLesson("# CU-100 - Title\\n\\n> Draft. Not checked.\\n\\n**Objective.** Do it. Taught by X.\\n\\nLead.\\n\\n## One two\\n\\nSome **bold** <b>x</b> and CU-101.\\n\\n{{play:wire}}\\n\\n{{graph:nm_first}}\\n\\n{{wipe:a.jpg|b.jpg|A|B|cap}}\\n\\n![pic](x.jpg)\\n\\n```text\\nhi\\n```\\n\\n| a | b |\\n|---|---|\\n| 1 | 2 |\\n\\n## Sources\\n\\n- [x](https://a.example)\\n");
    console.log(JSON.stringify({saved:L.loadProgress(store),again:L.lessonParts(c,L.loadProgress(store)["CU-100"]),safe:L.loadProgress(broken),wrote:L.saveProgress({},broken),doc,route:[L.parseRoute("university"),L.parseRoute("university/track/video"),L.parseRoute("university/CU-101"),L.parseRoute("university/all"),L.parseRoute("university/x")],dirty:[...L.dirtyFrom(G,"3")].sort(),reach:[...L.reachable(G,W)].length,dead:[...L.reachable({...G,"99":{class_type:"VAEDecode",inputs:{samples:["3",0],vae:["4",2]}}},W)].includes("99"),order:L.layoutGraph(G,W).order.length,mins:L.readingMinutes(new Array(450).join("word ")),nb:L.neighbours("b",{codes:["a","b","c"]}),esc:L.inline("<script> `<x>` [a](javascript:alert(1)) [b](#university) [c](https://e.example)")}));''')
    assert out["saved"]["CU-100"] == {"read": True, "plays": {"wire": True}} and out["safe"] == {} and out["wrote"] is False
    assert out["again"]["parts"] == [["read", True], ["quiz", False], ["play", True]] and not out["again"]["done"]
    d = out["doc"]; assert d["code"] == "CU-100" and d["title"] == "Title" and d["draft"].startswith("Draft") and d["objective"].startswith("Do it") and [s["id"] for s in d["sections"]] == ["one-two", "sources"]
    assert [b["t"] for b in d["sections"][0]["blocks"]] == ["p", "play", "graph", "wipe", "img", "code", "table"]; h = d["sections"][0]["blocks"][0]["html"]; assert "<strong>bold</strong>" in h and "<b>" not in h and 'href="#university/CU-101"' in h
    assert [r["view"] for r in out["route"]] == ["home", "track", "lesson", "all", "home"] and out["dirty"] == ["3", "8", "9"] and out["reach"] == 7 and out["dead"] is False and out["order"] == 7 and out["mins"] == 2 and out["nb"]["prev"] == "a" and out["nb"]["next"] == "c"
    assert "<script>" not in out["esc"] and "&lt;x&gt;" in out["esc"] and "javascript:" not in out["esc"].replace("[a](javascript:alert(1))", "") and 'href="#university"' in out["esc"] and 'href="https://e.example"' in out["esc"]

# ---------- graphs
def graph_files(): return [p for p in B.GRAPHS.glob("*.json") if p.name != "verified.json"]
def test_every_graph_is_well_formed_and_validated_by_comfyui():
    ver = B.VERIFIED(); defs = B.DEFS(); assert len(graph_files()) >= 30
    for p in graph_files():
        d = json.loads(p.read_text()); m, g = d["meta"], d["graph"]; assert m["title"] and m["runs"] in ("cpu", "model") and isinstance(m["needs"], list) and isinstance(m["packs"], list), p.name
        row = ver.get(p.stem); assert row, p.name + " was never verified: run scripts/verify_university_graphs.py"; assert row["sha"] == B.graph_sha(g), p.name + " changed since it was verified"
        assert row["validate"] == "ok" or (m["packs"] and row["validate"] == "needs a pack"), (p.name, row)
        if m["runs"] == "cpu": assert row.get("ran") is True, p.name
        else: assert m["needs"] or m["packs"], p.name + " needs models but does not say which"
        for n, x in g.items():
            assert x["class_type"] in defs or m["packs"], (p.name, x["class_type"])
            for k, v in x["inputs"].items(): assert not (isinstance(v, str) and "${" in v), (p.name, n, k)
        assert set(m.get("notes", {})) <= set(g), p.name

def test_graph_files_carry_no_private_text():
    for p in graph_files():
        t = p.read_text(); assert not re.search(r"/mnt/|/home/|127\.0\.0\.1", t), p.name

def test_api_sends_graphs_with_only_their_own_definitions(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.delenv("STUDIO_UNIVERSITY", raising=False); import studio.server as s
    c = TestClient(s.app); cat = c.get("/api/university").json(); row = next(x for x in cat["courses"] if x["graphs"]); d = c.get("/api/university/" + row["code"]).json(); g = d["graphs"][0]
    assert g["id"] in row["graphs"] and g["graph"] and set(g["defs"]) == {n["class_type"] for n in g["graph"].values()} and g["verified"]["validate"] == "ok"
    assert B.load_graph("../secrets") is None and B.load_graph("nope") is None

# ---------- running a lab from the page
def test_run_lab_route_runs_the_stored_file_only(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.delenv("STUDIO_UNIVERSITY", raising=False); import studio.server as s
    seen = []
    def fake(path, *a, **k): seen.append(Path(path).name); return True, "ok\n", .1, ""
    monkeypatch.setattr(B, "run_lab", fake); c = TestClient(s.app); code = c.get("/api/university").json()["courses"][0]["code"]
    r = c.post(f"/api/university/{code}/run-lab", json={"code": "import os"}).json(); assert r["ok"] and seen == ["lab.py"] and r["output"] == "ok\n" and r["same"] is False
    assert c.post("/api/university/CU-999/run-lab").status_code == 404 and c.post("/api/university/nope/run-lab").status_code == 400
    assert s._LAB_LOCK.acquire(blocking=False)
    try: assert c.post(f"/api/university/{code}/run-lab").status_code == 409
    finally: s._LAB_LOCK.release()

# ---------- catalogue and embeds
def test_tracks_are_ordered_complete_and_counts_are_computed():
    cat = json.loads((B.HERE / "catalogue.json").read_text()); rows = cat["courses"]; listed = [c for t in cat["tracks"] for c in t["codes"]]
    assert sorted(listed) == sorted(r["code"] for r in rows), "every lesson belongs to exactly one track"
    n = cat["counts"]; assert n["lessons"] == len(rows) and n["audited"] + n["draft"] == len(rows) and n["graphs"] == len(graph_files()) and n["plays"] == len({p for r in rows for p in r["plays"]})
    assert n["graphs_ran"] == sum(1 for v in B.VERIFIED().values() if v.get("ran"))
    for t in cat["tracks"]: assert (WEB / t["art"]).exists(), t["slug"]
    for a in cat["art"]: assert (WEB / a).exists(), a

def test_page_types_no_counts():
    t = (WEB / "university.js").read_text(); assert not re.search(r"\b\d{2,} (lessons|tracks|graphs|labs)\b", t)

def test_every_embed_in_every_lesson_is_real():
    rows = B.courses(); assert not {c["code"]: p for c in rows for p in [B.check_embeds(c, (c["dir"] / "lesson.md").read_text())] if p}

def test_every_play_has_a_task_and_is_used_by_a_lesson_or_reported():
    t = (WEB / "university_plays.js").read_text(); names = B.play_names(); assert len(names) >= 20
    assert len(re.findall(r"^  [a-z0-9_]+: \{ title: \"[^\"]+\", task: \"[^\"]+\"", t, re.M)) == len(names)

def test_finished_lessons_have_the_full_kit():
    rows = [c for c in B.courses() if c.get("kit")]; assert len(rows) >= 2
    assert not {c["code"]: g for c in rows for g in [B.kit_gaps(c)] if g}

def test_drafts_are_labelled_on_the_page():
    for c in B.courses():
        if c.get("status") == "draft": assert (c["dir"] / "lesson.md").read_text().split("\n")[2].startswith("> Draft."), c["code"]

def test_verified_claims_name_how_and_refs_exist():
    for c in B.courses():
        for v in c.get("verified", []):
            assert v.get("claim") and v.get("how") in ("source", "run here", "docs", "test"), (c["code"], v)
            if v["how"] == "source" and (SRC / "execution.py").exists() and v.get("ref"): assert B.symbol_exists(SRC, v["ref"]), (c["code"], v["ref"])

# ---------- rules
def test_page_files_stay_local_and_clean():
    for f in FILES:
        t = (WEB / f).read_text(); assert not re.search(r"https?://|//cdn\.|@import", t), f; assert "\u2014" not in t, f
    assert 'href="university.css"' in (WEB / "index.html").read_text() and 'import { University } from "./university.js"' in (WEB / "app.js").read_text()

def test_progress_storage_is_guarded():
    t = (WEB / "university_logic.js").read_text(); assert re.search(r"function loadProgress.*try \{", t) and re.search(r"function saveProgress.*try \{", t)
    assert "localStorage" not in (WEB / "university.js").read_text() and "localStorage" not in (WEB / "university_plays.js").read_text()

def test_lessons_name_no_pack_on_the_do_not_install_list():
    f = Path(paths.setting("PACK_PICKS_DIR", default=str(Path(SRC).parent / "worker" / "PACK_PICKS_2026-11-01"))) / "DO_NOT_INSTALL.md"
    if not f.exists(): pytest.skip("the private list is not on this machine")
    bad = set(re.findall(r"`([\w.-]+__[\w.-]+)`", f.read_text())); names = {b.split("__", 1)[1].lower() for b in bad if len(b.split("__", 1)[1]) > 8}
    for c in B.courses():
        t = (c["dir"] / "lesson.md").read_text().lower(); hits = [n for n in names if n in t]; assert not hits, (c["code"], hits)
