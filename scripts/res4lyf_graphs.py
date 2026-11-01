#!/usr/bin/env python3
"""Builds and runs the RES4LYF graphs behind the studio's page, against one private ComfyUI instance with the pack loaded.

Writes API graphs to docs/res4lyf/graphs and images plus results.json to studio/web/res4lyf_renders.
Refuses the live ports. One seed for everything, and every result is kept: no re-rolls.
Usage: res4lyf_graphs.py http://127.0.0.1:8683 /path/to/instance sd15,sdxl,flux [name,name]
"""
import json
import pathlib
import shutil
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RENDERS = ROOT / "studio" / "web" / "res4lyf_renders"
GRAPHS = RENDERS / "graphs"
LIVE_PORTS = {8200, 8322, 8002, 8086, 8300}
SEED = 4242
SUBJECT = "a red lighthouse on a rocky coast at dusk, waves, dramatic clouds, oil painting"
STYLE = "abstract swirling brushstrokes in deep blue and gold, thick impasto, starry night sky"
WINTER = "a red lighthouse on a rocky coast in deep winter, snow on the rocks, oil painting"
LEFT, RIGHT = "a red lighthouse, oil painting", "a snowy pine forest, oil painting"
MOTION = "a red lighthouse on a rocky coast at dusk, waves crashing, clouds drifting, cinematic"
NEGATIVE = "low quality, blurry, jpeg artifacts"
PROFILES = {
    "sd15": {"label": "Stable Diffusion 1.5 (DreamShaper 8)", "ckpt": "DreamShaper_8_pruned.safetensors", "size": 512, "steps": 20, "cfg": 6.5, "patch": "ReSDPatcher", "latent": "EmptyLatentImage"},
    "sdxl": {"label": "SDXL 1.0 base", "ckpt": "sd_xl_base_1.0.safetensors", "size": 1024, "steps": 20, "cfg": 6.5, "patch": "ReSDPatcher", "latent": "EmptyLatentImage"},
    "wan": {"label": "Wan 2.2 TI2V 5B (video)", "unet": "wan2.2_ti2v_5B_fp16.safetensors", "te": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "vae": "wan2.2_vae.safetensors", "size": 704, "steps": 20, "cfg": 5.0},
    "flux": {"label": "FLUX.1 schnell", "unet": "flux1-schnell.safetensors", "clip": ("clip_l.safetensors", "t5xxl_fp16.safetensors"), "vae": "ae.safetensors", "size": 1024, "steps": 8, "cfg": 1.0, "patch": "ReFluxPatcher", "latent": "EmptySD3LatentImage"},
}
P = PROFILES["sd15"]
MODEL, CLIP, VAE = ["ck", 0], ["ck", 1], ["ck", 2]


def clip_ref():
    return CLIP if "ckpt" in P else ["ck_clip", 0]


def vae_ref():
    return VAE if "ckpt" in P else ["ck_vae", 0]


