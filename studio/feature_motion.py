"""The Motion page: what a person wants to move, and the models on this machine that do it. Each route says how it runs (a tool, a program of our own, or a graph on its family's server), what its licence lets you do, and shows only what was really rendered here (motion_proof.json).
Anything that shows a person goes through studio/likeness.py, and the mark and receipt it adds. Samples show invented adults made here, fully clothed. A route whose files are not on this machine says what it is waiting for and shows nothing."""
import json, os, shutil, subprocess, sys, threading, time, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psn import paths
from studio import likeness

ROOT = Path(__file__).resolve().parent; RUNNERS = ROOT / "worldkit" / "runners"; PROOF = ROOT / "motion_proof.json"
router = APIRouter(); JOBS: dict = {}
PAGE = {"tab": "motion", "label": "Motion", "title": ["Motion", "Words in. A body moving.", "Make a character move, follow a performance, animate a portrait, lip-sync a clip, or capture motion into a rig. Only what ran on this machine is shown, with its numbers and its faults."], "module": "motion.js", "export": "Motion", "css": "motion.css"}
GROUPS = [
    {"id": "words", "title": "Move from words", "short": "Words to a rig", "does": "Describe a motion. It lands on a World Kit character as a clip you can play, export or shoot in Virtual Set."},
    {"id": "perform", "title": "Follow a performance", "short": "Video to video", "does": "One picture of a person and one clip of someone moving: the person in the picture does what the clip does."},
    {"id": "portrait", "title": "Animate a portrait", "short": "A face moves", "does": "A still face takes its expressions and head turns from a clip of another face."},
    {"id": "lipsync", "title": "Lip-sync to audio", "short": "A mouth speaks", "does": "A clip and a speech track: the mouth is redrawn to the words."},
    {"id": "capture", "title": "Capture into a rig", "short": "Video to a rig", "does": "A clip of someone moving becomes motion data for your rigged characters."},
    {"id": "dance", "title": "Dance", "short": "To the music", "does": "A dance from words on a character, or a person dancing to a track."},
]
KIMODO_WEIGHTS = "_libraries/models-legacy-layout/motion/kimodo/"
#: person: a real person could be shown, so the likeness guard applies. commercial: True, False or "conditional"; the licence line says why. model_files are relative to the models root. Ordered best first within a group, from looking at the results.
ROUTES = [
    {"id": "kimodo_soma", "group": "words", "label": "Kimodo SOMA", "model": "nvidia/Kimodo-SOMA-RP-v1.1", "via": "tool", "tool": "kimodo", "needs": ["text"], "licence": "NVIDIA Open Model License; its Llama 3 text encoder is under the Llama 3 Community License", "commercial": True, "peak_gb": 3.0, "person": False, "does": "Text to a 77-joint body motion, fitted to a World Kit rig from joint positions.", "model_files": [KIMODO_WEIGHTS + "Kimodo-SOMA-RP-v1.1/model.safetensors"]},
    {"id": "kimodo_dance", "group": "dance", "label": "Kimodo dance", "model": "nvidia/Kimodo-SOMA-RP-v1.1", "via": "tool", "tool": "kimodo", "needs": ["text"], "licence": "NVIDIA Open Model License; its Llama 3 text encoder is under the Llama 3 Community License", "commercial": True, "peak_gb": 3.0, "person": False, "does": "The same model asked for a dance. It does not hear music: the steps are not on the beat.", "model_files": [KIMODO_WEIGHTS + "Kimodo-SOMA-RP-v1.1/model.safetensors"]},
    {"id": "wan_animate2", "group": "perform", "label": "Wan Animate 2", "model": "Comfy-Org/Wan-Animate-2 (distilled, int8)", "via": "family", "family": "Wan2.2-Animate", "template": "motion_wan_animate2", "needs": ["image", "video", "text"], "slots": {"image": "189|image", "video": "240|file", "text": "604|value"}, "seed_slot": "261:19|noise_seed", "size_slots": ["261:243|resize_type.width", "261:243|resize_type.height"], "default_text": "A person moving naturally, whole body in frame, the camera still.", "licence": "Apache-2.0", "commercial": True, "peak_gb": 42.0, "person": True, "does": "A person from one picture performs a driving clip, with no pose step.", "model_files": ["_complete_pipelines/Wan2.2-Animate/diffusion_models/wan_animate_2_distill_int8_convrot.safetensors"]},
    {"id": "scail2", "group": "perform", "label": "SCAIL 2", "model": "Comfy-Org/SCAIL-2", "via": "family", "family": "Wan-SCAIL-2", "template": "motion_scail2", "needs": ["image", "video", "text"], "slots": {"image": "30|image", "video": "155|file", "text": "213:3|text"}, "seed_slot": "213:19|noise_seed", "size_slots": ["213:178|value", "213:179|value"], "default_text": "An adult in plain everyday clothes, fully clothed, moving naturally in a plain studio.", "licence": "MIT on Hugging Face, Apache-2.0 on GitHub", "commercial": True, "peak_gb": 30.0, "person": True, "does": "Character replacement in a driving clip, with segmentation by SAM 3.1.", "model_files": ["_complete_pipelines/Wan-SCAIL-2/diffusion_models/wan2.1_14B_SCAIL_2_nvfp4_mxpf8_mix.safetensors"]},
    {"id": "liveportrait", "group": "portrait", "label": "LivePortrait", "model": "KwaiVGI/LivePortrait", "via": "family", "family": "LivePortrait", "template": "motion_liveportrait", "needs": ["image", "video"], "slots": {"image": "src|image", "video": "drive|file"}, "licence": "LivePortrait is MIT. Its face finder here is InsightFace buffalo_l, whose weights are for non-commercial use", "commercial": "conditional", "peak_gb": 4.0, "person": True, "does": "A still face follows the expressions and head turns of a driving clip. Face only: the body stays put.", "model_files": ["liveportrait/safetensors/appearance_feature_extractor.safetensors"]},
    {"id": "latentsync", "group": "lipsync", "label": "LatentSync 1.6", "model": "ByteDance/LatentSync-1.6", "via": "runner", "runner": "latentsync_run.py", "needs": ["video", "audio"], "licence": "Code Apache-2.0, weights OpenRAIL++. Its face finder is InsightFace buffalo_l, whose weights are for non-commercial use", "commercial": "conditional", "peak_gb": 16.0, "person": True, "does": "Redraws the mouth of an existing clip to a speech track, 25 frames a second.", "model_files": ["video_cont/latentsync/latentsync_unet.pt"]},
    {"id": "infinitetalk", "group": "lipsync", "label": "InfiniteTalk", "model": "MeiGen-AI/InfiniteTalk on Wan 2.1 I2V", "via": "family", "family": "Wan2.1", "template": "motion_infinitetalk", "needs": ["image", "audio", "text"], "slots": {"image": "img|image", "audio": "aud|audio", "text": "t|text"}, "seed_slot": "seed|noise_seed", "default_text": "An adult speaking calmly to the camera, fully clothed, head and shoulders, plain background.", "licence": "Apache-2.0", "commercial": True, "peak_gb": 36.0, "person": True, "does": "One picture and a speech track: a new clip of that person talking, with head and shoulders moving.", "model_files": ["diffusion_models/wan2.1_i2v_480p_14B_fp8_scaled.safetensors", "model_patches/wan2.1_infinitetalk_single_fp16_from_kj.safetensors", "_by_repo/Kijai__wav2vec2_safetensors/wav2vec2-chinese-base_fp16.safetensors"]},
    {"id": "sam3d_capture", "group": "capture", "label": "SAM 3D Body capture", "model": "facebook/sam-3d-body-dinov3", "via": "family", "family": "SAM-3D-Body", "template": "motion_sam3d_capture", "needs": ["video"], "slots": {"video": "drive|file"}, "licence": "SAM License", "commercial": True, "peak_gb": 28.0, "person": True, "extra_files": (".bvh",), "does": "Each frame of a clip gives a body pose. The poses are smoothed and written as a BVH, with a film of the pose over the clip. Put the BVH on a World Kit character as a clip.", "model_files": ["detection/sam_3d_body_dinov3_bf16.safetensors"]},
    {"id": "wan_dancer", "group": "dance", "label": "Wan Dancer", "model": "Comfy-Org/Wan-Dancer", "via": "family", "family": "Wan2.2-Dancer", "template": "motion_wan_dancer", "needs": ["image", "audio"], "slots": {"image": "547|image", "audio": "548|audio"}, "licence": "Apache-2.0", "commercial": True, "peak_gb": 40.0, "person": True, "does": "A person from one picture dancing to a music track.", "model_files": ["_complete_pipelines/Wan2.2-Dancer/diffusion_models/wan2.2_dancer_14b_global_fp8_scaled.safetensors", "_complete_pipelines/Wan2.2-Dancer/diffusion_models/wan2.2_dancer_14b_local_fp8_scaled.safetensors"]},
]
#: Models looked at and not offered as routes, and why. The page and the final report say the same.
NOT_OFFERED = [
    {"model": "Kimodo SMPL-X", "why": "NVIDIA R&D licence: non-production, no works for sale or distribution. The weights' config is also missing here."},
    {"model": "Kimodo G1 and Kimodo SEED", "why": "G1 gives a Unitree robot's joints, with no rig here to show them on. SEED is the same kind of body as SOMA and has not been compared with it."},
    {"model": "TMR", "why": "It compares text with motion; it makes nothing to look at."},
    {"model": "AnimateDiff, Wan 2.1 Fun InP", "why": "General clip makers, not motion transfer: they are on the Families page."},
    {"model": "HY-Motion 1.0", "why": "Withdrawn: it gave broken poses at the model's own guidance. Its licence also excludes the EU, UK and South Korea."},
    {"model": "Motius-GEM-SMPL", "why": "Non-commercial twice over (its source and the SMPL-X body model)."},
    {"model": "Sonic", "why": "CC BY-NC-SA, whatever its mirror says, and its detector and frame files are missing here."},
    {"model": "GEM-X SOMA", "why": "Two of its checkpoints (gem_soma, mhr_model) are not on this machine yet. Its terms ask for consent from anyone captured and forbid impersonation."},
    {"model": "4DAnyone", "why": "The model itself is not on this machine. Its parts are research-only or AGPL."},
    {"model": "FlashPortrait, OmniAvatar, StableAvatar, LongCat Avatar, Lynx, MuseTalk, MultiTalk", "why": "Base weights or their packs' dependencies are missing here, so nothing has been rendered with them."},
]
ALLOWED = {"image": (".png", ".jpg", ".jpeg", ".webp"), "video": (".mp4", ".mov", ".webm", ".mkv"), "audio": (".wav", ".mp3", ".flac", ".m4a", ".ogg")}


