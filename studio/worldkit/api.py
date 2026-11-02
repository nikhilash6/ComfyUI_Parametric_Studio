"""/api/worldkit/*: the library, the builds, the pack export. Route logic is in plain functions over a Library that return (status, body), so each is tested without a server, ComfyUI or a GPU; the router
below is the thin FastAPI layer."""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from studio.worldkit import capabilities as C
from studio.worldkit import characters as CS
from studio.worldkit import export as X
from studio.worldkit import library as L
from studio.worldkit import looks, runner, safety
from studio.worldkit import steps as S
from studio.worldkit.makers import character, place, prop

router = APIRouter()
FILE_TYPES = {"asset.glb": "model/gltf-binary", "preview.mp4": "video/mp4", "thumb.jpg": "image/jpeg"}
_SESSION = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
#: Informational only: licences are recorded per asset, never a gate.
LICENCE_NOTES = {
    "character": "Sheet: Krea 2 Turbo (Krea 2 Community License). Picture check: InsightFace buffalo_l (its weights are for non-commercial research) and NudeNet (AGPL-3.0). Mesh: TRELLIS.2 (MIT), its image encoder DINOv3 (DINOv3 License), BiRefNet cut-out. SkinTokens: MIT; Kimodo: NVIDIA Open Model License (its text encoder: Llama 3 Community Licence); retarget tools GPL (tools only)",
    "prop": "by mesh model: SAM 3D Objects, SAM License; TRELLIS.2, TripoSR, Shap-E, MIT; Hunyuan3D, Tencent community licence. A text prop's picture comes from FLUX.2 Klein 4B (Apache-2.0)",
    "place": "procedural (Blender scripts in this repo); textures procedural, or from FLUX.2 Klein 4B (Apache-2.0)",
    "look": "Blender's bundled studio-light HDRIs (their licence not checked)",
}


def _err(code: int, msg: str) -> tuple[int, dict]:
    return code, {"error": msg}


def summary(meta: dict, running: bool = False) -> dict:
    build = meta.get("build") or {}
    steps_ = build.get("steps") or []
    failed = next((r for r in steps_ if r["status"] == "failed" and "optional" not in r.get("note", "")), None)
    return {"id": meta["id"], "type": meta["type"], "name": meta["name"], "tags": meta.get("tags", []),
            "status": meta["status"], "build": build.get("state", "pending"), "error": build.get("error", ""),
            "progress": [sum(1 for r in steps_ if r["status"] in ("done", "skipped")), len(steps_)],
            "failed_step": failed["name"] if failed else "", "lost_motions": S.lost_motions(build) if meta["type"] == "character" else [], "files": sorted((meta.get("files") or {}).keys()),
            "scale_m": meta.get("scale_m"), "clips": [c.get("name") for c in meta.get("clips") or []],
            "rig_bones": (meta.get("rig") or {}).get("bones", 0), "licence_class": meta.get("licence_class"),
            "created": meta.get("created"), "updated": meta.get("updated"), "running": bool(running)}


def list_assets(lib, query: dict, *, is_running) -> tuple[int, dict]:
    t, st = query.get("type") or None, query.get("status") or None
    if t is not None and t not in L.TYPES:
        return _err(400, f"type must be one of {', '.join(L.TYPES)}")
    if st is not None and st not in L.STATUSES:
        return _err(400, f"status must be one of {', '.join(L.STATUSES)}")
    metas = lib.list(type_=t, tag=query.get("tag") or None, q=query.get("q") or None, status=st)
    return 200, {"assets": [summary(m, is_running(m["id"])) for m in metas]}


def get_asset(lib, aid: str, *, is_running) -> tuple[int, dict]:
    meta = lib.get(aid)
    if meta is None:
        return _err(404, "no such asset")
    return 200, {**meta, "running": bool(is_running(aid))}


def looks_payload() -> tuple[int, dict]:
    return 200, {"looks": looks.public(), "times": list(looks.TIMES), "weathers": list(looks.WEATHERS)}


def characters_payload(chars, *, sheet_running=lambda cid: False) -> tuple[int, dict]:
    """The saved characters, each with whether it can become a 3D character now and why not. A sheet marked building with no thread behind it was cut off by a restart: "interrupted", and it can be tried again."""
    off = safety.character_problem()
    out = []
    for ch in chars:
        why = off or CS.sheet_problem(ch)
        running = bool(sheet_running(ch.id))
        status = "interrupted" if ch.status == "building" and not running else ch.status
        out.append({"id": ch.id, "name": ch.name, "description": ch.description, "status": status, "running": running, "error": ch.error, "take": ch.take, "sheet": not why and ch.sheet().is_file(), "ok": not why, "why": why})
    return 200, {"characters": out, "enabled": not off, "message": off, "limits": safety.CHECK_LIMITS}


