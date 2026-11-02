"""Every base the Train page knows, with the trainer that drives it, the files it needs and its licence. Nothing here claims a base works: `measurements` in train.py decides that, from real runs.

load: how ComfyUI opens the base. {"ckpt": file} for a checkpoint, {"unet": file, "clip": [files...], "clip_type": type, "vae": file} for split files. A checkpoint may name its own clip and vae too.
sample: the same-seed A/B render. Numbers come from this studio's family templates, which were each rendered for real.
quantized: the file on disk holds int8 or fp8 weights. ComfyUI then trains with its compute type and bypass adapters, and the page says the LoRA was trained on a quantized base.
peak_gib: what the family's render needs (MODELS.md) or the trainer's config declares. Marked "expected": a measured peak replaces it on the page once a run is on record.
licence: name, url and the one line a person must know before training on it. Trained LoRAs are derivative of the base under most of these, so the line matters.
"""
from __future__ import annotations

_FLUX2_VAE, _Q4, _Q8 = "flux2-vae.safetensors", "qwen_3_4b.safetensors", "qwen3vl_8b_bf16.safetensors"
_T5F8 = "t5xxl_fp8_e4m3fn_scaled.safetensors"

LICENCES = {
    "apache": {"name": "Apache-2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0", "note": "Open for training and commercial use."},
    "openrail": {"name": "CreativeML Open RAIL++-M", "url": "https://github.com/Stability-AI/generative-models/blob/main/model_licenses/LICENSE-SDXL1.0", "note": "Open for training. Use limits apply."},
    "openrail15": {"name": "CreativeML Open RAIL-M", "url": "https://github.com/CompVis/stable-diffusion/blob/main/LICENSE", "note": "Open for training. Use limits apply."},
    "flux1dev": {"name": "FLUX.1 [dev] Non-Commercial License", "url": "https://huggingface.co/black-forest-labs/FLUX.1-dev/blob/main/LICENSE.md", "note": "Non-commercial unless you hold a licence from Black Forest Labs."},
    "flux3": {"name": "FLUX Kommunity License", "url": "https://huggingface.co/black-forest-labs/flux-3-image-klein", "note": "Non-commercial by default. Outputs may be used commercially only under US$5,000,000 yearly revenue."},
    "flux2_9b": {"name": "FLUX Non-Commercial License", "url": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B", "note": "Non-commercial unless you hold a licence from Black Forest Labs."},
    "qwen21": {"name": "Qwen Research License", "url": "https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE", "note": "Research or evaluation only. Do not use the LoRA commercially."},
    "ltx": {"name": "LTX-2.x Community License", "url": "https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x", "note": "Entities with US$10,000,000 or more in yearly revenue need a paid licence."},
    "h3": {"name": "MiniMax H3 licence", "url": "https://huggingface.co/Comfy-Org/MiniMax-H3", "note": "Excludes the EU, UK, South Korea and the USA, including outputs. Read it before training."},
    "music3": {"name": "MiniMax-Music3 Community License", "url": "https://huggingface.co/MiniMaxAI/MiniMax-Music3/blob/main/LICENSE", "note": "Commercial products must display the name, and need authorization above US$20,000,000 yearly revenue."},
    "anima": {"name": "CircleStone Labs Non-Commercial", "url": "https://huggingface.co/circlestone-labs/Anima", "note": "Non-commercial. You may not be paid for its use."},
    "krea2": {"name": "Krea 2 Community License", "url": "https://huggingface.co/krea/Krea-2-Turbo/blob/main/LICENSE.pdf", "note": "A custom licence. Read its terms for commercial use and for sharing a LoRA."},
    "mit": {"name": "MIT", "url": "https://opensource.org/license/mit", "note": "Open for training and commercial use."},
    "sd3": {"name": "Stability AI Community License", "url": "https://huggingface.co/stabilityai/stable-diffusion-3.5-medium/blob/main/LICENSE.md", "note": "Free under US$1,000,000 yearly revenue; above that you need a licence from Stability AI."},
    "ideogram": {"name": "Ideogram 4 Non-Commercial Agreement", "url": "https://huggingface.co/ideogram-ai/ideogram-4-fp8/blob/main/LICENSE.md", "note": "Non-commercial."},
    "unchecked": {"name": "Not checked", "url": "", "note": "The licence text has not been read for this page. Read the publisher's terms before you train."},
}


def _unet(unet, clip, clip_type, vae, dtype="default"):
    return {"unet": unet, "dtype": dtype, "clip": clip if isinstance(clip, list) else [clip], "clip_type": clip_type, "vae": vae}


def _s(latent, steps, cfg, sampler="euler", scheduler="simple", shift=None, shift_node=None, **more):
    return {"latent": latent, "steps": steps, "cfg": cfg, "sampler": sampler, "scheduler": scheduler, "shift": shift, "shift_node": shift_node, **more}


def _base(label, family, file, arch, load, sample, licence, peak, media="image", sizes=(512, 768, 1024), lr=None, trainer="comfy", needs=None, repo=None, **more):
    return {"label": label, "family": family, "file": file, "arch": arch, "load": load, "sample": sample, "licence": LICENCES[licence], "peak_gib": peak, "media": media, "sizes": list(sizes), "lr": lr, "trainer": trainer, "needs": needs or (), "repo": repo, **more}


_SDXL = {"sizes": [768, 1024], "needs": ("conditioner.embedders.1.", "model.diffusion_model.")}

BASES = {
    # ---- ComfyUI's own TrainLoraNode: no new install, the files are the ones the studio already renders with
    "sdxl-base-1.0": {**_base("Stable Diffusion XL base 1.0", "SDXL", "sd_xl_base_1.0.safetensors", "SDXL", {"ckpt": "sd_xl_base_1.0.safetensors"}, _s("EmptyLatentImage", 25, 7.0, "euler", "normal"), "openrail", 12, repo="stabilityai/stable-diffusion-xl-base-1.0"), **_SDXL},
    "sd-1.5": {**_base("Stable Diffusion 1.5", "SD 1.5", "v1-5-pruned-emaonly.safetensors", "SD 1.5", {"ckpt": "v1-5-pruned-emaonly.safetensors"}, _s("EmptyLatentImage", 25, 7.0, "euler", "normal"), "openrail15", 6, sizes=(512,), repo="stable-diffusion-v1-5/stable-diffusion-v1-5"), "needs": ("cond_stage_model.", "model.diffusion_model.")},
    "flux2-klein-base-4b": _base("FLUX.2 Klein 4B (base)", "FLUX.2 Klein", "flux-2-klein-base-4b.safetensors", "FLUX.2 Klein 4B", _unet("flux-2-klein-base-4b.safetensors", _Q4, "flux2", _FLUX2_VAE), _s("EmptyFlux2LatentImage", 20, 4.0), "apache", 23, lr=1e-4, repo="Comfy-Org/Flux-2-Klein-4B"),
    "flux2-klein-9b": _base("FLUX.2 Klein 9B", "FLUX.2 Klein", "flux-2-klein-9b.safetensors", "FLUX.2 Klein 9B", _unet("flux-2-klein-9b.safetensors", "qwen_3_8b_fp8mixed.safetensors", "flux2", _FLUX2_VAE), _s("EmptyFlux2LatentImage", 6, 1.0), "flux2_9b", 30, lr=1e-4, repo="black-forest-labs/FLUX.2-klein-9B"),
    "flux3-klein": _base("FLUX.3 Klein", "FLUX.3 Klein", "flux3_image_klein_bf16.safetensors", "FLUX.3 Klein", _unet("flux3_image_klein_bf16.safetensors", "qwen3vl_4b_bf16.safetensors", "flux3", _FLUX2_VAE), _s("EmptyFlux2LatentImage", 15, 1.0, "er_sde"), "flux3", 24, lr=1e-4, repo="black-forest-labs/flux-3-image-klein", known_failure="ComfyUI's training node fails on this base (a torch.cat with out= cannot take gradients), and no external trainer here supports it yet."),
    "flux1-schnell": _base("FLUX.1 schnell", "FLUX.1", "flux1-schnell.safetensors", "FLUX.1 schnell", _unet("flux1-schnell.safetensors", ["clip_l.safetensors", _T5F8], "flux", "ae.safetensors"), _s("EmptySD3LatentImage", 4, 1.0), "apache", 34, lr=1e-4, repo="black-forest-labs/FLUX.1-schnell"),
    "qwen-image-2.1": _base("Qwen-Image 2.1", "Qwen Image", "qwen_image_2.1_bf16.safetensors", "Qwen-Image 2.1", _unet("qwen_image_2.1_bf16.safetensors", _Q8, "qwen_image", "qwen_image_2.1_vae_bf16.safetensors"), _s("EmptyLatentImage", 40, 1.0), "qwen21", 40, lr=1e-4, repo="Comfy-Org/Qwen-Image-2.1", trainer="ai-toolkit",
                               aitk={"template": "qwen2.yaml", "arch": "qwen_image_2", "sample_steps": 30, "guidance": 1.0, "files": {"dit": ("diffusion_models", "qwen_image_2.1_bf16.safetensors"), "te": ("text_encoders", "qwen3vl_8b_bf16.safetensors"), "vae": ("vae", "qwen_image_2.1_vae_bf16.safetensors")}}),
    "krea2-raw": _base("Krea 2 Raw", "Krea 2", "krea2_raw_bf16.safetensors", "Krea 2", _unet("krea2_raw_bf16.safetensors", "qwen3vl_4b_bf16.safetensors", "krea2", "qwen_image_vae.safetensors", dtype="fp8_e4m3fn"), _s("EmptyLatentImage", 26, 3.5), "krea2", 40, lr=1e-4, repo="Comfy-Org/Krea-2"),
    "hidream-o1": _base("HiDream-O1 Image", "HiDream", "hidream_o1_image_bf16.safetensors", "HiDream-O1", {"ckpt": "hidream_o1_image_bf16.safetensors"}, _s("EmptyHiDreamO1LatentImage", 28, 5.0, "euler", "normal", wrap=[("ModelNoiseScale", {"noise_scale": 8.0})]), "mit", 40, lr=1e-4, repo="Comfy-Org/HiDream-O1-Image", trainer="ai-toolkit",
                           aitk={"template": "hidream_o1.yaml", "arch": "hidream_o1", "sample_steps": 28, "guidance": 5.0, "files": {"dit": ("checkpoints", "hidream_o1_image_bf16.safetensors")}}),
    "z-image": _base("Z-Image", "Z-Image", "z_image_bf16.safetensors", "Z-Image", _unet("z_image_bf16.safetensors", _Q4, "lumina2", "ae.safetensors"), _s("EmptySD3LatentImage", 25, 4.0, "res_multistep", shift=3.0, shift_node="ModelSamplingAuraFlow"), "apache", 20, lr=1e-4, repo="Comfy-Org/z_image"),
    "lumina-2": _base("Lumina Image 2.0", "Lumina", "lumina_2_model_bf16.safetensors", "Lumina 2", _unet("lumina_2_model_bf16.safetensors", "gemma_2_2b_it_elm_bf16.safetensors", "lumina2", "ae.safetensors"), _s("EmptySD3LatentImage", 30, 4.0, "res_multistep", shift=4.0, shift_node="ModelSamplingAuraFlow"), "apache", 12, lr=1e-4, repo="Comfy-Org/Lumina_Image_2.0_Repackaged"),
    "sd3.5-medium": {**_base("Stable Diffusion 3.5 Medium", "SD3.5", "sd3.5_medium.safetensors", "SD3.5 Medium", {"ckpt": "sd3.5_medium.safetensors", "clip": ["clip_l.safetensors", "clip_g.safetensors", _T5F8], "clip_type": "sd3"}, _s("EmptySD3LatentImage", 20, 4.01, "euler", "sgm_uniform"), "sd3", 16, lr=1e-4, repo="stabilityai/stable-diffusion-3.5-medium")},
    "anima-base": _base("Anima base 1.0", "Anima", "anima-base-v1.0.safetensors", "Anima", _unet("anima-base-v1.0.safetensors", "qwen_3_06b_base.safetensors", "stable_diffusion", "qwen_image_vae.safetensors"), _s("EmptyLatentImage", 30, 4.5, "er_sde"), "anima", 13, lr=1e-4, repo="circlestone-labs/Anima", known_failure="ComfyUI's training node fails on this base (a compiled rope split with no gradient formula), and no external trainer here is wired for it yet."),
    "ernie-image": _base("ERNIE Image", "ERNIE Image", "ernie-image.safetensors", "ERNIE Image", _unet("ernie-image.safetensors", "ministral-3-3b.safetensors", "flux2", _FLUX2_VAE), _s("EmptyFlux2LatentImage", 20, 4.0), "apache", 24, lr=1e-4, repo="Comfy-Org/ERNIE-Image", known_failure="ComfyUI's training node fails on this base (a compiled rope split with no gradient formula), and no external trainer here is wired for it yet."),
    "pixart-sigma": _base("PixArt-Sigma", "PixArt", "pixart-sigma_transformer.safetensors", "PixArt-Sigma", _unet("pixart-sigma_transformer.safetensors", "t5xxl_fp16.safetensors", "pixart", "sdxl_vae.safetensors"), _s("EmptyLatentImage", 20, 4.5, "euler", "normal"), "openrail", 12, lr=1e-4, repo="PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"),
    "wan2.2-5b": _base("Wan 2.2 TI2V-5B", "Wan 2.2", "wan2.2_ti2v_5B_fp16.safetensors", "Wan 2.2 5B", _unet("wan2.2_ti2v_5B_fp16.safetensors", "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "wan", "wan2.2_vae.safetensors"), _s("Wan22ImageToVideoLatent", 20, 5.0, "uni_pc", shift=8.0, shift_node="ModelSamplingSD3"), "apache", 35, media="image-for-video", lr=1e-4, repo="Comfy-Org/Wan_2.2_ComfyUI_Repackaged"),
    # ---- ostris ai-toolkit: a separate install, driven through its own process
    "flux1-dev": _base("FLUX.1 [dev]", "FLUX.1", "flux1-dev-pipeline", "FLUX.1 dev", {}, _s("EmptySD3LatentImage", 20, 1.0), "flux1dev", 40, trainer="ai-toolkit", lr=1e-4, repo="black-forest-labs/FLUX.1-dev", ab_from_samples=True,
                       aitk={"template": "flux_dev.yaml", "arch": "flux", "files": {"pipeline": ("diffusers", "flux1-dev-pipeline")}, "folder_needs": {"pipeline": ["transformer", "vae", "text_encoder", "text_encoder_2"]}, "sample_steps": 20, "guidance": 4.0}),
    "ltx2.5": _base("LTX-2.5 (distilled int8)", "LTX-2.5", "ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors", "LTX-2.5", {}, _s("EmptyLTXVLatentVideo", 8, 1.0), "ltx", 36, media="image-for-video", sizes=(512, 768), trainer="ai-toolkit", lr=1e-4, repo="Lightricks/LTX-2.5", ab_from_samples=True, quantized=True,
                    aitk={"template": "ltx25.yaml", "arch": "ltx2.5", "num_frames": 1, "sample_steps": 8, "guidance": 1.0, "files": {"dit": ("diffusion_models", "ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors"), "te": ("text_encoders", "gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors"), "vae": ("vae", "ltx-2.5-video-vae-conv-bf16.safetensors"), "audio_vae": ("vae", "ltx-2.5-audio-vae-bf16.safetensors")}}),
    "minimax-h3": _base("MiniMax H3 (FL2VA int8)", "MiniMax H3", "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "MiniMax H3", {}, _s("EmptyLatentImage", 20, 1.0), "h3", 55, media="image-for-video", sizes=(512, 768), trainer="ai-toolkit", lr=1e-4, repo="Comfy-Org/MiniMax-H3", ab_from_samples=True, quantized=True,
                        aitk={"template": "h3.yaml", "arch": "minimax_h3", "num_frames": 1, "sample_steps": 20, "guidance": 1.0, "files": {"dit": ("diffusion_models", "minimax_h3_fl2va_pruned_int8_convrot.safetensors"), "te": ("text_encoders", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"), "vae": ("vae", "minimax_h3_video_vae_fp16.safetensors"), "audio_vae": ("vae", "minimax_h3_audio_vae_fp32.safetensors"), "adapter": ("loras", "minimax_h3_image_training_adapter.safetensors")}}),
}

#: The trainers the page can drive. Install steps are what a stranger follows on their own machine; nothing is installed for them.
TRAINERS = {
    "comfy": {"label": "ComfyUI TrainLoraNode", "site": "https://docs.comfy.org", "note": "ComfyUI's own training nodes, inside your ComfyUI. Nothing more to install. Saves only at the end, so a cancel loses the run."},
    "ai-toolkit": {"label": "ostris ai-toolkit", "site": "https://github.com/ostris/ai-toolkit", "note": "A separate trainer with its own Python. Saves checkpoints as it goes, writes sample pictures, and can resume from its last save.",
                   "install": ["git clone https://github.com/ostris/ai-toolkit", "cd ai-toolkit && git submodule update --init --recursive", "python3.12 -m venv venv && venv/bin/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130", "venv/bin/pip install -r requirements.txt", "Tell the studio where it is: set STUDIO_TRAINER_AI_TOOLKIT_DIR to that folder and STUDIO_TRAINER_AI_TOOLKIT_PYTHON to venv/bin/python, then restart the studio."]},
}
