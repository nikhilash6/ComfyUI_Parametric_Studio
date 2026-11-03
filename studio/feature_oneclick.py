"""One-click tools on the Edit page: one photo or clip in, a finished set out. Each tool is one ComfyUI graph in workflows/oneclick_*.json, filled through its ${names}
like the goal templates, and every model it loads is listed with its licence where the person picks the tool.

- angles: a coverage set of four camera angles from one still (Qwen-Image-Edit-2511, Lightning 4-step, fal's Multiple-Angles LoRA; its card's "<sks> azimuth elevation distance" prompts).
- relight: one-click relight of a photo (Qwen-Image-Edit-2509 int8, Lightning 4-step, dx8152's Relight LoRA; its card's trigger word is 重新照明, "relight").
- effects: inflate (Systms' INFL8 LoRA) or turn the subject to marble or gold (prompt only), then optionally an LTX-2.5 clip from the photo to the edited frame.
- matte: the LTX-2.5 Alpha-Gen IC-LoRA pulls a matte from a clip; the studio merges it with the plate into ProRes 4444 and WebM files with real alpha, and drops the
  subject onto a new set made by Z-Image Turbo.

No page of its own (no PAGE): the Edit page shows it. The router loads like every feature_*.py file."""
import json, math, os, random, re, shutil, subprocess, threading, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psn import paths
from studio.graph_template import fill, placeholders

router = APIRouter()
WF = Path(__file__).resolve().parent.parent / "workflows"
ART = Path(__file__).resolve().parent / "web" / "oneclick_art"

try: from studio import licences as LIC                       # the licence table, once the licence audit is merged
except ImportError: LIC = None


def _lic(licence, url, *limits): return {"licence": licence, "url": url, "limits": list(limits)}


def _family(name, fallback):
    """A family's entry from studio/licences.py when it is there, else the same words kept here."""
    e = LIC.FAMILIES.get(name) if LIC else None
    return {**e, "limits": list(e["limits"])} if e else fallback


APACHE = "Apache-2.0"
#: every model a tool loads. Each licence was read from the model's own Hugging Face page on 2026-11-02.
MODELS = {
    "qwen2511": {"name": "Qwen-Image-Edit-2511 (fp8)", "file": "qwen_image_edit_2511_fp8mixed.safetensors", **_lic(APACHE, "https://huggingface.co/Qwen/Qwen-Image-Edit-2511")},
    "qwen2509": {"name": "Qwen-Image-Edit-2509 (int8)", "file": "qwen_image_edit_2509_int8_convrot.safetensors", **_lic(APACHE, "https://huggingface.co/Qwen/Qwen-Image-Edit-2509")},
    "lightning2511": {"name": "Qwen-Image-Edit-2511 Lightning 4-step LoRA (lightx2v)", "file": "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors", **_lic(APACHE, "https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning")},
    "lightning2509": {"name": "Qwen-Image-Edit-2509 Lightning 4-step LoRA (lightx2v)", "file": "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors", **_lic(APACHE, "https://huggingface.co/lightx2v/Qwen-Image-Lightning")},
    "angles": {"name": "Multiple-Angles LoRA for 2511 (fal)", "file": "qwen-image-edit-2511-multiple-angles-lora.safetensors", **_lic(APACHE, "https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA")},
    "relight": {"name": "Relight LoRA for 2509 (dx8152)", "file": "Qwen-Image-Edit-2509-Relight.safetensors", **_lic(APACHE, "https://huggingface.co/dx8152/Qwen-Image-Edit-2509-Relight")},
    "infl8": {"name": "INFL8 inflate LoRA for 2511 (Systms)", "file": "Qwen_Image_Edit_2511-SYSTMS_INFL8.safetensors", **_lic(APACHE, "https://huggingface.co/systms/SYSTMS-INFL8-LoRA-Qwen-Image-Edit-2511")},
    "qwen_vl": {"name": "Qwen2.5-VL 7B text encoder (fp8)", "file": "qwen_2.5_vl_7b_fp8_scaled.safetensors", **_lic(APACHE, "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI")},
    "ltx": {"name": "LTX-2.5 22B distilled (int8) and its Gemma encoder", "file": "ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors",
            **_family("LTX-2.5", _lic("LTX-2.x Community License (gated download): entities with US$10,000,000 or more annual revenue need a paid licence", "https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x", "Revenue cap US$10M"))},
    "alpha": {"name": "LTX-2.5 Alpha-Gen IC-LoRA (Lightricks)", "file": "ltx-2.5-22b-ic-lora-alpha-gen-0.9.safetensors",
              **_lic("LTX-2.x Community License, as for LTX-2.5 itself (gated download)", "https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Alpha-Gen", "Revenue cap US$10M")},
    "zimage": {"name": "Z-Image Turbo", "file": "z_image_turbo_bf16.safetensors", **_family("Z-Image", _lic(APACHE, "https://huggingface.co/Tongyi-MAI/Z-Image-Turbo"))},
}

