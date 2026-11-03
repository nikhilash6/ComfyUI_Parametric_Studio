"""Swap on any model, and the README's bonus-track section: every row and every claim points at a graph and a render that are really in the repo. No live ports, no GPU."""
import importlib.util, json, re
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "studio" / "swap_showcase.json"; WEB = REPO / "studio" / "web"
README = (REPO / "README.md").read_text(encoding="utf-8")


def _rows(): return json.loads(DATA.read_text(encoding="utf-8"))["rows"]


def _table_module():
    spec = importlib.util.spec_from_file_location("build_swap_table", REPO / "scripts" / "build_swap_table.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_every_rendered_row_has_its_graph_its_render_and_the_record_that_ties_them():
    rendered = [r for r in _rows() if r["status"] == "rendered"]
    assert len(rendered) >= 7
    for r in rendered:
        g = json.loads((REPO / r["graph"]).read_text(encoding="utf-8"))
        assert isinstance(g, dict) and all("class_type" in n for n in g.values() if isinstance(n, dict)), r["id"]      # ComfyUI API format
        p = r["proof"]
        for k in ("src", "poster"): assert (WEB / p[k]).is_file(), (r["id"], p[k])
        rec = (REPO / p["record"]).read_text(encoding="utf-8")
        assert p["key"].split(".")[-1] in rec and p["src"].split("/")[-1].split(".")[0] in rec, (r["id"], "the record does not name this render")
        assert r["output"] in ("video", "still") and r["licence"] and r["looked"] and r["flaw"] and r["open"]["hash"], r["id"]
        assert p["peak_vram_gib"] > 0 and p["seconds"] > 0, r["id"]


def test_coming_rows_show_no_picture_and_claim_no_proof():
    for r in _rows():
        if r["status"] != "rendered": assert r["status"] == "coming" and "proof" not in r and "looked" not in r, r["id"]


def test_recast_row_is_the_h3_graph_with_the_swap_lora():
    r = next(x for x in _rows() if x["id"] == "h3_recast")
    g = (REPO / r["graph"]).read_text(encoding="utf-8")
    assert "minimax_h3_ref2va" in g and "h3_character_swap" in g


def test_readme_swap_table_is_written_from_the_same_file():
    m = _table_module()
    block = README.split(m.START, 1)[1].split(m.END, 1)[0].strip()
    assert block == m.table().strip(), "README swap table is stale: run scripts/build_swap_table.py"
    for r in _rows():
        if r["status"] == "rendered": assert f"]({r['graph']})" in block, r["id"]
        else: assert r["graph"] not in block, f"{r['id']} is coming and must not be linked as done"


def test_every_link_and_picture_in_the_bonus_and_swap_sections_is_in_the_repo():
    sect = README.split("## Bonus tracks: what's built for each", 1)[1].split("\n## Install", 1)[0]
    targets = re.findall(r'(?:href|src)="([^"]+)"', sect) + re.findall(r"\]\(([^)\s]+)\)", sect)
    local = [t for t in targets if not t.startswith(("http", "#"))]
    assert len(local) > 40
    for t in local: assert (REPO / t).exists(), t


def test_bonus_section_claims_only_the_two_categories_entered():
    sect = README.split("## Bonus tracks: what's built for each", 1)[1].split("\n## Swap the person", 1)[0]
    assert "submitted under Open Weights Only and VFX Workflow Built with LTX" in sect
    assert "### VFX Workflow Built with LTX (entered)" in sect and "### Built with FLUX (shown, not entered)" in sect and "### Built with MiniMax H3 (shown, not entered)" in sect
    assert not re.search(r"\b(winner|wins|eligible for the|qualif)", sect.replace("Each entry is eligible for both", ""), re.I)
    assert "excludes the US, EU, UK and South Korea" in sect


def test_flux_track_lists_only_flux3_graphs():
    sect = README.split("### Built with FLUX", 1)[1].split("**Other FLUX models", 1)[0]
    for g in re.findall(r'href="([^"]+\.json)"', sect) + re.findall(r"\]\(([^)]+\.json)\)", sect):
        if "proof" in g or "showcase.json" in g or "family_status" in g: continue
        assert "flux3" in (REPO / g).read_text(encoding="utf-8").replace("-", "_"), g


def test_ltx_track_graphs_run_ltx_25():
    sect = README.split("### VFX Workflow Built with LTX", 1)[1].split("### Built with FLUX", 1)[0]
    graphs = [g for g in re.findall(r'href="(workflows/[^"]+\.json)"', sect)]
    assert len(graphs) >= 5
    for g in graphs: assert "ltx-2.5-22b" in (REPO / g).read_text(encoding="utf-8"), g


def test_the_page_serves_the_rows_and_each_graph(monkeypatch, tmp_path):
    from studio import feature_swap
    app = FastAPI(); app.include_router(feature_swap.router); c = TestClient(app)
    d = c.get("/api/swap").json(); ids = [r["id"] for r in d["rows"] if r["status"] == "rendered"]
    assert "h3_recast" in ids and all(r["graph_here"] for r in d["rows"] if r["status"] == "rendered")
    assert c.get("/api/swap/graph/h3_recast").json() == json.loads((REPO / "workflows" / "h3_recast_api.json").read_text())
    assert c.get("/api/swap/graph/nope").status_code == 404
    # a rendered row whose render went missing is shown as coming, with no picture
    rows = json.loads(DATA.read_text()); rows["rows"][0]["proof"]["src"] = "showcase/not_here.mp4"
    f = tmp_path / "s.json"; f.write_text(json.dumps(rows)); monkeypatch.setattr(feature_swap, "DATA", f)
    r0 = c.get("/api/swap").json()["rows"][0]
    assert r0["status"] == "coming" and "proof" not in r0


def test_page_is_a_feature_page_and_the_demo_saves_its_answers():
    from studio import feature_swap
    p = feature_swap.PAGE
    assert p["tab"] == "swap" and (WEB / p["module"]).is_file() and (WEB / p["css"]).is_file()
    js = (WEB / p["module"]).read_text()
    assert f"export function {p['export']}(" in js and "/api/swap" in js and "demo-api/swap__graph__" in js
    src = (REPO / "scripts" / "build_pages.py").read_text()
    assert 'save("swap")' in src and '"swap/graph/" + r["id"]' in src


def test_no_box_paths_in_the_shipped_swap_files():
    for f in (DATA, WEB / "swap.js", WEB / "swap.css", REPO / "studio" / "feature_swap.py", REPO / "scripts" / "build_swap_table.py"):
        assert not re.search(r"/mnt/|/home/|~/", f.read_text()), f
