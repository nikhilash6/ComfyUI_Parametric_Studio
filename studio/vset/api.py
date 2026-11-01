"""/api/vset/*: shots, shot lists, the camera preview and what each mode needs. Route logic is in plain functions that return (status, body), so each is tested without a server, ComfyUI or a GPU; the router below is the thin FastAPI layer. Running keys are "shot:<id>" and "list:<id>"."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from studio.vset import camera, needs, passes, runner
from studio.vset import shot as SH
from studio.vset import shotlist as SL
from studio.worldkit import library as L
from studio.worldkit import capabilities as C
from studio.worldkit import looks, safety
from studio.worldkit import steps as S

router = APIRouter()
FIELDS = ("name", "session_id", "set", "cast", "marks", "camera", "format", "look", "mode", "mode_settings", "seed", "prompt")
#: The files of a shot that a page may ask for: never a path from a request. name -> (step, output key).
FILES = {**{k: ("scene", k) for k in (*passes.PASSES, "clay", *passes.STILLS)}, "key_first": ("key_first", "main"), "key_last": ("key_last", "main"), "video": ("video", "main")}
TYPES = {".mp4": "video/mp4", ".png": "image/png", ".webm": "video/webm"}


def _err(code: int, msg: str) -> tuple[int, dict]:
    return code, {"error": msg}


def _url(sid: str, name: str) -> str:
    return f"/api/vset/shots/{sid}/file/{name}"


def summary(shot: dict, state: dict, running: bool) -> dict:
    out = S.outputs(state) if state.get("steps") else {}
    steps = state.get("steps") or []
    failed = next((r["name"] for r in steps if r["status"] == "failed"), "")
    return {"id": shot["id"], "name": shot.get("name", ""), "mode": shot["mode"], "camera": shot["camera"]["preset"], "format": shot["format"], "prompt": shot.get("prompt", ""), "seed": shot.get("seed"),
            "state": state.get("state", "new"), "error": state.get("error", ""), "rerolls": state.get("rerolls", 0), "qc": state.get("qc"), "running": bool(running), "failed_step": failed,
            "progress": [sum(1 for r in steps if r["status"] in ("done", "skipped")), len(steps)], "scope": state.get("scope", ""),
            "video_url": _url(shot["id"], "video") if out.get("video") else "", "passes": {k: _url(shot["id"], k) for k in (out.get("scene") or {})},
            "keyframes": {k: _url(shot["id"], k) for k in ("key_first", "key_last") if out.get(k)}, "engine": ((out.get("scene") or {}).get("shaded") or {}).get("engine", "")}


def meta_payload() -> tuple[int, dict]:
    return 200, {"modes": SH.MODE_SPECS, "wan": {k: SH.WAN_SPEC[k] for k in ("fps", "frames", "seconds", "aspects")}, "ltx": {k: SH.LTX_SPEC[k] for k in ("fps", "frames", "seconds", "aspects")}, "presets": list(camera.PRESETS), "defaults": camera.DEFAULTS, "easings": list(camera.EASINGS), "aspects": list(SH.ASPECTS),
                 "controls": list(SH.CONTROLS), "engines": list(SH.ENGINES), "keyframes": list(SH.KEYFRAMES), "looks": looks.public(), "lens_mm": camera.LENS_MM, "sensor_mm": camera.SENSOR_MM}


def camera_preview(payload, *, library) -> tuple[int, dict]:
    shot = payload.get("shot") if isinstance(payload, dict) else None
    if not isinstance(shot, dict) or shot.get("mode") not in SH.MODES:
        return _err(400, "send a shot with a mode")
    bad = camera.problems(shot.get("camera"))
    cast = shot.get("cast") or []
    if not all(isinstance(c, dict) and isinstance(c.get("marks"), list) and c["marks"] for c in cast):
        bad.append("each cast member needs marks")
    marks = None
    if not bad:
        marks = SH.subject_marks(shot)
        if not (isinstance(marks, list) and marks and all(isinstance(m, list) and len(m) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in m) for m in marks)):
            bad.append("the marks are a path of [x, y] points")
    try:
        n, size = SH.frames(shot), SH.size(shot)
    except (KeyError, TypeError, ValueError):
        bad.append("the format needs an aspect and seconds")
    if bad:
        return _err(400, "; ".join(bad))
    place = library.get(str((shot.get("set") or {}).get("place") or ""))
    ins = (place or {}).get("inspect") or {}
    keys = camera.keys(shot["camera"], marks, n, seed=int(shot.get("seed") or 0))
    return 200, {"keys": keys, "fps": SH.fps(shot), "size": list(size), "frames": n, "sensor_mm": camera.SENSOR_MM, "subject": [list(p) for p in camera.along(marks, n)],
                 "cast": [[list(p) for p in camera.along(c["marks"], n)] for c in cast], "bounds": {"lo": ins["lo"], "hi": ins["hi"]} if ins.get("lo") else None}


def route_of(shot: dict) -> str:
    """The route in the capability report that a shot used. The page's routeName does the same for a form."""
    mode, ms = shot.get("mode"), shot.get("mode_settings") or {}
    if mode == "A" and ms.get("engine") == "wan":
        return "A_wan"
    if mode == "A" and ms.get("engine") == "ltx":
        return "A_ltx_raw" if ms.get("keyframes") == "raw" else "A_ltx"
    if mode == "C" and ms.get("keyframes") == "raw":
        return "C_raw"
    return str(mode)