#: the fal card's prompt grammar: <sks> [azimuth] [elevation] [distance]
AZIMUTHS = ("front view", "front-right quarter view", "right side view", "back-right quarter view", "back view", "back-left quarter view", "left side view", "front-left quarter view")
ELEVATIONS = ("low-angle shot", "eye-level shot", "elevated shot", "high-angle shot")
DISTANCES = ("close-up", "medium shot", "wide shot")
ANGLE_SETS = {
    "coverage": [("Wide, from above", "front view elevated shot wide shot"), ("Close-up", "front view eye-level shot close-up"), ("Three-quarter left", "front-left quarter view eye-level shot medium shot"), ("Low angle, right", "front-right quarter view low-angle shot medium shot")],
    "turnaround": [("Front", "front view eye-level shot medium shot"), ("Right side", "right side view eye-level shot medium shot"), ("Back", "back view eye-level shot medium shot"), ("Left side", "left side view eye-level shot medium shot")],
    "heights": [("Low angle", "front view low-angle shot medium shot"), ("Eye level", "front view eye-level shot medium shot"), ("Elevated", "front view elevated shot medium shot"), ("High angle", "front view high-angle shot medium shot")],
    "orbit": [("Front right", "front-right quarter view eye-level shot medium shot"), ("Right", "right side view eye-level shot medium shot"), ("Back right", "back-right quarter view eye-level shot medium shot"), ("Back", "back view eye-level shot medium shot")],
}
ANGLE_STRENGTH = {"standard": 0.9, "strong": 1.0, "gentle": 0.8}       # the card: 0.8 to 1.0, start at 0.9

RELIGHT_TRIGGER = "重新照明"
LIGHTS = {
    "golden hour": "warm low golden-hour sunlight from the left, long soft shadows",
    "window light": "soft diffuse daylight through a window on the right, gentle falloff",
    "studio rim": "a dark studio with a clean bright rim light from behind and a soft key light in front",
    "neon night": "night-time neon light, magenta from the left and cyan from the right, coloured reflections",
    "candlelight": "warm flickering candlelight from below in a dark room",
    "overcast": "soft even overcast daylight with no hard shadows",
}

EFFECTS = {   # LoRA strength, still prompt, motion prompt. INFL8's card: "inflate the [subject]"; the statues need no LoRA.
    "inflate": (1.0, "Inflate the {subject}.", "The clothes of the {subject} slowly puff up and swell like an inflating balloon, growing rounder and shinier second by second, while the {subject} keeps the same pose. Continuous smooth inflation, no cuts, no fades. The camera stays still. Soft rubbery stretching sounds, no music, no speech."),
    "marble statue": (0.0, "Turn the {subject} into a white marble statue with carved stone texture. Keep the pose, the framing and the background unchanged.", "The {subject} slowly turns to white marble, the stone spreading over clothes and skin second by second until it is a still statue. Continuous change, no cuts, no fades. The camera stays still. A soft stone grinding sound, no music, no speech."),
    "gold statue": (0.0, "Turn the {subject} into a polished gold statue with a mirror-like metal surface. Keep the pose, the framing and the background unchanged.", "The {subject} slowly turns to shining gold, the metal spreading over clothes and skin second by second until it is a still statue. Continuous change, no cuts, no fades. The camera stays still. A soft metallic shimmer sound, no music, no speech."),
}
NEG_VIDEO = "worst quality, inconsistent motion, blurry, jittery, distorted, watermark, text"
LTX_SIZES = {"16:9": (960, 544), "9:16": (544, 960), "1:1": (704, 704)}
MATTE_SET = "An empty {place}, no people, photorealistic, natural light, wide shot, sharp focus"