def base(g):
    if "ckpt" in P:
        g["ck"] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": P["ckpt"]}}
    else:
        g["ck"] = {"class_type": "UNETLoader", "inputs": {"unet_name": P["unet"], "weight_dtype": "default"}}
        g["ck_clip"] = {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": P["clip"][0], "clip_name2": P["clip"][1], "type": "flux"}}
        g["ck_vae"] = {"class_type": "VAELoader", "inputs": {"vae_name": P["vae"]}}
    g["neg"] = text(NEGATIVE)
    g["empty"] = {"class_type": P["latent"], "inputs": {"width": P["size"], "height": P["size"], "batch_size": 1}}
    return g


def text(t):
    return {"class_type": "CLIPTextEncode", "inputs": {"text": t, "clip": clip_ref()}}


def clown(sampler, pos="pos", latent="empty", model="ck", **kw):
    i = {"eta": 0.5, "sampler_name": sampler, "scheduler": "beta57", "steps": P["steps"], "steps_to_run": -1, "denoise": 1.0, "cfg": P["cfg"], "seed": SEED, "sampler_mode": "standard", "bongmath": True,
         "model": [model, 0], "positive": [pos, 0], "negative": ["neg", 0], "latent_image": [latent, 0]}
    i.update(kw)
    return {"class_type": "ClownsharKSampler_Beta", "inputs": i}


def out(g, name, latent):
    g["dec"] = {"class_type": "VAEDecode", "inputs": {"samples": [latent, 0], "vae": vae_ref()}}
    g["save"] = {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": "res4lyf_" + PROFILE + "_" + name}}
    return g


def encode(key, image):
    return {key + "_img": {"class_type": "LoadImage", "inputs": {"image": image}},
            key: {"class_type": "VAEEncode", "inputs": {"pixels": [key + "_img", 0], "vae": vae_ref()}}}


def control():
    g = base({"pos": None})
    g["pos"] = text(SUBJECT)
    g["s"] = {"class_type": "KSampler", "inputs": {"model": ["ck", 0], "seed": SEED, "steps": P["steps"], "cfg": P["cfg"], "sampler_name": "euler", "scheduler": "normal", "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["empty", 0], "denoise": 1.0}}
    return out(g, "control", "s")


def plain(name, sampler, prompt=SUBJECT, **kw):
    g = base({})
    g["pos"] = text(prompt)
    g["s"] = clown(sampler, **kw)
    return out(g, name, "s")


def chain():
    g = base({})
    g["pos"] = text(SUBJECT)
    g["a"] = clown("multistep/res_2m", steps_to_run=P["steps"] * 2 // 5)
    g["s"] = {"class_type": "ClownsharkChainsampler_Beta", "inputs": {"eta": 0.5, "sampler_name": "exponential/res_3s", "steps_to_run": -1, "cfg": P["cfg"], "sampler_mode": "resample", "bongmath": True, "latent_image": ["a", 0]}}
    return out(g, "chain", "s")


def style():
    g = base({})
    g["pos"] = text(SUBJECT)
    g["patched"] = {"class_type": P["patch"], "inputs": {"model": ["ck", 0], "style_dtype": "float64", "enable": True}}
    g.update(encode("ref", "res4lyf_style_ref_" + PROFILE + ".png"))
    g["guide"] = {"class_type": "ClownGuide_Style_Beta", "inputs": {"apply_to": "positive", "method": "WCT", "weight": 1.0, "synweight": 1.0, "weight_scheduler": "constant", "start_step": 0, "end_step": -1, "invert_mask": False, "guide": ["ref", 0]}}
    g["s"] = clown("exponential/res_2s", model="patched", guides=["guide", 0])
    return out(g, "style", "s")


def unsample():
    g = base({})
    g["pos"] = text(SUBJECT)
    g["new"] = text(WINTER)
    g.update(encode("src", "res4lyf_source_" + PROFILE + ".png"))
    g["g_un"] = {"class_type": "ClownGuide_Beta", "inputs": {"guide_mode": "epsilon", "channelwise_mode": False, "projection_mode": True, "weight": 0.5, "cutoff": 1.0, "weight_scheduler": "beta57", "start_step": 0, "end_step": P["steps"] // 2, "invert_mask": False, "guide": ["src", 0]}}
    g["a"] = clown("multistep/res_3m", latent="src", cfg=1.0, sampler_mode="unsample", seed=0, guides=["g_un", 0])
    g["s"] = {"class_type": "ClownsharkChainsampler_Beta", "inputs": {"eta": 0.5, "sampler_name": "multistep/res_3m", "steps_to_run": -1, "cfg": P["cfg"], "sampler_mode": "resample", "bongmath": True, "latent_image": ["a", 0], "positive": ["new", 0]}}
    return out(g, "unsample", "s")


def regional():
    g = base({})
    g["left"], g["right"] = text(LEFT), text(RIGHT)
    g["patched"] = {"class_type": P["patch"], "inputs": {"model": ["ck", 0], "style_dtype": "float64", "enable": True}}
    g["m0"] = {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": P["size"], "height": P["size"]}}
    g["m1"] = {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": P["size"] // 2, "height": P["size"]}}
    g["mask"] = {"class_type": "MaskComposite", "inputs": {"destination": ["m0", 0], "source": ["m1", 0], "x": 0, "y": 0, "operation": "add"}}
    g["pos"] = {"class_type": "ClownRegionalConditioning2", "inputs": {"weight": 1.0, "region_bleed": 0.0, "region_bleed_start_step": 0, "weight_scheduler": "constant", "start_step": 0, "end_step": -1, "mask_type": "boolean_masked", "edge_width": 32, "invert_mask": False, "conditioning_masked": ["left", 0], "conditioning_unmasked": ["right", 0], "mask": ["mask", 0]}}
    g["s"] = clown("exponential/res_2s", model="patched")
    return out(g, "regional", "s")


def redux_parts(g, image):
    g["pos_text"] = text(SUBJECT)
    g["sm"] = {"class_type": "StyleModelLoader", "inputs": {"style_model_name": "flux/flux1-redux-dev.safetensors"}}
    g["cv"] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "SIG CLIP/SIGLIP 384/sigclip_vision_patch14_384.safetensors"}}
    g["ref_img"] = {"class_type": "LoadImage", "inputs": {"image": image}}
    g["vis"] = {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["cv", 0], "image": ["ref_img", 0], "crop": "center"}}


def redux():
    g = base({})
    redux_parts(g, "res4lyf_style_ref_flux.png")
    g["pos"] = {"class_type": "StyleModelApply", "inputs": {"conditioning": ["pos_text", 0], "style_model": ["sm", 0], "clip_vision_output": ["vis", 0], "strength": 1.0, "strength_type": "multiply"}}
    g["s"] = clown("multistep/res_2m")
    return out(g, "redux", "s")


def redux_style():
    g = base({})
    redux_parts(g, "res4lyf_style_ref_flux.png")
    g["patched_style"] = {"class_type": "ReReduxPatcher", "inputs": {"style_model": ["sm", 0], "style_dtype": "float64", "enable": True}}
    g["pos"] = {"class_type": "StyleModelApply", "inputs": {"conditioning": ["pos_text", 0], "style_model": ["patched_style", 0], "clip_vision_output": ["vis", 0], "strength": 1.0, "strength_type": "multiply"}}
    g["s"] = clown("multistep/res_2m")
    return out(g, "redux_style", "s")


def wan():
    g = {"ck": {"class_type": "UNETLoader", "inputs": {"unet_name": P["unet"], "weight_dtype": "default"}}}
    g["ck_clip"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": P["te"], "type": "wan"}}
    g["ck_vae"] = {"class_type": "VAELoader", "inputs": {"vae_name": P["vae"]}}
    g["pos"], g["neg"] = text(MOTION), text("static, blurry, low quality")
    g["empty"] = {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["ck_vae", 0], "width": 704, "height": 480, "length": 49, "batch_size": 1}}
    g["s"] = clown("multistep/res_2m")
    g["dec"] = {"class_type": "VAEDecode", "inputs": {"samples": ["s", 0], "vae": ["ck_vae", 0]}}
    g["save"] = {"class_type": "SaveAnimatedWEBP", "inputs": {"images": ["dec", 0], "filename_prefix": "res4lyf_wan_res_2m", "fps": 16.0, "lossless": False, "quality": 82, "method": "default"}}
    return g


def calls_for(name):
    n = P["steps"]
    k = n * 2 // 5
    return {"res_2s": n * 2, "res_3s": n * 3, "chain": k + (n - k) * 3, "style": n * 2, "unsample": n * 2, "regional": n * 2}.get(name, n)


# name: (graph, what it shows). Order matters: later graphs use earlier images as inputs.
PLAN = [
    ("control", control, "Plain ComfyUI KSampler, Euler, normal schedule. Not the pack: the comparison point."),
    ("beta57", lambda: plain("beta57", "linear/euler"), "ClownsharKSampler with Euler on the beta57 schedule."),
    ("res_2m", lambda: plain("res_2m", "multistep/res_2m"), "ClownsharKSampler, res_2m on beta57."),
    ("res_2s", lambda: plain("res_2s", "exponential/res_2s"), "ClownsharKSampler, res_2s on beta57."),
    ("res_3s", lambda: plain("res_3s", "exponential/res_3s"), "ClownsharKSampler, res_3s on beta57."),
    ("chain", chain, "Chained samplers: res_2m for the first steps, then a Chainsampler finishes with res_3s."),
    ("style_ref", lambda: plain("style_ref", "multistep/res_2m", prompt=STYLE), "The reference image for the style graph, also made with the pack."),
    ("style", style, "Style transfer: ClownGuide Style (WCT) with the reference, same subject prompt."),
    ("unsample", unsample, "Unsample the res_2m image, then resample it with a winter prompt."),
    ("regional", regional, "Regional conditioning: lighthouse prompt on the left half, forest on the right."),
]


EXTRA = {"flux": [
    ("redux", redux, "Redux with ComfyUI's own StyleModelApply: the style reference joins the prompt as extra image tokens."),
    ("redux_style", redux_style, "The pack's ReReduxPatcher in front of the same node, on the same reference. Byte for byte the same image as the plain Redux render, so it changed nothing here."),
]}
WAN_PLAN = [("res_2m", wan, "Video: ClownsharKSampler, res_2m on beta57, 49 frames at 704x480.")]


def call(url, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def run(url, name, graph, wait=5400):
    t0 = time.time()
    pid = call(url, "/prompt", {"prompt": graph})["prompt_id"]
    while time.time() - t0 < wait:
        h = call(url, "/history/" + pid).get(pid)
        if h and h.get("status", {}).get("completed"):
            imgs = [i for o in h["outputs"].values() for i in o.get("images", [])]
            return {"ok": True, "seconds": round(time.time() - t0, 1), "images": imgs, "prompt_id": pid}
        if h and h.get("status", {}).get("status_str") == "error":
            msgs = [m[1].get("exception_message", "")[:400] for m in h["status"].get("messages", []) if m[0] == "execution_error"]
            return {"ok": False, "seconds": round(time.time() - t0, 1), "error": " ".join(msgs)}
        time.sleep(3)
    return {"ok": False, "seconds": wait, "error": "timed out"}


def main():
    global P, PROFILE
    url, inst, wanted = sys.argv[1].rstrip("/"), pathlib.Path(sys.argv[2]), sys.argv[3].split(",")
    only = sys.argv[4].split(",") if len(sys.argv) > 4 else None
    if urllib.parse.urlparse(url).port in LIVE_PORTS:
        raise SystemExit("refusing a live port")
    GRAPHS.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    rp = RENDERS / "results.json"
    results = json.loads(rp.read_text()) if rp.exists() else {}
    device = call(url, "/system_stats")["devices"][0]["name"]
    for PROFILE in wanted:
        P = PROFILES[PROFILE]
        for name, make, what in ({"wan": WAN_PLAN}.get(PROFILE, PLAN + EXTRA.get(PROFILE, []))):
            if only and name not in only:
                continue
            key = f"{PROFILE}_{name}"
            graph = make()
            (GRAPHS / f"{key}.json").write_text(json.dumps(graph, indent=1))
            try:
                r = run(url, key, graph)
            except Exception as e:  # A rejected graph answers HTTP 400 with the reason in its body.
                r = {"ok": False, "seconds": 0, "error": (e.read().decode()[:600] if hasattr(e, "read") else str(e))}
            if r["ok"]:
                img = r.pop("images")[0]
                src = inst / "output" / img.get("subfolder", "") / img["filename"]
                shutil.copy(src, RENDERS / f"{key}{src.suffix}")
                if name == "res_2m":
                    shutil.copy(src, inst / "input" / f"res4lyf_source_{PROFILE}.png")
                if name == "style_ref":
                    shutil.copy(src, inst / "input" / f"res4lyf_style_ref_{PROFILE}.png")
            results[key] = {**r, "family": P["label"], "name": name, "what": what, "calls": calls_for(name), "seed": SEED, "steps": P["steps"], "cfg": P["cfg"], "size": P["size"], "device": device, "graph": f"res4lyf_renders/graphs/{key}.json", "pack_commit": "56e4475"}
            rp.write_text(json.dumps(results, indent=1))
            print(key, "ok" if r["ok"] else "FAILED", r["seconds"], r.get("error", "")[:300], flush=True)


if __name__ == "__main__":
    main()
