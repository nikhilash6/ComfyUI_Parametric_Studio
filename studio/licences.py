"""Model licences in one place: what the studio shows on a goal tile, a family card and the Create form, and what MODELS.md summarises.

Each entry was read from the model's own page on 2026-11-02: the Hugging Face API's licence fields for every repository named, and the licence text where it is not a
plain open-source licence. Gated licence files that would not open without accepting them are marked "text gated" in `licence`; their terms come from the card's own
agreement prompt or licence name. This is a summary to help people find the terms, not legal advice.

`limits` holds the short words a person must see before they pick a model: non-commercial, research only, a revenue or user cap, a territory exclusion, or an
unverified licence. An empty tuple means the licence is an open-source licence (Apache-2.0, MIT, BSD) or an open licence with use rules only (OpenRAIL, the SAM,
DINOv3 and NVIDIA Open Model licences), with commercial use allowed. Where only some models in a family are restricted, the limit names them in brackets."""

NC, RO, UNVERIFIED = "Non-commercial", "Research only", "Licence unverified"
EX_EU_UK_KR = "Excludes EU, UK, South Korea"
EX_US_EU_UK_KR = "Excludes US, EU, UK, South Korea"


def cap(amount): return f"Revenue cap US${amount}"


def L(licence, url, *limits): return {"licence": licence, "url": url, "limits": tuple(limits)}


APACHE, MIT = "https://www.apache.org/licenses/LICENSE-2.0", "https://opensource.org/license/mit"
H3_URL = "https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE"
LTX_URL = "https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x"
KREA_URL = "https://huggingface.co/Comfy-Org/Krea-2/blob/main/LICENSE.pdf"
STABILITY_URL = "https://stability.ai/community-license-agreement"
HUNYUAN_TERRITORY = "Tencent Hunyuan Community License: it does not apply in the EU, the UK or South Korea"