#: peak_gib: the lane's measured peak on a 96 GB card, plus a tenth, each from an empty card: angles 29.2, relight 29.1, the effect still 28.7, the effect still + clip 38.9
#: (66.0 before the graph unloaded Qwen ahead of LTX), the matte 51.9 GiB
TOOLS = {
    "angles": {"label": "Coverage set from one still", "blurb": "Upload one photo and get four new camera angles of the same scene: a wide, a close-up, a three-quarter and a low angle, or a full turnaround.",
               "input": "image", "graph": "oneclick_angles_api.json", "models": ["qwen2511", "lightning2511", "angles", "qwen_vl"], "peak_gib": 32,
               "options": {"set": list(ANGLE_SETS), "strength": list(ANGLE_STRENGTH)}, "defaults": {"set": "coverage", "strength": "standard"}},
    "relight": {"label": "Relight a photo", "blurb": "Pick a light and the photo is relit: the people, the clothes and the framing stay, only the light changes.",
                "input": "image", "graph": "oneclick_relight_api.json", "models": ["qwen2509", "lightning2509", "relight", "qwen_vl"], "peak_gib": 32,
                "options": {"light": list(LIGHTS)}, "defaults": {"light": "golden hour"}, "text": {"direction": "Your own light, in plain words (optional, replaces the pick)"}},
    "effects": {"label": "One-tap photo effects", "blurb": "Inflate the subject like a balloon, or turn it to marble or gold. Ask for a clip and LTX-2.5 moves from your photo to the effect, with sound.",
                "input": "image", "graph": "oneclick_effect_api.json", "graph_clip": "oneclick_effect_clip_api.json", "models": ["qwen2511", "lightning2511", "infl8", "qwen_vl", "ltx"], "peak_gib": 32, "peak_clip_gib": 43,
                "options": {"effect": list(EFFECTS), "output": ["still", "still + clip"], "seconds": [3, 4, 5]}, "defaults": {"effect": "inflate", "output": "still", "seconds": 5},
                "text": {"subject": "What to change, in a few words (default: the person)"}},
    "matte": {"label": "Alpha matte and a new background", "blurb": "Pull the person out of a clip as a real alpha video (ProRes 4444 and WebM), and drop them onto a new set made from your words.",
              "input": "video", "graph": "oneclick_matte_api.json", "models": ["ltx", "alpha", "zimage"], "peak_gib": 57,
              "options": {"seconds": [2, 3, 4, 5], "aspect": ["auto", "16:9", "9:16", "1:1"]}, "defaults": {"seconds": 4, "aspect": "auto"},
              "text": {"background": "The new set, in plain words (for example: a sunlit beach boardwalk)"}},
}
#: save node -> label, per tool; the order is the order the result shows
OUTPUTS = {
    "angles": {f"save{i}": None for i in range(1, 5)},
    "relight": {"save1": "Relit"},
    "effects": {"save1": "Effect", "l_save": "Clip"},
    "matte": {"save_comp": "On the new set", "z_save": "The new set", "save_matte": "Matte", "save_plate": "Plate"},
}
JOBS: dict = {}
_post_lock = threading.Lock()


def comfy_url(): return os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/")


def models_of(tid, clip=True):
    keys = [k for k in TOOLS[tid]["models"] if clip or k != "ltx"]
    return [{"id": k, **MODELS[k], "badge": badge(MODELS[k]["limits"])} for k in keys]


