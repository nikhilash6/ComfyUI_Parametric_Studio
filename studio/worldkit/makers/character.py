"""Character maker: a saved character's sheet -> SAM 3D Body (mesh) -> AutoRemesher (topology, optional) -> SkinTokens (rig) -> motion clips (Kimodo from text; each retargeted onto the rig) -> one
glb with the clips (Blender, CPU). Off unless STUDIO_WORLDKIT_CHARACTERS=1: see safety.py for what is and is not checked. Characters come only from saved characters.

Known limits: SAM 3D Body gives an untextured body (proportions, not clothes or hair), and AutoRemesher's quad LODs drop UVs and colour; recipe "mesh" can be
sam3d_objects (colour kept) and "remesh" off."""
from __future__ import annotations

import re

from studio.worldkit import jobs
from studio.worldkit import library as L
from studio.worldkit import steps as S
from studio.worldkit import tools

MESHES = ("sam3d_body", "sam3d_objects")
BODY_GRAPH = "worldkit_body_photo_api.json"
DEFAULT_CLIPS = ({"name": "idle", "text": "a person stands relaxed in place, breathing, shifting weight slightly"},
                 {"name": "walk", "text": "a person walks forward at a relaxed pace"},
                 {"name": "wave", "text": "a person stands and waves with the right hand"})
DEFAULT_RECIPE = {"mesh": "sam3d_body", "remesh": True, "height_m": 1.7}
CLIP_NAME = re.compile(r"^[a-z][a-z_]{0,23}$")
MAX_CLIPS = 4
CLIP_SECONDS = 5
BUILD_STEP = "assemble"


def recipe(given: dict | None) -> tuple[dict, list[str]]:
    given = dict(given or {})
    r = {**DEFAULT_RECIPE, **given}
    r["clips"] = given["clips"] if "clips" in given else [dict(c) for c in DEFAULT_CLIPS]
    bad: list[str] = []
    if r["mesh"] not in MESHES:
        bad.append(f"mesh must be one of {', '.join(MESHES)}")
    if not isinstance(r["remesh"], bool):
        bad.append("remesh is true or false")
    lo, hi = L.HEIGHT_M
    h = r["height_m"]
    if isinstance(h, bool) or not isinstance(h, (int, float)) or not lo <= h <= hi:
        bad.append(f"height_m is {lo}-{hi} m")
    clips = r["clips"]
    if not isinstance(clips, list) or len(clips) > MAX_CLIPS:
        bad.append(f"clips is a list of up to {MAX_CLIPS}")
        clips = []
    names = []
    for c in clips:
        if not isinstance(c, dict) or not CLIP_NAME.match(str(c.get("name", ""))):
            bad.append("each clip has a name of lowercase letters (and _)")
            continue
        if not str(c.get("text") or "").strip():
            bad.append(f"clip {c['name']}: describe the motion")
        names.append(c["name"])
    if len(set(names)) != len(names):
        bad.append("clip names must be different")
    return r, bad


def _clip_steps(c: dict) -> list[S.Step]:
    name = c["name"]

    def motion(ctx):
        return {"main": {"path": str((ctx.get("kimodo") or tools.kimodo)(c["text"], ctx["work"] / f"motion_{name}", seconds=CLIP_SECONDS))}}

    def retarget(ctx):
        if f"motion_{name}" not in ctx["outputs"]:
            return None                        # the motion failed (optional): no retarget, the clip is left out
        return {"main": {"path": str((ctx.get("retarget") or tools.retarget)(S.out_path(ctx, f"motion_{name}"), S.out_path(ctx, "rig"), ctx["work"] / f"retarget_{name}"))}}

    return [S.Step(f"motion_{name}", f"Motion '{name}'", local=motion, optional=True),
            S.Step(f"retarget_{name}", f"Retarget '{name}'", local=retarget, optional=True)]


def steps(meta: dict) -> list[S.Step]:
    r, bad = recipe(meta.get("recipe"))
    if bad:
        raise ValueError("; ".join(bad))
    cid = meta["source"]["character_id"]
    shape = "remesh" if r["remesh"] else "mesh"

    def sheet(ctx):
        from studio.worldkit import characters as CS, safety
        why = safety.character_problem()
        if why:
            raise S.StepError(why)
        ch = (ctx.get("get_character") or CS.get)(cid)
        bad = CS.sheet_problem(ch)
        if bad:
            raise S.StepError(bad)
        return {"main": {"path": str(ch.sheet())}}

    def mesh_req(ctx):
        tools.require("sam3d_body")
        name = (ctx.get("to_input") or jobs.to_input)(S.out_path(ctx, "sheet"))
        return jobs.graph(BODY_GRAPH, {"image": name}, f"World Kit body: {meta['name']}")

    def mesh_local(ctx):
        return {"main": {"path": str((ctx.get("sam3d") or tools.sam3d_objects)(S.out_path(ctx, "sheet"), ctx["work"] / "mesh"))}}

    def remesh(ctx):
        return {"main": {"path": str((ctx.get("autoremesher") or tools.autoremesher)(S.out_path(ctx, "mesh"), ctx["work"] / "remesh"))}}

    def rig(ctx):
        return {"main": {"path": str((ctx.get("skintokens") or tools.skintokens)(S.out_path(ctx, shape), ctx["work"] / "rig"))}}

    out = [S.Step("sheet", "Sheet", local=sheet),
           S.Step("mesh", "Mesh", request=mesh_req, pick=S.pick_first(suffix=(".glb",))) if r["mesh"] == "sam3d_body" else S.Step("mesh", "Mesh", local=mesh_local)]
    if r["remesh"]:
        out.append(S.Step("remesh", "Remesh (AutoRemesher)", local=remesh))
    out.append(S.Step("rig", "Rig (SkinTokens)", local=rig))
    for c in r["clips"]:
        out += _clip_steps(c)
    out.append(S.Step(BUILD_STEP, "Assemble (Blender)", local=assemble))
    return out


def assemble(ctx: dict, *, blender=None) -> dict:
    """The rigged mesh + the retargeted clips -> character.glb (Blender, CPU only), its humanoid map."""
    from studio.worldkit import blender as B, rigmap
    bl = blender or ctx.get("blender") or B
    meta = ctx["asset"]
    r, _ = recipe(meta.get("recipe"))
    clips = [{"name": c["name"], "path": S.out_path(ctx, f"retarget_{c['name']}")} for c in r["clips"] if f"retarget_{c['name']}" in ctx["outputs"]]
    work = ctx["work"] / BUILD_STEP
    work.mkdir(parents=True, exist_ok=True)
    out = work / "character.glb"
    with B.cpu_only():
        res = bl.run("wk_assemble.py", {"rig": S.out_path(ctx, "rig"), "clips": clips, "height_m": r["height_m"], "out": str(out)},
                     work=work, name="assemble", timeout=1800, gpu=False)
    ins = dict(res["inspect"])
    bone_list = ins.pop("bones", [])
    main = {"path": str(out), "inspect": ins, "clips": res.get("clips", [])}
    try:
        main["rig"] = {"bones": len(bone_list), "standard": "skintokens", "slots": rigmap.slots(bone_list)}
    except rigmap.RigMapError as exc:
        main["rig"] = {"bones": len(bone_list), "standard": "skintokens", "slots": {}}
        main["note"] = f"no humanoid map: {exc}"
    return {"main": main}
