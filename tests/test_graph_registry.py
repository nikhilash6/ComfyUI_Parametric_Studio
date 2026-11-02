"""Every graph the studio runs is on the Pro, API and Apps pages, from one list. Stubbed: no ComfyUI, no live port."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from studio import graph_registry as G, model3d as M, recipes as R, families_api as F, server as S
from studio.goals import GOALS

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"


@pytest.fixture(scope="module")
def rows(): return G.all_rows()


def test_every_goal_is_listed(rows):
    assert {r["id"] for r in rows if r["kind"] == "goal"} == set(GOALS)


def test_every_family_template_is_listed(rows):
    have = {(r["sub"], r["id"]) for r in rows if r["key"].startswith("family:")}
    want = {(f, t["name"]) for f, r in F.status_data()["families"].items() for t in r.get("templates") or [] if isinstance(t, dict)}
    assert want == have and len(want) > 200


def test_every_3d_model_is_listed_and_says_how_it_runs(rows):
    by = {r["id"]: r for r in rows if r.get("section") == "model3d"}
    assert set(by) == {m["id"] for m in M.MODELS}
    for m in M.MODELS:
        r = by[m["id"]]
        if m["via"] == "family": assert r["graph_url"]
        else: assert r["graph_url"] is None and "not a ComfyUI graph" in r["runs_as"]
        assert r["call"]["path"] == "/api/3d/run" and r["call"]["body"]["model"] == m["id"]


def test_every_world_kit_and_virtual_set_graph_is_listed(rows):
    assert set(G.workflow_files()) == set(G.WORKFLOWS) == {r["id"] for r in rows if r["kind"] == "workflow"}
    assert G.workflow_files()                                 # a new worldkit_ or vset_ file needs a row, or this fails


def test_every_recipe_that_runs_is_listed(rows):
    have = {r["id"] for r in rows if r["kind"] == "recipe"}
    for x in [*R.load()["recipes"], *R.library()]:
        if not x.get("reference") and any(s.get("goal") for s in x.get("steps") or []): assert x["id"] in have


def test_named_additions_are_there(rows):
    ids = {r["id"] for r in rows}
    assert {"trellis2", "hunyuan3d", "triposr", "triposplat", "shap_e", "moge", "skintokens", "kimodo", "anigen", "svd_xt_1_1_i2v", "sd15_instruct_pix2pix", "image_lotus_depth_v1_1", "utility_sdpose_ood_image_to_pose", "utility_sam3d_body", "trellis2_image_to_mesh"} <= ids


def test_keys_are_unique_and_every_row_has_a_real_call(rows):
    assert len({r["key"] for r in rows}) == len(rows)
    for r in rows: assert r["call"]["method"] == "POST" and r["call"]["path"].startswith("/api/") and r["call"]["poll"].startswith("/api/") and r["runs_as"] and r["label"]


def test_counts_are_computed(rows):
    c = G.counts(rows); assert c["all"] == len(rows) == c["graph"] + c["not_graph"] and c["not_graph"] == sum(1 for m in M.MODELS if m["via"] != "family") + c.get("tryon", 0) + sum(1 for r in rows if r.get("section") == "motion" and not r["graph_url"]) + c.get("voices", 0)


@pytest.fixture
def client(monkeypatch):
    return TestClient(S.app)


def test_the_list_and_the_workflow_graphs_answer(client):
    d = client.get("/api/all-graphs").json(); assert d["counts"]["all"] == len(d["rows"])
    for n in G.workflow_files():
        j = client.get("/api/workflow-graphs/" + n).json(); assert j["format"] == "api" and j["graph"]
    assert client.get("/api/workflow-graphs/nope.json").status_code == 404


def test_a_sample_of_graph_urls_resolve(client, rows, monkeypatch):
    from studio import apps as A
    monkeypatch.setattr(A, "object_info", lambda: (_ for _ in ()).throw(RuntimeError("no comfy here")))
    kinds = {}
    for r in rows:
        if r["graph_url"] and r["kind"] not in kinds: kinds[r["kind"]] = r
    for r in kinds.values():
        j = client.get(r["graph_url"]); assert j.status_code in (200, 503), r["key"]


@pytest.mark.parametrize("page", ["apipage.js", "extras.js", "app.js"])
def test_all_three_pages_read_the_one_list(page):
    assert "useAllGraphs" in (WEB / page).read_text()


def test_the_helper_reads_the_registry():
    t = (WEB / "graph_rows.js").read_text(); assert '"/api/all-graphs"' in t and "not a ComfyUI graph" not in (WEB / "extras.js").read_text()


def test_a_virtual_set_call_is_a_valid_shot_once_it_names_a_place(tmp_path):
    from studio.vset import shot as SH
    glb = tmp_path / "asset.glb"; glb.write_bytes(b"x")
    class Lib:
        def path(self, aid, name): return glb
        def get(self, aid): return {"id": aid, "name": "street", "type": "place", "status": "approved", "files": {"asset.glb": True}, "inspect": {"lo": [-5, -5, 0], "hi": [5, 5, 3]}}
    for name, (_, _, call) in G.WORKFLOWS.items():
        if not name.startswith("vset_"): continue
        assert call["body"]["render"] is True and SH.problems(SH.new_shot(**call["body"]["shot"]), library=Lib()) == [], name


def test_a_world_kit_call_is_a_valid_prop():
    from studio.worldkit.makers import prop as P
    for name in ("worldkit_krea2_t2i_api.json", "worldkit_cutout_api.json"):
        src = G.WORKFLOWS[name][2]["body"]["source"]; kind = "text" if src.get("prompt") else "image"
        assert P.source_problem({"kind": kind, **src}) == ""