def route(rid):
    r = next((x for x in ROUTES if x["id"] == rid), None)
    if not r: raise HTTPException(404, "no such motion route")
    return r


def models_root():
    from studio.worldkit import capabilities as C
    return Path(C.models_root())


def need(r, root=None):
    """'' when this route can run here, otherwise what it is waiting for."""
    root = Path(root) if root else models_root()
    miss = [Path(f).name for f in r["model_files"] if not (root / f).exists()]
    if miss: return "waiting for " + ", ".join(miss)
    if r["via"] == "tool":
        from studio.worldkit import capabilities as C
        return C.tool_problem(r["tool"])
    return ""


def proof():
    try: return json.load(open(PROOF, encoding="utf-8"))
    except (OSError, ValueError): return {"routes": {}}


def _slug(r):
    if not r.get("family"): return None
    from psn import instances as I
    return I.slug(r["family"])


def listing(check=need):
    pr = proof().get("routes", {}); rows = []
    for r in ROUTES:
        why = check(r); got = pr.get(r["id"]) or {}
        rows.append({k: r.get(k) for k in ("id", "group", "label", "model", "via", "needs", "licence", "commercial", "person", "does", "peak_gb", "family", "template")} | {"family_slug": _slug(r), "ready": not why, "why_not": why, "samples": got.get("samples") or [], "weak": got.get("weak") or [], "proof": got.get("label") or "Not rendered here yet"})
    return rows


