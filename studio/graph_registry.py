"""One list of everything the studio can run, for the Pro, API and Apps pages, so a new graph shows on all three by being added once: goals, recipes, family templates, the 3D runners and tools from model3d, and the graphs World Kit and Virtual Set send.
Each row says how it runs. A runner or a tool is not a ComfyUI graph and has graph_url None, and its call is the real call that runs it. Counts are computed from the rows."""
import json, os
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(); WF = Path(__file__).resolve().parent.parent / "workflows"
RUNS = {"goal": "ComfyUI graph", "recipe": "ComfyUI graphs in a chain", "family": "ComfyUI graph on its family's own server", "runner": "A small program in its own process, not a ComfyUI graph", "tool": "A third-party tool in its own environment, not a ComfyUI graph", "workflow": "ComfyUI graph that World Kit or Virtual Set fills in and sends"}
MODEL_BODY = {"mesh_from_image": {"image": "NAME_FROM_POST_/api/upload"}, "relief_from_image": {"image": "NAME_FROM_POST_/api/upload"}, "splat_from_image": {"image": "NAME_FROM_POST_/api/upload"}, "rigged_from_image": {"image": "NAME_FROM_POST_/api/upload"}, "mesh_from_text": {"prompt": "a wooden chair", "seed": 7}, "motion": {"prompt": "a person walks forward, then waves", "seed": 7}, "rig": {"mesh": "PATH_FROM_GET_/api/models3d"}}
ASSETS, SHOTS = "/api/worldkit/assets", "/api/vset/shots"
def _shot(mode, **settings):
    return {"shot": {"mode": mode, "mode_settings": settings, "set": {"place": "PLACE_ASSET_ID"}, "format": {"aspect": "16:9", "seconds": 5}, "prompt": "a slow walk along the street at dusk"}, "render": True}
#: The graph templates behind World Kit and Virtual Set: label, where it opens, and the call that sends it. A new file here without a row fails a test.
WORKFLOWS = {
    "worldkit_krea2_t2i_api.json": ("World Kit: a prop's picture (Krea 2)", "worldkit", {"method": "POST", "path": ASSETS, "body": {"type": "prop", "name": "fire hydrant", "source": {"prompt": "a red fire hydrant"}}, "poll": ASSETS + "/ID"}),
    "worldkit_cutout_api.json": ("World Kit: cut a prop out of its picture", "worldkit", {"method": "POST", "path": ASSETS, "body": {"type": "prop", "name": "bear statue", "source": {"image": "NAME_FROM_POST_/api/upload"}}, "poll": ASSETS + "/ID"}),
    "worldkit_trellis2_character_api.json": ("World Kit: a character's textured mesh (TRELLIS.2)", "worldkit", {"method": "POST", "path": ASSETS, "body": {"type": "character", "name": "Maya", "source": {"character_id": "ID_FROM_POST_/api/worldkit/characters"}}, "poll": ASSETS + "/ID", "note": "Make the saved character first, from a name and a description. Its sheet has to pass the picture check."}),
    "worldkit_body_photo_api.json": ("World Kit: a character's plain body (SAM 3D Body)", "worldkit", {"method": "POST", "path": ASSETS, "body": {"type": "character", "name": "Maya", "source": {"character_id": "ID_FROM_POST_/api/worldkit/characters"}, "recipe": {"mesh": "sam3d_body"}}, "poll": ASSETS + "/ID", "note": "A recipe choice, not the default: it gives a bare grey figure with no clothes on the mesh."}),
    "vset_h3_motion_api.json": ("Virtual Set: copy a motion with MiniMax H3", "virtualset", {"method": "POST", "path": SHOTS, "body": _shot("D"), "poll": SHOTS + "/ID"}),
    "vset_h3_union_api.json": ("Virtual Set: guide MiniMax H3 with depth and pose", "virtualset", {"method": "POST", "path": SHOTS, "body": _shot("A", engine="h3", control="depth"), "poll": SHOTS + "/ID"}),
    "vset_keyframe_edit_api.json": ("Virtual Set: edit a keyframe (Qwen-Image 2.1)", "virtualset", {"method": "POST", "path": SHOTS, "body": _shot("C", keyframes="qwen"), "poll": SHOTS + "/ID"}),
    "vset_ltx25_layout_api.json": ("Virtual Set: LTX-2.5 layout to render", "virtualset", {"method": "POST", "path": SHOTS, "body": _shot("A", engine="ltx", keyframes="qwen"), "poll": SHOTS + "/ID"}),
    "vset_wan22_funcontrol_api.json": ("Virtual Set: Wan 2.2 Fun Control", "virtualset", {"method": "POST", "path": SHOTS, "body": _shot("A", engine="wan", control="depth"), "poll": SHOTS + "/ID"}),
}


def workflow_files():
    """The graph templates World Kit and Virtual Set read."""
    return sorted(p.name for p in WF.glob("*.json") if p.name.startswith(("worldkit_", "vset_")))


def _goal_rows():
    from studio.goals import GOALS
    return [{"key": "goal:" + k, "kind": "goal", "id": k, "label": v["label"], "sub": v["family"], "graph_url": "/api/graphs/" + k, "open": "create", "call": {"method": "POST", "path": "/api/generate", "body": {"goal": k, "prompt": "a lighthouse at dawn"}, "poll": "/api/jobs/ID"}} for k, v in GOALS.items()]


