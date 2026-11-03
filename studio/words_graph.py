"""One builder for every "Which word painted what" graph: API format, ComfyUI core nodes plus our two PSN attention nodes.
The proof renders (scripts/attention_maps_renders.py), the page's copy button and POST /api/words/run all use it, so what the page shows is what ran.
With record=False it is the same graph without the recorder, which the proof uses to show the picture does not change. Standard library only."""
MODELS = {
    "sd15": {"name": "SD 1.5", "ckpt": "v1-5-pruned-emaonly.safetensors", "size": 512, "licence": "CreativeML OpenRAIL-M"},
    "sdxl": {"name": "SDXL base 1.0", "ckpt": "sd_xl_base_1.0.safetensors", "size": 1024, "licence": "CreativeML OpenRAIL++-M"},
}
NEGATIVE = "blurry, low quality, watermark, text"; SEED = 424242; STEPS = 20; CFG = 7.0; SAMPLER = "dpmpp_2m"; SCHEDULER = "karras"
PICTURE, SHEET, MAPS = "9", "11", "10"          # node ids the page reads back: the picture, the sheet, the maps node


def build(r, record=True):
    """r: model, prompt, seed, steps, cfg, id. -> a graph for ComfyUI's /prompt."""
    m = MODELS[r["model"]]; tag = str(r.get("id") or "run"); model = ["2", 0] if record else ["1", 0]
    g = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": m["ckpt"]}}}
    if record: g["2"] = {"class_type": "PSN_AttentionRecord", "inputs": {"model": ["1", 0]}}
    g["3"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": r["prompt"]}}
    g["4"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": r.get("negative", NEGATIVE)}}
    g["5"] = {"class_type": "EmptyLatentImage", "inputs": {"width": m["size"], "height": m["size"], "batch_size": 1}}
    g["6"] = {"class_type": "KSampler", "inputs": {"model": model, "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0], "seed": int(r.get("seed", SEED)), "steps": int(r.get("steps", STEPS)),
                                                  "cfg": float(r.get("cfg", CFG)), "sampler_name": r.get("sampler", SAMPLER), "scheduler": r.get("scheduler", SCHEDULER), "denoise": 1.0}}
    g["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}}
    g[PICTURE] = {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": f"words/{tag}{'' if record else '-plain'}"}}
    if record:
        g[MAPS] = {"class_type": "PSN_AttentionMaps", "inputs": {"attention": ["2", 1], "clip": ["1", 1], "text": r["prompt"], "image": ["8", 0], "skip_punctuation": True}}
        g[SHEET] = {"class_type": "SaveImage", "inputs": {"images": [MAPS, 0], "filename_prefix": f"words/{tag}-sheet"}}
    return g