#: every family in studio/family_status.json
FAMILIES = {
    "ACE-Step-1.5": L("MIT (ACE-Step's repository); the ComfyUI repackage is tagged Apache-2.0", "https://huggingface.co/ACE-Step/Ace-Step1.5"),
    "Allegro": L("Apache-2.0", "https://huggingface.co/rhymes-ai/Allegro-TI2V"),
    "Anima": L("CircleStone Labs Non-Commercial License v1.2. Outputs may be used for any purpose", "https://huggingface.co/circlestone-labs/Anima/blob/main/LICENSE.md", NC),
    "Boogu": L("Apache-2.0 (ComfyUI repackage)", "https://huggingface.co/Comfy-Org/Boogu-Image"),
    "CogVideoX": L("CogVideoX License: free for research; commercial use needs registration, and more than 1 million visits a month needs a further licence", "https://huggingface.co/zai-org/CogVideoX-5b/blob/main/LICENSE", "Commercial use needs registration", "User cap 1M visits a month"),
    "colorization": L("No model repository is recorded for this family", "", UNVERIFIED),
    "Cosmos": L("NVIDIA Open Model License: commercial use allowed", "https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license"),
    "DreamX-Creator": L("Apache-2.0", "https://huggingface.co/t8star/DreamX-Creator-Comfy"),
    "dwpose": L("Apache-2.0", "https://huggingface.co/yzd-v/DWPose"),
    "Ernie-Image": L("Apache-2.0 (ComfyUI repackage)", "https://huggingface.co/Comfy-Org/ERNIE-Image"),
    "face": L("No model repository is recorded for this family", "", UNVERIFIED),
    "Fibo-2.0": L("CC-BY-NC-4.0, non-commercial (Bria FIBO licence; text gated)", "https://huggingface.co/briaai/Fibo-2.0-dev", NC),
    "FitDiT": L("CC BY-NC-SA 4.0", "https://huggingface.co/BoyuanJiang/FitDiT", NC),
    "FlashVSR-v1.1": L("Apache-2.0", "https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1"),
    "Flux-Kontext": L("FLUX.1 [dev] Non-Commercial License (text gated)", "https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev", NC),
    "Flux.1": L("Schnell: Apache-2.0. Dev and Redux: FLUX.1 [dev] Non-Commercial License (text gated)", "https://huggingface.co/black-forest-labs/FLUX.1-dev", NC + " (Dev, Redux)"),
    "Flux.2": L("Klein 4B and Klein Base 4B: Apache-2.0. Klein 9B and Dev: FLUX Non-Commercial License (text gated)", "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B", NC + " (Klein 9B, Dev)"),
    "Flux.3-Klein": L("FLUX Kommunity License (text gated): outputs may be used commercially only by companies under US$5,000,000 gross annual revenue", "https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy", cap("5M")),
    "frame_interpolation": L("MIT and Apache-2.0 (ComfyUI repackage)", "https://huggingface.co/Comfy-Org/Frame-Interpolation"),
    "greyscale_to_rgba": L("No model repository is recorded for this family", "", UNVERIFIED),
    "HiDream": L("MIT", "https://huggingface.co/HiDream-ai/HiDream-O1-Image"),
    "Hunyuan3D-2.1": L(HUNYUAN_TERRITORY + "; over 1 million monthly users needs a licence from Tencent", "https://huggingface.co/tencent/Hunyuan3D-2.1/blob/main/LICENSE", EX_EU_UK_KR, "User cap 1M monthly users"),
    "HunyuanDiT-1.2": L("Tencent Hunyuan Community License. HunyuanImage 2.1, also in this family, does not apply in the EU, the UK or South Korea", "https://huggingface.co/tencent/HunyuanImage-2.1", EX_EU_UK_KR + " (HunyuanImage 2.1)"),
    "HunyuanVideo": L(HUNYUAN_TERRITORY, "https://huggingface.co/tencent/HunyuanVideo-1.5", EX_EU_UK_KR),
    "HunyuanWorld": L(HUNYUAN_TERRITORY + "; over 1 million monthly users needs a licence from Tencent", "https://huggingface.co/tencent/HunyuanWorld-1", EX_EU_UK_KR, "User cap 1M monthly users"),
    "HY-Motion": L(HUNYUAN_TERRITORY + "; over 1 million monthly users needs a licence from Tencent", "https://huggingface.co/tencent/HY-Motion-1.0", EX_EU_UK_KR, "User cap 1M monthly users"),
    "Ideogram4": L("Ideogram 4 Non-Commercial licence (ComfyUI repackage of ideogram-ai/ideogram-4-fp8; text gated)", "https://huggingface.co/ideogram-ai/ideogram-4-fp8", NC),
    "instantCharacter": L("No licence is stated on its model card", "https://huggingface.co/tencent/InstantCharacter", UNVERIFIED),
    "InstantMesh": L("Apache-2.0", "https://huggingface.co/TencentARC/InstantMesh"),
    "IP-Adapter": L("Apache-2.0", "https://huggingface.co/h94/IP-Adapter"),
    "Iris-3B": L("Apache-2.0", "https://huggingface.co/speridlabs/iris-3b"),
    "JoyAI-Video-Edit": L("Apache-2.0", "https://huggingface.co/jdopensource/JoyAI-Video-Edit"),
    "Kandinsky-5.0-T2I-Lite": L("MIT", "https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers"),
    "Kolors": L("Kolors model licence (the card is tagged Apache-2.0): over 100 million monthly users, or a cloud platform, needs a licence", "https://huggingface.co/Kwai-Kolors/Kolors/blob/main/MODEL_LICENSE", "User cap 100M monthly users"),
    "Krea2": L("Krea 2 Community License: commercial use of the model or its outputs only for companies under US$1,000,000 total annual revenue; content filtering required", KREA_URL, cap("1M")),
    "LDM3D-4C": L("CreativeML OpenRAIL-M", "https://huggingface.co/Intel/ldm3d-4c"),
    "LongCat-Avatar-15": L("MIT", "https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5"),
    "LongCat-Image": L("Apache-2.0", "https://huggingface.co/meituan-longcat/LongCat-Image"),
    "LTX-2.5": L("LTX-2.x Community License (gated download): entities with US$10,000,000 or more annual revenue need a paid licence", LTX_URL, cap("10M")),
    "Lumina-2": L("Lumina Image 2: Apache-2.0; its Gemma 2 encoder is under the Gemma Terms of Use. The NewBie template adds jina-clip-v2 (CC BY-NC 4.0) and Gemma 3", "https://huggingface.co/Comfy-Org/Lumina-Image-2", NC + " (NewBie template)"),
    "Matrix-3D": L("MIT (gated download)", "https://huggingface.co/Skywork/Matrix-3D"),
    "Matrix-Game-2": L("MIT", "https://huggingface.co/Skywork/Matrix-Game-2.0"),
    "MIDI-3D": L("Apache-2.0", "https://huggingface.co/VAST-AI/MIDI-3D"),
    "Ming-Image": L("MIT (ComfyUI repackage)", "https://huggingface.co/Comfy-Org/Ming-Image"),
    "Mini-Max-Music3": L("MiniMax-Music3 Community License (the ComfyUI repackage is tagged Apache-2.0; the studio follows MiniMax's own text): commercial products must show \"MiniMax-Music3\", and over US$20,000,000 yearly revenue needs MiniMax's written authorization", "https://huggingface.co/MiniMaxAI/MiniMax-Music3/blob/main/LICENSE", cap("20M")),
    "MiniMax-H3": L("MiniMax H3 Community License: it excludes the US, the EU, the UK and South Korea, outputs included; commercial products must show \"MiniMax H3\", and over US$20,000,000 yearly revenue needs MiniMax's written authorization", H3_URL, EX_US_EU_UK_KR, cap("20M")),
    "Mochi": L("Apache-2.0", "https://huggingface.co/genmo/mochi-1-preview"),
    "Moss-Image": L("Apache-2.0 (ComfyUI repackage)", "https://huggingface.co/Comfy-Org/MOSS-Image"),
    "MOVA": L("Apache-2.0", "https://huggingface.co/OpenMOSS-Team/MOVA-720p"),
    "Omnigen-2": L("Apache-2.0", "https://huggingface.co/OmniGen2/OmniGen2"),
    "Ovis-Image": L("Apache-2.0", "https://huggingface.co/AIDC-AI/Ovis-Image-7B"),
    "PartCrafter": L("MIT", "https://huggingface.co/wgsxm/PartCrafter"),
    "Pixal3D": L("MIT (ComfyUI repackage)", "https://huggingface.co/Comfy-Org/Pixal3D"),
    "PixArt-Sigma": L("CreativeML OpenRAIL++-M", "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"),
    "PixelDiT": L("NVIDIA Source Code License: non-commercial, research or evaluation only", "https://huggingface.co/Comfy-Org/PixelDiT/blob/main/LICENSE", RO),
    "Prism-Alpha": L("No model repository is recorded for this family", "", UNVERIFIED),
    "Qwen-Image-2.1": L("Qwen-Image, its Edit models and 2512: Apache-2.0. Qwen-Image 2.1: Qwen Research License, research or evaluation only", "https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE", RO + " (Qwen-Image 2.1)"),
    "rife": L("MIT and Apache-2.0 (ComfyUI repackage)", "https://huggingface.co/Comfy-Org/Frame-Interpolation"),
    "SAM-3D-Objects": L("SAM License: commercial use allowed, with use rules", "https://huggingface.co/facebook/sam-3d-objects"),
    "sam3": L("SAM License: commercial use allowed, with use rules", "https://huggingface.co/Comfy-Org/sam3.1/blob/main/LICENSE"),
    "SANA-Video": L("Apache-2.0", "https://huggingface.co/Efficient-Large-Model/SANA-Video_2.0_5B_720p"),
    "SD15": L("CreativeML OpenRAIL-M", "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5"),
    "SD3-SD3.5": L("Stability AI Community License (text gated): free commercial use only under US$1,000,000 annual revenue", STABILITY_URL, cap("1M")),
    "SDXL": L("Base and refiner: CreativeML OpenRAIL++-M. SDXL Turbo: Stability AI Community License, US$1,000,000 revenue cap", "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0", cap("1M") + " (Turbo)"),
    "SeedVR2": L("Apache-2.0", "https://huggingface.co/ByteDance-Seed/SeedVR2-7B"),
    "SeFi-Image-2B-turbo": L("CC BY-NC 4.0", "https://huggingface.co/SeFi-Image/SeFi-Image-2B-turbo", NC),
    "Shap-E": L("MIT", "https://huggingface.co/openai/shap-e"),
    "Stable-Cascade": L("Stability AI Non-Commercial Research Community License", "https://huggingface.co/stabilityai/stable-cascade/blob/main/LICENSE", NC),
    "Stable-Fast-3D": L("Stability AI Community License (text gated): free commercial use only under US$1,000,000 annual revenue", STABILITY_URL, cap("1M")),
    "SVD": L("Stable Video Diffusion 1.1 Community License (Stability AI Community License): free commercial use only under US$1,000,000 annual revenue", STABILITY_URL, cap("1M")),
    "TRELLIS-2-4B": L("MIT. Its image encoder DINOv3 is under the DINOv3 License (commercial use allowed); BiRefNet is MIT", "https://huggingface.co/microsoft/TRELLIS.2-4B"),
    "TripoSR": L("MIT", "https://huggingface.co/stabilityai/TripoSR"),
    "TurboWan2.2-I2V": L("Apache-2.0", "https://huggingface.co/TurboDiffusion/TurboWan2.2-I2V-A14B-720P"),
    "UniRig": L("MIT", "https://huggingface.co/VAST-AI/UniRig"),
    "upscale_models": L("Real-ESRGAN: BSD-3-Clause; BiRefNet: MIT", "https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE"),
    "VLM": L("Varies by model: Florence-2 MIT; Qwen3, Qwen3.5, Qwen3-VL and Gemma 4 Apache-2.0", "https://huggingface.co/microsoft/Florence-2-large"),
    "Wan-SCAIL-2": L("MIT (ComfyUI repackage); the lightx2v distill LoRA is Apache-2.0", "https://huggingface.co/Comfy-Org/SCAIL-2"),
    "Wan2.1": L("Apache-2.0; InfiniteTalk Apache-2.0, its wav2vec2 encoder MIT", "https://huggingface.co/Wan-AI/Wan2.1-T2V-14B"),
    "Wan2.2": L("Apache-2.0", "https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B"),
    "Wan2.2-Animate": L("Apache-2.0", "https://huggingface.co/Wan-AI/Wan2.2-Animate-14B"),
    "Wan2.2-Dancer": L("Apache-2.0 (ComfyUI repackage)", "https://huggingface.co/Comfy-Org/Wan-Dancer"),
    "yue2": L("CC BY-NC 4.0", "https://huggingface.co/m-a-p/YuE2-3B", NC),
    "Z-Image": L("Apache-2.0", "https://huggingface.co/Tongyi-MAI/Z-Image-Turbo"),
    "SAM-3D-Body": L("SAM License: commercial use allowed, with use rules", "https://huggingface.co/facebook/sam-3d-body-dinov3"),
    "TripoSplat": L("MIT", "https://huggingface.co/VAST-AI/TripoSplat"),
    "MoGe": L("MIT", "https://huggingface.co/Ruicheng/moge-2-vitl-normal"),
    "Lotus": L("Apache-2.0", "https://huggingface.co/jingheya/lotus-depth-d-v1-1"),
    "SDPose": L("MIT (ComfyUI repackage)", "https://huggingface.co/Comfy-Org/SDPose"),
    "AniGen": L("MIT", "https://huggingface.co/VAST-AI/AniGen"),
    "AnimateDiff": L("AnimateDiff motion modules: Apache-2.0; AnimateDiff-Lightning: CreativeML OpenRAIL-M. The checkpoint's own licence also applies", "https://huggingface.co/guoyww/animatediff"),
    "Chroma": L("Apache-2.0", "https://huggingface.co/lodestones/Chroma1-HD"),
    "FireRed-Image-Edit": L("Apache-2.0", "https://huggingface.co/FireRedTeam/FireRed-Image-Edit-1.1-ComfyUI"),
    "IC-Light": L("Code: Apache-2.0. The weights' own card names no licence", "https://github.com/lllyasviel/IC-Light/blob/main/LICENSE", UNVERIFIED + " (weights)"),
    "CCSR": L("Apache-2.0 (the code repository and the weights' repackage)", "https://huggingface.co/Kijai/ccsr-safetensors"),
    "LivePortrait": L("MIT; its InsightFace face finder (buffalo_l) is for non-commercial research only", "https://huggingface.co/KwaiVGI/LivePortrait", NC + " (InsightFace)"),
}

