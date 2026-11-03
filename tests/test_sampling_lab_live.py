"""The Sampling Lab lists what runs here honestly: every sampler and scheduler name ComfyUI offered, the pack and licence for each,
an atlas entry behind each link, pack renders that really used the pack, and data the read-only demo saves."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "studio" / "sampling_lab"
WEB = ROOT / "studio" / "web"
LIVE = json.loads((DATA / "live.json").read_text())
ATLAS = json.loads((DATA / "atlas.json").read_text())
RENDERS = json.loads((DATA / "renders.json").read_text())
IDS = {e["id"]: e for e in ATLAS["entries"]}
BOX = re.compile(r"/(?:m" + r"nt|ho" + r"me|tmp)/[\w./-]*|~/[\w./-]+")


def test_every_offered_name_has_a_pack_licence_and_entry():
    rows = LIVE["samplers"] + LIVE["schedulers"]
    assert len(LIVE["samplers"]) >= 45 and len(LIVE["schedulers"]) >= 9
    for r in rows:
        assert r["pack"], r["name"]
        assert r["licence"], r["name"]
        if r["entry"]: assert r["entry"] in IDS, r["name"]
    assert len({r["name"] for r in LIVE["samplers"]}) == len(LIVE["samplers"])


def test_core_names_are_credited_to_core():
    import sys
    sys.path.insert(0, str(ROOT / "studio"))
    import sampling_graph as G
    by = {r["name"]: r for r in LIVE["samplers"] + LIVE["schedulers"]}
    for n in G.CORE_SAMPLERS + G.CORE_SCHEDULERS:
        if n in by: assert by[n]["pack"] == "core" and by[n]["licence"] == "GPL-3.0", n


def test_a_gold_mark_means_a_render_of_that_exact_name():
    shots = {r["id"]: r for r in RENDERS["renders"] if r.get("status") == "rendered"}
    for r in LIVE["samplers"]:
        if r["rendered"]: assert shots[r["render"]]["sampler"] == r["name"], r["name"]
    for r in LIVE["schedulers"]:
        if r["rendered"]: assert shots[r["render"]]["scheduler"] == r["name"], r["name"]


def test_guidance_rows_point_at_live_guidance_entries():
    assert LIVE["guidance"]
    for g in LIVE["guidance"]:
        e = IDS[g["entry"]]
        assert e["family"] == "guidance" and (e["in_core"] or e["live"]), g["entry"]


def test_pack_renders_used_the_pack_and_have_pictures():
    rows = [r for r in RENDERS["renders"] if str(r.get("set", "")).startswith("pack-")]
    assert 10 <= sum(1 for r in rows if not r.get("baseline")) <= 15
    for s in {r["set"] for r in rows}:
        assert sum(1 for r in rows if r["set"] == s and r.get("baseline")) == 1, s
        assert RENDERS["bases"][s] in {r["id"] for r in rows if r["set"] == s}
    for r in rows:
        if r["status"] == "rendered": assert (WEB / r["url"]).exists(), r["id"]
        if r.get("baseline"):
            assert r["pack"] == "core" and not r.get("patches")
            continue
        assert r["pack"] != "core", r["id"]
        if r.get("entry"):
            e = IDS[r["entry"]]
            assert not e["in_core"], f"{r['id']}: a pack render must not prove a core entry"
            assert e["rendered"] and r["id"] in e["rendered_ids"], r["id"]
            assert any(p["pack"].split("__")[-1] == r["pack"].split("__")[-1] for p in e["providers"]), r["id"]


def test_every_pack_render_has_a_note_written_after_looking():
    for r in RENDERS["renders"]:
        if str(r.get("set", "")).startswith("pack-") and r["status"] == "rendered": assert r.get("seen"), r["id"]


def test_new_entries_cite_files_and_ship_no_machine_paths():
    added = {i for a in ATLAS.get("additions", []) if a.get("by") == "add_pool51_atlas.py" for i in a["entries"]}
    assert len(added) >= 40
    for i in added:
        e = IDS[i]
        assert e["evidence"] and all(re.match(r".+\.py:\d+$", ev["where"]) for ev in e["evidence"]), i
        assert e["providers"][0]["licence"] is not None and e["label"] == "from code", i
    text = (DATA / "live.json").read_text() + json.dumps([IDS[i] for i in added]) + json.dumps(ATLAS["surprises"])
    assert not BOX.search(text)


def test_live_flags_only_where_a_node_or_name_is_offered():
    offered = {r["name"] for r in LIVE["samplers"] + LIVE["schedulers"]}
    for e in ATLAS["entries"]:
        if e.get("live") and not e.get("in_core"):
            assert any(p.get("nodes") or set(p.get("names") or []) & offered for p in e["providers"] if p["pack"] != "core"), e["id"]


def test_the_api_serves_it_and_the_demo_saves_it():
    src = (ROOT / "studio" / "sampling_lab.py").read_text()
    assert '@router.get("/api/sampling/live")' in src and 'live.json' in src
    assert '"sampling/live"' in (ROOT / "scripts" / "build_pages.py").read_text()
    js = (WEB / "samplinglab.js").read_text()
    assert 'api("/api/sampling/live")' in js and '["live", "Live here"' in js


def test_pack_render_sets_have_names_on_the_bench():
    js = (WEB / "samplinglab_bench.js").read_text()
    for s in ("pack-sampler", "pack-scheduler", "pack-guidance"): assert f'"{s}":' in js


def test_live_logic_runs_without_a_browser(tmp_path):
    probe = tmp_path / "probe.mjs"
    probe.write_text(f"""import * as L from {json.dumps(str(WEB / 'samplinglab_logic.js'))};
const rows = [{{name: "euler", pack: "core", entry: "core-euler", rendered: true}}, {{name: "hfe_s1", pack: "WASasquatch__RES4SHO", entry: "res4sho-hfe"}}, {{name: "hfe_s2", pack: "WASasquatch__RES4SHO", entry: null}}, {{name: "Distance", pack: "Extraltodeus__DistanceSampler", entry: "x"}}];
const g = L.liveGroups(rows), f = L.liveGroups(rows, "dist");
console.log(JSON.stringify({{order: g.map((x) => x.pack), sizes: g.map((x) => x.rows.length), f: f.map((x) => x.pack), c: L.liveCounts(rows), view: L.parseRoute("sampling/live").view, run: L.runsHere({{live: true, rendered: true}}).word}}));""")
    out = json.loads(subprocess.run(["node", str(probe)], capture_output=True, text=True, check=True).stdout)
    assert out == {"order": ["core", "WASasquatch__RES4SHO", "Extraltodeus__DistanceSampler"], "sizes": [1, 2, 1], "f": ["Extraltodeus__DistanceSampler"],
                   "c": {"all": 4, "core": 1, "packs": 3, "explained": 3, "rendered": 1}, "view": "live", "run": "Installed, and rendered"}
