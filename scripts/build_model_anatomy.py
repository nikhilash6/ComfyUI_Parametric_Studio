#!/usr/bin/env python3
"""Builds the Model Anatomy cache: every model file's header, read without a GPU and without loading a weight, so the page and the read-only demo can show it.
Usage: build_model_anatomy.py [--map MODEL_USE_MAP.tsv] [--models DIR] [--out studio/anatomy]
--map is the studio's list of model files (columns file, on_disk, disk_path, family). Without it, every file under --models is read.
Paths come from $PSN_MODEL_USE_MAP and $COMFYUI_MODELS_DIR when the flags are left out. The output holds paths relative to the models folder only."""
import argparse, collections, csv, datetime, gzip, hashlib, json, os, re, sys, time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from studio import anatomy as A, sfw  # noqa: E402

COMFY_FOLDERS = ("checkpoints", "diffusion_models", "unet", "loras", "vae", "vae_approx", "text_encoders", "clip", "clip_vision", "controlnet", "model_patches", "upscale_models", "latent_upscale_models", "embeddings", "style_models", "gligen", "hypernetworks", "photomaker", "audio_encoders", "TTS", "LLM", "sams", "ultralytics")
EXT = A.READ_EXT + A.PICKLE_EXT + (".onnx", ".pb", ".json")
# Side by side on the page. Picked by file name, and left out when the file isn't here.
PRESETS = [
    {"id": "video-and-image", "label": "Klein 4B, H3, Wan 2.2, LTX-2.5", "files": ["flux-2-klein-4b.safetensors", "MiniMax_H3_FL2VA_pruned_nvfp4.safetensors", "Wan2_2-T2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors", "ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors"]},
    {"id": "image-sizes", "label": "SD 1.5, SDXL, Klein 4B, Klein 9B", "files": ["v1-5-pruned-emaonly.safetensors", "sd_xl_base_1.0.safetensors", "flux-2-klein-4b.safetensors", "flux-2-klein-9b.safetensors"]},
    {"id": "same-model-three-ways", "label": "Three video models, three formats: fp16, fp8, GGUF Q8_0", "files": ["wan2.2_ti2v_5B_fp16.safetensors", "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "SkyReels-v3-r2v-Q8_0.gguf"]},
]


def folder_of(rel):
    for p in rel.split("/")[:-1]:
        if p in COMFY_FOLDERS: return p
    return rel.split("/")[0] if "/" in rel else ""


def unsafe_name(name):
    """Left out by file name: the studio's SFW words, and files named for celebrity likeness."""
    words = re.sub(r"[_.\-]+", " ", name)
    return sfw.flagged(words) or bool(re.search(r"celeb", words, re.I))


def rows_from_map(path, models):
    out = []
    for r in csv.DictReader(open(path, encoding="utf8"), delimiter="\t"):
        p = (r.get("disk_path") or "").strip()
        if r.get("on_disk") != "yes" or not p: continue
        if not os.path.abspath(p).startswith(models + os.sep): continue
        out.append({"path": p, "family": (r.get("family") or "").strip(), "gb": r.get("gb")})
    return out


def rows_from_walk(models):
    out = []
    for d, _, fs in os.walk(models, followlinks=True):
        for f in fs:
            if f.lower().endswith(EXT) and not f.endswith(".json"): out.append({"path": os.path.join(d, f), "family": "", "gb": None})
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--map", default=os.environ.get("PSN_MODEL_USE_MAP", "")); ap.add_argument("--models", default=os.environ.get("COMFYUI_MODELS_DIR", "")); ap.add_argument("--out", default=os.path.join(ROOT, "studio", "anatomy")); a = ap.parse_args()
    if not a.models: sys.exit("Say where the models are: --models DIR or $COMFYUI_MODELS_DIR.")
    models = os.path.abspath(a.models); t0 = time.time()
    rows = rows_from_map(a.map, models) if a.map else rows_from_walk(models)
    by_real, skipped_names, missing = {}, 0, 0
    for r in rows:
        rel = os.path.relpath(os.path.abspath(r["path"]), models)
        if unsafe_name(os.path.basename(rel)): skipped_names += 1; continue
        try: real = os.path.realpath(r["path"]); os.stat(real)
        except OSError: missing += 1; continue
        if real in by_real: by_real[real]["also"].append(rel); continue
        by_real[real] = {"rel": rel, "family": r["family"], "gb": r["gb"], "also": []}
    full, index, sigs, header_read = {}, [], {}, 0
    for real, r in sorted(by_real.items(), key=lambda kv: kv[1]["rel"].lower()):
        x = A.analyse(real, r["rel"]); x["id"] = A.sid(r["rel"]); x["folder"] = folder_of(r["rel"])
        if r["family"]: x["family"] = r["family"]
        if r["also"]: x["also"] = sorted(r["also"])
        if x.get("read"):
            header_read += x["header_bytes"]
            sig = hashlib.sha1(json.dumps([x["size"], x["tree"]], sort_keys=True).encode()).hexdigest()
            if sig in sigs: x["same_header_as"] = sigs[sig]
            else: sigs[sig] = x["id"]
        full[x["id"]] = x
        s = A.summary(x); s["folder"] = x["folder"]; index.append(s)
    present = {x["file"]: x["id"] for x in full.values() if x.get("read")}
    presets = [{"id": p["id"], "label": p["label"], "ids": [present[f] for f in p["files"] if f in present]} for p in PRESETS]
    presets = [p for p in presets if len(p["ids"]) >= 2]
    read = [x for x in full.values() if x.get("read")]
    why = collections.Counter("pickle" if "pickle" in x["why"] else "failed" if "didn't read" in x["why"] else "other" for x in full.values() if not x.get("read"))
    head = {"built": datetime.date.today().isoformat(), "files": len(full), "read": len(read), "not_read": dict(why), "skipped_names": skipped_names, "missing": missing,
            "weights": sum(x["weights"] for x in read), "data_bytes": sum(x["data_bytes"] for x in read), "file_bytes": sum(x["size"] for x in full.values()), "header_bytes": header_read,
            "formats": dict(collections.Counter(x["format"] for x in full.values())), "loras": sum(1 for x in read if x.get("lora")), "presets": presets,
            "source": "the studio's model list" if a.map else "every file in the models folder", "seconds": round(time.time() - t0, 1)}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "index.json"), "w", encoding="utf8") as f: json.dump({**head, "models": index}, f, separators=(",", ":"))
    with gzip.open(os.path.join(a.out, "models.json.gz"), "wt", encoding="utf8", compresslevel=9) as f: json.dump(full, f, separators=(",", ":"))
    print(f"{len(full)} files, {len(read)} headers read ({header_read >> 20} MB of headers for {head['file_bytes'] >> 30} GB of files) in {head['seconds']} s; {skipped_names} left out by name, {missing} missing")


if __name__ == "__main__": main()