def new_character(payload, *, start, capability=C.route) -> tuple[int, dict]:
    if not isinstance(payload, dict):
        return _err(400, "send a JSON object")
    if set(payload) - {"name", "description"}:
        return _err(400, "a saved character is made from a name and a description, and nothing else")
    off = safety.character_problem()
    if off:
        return _err(403, off)
    bad = _route_problem("character_sheet", capability)          # no picture model or no picture check: say so and make nothing
    if bad:
        return _err(409, bad)
    ch, why = CS.create(payload.get("name"), payload.get("description"))
    if ch is None:
        return _err(400, why)
    start(ch.id)
    return 200, {"id": ch.id, "status": ch.status}


def character_again(cid: str, *, start, sheet_running=lambda c: False, capability=C.route) -> tuple[int, dict]:
    """Another try at the sheet from the same words. Every check runs again on the new picture."""
    off = safety.character_problem()
    if off:
        return _err(403, off)
    if CS.get(cid) is None:
        return _err(404, "no such saved character")
    if sheet_running(cid):
        return _err(409, "this character's sheet is being made now")
    bad = _route_problem("character_sheet", capability)
    if bad:
        return _err(409, bad)
    ch = CS.next_take(cid)
    start(cid)
    return 200, {"id": cid, "status": ch.status, "take": ch.take}


def character_sheet_path(cid: str):
    """The sheet's file, only while it holds a pass for this exact picture."""
    ch = CS.get(cid)
    return ch.sheet() if ch is not None and ch.sheet().is_file() and CS.picturecheck.passed(ch.check, ch.sheet()) else None


_SHEETS: dict = {}


def _sheet_running(cid: str) -> bool:
    t = _SHEETS.get(cid)
    return t is not None and t.is_alive()


def _start_sheet(cid: str) -> None:
    import threading
    t = threading.Thread(target=CS.build_sheet, args=(cid,), daemon=True, name=f"sheet-{cid}")
    _SHEETS[cid] = t
    t.start()


def _route_problem(name: str, capability) -> str:
    r = capability(name)
    return "" if r["ready"] else " ".join(r["problems"])


def create(lib, payload, *, get_character, start, capability=C.route) -> tuple[int, dict]:
    if not isinstance(payload, dict):
        return _err(400, "send a JSON object")
    t = payload.get("type")
    if t not in L.TYPES:
        return _err(400, f"type must be one of {', '.join(L.TYPES)}")
    session = str(payload.get("session_id") or "worldkit")
    if not _SESSION.match(session):
        return _err(400, "invalid session id")
    tags = payload.get("tags") or []
    if not isinstance(tags, list):
        return _err(400, "tags is a list of words")
    src = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    given = payload.get("recipe") if isinstance(payload.get("recipe"), dict) else {}
    name, look, r = str(payload.get("name") or "").strip(), {}, {}
    bad = safety.text_problem(name, tags, src, given)
    if bad:
        return _err(400, bad)
    if t == "character":
        bad = safety.character_problem()
        if bad:
            return _err(403, bad)
        cid = str(src.get("character_id") or "")
        ch = get_character(cid) if cid else None
        bad = CS.sheet_problem(ch)
        if bad:
            return _err(400, bad)
        r, problems = character.recipe(given)
        if problems:
            return _err(400, "; ".join(problems))
        bad = safety.text_problem([c.get("text") for c in r["clips"]])
        if bad:
            return _err(400, bad)
        bad = _route_problem("character", capability)
        if bad:
            return _err(409, bad)
        name = name or ch.name
        source = {"kind": "character", "character_id": cid, "name": ch.name, "description": ch.description[:600]}
    elif t == "prop":
        kind = "text" if src.get("prompt") else ("mesh" if src.get("mesh") else "image")
        source = {"kind": kind, **{k: src[k] for k in ("prompt", "image", "mesh") if k in src}}
        bad = prop.source_problem(source)
        if bad:
            return _err(400, bad)
        pick = given.get("mesh_model")
        if pick in C.TEXT_MESH_ROUTES and kind == "text":
            r_ = C.route_of([pick])                     # words straight to a mesh: no picture model and no cut-out needed
            bad = "" if r_["ready"] else " ".join(r_["problems"])
        elif pick and kind != "mesh" and pick in C.MESH_ROUTES:
            r_ = C.route_of(["text_image", "cutout", pick] if kind == "text" else ["cutout", pick])
            bad = "" if r_["ready"] else " ".join(r_["problems"])
        else:
            bad = _route_problem(f"prop_{kind}", capability)
        if bad:
            return _err(409, bad)
        name = name or str(src.get("prompt") or "prop")[:60]
        r, problems = prop.recipe(given, name)
        if problems:
            return _err(400, "; ".join(problems))
    elif t == "place":
        brief = str(src.get("brief") or "").strip()
        if not brief:
            return _err(400, "describe the place (a brief like 'rainy downtown block')")
        r = place.plan(brief, overrides=given)
        problems = place.recipe_problems(r)
        if problems:
            return _err(400, "; ".join(problems))
        name, source = name or brief[:60], {"kind": "brief", "brief": brief[:600]}
    else:
        preset = str(src.get("preset") or looks.DEFAULT)
        problems = looks.problems(preset, src.get("time"), src.get("weather"))
        if problems:
            return _err(400, "; ".join(problems))
        look = {"preset": preset, "time": src.get("time") or None, "weather": src.get("weather") or None}
        name, source = name or looks.LOOKS[preset]["label"], {"kind": "preset", "preset": preset}
    try:
        meta = L.new_meta(t, name, source=source, tags=tags, session_id=session, recipe=r, look=look, licence_note=LICENCE_NOTES[t])
        meta["build"] = S.new_state([s.name for s in runner.build_steps(meta)])
        lib.create(meta)
    except (L.AssetError, ValueError) as exc:
        return _err(400, str(exc))
    start(meta["id"])
    return 200, {"asset": summary(meta, True)}


