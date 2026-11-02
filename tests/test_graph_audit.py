"""Every graph the studio ships passes the static check (studio/graph_audit.py) against a saved /object_info, so a wrong node name, a wrong input name, a broken link or a bad value fails CI.
No ComfyUI, no GPU, no model files: model and upload menus are this machine's files and are not checked here. A graph that needs a pack the main ComfyUI does not load says so in its metadata ("needs"), and is checked against the lane that loads it.
Refresh the snapshot with: python scripts/graph_audit.py --out /tmp/a.tsv --oi <family instance object_info ...> --lane <lane object_info> --snapshot tests/fixtures/graph_audit_object_info.json.gz"""
import gzip, json
from pathlib import Path
import pytest
from studio import graph_audit as GA

SNAP = json.load(gzip.open(Path(__file__).parent / "fixtures" / "graph_audit_object_info.json.gz", "rt", encoding="utf-8"))
MAIN, LANE = SNAP["main"], SNAP["lane"]
#: Graphs from ComfyUI's own template package that the converter cannot carry yet. Only present where that package is installed; each says why.
KNOWN = {
    "family:ernie-image/image_ernie_image": "a sub-graph input with only a widget value feeds PreviewAny.source, a link-only input",
    "family:ernie-image/image_ernie_image_turbo": "a sub-graph input with only a widget value feeds PreviewAny.source, a link-only input",
    "family:ltx-2-5/video_ltx2_i2v_lora": "the template's sub-graph output names link 265, which its own link list does not have",
    "family:ming-image/image_ming_image_01_design_image_edit": "a bypassed ResizeImageMaskNode passes IMAGE,MASK through, and the converter only passes matching types",
    "app:templates_rob_realistic_2k_images_quick_variations": "uses AILab_QwenVL and ImageRemoveAlpha+, packs the studio does not ship",
}


def _rows():
    rows = GA.file_rows() + GA.goal_rows()
    try: rows += [r for r in GA.family_rows() if r.get("graph") is not None]
    except Exception: pass
    try: rows += [r for r in GA.step_rows(MAIN) if not r.get("build_error")]
    except Exception: pass
    return rows


ROWS = _rows()


def _problems(r):
    needs = GA.needs(r.get("graph"), r.get("meta"))
    if r["target"] == "family" and r.get("family"): oi = GA.server_oi(LANE, GA.family_packs(r["family"]))
    else: oi = LANE if any(x.startswith("pack ") for x in needs) else MAIN
    api, conv, fmt = GA.to_api(r, oi)
    if api is None: return [("not-api-format", c) for c in conv] or [("not-api-format", fmt)]
    return [("bad-input", "convert: " + c) for c in conv] + GA.check(api, oi, files=None, model_opts=False, resolves=r.get("resolves", True))


def test_every_kind_of_graph_is_found():
    src = {r["source"] for r in ROWS}
    assert {"workflows", "goals", "university", "res4lyf_renders/graphs", "res4lyf_renders/nodes", "pipelines/graphs", "web/pipelines", "family-graphs (studio)"} <= src
    assert sum(1 for r in ROWS if r["source"] == "workflows") == len(list((GA.REPO / "workflows").glob("*.json")))
    assert len(ROWS) > 600


@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_graph_passes_static_check(row):
    if row["id"] in KNOWN: pytest.skip(KNOWN[row["id"]])
    probs = [p for p in _problems(row) if p[0] != "missing-model"]
    assert not probs, "\n".join(t for _, t in probs)


def test_check_catches_the_usual_mistakes():
    oi = {"A": {"input": {"required": {"x": ["INT", {"min": 0, "max": 9}], "c": [["p", "q"], {}]}}, "output": ["IMAGE"], "output_node": False},
          "S": {"input": {"required": {"images": ["IMAGE", {}]}}, "output": [], "output_node": True},
          "M": {"input": {"required": {"model": ["MODEL", {}]}}, "output": [], "output_node": True}}
    kinds = lambda g: sorted({k for k, _ in GA.check(g, oi)})
    assert kinds({"1": {"class_type": "A", "inputs": {"x": 3, "c": "p"}}, "2": {"class_type": "S", "inputs": {"images": ["1", 0]}}}) == []
    assert kinds({"1": {"class_type": "Nope", "inputs": {}}}) == ["missing-node"]
    bad = [{"1": {"class_type": "A", "inputs": {"x": 30, "c": "p"}}, "2": {"class_type": "S", "inputs": {"images": ["1", 0]}}},       # over its maximum
           {"1": {"class_type": "A", "inputs": {"x": 3, "c": "z"}}, "2": {"class_type": "S", "inputs": {"images": ["1", 0]}}},        # not a choice
           {"1": {"class_type": "A", "inputs": {"c": "p"}}, "2": {"class_type": "S", "inputs": {"images": ["1", 0]}}},                # required input empty
           {"1": {"class_type": "A", "inputs": {"x": 3, "c": "p"}}, "2": {"class_type": "S", "inputs": {"images": ["9", 0]}}},        # link to no node
           {"1": {"class_type": "A", "inputs": {"x": 3, "c": "p"}}, "2": {"class_type": "S", "inputs": {"images": ["1", 1]}}},        # link to no output
           {"1": {"class_type": "A", "inputs": {"x": 3, "c": "p"}}, "2": {"class_type": "M", "inputs": {"model": ["1", 0]}}},         # IMAGE into MODEL
           {"1": {"class_type": "A", "inputs": {"x": 3, "c": "p"}}}]                                                                   # nothing to save
    for g in bad: assert kinds(g) == ["bad-input"], g


def test_needs_is_read_from_metadata():
    g = {"1": {"class_type": "X", "inputs": {}, "_meta": {"needs": ["pack a/b"]}}}
    assert GA.needs(g) == ["pack a/b"] and GA.needs({"nodes": [], "links": [], "extra": {"needs": ["weights w"]}}) == ["weights w"] and GA.needs(None, {"needs": ["n"]}) == ["n"]