def _recipe_rows():
    from studio import recipes as R
    seen, out = set(), []
    for r in [*R.load()["recipes"], *R.library()]:
        if r["id"] in seen or r.get("reference") or not any(s.get("goal") for s in r.get("steps") or []): continue         # a reference card has nothing to run
        seen.add(r["id"]); out.append({"key": "recipe:" + r["id"], "kind": "recipe", "id": r["id"], "label": r.get("title") or r["id"], "sub": r.get("pitch") or "Recipe", "group": r.get("group"), "graph_url": "/api/recipe-graphs/" + r["id"], "open": "recipes", "call": {"method": "POST", "path": f"/api/recipes/{r['id']}/run", "body": {"values": {}}, "poll": f"/api/recipes/{r['id']}/runs/ID"}})
    return out


def _family_rows():
    from urllib.parse import quote
    from studio import families_api as F
    out = []; scan = F.scan()
    for f, r in F.status_data().get("families", {}).items():
        art = next((m.get("poster") for m in (r.get("media") or []) if m.get("kind") != "audio" and m.get("poster") and not m.get("library")), None) or next((m.get("poster") for m in (r.get("media") or []) if m.get("poster")), None); slug = r.get("slug")
        ran = {m.get("tpl") for m in r.get("media") or [] if m.get("own")}
        for t in r.get("templates") or []:
            if not isinstance(t, dict): continue
            out.append({"key": f"family:{slug}/{t['name']}", "kind": "family", "id": t["name"], "slug": slug, "label": t.get("title") or t["name"], "sub": f, "cat": t.get("cat") or r.get("kind") or "", "desc": t.get("desc") or "", "art": art, "ready": F.tpl_state(t, scan.get(f, {}))["ready"], "ran_here": t["name"] in ran, "graph_url": f"/api/family-graphs/{slug}/{quote(t['name'], safe='')}", "open": "families/" + slug, "call": {"method": "POST", "path": f"/api/families/{slug}/templates/{quote(t['name'], safe='')}/run", "body": {"values": {}}, "poll": f"/api/families/{slug}/jobs/ID"}})
    return out


def _model_rows(need=None):
    """Each 3D model as a way to run it from code. One that runs a family template points at that graph; a runner or a tool has none, and says so."""
    from studio import model3d as M
    rows = []; pr = M.proof()
    for m in M.MODELS:
        graph = None
        if m["via"] == "family":
            from urllib.parse import quote
            from studio import families_api as F
            graph = f"/api/family-graphs/{F._slug(m['family'])}/{quote(m['template'], safe='')}"
        rows.append({"key": "model3d:" + m["id"], "kind": "family" if m["via"] == "family" else m["via"], "section": "model3d", "id": m["id"], "label": m["label"], "sub": m["note"], "job": m["job"], "licence": m.get("licence"), "proof": pr.get(m["id"]) or {"status": "not run"}, "art": (pr.get(m["id"]) or {}).get("sheet"), "graph_url": graph, "open": "viewer", "runs_as": RUNS["family" if m["via"] == "family" else m["via"]], "call": {"method": "POST", "path": "/api/3d/run", "body": {"model": m["id"], **MODEL_BODY[m["job"]]}, "poll": "/api/3d/jobs/ID"}})
    return rows


def _tryon_rows():
    """The try-on methods that are runners. The family ones are already family rows."""
    from studio import tryon as T
    return [{"key": "tryon:" + m["id"], "kind": m["via"], "section": "tryon", "id": m["id"], "label": f"Try-on: {m['label']}", "sub": m["note"], "licence": m["licence"], "graph_url": None, "open": "design/fashion", "call": {"method": "POST", "path": "/api/tryon/run", "body": {"method": m["id"], "person": "NAME_FROM_POST_/api/upload", "garment": "NAME_FROM_POST_/api/upload", "category": "tops"}, "poll": "/api/tryon/jobs/ID"}} for m in T.METHODS if m["via"] == "runner"]


def _workflow_rows():
    return [{"key": "workflow:" + n, "kind": "workflow", "id": n, "label": WORKFLOWS[n][0], "sub": "World Kit" if WORKFLOWS[n][1] == "worldkit" else "Virtual Set", "graph_url": "/api/workflow-graphs/" + n, "open": WORKFLOWS[n][1], "call": WORKFLOWS[n][2]} for n in workflow_files() if n in WORKFLOWS]


def all_rows():
    rows = [*_goal_rows(), *_model_rows(), *_tryon_rows(), *_workflow_rows(), *_family_rows(), *_recipe_rows()]
    for r in rows: r.setdefault("runs_as", RUNS[r["kind"]])
    return rows


def counts(rows):
    out = {"all": len(rows), "graph": sum(1 for r in rows if r["graph_url"]), "not_graph": sum(1 for r in rows if not r["graph_url"])}
    for r in rows:
        k = r.get("section") or r["kind"]; out[k] = out.get(k, 0) + 1
    return out


@router.get("/api/all-graphs")
def all_graphs():
    rows = all_rows(); return {"rows": rows, "counts": counts(rows)}


@router.get("/api/workflow-graphs/{name}")
def workflow_graph(name: str):
    """A World Kit or Virtual Set graph as it is stored; ${names} are what those pages fill in."""
    if name not in WORKFLOWS or name not in workflow_files(): raise HTTPException(404, "no such graph")
    from studio.graph_template import placeholders
    tpl = json.load(open(WF / name, encoding="utf-8")); return {"name": name, "format": "api", "fills": sorted(placeholders(tpl)), "graph": tpl}