def _as_prop(lib, meta: dict, start, capability=C.route) -> tuple[int, dict]:
    """A character without a rig is never a cast member; it is offered as a static prop instead."""
    st = {r["name"]: r for r in (meta.get("build") or {}).get("steps") or []}
    if (st.get("rig") or {}).get("status") == "done":
        return _err(400, "this character has a rig; use it as a cast member")
    shape = next((st[n] for n in ("remesh", "flat", "mesh") if (st.get(n) or {}).get("status") == "done"), None)
    if shape is None:
        return _err(400, "this character has no mesh yet to make a static prop from")
    work_rel = "lib:" + str(lib.keep_mesh(meta["id"], shape["outputs"]["main"]["path"]))
    return create(lib, {"type": "prop", "name": f"{meta['name']} (static)"[:L.MAX_NAME], "tags": meta.get("tags", []), "session_id": meta["session_id"], "source": {"mesh": work_rel},
                        "recipe": {"size_m": float((meta.get("recipe") or {}).get("height_m", 1.7))}}, get_character=lambda cid: None, start=start, capability=capability)


def action(lib, aid: str, verb: str, payload, *, start, is_running, cancel=None, capability=C.route) -> tuple[int, dict]:
    meta = lib.get(aid)
    if meta is None:
        return _err(404, "no such asset")
    running = is_running(aid)
    if verb in ("retry", "retry-motion", "archive", "as-prop", "clips") and running:
        return _err(409, "this asset is building now; wait for it to finish")
    try:
        if verb == "retry":
            lib.update(aid, build=S.retry(meta["build"]))
            start(aid)
            return 200, {"asset": summary(lib.get(aid), True)}
        if verb == "retry-motion":
            name = str((payload or {}).get("name") or "")
            if name not in S.lost_motions(meta.get("build")):
                return _err(400, "that motion is not one this character lost")
            lib.update(aid, build=S.retry_motion(meta["build"], name, character.BUILD_STEP), status="draft")
            start(aid)
            return 200, {"asset": summary(lib.get(aid), True)}
        if verb == "cancel":
            if not running or cancel is None or not cancel(aid):
                return _err(409, "this asset is not building")
            return 200, {"asset": summary(meta, True)}
        if verb == "approve":
            return 200, {"asset": summary(lib.approve(aid), running)}
        if verb == "unapprove":
            return 200, {"asset": summary(lib.update(aid, status="draft"), running)}
        if verb == "archive":
            return 200, {"archived": str(lib.archive(aid))}
        if verb == "as-prop":
            if meta["type"] != "character":
                return _err(400, "only a character can become a static prop")
            return _as_prop(lib, meta, start, capability)
        if verb == "clips":
            if meta["type"] != "character":
                return _err(400, "only a character has motion clips")
            clips = (payload or {}).get("clips")
            bad = safety.text_problem(clips)
            if bad:
                return _err(400, bad)
            r, bad = character.recipe({**meta["recipe"], "clips": clips})
            if bad:
                return _err(400, "; ".join(bad))
            state = S.sync(meta["build"], [s.name for s in runner.build_steps({**meta, "recipe": r})])
            lib.update(aid, recipe=r, build=state, status="draft")
            start(aid)
            return 200, {"asset": summary(lib.get(aid), True)}
    except L.AssetError as exc:
        return _err(400, str(exc))
    return _err(404, f"no action {verb!r}")


