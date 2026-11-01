"""The bridge from a build step to the studio's own job flow. Three kinds of request:
  {"kind": "goal", ...}   the same call as POST /api/generate, on the main ComfyUI (a goal in studio/goals.py)
  {"kind": "graph", "template", "values", "label"}   a graph in workflows/ with ${names}, queued the same way and visible in GET /api/jobs/<id>
  {"kind": "family", "family", "template", "image"}   a family template on its own instance, through studio/families_api (its VRAM gate included)
wait() polls the job and hands back {"status", "error", "artifacts": [{"path", "media_type", ...}]}: a local file for each output."""
from __future__ import annotations

import json
import mimetypes
import os
import shutil
import sys
import time
import urllib.parse
import uuid
from pathlib import Path

from fastapi import HTTPException

from psn import paths

TIMEOUT_S = 6 * 3600
POLL_S = 3.0
VANISHED_S = 90.0          # no history and no queue entry for this long: the server restarted under the job
PORTABLE_MATCH = 0.94      # the same file under another folder or a small rename. Lower than this, a missing wan2.2_fun_control maps onto wan2.2_fun_camera, which is a different model.
IMAGE = (".png", ".jpg", ".jpeg", ".webp")
VIDEO = (".mp4", ".webm", ".mov", ".gif")


def server():
    """The running studio module. Run with `python -m studio.server` it is __main__: a second import would be a second app."""
    main = sys.modules.get("__main__")
    if main is not None and hasattr(main, "_generate"):
        return main
    from studio import server as S
    return S


def goal(goal_id: str, prompt: str, options: dict | None = None, seed: int | None = None, image: str = "") -> dict:
    return {"kind": "goal", "goal": goal_id, "prompt": prompt, "options": dict(options or {}), **({"seed": seed} if seed is not None else {}), **({"image": image} if image else {})}


def graph(template: str, values: dict, label: str) -> dict:
    return {"kind": "graph", "template": template, "values": dict(values), "label": label}


def family(family_name: str, template: str, image: str = "") -> dict:
    return {"kind": "family", "family": family_name, "template": template, "image": image}


def _detail(e: HTTPException) -> str:
    return str(e.detail)[:800]


def to_input(path, stem: str = "") -> str:
    """Put a local picture or clip in ComfyUI's input folder (the live upload route); its name there."""
    S = server(); p = Path(path)
    return S._upload(p.read_bytes(), stem + p.name, mimetypes.guess_type(p.name)[0])["name"]


def _submit_graph(req: dict) -> str:
    from studio.graph_template import fill
    S = server(); name = req["template"]
    tpl = json.load(open(os.path.join(S.WF, name), encoding="utf-8"))
    g = fill(tpl, req["values"])
    if not S.comfy_up():
        raise RuntimeError(f"ComfyUI is not reachable at {S.COMFY}")
    if req.get("portable"):
        try:
            from studio.names import resolve_names
            g, _ = resolve_names(g, S.comfy("/object_info", timeout=20), threshold=PORTABLE_MATCH)
        except Exception:
            pass
    res = S.comfy("/prompt", {"prompt": g, "client_id": S.CLIENT_ID})
    jid = res.get("prompt_id") if isinstance(res, dict) else None
    if not jid:
        raise RuntimeError("ComfyUI did not return a job")
    S.JOBS[jid] = {"goal": "worldkit", "prompt": req.get("label", name), "seed": None, "options": {}, "started": time.time()}
    return jid


def _family_image(info: dict, image: str, values: dict, tpl_path: str) -> None:
    """A template's LoadImage takes a name in the instance's own input folder."""
    from psn import instances as I
    d = Path(I.INSTANCES) / info["slug"] / "input"
    d.mkdir(parents=True, exist_ok=True)
    name = "wk_" + uuid.uuid4().hex[:10] + Path(image).suffix.lower()
    shutil.copy2(image, d / name)
    ui = json.load(open(tpl_path, encoding="utf-8"))
    if "nodes" not in ui:                                    # the studio's own templates are API graphs: node id -> class_type
        nid = next((k for k, n in ui.items() if isinstance(n, dict) and n.get("class_type") == "LoadImage"), None)
    else:
        nid = next((n["id"] for n in ui["nodes"] if n.get("type") == "LoadImage"), None)
    if nid is None:
        raise RuntimeError("this template has no picture input")
    values[f"{nid}|image"] = name