#: the model family behind each goal (studio/goals.py `family`): the goal tiles and the Create form show this licence
GOAL_FAMILIES = {
    "FLUX.2 Klein 4B": L("Apache-2.0", "https://huggingface.co/black-forest-labs/FLUX.2-klein-4B"),
    "Wan 2.2 TI2V-5B": L("Apache-2.0", "https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B"),
    "Wan 2.2 Fun Camera 14B": L("Apache-2.0", "https://huggingface.co/alibaba-pai/Wan2.2-Fun-A14B-Control-Camera"),
    "Anima": FAMILIES["Anima"],
    "FLUX.3 Klein": FAMILIES["Flux.3-Klein"],
    "Krea 2": FAMILIES["Krea2"],
    "LTX-2.5": FAMILIES["LTX-2.5"],
    "MiniMax H3": FAMILIES["MiniMax-H3"],
    "MiniMax Music 3": FAMILIES["Mini-Max-Music3"],
}

#: InsightFace buffalo_l: the character picture check's age reader and LivePortrait's face finder. Not shipped; the founders keep it, labelled non-commercial.
INSIGHTFACE = L("InsightFace model zoo: \"ALL models are available for non-commercial research purposes only.\"", "https://github.com/deepinsight/insightface/tree/master/model_zoo", NC)


def badge(limits):
    """The few words on a tile: the first limit, shortened so it fits."""
    if not limits: return ""
    first = limits[0]
    return "Territory limits" if first.startswith("Excludes") else "Revenue cap" if first.startswith("Revenue cap") else first.split(" (")[0] + (" in part" if " (" in first else "")


def for_family(name):
    """{licence, url, limits, badge} for a family, or None when it is not listed here."""
    e = FAMILIES.get(name)
    return e and {**e, "limits": list(e["limits"]), "badge": badge(e["limits"])}


def for_goal(family):
    e = GOAL_FAMILIES.get(family)
    return e and {**e, "limits": list(e["limits"]), "badge": badge(e["limits"])}
