"""One background build per asset: the maker's steps, then the preview and the ingest, run by steps.run; the state is meta["build"]. A server restart leaves "building" with no thread: the UI shows it
interrupted and Retry resumes (steps.run waits on recorded jobs and resubmits interrupted ones)."""
from __future__ import annotations

import logging
import threading

from studio import worldkit
from studio.worldkit import blender as B
from studio.worldkit import jobs, preview
from studio.worldkit import steps as S
from studio.worldkit.makers import character, place, prop

MAKERS = {"character": character, "prop": prop, "place": place}
_THREADS: dict[str, threading.Thread] = {}
_CANCELS: dict[str, threading.Event] = {}
_LOCK = threading.Lock()
log = logging.getLogger(__name__)


def build_steps(meta: dict) -> list[S.Step]:
    maker = MAKERS.get(meta["type"])
    return [*(maker.steps(meta) if maker else []), *preview.steps(meta)]


def seams(cancel=None, work=None) -> dict:
    """How a build talks to the studio's job flow. Tests hand in their own."""
    stop = (lambda: cancel.is_set()) if cancel is not None else None
    return {"submit": jobs.submit, "wait": lambda jid: jobs.wait(jid, work=work, cancelled=stop)}


def run_build(aid: str, *, library, seams_: dict | None = None, cancel=None) -> dict:
    meta = library.require(aid)

    def save(state):
        library.update(aid, build=state)

    try:
        steps_ = build_steps(meta)
    except ValueError as exc:
        state = {**(meta.get("build") or {}), "state": "failed", "error": f"recipe: {exc}"}
        save(state)
        return state
    work = worldkit.work_root() / aid
    work.mkdir(parents=True, exist_ok=True)
    s = seams_ if seams_ is not None else seams(cancel, work / "_downloads")
    ctx = {"asset": meta, "library": library, "work": work, **s}
    with B.cancel_scope(cancel):
        return S.run(meta.get("build"), steps_, ctx=ctx, submit=s["submit"], wait=s["wait"], save=save,
                     cancelled=(lambda: cancel.is_set()) if cancel is not None else None)


def is_running(aid: str) -> bool:
    with _LOCK:
        t = _THREADS.get(aid)
        return t is not None and t.is_alive()


def cancel(aid: str) -> bool:
    with _LOCK:
        ev = _CANCELS.get(aid)
    if ev is None:
        return False
    ev.set()
    return True


def _target(aid: str, library, seams_, ev) -> None:
    try:
        run_build(aid, library=library, seams_=seams_, cancel=ev)
    except Exception:  # a crash outside a step must not die silently
        log.exception("World Kit build %s crashed", aid)
        try:
            meta = library.require(aid)
            library.update(aid, build={**meta["build"], "state": "failed", "error": "the build crashed; see the studio's log"})
        except Exception:
            pass
    finally:
        with _LOCK:
            if _THREADS.get(aid) is threading.current_thread():
                del _THREADS[aid]
                _CANCELS.pop(aid, None)


def start(aid: str, *, library, seams_: dict | None = None) -> threading.Thread:
    with _LOCK:
        t = _THREADS.get(aid)
        if t is not None and t.is_alive():
            return t
        ev = threading.Event()
        t = threading.Thread(target=_target, args=(aid, library, seams_, ev), daemon=True, name=f"worldkit-{aid}")
        _THREADS[aid], _CANCELS[aid] = t, ev
        t.start()
        return t
