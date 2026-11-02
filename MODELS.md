# Models

Models are not part of this repository. They download from their publishers and keep their own licences, which are separate from this project's AGPL. This page is a summary to help you find the terms, not legal advice. Read the licence itself before you rely on any of this.

**How this was checked (2026-10-30, re-checked 2026-11-02):** gated status and licence fields come from the Hugging Face API for each repository. Where a licence's terms are described below, the licence text was read from the same source, except where marked. Sizes come from `studio/models_manifest.json` and are in GiB (Hugging Face shows GB, so its numbers look about 7% larger). Peak VRAM is the highest figure measured for that goal in the studio's own showcase renders, on one 96 GB NVIDIA card at small sizes and short lengths. On other cards or settings it will differ. On 2026-11-02 every repository named on this page was read again from the Hugging Face API, and the licence text was read for every licence that limits use. A few licence files are gated and would not open without accepting them; those rows say "text gated", and their terms come from the card's own agreement prompt. The studio's own copy of these facts is `studio/licences.py`, which the goal tiles, family cards and the Create page read.

## Generation models

| Family | Goals | Total GiB | Files (GiB) | Peak VRAM GiB | Licence | Gated | Source |
|---|---|---|---|---|---|---|---|
| FLUX.2 Klein 4B | Image | 15.0 | `flux-2-klein-4b.safetensors` (7.22)<br>`qwen_3_4b.safetensors` (7.49)<br>`flux2-vae.safetensors` (0.31) | 22.6 | Apache-2.0 | No | [Comfy-Org/Flux-2-Klein-4B](https://huggingface.co/Comfy-Org/Flux-2-Klein-4B), upstream [black-forest-labs/FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) |
| Wan 2.2 TI2V-5B | Video, Animate | 16.9 | `wan2.2_ti2v_5B_fp16.safetensors` (9.31)<br>`umt5_xxl_fp8_e4m3fn_scaled.safetensors` (6.27)<br>`wan2.2_vae.safetensors` (1.31) | 34.7 | Apache-2.0 | No | [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged), upstream [Wan-AI/Wan2.2-TI2V-5B](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B) |
| Anima | Anime | 9.2 | `anima-aesthetic-v1.1.safetensors` (3.90)<br>`anima-turbo-v1.1.safetensors` (3.90)<br>`qwen_3_06b_base.safetensors` (1.11)<br>`qwen_image_vae.safetensors` (0.24) | 13.2 | CircleStone Labs Non-Commercial License v1.2 | No | [circlestone-labs/Anima](https://huggingface.co/circlestone-labs/Anima) |
| FLUX.3 Klein | Image HQ | 18.9 | `flux3-image-klein-bf16.safetensors` (10.34)<br>`qwen3vl_4b_bf16.safetensors` (8.27)<br>`flux2-vae.safetensors` (0.31) | 24.1 | FLUX Kommunity License | Yes (accept on Hugging Face) | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy), upstream [black-forest-labs/flux-3-image-klein](https://huggingface.co/black-forest-labs/flux-3-image-klein) |
| LTX-2.5 | Video + sound, Animate + sound | 36.0 | `ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors` (20.03)<br>`gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors` (14.32)<br>`ltx-2.5-video-vae-conv-bf16.safetensors` (1.35)<br>`ltx-2.5-audio-vae-bf16.safetensors` (0.34) | 44.3 | LTX-2.x Community License | Yes (accept on Hugging Face) | [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) |
| MiniMax H3 | Video H3, Animate H3 | 41.4 | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` (19.53)<br>`qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` (14.61)<br>`minimax_h3_video_vae_fp16.safetensors` (4.85)<br>`minimax_h3_audio_vae_fp32.safetensors` (0.56)<br>`minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` (1.82) | 45.4 | MiniMax H3 Community License | No | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3), upstream [MiniMaxAI/MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3) |
| MiniMax Music 3 | Music | 20.3 | `minimax_music3_dit_fp16.safetensors` (4.58)<br>`minimax_music3_text_encoder_pruned_bf16.safetensors` (15.56)<br>`minimax_music3_dav.safetensors` (0.20) | 26.8 | MiniMax-Music3 Community License (see the note below) | No | [Comfy-Org/MiniMax-Music-3](https://huggingface.co/Comfy-Org/MiniMax-Music-3), upstream [MiniMaxAI/MiniMax-Music3](https://huggingface.co/MiniMaxAI/MiniMax-Music3) |

Animate shares its files with Video, Animate + sound with Video + sound, and Animate H3 with Video H3, so each set downloads once.

### Flagship apps and the other goals

These goals reuse the families above and add the files listed here. Sizes come from `studio/models_manifest.json`; peak VRAM from the installer's figures, measured for Recast, VFX and Director and taken from the nearest measured goal for the others.

| Goal | Adds | Total GiB | Peak VRAM GiB | Licence | Gated | Source |
|---|---|---|---|---|---|---|
| Recast | MiniMax H3 Ref2VA (`minimax_h3_ref2va_pruned_int8_convrot.safetensors`, 19.53) and the character swap LoRA (`h3_character_swap_pro4500_1000.safetensors`, 0.14) | 39.7 | 36.3 | MiniMax H3 Community License, for both | No | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3), [akatz-ai/MiniMax-H3-Character-Swap-LoRA](https://huggingface.co/akatz-ai/MiniMax-H3-Character-Swap-LoRA) |
| Frozen orbit | pablodawson's 360 orbit LoRA (`minimax_h3_flf2v_lora_v1.safetensors`, 0.14) | 39.1 | 46.8 | MiniMax H3 Community License | No | [pablodawson/MiniMax-H3-360-Orbit-LoRA](https://huggingface.co/pablodawson/MiniMax-H3-360-Orbit-LoRA) |
| Reshoot, Director, Director first + last frame | Nothing beyond Video H3 | 41.4 | 45.6 to 46.8 | MiniMax H3 Community License | No | as Video H3 |
| VFX | Four Lightricks IC-LoRAs: Clean Plate (0.30), Water Simulation (0.84), Day To Night (0.30), Alpha Gen (1.22) | 38.7 | 44.8 | LTX-2.x Community License, for each LoRA too | Yes | [Lightricks on Hugging Face](https://huggingface.co/Lightricks), for example [LTX-2.5-22b-IC-LoRA-Water-Simulation](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Water-Simulation) |
| Reshoot (Wan camera) | Wan 2.2 Fun Camera 14B, high and low noise (14.25 each), with the Wan 2.1 encoder and VAE | 35.0 | 34.7 | Apache-2.0 | No | [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged), upstream [alibaba-pai/Wan2.2-Fun-A14B-Control-Camera](https://huggingface.co/alibaba-pai/Wan2.2-Fun-A14B-Control-Camera) |
| Product Studio | Nothing beyond Image HQ | 18.9 | 24.1 | FLUX Kommunity License | Yes | as FLUX.3 Klein |
| Lettering | Krea 2 Turbo (`krea2_turbo_bf16.safetensors`) with the Qwen3-VL 4B encoder and the Qwen-Image VAE. Not in the manifest yet, so the installer does not fetch it; the tile says its file list is not published | not listed | not measured | Krea 2 Community License | No (ComfyUI repackage); the upstream Krea repositories ask you to accept it | [Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2), upstream [krea/Krea-2-Turbo](https://huggingface.co/krea/Krea-2-Turbo) |

### What the licences say

Verified from the licence text unless noted.

- **FLUX.2 Klein 4B, Wan 2.2 TI2V-5B:** Apache-2.0 on both the ComfyUI repackage and the upstream repository.
- **Anima:** non-commercial. You may not receive payment from its use. Hugging Face lists it as built on NVIDIA Cosmos-Predict2-2B, which has its own [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license).
- **FLUX.3 Klein:** non-commercial by default. Its licence file is gated, so on 2026-11-02 it was not re-read; the terms below are from the 2026-10-30 reading, and published summaries of the licence give the same US$5,000,000 figure. Outputs may be used commercially only by a "Qualifying User", meaning you and your affiliates have gross annualized revenue under US$5,000,000. Anything else needs a licence from Black Forest Labs. Also read its limits on prohibited uses.
- **LTX-2.5:** LTX-2.x Community License. Entities with annual revenue of at least US$10,000,000 need a paid commercial licence. The text read for this summary was the copy shipped with Lightricks' ComfyUI-LTXVideo pack (dated January 5, 2026). The current text is at [LICENSE-2_x](https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x).
- **MiniMax H3:** **the licence excludes some countries.** Its grant applies "worldwide, excluding the Excluded Territories", defined as the European Union, the United Kingdom, the Republic of Korea and the United States of America, and it says you may not use or display the works or their outputs outside the permitted territory. MiniMax invites people in those places to contact them about a licence. If you are in one of those places, read it before you install these goals. Commercial products need the name "MiniMax H3" shown in their interface, and written authorization above US$20,000,000 in yearly revenue. Anyone offering a hosted service has further safeguard duties.
- **Krea 2 (the Lettering goal, World Kit character sheets):** Krea 2 Community License v.1, June 22, 2026. Section 2.3: "Commercial Use under this Agreement of the Krea Model, Derivatives, or Outputs is permitted only if you (including all affiliated entities under common ownership or control) have total company-wide annual revenue of less than one million United States dollars ($1,000,000 USD)". Above that you need Krea's enterprise licence. Section 4.2 also asks anyone deploying it to "implement reasonable and appropriate Content Filter measures". The studio checks prompts for safe-for-work words but runs no image filter on Krea 2's output.
- **LTX IC-LoRAs:** each Lightricks IC-LoRA repository is tagged `ltx-2.x-community-license` and links the same LTX-2.x licence, so the US$10,000,000 threshold applies to the LoRAs too.
- **H3 LoRAs:** the character swap and orbit LoRAs are both tagged `minimax-h3-community-license-agreement`, so the territory and revenue terms of MiniMax H3 apply to them.
- **Hunyuan (Hunyuan3D 2 and 2.1, HunyuanVideo, HunyuanImage 2.1, HunyuanWorld, HY-Motion):** "THIS LICENSE AGREEMENT DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA", and that reaches outputs. Hunyuan3D 2.1, HunyuanWorld and HY-Motion also need a licence from Tencent above 1 million monthly active users.
- **Qwen-Image 2.1 and PixelDiT:** research or evaluation only. Qwen-Image 2.1 is under the Qwen RESEARCH LICENSE AGREEMENT ("'Non-Commercial' shall mean for research or evaluation purposes only"); PixelDiT under the NVIDIA Source Code License ("only may be used or intended for use non-commercially"). Our renders of them are test renders; don't use them commercially. The Virtual Set's photoreal keyframes and the try-on and try-off methods on Qwen-Image 2.1 carry the same label.
- **Ideogram 4:** the ComfyUI repackage is tagged `ideogram-non-commercial-model-agreement` and the upstream `ideogram-ai/ideogram-4-fp8` is tagged `ideogram-4-non-commercial`. These are downloadable weights run by local nodes, not Ideogram's API. Non-commercial.
- **Stability AI Community License (SD 3.5, SDXL Turbo, Stable Video Diffusion 1.1, Stable Fast 3D, Stable Audio Open):** "If at any time You or Your Affiliate(s), either individually or in aggregate, generate more than USD $1,000,000 in annual revenue ... any licenses granted to You under this Agreement shall terminate". Stable Cascade is under Stability's separate Non-Commercial Research Community License.
- **InsightFace `buffalo_l` (the character picture check's age reader):** non-commercial research only. You download these weights yourself; we don't ship them. Replace it before any commercial use of the character maker.
- **Motion routes:** each row on the Motion page carries its own line. Kimodo SOMA and G1 are under the NVIDIA Open Model License, and Kimodo SMPL-X under NVIDIA's R&D licence, which is why it is not offered. LivePortrait is MIT and LatentSync is Apache-2.0 code with OpenRAIL++ weights, but both find faces with InsightFace buffalo_l, whose weights are non-commercial. Wan Animate 2, InfiniteTalk and Wan Dancer are Apache-2.0, and SCAIL 2 is MIT on Hugging Face, Apache-2.0 on GitHub. SAM 3D Body is under the SAM License.
- **Llama 3 (Kimodo's text encoder):** Meta Llama 3 Community License. Built with Meta Llama 3.
- **MiniMax Music 3:** the sources disagree. The [Comfy-Org repackage](https://huggingface.co/Comfy-Org/MiniMax-Music-3) that the installer downloads from is tagged Apache-2.0, but the [upstream LICENSE](https://huggingface.co/MiniMaxAI/MiniMax-Music3/blob/main/LICENSE) is the "MiniMax-Music3 Community License": commercial products must display the name, and authorization is needed above US$20,000,000 in yearly revenue. This page treats the upstream text as the one that applies. The studio's label says the same.

The full list of families, with each licence and what it limits, is in [Family templates and other graphs](#family-templates-and-other-graphs) below.

The H3, FLUX.3 and LTX text encoders (Qwen3-VL, Gemma 4) are packaged inside those model repositories, and their base models have their own terms: Qwen/Qwen3-VL-32B-Instruct and google/gemma-4-12b are tagged Apache-2.0 on Hugging Face (Gemma's page links its own [licence page](https://ai.google.dev/gemma/docs/gemma_4_license)). Unverified: whether anything beyond the package's licence applies to the repackaged encoder files.

### Not in the manifest yet

Unverified means not checked against the licence text.

| File | Used by | Status |
|---|---|---|
| `flux-2-klein-base-4b.safetensors` (Comfy-Org/Flux-2-Klein-4B, Apache-2.0) | Image, quality mode | The installer does not fetch it; the fast mode works without it |

## Language models for the crew

From `studio/llm_tiers.py`. All are tagged Apache-2.0 and ungated on Hugging Face, for both the Qwen source and the unsloth GGUF. The sizes are the weights, from that file.

| Tier | Model | Quant | GB | Needs | Runs on | Licence | Gated | Source |
|---|---|---|---|---|---|---|---|---|
| tiny | Qwen/Qwen3.5-2B | Q8_0 | 2.0 | 6 GB RAM | cpu | Apache-2.0 | No | [unsloth/Qwen3.5-2B-GGUF](https://huggingface.co/unsloth/Qwen3.5-2B-GGUF) `Qwen3.5-2B-Q8_0.gguf` |
| small | Qwen/Qwen3.5-4B | UD-Q6_K_XL | 4.1 | 8 GB RAM | cpu | Apache-2.0 | No | [unsloth/Qwen3.5-4B-GGUF](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF) `Qwen3.5-4B-UD-Q6_K_XL.gguf` |
| medium | Qwen/Qwen3.5-9B | UD-Q5_K_XL | 6.7 | 16 GB RAM | cpu | Apache-2.0 | No | [unsloth/Qwen3.5-9B-GGUF](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF) `Qwen3.5-9B-UD-Q5_K_XL.gguf` |
| moe | Qwen/Qwen3.5-35B-A3B | UD-Q4_K_XL | 22.2 | 32 GB RAM | cpu | Apache-2.0 | No | [unsloth/Qwen3.5-35B-A3B-GGUF](https://huggingface.co/unsloth/Qwen3.5-35B-A3B-GGUF) `Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf` |
| large | Qwen/Qwen3.5-27B | UD-Q4_K_XL | 17.6 | 32 GB RAM, 24 GB VRAM | gpu | Apache-2.0 | No | [unsloth/Qwen3.5-27B-GGUF](https://huggingface.co/unsloth/Qwen3.5-27B-GGUF) `Qwen3.5-27B-UD-Q4_K_XL.gguf` |
| studio | Qwen/Qwen3.8-27B-FP8 | FP8 | 29.0 | 64 GB RAM, 64 GB VRAM | gpu | Apache-2.0 | No | [Qwen/Qwen3.8-27B-FP8](https://huggingface.co/Qwen/Qwen3.8-27B-FP8) (vLLM) |

The speed figures in that file are estimates from memory bandwidth, not benchmarks.

## Partner-node audit

Open Weights Only forbids partner nodes and closed-source APIs. A node counts as a partner node if ComfyUI marks it `api_node` in `/object_info`. This audit checked every graph against ComfyUI v0.43.0's node list on 2026-10-30, and searched the code for hosted API hosts.

| Where | Result |
|---|---|
| `workflows/*.json` (all, including the in-progress flagship graphs) | **No partner nodes.** All nodes are ComfyUI core, except `LTXFloatToInt` (Lightricks ComfyUI-LTXVideo, used by LTX), `VRAM_Debug` (KJNodes), the LTX IC-LoRA nodes (ComfyUI-LTXVideo) and `PSN_FPSResampler` (this repo) |
| `studio/edits.py`, tool `bgremove` | **Partner node.** The `utility-bria_remove_video_background` template uses `BriaRemoveVideoBackground`. The other 15 tools use local nodes. Hidden in the open edition |
| Apps tab, official apps from ComfyUI's template package | **8 of 11 official apps use partner nodes** (`GeminiImage2Node`, `GeminiNode`, `KlingFirstLastFrameNode`, `GrokImageEditNodeV2`, `GrokImageNode`, `RecraftRemoveBackgroundNode`). The open edition hides them: the studio reads the `api_node` flag and leaves out any app that uses one. A later edition could turn them back on (see EDITIONS.md) |
| `psn_nodes/gen/psn_gemini_prompt_crafter.py` | Prepares requests for a closed API. Not registered as a node in the open edition |
| Language model for the crew | Local by default. Subagents talk only to loopback servers in the Open edition. `STUDIO_LLM_URL` can point the crew at a server you choose |
| `psn/`, `psn_nodes/`, `studio/`, `install.py` | A test (`tests/test_open_edition_no_paid_apis.py`) fails the build if a paid model host or SDK appears in that code. Since 2026-11-02 it reads `studio/` and the installer too, not only `psn/` and `psn_nodes/`. The node `psn_gemini_prompt_crafter` only builds and parses payloads and makes no call; it is still worth removing from an Open Weights entry |
| Every graph in the repository | The same test checks every graph file in the repo (581 files that hold nodes, in `workflows/`, `studio/family_templates/`, the University, Pipelines, Sampling Lab and RES4LYF pages) against the 312 partner nodes ComfyUI 0.43.0 flags `api_node`, kept in `tests/fixtures/partner_nodes.json`. None is used |
| Comfy Cloud | `STUDIO_BACKEND=sdk` sends the same open-weights graphs to Comfy Cloud and spends your credits. It is off by default, and the test checks that the default backend is the local ComfyUI |
| Model browser | Catalogue lookups to Civitai and Hugging Face. No generation goes through them |
| `psn/connectors/registry.py` | Remote generation connectors are marked planned, and off in the Open edition |

## Open Weights Only: the rule and the default path

The contest page (<https://www.comfy.org/open-source-higgsfield>, read 2026-11-02) says of the category: "No partner nodes or closed-source APIs, open-weights models only." Its Q&A adds: "You may use partner models; only the Open Weights Only category requires open-weights models with no partner nodes or closed-source APIs." It names no licence test, so a community or non-commercial licence on downloadable weights is not, on the page's words, a bar. Each such licence is still labelled where you pick the model.

What a person meets first, and what the test above holds:

- **Create opens on the Image goal:** FLUX.2 Klein 4B, Apache-2.0, ungated.
- **Graphs run on the local ComfyUI.** Comfy Cloud is opt-in.
- **The crew's language models** are the Qwen3.5 and Qwen3.8 tiers in the table above, all Apache-2.0, served on this machine.
- **No goal, family template or other graph uses a partner node,** and the two closed models in the Atlas (ChatGPT, Sora) are history cards that cannot be run.

## Where the studio shows a licence

- **Goal tiles** (Create and Models): the badge says Apache-2.0 for an open licence. For any other it names the first limit: Non-commercial, Research only, Revenue cap or Territory limits. Hover for the full terms.
- **Beside Generate:** the picked goal's limits in bold, its licence and a link to the licence text.
- **Family cards and family pages:** the same badge and line, from `studio/licences.py`.
- **Shot Board jobs, the Virtual Set's engine and keyframe pickers, the World Kit character form, Try-on, Train, Motion, Music, Voices, Pipelines and Recipes** each carry their own licence line.

## Family templates and other graphs

Every family the studio can run on its own ComfyUI, with the licence of the models its templates name. "Limits" is what to know before using it commercially or outside the listed territory. Read 2026-11-02 from each repository's Hugging Face card and, where the licence limits use, its text. "In part" means only the named models in that family are limited.

| Family | Kind | Licence | Limits | Source |
|---|---|---|---|---|
| ACE-Step-1.5 | audio | MIT (ACE-Step's repository); the ComfyUI repackage is tagged Apache-2.0 | None | [link](https://huggingface.co/ACE-Step/Ace-Step1.5) |
| Allegro | video | Apache-2.0 | None | [link](https://huggingface.co/rhymes-ai/Allegro-TI2V) |
| AniGen | 3d | MIT | None | [link](https://huggingface.co/VAST-AI/AniGen) |
| Anima | image | CircleStone Labs Non-Commercial License v1.2. Outputs may be used for any purpose | Non-commercial | [link](https://huggingface.co/circlestone-labs/Anima/blob/main/LICENSE.md) |
| AnimateDiff | video | AnimateDiff motion modules: Apache-2.0; AnimateDiff-Lightning: CreativeML OpenRAIL-M. The checkpoint's own licence also applies | None | [link](https://huggingface.co/guoyww/animatediff) |
| Boogu | image | Apache-2.0 (ComfyUI repackage) | None | [link](https://huggingface.co/Comfy-Org/Boogu-Image) |
| CCSR | image | Apache-2.0 (the code repository and the weights' repackage) | None | [link](https://huggingface.co/Kijai/ccsr-safetensors) |
| Chroma | image | Apache-2.0 | None | [link](https://huggingface.co/lodestones/Chroma1-HD) |
| CogVideoX | video | CogVideoX License: free for research; commercial use needs registration, and more than 1 million visits a month needs a further licence | Commercial use needs registration; User cap 1M visits a month | [link](https://huggingface.co/zai-org/CogVideoX-5b/blob/main/LICENSE) |
| colorization | utility | No model repository is recorded for this family | Licence unverified | None recorded |
| Cosmos | video | NVIDIA Open Model License: commercial use allowed | None | [link](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license) |
| DreamX-Creator | image | Apache-2.0 | None | [link](https://huggingface.co/t8star/DreamX-Creator-Comfy) |
| dwpose | utility | Apache-2.0 | None | [link](https://huggingface.co/yzd-v/DWPose) |
| Ernie-Image | image | Apache-2.0 (ComfyUI repackage) | None | [link](https://huggingface.co/Comfy-Org/ERNIE-Image) |
| face | utility | No model repository is recorded for this family | Licence unverified | None recorded |
| Fibo-2.0 | image | CC-BY-NC-4.0, non-commercial (Bria FIBO licence; text gated) | Non-commercial | [link](https://huggingface.co/briaai/Fibo-2.0-dev) |
| FireRed-Image-Edit | image | Apache-2.0 | None | [link](https://huggingface.co/FireRedTeam/FireRed-Image-Edit-1.1-ComfyUI) |
| FitDiT | utility | CC BY-NC-SA 4.0 | Non-commercial | [link](https://huggingface.co/BoyuanJiang/FitDiT) |
| FlashVSR-v1.1 | utility | Apache-2.0 | None | [link](https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1) |
| Flux-Kontext | image | FLUX.1 [dev] Non-Commercial License (text gated) | Non-commercial | [link](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev) |
| Flux.1 | image | Schnell: Apache-2.0. Dev and Redux: FLUX.1 [dev] Non-Commercial License (text gated) | Non-commercial (Dev, Redux) | [link](https://huggingface.co/black-forest-labs/FLUX.1-dev) |
| Flux.2 | image | Klein 4B and Klein Base 4B: Apache-2.0. Klein 9B and Dev: FLUX Non-Commercial License (text gated) | Non-commercial (Klein 9B, Dev) | [link](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) |
| Flux.3-Klein | image | FLUX Kommunity License (text gated): outputs may be used commercially only by companies under US$5,000,000 gross annual revenue | Revenue cap US$5M | [link](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy) |
| frame_interpolation | utility | MIT and Apache-2.0 (ComfyUI repackage) | None | [link](https://huggingface.co/Comfy-Org/Frame-Interpolation) |
| greyscale_to_rgba | utility | No model repository is recorded for this family | Licence unverified | None recorded |
| HiDream | image | MIT | None | [link](https://huggingface.co/HiDream-ai/HiDream-O1-Image) |
| Hunyuan3D-2.1 | 3d | Tencent Hunyuan Community License: it does not apply in the EU, the UK or South Korea; over 1 million monthly users needs a licence from Tencent | Excludes EU, UK, South Korea; User cap 1M monthly users | [link](https://huggingface.co/tencent/Hunyuan3D-2.1/blob/main/LICENSE) |
| HunyuanDiT-1.2 | image | Tencent Hunyuan Community License. HunyuanImage 2.1, also in this family, does not apply in the EU, the UK or South Korea | Excludes EU, UK, South Korea (HunyuanImage 2.1) | [link](https://huggingface.co/tencent/HunyuanImage-2.1) |
| HunyuanVideo | video | Tencent Hunyuan Community License: it does not apply in the EU, the UK or South Korea | Excludes EU, UK, South Korea | [link](https://huggingface.co/tencent/HunyuanVideo-1.5) |
| HunyuanWorld | 3d | Tencent Hunyuan Community License: it does not apply in the EU, the UK or South Korea; over 1 million monthly users needs a licence from Tencent | Excludes EU, UK, South Korea; User cap 1M monthly users | [link](https://huggingface.co/tencent/HunyuanWorld-1) |
| HY-Motion | 3d | Tencent Hunyuan Community License: it does not apply in the EU, the UK or South Korea; over 1 million monthly users needs a licence from Tencent | Excludes EU, UK, South Korea; User cap 1M monthly users | [link](https://huggingface.co/tencent/HY-Motion-1.0) |
| IC-Light | image | Code: Apache-2.0. The weights' own card names no licence | Licence unverified (weights) | [link](https://github.com/lllyasviel/IC-Light/blob/main/LICENSE) |
| Ideogram4 | image | Ideogram 4 Non-Commercial licence (ComfyUI repackage of ideogram-ai/ideogram-4-fp8; text gated) | Non-commercial | [link](https://huggingface.co/ideogram-ai/ideogram-4-fp8) |
| instantCharacter | utility | No licence is stated on its model card | Licence unverified | [link](https://huggingface.co/tencent/InstantCharacter) |
| InstantMesh | 3d | Apache-2.0 | None | [link](https://huggingface.co/TencentARC/InstantMesh) |
| IP-Adapter | utility | Apache-2.0 | None | [link](https://huggingface.co/h94/IP-Adapter) |
| Iris-3B | utility | Apache-2.0 | None | [link](https://huggingface.co/speridlabs/iris-3b) |
| JoyAI-Video-Edit | video | Apache-2.0 | None | [link](https://huggingface.co/jdopensource/JoyAI-Video-Edit) |
| Kandinsky-5.0-T2I-Lite | image | MIT | None | [link](https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers) |
| Kolors | image | Kolors model licence (the card is tagged Apache-2.0): over 100 million monthly users, or a cloud platform, needs a licence | User cap 100M monthly users | [link](https://huggingface.co/Kwai-Kolors/Kolors/blob/main/MODEL_LICENSE) |
| Krea2 | image | Krea 2 Community License: commercial use of the model or its outputs only for companies under US$1,000,000 total annual revenue; content filtering required | Revenue cap US$1M | [link](https://huggingface.co/Comfy-Org/Krea-2/blob/main/LICENSE.pdf) |
| LDM3D-4C | image | CreativeML OpenRAIL-M | None | [link](https://huggingface.co/Intel/ldm3d-4c) |
| LivePortrait | video | MIT; its InsightFace face finder (buffalo_l) is for non-commercial research only | Non-commercial (InsightFace) | [link](https://huggingface.co/KwaiVGI/LivePortrait) |
| LongCat-Avatar-15 | video | MIT | None | [link](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) |
| LongCat-Image | image | Apache-2.0 | None | [link](https://huggingface.co/meituan-longcat/LongCat-Image) |
| Lotus | utility | Apache-2.0 | None | [link](https://huggingface.co/jingheya/lotus-depth-d-v1-1) |
| LTX-2.5 | video | LTX-2.x Community License (gated download): entities with US$10,000,000 or more annual revenue need a paid licence | Revenue cap US$10M | [link](https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x) |
| Lumina-2 | image | Lumina Image 2: Apache-2.0; its Gemma 2 encoder is under the Gemma Terms of Use. The NewBie template adds jina-clip-v2 (CC BY-NC 4.0) and Gemma 3 | Non-commercial (NewBie template) | [link](https://huggingface.co/Comfy-Org/Lumina-Image-2) |
| Matrix-3D | 3d | MIT (gated download) | None | [link](https://huggingface.co/Skywork/Matrix-3D) |
| Matrix-Game-2 | video | MIT | None | [link](https://huggingface.co/Skywork/Matrix-Game-2.0) |
| MIDI-3D | 3d | Apache-2.0 | None | [link](https://huggingface.co/VAST-AI/MIDI-3D) |
| Ming-Image | image | MIT (ComfyUI repackage) | None | [link](https://huggingface.co/Comfy-Org/Ming-Image) |
| Mini-Max-Music3 | audio | MiniMax-Music3 Community License (the ComfyUI repackage is tagged Apache-2.0; the studio follows MiniMax's own text): commercial products must show "MiniMax-Music3", and over US$20,000,000 yearly revenue needs MiniMax's written authorization | Revenue cap US$20M | [link](https://huggingface.co/MiniMaxAI/MiniMax-Music3/blob/main/LICENSE) |
| MiniMax-H3 | video | MiniMax H3 Community License: it excludes the US, the EU, the UK and South Korea, outputs included; commercial products must show "MiniMax H3", and over US$20,000,000 yearly revenue needs MiniMax's written authorization | Excludes US, EU, UK, South Korea; Revenue cap US$20M | [link](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE) |
| Mochi | video | Apache-2.0 | None | [link](https://huggingface.co/genmo/mochi-1-preview) |
| MoGe | 3d | MIT | None | [link](https://huggingface.co/Ruicheng/moge-2-vitl-normal) |
| Moss-Image | image | Apache-2.0 (ComfyUI repackage) | None | [link](https://huggingface.co/Comfy-Org/MOSS-Image) |
| MOVA | video | Apache-2.0 | None | [link](https://huggingface.co/OpenMOSS-Team/MOVA-720p) |
| Omnigen-2 | image | Apache-2.0 | None | [link](https://huggingface.co/OmniGen2/OmniGen2) |
| Ovis-Image | image | Apache-2.0 | None | [link](https://huggingface.co/AIDC-AI/Ovis-Image-7B) |
| PartCrafter | 3d | MIT | None | [link](https://huggingface.co/wgsxm/PartCrafter) |
| Pixal3D | 3d | MIT (ComfyUI repackage) | None | [link](https://huggingface.co/Comfy-Org/Pixal3D) |
| PixArt-Sigma | image | CreativeML OpenRAIL++-M | None | [link](https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS) |
| PixelDiT | image | NVIDIA Source Code License: non-commercial, research or evaluation only | Research only | [link](https://huggingface.co/Comfy-Org/PixelDiT/blob/main/LICENSE) |
| Prism-Alpha | video | No model repository is recorded for this family | Licence unverified | None recorded |
| Qwen-Image-2.1 | image | Qwen-Image, its Edit models and 2512: Apache-2.0. Qwen-Image 2.1: Qwen Research License, research or evaluation only | Research only (Qwen-Image 2.1) | [link](https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE) |
| rife | utility | MIT and Apache-2.0 (ComfyUI repackage) | None | [link](https://huggingface.co/Comfy-Org/Frame-Interpolation) |
| SAM-3D-Body | 3d | SAM License: commercial use allowed, with use rules | None | [link](https://huggingface.co/facebook/sam-3d-body-dinov3) |
| SAM-3D-Objects | 3d | SAM License: commercial use allowed, with use rules | None | [link](https://huggingface.co/facebook/sam-3d-objects) |
| sam3 | utility | SAM License: commercial use allowed, with use rules | None | [link](https://huggingface.co/Comfy-Org/sam3.1/blob/main/LICENSE) |
| SANA-Video | video | Apache-2.0 | None | [link](https://huggingface.co/Efficient-Large-Model/SANA-Video_2.0_5B_720p) |
| SD15 | image | CreativeML OpenRAIL-M | None | [link](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5) |
| SD3-SD3.5 | image | Stability AI Community License (text gated): free commercial use only under US$1,000,000 annual revenue | Revenue cap US$1M | [link](https://stability.ai/community-license-agreement) |
| SDPose | utility | MIT (ComfyUI repackage) | None | [link](https://huggingface.co/Comfy-Org/SDPose) |
| SDXL | image | Base and refiner: CreativeML OpenRAIL++-M. SDXL Turbo: Stability AI Community License, US$1,000,000 revenue cap | Revenue cap US$1M (Turbo) | [link](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) |
| SeedVR2 | utility | Apache-2.0 | None | [link](https://huggingface.co/ByteDance-Seed/SeedVR2-7B) |
| SeFi-Image-2B-turbo | image | CC BY-NC 4.0 | Non-commercial | [link](https://huggingface.co/SeFi-Image/SeFi-Image-2B-turbo) |
| Shap-E | 3d | MIT | None | [link](https://huggingface.co/openai/shap-e) |
| Stable-Cascade | image | Stability AI Non-Commercial Research Community License | Non-commercial | [link](https://huggingface.co/stabilityai/stable-cascade/blob/main/LICENSE) |
| Stable-Fast-3D | 3d | Stability AI Community License (text gated): free commercial use only under US$1,000,000 annual revenue | Revenue cap US$1M | [link](https://stability.ai/community-license-agreement) |
| SVD | video | Stable Video Diffusion 1.1 Community License (Stability AI Community License): free commercial use only under US$1,000,000 annual revenue | Revenue cap US$1M | [link](https://stability.ai/community-license-agreement) |
| TRELLIS-2-4B | 3d | MIT. Its image encoder DINOv3 is under the DINOv3 License (commercial use allowed); BiRefNet is MIT | None | [link](https://huggingface.co/microsoft/TRELLIS.2-4B) |
| TripoSplat | 3d | MIT | None | [link](https://huggingface.co/VAST-AI/TripoSplat) |
| TripoSR | 3d | MIT | None | [link](https://huggingface.co/stabilityai/TripoSR) |
| TurboWan2.2-I2V | video | Apache-2.0 | None | [link](https://huggingface.co/TurboDiffusion/TurboWan2.2-I2V-A14B-720P) |
| UniRig | 3d | MIT | None | [link](https://huggingface.co/VAST-AI/UniRig) |
| upscale_models | utility | Real-ESRGAN: BSD-3-Clause; BiRefNet: MIT | None | [link](https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE) |
| VLM | llm | Varies by model: Florence-2 MIT; Qwen3, Qwen3.5, Qwen3-VL and Gemma 4 Apache-2.0 | None | [link](https://huggingface.co/microsoft/Florence-2-large) |
| Wan-SCAIL-2 | video | MIT (ComfyUI repackage); the lightx2v distill LoRA is Apache-2.0 | None | [link](https://huggingface.co/Comfy-Org/SCAIL-2) |
| Wan2.1 | video | Apache-2.0; InfiniteTalk Apache-2.0, its wav2vec2 encoder MIT | None | [link](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| Wan2.2 | video | Apache-2.0 | None | [link](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B) |
| Wan2.2-Animate | video | Apache-2.0 | None | [link](https://huggingface.co/Wan-AI/Wan2.2-Animate-14B) |
| Wan2.2-Dancer | video | Apache-2.0 (ComfyUI repackage) | None | [link](https://huggingface.co/Comfy-Org/Wan-Dancer) |
| yue2 | audio | CC BY-NC 4.0 | Non-commercial | [link](https://huggingface.co/m-a-p/YuE2-3B) |
| Z-Image | image | Apache-2.0 | None | [link](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) |

### Other files the graphs name

| File or model | Used by | Licence | Limits |
|---|---|---|---|
| MiniMax H3 Fun ControlNet Union 2.0 | Virtual Set, mode A | MiniMax H3 Community License | Excludes US, EU, UK, South Korea; revenue cap US$20M |
| LTX-2.5 Layout To Render IC-LoRA | Virtual Set, mode A | LTX-2.x Community License | Revenue cap US$10M |
| Wan 2.2 Fun Control 14B, lightx2v 4-step LoRAs | Virtual Set, mode A | Apache-2.0 | None |
| Qwen-Image 2.1, its outfit-swap LoRA | Virtual Set keyframes, Try-on | Qwen Research License; the LoRA is rent-only at its source | Research only |
| FLUX.2 Klein try-on LoRAs (Civitai) | Try-on | Klein 4B Apache-2.0, Klein 9B FLUX Non-Commercial; the LoRAs are rent-only | Non-commercial (labelled on the page) |
| SAM 3.1, SAM 3D Body | World Kit cut-out and body photo | SAM License | None |
| MoGe 2, TRELLIS.2, BiRefNet | World Kit | MIT; TRELLIS.2's DINOv3 encoder is under the DINOv3 License | None |
| ACE-Step 1.5 | Music page | MIT (ComfyUI repackage tagged Apache-2.0) | None |
| YuE2, SheetSage2 | Music page | CC BY-NC 4.0 | Non-commercial |
| Stable Audio Open 1.0 | Music page | Stability AI Community License | Revenue cap US$1M |
| Z-Image Turbo Fun ControlNet Union, Lotus depth, SD VAE ft-MSE | Pipelines (Room through a century) | Apache-2.0, Apache-2.0, MIT | None |
| DreamShaper 8 | Sampling Lab, RES4LYF page | CreativeML OpenRAIL-M | None |
| Kimodo SOMA | Motion | NVIDIA Open Model License; its text encoder Llama 3 is under the Meta Llama 3 Community License | None (Kimodo SMPL-X, under NVIDIA's R&D licence, is not offered) |
| LatentSync 1.6 | Motion | OpenRAIL++ | None; it finds faces with InsightFace, below |
| InsightFace `buffalo_l` | Character picture check, LivePortrait, LatentSync | InsightFace model zoo: "ALL models are available for non-commercial research purposes only." | Non-commercial; not shipped, you download it |
| Kokoro 82M | Voices | Apache-2.0 | None |
| FASHN VTON 1.5 | Try-on | Apache-2.0 | None |