def _inputs(r, b):
    """{kind: a real file in the studio's input folder} for what this route takes. A name the browser sent is never joined raw."""
    from studio.worldkit.makers.prop import _under
    base = paths.comfy_input(True); out = {}
    for k in r["needs"]:
        if k == "text": continue
        if not b.get(k): raise HTTPException(400, f"{r['label']} needs a {k}")
        try: out[k] = _under(base, b[k], ALLOWED[k])
        except Exception: raise HTTPException(400, f"{Path(str(b[k])).name} is not a usable {k} in the studio's input folder") from None
    return out


def _out(r, ext=".mp4"):
    d = Path(paths.output_dir(True)) / "motion"; d.mkdir(parents=True, exist_ok=True)
    return d / f"{r['id']}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"


def _tool_paths(root):
    return {"--weights": root / "video_cont/latentsync/latentsync_unet.pt", "--vae": root / "vae/vae-ft-mse-840000-ema-pruned.safetensors", "--vae-config": root / "musetalk/sd-vae"}


def _run_runner(r, inputs, b, work, out):
    from studio.worldkit import blender as B, tools
    why = B.vram_problem(r["peak_gb"])
    if why: raise RuntimeError(f"{r['label']}: {why}. Nothing was evicted; try again when there is room.")
    args = [sys.executable, RUNNERS / r["runner"], "--code", paths.setting("STUDIO_TOOL_LATENTSYNC", default=paths.home("ai", "LatentSync")), "--faces", models_root() / "face/insightface/models/buffalo_l", "--video", inputs["video"], "--audio", inputs["audio"], "--out", out, "--work", work, "--seed", int(b.get("seed") or 1247)]
    for k, v in _tool_paths(models_root()).items(): args += [k, v]
    return tools._made(Path(out), tools.call(args, Path(work) / "run.log", 3600), r["label"], Path(work) / "run.log")


