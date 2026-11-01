"""The 3D page's models: make a mesh from a picture or words, rig a mesh, make a motion. Each model says how it runs (a family template on its own ComfyUI, a small runner in its own process, or a third-party tool), what it needs, and what this box has actually shown of it.
Results land in the output folder's 3d/ as .glb or .bvh, so the 3D page lists them and World Kit can take them as a prop. A model is offered only when its files are here; `proof` is recorded evidence, and a model nobody has run says so."""
import json, shutil, subprocess, sys, threading, time, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psn import paths

ROOT = Path(__file__).resolve().parent; RUNNERS = ROOT / "worldkit" / "runners"; PROOF = ROOT / "model3d_proof.json"
router = APIRouter(); JOBS: dict = {}
#: job: mesh_from_image, mesh_from_text, relief_from_image, splat_from_image, rigged_from_image, rig, motion. via: family (template), runner (studio/worldkit/runners), tool (studio/worldkit/tools.py). need: a key of worldkit.capabilities.NEEDS. peak_gb is measured where proof exists.
MODELS = [
    {"id": "trellis2", "label": "TRELLIS.2", "job": "mesh_from_image", "via": "family", "family": "TRELLIS-2-4B", "template": "trellis2_image_to_mesh", "need": "trellis2", "licence": "MIT", "note": "Textured mesh with a baked PBR atlas."},
    {"id": "hunyuan3d", "label": "Hunyuan3D 2", "job": "mesh_from_image", "via": "family", "family": "Hunyuan3D-2.1", "template": "3d_hunyuan3d_image_to_model", "need": "hunyuan3d", "licence": "Tencent Hunyuan community licence", "note": "Shape only, no colour."},
    {"id": "sam3d_objects", "label": "SAM 3D Objects", "job": "mesh_from_image", "via": "tool", "need": "sam3d_objects", "licence": "SAM License", "note": "Needs a cut-out."},
    {"id": "triposr", "label": "TripoSR", "job": "mesh_from_image", "via": "runner", "runner": "triposr_image.py", "need": "triposr", "peak_gb": 4.0, "licence": "MIT", "note": "Fastest. Soft shape, vertex colour."},
    {"id": "triposplat", "label": "TripoSplat", "job": "splat_from_image", "via": "family", "family": "TripoSplat", "template": "3d_triposplat_image_to_gaussian_splat", "need": "triposplat", "licence": "see the model page", "note": "A Gaussian splat and a turntable clip, not a mesh."},
    {"id": "moge", "label": "MoGe 2", "job": "relief_from_image", "via": "family", "family": "MoGe", "template": "3d_moge_perspective_to_mesh", "need": "moge", "licence": "see the model page", "note": "Only the side the camera sees: a relief for sets, not a whole object."},
    {"id": "shap_e", "label": "Shap-E", "job": "mesh_from_text", "via": "runner", "runner": "shap_e_text.py", "need": "shap_e", "peak_gb": 4.0, "licence": "MIT", "note": "Words to a small rough mesh, no picture step."},
    {"id": "skintokens", "label": "SkinTokens", "job": "rig", "via": "tool", "need": "skintokens", "licence": "MIT", "note": "A mesh to a rigged GLB."},
    {"id": "anigen", "label": "AniGen", "job": "rigged_from_image", "via": "tool", "need": "anigen", "licence": "see the repo's licence file", "note": "A coloured mesh with a skeleton and skin, straight from a picture. Give it a cut-out."},
    {"id": "kimodo", "label": "Kimodo", "job": "motion", "via": "tool", "need": "kimodo", "licence": "NVIDIA Open Model License", "note": "Words to a BVH motion on a human skeleton."},
]
TEXT_JOBS = ("mesh_from_text", "motion"); IMAGE_JOBS = ("mesh_from_image", "relief_from_image", "rigged_from_image", "splat_from_image")


def proof():
    """What this box has shown of each model: {id: {status, seconds, peak_gib, seed, input, sheet, note}}."""
    try: return json.load(open(PROOF, encoding="utf-8"))
    except (OSError, ValueError): return {}


def model(mid):
    m = next((x for x in MODELS if x["id"] == mid), None)
    if not m: raise HTTPException(404, "no such 3D model")
    return m


def listing(need=None):
    """Every model with its live readiness and its recorded proof."""
    if need is None:
        from studio.worldkit import capabilities as C
        need = C.need
    pr = proof(); out = []
    for m in MODELS:
        n = need(m["need"]); p = pr.get(m["id"])
        out.append({k: m.get(k) for k in ("id", "label", "job", "licence", "note")} | {"ready": n["state"] == "ready", "why_not": "" if n["state"] == "ready" else n["message"], "proof": p or {"status": "not run"}})
    return out


def _out_path(mid, suffix):
    d = Path(paths.output_dir(True)) / "3d"; d.mkdir(parents=True, exist_ok=True)
    return d / f"{mid}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{suffix}"


def _input_picture(name):
    from studio.worldkit.makers.prop import picture_path
    return picture_path(name)


def _input_mesh(rel):
    from studio.worldkit.makers.prop import mesh_path
    return mesh_path(rel)