def badge(limits):
    if LIC: return LIC.badge(tuple(limits))
    if not limits: return ""
    return "Revenue cap" if limits[0].startswith("Revenue cap") else limits[0]


def examples():
    """Our own renders of each tool, shown as its example. Written by hand after the render was looked at."""
    try: return json.loads((ART / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}


def catalogue():
    ex = examples()
    return [{"id": k, **{x: t[x] for x in ("label", "blurb", "input", "options", "defaults", "peak_gib")}, "text": t.get("text", {}), "models": models_of(k), "graphs": [t["graph"]] + ([t["graph_clip"]] if t.get("graph_clip") else []), "example": ex.get(k)} for k, t in TOOLS.items()]


# ---------- values for each graph
def _input_name(v, kind):
    name = str(v or "").strip()
    if not name: raise HTTPException(400, "add a photo first" if kind == "image" else "add a source clip first")
    pat = r"\.(png|jpe?g|webp)$" if kind == "image" else r"\.(mp4|webm|mov|mkv)$"
    if os.path.basename(name) != name or not re.search(pat, name, re.I): raise HTTPException(400, "upload a png, jpg or webp photo" if kind == "image" else "upload an mp4, webm, mov or mkv clip")
    return name


def image_aspect(name):
    """The nearest LTX size for an uploaded photo, or 16:9 when it cannot be read here (ComfyUI on another machine)."""
    try:
        from PIL import Image
        with Image.open(os.path.join(paths.comfy_input(True), name)) as im: w, h = im.size
        return min(LTX_SIZES, key=lambda a: abs(math.log((w / h) / (LTX_SIZES[a][0] / LTX_SIZES[a][1]))))
    except Exception: return "16:9"


def frames_ltx(seconds): return 8 * max(1, round(seconds * 24 / 8)) + 1


def values(tid, b):
    """-> (graph file, values, options, labels {save node: label}). Raises 400 on a bad request."""
    t = TOOLS[tid]; o = {**t["defaults"], **{k: v for k, v in (b.get("options") or {}).items() if k in t["options"] and v in t["options"][k]}}
    text = {k: str((b.get("text") or {}).get(k) or "").strip()[:300] for k in t.get("text", {})}
    from studio.likeness import words_problem
    bad = words_problem(*text.values())
    if bad: raise HTTPException(400, bad)
    seed = b.get("seed")
    try: seed = random.randint(0, 2**31 - 1) if seed in (None, "") else int(seed)
    except (TypeError, ValueError, OverflowError): raise HTTPException(400, "seed must be a whole number") from None
    labels = dict(OUTPUTS[tid]); v = {"seed": seed}
    if tid == "angles":
        image = _input_name(b.get("image"), "image"); shots = ANGLE_SETS[o["set"]]
        v.update(image=image, strength=ANGLE_STRENGTH[o["strength"]], **{f"angle_{i}": shots[i - 1][1] for i in range(1, 5)})
        labels = {f"save{i}": shots[i - 1][0] for i in range(1, 5)}
        return t["graph"], v, o, labels
    if tid == "relight":
        image = _input_name(b.get("image"), "image"); light = text["direction"] or LIGHTS[o["light"]]
        v.update(image=image, prompt=f"{RELIGHT_TRIGGER}, relight the picture with {light.rstrip('.')}. Keep the people, their clothes, the pose, the framing and the background unchanged.")
        return t["graph"], v, o, labels
    if tid == "effects":
        image = _input_name(b.get("image"), "image"); strength, still, motion = EFFECTS[o["effect"]]; subject = text["subject"] or "person"
        v.update(image=image, fx_strength=strength, prompt=still.format(subject=subject))
        if o["output"] == "still":
            labels.pop("l_save"); return t["graph"], v, o, labels
        w, h = LTX_SIZES[image_aspect(image)]
        v.update(motion_prompt=motion.format(subject=subject), negative=NEG_VIDEO, width=w, height=h, frames=frames_ltx(o["seconds"]))
        return t["graph_clip"], v, o, labels
    # matte
    video = _input_name(b.get("video"), "video"); place = text["background"] or "sunlit seaside boardwalk"
    from studio.goals import probe_input
    info = probe_input(video); aspect = o["aspect"]
    if aspect == "auto":
        aspect = min(LTX_SIZES, key=lambda a: abs(math.log((info["width"] / max(1, info["height"])) / (LTX_SIZES[a][0] / LTX_SIZES[a][1])))) if info else "16:9"
    if info and info["duration"] < 0.5: raise HTTPException(400, "the source clip is too short")
    k = max(1, round(o["seconds"] * 24 / 8))
    if info: k = max(1, min(k, math.floor((math.floor(info["duration"] * 24) - 1) / 8)))
    frames = 8 * k + 1; w, h = LTX_SIZES[aspect]
    v.update(video=video, frames=frames, slice_seconds=round(frames / 24 + 0.1, 3), width=w, height=h, background=MATTE_SET.format(place=place.rstrip(".")))
    return t["graph"], v, o, labels


def build(tid, b):
    name, v, o, labels = values(tid, b)
    tpl = json.loads((WF / name).read_text(encoding="utf-8"))
    miss = placeholders(tpl) - set(v)
    if miss: raise HTTPException(500, f"graph needs {sorted(miss)}")
    return fill(tpl, v), v, o, labels, name


# ---------- running
def _comfy(path, payload=None, timeout=30):
    req = urllib.request.Request(comfy_url() + path, data=json.dumps(payload).encode() if payload is not None else None, headers={"Content-Type": "application/json"} if payload is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read() or b"{}")


@router.get("/api/oneclick")
def oneclick_list(): return {"tools": catalogue()}


@router.post("/api/oneclick/{tid}/graph")
def oneclick_graph(tid: str, b: dict = None):
    """The exact graph a run would send, filled in. Nothing runs."""
    if tid not in TOOLS: raise HTTPException(404, "no such tool")
    g, v, o, labels, name = build(tid, b or {}); return {"workflow": "workflows/" + name, "graph": g, "values": v, "options": o}


@router.post("/api/oneclick/{tid}/run")
def oneclick_run(tid: str, b: dict = None):
    if tid not in TOOLS: raise HTTPException(404, "no such tool")
    b = b or {}; g, v, o, labels, name = build(tid, b)
    try:
        from studio.names import resolve_names
        g, rep = resolve_names(g, _comfy("/object_info", timeout=60))
    except HTTPException: raise
    except Exception: rep = []
    missing = sorted({r["was"] for r in rep if r["now"] is None})
    if missing: raise HTTPException(400, "This needs model files that are not installed: " + ", ".join(missing) + ". Download them on the Models page. The studio will not run a different model in their place.")
    try: res = _comfy("/prompt", {"prompt": g, "client_id": "studio-oneclick"})
    except urllib.error.HTTPError as e:
        try: why = json.loads(e.read() or b"{}").get("error", {}).get("message", "")
        except Exception: why = ""
        raise HTTPException(400, f"ComfyUI rejected the graph: {why}"[:400]) from None
    except Exception: raise HTTPException(503, "ComfyUI is not reachable") from None
    from studio.apps import dropped_outputs
    if dropped_outputs(res): raise HTTPException(502, dropped_outputs(res)[:500])
    jid = res["prompt_id"]
    JOBS[jid] = {"tool": tid, "workflow": name, "labels": labels, "seed": v["seed"], "options": o, "started": time.time(), "models": [m["name"] for m in models_of(tid, clip=name.endswith("clip_api.json") or tid == "matte")]}
    return {"job": jid, "seed": v["seed"], "options": o}


def _url(f): return "/api/view?" + urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})