def fit_size(width, height, longest=832, step=32):
    """A size this model can take that keeps a clip's shape, so nobody's head or feet get cropped off."""
    k = longest / max(width, height)
    return max(step, round(width * k / step) * step), max(step, round(height * k / step) * step)


def _clip_size(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)], capture_output=True, text=True, timeout=60).stdout.strip().split(",")
    return int(o[0]), int(o[1])


def _run_family(r, inputs, b):
    from psn import instances as I
    from studio import families_api as F
    from studio.worldkit import jobs
    info = F._ensure(r["family"]); d = Path(I.INSTANCES) / info["slug"] / "input"; d.mkdir(parents=True, exist_ok=True); values = {}
    for k, slot in r["slots"].items():
        if k == "text": values[slot] = " ".join(str(b.get("text") or r.get("default_text") or "").split()); continue
        name = "motion_" + uuid.uuid4().hex[:10] + Path(inputs[k]).suffix.lower(); shutil.copy2(inputs[k], d / name); values[slot] = name
    if b.get("seed") and r.get("seed_slot"): values[r["seed_slot"]] = int(b["seed"])
    if r.get("size_slots") and inputs.get("video"): values.update(zip(r["size_slots"], fit_size(*_clip_size(inputs["video"]), longest=r.get("longest", 832))))
    body = {"values": values, "permission": b.get("permission") is True}
    job = F.template_run(F._slug(r["family"]), r["template"], body)["job"]; res = jobs.wait(f"{F._slug(r['family'])}/{job}")
    if res.get("status") != "done": raise RuntimeError(res.get("error") or f"{r['label']} ended {res.get('status')}")
    got = [Path(a["path"]) for a in res.get("artifacts") or [] if a.get("media_type") == "video"]
    if not got: raise RuntimeError(f"{r['label']} finished with no video")
    extra = [Path(a["path"]) for a in res.get("artifacts") or [] if Path(a["path"]).suffix.lower() in r.get("extra_files", ())]
    if r.get("extra_files") and not extra: raise RuntimeError(f"{r['label']} finished with no {' or '.join(r['extra_files'])} file")
    return (got[0], extra) if r.get("extra_files") else got[0]


