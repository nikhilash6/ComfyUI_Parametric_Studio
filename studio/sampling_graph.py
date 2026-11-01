"""One builder for every Sampling Lab graph: API format, ComfyUI core nodes only, one change from the baseline.
The proof sweep (scripts/sampling_lab_renders.py), the page's "copy this graph" button and POST /api/sampling/run all use it, so what the page shows is what ran. Standard library only."""
PROMPT = "a weathered brass astrolabe on an oak table beside a stack of old sea charts, warm window light, shallow depth of field, fine engraving detail, photograph"
NEGATIVE = "blurry, low quality, watermark, text"; SEED = 424242; STEPS = 20
MODELS = {
    "sd15": {"name": "SD 1.5", "ckpt": "v1-5-pruned-emaonly.safetensors", "size": 512, "licence": "CreativeML OpenRAIL-M", "kind": "eps"},
    "sdxl": {"name": "SDXL base 1.0", "ckpt": "sd_xl_base_1.0.safetensors", "size": 1024, "licence": "CreativeML OpenRAIL++-M", "kind": "eps"},
    "sd35": {"name": "SD 3.5 Medium", "ckpt": "sd3/sd3.5_medium.safetensors", "size": 1024, "licence": "Stability AI Community", "kind": "flow", "clips": ["clip_l.safetensors", "clip_g.safetensors", "t5xxl_fp16.safetensors"], "vae": "taesd3", "note": "Decoded with the small TAESD3 preview VAE, because no full SD3 VAE is on disk."},
}
# The sampler and scheduler names ComfyUI core lists (comfy/samplers.py). A wrong name would fail at ComfyUI anyway; this keeps pack names out of a "core" graph.
CORE_SAMPLERS = ("euler", "euler_cfg_pp", "euler_ancestral", "euler_ancestral_cfg_pp", "heun", "heunpp2", "exp_heun_2_x0", "exp_heun_2_x0_sde", "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", "dpmpp_2s_ancestral_cfg_pp", "dpmpp_sde", "dpmpp_sde_gpu", "dpmpp_2m", "dpmpp_2m_cfg_pp", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu", "dpmpp_2m_sde_heun", "dpmpp_2m_sde_heun_gpu", "dpmpp_3m_sde", "dpmpp_3m_sde_gpu", "ddpm", "lcm", "ipndm", "ipndm_v", "deis", "cfgpp_ud10_ab", "res_multistep", "res_multistep_cfg_pp", "res_multistep_ancestral", "res_multistep_ancestral_cfg_pp", "gradient_estimation", "gradient_estimation_cfg_pp", "er_sde", "seeds_2", "seeds_3", "sa_solver", "sa_solver_pece", "ddim", "uni_pc", "uni_pc_bh2")
CORE_SCHEDULERS = ("simple", "sgm_uniform", "karras", "exponential", "ddim_uniform", "beta", "normal", "linear_quadratic", "kl_optimal")
# Core model patches a user can switch on, with the default settings the proof sweep used. SD3 Skip Layer only applies to the flow model's blocks.
CORE_PATCHES = {
    "RescaleCFG": {"multiplier": 0.7}, "CFGNorm": {"strength": 1.0}, "APG": {"eta": 1.0, "norm_threshold": 5.0, "momentum": 0.0}, "TCFG": {}, "CFGZeroStar": {}, "Mahiro": {},
    "PerturbedAttentionGuidance": {"scale": 3.0}, "SelfAttentionGuidance": {"scale": 0.5, "blur_sigma": 2.0},
    "SkipLayerGuidanceSD3": {"layers": "7, 8, 9", "scale": 3.0, "start_percent": 0.01, "end_percent": 0.15},
    "FreeU_V2": {"b1": 1.3, "b2": 1.4, "s1": 0.9, "s2": 0.2}, "TomePatchModel": {"ratio": 0.3}, "HyperTile": {"tile_size": 256, "swap_size": 2, "max_depth": 0, "scale_depth": False},
}

def build(r):
    """r: model, sampler, scheduler, cfg, patches [[class, inputs]], guider, seed, steps, prompt, negative, id. A graph for ComfyUI's /prompt."""
    m = MODELS[r["model"]]; g = {}
    g["1"] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": m["ckpt"]}}
    clip = ["1", 1]; vae = ["1", 2]
    if m.get("clips"):
        g["2"] = {"class_type": "TripleCLIPLoader", "inputs": dict(zip(("clip_name1", "clip_name2", "clip_name3"), m["clips"]))}; clip = ["2", 0]
    if m.get("vae"):
        g["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": m["vae"]}}; vae = ["3", 0]
    g["4"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": r.get("prompt") or PROMPT}}
    g["5"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": NEGATIVE if r.get("negative") is None else r["negative"]}}
    g["6"] = {"class_type": "EmptySD3LatentImage" if m["kind"] == "flow" else "EmptyLatentImage", "inputs": {"width": m["size"], "height": m["size"], "batch_size": 1}}
    model = ["1", 0]
    for i, (cls, inputs) in enumerate(r.get("patches") or []):
        nid = str(20 + i); g[nid] = {"class_type": cls, "inputs": {"model": model, **inputs}}; model = [nid, 0]
    g["7"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": int(r.get("seed", SEED))}}
    if r.get("guider") == "PerpNegGuider":
        g["13"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": ""}}
        g["8"] = {"class_type": "PerpNegGuider", "inputs": {"model": model, "positive": ["4", 0], "negative": ["5", 0], "empty_conditioning": ["13", 0], "cfg": r["cfg"], "neg_scale": 1.0}}
    else:
        g["8"] = {"class_type": "CFGGuider", "inputs": {"model": model, "positive": ["4", 0], "negative": ["5", 0], "cfg": r["cfg"]}}
    g["9"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": r["sampler"]}}
    g["10"] = {"class_type": "BasicScheduler", "inputs": {"model": model, "scheduler": r["scheduler"], "steps": int(r.get("steps", STEPS)), "denoise": 1.0}}
    g["11"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["7", 0], "guider": ["8", 0], "sampler": ["9", 0], "sigmas": ["10", 0], "latent_image": ["6", 0]}}
    g["12"] = {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": vae}}
    g["14"] = {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": "sampling_lab/" + str(r.get("id") or "run")}}
    return g