def _kind(fn): return "video" if fn.lower().endswith((".mp4", ".webm", ".mov")) else "image"


def files_of(hist, labels):
    """What a job made, in the tool's own order, each with its label. Previews and echoed inputs are not results."""
    out = []
    for nid, label in labels.items():
        for items in ((hist.get("outputs") or {}).get(nid) or {}).values():
            for it in items if isinstance(items, list) else []:
                if isinstance(it, dict) and it.get("filename") and it.get("type") not in ("temp", "input"):
                    out.append({"label": label, "node": nid, "filename": it["filename"], "subfolder": it.get("subfolder", ""), "url": _url(it), "kind": _kind(it["filename"])})
    return out


def alpha_files(files, out_dir=None, run=subprocess.run):
    """The plate and the matte merged into two files with a real alpha channel: ProRes 4444 (.mov, for editors) and VP9 WebM (for the web).
    Needs the outputs on this machine; returns [] with a reason when they are not."""
    plate = next((f for f in files if f["node"] == "save_plate"), None); matte = next((f for f in files if f["node"] == "save_matte"), None)
    if not plate or not matte: return [], "the plate or the matte is missing"
    root = Path(out_dir or paths.output_dir()); p, m = root / plate["subfolder"] / plate["filename"], root / matte["subfolder"] / matte["filename"]
    if not p.exists() or not m.exists(): return [], "the outputs are on another machine, so the alpha files can't be made here"
    if not shutil.which("ffmpeg"): return [], "ffmpeg is not installed"
    stem = re.sub(r"_plate.*$|plate_?", "", plate["filename"].rsplit(".", 1)[0]) or "alpha"
    merge = "[1:v]format=gray[a];[0:v][a]alphamerge"
    jobs = [(f"alpha_{stem}.mov", ["-filter_complex", merge + ",format=yuva444p10le", "-c:v", "prores_ks", "-profile:v", "4444", "-an"], "ProRes 4444 with alpha"),
            (f"alpha_{stem}.webm", ["-filter_complex", merge + ",format=yuva420p", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "28", "-auto-alt-ref", "0", "-an"], "WebM with alpha")]
    out = []
    for name, args, label in jobs:
        dest = root / plate["subfolder"] / name
        r = run(["ffmpeg", "-y", "-v", "error", "-i", str(p), "-i", str(m), *args, str(dest)], capture_output=True, text=True, timeout=600)
        if r.returncode != 0: return out, f"ffmpeg failed: {(r.stderr or '')[-200:]}"
        f = {"filename": name, "subfolder": plate["subfolder"], "type": "output"}; out.append({"label": label, "node": "alpha", **f, "url": _url(f), "kind": "video", "alpha": True})
    return out, ""


