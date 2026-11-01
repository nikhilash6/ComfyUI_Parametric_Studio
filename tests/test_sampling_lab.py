"""The Sampling Lab: its data is honest and its routes only ever build core graphs. ComfyUI is stubbed: no GPU, no real queue."""
import json, os, re
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import studio.server as S
from studio import sampling_graph as G, sampling_lab as L

ROOT = Path(__file__).parent.parent; WEB = ROOT / "studio" / "web"; DATA = ROOT / "studio" / "sampling_lab"
atlas = json.loads((DATA / "atlas.json").read_text()); renders = json.loads((DATA / "renders.json").read_text()); measures = json.loads((DATA / "measures.json").read_text())
LABELS = {"from code", "from pack README claim", "measured here", "inference"}

@pytest.fixture
def client(monkeypatch):
    calls = []
    def comfy(path, payload=None, timeout=30, raw=False):
        calls.append((path, payload))
        if path.startswith("/object_info"): return {"CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [["v1-5-pruned-emaonly.safetensors", "sd_xl_base_1.0.safetensors"]]}}}}
        if path == "/prompt": return {"prompt_id": "job1"}
        return {}
    monkeypatch.setattr(S, "comfy", comfy); monkeypatch.setattr(S, "comfy_up", lambda: True); monkeypatch.setattr(L, "_srv", lambda: S); S.JOBS.pop("job1", None)
    c = TestClient(S.app); c.calls = calls; return c

def test_wired_in():
    app = (WEB / "app.js").read_text()
    assert 'import { SamplingLab } from "./samplinglab.js"' in app and '["sampling", "Sampling"]' in app and "sampling: [" in app and "<${SamplingLab} route=${tab}/>" in app
    assert 'href="samplinglab.css"' in (WEB / "index.html").read_text()

def test_page_loads_nothing_from_outside():
    for f in ("samplinglab.js", "samplinglab.css", "samplinglab_logic.js"): assert not re.search(r"https?://|//cdn\.|@import", (WEB / f).read_text())

def test_atlas_has_every_core_sampler_and_scheduler():
    names = set()
    for e in atlas["entries"]:
        r = e.get("core_ref") or {}
        if e["in_core"]: names.update([r.get("sampler_name")] + list(r.get("sampler_names") or []))
    assert set(G.CORE_SAMPLERS) <= names, set(G.CORE_SAMPLERS) - names
    sch = {(e.get("core_ref") or {}).get("scheduler") for e in atlas["entries"] if e["in_core"]}
    assert set(G.CORE_SCHEDULERS) <= sch, set(G.CORE_SCHEDULERS) - sch

def test_core_lists_match_core_source():
    src = Path(os.environ.get("COMFYUI_DIR", "/nonexistent")) / "comfy/samplers.py"
    if not src.exists(): pytest.skip("no ComfyUI on this machine")
    t = src.read_text(); listed = re.findall(r'"(\w+)"', re.search(r"KSAMPLER_NAMES = \[(.*?)\]", t, re.S).group(1))
    assert set(listed) | {"ddim", "uni_pc", "uni_pc_bh2"} == set(G.CORE_SAMPLERS)
    assert set(re.findall(r'^\s+"(\w+)": SchedulerHandler', t, re.M)) == set(G.CORE_SCHEDULERS)

def test_every_entry_has_plain_math_evidence_label_and_credit():
    assert len(atlas["entries"]) > 100; ids = [e["id"] for e in atlas["entries"]]; assert len(ids) == len(set(ids))
    for e in atlas["entries"]:
        assert e["plain"].strip() and e["math"].strip() and e["evidence"], e["id"]
        assert e["label"] in LABELS, (e["id"], e["label"])
        assert all(re.search(r":\d+$", x["where"]) for x in e["evidence"]), e["id"]
        assert e["providers"] or e["in_core"], e["id"]
        for c in e["claims"]: assert c.get("label") in LABELS, e["id"]
        for f in e["family_fit"]: assert f.get("label") in LABELS, e["id"]

def test_no_box_paths_or_pasted_code_ship():
    t = (DATA / "atlas.json").read_text() + (DATA / "renders.json").read_text()
    assert not re.search(r"/mnt/|/home/|/tmp/claude", t)
    for e in atlas["entries"]: assert not re.search(r"^\s*(def |class \w+\(|import \w+|from \w+ import )", e["math"], re.M), e["id"]

def test_res4lyf_is_short_and_points_at_its_page():
    rows = [e for e in atlas["entries"] if any("RES4LYF" in p["pack"] for p in e["providers"])]
    assert all(len(e["math"]) < 1500 for e in rows if not e["in_core"]), "RES4LYF entries stay short"
    assert any(p.get("res4lyf") for e in rows for p in e["providers"]) if rows else True
    assert "res4lyf" in (WEB / "samplinglab.js").read_text()

def test_no_pack_files_copied_in():
    assert not list((ROOT / "studio" / "sampling_lab").glob("*.py")) and not list((ROOT / "studio" / "web" / "sampling_lab").glob("*.py"))
    src = (ROOT / "scripts" / "build_sampling_lab.py").read_text(); assert "import_module" not in src and not re.search(r"\b(exec|eval)\(", src)

def test_every_render_file_is_there_and_all_core():
    done = [r for r in renders["renders"] if r["status"] == "rendered"]; assert 35 <= len(done) <= 60
    core = set(G.CORE_PATCHES) | {"PerpNegGuider"}
    for r in done:
        assert (ROOT / "studio/web" / r["url"]).exists(), r["id"]
        assert r["sampler"] in G.CORE_SAMPLERS and r["scheduler"] in G.CORE_SCHEDULERS and all(p[0] in core for p in r["patches"]), r["id"]
    assert renders["pack_lab"]["rendered"] == 0, "the page must not imply a pack proof that failed"

def test_ddim_really_matched_euler_here():
    by = {r["id"]: r for r in renders["renders"]}; assert by["sampler-ddim"]["sha256"] == by["sampler-euler"]["sha256"] and "sampler-euler" in by["sampler-ddim"]["identical_to"]

def test_measures_come_from_real_runs():
    s = measures["solvers"]; assert set(G.CORE_SAMPLERS) <= set(s)
    assert s["euler"]["eps"]["calls"]["20"] == 20 and s["heun"]["eps"]["calls"]["20"] == 39 and s["euler"]["eps"]["same_answer_with_other_noise_seed"] is True and s["euler_ancestral"]["eps"]["same_answer_with_other_noise_seed"] is False
    k = measures["schedules"]["sd_eps"]["by_steps"]["20"]["karras"]; assert len(k) == 21 and k[-1] == 0 and all(a >= b for a, b in zip(k, k[1:]))

def test_routes(client):
    assert client.get("/api/sampling/summary").json()["entries"] == len(atlas["entries"])
    d = client.get("/api/sampling/atlas").json(); assert "math" not in d["entries"][0] and len(d["entries"]) == len(atlas["entries"])
    eid = d["entries"][0]["id"]; assert client.get(f"/api/sampling/entry/{eid}").json()["math"]
    assert client.get("/api/sampling/entry/not-a-thing").status_code == 404
    assert client.get("/api/sampling/measures").json()["label"] == "measured here" and client.get("/api/sampling/renders").json()["seed"] == G.SEED

def test_graph_is_core_only(client):
    g = client.get("/api/sampling/graph?model=sd15&sampler=heun&scheduler=beta&patch=RescaleCFG&cfg=9").json()["graph"]
    kinds = {n["class_type"] for n in g.values()}; assert {"KSamplerSelect", "BasicScheduler", "RescaleCFG", "SamplerCustomAdvanced"} <= kinds
    assert g["9"]["inputs"]["sampler_name"] == "heun" and g["10"]["inputs"]["scheduler"] == "beta" and g["8"]["inputs"]["cfg"] == 9
    assert g["20"]["inputs"]["model"] == ["1", 0] and g["8"]["inputs"]["model"] == ["20", 0] and g["10"]["inputs"]["model"] == ["20", 0]

@pytest.mark.parametrize("q", ["sampler=res_2m", "scheduler=beta57", "model=flux", "patch=Evil", "cfg=99", "steps=500", "cfg=abc", "patch=SkipLayerGuidanceSD3&model=sdxl"])
def test_refuses_what_is_not_core(client, q):
    assert client.get("/api/sampling/graph?" + q).status_code == 400

def test_run_queues_and_records(client):
    r = client.post("/api/sampling/run", json={"model": "sd15", "sampler": "euler"}); assert r.status_code == 200 and r.json()["job"] == "job1"
    assert S.JOBS["job1"]["goal"] == "sampling_lab"; assert any(p == "/prompt" for p, _ in client.calls)

def test_run_will_not_swap_a_missing_model(client):
    r = client.post("/api/sampling/run", json={"model": "sd35"}); assert r.status_code == 400 and "not installed" in r.json()["detail"]
    assert not any(p == "/prompt" for p, _ in client.calls)

def test_run_keeps_the_sfw_rule(client):
    r = client.post("/api/sampling/run", json={"model": "sd15", "prompt": "nude figure"}); assert r.status_code == 400; assert not any(p == "/prompt" for p, _ in client.calls)

def test_run_when_comfy_is_down(client, monkeypatch):
    monkeypatch.setattr(S, "comfy_up", lambda: False); assert client.post("/api/sampling/run", json={"model": "sd15"}).status_code == 503

def test_run_needs_json(client):
    assert client.post("/api/sampling/run", content=b"not json").status_code == 400 and client.post("/api/sampling/run", json=[1]).status_code == 400

def test_empty_data_does_not_break_routes(tmp_path, monkeypatch, client):
    monkeypatch.setattr(L, "DATA", tmp_path); L._cache.clear()
    assert client.get("/api/sampling/summary").json()["entries"] == 0 and client.get("/api/sampling/renders").json()["renders"] == []
    L._cache.clear()

def test_second_reader_results_are_kept_honest():
    audited = [e for e in atlas["entries"] if e["audit"]]; assert audited
    assert atlas["coverage"]["second_reader_total"] == len(audited)
    for e in audited: assert e["audit"]["verdict"] in ("correct", "minor", "wrong", "couldnt_verify"), e["id"]
    for e in audited:
        if e["audit"]["verdict"] == "wrong": assert e["audit"]["fixed"], f"{e['id']} was found wrong and has no correction"

def test_new_page_files_stay_local_and_wired():
    for f in ("samplinglab_kit.js", "samplinglab_bench.js", "samplinglab_method.js"): assert not re.search(r"https?://|//cdn\.|@import", (WEB / f).read_text())
    css = (WEB / "samplinglab.css").read_text()
    for font in re.findall(r"url\((vendor/fonts/[^)]+)\)", css): assert (WEB / font).stat().st_size < 40000, font
    assert (WEB / "vendor/fonts/LICENSE-STIX-OFL.txt").exists() and "STIX" in (ROOT / "THIRD_PARTY_NOTICES.md").read_text()

def test_no_em_dashes_in_the_page():
    for f in ("samplinglab.js", "samplinglab_kit.js", "samplinglab_bench.js", "samplinglab_method.js", "samplinglab_logic.js", "samplinglab.css"): assert "\u2014" not in (WEB / f).read_text(), f

def test_only_core_methods_claim_a_render():
    assert not [e["id"] for e in atlas["entries"] if e["rendered"] and not e["in_core"]]
    assert renders["pack_lab"]["rendered"] == 0, "the page says no pack method is proven; change the copy if that ever changes"

def test_surprise_figures_match_the_measures():
    by = {r["id"]: r for r in renders["renders"]}; s = measures["schedules"]
    assert by["sampler-ddim"]["sha256"] == by["sampler-euler"]["sha256"] and by["sampler-ddim"]["diff_to_base"] == 0
    assert by["guidance-cfgnorm-14"]["contrast"] < by["guidance-cfg-14"]["contrast"] / 2
    q = [x for x in s["sd_eps"]["by_steps"]["20"]["linear_quadratic"] if x > 0][-1]; k = [x for x in s["sd_eps"]["by_steps"]["20"]["karras"] if x > 0][-1]
    assert q > 2 and k < .05

def test_author_gaps_are_real_gaps():
    owners = json.loads((DATA / "pack_owners.json").read_text())["owners"]
    for c in atlas["credits"]:
        if c["pack"] in owners: assert c["author"] == owners[c["pack"]]
    assert all(p.get("author") == owners[p["pack"]] for e in atlas["entries"] for p in e["providers"] if p["pack"] in owners)

def test_list_route_carries_author_and_render_ids(client):
    rows = client.get("/api/sampling/atlas").json()["entries"]
    assert all("by" in r and "rendered_ids" in r for r in rows); assert next(r for r in rows if r["id"] == "core-euler")["rendered_ids"]
    assert "math" not in rows[0], "the list stays light"
