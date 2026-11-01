"""Try-on and try-off for the Fashion designer: a person and a garment to the person wearing it, or a person to the garment alone. Each method says how it runs and what its licence lets you do; the first one ready is the default, and they are ordered by what they did on this box's own test, best first. One limited to non-commercial use says so.
A family method runs a template on its own ComfyUI, a runner method runs in its own process. Results land in the output folder's tryon/. Only invented people belong here: there is no face or identity input."""
import shutil, sys, threading, time, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psn import paths

ROOT = Path(__file__).resolve().parent; RUNNERS = ROOT / "worldkit" / "runners"
router = APIRouter(); JOBS: dict = {}
#: direction: on or off. commercial: False means the page labels it non-commercial. Ordered best first, from looking at each one on the same invented model and garments; the first one ready is the default.
METHODS = [
    {"id": "klein4b", "label": "FLUX.2 Klein 4B with the try-on LoRA", "direction": "on", "via": "family", "family": "Flux.2", "template": "klein4b_tryon", "person": "20", "garment": "30", "licence": "Klein 4B Apache-2.0; the LoRA is rent-only on Civitai, so check before selling pictures", "commercial": False, "note": "The cleanest on our tests: it replaced the whole outfit on both the coat and the dress and kept the face. 66 to 82 s, 21 GB."},
    {"id": "klein9b_lora", "label": "FLUX.2 Klein 9B with the try-on LoRA", "direction": "on", "via": "family", "family": "Flux.2", "template": "klein9b_tryon_lora", "person": "20", "garment": "30", "licence": "FLUX.2 Klein 9B licence; the LoRA is rent-only on Civitai", "commercial": False, "note": "Quicker than 4B and it replaced the whole outfit, but on our dress test the colour came out paler and the hem shorter. The LoRA was made for Base 9B and this runs on the distilled 9B. 43 s, 29 GB."},
    {"id": "qwen21", "label": "Qwen Image 2.1 + Outfit Swap", "direction": "on", "via": "family", "family": "Qwen-Image-2.1", "template": "qwen21_tryon", "person": "7", "garment": "17", "licence": "Qwen Image licence; the LoRA is rent-only on its source", "commercial": False, "note": "Best on our test: the coat kept its full length and buttons, the jeans and face stayed the same. 80 s, 28 GB."},
    {"id": "fashn", "label": "FASHN VTON 1.5", "direction": "on", "via": "runner", "runner": "fashn_tryon.py", "licence": "Apache-2.0", "commercial": True, "peak_gb": 8.0, "note": "Open licence and light: 32 s, 5.4 GB, 576 pixels. On our test it shortened a long coat and a dress. Say whether the garment is a top, bottoms or one piece."},
    {"id": "klein9b", "label": "FLUX.2 Klein 9B, two references", "direction": "on", "via": "family", "family": "Flux.2", "template": "klein9b_tryon", "person": "20", "garment": "30", "licence": "FLUX.2 Klein licence", "commercial": False, "note": "On our test it dressed the coat well but also recoloured the trousers to match. 41 s, 33 GB."},
    {"id": "qwen21_off", "label": "Qwen Image 2.1", "direction": "off", "via": "family", "family": "Qwen-Image-2.1", "template": "qwen21_tryoff", "person": "7", "licence": "Qwen Image licence", "commercial": True, "note": "A general edit model asked for a product shot of what the person wears. On our test: a clean white t-shirt, with a small label it made up. It invents what it cannot see."},
]


def method(mid):
    m = next((x for x in METHODS if x["id"] == mid), None)
    if not m: raise HTTPException(404, "no such try-on method")
    return m


def need(m):
    """'' when this method can run here, else why not."""
    if m["via"] == "family":
        from studio import families_api as F
        t = next((x for x in F._meta(m["family"]).get("templates", []) if x.get("name") == m["template"]), None)
        if t is None: return f"the template {m['template']} is missing"
        s = F.tpl_state(t, F.scan().get(m["family"], {}))
        return "" if s["ready"] else "needs " + ", ".join(x["name"] for x in s["missing"][:3])
    from studio.worldkit import capabilities as C
    root = C.models_root(); miss = [str(p) for p in _fashn_paths(root).values() if not Path(p).exists()]
    return "" if not miss else "needs " + ", ".join(Path(p).name for p in miss[:3])


def _fashn_paths(root):
    from psn import instances as I
    root = Path(root)
    return {"--code": Path(I.REPO_LIB) / "drphero__ComfyUI-FASHN-VTON", "--weights": root / "_by_repo" / "fashn-ai__fashn-vton-1.5", "--pose": root / "_complete_pipelines" / "FitDiT" / "dwpose", "--parser": root / "_by_repo" / "fashn-ai__fashn-human-parser"}