NO_PROOF = {"state": "none", "passed": 0, "review": 0, "failed": 0, "running": 0, "shot": ""}


def route_proofs(*, is_running, root=None) -> dict:
    """What each route has actually done here, read from the shots on disk on every call. "passed" means a video exists and the automatic checks (flicker, face when one ran) found nothing: it does not judge the picture. Passes-only renders say nothing about a video route."""
    out: dict = {}
    for shot in SH.list_shots(root):
        state = SH.load_state(shot["id"], root)
        video = next((r for r in state.get("steps") or [] if r.get("name") == "video" and r.get("status") == "done"), None)
        have = bool(video and Path(((video.get("outputs") or {}).get("main") or {}).get("path") or "").is_file())
        if is_running(f"shot:{shot['id']}"):
            kind = "running"
        elif state.get("scope") == "passes":
            continue
        elif state.get("state") == "done" and have and (state.get("qc") or {}).get("ok"):
            kind = "passed"
        elif state.get("state") in ("done", "review") and have:
            kind = "review"
        elif state.get("state") == "failed":
            kind = "failed"
        else:
            continue
        row = out.setdefault(route_of(shot), dict(NO_PROOF))
        row[kind] += 1
        if not row["shot"] or (kind == "passed" and row["passed"] == 1):        # newest first: link the newest shot that passed, else the newest
            row["shot"] = shot["id"]
    for row in out.values():
        row["state"] = next(k for k in ("passed", "review", "running", "failed") if row[k])
    return out


def with_proof(report: dict, proofs: dict) -> dict:
    routes = {k: {**r, "proof": proofs.get(k, dict(NO_PROOF))} for k, r in (report.get("routes") or {}).items()}
    return {**report, "routes": routes}


def list_shots(*, is_running, root=None) -> tuple[int, dict]:
    return 200, {"shots": [summary(s, SH.load_state(s["id"], root), is_running(f"shot:{s['id']}")) for s in SH.list_shots(root)]}


def get_shot(sid: str, *, is_running, root=None) -> tuple[int, dict]:
    try:
        shot = SH.load(sid, root)
    except SH.ShotError:
        return _err(404, "no such shot")
    state = SH.load_state(sid, root)
    return 200, {"shot": shot, "state": state, "summary": summary(shot, state, is_running(f"shot:{sid}"))}


def save_shot(payload, *, library, is_running, root=None) -> tuple[int, dict]:
    given = payload.get("shot") if isinstance(payload, dict) else None
    if not isinstance(given, dict):
        return _err(400, "send {shot: {...}}")
    sid, fields = given.get("id"), {k: given[k] for k in FIELDS if k in given}
    old = None
    if sid:
        try:
            old = SH.load(sid, root)
        except SH.ShotError:
            old = None
        if old is not None and is_running(f"shot:{sid}"):
            return _err(409, "this shot is rendering now")
    shot = {**old, **fields} if old is not None else SH.new_shot(**fields)
    bad = SH.problems(shot, library=library)
    if bad:
        return _err(400, "; ".join(bad))
    shot = SH.save(shot, root)
    SH.save_state(shot["id"], {}, root)                     # an edited shot renders fresh
    return 200, {"shot": shot}


