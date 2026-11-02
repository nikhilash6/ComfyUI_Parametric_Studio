"""Resumable build steps. A build is an ordered list of steps; each is a ComfyUI job (request -> submit -> wait -> pick the outputs) or a
local step (Blender, ffmpeg, a tool, file work). The state lives in the asset's meta["build"], so a failed rig keeps the mesh, the error
names the step ("Rig: ..."), and retry reruns only what did not finish.

A restart mid-step: a recorded ComfyUI job is waited on again (never a second submit while it lives); a job that came back "interrupted" is
resubmitted, at most once. A local step that was running simply runs again: its work folder holds nothing a rerun can trust."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

STATES = ("pending", "running", "done", "failed", "skipped")
MAX_ATTEMPTS = 2                  # the first submit plus one resubmit of an interrupted job


class StepError(RuntimeError):
    pass


@dataclass(frozen=True)
class Step:
    name: str
    label: str
    request: Callable[[dict], dict | None] | None = None
    pick: Callable[[list, dict], dict] | None = None
    local: Callable[[dict], dict | None] | None = None
    optional: bool = False


def _record(name: str) -> dict:
    return {"name": name, "status": "pending", "job_id": "", "outputs": {}, "error": "", "note": "", "attempts": 0,
            "updated": 0.0}


def new_state(names) -> dict:
    return {"state": "pending", "steps": [_record(n) for n in names], "error": ""}


def _pending(rec: dict, note: str = "") -> dict:
    return {**rec, "status": "pending", "job_id": "", "outputs": {}, "error": "", "note": note, "attempts": 0}


def sync(state: dict | None, names) -> dict:
    """The state for this list of steps: records kept by name; new names pending; from the first position where the
    list differs from the old one, every finished step becomes pending again (an earlier step changed)."""
    state = dict(state or {})
    old = [r for r in state.get("steps") or [] if isinstance(r, dict) and r.get("name")]
    by = {r["name"]: r for r in old}
    out, stale = [], False
    for i, n in enumerate(names):
        if i >= len(old) or old[i]["name"] != n:
            stale = True
        rec = dict(by.get(n) or _record(n))
        if stale and n in by and rec["status"] in ("done", "failed", "skipped"):
            rec = _pending(rec, "stale: an earlier step changed")
        out.append(rec)
    done = bool(out) and all(r["status"] in ("done", "skipped") or (r["status"] == "failed" and "optional" in r["note"])
                             for r in out)
    return {**state, "steps": out, "state": state.get("state", "pending") if done else "pending",
            "error": state.get("error", "") if done else ""}


def reset_from(state: dict, name: str) -> dict:
    names = [r["name"] for r in state["steps"]]
    i = names.index(name)
    steps = [r if k < i else _pending(r) for k, r in enumerate(state["steps"])]
    return {**state, "steps": steps, "state": "pending", "error": ""}


def retry(state: dict) -> dict:
    """Rerun what did not finish. A running record that holds a job_id is kept, so run() waits on that job instead of
    submitting a second one; failed, stale and pending records go back to pending."""
    steps = [r if r["status"] in ("done", "skipped") or (r["status"] == "running" and r.get("job_id"))
             else _pending(r) for r in state.get("steps") or []]
    return {**state, "steps": steps, "state": "pending", "error": ""}


def lost_motions(state: dict | None) -> list[str]:
    """Clips whose optional motion or fit failed, so the finished character has none of them. Only once the build has ended."""
    if not state or state.get("state") not in ("done", "failed"):
        return []
    return [r["name"].split("_", 1)[1] for r in state.get("steps") or [] if r["name"].startswith(("motion_", "retarget_")) and r["status"] == "failed"]


def retry_motion(state: dict, name: str, then: str) -> dict:
    """One lost clip again: its motion and fit, then everything from `then` on (the file has to be put together again). The other clips keep what they made."""
    mine = (f"motion_{name}", f"retarget_{name}")
    names = [r["name"] for r in state["steps"]]
    i = names.index(then)
    steps = [_pending(r) if r["name"] in mine or k >= i else r for k, r in enumerate(state["steps"])]
    return {**state, "steps": steps, "state": "pending", "error": ""}


def outputs(state: dict) -> dict:
    return {r["name"]: r["outputs"] for r in state.get("steps") or [] if r["status"] == "done"}


def out_path(ctx: dict, step: str, key: str = "main") -> str:
    return str(ctx["outputs"][step][key]["path"])


def _match(a: dict, suffix=(), media_type=()) -> bool:
    p = str(a.get("path") or "").lower()
    return (not suffix or p.endswith(tuple(suffix))) and (not media_type or a.get("media_type") in media_type)


def _found(i: int, a: dict) -> dict:
    return {"index": i, "path": str(a.get("path") or ""), **{k: v for k, v in a.items() if k != "path"}}


def pick_first(*, suffix=(), media_type=(), key: str = "main"):
    def pick(arts: list, ctx: dict) -> dict:
        for i, a in enumerate(arts):
            if _match(a, suffix, media_type):
                return {key: _found(i, a)}
        raise StepError(f"the job made no {'/'.join([*suffix, *media_type]) or 'usable'} output")
    return pick


def run(state: dict | None, steps: list[Step], *, ctx: dict, submit, wait, save, cancelled=None,
        clock=time.time) -> dict:
    by = {s.name: s for s in steps}
    state = sync(state, [s.name for s in steps])
    state.update(state="building", error="")
    save(state)
    for rec in state["steps"]:
        if rec["status"] in ("done", "skipped") or (rec["status"] == "failed" and "optional" in rec["note"]):
            continue
        if cancelled is not None and cancelled():
            state.update(state="failed", error="cancelled")
            save(state)
            return state
        step = by[rec["name"]]
        ctx["outputs"] = outputs(state)
        try:
            if step.local is not None:
                rec.update(status="running", updated=clock())
                save(state)
                out = step.local(ctx)
                rec.update(status="skipped" if out is None else "done", outputs=out or {}, error="", updated=clock())
                save(state)
                continue
            res = None
            if rec["status"] == "running" and rec["job_id"]:
                res = wait(rec["job_id"])             # a restart: the recorded job, never a second submit
                if res.get("status") == "interrupted" and rec["attempts"] < MAX_ATTEMPTS:
                    res = None
            if res is None:
                req = step.request(ctx)
                if req is None:
                    rec.update(status="skipped", updated=clock())
                    save(state)
                    continue
                rec.update(status="running", job_id="", error="", attempts=rec["attempts"] + 1, updated=clock())
                save(state)
                rec["job_id"] = submit(req)
                save(state)
                res = wait(rec["job_id"])
            if res.get("status") != "done":
                raise StepError(res.get("error") or f"the job ended {res.get('status')}")
            out = step.pick(res.get("artifacts") or [], ctx)
            for o in out.values():
                o["job_id"] = rec["job_id"]
            rec.update(status="done", outputs=out, error="", updated=clock())
            save(state)
        except Exception as exc:
            msg = str(exc) if isinstance(exc, (StepError, RuntimeError, ValueError)) else f"{type(exc).__name__}: {exc}"
            rec.update(status="failed", error=msg[:2000], updated=clock())
            if step.optional:
                rec["note"] = "optional: the build continues without it"
                save(state)
                continue
            state.update(state="failed", error=f"{step.label or step.name}: {msg}"[:2000])
            save(state)
            return state
    state.update(state="done", error="")
    save(state)
    return state