def default(direction, rows):
    """The first ready method for this direction. METHODS is ordered best first."""
    return next((r["id"] for r in rows if r["direction"] == direction and r["ready"]), "")


def listing(check=need):
    rows = []
    for m in METHODS:
        why = check(m); rows.append({k: m.get(k) for k in ("id", "label", "direction", "licence", "commercial", "note")} | {"ready": not why, "why_not": why})
    return rows


def _out(mid):
    d = Path(paths.output_dir(True)) / "tryon"; d.mkdir(parents=True, exist_ok=True)
    return d / f"{mid}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.png"


def _picture(name):
    from studio.worldkit.makers.prop import picture_path
    return picture_path(name)


def _run_family(m, person, garment, poll=time.sleep):
    """Both pictures into the family's input folder, then its template."""
    from psn import instances as I
    from studio import families_api as F
    from studio.worldkit import jobs
    info = F._ensure(m["family"]); d = Path(I.INSTANCES) / info["slug"] / "input"; d.mkdir(parents=True, exist_ok=True); values = {}
    for key, pic in (("person", person), ("garment", garment)):
        if pic is None: continue
        name = "tryon_" + uuid.uuid4().hex[:10] + Path(pic).suffix.lower(); shutil.copy2(pic, d / name); values[f"{m[key]}|image"] = name
    job = F.template_run(F._slug(m["family"]), m["template"], {"values": values})["job"]
    res = jobs.wait(f"{F._slug(m['family'])}/{job}")
    if res.get("status") != "done": raise RuntimeError(res.get("error") or f"{m['label']} ended {res.get('status')}")
    got = [Path(a["path"]) for a in res.get("artifacts") or [] if a.get("media_type") == "image"]
    if not got: raise RuntimeError(f"{m['label']} finished with no picture")
    return got[0]


def _run_runner(m, person, garment, b, out, log, run=None):
    from studio.worldkit import blender as B, capabilities as C, tools
    why = B.vram_problem(m.get("peak_gb", 8.0))
    if why: raise RuntimeError(f"{m['label']}: {why}. Nothing was evicted; try again when there is room.")
    args = [sys.executable, RUNNERS / m["runner"], "--person", person, "--garment", garment, "--out", out, "--category", b.get("category") or "tops", "--photo", b.get("photo") or "flat-lay", "--seed", int(b.get("seed") or 42)]
    for k, v in _fashn_paths(C.models_root()).items(): args += [k, v]
    return tools._made(Path(out), (run or tools.call)(args, log, 1200), m["label"], log)


def execute(m, b, work, *, runner=None, family=None):
    person = _picture(b.get("person") or ""); garment = _picture(b.get("garment") or "") if m["direction"] == "on" else None
    out = _out(m["id"])
    if m["via"] == "runner": return (runner or _run_runner)(m, person, garment, b, out, Path(work) / "tryon.log")
    src = (family or _run_family)(m, person, garment); shutil.copy2(src, out); return out


def _worker(rec, m, b):
    work = Path(paths.setting("STUDIO_WORLDKIT_WORK") or "/tmp") / "tryon" / rec["job"]; work.mkdir(parents=True, exist_ok=True); t0 = time.time()
    try:
        out = execute(m, b, work); rec.update(status="done", file=str(Path(out).relative_to(Path(paths.output_dir(True)))), seconds=round(time.time() - t0, 1))
    except Exception as e: rec.update(status="error", error=f"{e}"[:900])


@router.get("/api/tryon/methods")
def methods_get():
    rows = listing(); return {"methods": rows, "default": {"on": default("on", rows), "off": default("off", rows)}}


@router.post("/api/tryon/run")
def run_post(b: dict = None):
    b = b or {}; m = method(str(b.get("method") or "")); why = need(m)
    if why: raise HTTPException(409, f"{m['label']}: {why}")
    if not b.get("person") or (m["direction"] == "on" and not b.get("garment")): raise HTTPException(400, "give a picture of the person" + (" and the garment" if m["direction"] == "on" else ""))
    jid = "try-" + uuid.uuid4().hex[:10]; rec = {"job": jid, "method": m["id"], "status": "running", "started": time.time()}; JOBS[jid] = rec
    threading.Thread(target=_worker, args=(rec, m, b), daemon=True, name=f"tryon-{jid}").start(); return rec


@router.get("/api/tryon/jobs/{jid}")
def job_get(jid: str):
    r = JOBS.get(jid)
    if not r: raise HTTPException(404, "no such job")
    return r