def _kept_passes(state: dict) -> dict:
    """A new render keeps finished passes: the shot has not changed since they were made, because saving a shot clears its state."""
    rec = next((r for r in state.get("steps") or [] if r["name"] == "scene" and r["status"] == "done"), None)
    if rec is None or not all(Path(o["path"]).is_file() for o in rec["outputs"].values()):
        return {}
    return {"steps": [rec], "state": "pending", "error": "", "rerolls": 0}


def render_shot(sid: str, *, library, start, is_running, root=None, passes_only: bool = False, capability=needs.render_problems) -> tuple[int, dict]:
    try:
        shot = SH.load(sid, root)
    except SH.ShotError:
        return _err(404, "no such shot")
    if is_running(f"shot:{sid}"):
        return _err(409, "this shot is rendering now")
    bad = SH.problems(shot, library=library)
    if bad:
        return _err(400, "; ".join(bad))
    if passes_only:
        why = C.blender_problem()
        if why:
            return _err(409, why)
        state = {}
    else:
        why = capability(shot)
        if why:
            return _err(409, " ".join(why))
        state = _kept_passes(SH.load_state(sid, root))
    SH.save_state(sid, state, root)
    start(sid, passes_only)
    return 200, {"shot": summary(shot, state, True)}


def retry_shot(sid: str, *, start, is_running, root=None) -> tuple[int, dict]:
    try:
        shot = SH.load(sid, root)
    except SH.ShotError:
        return _err(404, "no such shot")
    if is_running(f"shot:{sid}"):
        return _err(409, "this shot is rendering now")
    state = SH.load_state(sid, root)
    if not state.get("steps"):
        return _err(400, "render the shot first")
    SH.save_state(sid, {**S.retry(state), "rerolls": 0}, root)
    start(sid, state.get("scope") == "passes")
    return 200, {"shot": summary(shot, SH.load_state(sid, root), True)}


def cancel_shot(sid: str, *, is_running, cancel) -> tuple[int, dict]:
    if not is_running(f"shot:{sid}") or not cancel(f"shot:{sid}"):
        return _err(409, "this shot is not rendering")
    return 200, {"cancelled": True}


def shot_file(sid: str, name: str, root=None):
    """(path, content type) of one of a shot's outputs, or None. The name is matched against a fixed list, and the path comes from the shot's own state, never from the request."""
    if name not in FILES or not L.valid_id(sid):
        return None
    step, key = FILES[name]
    state = SH.load_state(sid, root)
    o = (S.outputs(state).get(step) or {}).get(key) if state.get("steps") else None
    if not o or not o.get("path"):
        return None
    p = Path(o["path"])
    return (p, TYPES.get(p.suffix.lower(), "application/octet-stream")) if p.is_file() else None


def create_list(payload, *, library, root=None) -> tuple[int, dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("base"), dict):
        return _err(400, "send {name, script, base}")
    name, script = str(payload.get("name") or "Shot list"), str(payload.get("script") or "")
    bad = safety.text_problem(name, script)
    if bad:
        return _err(400, bad)
    try:
        shots = SL.from_script(script, base=payload["base"], name=name)
    except (ValueError, TypeError) as exc:
        return _err(400, str(exc))
    for i, s in enumerate(shots, 1):
        bad = SH.problems(s, library=library)
        if bad:
            return _err(400, f"shot {i}: " + "; ".join(bad))
    for s in shots:
        SH.save(s, root)
    return 200, {"list": SL.save_list(SL.new_list(name, [s["id"] for s in shots], base=payload["base"], script=script), root)}


def get_list(lid: str, *, is_running, root=None) -> tuple[int, dict]:
    try:
        lst = SL.load_list(lid, root)
    except SH.ShotError:
        return _err(404, "no such list")
    shots = []
    for sid in lst["shots"]:
        try:
            shots.append(summary(SH.load(sid, root), SH.load_state(sid, root), is_running(f"shot:{sid}")))
        except SH.ShotError:
            continue
    return 200, {"list": lst, "shots": shots, "running": bool(is_running(f"list:{lid}"))}


def list_lists(root=None) -> tuple[int, dict]:
    return 200, {"lists": [{"id": x["id"], "name": x["name"], "shots": len(x["shots"]), "state": x.get("state", {})} for x in SL.list_lists(root)]}


