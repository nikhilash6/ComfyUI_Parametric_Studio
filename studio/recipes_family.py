"""One LoRA on a family's own template: the family's graph as it stands, with the LoRA put in right after its model. For LoRAs on image models outside H3, whose notes gave no one-click settings: the settings here are our own starting point, and the recipe says so."""
import json, time
from pathlib import Path
from fastapi import APIRouter
from studio import recipes as R

router = APIRouter(); DIR = Path(__file__).resolve().parent / "family_templates"

def build_graph(spec, values=None, image="check.png", seed=None):
    """The template with this step's prompt, seed, size, picture and LoRA. Pure, so a test can read it."""
    g = json.load(open(DIR / f"{spec['template']}.json")); values = values or {}
    unet = next(k for k, n in g.items() if n["class_type"] == "UNETLoader"); sampler = next(k for k, n in g.items() if n["class_type"] in ("KSampler", "SamplerCustom"))
    pos = g[sampler]["inputs"]["positive"][0]
    while "conditioning" in g[pos]["inputs"] or g[pos]["class_type"] == "WanImageToVideo": pos = g[pos]["inputs"]["conditioning" if "conditioning" in g[pos]["inputs"] else "positive"][0]
    g[pos]["inputs"]["text" if "text" in g[pos]["inputs"] else "prompt"] = R._fill(spec["prompt"], values)
    g[sampler]["inputs"]["seed" if "seed" in g[sampler]["inputs"] else "noise_seed"] = int(spec["seed"] if seed is None else seed)
    for k, n in g.items():
        if n["class_type"].startswith("Empty") and spec.get("size"): n["inputs"].update(width=spec["size"][0], height=spec["size"][1])
        if n["class_type"] == "LoadImage": n["inputs"]["image"] = image
    for nid, kv in (spec.get("set") or {}).items(): g[nid]["inputs"].update(kv)
    for i, (name, strength) in enumerate(spec.get("loras") or []):
        last = next((k for k, n in g.items() if n["class_type"] == "LoraLoaderModelOnly"), None)
        if i == 0 and last and spec.get("replace_lora"): g[last]["inputs"].update(lora_name=name, strength_model=float(strength)); continue
        nid = f"recipe_lora_{i}"; src = [unet, 0] if i == 0 else [f"recipe_lora_{i - 1}", 0]
        for n in g.values():
            for key, v in n["inputs"].items():
                if v == src: n["inputs"][key] = [nid, 0]
        g[nid] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": src, "lora_name": name, "strength_model": float(strength)}}
    return g

def _run_family_lora(run, st, spec, ctx):
    S = R._srv(); image = R._input_name(run, ctx, spec["image"], "image") if spec.get("image") else "check.png"; seed = int(spec["seed"]) + ctx["seed_add"]; st["seed"] = seed
    g = build_graph(spec, ctx["values"], image, seed)
    try: r = S.comfy("/prompt", {"prompt": g, "client_id": S.CLIENT_ID})
    except Exception as e: raise R.StepError(f"ComfyUI rejected the graph: {str(e)[:300]}") from None
    R._keep_graph(run, st, lambda: g); jid = r["prompt_id"]; S.JOBS[jid] = {"goal": "template:" + spec["template"], "prompt": spec["template"], "started": time.time(), "options": {}}
    return R._wait_job(run, st, jid)

# ---------- H3 with reference pictures or a source clip: the same nodes as the Recast goal, with the LoRA of this recipe
REF_BASE = "minimax_h3/minimax_h3_ref2va_pruned_int8_convrot.safetensors"
def h3_reference_graph(spec, values=None, pictures=(), video=None, seed=None):
    """MiniMaxH3ReferenceToVideo with up to two pictures and one clip, then the LoRA on the Ref2VA base. Pure, so a test can read it."""
    from studio.goals import WF
    import os
    t = json.load(open(os.path.join(WF, "h3_recast_api.json"))); w, h = spec.get("size") or (1024, 576); frames = int(spec.get("frames") or 73); g = {k: t[k] for k in ("unet", "clip", "vae", "avae", "noise", "dec", "guider", "sched", "ksel", "samp", "free_te")}
    ref = {"clip": ["clip", 0], "vae": ["vae", 0], "audio_vae": ["avae", 0], "prompt": R._fill(spec["prompt"], values or {}), "width": w, "height": h, "length": frames, "ref_image_size": "match"}
    for i, name in enumerate(pictures): g[f"pic{i}"] = {"class_type": "LoadImage", "inputs": {"image": name}}; ref[f"ref_images.ref_image_{i}"] = [f"pic{i}", 0]
    audio = None
    if video:
        g.update({"src": {"class_type": "LoadVideo", "inputs": {"file": video}}, "comp": {"class_type": "GetVideoComponents", "inputs": {"video": ["src", 0]}}, "trim": {"class_type": "ImageFromBatch", "inputs": {"image": ["comp", 0], "batch_index": 0, "length": frames}}, "scale": {"class_type": "ImageScale", "inputs": {"image": ["trim", 0], "upscale_method": "lanczos", "width": w, "height": h, "crop": "center"}}}); ref["ref_videos.ref_video_0"] = ["scale", 0]; audio = ["comp", 1]
    g["ref"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": ref}; g["unet"] = {**g["unet"], "inputs": {**g["unet"]["inputs"], "unet_name": REF_BASE}}
    g["lora"] = {"class_type": spec.get("loader") or "LoraLoaderBypassModelOnly", "inputs": {"model": ["unet", 0], "lora_name": spec["lora"], "strength_model": float(spec.get("strength", 1))}}
    g["guider"] = {**g["guider"], "inputs": {"model": ["lora", 0], "conditioning": ["free_te", 0]}}; g["sched"] = {**g["sched"], "inputs": {"model": ["lora", 0], "scheduler": spec.get("scheduler") or "simple", "steps": int(spec.get("steps") or 20), "denoise": 1.0}}
    g["ksel"] = {**g["ksel"], "inputs": {"sampler_name": spec.get("sampler") or "euler"}}; g["noise"] = {**g["noise"], "inputs": {"noise_seed": int(spec["seed"] if seed is None else seed)}}
    g["mk"] = {"class_type": "CreateVideo", "inputs": {"images": ["dec", 0], "fps": 24.0, **({"audio": audio} if audio else {})}}; g["save"] = {"class_type": "SaveVideo", "inputs": {"video": ["mk", 0], "filename_prefix": "h3_reference/h3_reference", "format": "auto", "codec": "auto"}}
    return g
def _run_h3_reference(run, st, spec, ctx):
    S = R._srv(); seed = int(spec["seed"]) + ctx["seed_add"]; st["seed"] = seed
    pics = [R._input_name(run, ctx, p, "image") for p in spec.get("pictures") or []]; video = R._input_name(run, ctx, spec["video"], "video") if spec.get("video") else None
    g = h3_reference_graph(spec, ctx["values"], pics, video, seed)
    try: r = S.comfy("/prompt", {"prompt": g, "client_id": S.CLIENT_ID})
    except Exception as e: raise R.StepError(f"ComfyUI rejected the graph: {str(getattr(e, 'read', lambda: e)())[:400]}") from None
    R._keep_graph(run, st, lambda: g); jid = r["prompt_id"]; S.JOBS[jid] = {"goal": "h3_reference", "prompt": spec["label"], "started": time.time(), "options": {}}
    return R._wait_job(run, st, jid)
R.EXTRA_STEPS.update(family_lora=_run_family_lora, h3_reference=_run_h3_reference)