def _submit_family(req: dict) -> str:
    from studio import families_api as F
    fam = req["family"]; tid = req["template"]; slug = F._slug(fam); values: dict = {}
    if req.get("image"):
        _, path = F._tpl(fam, tid)
        _family_image(F._ensure(fam), req["image"], values, path)
    return f"{slug}/{F.template_run(slug, tid, {'values': values})['job']}"


def submit(req: dict) -> str:
    try:
        if req["kind"] == "goal":
            return server()._generate({k: v for k, v in req.items() if k != "kind"})["job"]
        if req["kind"] == "graph":
            return _submit_graph(req)
        if req["kind"] == "family":
            return _submit_family(req)
    except HTTPException as e:
        raise RuntimeError(_detail(e)) from None
    raise ValueError(f"unknown job kind {req.get('kind')!r}")


def _media(name: str) -> str:
    n = name.lower()
    return "image" if n.endswith(IMAGE) else "video" if n.endswith(VIDEO) else "file"


def _main_files(rows: list[dict], work: Path) -> list[dict]:
    """Outputs of the main ComfyUI: the file itself when this machine can see it, otherwise a copy through its /view."""
    S = server(); out = []
    for r in rows:
        if r.get("type", "output") != "output":
            continue
        p = Path(paths.output_dir(True)) / r.get("subfolder", "") / r["filename"]
        if not p.is_file():
            q = urllib.parse.urlencode({"filename": r["filename"], "subfolder": r.get("subfolder", ""), "type": "output"})
            work.mkdir(parents=True, exist_ok=True)
            p = work / r["filename"]
            p.write_bytes(S.comfy("/view?" + q, timeout=120, raw=True))
        out.append({"path": str(p), "media_type": _media(r["filename"])})
    return out


def wait(job_id: str, *, work: Path | None = None, timeout_s: float = TIMEOUT_S, poll_s: float = POLL_S, sleep=time.sleep, clock=time.monotonic, cancelled=None) -> dict:
    deadline = clock() + timeout_s
    work = Path(work) if work else Path(paths.setting("STUDIO_WORLDKIT_WORK") or ".") / "_downloads"
    slug, _, fam_job = job_id.partition("/")
    gone_since = None
    while True:
        if cancelled is not None and cancelled():
            _cancel(job_id, slug, fam_job)
            return {"status": "failed", "artifacts": [], "error": "cancelled"}
        if fam_job:
            from studio import families_api as F
            try:
                r = F.job_get(slug, fam_job)
            except HTTPException:
                return {"status": "interrupted", "artifacts": [], "error": f"family job {fam_job} is gone"}
            st = r.get("status")
            if st == "done":
                root = Path(F.I.INSTANCES) / slug / "output"
                return {"status": "done", "error": "", "artifacts": [{"path": str(root / x.get("subfolder", "") / x["filename"]), "media_type": _media(x["filename"])} for x in r.get("files") or [] if x.get("type", "output") == "output"]}
            if st in ("error", "refused"):
                return {"status": "failed", "artifacts": [], "error": str(r.get("error") or r.get("message") or st)[:800]}
        else:
            r = server().job(job_id)
            st = r.get("status")
            if st == "done":
                return {"status": "done", "error": "", "artifacts": _main_files(r.get("files") or [], work)}
            if st == "error":
                return {"status": "failed", "artifacts": [], "error": str(r.get("error") or "the job failed")[:800]}
            if st == "queued" and not r.get("position"):       # in neither the queue nor the history
                gone_since = gone_since if gone_since is not None else clock()
                if clock() - gone_since >= VANISHED_S:
                    return {"status": "interrupted", "artifacts": [], "error": "ComfyUI no longer knows this job; it may have restarted"}
            else:
                gone_since = None
        if clock() >= deadline:
            _cancel(job_id, slug, fam_job)
            return {"status": "failed", "artifacts": [], "error": f"timed out after {timeout_s:.0f} s waiting for the job"}
        sleep(poll_s)


def _cancel(job_id: str, slug: str, fam_job: str) -> None:
    try:
        if fam_job:
            from studio import families_api as F
            F.job_cancel(slug, fam_job)
        else:
            server().cancel(job_id)
    except Exception:
        pass