def order_list(lid: str, ids, root=None) -> tuple[int, dict]:
    try:
        lst = SL.load_list(lid, root)
    except SH.ShotError:
        return _err(404, "no such list")
    if not isinstance(ids, list) or sorted(map(str, ids)) != sorted(lst["shots"]):
        return _err(400, "send every shot id of the list, in the new order")
    return 200, {"list": SL.save_list({**lst, "shots": list(ids)}, root)}


def render_list(lid: str, *, library, start_list, is_running, root=None, capability=needs.render_problems) -> tuple[int, dict]:
    try:
        lst = SL.load_list(lid, root)
    except SH.ShotError:
        return _err(404, "no such list")
    if is_running(f"list:{lid}"):
        return _err(409, "this list is rendering now")
    for sid in lst["shots"]:
        try:
            shot = SH.load(sid, root)
        except SH.ShotError:
            return _err(400, f"the list names a shot that is gone: {sid}")
        why = SH.problems(shot, library=library) or capability(shot)
        if why:
            return _err(409, " ".join(why))
    start_list(lid)
    return 200, {"list": lst}


# ---------- routes
def _lib():
    return L.Library()


def _send(res):
    code, body = res
    if code >= 400:
        raise HTTPException(code, body.get("error") or "refused")
    return body


def _start(sid: str, passes_only: bool = False) -> None:
    runner.start_shot(sid, library=_lib(), passes_only=passes_only)


def _start_list(lid: str) -> None:
    runner.start_list(lid, library=_lib())


@router.get("/api/vset/meta")
def meta_get():
    return _send(meta_payload())


@router.get("/api/vset/capabilities")
def capabilities_get():
    """What each mode needs and whether it is here: a real file check on every call, because models arrive by download. Each route also says what its shots on this machine have shown so far."""
    return with_proof(needs.report(), route_proofs(is_running=runner.is_running))


@router.post("/api/vset/camera")
def camera_post(b: dict):
    return _send(camera_preview(b, library=_lib()))


@router.get("/api/vset/shots")
def shots_get():
    return _send(list_shots(is_running=runner.is_running))


@router.post("/api/vset/shots")
def shots_post(b: dict):
    body = _send(save_shot(b, library=_lib(), is_running=runner.is_running))
    if b.get("render"):
        _send(render_shot(body["shot"]["id"], library=_lib(), start=_start, is_running=runner.is_running, passes_only=b.get("render") == "passes"))
    return body


@router.get("/api/vset/shots/{sid}")
def shot_get(sid: str):
    return _send(get_shot(sid, is_running=runner.is_running))


@router.get("/api/vset/shots/{sid}/file/{name}")
def shot_file_get(sid: str, name: str):
    got = shot_file(sid, name)
    if got is None:
        raise HTTPException(404, "no such file")
    return FileResponse(got[0], media_type=got[1], headers={"Cache-Control": "no-store"})


@router.post("/api/vset/shots/{sid}/{verb}")
def shot_action(sid: str, verb: str):
    if verb in ("render", "passes"):
        return _send(render_shot(sid, library=_lib(), start=_start, is_running=runner.is_running, passes_only=verb == "passes"))
    if verb == "retry":
        return _send(retry_shot(sid, start=_start, is_running=runner.is_running))
    if verb == "cancel":
        return _send(cancel_shot(sid, is_running=runner.is_running, cancel=runner.cancel))
    raise HTTPException(404, f"no action {verb!r}")


@router.get("/api/vset/lists")
def lists_get():
    return _send(list_lists())


@router.post("/api/vset/lists")
def lists_post(b: dict):
    return _send(create_list(b, library=_lib()))


@router.get("/api/vset/lists/{lid}")
def list_get(lid: str):
    return _send(get_list(lid, is_running=runner.is_running))


@router.post("/api/vset/lists/{lid}/{verb}")
def list_action(lid: str, verb: str, b: dict | None = None):
    if verb == "order":
        return _send(order_list(lid, (b or {}).get("ids")))
    if verb == "render":
        return _send(render_list(lid, library=_lib(), start_list=_start_list, is_running=runner.is_running))
    raise HTTPException(404, f"no action {verb!r}")