def asset_path(lib, aid: str, name: str):
    """(path, content type) of one of an asset's files, or None. The name is matched against a fixed list, never joined raw."""
    if name not in FILE_TYPES:
        return None
    meta = lib.get(aid)
    if meta is None:
        return None
    p = lib.dir(meta["type"], aid) / name
    return (p, FILE_TYPES[name]) if p.is_file() else None


def export_pack(lib, payload) -> tuple[int, dict]:
    return X.build_pack(lib, payload)


def exports_payload(lib) -> tuple[int, dict]:
    return 200, {"exports": X.list_exports(lib)}


# ---------- routes
def _lib():
    return L.Library()


def _send(res):
    code, body = res
    if code >= 400:
        raise HTTPException(code, body.get("error") or "refused")
    return body


def _start(aid: str) -> None:
    runner.start(aid, library=_lib())


@router.get("/api/worldkit/assets")
def assets_list(type: str = "", tag: str = "", q: str = "", status: str = ""):
    return _send(list_assets(_lib(), {"type": type, "tag": tag, "q": q, "status": status}, is_running=runner.is_running))


@router.post("/api/worldkit/assets")
def assets_create(b: dict):
    return _send(create(_lib(), b, get_character=CS.get, start=_start))


@router.get("/api/worldkit/assets/{aid}")
def assets_get(aid: str):
    return _send(get_asset(_lib(), aid, is_running=runner.is_running))


@router.get("/api/worldkit/assets/{aid}/file/{name}")
def assets_file(aid: str, name: str):
    got = asset_path(_lib(), aid, name)
    if got is None:
        raise HTTPException(404, "no such file")
    return FileResponse(got[0], media_type=got[1], headers={"Cache-Control": "no-store"})


@router.post("/api/worldkit/assets/{aid}/{verb}")
def assets_action(aid: str, verb: str, b: dict | None = None):
    return _send(action(_lib(), aid, verb, b or {}, start=_start, is_running=runner.is_running, cancel=runner.cancel))


@router.get("/api/worldkit/looks")
def looks_get():
    return _send(looks_payload())


@router.get("/api/worldkit/characters")
def characters_get():
    return _send(characters_payload(CS.all_saved(), sheet_running=_sheet_running))


@router.post("/api/worldkit/characters")
def characters_post(payload: dict):
    """A new saved character, from words only: there is no upload here and never will be. Its sheet is then made and checked on a background thread."""
    return _send(new_character(payload, start=_start_sheet))


@router.post("/api/worldkit/characters/{cid}/again")
def characters_again(cid: str):
    return _send(character_again(cid, start=_start_sheet, sheet_running=_sheet_running))


@router.get("/api/worldkit/characters/{cid}/sheet")
def characters_sheet(cid: str):
    p = character_sheet_path(cid)
    if p is None:
        raise HTTPException(404, "no sheet")
    return FileResponse(p, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.delete("/api/worldkit/characters/{cid}")
def characters_delete(cid: str):
    if _sheet_running(cid):
        return _send(_err(409, "this character's sheet is being made now"))
    return _send((200, {"ok": True}) if CS.delete(cid) else _err(404, "no such saved character"))


@router.get("/api/worldkit/capabilities")
def capabilities_get():
    """What each maker needs and whether it is here: a real file check on every call, because models arrive by download."""
    return C.report()


@router.get("/api/worldkit/meshes")
def meshes_get():
    """Studio 3D results that can become a prop: the same list as the 3D page."""
    from pathlib import Path

    from psn import paths
    from studio import glb
    root = Path(paths.output_dir(True))
    return {"items": [m["path"] for m in glb.list_glb(str(root))]}


@router.post("/api/worldkit/export")
def export_post(b: dict | None = None):
    return _send(export_pack(_lib(), b or {}))


@router.get("/api/worldkit/exports")
def exports_get():
    return _send(exports_payload(_lib()))


@router.get("/api/worldkit/exports/{name}")
def export_file(name: str):
    p = X.zip_path(_lib(), name)
    if p is None:
        raise HTTPException(404, "no such export")
    return FileResponse(p, media_type="application/zip", filename=name)
