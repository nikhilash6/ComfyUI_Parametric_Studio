"""Rendering a shot: the Blender passes (a local step on the CPU), the mode's ComfyUI jobs (the last is "video"), then QC (local). A failed video or a failed QC gets ONE automatic reroll with a new seed; the passes and keyframes are kept, only the video reruns, and shot.json
records the seed that made the final video. Then the shot waits for review (state "review"); a video that fails twice is "failed". QC that cannot run sends the shot to review without a reroll. A shot whose assets changed since it was saved is refused before any work.
"Passes only" stops after the scene step: it needs Blender and nothing else. A list renders its shots in order, then scores set consistency across them. One live thread per shot or list; the state is state.json, and a restart leaves "building" with no thread: the page shows it interrupted and Retry resumes."""
from __future__ import annotations

import logging
import threading
import time

from studio import worldkit
from studio.vset import shot as SH
from studio.vset import shotlist as SL
from studio.worldkit import blender as B
from studio.worldkit import jobs
from studio.worldkit import steps as S

REROLLS = 1
_THREADS: dict[str, threading.Thread] = {}
_CANCELS: dict[str, threading.Event] = {}
_LOCK = threading.Lock()
log = logging.getLogger(__name__)


def seams(cancel=None, work=None) -> dict:
    """How a render talks to the studio's job flow. Tests hand in their own."""
    stop = (lambda: cancel.is_set()) if cancel is not None else None
    return {"submit": jobs.submit, "wait": lambda jid: jobs.wait(jid, work=work, cancelled=stop), "to_input": jobs.to_input}


def _anchor(ctx: dict, shot: dict) -> str:
    """The saved character's sheet, only when there is a cast and a face classifier was handed in."""
    if not ctx.get("classify") or not shot.get("cast"):
        return ""
    from studio.worldkit import characters as CS
    cid = str((ctx["library"].require(shot["cast"][0]["asset"]).get("source") or {}).get("character_id") or "")
    ch = CS.get(cid)
    return str(ch.sheet()) if ch is not None and ch.sheet().is_file() else ""


def _qc(ctx: dict, shot: dict) -> dict:
    from studio.vset import qc
    try:
        work = SH.shot_dir(shot["id"], ctx.get("root")) / "qc"
        edges = str((ctx["outputs"].get("scene", {}).get("edges") or {}).get("path") or "")
        return {**qc.judge(S.out_path(ctx, "video"), work=work, anchor=_anchor(ctx, shot), classify=ctx.get("classify"), edges=edges), "checked": True}
    except Exception as exc:          # QC that cannot run sends the shot to review, never to a reroll
        return {"ok": False, "checked": False, "reasons": [f"QC could not run: {type(exc).__name__}: {exc}"[:400]]}


def steps_for(shot: dict, *, library, passes_only: bool = False) -> list[S.Step]:
    from studio.vset import modes
    from studio.vset.modes import common
    if passes_only:
        return [common.scene_step(shot)]
    return [common.scene_step(shot), *modes.steps(shot, library=library), S.Step("qc", "Quality check", local=lambda ctx: {"main": _qc(ctx, shot)})]


def run_shot(sid: str, *, library, seams_: dict | None = None, root=None, cancel=None, passes_only: bool = False) -> dict:
    shot = SH.load(sid, root)
    state = SH.load_state(sid, root)
    bad = SH.problems(shot, library=library)
    if bad:
        state = {**state, "state": "failed", "error": "the shot cannot render: " + "; ".join(bad)}
        SH.save_state(sid, state, root)
        return state
    s = seams_ if seams_ is not None else seams(cancel, worldkit.work_root() / "_vset" / sid)
    stopped = (lambda: cancel.is_set()) if cancel is not None else None
    rerolls = int(state.get("rerolls") or 0)
    with B.cancel_scope(cancel):
        while True:
            def save(st, _r=rerolls, _seed=shot["seed"]):
                SH.save_state(sid, {**st, "rerolls": _r, "seed": _seed, "scope": "passes" if passes_only else "video"}, root)

            ctx = {"library": library, "seed": shot["seed"], "root": root, **s}
            state = S.run(state, steps_for(shot, library=library, passes_only=passes_only), ctx=ctx, submit=s["submit"], wait=s["wait"], save=save, cancelled=stopped)
            recs = {r["name"]: r for r in state["steps"]}
            qrec = recs.get("qc") or {}
            qc_out = (qrec.get("outputs") or {}).get("main") if qrec.get("status") == "done" else None
            video_failed = state["state"] == "failed" and (recs.get("video") or {}).get("status") == "failed"
            qc_failed = state["state"] == "done" and qc_out is not None and not qc_out.get("ok")
            state.update(rerolls=rerolls, seed=shot["seed"], qc=qc_out, scope="passes" if passes_only else "video")
            if not (video_failed or qc_failed) or (cancel is not None and cancel.is_set()):
                break
            if (qc_failed and qc_out.get("checked") is False) or rerolls >= REROLLS:
                state["state"] = "review" if qc_failed else "failed"
                break
            rerolls += 1
            shot = SH.save({**shot, "seed": (shot["seed"] + 1) % 2 ** 32}, root)
            state = S.reset_from(state, "video")
    SH.save_state(sid, state, root)
    return state


def run_list(lid: str, *, library, seams_: dict | None = None, root=None) -> dict:
    from studio.vset import qc
    lst = SL.load_list(lid, root)
    results = {sid: run_shot(sid, library=library, seams_=seams_, root=root).get("state") for sid in lst["shots"]}
    firsts = {}
    try:
        for sid in lst["shots"]:
            st = SH.load_state(sid, root)
            video = (S.outputs(st).get("video") or {}).get("main") if st.get("steps") else None
            if video and st.get("state") in ("done", "review"):
                firsts[sid] = qc.sample_frames(video["path"], SH.shot_dir(sid, root) / "consistency", n=4)
        consistency = qc.list_consistency(firsts)
    except Exception as exc:          # the shots stand; the score says why it is missing
        consistency = {"scores": {}, "min": None, "ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
    lst["state"] = {"shots": results, "consistency": consistency, "updated": time.time()}
    SL.save_list(lst, root)
    return lst["state"]


def is_running(key: str) -> bool:
    with _LOCK:
        t = _THREADS.get(key)
        return t is not None and t.is_alive()


def cancel(key: str) -> bool:
    with _LOCK:
        ev = _CANCELS.get(key)
    if ev is None:
        return False
    ev.set()
    return True


def _start(key: str, fn) -> threading.Thread:
    ev = threading.Event()

    def target():
        try:
            fn(ev)
        except Exception:             # a crash outside a step must not die silently
            log.exception("Virtual Set %s crashed", key)
        finally:
            with _LOCK:
                if _THREADS.get(key) is threading.current_thread():
                    del _THREADS[key]
                    _CANCELS.pop(key, None)
    with _LOCK:
        t = _THREADS.get(key)
        if t is not None and t.is_alive():
            return t
        t = threading.Thread(target=target, daemon=True, name=f"vset-{key}")
        _THREADS[key], _CANCELS[key] = t, ev
        t.start()
        return t


def start_shot(sid: str, *, library, seams_: dict | None = None, root=None, passes_only: bool = False) -> threading.Thread:
    return _start(f"shot:{sid}", lambda ev: run_shot(sid, library=library, seams_=seams_, root=root, cancel=ev, passes_only=passes_only))


def start_list(lid: str, *, library, seams_: dict | None = None, root=None) -> threading.Thread:
    return _start(f"list:{lid}", lambda ev: run_list(lid, library=library, seams_=seams_, root=root))
