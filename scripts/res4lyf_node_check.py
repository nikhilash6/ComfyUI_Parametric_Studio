#!/usr/bin/env python3
"""Puts every RES4LYF node into a real graph of its own on a private ComfyUI instance, renders it and records what happened.

Each node gets the simplest inputs its declared types allow, with its own defaults for everything else, and its output is
wired into a render: sigmas, guides, options, models, conditioning and latents into a ClownsharKSampler; samplers into a
SharkSampler; images and masks straight to a saved image. Anything else is previewed as text.

So "rendered" means the graph ran end to end with those settings. It does not mean they suit any real job, and a bad-looking
picture is often only a poor default for this setup. Writes studio/web/res4lyf_node_check.json and res4lyf_renders/nodes/.
Refuses the live ports. One seed, no re-rolls.
Usage: res4lyf_node_check.py http://127.0.0.1:8683 /path/to/instance [--only name,name]
"""
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

WEB = pathlib.Path(__file__).resolve().parent.parent / "studio" / "web"
OUT, THUMBS = WEB / "res4lyf_node_check.json", WEB / "res4lyf_renders" / "nodes"
LIVE_PORTS = {8200, 8322, 8002, 8086, 8300}
CKPT, SIZE, STEPS, SEED, CFG = "DreamShaper_8_pruned.safetensors", 512, 12, 4242, 6.5
PROMPT = "a red lighthouse on a rocky coast at dusk, waves, dramatic clouds, oil painting"
SOURCES = {
    "MODEL": ("ck", 0), "CLIP": ("ck", 1), "VAE": ("ck", 2), "LATENT": ("src", 0), "CONDITIONING": ("pos", 0), "SIGMAS": ("sig", 0),
    "IMAGE": ("img", 0), "MASK": ("mask", 0), "SAMPLER": ("smp", 0), "GUIDES": ("guide", 0), "OPTIONS": ("opt", 0),
    "STYLE_MODEL": ("style", 0), "CLIP_VISION_OUTPUT": ("vis", 0),
}
OPTIONAL_WIRED = {"MODEL", "CLIP", "VAE", "LATENT", "CONDITIONING", "IMAGE"}
BASE = {
    "ck": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
    "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": PROMPT, "clip": ["ck", 1]}},
    "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": "low quality, blurry", "clip": ["ck", 1]}},
    "empty": {"class_type": "EmptyLatentImage", "inputs": {"width": SIZE, "height": SIZE, "batch_size": 1}},
    "img": {"class_type": "LoadImage", "inputs": {"image": "res4lyf_source_sd15.png"}},
    "src": {"class_type": "VAEEncode", "inputs": {"pixels": ["img", 0], "vae": ["ck", 2]}},
    "sig": {"class_type": "BasicScheduler", "inputs": {"model": ["ck", 0], "scheduler": "normal", "steps": STEPS, "denoise": 1.0}},
    "m0": {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": SIZE, "height": SIZE}},
    "m1": {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": SIZE // 2, "height": SIZE}},
    "mask": {"class_type": "MaskComposite", "inputs": {"destination": ["m0", 0], "source": ["m1", 0], "x": 0, "y": 0, "operation": "add"}},
    "style": {"class_type": "StyleModelLoader", "inputs": {"style_model_name": "flux/flux1-redux-dev.safetensors"}},
    "vision": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "SIG CLIP/SIGLIP 384/sigclip_vision_patch14_384.safetensors"}},
    "vis": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["vision", 0], "image": ["img", 0], "crop": "center"}},
    "smp": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
    "guide": {"class_type": "ClownGuide_Beta", "inputs": {"guide_mode": "epsilon", "channelwise_mode": True, "projection_mode": True, "weight": 0.75, "cutoff": 1.0, "weight_scheduler": "beta57", "start_step": 0, "end_step": STEPS // 2, "invert_mask": False, "guide": ["src", 0]}},
    "opt": {"class_type": "ClownOptions_SDE_Beta", "inputs": {"noise_type_sde": "gaussian", "noise_type_sde_substep": "gaussian", "noise_mode_sde": "hard", "noise_mode_sde_substep": "hard", "eta": 0.5, "eta_substep": 0.5, "seed": SEED}},
}
SMALL = {"steps": STEPS, "steps_to_run": -1, "end_step": STEPS // 2, "width": SIZE, "height": SIZE, "batch_size": 1, "seed": SEED, "noise_seed": SEED}
# Where each output type plugs into the render, most useful first.
PRIORITY = ("SIGMAS", "GUIDES", "OPTIONS", "MODEL", "CONDITIONING", "LATENT", "SAMPLER", "IMAGE", "MASK")
SLOT = {"SIGMAS": "sigmas", "GUIDES": "guides", "OPTIONS": "options_group.options0", "MODEL": "model", "CONDITIONING": "positive", "LATENT": "latent_image"}


def literal(name, spec):
    t, o = spec[0], spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
    if name in SMALL and t == "INT":
        return True, SMALL[name]
    if "default" in o:
        return True, o["default"]
    if isinstance(t, list):
        return bool(t), t[0] if t else None
    if t == "COMBO":
        opts = o.get("options") or []
        return bool(opts), opts[0] if opts else None
    return {"INT": (True, 0), "FLOAT": (True, 0.0), "BOOLEAN": (True, False), "STRING": (True, "")}.get(t, (False, None))


def sampler(**over):
    i = {"eta": 0.5, "sampler_name": "multistep/res_2m", "scheduler": "beta57", "steps": STEPS, "steps_to_run": -1, "denoise": 1.0, "cfg": CFG, "seed": SEED, "sampler_mode": "standard", "bongmath": True,
         "model": ["ck", 0], "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["empty", 0]}
    i.update(over)
    return {"class_type": "ClownsharKSampler_Beta", "inputs": i}


def graph_for(name, info):
    g = {k: {"class_type": v["class_type"], "inputs": dict(v["inputs"])} for k, v in BASE.items()}
    node, missing = {}, []
    for section in ("required", "optional"):
        for arg, spec in (info["input"].get(section) or {}).items():
            t = spec[0]
            if t == "COMFY_AUTOGROW_V3":
                inner = spec[1]["template"]["input"]
                if section == "required" and "options" in (inner.get("required") or {}):
                    node[arg + ".options0"] = ["opt", 0]
                continue
            if isinstance(t, str) and t in SOURCES and (section == "required" or t in OPTIONAL_WIRED):
                node[arg] = list(SOURCES[t])
            elif section == "required":
                ok, value = literal(arg, spec)
                if ok:
                    node[arg] = value
                else:
                    missing.append(str(t))
    if missing:
        return None, "", "needs " + ", ".join(sorted(set(missing)))
    g["n"] = {"class_type": name, "inputs": node}
    outs = [t if isinstance(t, str) else "COMBO" for t in (info.get("output") or [])]
    wired = next((t for t in PRIORITY if t in outs), None)
    if wired in SLOT:
        over = {SLOT[wired]: ["n", outs.index(wired)]}
        if wired == "LATENT":
            over["denoise"] = 0.6
        g["s"] = sampler(**over)
        image = ["dec", 0]
    elif wired == "SAMPLER":
        g["s"] = {"class_type": "SharkSampler_Beta", "inputs": {"scheduler": "beta57", "steps": STEPS, "steps_to_run": -1, "denoise": 1.0, "cfg": CFG, "seed": SEED, "sampler_mode": "standard", "model": ["ck", 0], "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["empty", 0], "sampler": ["n", outs.index("SAMPLER")]}}
        image = ["dec", 0]
    elif wired == "IMAGE":
        image = ["n", outs.index("IMAGE")]
    elif wired == "MASK":
        g["m2i"] = {"class_type": "MaskToImage", "inputs": {"mask": ["n", outs.index("MASK")]}}
        image = ["m2i", 0]
    else:
        image = None
    if image:
        if image[0] == "dec":
            g["dec"] = {"class_type": "VAEDecode", "inputs": {"samples": ["s", 0], "vae": ["ck", 2]}}
        g["save"] = {"class_type": "SaveImage", "inputs": {"images": image, "filename_prefix": "res4lyf_node"}}
    elif outs:
        for i in range(len(outs)):
            g[f"p{i}"] = {"class_type": "PreviewAny", "inputs": {"source": ["n", i]}}
    elif not info.get("output_node"):
        return None, "", "no outputs"
    # Keep only what the output reaches, so an unused source isn't loaded.
    sinks = [k for k in g if k == "save" or k.startswith("p") and k[1:].isdigit()] or ["n"]
    keep, stack = set(), sinks
    while stack:
        k = stack.pop()
        if k not in keep:
            keep.add(k)
            stack = stack + [v[0] for v in g[k]["inputs"].values() if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and v[0] in g]
    return {k: g[k] for k in keep}, (wired or ""), ""


def call(url, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def run(url, graph, wait=120):
    t0 = time.time()
    try:
        pid = call(url, "/prompt", {"prompt": graph})["prompt_id"]
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            body = json.loads(raw or "{}")
        except ValueError:
            return "rejected", raw[:300], None
        errs = [x.get("message", "") + ": " + x.get("details", "") for v in (body.get("node_errors") or {}).values() for x in v.get("errors", [])]
        return "rejected", "; ".join(errs)[:300] or str(body.get("error", ""))[:300], None
    while time.time() - t0 < wait:
        h = call(url, "/history/" + pid).get(pid)
        if h and h.get("status", {}).get("completed"):
            imgs = [i for o in h["outputs"].values() for i in o.get("images", [])]
            return "ran", "", imgs[0] if imgs else None
        if h and h.get("status", {}).get("status_str") == "error":
            msg = [m[1].get("exception_type", "") + ": " + m[1].get("exception_message", "") for m in h["status"].get("messages", []) if m[0] == "execution_error"]
            return "error", " ".join(msg)[:300], None
        time.sleep(0.4)
    urllib.request.urlopen(urllib.request.Request(url + "/interrupt", data=b"{}", headers={"Content-Type": "application/json"}), timeout=30).read()
    return "timeout", f"over {wait}s", None


def safe(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name)


def main():
    url, inst = sys.argv[1].rstrip("/"), pathlib.Path(sys.argv[2])
    if urllib.parse.urlparse(url).port in LIVE_PORTS:
        raise SystemExit("refusing a live port")
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    THUMBS.mkdir(parents=True, exist_ok=True)
    info = call(url, "/object_info")
    device = call(url, "/system_stats")["devices"][0]["name"]
    pack = {n: v for n, v in info.items() if "RES4LYF" in str(v.get("python_module", ""))}
    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    for name in sorted(pack, key=str.lower):
        if only and name not in only:
            continue
        if not only and name in results:
            continue
        graph, wired, why = graph_for(name, pack[name])
        if str(pack[name].get("category")) == "RES4LYF/loaders":
            r = {"state": "skipped", "detail": "loads a whole model chosen by its own settings"}
        elif graph is None:
            r = {"state": "needs", "detail": why}
        else:
            (THUMBS / f"{safe(name)}.json").write_text(json.dumps(graph, indent=1))
            state, detail, img = run(url, graph)
            r = {"state": "rendered" if img else state, "detail": detail, "wired": wired, "graph": f"res4lyf_renders/nodes/{safe(name)}.json"}
            if img:
                src = inst / "output" / img.get("subfolder", "") / img["filename"]
                im = Image.open(src).convert("RGB")
                im.thumbnail((256, 256))
                im.save(THUMBS / f"{safe(name)}.jpg", quality=78)
                r["thumb"] = f"res4lyf_renders/nodes/{safe(name)}.jpg"
        r["device"] = device
        results[name] = r
        OUT.write_text(json.dumps(results, indent=0, sort_keys=True))
        print(name, r["state"], r["detail"][:110], flush=True)
    counts = {}
    for r in results.values():
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    print(counts)


if __name__ == "__main__":
    main()