@router.get("/api/oneclick/jobs/{jid}")
def oneclick_job(jid: str):
    meta = JOBS.get(jid)
    if not meta: raise HTTPException(404, "no such job here")
    if meta.get("done"): return meta["done"]
    try: h = _comfy(f"/history/{urllib.parse.quote(jid)}").get(jid)
    except Exception: return {"status": "unknown", "detail": "ComfyUI is not reachable"}
    st = (h or {}).get("status") or {}
    if st.get("status_str") == "error":
        msg = next((i.get("exception_message", "") for k, i in st.get("messages", []) if k == "execution_error"), "")
        return {"status": "error", "error": msg.strip()[:400] or "the graph failed"}
    if not (h and (st.get("completed") or st.get("status_str") == "success")):
        try:
            q = _comfy("/queue", timeout=5); running = any(len(e) > 1 and e[1] == jid for e in q.get("queue_running", []))
        except Exception: running = False
        return {"status": "running" if running else "queued", "elapsed": round(time.time() - meta["started"], 1)}
    files = files_of(h, meta["labels"]); note = ""
    if meta["tool"] == "matte":
        with _post_lock:
            if meta.get("done"): return meta["done"]
            extra, note = alpha_files(files); files = extra + files
    meta["done"] = {"status": "done", "files": files, "note": note, "seconds": round(time.time() - meta["started"], 1), "seed": meta["seed"], "options": meta["options"], "models": meta["models"], "workflow": meta["workflow"]}
    return meta["done"]