def _runner_paths(m):
    """Where a runner reads its model and code, from the studio's settings."""
    from studio.worldkit import capabilities as C
    if m["id"] == "triposr": return ["--code", C.tool_home("triposr"), "--ckpt", C.models_root() / C.NEEDS["triposr"]["files"][0][0]]
    return ["--root", C.models_root()]


def _run_runner(m, args, out, log, run=None):
    """A runner in its own process, with this Python, after the same VRAM check the tools use."""
    from studio.worldkit import blender as B, tools
    why = B.vram_problem(m.get("peak_gb", 8.0))
    if why: raise RuntimeError(f"{m['label']}: {why}. Nothing was evicted; try again when there is room.")
    rc = (run or tools.call)([sys.executable, RUNNERS / m["runner"], *args, *_runner_paths(m), "--out", out], log, 1800)
    return tools._made(Path(out), rc, m["label"], log)


def _run_family(m, picture, seed=None):
    from studio.worldkit import jobs
    res = jobs.wait(jobs.submit(jobs.family(m["family"], m["template"], image=str(picture))))
    if res.get("status") != "done": raise RuntimeError(res.get("error") or f"{m['label']} ended {res.get('status')}")
    got = [Path(a["path"]) for a in res.get("artifacts") or []]; want = [p for p in got if p.suffix.lower() == ".glb"] or [p for p in got if p.suffix.lower() in (".spz", ".ply", ".mp4")]
    if not want: raise RuntimeError(f"{m['label']} finished with no 3D file")
    return want[0], got


def execute(m, body, work, *, runner=None, family=None, tool=None):
    """One job -> the finished file's path in the output folder. Raises with a plain sentence."""
    from studio.worldkit import tools as T
    job = m["job"]; seed = int(body.get("seed") or 42); text = " ".join(str(body.get("prompt") or "").split())
    if job in TEXT_JOBS:
        from studio.worldkit import safety
        bad = safety.text_problem(text) if text else "say what to make"
        if bad: raise ValueError(bad)
    if m["via"] == "family":
        src, all_ = (family or _run_family)(m, _input_picture(body.get("image") or ""), seed)
        out = _out_path(m["id"], src.suffix.lower()); shutil.copy2(src, out)
        for extra in all_:
            if extra != src: shutil.copy2(extra, out.with_suffix(extra.suffix.lower()))
        return out
    if m["via"] == "runner":
        out = _out_path(m["id"], ".glb"); log = work / f"{m['id']}.log"
        args = ["--prompt", text, "--seed", seed] if job == "mesh_from_text" else ["--image", _input_picture(body.get("image") or "")]
        return (runner or _run_runner)(m, args, out, log)
    t = tool or T
    if m["id"] == "sam3d_objects": made = t.sam3d_objects(_cutout_or_refuse(body), work, seed=seed)
    elif m["id"] == "anigen": made = t.anigen(_input_picture(body.get("image") or ""), work, seed=seed)
    elif m["id"] == "skintokens": made = t.skintokens(_input_mesh(body.get("mesh") or ""), work)
    elif m["id"] == "kimodo": made = t.kimodo(text, work, seconds=int(body.get("seconds") or 5), seed=seed)
    else: raise ValueError(f"{m['id']} has no way to run here")
    out = _out_path(m["id"], Path(made).suffix.lower()); shutil.copy2(made, out); return out


def _cutout_or_refuse(body):
    from PIL import Image
    p = _input_picture(body.get("image") or "")
    with Image.open(p) as im:
        if im.mode not in ("RGBA", "LA"): raise ValueError("SAM 3D Objects builds what a cut-out marks: give it a picture with a transparent background, or use the World Kit prop route, which cuts it out first")
    return p


def _worker(rec, m, body):
    work = Path(paths.setting("STUDIO_WORLDKIT_WORK") or "/tmp") / "model3d" / rec["job"]; work.mkdir(parents=True, exist_ok=True); t0 = time.time()
    try:
        out = execute(m, body, work); root = Path(paths.output_dir(True))
        rec.update(status="done", file=str(out.relative_to(root)), seconds=round(time.time() - t0, 1), glb=out.suffix.lower() == ".glb")
    except Exception as e: rec.update(status="error", error=f"{e}"[:900])


def _start(mid, body):
    m = model(mid); jid = "m3d-" + uuid.uuid4().hex[:10]; rec = {"job": jid, "model": mid, "status": "running", "started": time.time()}; JOBS[jid] = rec
    threading.Thread(target=_worker, args=(rec, m, body), daemon=True, name=f"model3d-{jid}").start(); return rec


@router.get("/api/3d/models")
def models_get(): return {"models": listing()}


@router.post("/api/3d/run")
def run_post(b: dict = None):
    b = b or {}; m = model(str(b.get("model") or "")); n = next(x for x in listing() if x["id"] == m["id"])
    if not n["ready"]: raise HTTPException(409, n["why_not"])
    return _start(m["id"], b)


@router.get("/api/3d/jobs/{jid}")
def job_get(jid: str):
    r = JOBS.get(jid)
    if not r: raise HTTPException(404, "no such job")
    return r
