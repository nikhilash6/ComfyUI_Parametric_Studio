"""Geometry and maths nodes: the Pack Lab picks say what was and was not done, the demo graphs check against the node list of the lane they ran on, the 3D page's mesh tools name only core nodes and real pictures, and nothing joins the default install. No ComfyUI, no Docker, no live ports."""
import json, re
from pathlib import Path
from studio import feature_packlab as L, graph_audit as GA

ROOT = Path(__file__).resolve().parents[1]; WEB = ROOT / "studio" / "web"; DEMOS = WEB / "pack_lab_demos"
LAB_OI = json.loads((ROOT / "tests" / "fixtures" / "geomath_lab_object_info.json").read_text())
CORE_MESH = {"WeldVertices", "DecimateMesh", "RemeshMesh", "FillHoles", "MeshSmoothNormals", "UnwrapMesh", "RotateMesh", "MergeMeshes", "GetMeshInfo", "RenderMesh"}


def pick(name): return next(p for p in L.picks()["picks"] if p["pack"] == name)


def test_comfymath_is_a_proven_lab_pick_with_its_risk_in_sight():
    p = pick("rabanti-github__ComfyMath")
    assert p["action"] == "install-candidate" and p["sandbox"] == "ok" and p["repo"] == "rabanti-github/ComfyMath"
    assert "Apache-2.0" in p["licence"] and "Factorial" in p["risk"] and "evanspearman__ComfyMath" in p["risk"]
    assert "pixel for pixel" in p["note"] and "repeat core" in p["adds"]


def test_geometrypack_is_named_properly_and_not_installable():
    assert not any(p["pack"] == "ComfyUI-GeometryPack" for p in L.picks()["picks"]), "the old name had no owner, so its link went nowhere"
    p = pick("PozzettiAndrea__ComfyUI-GeometryPack")
    assert p["action"] == "docs-only" and p["sandbox"] == "untested" and L.NAME_OK.fullmatch(p["pack"])
    assert "comfy-env==0.3.89" in p["risk"] and "comfy-3d-viewers==0.2.44" in p["risk"] and "GPL-3.0" in p["licence"]
    assert "DecimateMesh" in p["adds"], "says what core already covers"


def test_the_other_maths_packs_stay_out():
    names = {p["pack"] for p in L.picks()["picks"]}
    for gone in ("evanspearman__ComfyMath", "akatz-ai__ComfyUI-Basic-Math", "silveroxides__ComfyUI-LogicMath", "GuusF__Comfyui_CrazyMaths", "EmilioPlumed__ComfyUI-Math", "Arch666Angel__ComfyUI-Geometry-Nodes"):
        assert gone not in names, gone


def test_every_demo_graph_checks_against_the_lane_it_ran_on():
    files = sorted(DEMOS.glob("*.json")); assert len(files) == 4
    for f in files:
        d = json.loads(f.read_text()); g = d["graph"]; m = d["meta"]
        assert GA.is_api(g) and m["proved"] and m["licence"] and m["status"], f.name
        probs = [x for x in GA.check(g, LAB_OI, files=None, model_opts=False) if x[0] != "missing-model"]
        assert not probs, (f.name, probs)
        uses_cm = any(n["class_type"].startswith("CM_") for n in g.values())
        assert uses_cm == f.name.startswith("comfymath_"), f.name
        assert ("pack rabanti-github__ComfyMath" in m["needs"]) == uses_cm and ("Pack Lab only" in m["status"]) == uses_cm, f.name


def test_the_core_demo_uses_no_pack():
    g = json.loads((DEMOS / "core_mesh_cleanup.json").read_text())["graph"]
    assert {n["class_type"] for n in g.values()} & CORE_MESH >= {"WeldVertices", "DecimateMesh", "MeshSmoothNormals", "RotateMesh", "GetMeshInfo", "RenderMesh"}
    assert not any(n["class_type"].startswith(("CM_", "PSN_")) for n in g.values())


def test_mesh_tools_on_the_3d_page_are_core_and_real():
    d = json.loads((WEB / "mesh_tools.json").read_text())
    assert {n["node"] for n in d["core"]} <= CORE_MESH and len(d["core"]) >= 8
    for x in d["proof"]["pictures"]:
        f = WEB / x["src"]; assert f.is_file() and f.read_bytes()[8:12] == b"WEBP" and f.stat().st_size < 60_000 and x["alt"]
    assert (WEB / d["proof"]["graph"]).is_file() and "6,612" in d["proof"]["caption"] and "collision box" in d["proof"]["caption"]
    geo = next(k for k in d["packs"] if "GeometryPack" in k["pack"])
    assert geo["status"] == "Read, not installed" and "not run" in geo["why"]
    js = (WEB / "studio3d.js").read_text()
    assert "mesh_tools.json" in js and "<${MeshTools}/>" in js


def test_notices_docs_and_no_default_install():
    notes = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(); docs = (ROOT / "docs" / "NODES.md").read_text()
    assert "rabanti-github/ComfyMath" in notes and "Apache-2.0" in notes and "PozzettiAndrea/ComfyUI-GeometryPack" in notes and "was not run" in notes
    head = docs.split("<!-- node reference:")[0]
    assert "Pack Lab only" in head and "was not installed or tested" in head and "ComfyMathExpression" in head
    for f in ("install.py", "pyproject.toml", "INSTALL.md"):
        t = (ROOT / f).read_text(encoding="utf-8")
        assert not re.search(r"ComfyMath|GeometryPack|comfy-env|comfy_env", t), f
    assert not any("CM_" in p.read_text() for p in (ROOT / "workflows").glob("*.json")), "no shipped workflow needs the pack"