def _character_path(aid):
    from studio.worldkit import library as L
    lib = L.Library(); meta = lib.get(str(aid))
    if not meta or meta.get("type") != "character": raise HTTPException(400, "pick a built World Kit character")
    p = lib.dir("character", meta["id"]) / "asset.glb"
    if not p.is_file(): raise HTTPException(400, "that character has no finished file yet")
    return meta, p


def _run_kimodo(r, b, work):
    """Words -> a BVH -> the clip added to the chosen character through World Kit's own step (a character build keeps its rig and other clips). With no character, the BVH is the result."""
    from studio.worldkit import tools
    seconds = max(2, min(10, int(b.get("seconds") or 5))); seed = int(b.get("seed") or 7)
    bvh = tools.kimodo(str(b.get("text") or ""), Path(work) / "kimodo", seconds=seconds, seed=seed)
    out = _out(r, ".bvh"); shutil.copy2(bvh, out)
    return out


def execute(r, b, inputs, work, *, runner=_run_runner, family=_run_family, kimodo=_run_kimodo, mark=likeness.mark):
    t0 = time.time()
    if r["via"] == "tool": out = kimodo(r, b, work)
    else:
        raw = runner(r, inputs, b, work, _out(r)) if r["via"] == "runner" else family(r, inputs, b)
        raw, extra = raw if isinstance(raw, tuple) else (raw, [])
        out = _out(r); mark(raw, out)
        for e in extra: shutil.copy2(e, out.with_suffix(e.suffix.lower()))           # the motion file sits beside its film, same name
        if str(raw).startswith(str(Path(paths.output_dir(True)) / "motion")): Path(raw).unlink(missing_ok=True)
    likeness.receipt(out, r, b, inputs, seed=b.get("seed"), seconds=round(time.time() - t0, 1))
    return out


def _worker(rec, r, b, inputs):
    work = Path(paths.setting("STUDIO_WORLDKIT_WORK") or "/tmp") / "motion" / rec["job"]; work.mkdir(parents=True, exist_ok=True); t0 = time.time()
    try:
        out = execute(r, b, inputs, work); rec.update(status="done", file=str(Path(out).relative_to(Path(paths.output_dir(True)))), seconds=round(time.time() - t0, 1))
    except Exception as e: rec.update(status="error", error=f"{e}"[:900])


@router.get("/api/motion")
def motion_get():
    rows = listing(); return {"groups": GROUPS, "routes": rows, "not_offered": NOT_OFFERED, "ask": likeness.ASK, "limits": LIMITS, "hero": proof().get("hero")}


LIMITS = "Words are checked and pictures and clips go through the picture check, which looks for a readable adult face and nothing undressed. Nothing here can tell a real person from an invented one, and it never hears a voice: that part is your word, and it is kept with the result. Results that show a person carry a visible AI-generated mark."


@router.post("/api/motion/run")
def run_post(b: dict = None):
    b = b or {}; r = route(str(b.get("route") or "")); why = need(r)
    if "text" in r["needs"] and r["via"] == "tool" and not str(b.get("text") or "").strip(): raise HTTPException(400, "Say what happens.")
    if why: raise HTTPException(409, f"{r['label']}: {why}")
    inputs = _inputs(r, b); likeness.guard(r, b, inputs)
    jid = "mot-" + uuid.uuid4().hex[:10]; rec = {"job": jid, "route": r["id"], "status": "running", "started": time.time()}; JOBS[jid] = rec
    threading.Thread(target=_worker, args=(rec, r, b, inputs), daemon=True, name=f"motion-{jid}").start(); return rec


@router.get("/api/motion/jobs/{jid}")
def job_get(jid: str):
    r = JOBS.get(jid)
    if not r: raise HTTPException(404, "no such job")
    return r
