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
| Every graph in the repository | The same test checks every graph file in the repo (746 files that hold nodes, in `workflows/`, `studio/family_templates/`, the University, Pipelines, Sampling Lab, RES4LYF, blepping and Pack Lab pages) against 334 partner node ids: the 312 ComfyUI 0.43.0 flags `api_node`, kept in `tests/fixtures/partner_nodes.json`, plus its partner-node source list in `tests/partner_node_ids.txt` (322 ids; the two lists differ by a few). None is used |
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

<!-- model-files:start (scripts/build_model_links.py writes this part) -->

## Every model file, with its download link

Every model file a shipped graph, template, recipe, pipeline, family or feature names: 714 files. 641 have an official download checked against the Hugging Face API on 2026-11-03 (the file is in the repository's listing; size and SHA-256 are from that listing); 4 are release assets of the project on GitHub (size checked, no published SHA-256); and 1 is on ModelScope (SHA-256 matched). 48 sit in gated repositories (accept the licence on the model page and set `HF_TOKEN`), and 61 are under a licence the card marks non-commercial or research-only. 68 have no download the helper can fetch: 45 are on Civitai only (44 with their Civitai page, confirmed by SHA-256 or by file name and size), 2 were trained here, and 21 have no public source we could find. They are listed at the end of their family's table. The same data is in [`studio/models_manifest.json`](studio/models_manifest.json) under `files`.

**Get them:** `python3 scripts/get_models.py --for all --dry-run` lists what is missing; drop `--dry-run` to download. `--for image` (a goal), `--for family:Anima` (a family) or `--for flux-2-klein-4b.safetensors` (one file) narrow it. It resumes, checks SHA-256, skips files already in place, and reads `HF_TOKEN` only from the environment.

Licence here is the Hugging Face card's own field. The family tables above say what each licence limits; read the licence before you rely on it.

### ACE-Step-1.5

Used by: workflows `gamebuilder_ace15_music_api`, `music_ace15_turbo_api`, `music_ace15_xl_base_api`, `music_ace15_xl_turbo_api`, `music_roti_ace_cover_api`, `music_roti_ace_edit_api`, `music_roti_ace_extract_api`; 9 family templates; pipeline graphs `studio/web/pipelines/anime_short/graphs/score`, `studio/web/pipelines/room_century/graphs/score`; Music page `ace15_turbo`, `ace15_xl_base`, `ace15_xl_turbo`; features `gamebuilder/models`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `ace_1.5_vae.safetensors` | `vae/ace_1.5_vae.safetensors` | 0.31 | apache-2.0 | [Comfy-Org/ACE-Step-1.5](https://huggingface.co/Comfy-Org/ACE-Step-1.5/resolve/main/split_files/vae/ace_1.5_vae.safetensors) |
| `ace_step_1.5_turbo_aio.safetensors` | `checkpoints/ace_step_1.5_turbo_aio.safetensors` | 9.34 | apache-2.0 | [Comfy-Org/ACE-Step-1.5](https://huggingface.co/Comfy-Org/ACE-Step-1.5/resolve/main/checkpoints/ace_step_1.5_turbo_aio.safetensors) |
| `ace_step_v1_3.5b.safetensors` | `checkpoints/ace_step_v1_3.5b.safetensors` | 7.17 | apache-2.0 | [Comfy-Org/ACE-Step](https://huggingface.co/Comfy-Org/ACE-Step/resolve/main/all_in_one/ace_step_v1_3.5b.safetensors) |
| `acestep_v1.5_turbo.safetensors` | `diffusion_models/acestep_v1.5_turbo.safetensors` | 4.46 | apache-2.0 | [Comfy-Org/ACE-Step-1.5](https://huggingface.co/Comfy-Org/ACE-Step-1.5/resolve/main/split_files/diffusion_models/acestep_v1.5_turbo.safetensors) |
| `acestep_v1.5_xl_base_bf16.safetensors` | `diffusion_models/acestep_v1.5_xl_base_bf16.safetensors` | 9.29 | apache-2.0 | [Comfy-Org/ACE-Step-1.5](https://huggingface.co/Comfy-Org/ACE-Step-1.5/resolve/main/split_files/diffusion_models/acestep_v1.5_xl_base_bf16.safetensors) |
| `acestep_v1.5_xl_sft_bf16.safetensors` | `diffusion_models/acestep_v1.5_xl_sft_bf16.safetensors` | 9.29 | apache-2.0 | [Comfy-Org/ACE-Step-1.5](https://huggingface.co/Comfy-Org/ACE-Step-1.5/resolve/main/split_files/diffusion_models/acestep_v1.5_xl_sft_bf16.safetensors) |
| `acestep_v1.5_xl_turbo_bf16.safetensors` | `diffusion_models/acestep_v1.5_xl_turbo_bf16.safetensors` | 9.29 | apache-2.0 | [Comfy-Org/ACE-Step-1.5](https://huggingface.co/Comfy-Org/ACE-Step-1.5/resolve/main/split_files/diffusion_models/acestep_v1.5_xl_turbo_bf16.safetensors) |
| `qwen_0.6b_ace15.safetensors` | `text_encoders/qwen_0.6b_ace15.safetensors` | 1.11 | apache-2.0 | [Comfy-Org/ACE-Step-1.5](https://huggingface.co/Comfy-Org/ACE-Step-1.5/resolve/main/split_files/text_encoders/qwen_0.6b_ace15.safetensors) |
| `qwen_1.7b_ace15.safetensors` | `text_encoders/qwen_1.7b_ace15.safetensors` | 3.45 | apache-2.0 | [Comfy-Org/ACE-Step-1.5](https://huggingface.co/Comfy-Org/ACE-Step-1.5/resolve/main/split_files/text_encoders/qwen_1.7b_ace15.safetensors) |
| `qwen_4b_ace15.safetensors` | `text_encoders/qwen_4b_ace15.safetensors` | 7.80 | apache-2.0 | [Comfy-Org/ACE-Step-1.5](https://huggingface.co/Comfy-Org/ACE-Step-1.5/resolve/main/split_files/text_encoders/qwen_4b_ace15.safetensors) |

10 files, 61.52 GiB with a known size.

### Anima

Used by: goals `anime`; workflows `anima_core_t2i_api`, `oneclick_angles_api`, `oneclick_effect_api`, `oneclick_effect_clip_api`, `oneclick_relight_api`, `worldkit_krea2_t2i_api`; 11 studio templates; 35 family templates; 10 pipeline graphs; LoRA recipes `lora_435024ade2`; features `goals`, `train_bases`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `anima-aesthetic-v1.1.safetensors` | `diffusion_models/anima-aesthetic-v1.1.safetensors` | 3.90 | circlestone-labs-non-commercial-license (non-commercial) | [circlestone-labs/Anima](https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/diffusion_models/anima-aesthetic-v1.1.safetensors) |
| `anima-base-v1.0.safetensors` | `diffusion_models/anima-base-v1.0.safetensors` | 3.89 | circlestone-labs-non-commercial-license (non-commercial) | [circlestone-labs/Anima](https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/diffusion_models/anima-base-v1.0.safetensors) |
| `anima-lllite-any-test-like-v2.safetensors` | `model_patches/anima-lllite-any-test-like-v2.safetensors` | 0.02 | circlestone-labs-non-commercial-license (non-commercial) | [Comfy-Org/Anima-LLLite](https://huggingface.co/Comfy-Org/Anima-LLLite/resolve/main/model_patches/anima-lllite-any-test-like-v2.safetensors) |
| `anima-lllite-depth-1.safetensors` | `model_patches/anima-lllite-depth-1.safetensors` | 0.01 | circlestone-labs-non-commercial-license (non-commercial) | [Comfy-Org/Anima-LLLite](https://huggingface.co/Comfy-Org/Anima-LLLite/resolve/main/model_patches/anima-lllite-depth-1.safetensors) |
| `anima-lllite-inpainting-v2.safetensors` | `model_patches/anima-lllite-inpainting-v2.safetensors` | 0.06 | circlestone-labs-non-commercial-license (non-commercial) | [Comfy-Org/Anima-LLLite](https://huggingface.co/Comfy-Org/Anima-LLLite/resolve/main/model_patches/anima-lllite-inpainting-v2.safetensors) |
| `anima-preview3-base.safetensors` | `diffusion_models/anima-preview3-base.safetensors` | 3.89 | circlestone-labs-non-commercial-license (non-commercial) | [circlestone-labs/Anima](https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/diffusion_models/anima-preview3-base.safetensors) |
| `anima-turbo-lora-v0.2.safetensors` | `loras/anima-turbo-lora-v0.2.safetensors` | 0.14 | not stated on the card | [circlestone-labs/Anima-Official-LoRAs](https://huggingface.co/circlestone-labs/Anima-Official-LoRAs/resolve/main/anima-turbo-lora-v0.2.safetensors) |
| `anima-turbo-v1.1.safetensors` | `diffusion_models/anima-turbo-v1.1.safetensors` | 3.90 | circlestone-labs-non-commercial-license (non-commercial) | [circlestone-labs/Anima](https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/diffusion_models/anima-turbo-v1.1.safetensors) |
| `depth_anything_3_mono_large.safetensors` | `geometry_estimation/depth_anything_3_mono_large.safetensors` | 1.24 | apache-2.0 | [Comfy-Org/Depth-Anything-3](https://huggingface.co/Comfy-Org/Depth-Anything-3/resolve/main/geometry_estimation/depth_anything_3_mono_large.safetensors) |
| `qwen_3_06b_base.safetensors` | `text_encoders/qwen_3_06b_base.safetensors` | 1.11 | circlestone-labs-non-commercial-license (non-commercial) | [circlestone-labs/Anima](https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/text_encoders/qwen_3_06b_base.safetensors) |
| `qwen_image_vae.safetensors` | `vae/qwen_image_vae.safetensors` | 0.24 | circlestone-labs-non-commercial-license (non-commercial) | [circlestone-labs/Anima](https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/vae/qwen_image_vae.safetensors) |

11 files, 18.39 GiB with a known size.

### AnimateDiff

Used by: 27 studio templates; 32 family templates; University graphs `studio/university/graphs/d_merge_add_difference`, `studio/university/graphs/sd15_merge`, `studio/university/graphs/sdxl_txt2img`; 290 other graphs; features `feature_doctor`, `sampling_graph`, `train_bases`, `words_graph`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `animatediff_lightning_4step_comfyui.safetensors` | `animatediff_models/animatediff_lightning_4step_comfyui.safetensors` | 0.85 | creativeml-openrail-m | [ByteDance/AnimateDiff-Lightning](https://huggingface.co/ByteDance/AnimateDiff-Lightning/resolve/main/animatediff_lightning_4step_comfyui.safetensors) |
| `DreamShaper_8_pruned.safetensors` | `checkpoints/DreamShaper_8_pruned.safetensors` | 1.99 | other | [Lykon/DreamShaper](https://huggingface.co/Lykon/DreamShaper/resolve/main/DreamShaper_8_pruned.safetensors) |
| `mm_sd_v15_v2.ckpt` | `animatediff_models/mm_sd_v15_v2.ckpt` | 1.69 | apache-2.0 | [guoyww/animatediff](https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt) |
| `mm_sdxl_v10_beta.ckpt` | `animatediff_models/mm_sdxl_v10_beta.ckpt` | 0.88 | apache-2.0 | [guoyww/animatediff](https://huggingface.co/guoyww/animatediff/resolve/main/mm_sdxl_v10_beta.ckpt) |
| `sd_xl_base_1.0.safetensors` | `checkpoints/sd_xl_base_1.0.safetensors` | 6.46 | openrail++ | [stabilityai/stable-diffusion-xl-base-1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors) |
| `v3_sd15_mm.ckpt` | `animatediff_models/v3_sd15_mm.ckpt` | 1.56 | apache-2.0 | [guoyww/animatediff](https://huggingface.co/guoyww/animatediff/resolve/main/v3_sd15_mm.ckpt) |

6 files, 13.43 GiB with a known size.

### Boogu

Used by: workflows `oneclick_matte_api`, `vset_keyframe_edit_api`; 21 studio templates; 56 family templates; 10 pipeline graphs; University graphs `studio/university/graphs/b_unet_fp8`, `studio/university/graphs/c_flux_guidance`, `studio/university/graphs/c_style_redux`; 18 other graphs; features `train_bases`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `ae.safetensors` | `vae/ae.safetensors` | 0.31 | apache-2.0 | [Comfy-Org/Lumina-Image-2](https://huggingface.co/Comfy-Org/Lumina-Image-2/resolve/main/split_files/vae/ae.safetensors) |
| `boogu_image_edit_fp8_scaled.safetensors` | `diffusion_models/boogu_image_edit_fp8_scaled.safetensors` | 9.61 | apache-2.0 | [Comfy-Org/Boogu-Image](https://huggingface.co/Comfy-Org/Boogu-Image/resolve/main/diffusion_models/boogu_image_edit_fp8_scaled.safetensors) |
| `boogu_image_edit_int8_convrot.safetensors` | `diffusion_models/boogu_image_edit_int8_convrot.safetensors` | 10.59 | apache-2.0 | [Comfy-Org/Boogu-Image](https://huggingface.co/Comfy-Org/Boogu-Image/resolve/main/diffusion_models/boogu_image_edit_int8_convrot.safetensors) |
| `boogu_image_edit_turbo_hotfix_1k_20260708_int8_convrot.safetensors` | `diffusion_models/boogu_image_edit_turbo_hotfix_1k_20260708_int8_convrot.safetensors` | 9.62 | apache-2.0 | [Comfy-Org/Boogu-Image](https://huggingface.co/Comfy-Org/Boogu-Image/resolve/main/diffusion_models/boogu_image_edit_turbo_hotfix_1k_20260708_int8_convrot.safetensors) |
| `boogu_image_turbo_fp8_scaled.safetensors` | `diffusion_models/boogu_image_turbo_fp8_scaled.safetensors` | 9.61 | apache-2.0 | [Comfy-Org/Boogu-Image](https://huggingface.co/Comfy-Org/Boogu-Image/resolve/main/diffusion_models/boogu_image_turbo_fp8_scaled.safetensors) |
| `boogu_image_turbo_hotfix_int8_convrot.safetensors` | `diffusion_models/boogu_image_turbo_hotfix_int8_convrot.safetensors` | 10.59 | apache-2.0 | [Comfy-Org/Boogu-Image](https://huggingface.co/Comfy-Org/Boogu-Image/resolve/main/diffusion_models/boogu_image_turbo_hotfix_int8_convrot.safetensors) |
| `qwen3vl_8b_bf16.safetensors` | `text_encoders/qwen3vl_8b_bf16.safetensors` | 16.33 | apache-2.0 | [Comfy-Org/Qwen3-VL](https://huggingface.co/Comfy-Org/Qwen3-VL/resolve/main/text_encoders/qwen3vl_8b_bf16.safetensors) |
| `qwen3vl_8b_fp8_scaled.safetensors` | `text_encoders/qwen3vl_8b_fp8_scaled.safetensors` | 9.86 | apache-2.0 | [Comfy-Org/Qwen3-VL](https://huggingface.co/Comfy-Org/Qwen3-VL/resolve/main/text_encoders/qwen3vl_8b_fp8_scaled.safetensors) |

8 files, 76.51 GiB with a known size.

### CCSR

Used by: studio templates `ccsr_upscale_x2`; family templates `ccsr_upscale_x2`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `real-world_ccsr-fp16.safetensors` | `checkpoints/real-world_ccsr-fp16.safetensors` | 3.20 | apache-2.0 | [Kijai/ccsr-safetensors](https://huggingface.co/Kijai/ccsr-safetensors/resolve/main/real-world_ccsr-fp16.safetensors) |

1 files, 3.20 GiB with a known size.

### Chroma

Used by: 5 studio templates; 17 family templates; University graphs `studio/university/graphs/c_flux_guidance`, `studio/university/graphs/c_style_redux`, `studio/university/graphs/sd35_flow`; 26 other graphs; features `sampling_graph`, `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `Chroma1-HD-fp8mixed.safetensors` | `diffusion_models/Chroma1-HD-fp8mixed.safetensors` | 8.56 | apache-2.0 | [Comfy-Org/Chroma1-HD](https://huggingface.co/Comfy-Org/Chroma1-HD/resolve/main/split_files/diffusion_models/Chroma1-HD-fp8mixed.safetensors) |
| `t5xxl_fp16.safetensors` | `text_encoders/t5xxl_fp16.safetensors` | 9.12 | apache-2.0 | [comfyanonymous/flux_text_encoders](https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors) |

2 files, 17.68 GiB with a known size.

### Cosmos

Used by: goals `reshoot_wan`; workflows `campath_wan_api`, `vset_wan22_funcontrol_api`, `wan_camera_api`; 6 studio templates; 29 family templates; features `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `cosmos_predict2_14B_t2i.safetensors` | `diffusion_models/cosmos_predict2_14B_t2i.safetensors` | 26.57 | nvidia-open-model-license | [Comfy-Org/Cosmos-Predict2](https://huggingface.co/Comfy-Org/Cosmos-Predict2/resolve/main/cosmos_predict2_14B_t2i.safetensors) |
| `oldt5_xxl_fp8_e4m3fn_scaled.safetensors` | `text_encoders/oldt5_xxl_fp8_e4m3fn_scaled.safetensors` | 4.56 | not stated on the card | [comfyanonymous/cosmos_1.0_text_encoder_and_VAE_ComfyUI](https://huggingface.co/comfyanonymous/cosmos_1.0_text_encoder_and_VAE_ComfyUI/resolve/main/text_encoders/oldt5_xxl_fp8_e4m3fn_scaled.safetensors) |
| `wan_2.1_vae.safetensors` | `vae/wan_2.1_vae.safetensors` | 0.24 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/vae/wan_2.1_vae.safetensors) |

3 files, 31.37 GiB with a known size.

### Crew language models

Used by: features `llm_tiers`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `Qwen3.5-27B-UD-Q4_K_XL.gguf` | `LLM/Qwen3.5-27B-UD-Q4_K_XL.gguf` | 16.41 | apache-2.0 | [unsloth/Qwen3.5-27B-GGUF](https://huggingface.co/unsloth/Qwen3.5-27B-GGUF/resolve/main/Qwen3.5-27B-UD-Q4_K_XL.gguf) |
| `Qwen3.5-2B-Q8_0.gguf` | `LLM/Qwen3.5-2B-Q8_0.gguf` | 1.87 | apache-2.0 | [unsloth/Qwen3.5-2B-GGUF](https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/main/Qwen3.5-2B-Q8_0.gguf) |
| `Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf` | `LLM/Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf` | 20.71 | apache-2.0 | [unsloth/Qwen3.5-35B-A3B-GGUF](https://huggingface.co/unsloth/Qwen3.5-35B-A3B-GGUF/resolve/main/Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf) |
| `Qwen3.5-4B-UD-Q6_K_XL.gguf` | `LLM/Qwen3.5-4B-UD-Q6_K_XL.gguf` | 3.86 | apache-2.0 | [unsloth/Qwen3.5-4B-GGUF](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-UD-Q6_K_XL.gguf) |
| `Qwen3.5-9B-UD-Q5_K_XL.gguf` | `LLM/Qwen3.5-9B-UD-Q5_K_XL.gguf` | 6.28 | apache-2.0 | [unsloth/Qwen3.5-9B-GGUF](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-UD-Q5_K_XL.gguf) |

5 files, 49.14 GiB with a known size.

### Ernie-Image

Used by: goals `flux3`, `image`, `product`; workflows `flux2_klein4b_t2i_api`, `flux3_klein_core_t2i_api`; 17 studio templates; 31 family templates; 6 pipeline graphs; University graphs `studio/university/graphs/c_klein_fast`, `studio/university/graphs/wf_flux2_klein`; features `train_bases`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `ernie-image-prompt-enhancer.safetensors` | `text_encoders/ernie-image-prompt-enhancer.safetensors` | 6.41 | apache-2.0 | [Comfy-Org/ERNIE-Image](https://huggingface.co/Comfy-Org/ERNIE-Image/resolve/main/text_encoders/ernie-image-prompt-enhancer.safetensors) |
| `ernie-image-turbo.safetensors` | `diffusion_models/ernie-image-turbo.safetensors` | 14.96 | apache-2.0 | [Comfy-Org/ERNIE-Image](https://huggingface.co/Comfy-Org/ERNIE-Image/resolve/main/diffusion_models/ernie-image-turbo.safetensors) |
| `ernie-image.safetensors` | `diffusion_models/ernie-image.safetensors` | 14.96 | apache-2.0 | [Comfy-Org/ERNIE-Image](https://huggingface.co/Comfy-Org/ERNIE-Image/resolve/main/diffusion_models/ernie-image.safetensors) |
| `flux2-vae.safetensors` | `vae/flux2-vae.safetensors` | 0.31 | apache-2.0 | [Comfy-Org/Flux-2-Klein-4B](https://huggingface.co/Comfy-Org/Flux-2-Klein-4B/resolve/main/split_files/vae/flux2-vae.safetensors) |
| `ministral-3-3b.safetensors` | `text_encoders/ministral-3-3b.safetensors` | 7.19 | apache-2.0 | [Comfy-Org/ERNIE-Image](https://huggingface.co/Comfy-Org/ERNIE-Image/resolve/main/text_encoders/ministral-3-3b.safetensors) |

5 files, 43.83 GiB with a known size.

### face

Used by: studio templates `face_gfpgan_restore`; family templates `face_gfpgan_restore`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `detection_Resnet50_Final.pth` | `face_detection/detection_Resnet50_Final.pth` | 0.10 | MIT (the project's code repository) | [GitHub release](https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth) |
| `GFPGANv1.4.pth` | `face_restoration/GFPGANv1.4.pth` | 0.32 | unknown | [GitHub release](https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth) |
| `parsing_bisenet.pth` | `face_detection/parsing_bisenet.pth` | 0.05 | MIT (the project's code repository) | [GitHub release](https://github.com/xinntao/facexlib/releases/download/v0.2.0/parsing_bisenet.pth) |
| `parsing_parsenet.pth` | `face_detection/parsing_parsenet.pth` | 0.08 | MIT (the project's code repository) | [GitHub release](https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth) |

4 files, 0.56 GiB with a known size.

### Fibo-2.0

Used by: goals `flux3`, `product`; workflows `flux3_klein_core_t2i_api`, `worldkit_krea2_t2i_api`; 9 studio templates; 17 family templates; 4 pipeline graphs; features `train_bases`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `fibo2_dev_int8_convrot.safetensors` | `diffusion_models/fibo2_dev_int8_convrot.safetensors` | 7.83 | cc-by-nc-4.0 (non-commercial) | [Comfy-Org/Fibo-2.0](https://huggingface.co/Comfy-Org/Fibo-2.0/resolve/main/diffusion_models/fibo2_dev_int8_convrot.safetensors) |
| `fibo2_edit_turbo_int8_convrot.safetensors` | `diffusion_models/fibo2_edit_turbo_int8_convrot.safetensors` | 7.83 | cc-by-nc-4.0 (non-commercial) | [Comfy-Org/Fibo-2.0](https://huggingface.co/Comfy-Org/Fibo-2.0/resolve/main/diffusion_models/fibo2_edit_turbo_int8_convrot.safetensors) |
| `fibo_2.0_turbo_lora_avg_rank_270_bf16.safetensors` | `loras/fibo_2.0_turbo_lora_avg_rank_270_bf16.safetensors` | 1.85 | cc-by-nc-4.0 (non-commercial) | [Comfy-Org/Fibo-2.0](https://huggingface.co/Comfy-Org/Fibo-2.0/resolve/main/loras/fibo_2.0_turbo_lora_avg_rank_270_bf16.safetensors) |
| `qwen3vl_4b_bf16.safetensors` | `text_encoders/qwen3vl_4b_bf16.safetensors` | 8.27 | flux-kommunity-license | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/resolve/main/text_encoders/qwen3vl_4b_bf16.safetensors) (gated) |
| `qwen3vl_8b_int8_convrot.safetensors` | `text_encoders/qwen3vl_8b_int8_convrot.safetensors` | 8.71 | apache-2.0 | [Comfy-Org/Qwen3-VL](https://huggingface.co/Comfy-Org/Qwen3-VL/resolve/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors) |

5 files, 34.49 GiB with a known size.

### FireRed-Image-Edit

Used by: workflows `oneclick_angles_api`, `oneclick_effect_api`, `oneclick_effect_clip_api`, `oneclick_relight_api`; 6 studio templates; 31 family templates; features `feature_oneclick`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `FireRed-Image-Edit-1.1-Lightning-8steps-v1.2.safetensors` | `loras/FireRed-Image-Edit-1.1-Lightning-8steps-v1.2.safetensors` | 0.79 | apache-2.0 | [FireRedTeam/FireRed-Image-Edit-1.1-ComfyUI](https://huggingface.co/FireRedTeam/FireRed-Image-Edit-1.1-ComfyUI/resolve/main/FireRed-Image-Edit-1.1-Lightning-8steps-v1.2.safetensors) |
| `FireRed-Image-Edit-1.1-transformer.safetensors` | `diffusion_models/FireRed-Image-Edit-1.1-transformer.safetensors` | 38.05 | apache-2.0 | [FireRedTeam/FireRed-Image-Edit-1.1-ComfyUI](https://huggingface.co/FireRedTeam/FireRed-Image-Edit-1.1-ComfyUI/resolve/main/FireRed-Image-Edit-1.1-transformer.safetensors) |
| `qwen_2.5_vl_7b_fp8_scaled.safetensors` | `text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` | 8.74 | apache-2.0 | [Comfy-Org/Qwen-Image](https://huggingface.co/Comfy-Org/Qwen-Image/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors) |

3 files, 47.59 GiB with a known size.

### Flux-Kontext

Used by: 6 studio templates; 25 family templates; University graphs `studio/university/graphs/c_flux_guidance`, `studio/university/graphs/c_style_redux`, `studio/university/graphs/sd35_flow`; 26 other graphs; features `sampling_graph`, `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `clip_l.safetensors` | `text_encoders/clip_l.safetensors` | 0.23 | apache-2.0 | [comfyanonymous/flux_text_encoders](https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors) |
| `flux1-dev-kontext_fp8_scaled.safetensors` | `diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors` | 11.09 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-1-Kontext-Dev](https://huggingface.co/Comfy-Org/Flux-1-Kontext-Dev/resolve/main/split_files/diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors) |
| `t5xxl_fp8_e4m3fn_scaled.safetensors` | `text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors` | 4.80 | mit | [Comfy-Org/HiDream](https://huggingface.co/Comfy-Org/HiDream/resolve/main/split_files/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors) |

3 files, 16.12 GiB with a known size.

### Flux.1

Used by: goals `image`; workflows `flux2_klein4b_t2i_api`, `oneclick_matte_api`; 8 studio templates; 36 family templates; 65 recipes and pipelines; 14 pipeline graphs; 4 University graphs; 20 other graphs; LoRA recipes `lora_0d207abaad`, `lora_2eb366ecb5`, `lora_398d2ad270`; features `commercials`, `feature_motion`, `goals`, `train_bases`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `flux-2-klein-4b.safetensors` | `diffusion_models/flux-2-klein-4b.safetensors` | 7.22 | apache-2.0 | [Comfy-Org/Flux-2-Klein-4B](https://huggingface.co/Comfy-Org/Flux-2-Klein-4B/resolve/main/split_files/diffusion_models/flux-2-klein-4b.safetensors) |
| `flux-2-klein-base-4b.safetensors` | `diffusion_models/flux-2-klein-base-4b.safetensors` | 7.22 | apache-2.0 | [Comfy-Org/Flux-2-Klein-4B](https://huggingface.co/Comfy-Org/Flux-2-Klein-4B/resolve/main/split_files/diffusion_models/flux-2-klein-base-4b.safetensors) |
| `flux.1-fill-dev-OneReward-transformer_fp8.safetensors` | `diffusion_models/flux.1-fill-dev-OneReward-transformer_fp8.safetensors` | 11.09 | cc-by-nc-4.0 (non-commercial) | [Comfy-Org/OneReward](https://huggingface.co/Comfy-Org/OneReward/resolve/main/split_files/diffusion_models/flux.1-fill-dev-OneReward-transformer_fp8.safetensors) |
| `flux1-canny-dev.safetensors` | `diffusion_models/flux1-canny-dev.safetensors` | 22.17 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-1-Dev](https://huggingface.co/Comfy-Org/Flux-1-Dev/resolve/main/split_files/diffusion_models/flux1-canny-dev.safetensors) |
| `flux1-depth-dev-lora.safetensors` | `loras/flux1-depth-dev-lora.safetensors` | 1.16 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-1-Dev](https://huggingface.co/Comfy-Org/Flux-1-Dev/resolve/main/split_files/loras/flux1-depth-dev-lora.safetensors) |
| `flux1-dev-fp8.safetensors` | `checkpoints/flux1-dev-fp8.safetensors` | 16.06 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-1-Dev](https://huggingface.co/Comfy-Org/Flux-1-Dev/resolve/main/flux1-dev-fp8.safetensors) |
| `flux1-dev.safetensors` | `diffusion_models/flux1-dev.safetensors` | 22.17 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-1-Dev](https://huggingface.co/Comfy-Org/Flux-1-Dev/resolve/main/flux1-dev.safetensors) |
| `flux1-fill-dev.safetensors` | `diffusion_models/flux1-fill-dev.safetensors` | 22.17 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-1-Dev](https://huggingface.co/Comfy-Org/Flux-1-Dev/resolve/main/split_files/diffusion_models/flux1-fill-dev.safetensors) |
| `flux1-krea-dev_fp8_scaled.safetensors` | `diffusion_models/flux1-krea-dev_fp8_scaled.safetensors` | 11.09 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-1-Krea-Dev](https://huggingface.co/Comfy-Org/Flux-1-Krea-Dev/resolve/main/split_files/diffusion_models/flux1-krea-dev_fp8_scaled.safetensors) |
| `flux1-redux-dev.safetensors` | `style_models/flux1-redux-dev.safetensors` | 0.12 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-1-Redux-Dev](https://huggingface.co/Comfy-Org/Flux-1-Redux-Dev/resolve/main/flux1-redux-dev.safetensors) |
| `flux1-schnell-fp8.safetensors` | `checkpoints/flux1-schnell-fp8.safetensors` | 16.05 | apache-2.0 | [Comfy-Org/Flux-1-Schnell](https://huggingface.co/Comfy-Org/Flux-1-Schnell/resolve/main/flux1-schnell-fp8.safetensors) |
| `flux1-schnell.safetensors` | `diffusion_models/flux1-schnell.safetensors` | 22.15 | apache-2.0 | [Comfy-Org/Flux-1-Schnell](https://huggingface.co/Comfy-Org/Flux-1-Schnell/resolve/main/flux1-schnell.safetensors) |
| `lotus-depth-d-v1-1.safetensors` | `diffusion_models/lotus-depth-d-v1-1.safetensors` | 1.62 | apache-2.0 | [Comfy-Org/lotus](https://huggingface.co/Comfy-Org/lotus/resolve/main/lotus-depth-d-v1-1.safetensors) |
| `qwen_3_4b.safetensors` | `text_encoders/qwen_3_4b.safetensors` | 7.49 | apache-2.0 | [Comfy-Org/Flux-2-Klein-4B](https://huggingface.co/Comfy-Org/Flux-2-Klein-4B/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors) |
| `removal_timestep_alpha-2-1740.safetensors` | `loras/removal_timestep_alpha-2-1740.safetensors` | 0.08 | mit | [lrzjason/ObjectRemovalFluxFill](https://huggingface.co/lrzjason/ObjectRemovalFluxFill/resolve/main/removal_timestep_alpha-2-1740.safetensors) (community upload) |
| `sigclip_vision_patch14_384.safetensors` | `clip_vision/sigclip_vision_patch14_384.safetensors` | 0.80 | apache-2.0 | [Comfy-Org/sigclip_vision_384](https://huggingface.co/Comfy-Org/sigclip_vision_384/resolve/main/sigclip_vision_patch14_384.safetensors) |
| `uso-flux1-dit-lora-v1.safetensors` | `loras/uso-flux1-dit-lora-v1.safetensors` | 0.45 | apache-2.0 | [Comfy-Org/USO-1.0](https://huggingface.co/Comfy-Org/USO-1.0/resolve/main/split_files/loras/uso-flux1-dit-lora-v1.safetensors) |
| `uso-flux1-projector-v1.safetensors` | `model_patches/uso-flux1-projector-v1.safetensors` | 0.02 | apache-2.0 | [Comfy-Org/USO-1.0](https://huggingface.co/Comfy-Org/USO-1.0/resolve/main/split_files/model_patches/uso-flux1-projector-v1.safetensors) |
| `vae-ft-mse-840000-ema-pruned.safetensors` | `vae/vae-ft-mse-840000-ema-pruned.safetensors` | 0.31 | mit | [stabilityai/sd-vae-ft-mse-original](https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors) |

19 files, 169.43 GiB with a known size.

### Flux.2

Used by: 9 studio templates; 18 family templates; 65 recipes and pipelines; LoRA recipes `lora_db97e76f65`, `lora_fe78853867`; features `commercials`, `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `flux-2-klein-4b-fp8.safetensors` | `diffusion_models/flux-2-klein-4b-fp8.safetensors` | 3.79 | apache-2.0 | [black-forest-labs/FLUX.2-klein-4b-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8/resolve/main/flux-2-klein-4b-fp8.safetensors) |
| `flux-2-klein-9b-fp8.safetensors` | `diffusion_models/flux-2-klein-9b-fp8.safetensors` | 8.79 | flux-non-commercial-license (non-commercial) | [black-forest-labs/FLUX.2-klein-9b-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-fp8/resolve/main/flux-2-klein-9b-fp8.safetensors) (gated) |
| `flux-2-klein-9b-kv-fp8.safetensors` | `diffusion_models/flux-2-klein-9b-kv-fp8.safetensors` | 9.14 | flux-non-commercial-license (non-commercial) | [black-forest-labs/FLUX.2-klein-9b-kv-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-kv-fp8/resolve/main/flux-2-klein-9b-kv-fp8.safetensors) |
| `flux-2-klein-9b.safetensors` | `diffusion_models/flux-2-klein-9b.safetensors` | 16.91 | flux-non-commercial-license (non-commercial) | [black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B/resolve/main/flux-2-klein-9b.safetensors) (gated) |
| `flux-2-klein-base-4b-fp8.safetensors` | `diffusion_models/flux-2-klein-base-4b-fp8.safetensors` | 3.81 | apache-2.0 | [black-forest-labs/FLUX.2-klein-base-4b-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4b-fp8/resolve/main/flux-2-klein-base-4b-fp8.safetensors) |
| `flux-2-klein-base-9b-fp8.safetensors` | `diffusion_models/flux-2-klein-base-9b-fp8.safetensors` | 8.91 | flux-non-commercial-license (non-commercial) | [black-forest-labs/FLUX.2-klein-base-9b-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9b-fp8/resolve/main/flux-2-klein-base-9b-fp8.safetensors) (gated) |
| `flux2_dev_fp8mixed.safetensors` | `diffusion_models/flux2_dev_fp8mixed.safetensors` | 33.02 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-2-Dev](https://huggingface.co/Comfy-Org/Flux-2-Dev/resolve/main/split_files/diffusion_models/flux2_dev_fp8mixed.safetensors) |
| `Flux2TurboComfyv2.safetensors` | `loras/Flux2TurboComfyv2.safetensors` | 2.57 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-2-Dev](https://huggingface.co/Comfy-Org/Flux-2-Dev/resolve/main/split_files/loras/Flux2TurboComfyv2.safetensors) |
| `Flux_2-Turbo-LoRA_comfyui.safetensors` | `loras/Flux_2-Turbo-LoRA_comfyui.safetensors` | 2.57 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-2-Dev](https://huggingface.co/Comfy-Org/Flux-2-Dev/resolve/main/split_files/loras/Flux_2-Turbo-LoRA_comfyui.safetensors) |
| `full_encoder_small_decoder.safetensors` | `vae/full_encoder_small_decoder.safetensors` | 0.23 | apache-2.0 | [black-forest-labs/FLUX.2-small-decoder](https://huggingface.co/black-forest-labs/FLUX.2-small-decoder/resolve/main/full_encoder_small_decoder.safetensors) |
| `mistral_3_small_flux2_bf16.safetensors` | `text_encoders/mistral_3_small_flux2_bf16.safetensors` | 33.14 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-2-Dev](https://huggingface.co/Comfy-Org/Flux-2-Dev/resolve/main/split_files/text_encoders/mistral_3_small_flux2_bf16.safetensors) |
| `mistral_3_small_flux2_fp8.safetensors` | `text_encoders/mistral_3_small_flux2_fp8.safetensors` | 16.80 | flux-1-dev-non-commercial-license (non-commercial) | [Comfy-Org/Flux-2-Dev](https://huggingface.co/Comfy-Org/Flux-2-Dev/resolve/main/split_files/text_encoders/mistral_3_small_flux2_fp8.safetensors) |
| `qwen_3_8b_fp8mixed.safetensors` | `text_encoders/qwen_3_8b_fp8mixed.safetensors` | 8.07 | flux-non-commercial-license (non-commercial) | [Comfy-Org/Flux-2-Klein-9B](https://huggingface.co/Comfy-Org/Flux-2-Klein-9B/resolve/main/split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors) |
| `KleinBase4B_TryOn.safetensors` | `loras/flux2_klein/civitai2/KleinBase4B_TryOn.safetensors` | 0.04 | see the Civitai page | Civitai only: [Attach Outfit & Try On [Qwen & Klein]](https://civitai.com/models/2367983?modelVersionId=2666625) (matched by SHA-256) |
| `KleinBase9B_TryOn.safetensors` | `loras/flux2_klein/civitai2/KleinBase9B_TryOn.safetensors` | 0.08 | see the Civitai page | Civitai only: [Attach Outfit & Try On [Qwen & Klein]](https://civitai.com/models/2367983?modelVersionId=2666629) (matched by SHA-256) |

15 files, 147.87 GiB with a known size.

### Flux.3-Klein

Used by: goals `flux3`, `product`; workflows `flux3_klein_core_t2i_api`; studio templates `flux3_klein_bf16_t2i`, `flux3_klein_nvfp4_t2i`, `flux3_klein_sd_nvfp4_t2i`; 7 family templates; pipeline graphs `studio/web/pipelines/product_hero/graphs/photo`; features `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `flux3-image-klein-base-int8-convrot.safetensors` | `diffusion_models/flux3-image-klein-base-int8-convrot.safetensors` | 5.41 | flux-kommunity-license | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/resolve/main/diffusion_models/flux3-image-klein-base-int8-convrot.safetensors) (gated) |
| `flux3-image-klein-bf16.safetensors` | `diffusion_models/flux3-image-klein-bf16.safetensors` | 10.34 | flux-kommunity-license | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/resolve/main/diffusion_models/flux3-image-klein-bf16.safetensors) (gated) |
| `flux3-image-klein-int8-convrot.safetensors` | `diffusion_models/flux3-image-klein-int8-convrot.safetensors` | 5.43 | flux-kommunity-license | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/resolve/main/diffusion_models/flux3-image-klein-int8-convrot.safetensors) (gated) |
| `flux3_image_klein_bf16.safetensors` | `diffusion_models/flux3_image_klein_bf16.safetensors` | 10.32 | flux-kommunity-license | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/resolve/main/diffusion_models/flux3-image-klein-base-bf16.safetensors) (gated), published as `flux3-image-klein-base-bf16.safetensors` |
| `flux3_image_klein_nvfp4.safetensors` | `diffusion_models/flux3_image_klein_nvfp4.safetensors` | 4.90 | flux-kommunity-license | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/resolve/main/diffusion_models/flux3-image-klein-base-nvfp4.safetensors) (gated), published as `flux3-image-klein-base-nvfp4.safetensors` |
| `flux3_image_klein_sd_nvfp4.safetensors` | `diffusion_models/flux3_image_klein_sd_nvfp4.safetensors` | 4.92 | flux-kommunity-license | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/resolve/main/diffusion_models/flux3-image-klein-nvfp4.safetensors) (gated), published as `flux3-image-klein-nvfp4.safetensors` |
| `qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors` | `text_encoders/qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors` | 6.26 | flux-kommunity-license | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/resolve/main/text_encoders/qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors) (gated) |
| `qwen3vl_4b_int8_convrot.safetensors` | `text_encoders/qwen3vl_4b_int8_convrot.safetensors` | 4.52 | flux-kommunity-license | [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/resolve/main/text_encoders/qwen3vl_4b_int8_convrot.safetensors) (gated) |

8 files, 52.09 GiB with a known size.

### frame_interpolation

Used by: 4 studio templates; 5 family templates; pipeline graphs `studio/web/pipelines/anime_short/graphs/smooth`, `studio/web/pipelines/anime_short/graphs/smooth2`, `studio/web/pipelines/anime_short/graphs/smooth3`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `film_net_fp16.safetensors` | `frame_interpolation/film_net_fp16.safetensors` | 0.06 | mit-and-apache-2.0 | [Comfy-Org/Frame-Interpolation](https://huggingface.co/Comfy-Org/Frame-Interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors) |
| `rife47.pth` | `frame_interpolation/RIFE/rife47.pth` | 0.06 | mit-and-apache-2.0 | [Comfy-Org/Frame-Interpolation](https://huggingface.co/Comfy-Org/Frame-Interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors), published as `film_net_fp16.safetensors` |
| `rife_v4.25.safetensors` | `frame_interpolation/rife_v4.25.safetensors` | 0.06 | mit-and-apache-2.0 | [Comfy-Org/Frame-Interpolation](https://huggingface.co/Comfy-Org/Frame-Interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors), published as `film_net_fp16.safetensors` |
| `rife_v4.25_heavy.safetensors` | `frame_interpolation/rife_v4.25_heavy.safetensors` | 0.06 | mit-and-apache-2.0 | [Comfy-Org/Frame-Interpolation](https://huggingface.co/Comfy-Org/Frame-Interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors), published as `film_net_fp16.safetensors` |
| `rife_v4.25_lite.safetensors` | `frame_interpolation/rife_v4.25_lite.safetensors` | 0.06 | mit-and-apache-2.0 | [Comfy-Org/Frame-Interpolation](https://huggingface.co/Comfy-Org/Frame-Interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors), published as `film_net_fp16.safetensors` |

5 files, 0.32 GiB with a known size.

### HiDream

Used by: studio templates `hidream_o1_dev_t2i`, `hidream_o1_full_t2i`; 10 family templates; features `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `clip_g_hidream.safetensors` | `text_encoders/clip_g_hidream.safetensors` | 1.29 | mit | [Comfy-Org/HiDream](https://huggingface.co/Comfy-Org/HiDream/resolve/main/split_files/text_encoders/clip_g_hidream.safetensors) |
| `clip_l_hidream.safetensors` | `text_encoders/clip_l_hidream.safetensors` | 0.23 | mit | [Comfy-Org/HiDream](https://huggingface.co/Comfy-Org/HiDream/resolve/main/split_files/text_encoders/clip_l_hidream.safetensors) |
| `gemma4_e4b_it_fp8_scaled.safetensors` | `text_encoders/gemma4_e4b_it_fp8_scaled.safetensors` | 8.44 | apache-2.0 | [Comfy-Org/gemma-4](https://huggingface.co/Comfy-Org/gemma-4/resolve/main/text_encoders/gemma4_e4b_it_fp8_scaled.safetensors) |
| `hidream_e1_1_bf16.safetensors` | `diffusion_models/hidream_e1_1_bf16.safetensors` | 31.86 | mit | [Comfy-Org/HiDream](https://huggingface.co/Comfy-Org/HiDream/resolve/main/split_files/diffusion_models/hidream_e1_1_bf16.safetensors) |
| `hidream_e1_full_bf16.safetensors` | `diffusion_models/hidream_e1_full_bf16.safetensors` | 31.86 | mit | [Comfy-Org/HiDream](https://huggingface.co/Comfy-Org/HiDream/resolve/main/split_files/diffusion_models/hidream_e1_full_bf16.safetensors) |
| `hidream_i1_dev_fp8.safetensors` | `diffusion_models/hidream_i1_dev_fp8.safetensors` | 15.93 | mit | [Comfy-Org/HiDream](https://huggingface.co/Comfy-Org/HiDream/resolve/main/split_files/diffusion_models/hidream_i1_dev_fp8.safetensors) |
| `hidream_i1_fast_fp8.safetensors` | `diffusion_models/hidream_i1_fast_fp8.safetensors` | 15.93 | mit | [Comfy-Org/HiDream](https://huggingface.co/Comfy-Org/HiDream/resolve/main/split_files/diffusion_models/hidream_i1_fast_fp8.safetensors) |
| `hidream_i1_full_fp8.safetensors` | `diffusion_models/hidream_i1_full_fp8.safetensors` | 15.93 | mit | [Comfy-Org/HiDream](https://huggingface.co/Comfy-Org/HiDream/resolve/main/split_files/diffusion_models/hidream_i1_full_fp8.safetensors) |
| `hidream_o1_image_bf16.safetensors` | `checkpoints/hidream_o1_image_bf16.safetensors` | 15.24 | mit | [Comfy-Org/HiDream-O1-Image](https://huggingface.co/Comfy-Org/HiDream-O1-Image/resolve/main/checkpoints/hidream_o1_image_bf16.safetensors) |
| `hidream_o1_image_dev_fp8_scaled.safetensors` | `checkpoints/hidream_o1_image_dev_fp8_scaled.safetensors` | 7.51 | mit | [Comfy-Org/HiDream-O1-Image](https://huggingface.co/Comfy-Org/HiDream-O1-Image/resolve/main/checkpoints/hidream_o1_image_dev_fp8_scaled.safetensors) |
| `llama_3.1_8b_instruct_fp8_scaled.safetensors` | `text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors` | 8.46 | mit | [Comfy-Org/HiDream](https://huggingface.co/Comfy-Org/HiDream/resolve/main/split_files/text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors) |

11 files, 152.69 GiB with a known size.

### Hunyuan3D-2.1

Used by: 4 family templates; University graphs `studio/university/graphs/e_hunyuan3d_surfnet`, `studio/university/graphs/e_mesh_cleanup`, `studio/university/graphs/hunyuan3d_mesh`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `hunyuan3d-dit-v2-mv-turbo_fp16.safetensors` | `checkpoints/hunyuan3d-dit-v2-mv-turbo_fp16.safetensors` | 4.59 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-3D-2.0](https://huggingface.co/Comfy-Org/Hunyuan-3D-2.0/resolve/main/split_files/hunyuan3d-dit-v2-mv-turbo_fp16.safetensors) |
| `hunyuan3d-dit-v2-mv_fp16.safetensors` | `checkpoints/hunyuan3d-dit-v2-mv_fp16.safetensors` | 4.59 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-3D-2.0](https://huggingface.co/Comfy-Org/Hunyuan-3D-2.0/resolve/main/split_files/hunyuan3d-dit-v2-mv_fp16.safetensors) |
| `hunyuan3d-dit-v2_fp16.safetensors` | `checkpoints/hunyuan3d-dit-v2_fp16.safetensors` | 4.59 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-3D-2.0](https://huggingface.co/Comfy-Org/Hunyuan-3D-2.0/resolve/main/split_files/hunyuan3d-dit-v2_fp16.safetensors) |
| `hunyuan_3d_v2.1.safetensors` | `checkpoints/hunyuan_3d_v2.1.safetensors` | 6.86 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-3D-2.1](https://huggingface.co/Comfy-Org/Hunyuan-3D-2.1/resolve/main/hunyuan_3d_v2.1.safetensors) |

4 files, 20.63 GiB with a known size.

### HunyuanDiT-1.2

Used by: studio templates `hunyuan_image_21_t2i`, `hunyuandit_core_t2i`; 4 family templates.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `byt5_small_glyphxl_fp16.safetensors` | `text_encoders/byt5_small_glyphxl_fp16.safetensors` | 0.41 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Video-1.5](https://huggingface.co/Comfy-Org/Hunyuan-Video-1.5/resolve/main/split_files/text_encoders/byt5_small_glyphxl_fp16.safetensors) |
| `hunyuan_dit_1.2.safetensors` | `checkpoints/hunyuan_dit_1.2.safetensors` | 7.67 | not stated on the card | [comfyanonymous/hunyuan_dit_comfyui](https://huggingface.co/comfyanonymous/hunyuan_dit_comfyui/resolve/main/hunyuan_dit_1.2.safetensors) |
| `hunyuan_image_2.1_vae_fp16.safetensors` | `vae/hunyuan_image_2.1_vae_fp16.safetensors` | 0.76 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Image-2.1](https://huggingface.co/Comfy-Org/Hunyuan-Image-2.1/resolve/main/split_files/vae/hunyuan_image_2.1_vae_fp16.safetensors) |
| `hunyuanimage2.1_fp8_e4m3fn.safetensors` | `diffusion_models/hunyuanimage2.1_fp8_e4m3fn.safetensors` | 16.23 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Image-2.1](https://huggingface.co/Comfy-Org/Hunyuan-Image-2.1/resolve/main/split_files/diffusion_models/hunyuanimage2.1_fp8_e4m3fn.safetensors) |

4 files, 25.07 GiB with a known size.

### HunyuanVideo

Used by: 5 family templates.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `hunyuan_video_t2v_720p_bf16.safetensors` | `diffusion_models/hunyuan_video_t2v_720p_bf16.safetensors` | 23.88 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Video](https://huggingface.co/Comfy-Org/Hunyuan-Video/resolve/main/split_files/diffusion_models/hunyuan_video_t2v_720p_bf16.safetensors) |
| `hunyuan_video_vae_bf16.safetensors` | `vae/hunyuan_video_vae_bf16.safetensors` | 0.46 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Video](https://huggingface.co/Comfy-Org/Hunyuan-Video/resolve/main/split_files/vae/hunyuan_video_vae_bf16.safetensors) |
| `hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors` | `diffusion_models/hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors` | 15.52 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Video-1.5](https://huggingface.co/Comfy-Org/Hunyuan-Video-1.5/resolve/main/split_files/diffusion_models/hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors) |
| `hunyuanvideo1.5_720p_i2v_fp16.safetensors` | `diffusion_models/hunyuanvideo1.5_720p_i2v_fp16.safetensors` | 15.51 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Video-1.5](https://huggingface.co/Comfy-Org/Hunyuan-Video-1.5/resolve/main/split_files/diffusion_models/hunyuanvideo1.5_720p_i2v_fp16.safetensors) |
| `hunyuanvideo1.5_720p_t2v_fp16.safetensors` | `diffusion_models/hunyuanvideo1.5_720p_t2v_fp16.safetensors` | 15.51 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Video-1.5](https://huggingface.co/Comfy-Org/Hunyuan-Video-1.5/resolve/main/split_files/diffusion_models/hunyuanvideo1.5_720p_t2v_fp16.safetensors) |
| `hunyuanvideo15_latent_upsampler_1080p.safetensors` | `latent_upscale_models/hunyuanvideo15_latent_upsampler_1080p.safetensors` | 0.19 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Video-1.5](https://huggingface.co/Comfy-Org/Hunyuan-Video-1.5/resolve/main/split_files/latent_upscale_models/hunyuanvideo15_latent_upsampler_1080p.safetensors) |
| `hunyuanvideo15_vae_fp16.safetensors` | `vae/hunyuanvideo15_vae_fp16.safetensors` | 2.35 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Video-1.5](https://huggingface.co/Comfy-Org/Hunyuan-Video-1.5/resolve/main/split_files/vae/hunyuanvideo15_vae_fp16.safetensors) |
| `llava_llama3_fp8_scaled.safetensors` | `text_encoders/llava_llama3_fp8_scaled.safetensors` | 8.47 | tencent-hunyuan-community | [Comfy-Org/Hunyuan-Video](https://huggingface.co/Comfy-Org/Hunyuan-Video/resolve/main/split_files/text_encoders/llava_llama3_fp8_scaled.safetensors) |

8 files, 81.88 GiB with a known size.

### HunyuanWorld

Used by: studio templates `hunyuanworld_pano_t2i`; family templates `hunyuanworld_pano_t2i`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `HunyuanWorld-PanoDiT-Text_lora.safetensors` | `loras/HunyuanWorld-PanoDiT-Text_lora.safetensors` | 0.45 | tencent-hunyuanworld-1.0-community | [tencent/HunyuanWorld-1](https://huggingface.co/tencent/HunyuanWorld-1/resolve/main/HunyuanWorld-PanoDiT-Text/lora.safetensors), published as `lora.safetensors` |

1 files, 0.45 GiB with a known size.

### HY-Motion

Used by: studio templates `hymotion_t2m_preview`; family templates `hymotion_t2m_preview`; other graphs `studio/web/res4lyf_renders/nodes/UltraSharkSampler_Tiled`; features `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `clip-vit-large-patch14.safetensors` | `text_encoders/clip-vit-large-patch14.safetensors` | 1.59 | not stated on the card | [openai/clip-vit-large-patch14](https://huggingface.co/openai/clip-vit-large-patch14/resolve/main/model.safetensors), published as `model.safetensors` |
| `latest.ckpt` | `hymotion/latest.ckpt` | 3.89 | tencent-hunyuan-community | [tencent/HY-Motion-1.0](https://huggingface.co/tencent/HY-Motion-1.0/resolve/main/HY-Motion-1.0/latest.ckpt) |
| `qwen3_8b_bf16_single.safetensors` | `text_encoders/qwen3_8b_bf16_single.safetensors` | ? | unknown | No public source found |

3 files, 5.48 GiB with a known size.

### IC-Light

Used by: studio templates `iclight_fc_relight`; family templates `iclight_fc_relight`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `iclight_sd15_fc_unet_ldm.safetensors` | `diffusion_models/iclight_sd15_fc_unet_ldm.safetensors` | 1.60 | not stated on the card | [fofr/comfyui](https://huggingface.co/fofr/comfyui/resolve/main/unet/iclight_sd15_fc_unet_ldm.safetensors) (community upload) |

1 files, 1.60 GiB with a known size.

### Ideogram4

Used by: studio templates `ideogram4_json_t2i`, `ideogram4_poster_t2i`; 4 family templates.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `ideogram4_fp8_scaled.safetensors` | `diffusion_models/ideogram4_fp8_scaled.safetensors` | 8.64 | ideogram-non-commercial-model-agreement (non-commercial) | [Comfy-Org/Ideogram-4](https://huggingface.co/Comfy-Org/Ideogram-4/resolve/main/diffusion_models/ideogram4_fp8_scaled.safetensors) |
| `ideogram4_int8_convrot.safetensors` | `diffusion_models/ideogram4_int8_convrot.safetensors` | 8.93 | ideogram-non-commercial-model-agreement (non-commercial) | [Comfy-Org/Ideogram-4](https://huggingface.co/Comfy-Org/Ideogram-4/resolve/main/diffusion_models/ideogram4_int8_convrot.safetensors) |
| `ideogram4_unconditional_fp8_scaled.safetensors` | `diffusion_models/ideogram4_unconditional_fp8_scaled.safetensors` | 8.64 | ideogram-non-commercial-model-agreement (non-commercial) | [Comfy-Org/Ideogram-4](https://huggingface.co/Comfy-Org/Ideogram-4/resolve/main/diffusion_models/ideogram4_unconditional_fp8_scaled.safetensors) |
| `ideogram4_unconditional_int8_convrot.safetensors` | `diffusion_models/ideogram4_unconditional_int8_convrot.safetensors` | 8.93 | ideogram-non-commercial-model-agreement (non-commercial) | [Comfy-Org/Ideogram-4](https://huggingface.co/Comfy-Org/Ideogram-4/resolve/main/diffusion_models/ideogram4_unconditional_int8_convrot.safetensors) |

4 files, 35.14 GiB with a known size.

### Iris-3B

Used by: studio templates `iris3b_t2i`; family templates `iris3b_t2i`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `iris-3b.safetensors` | `diffusion_models/iris-3b.safetensors` | 11.13 | apache-2.0 | [speridlabs/iris-3b](https://huggingface.co/speridlabs/iris-3b/resolve/main/model.safetensors), published as `model.safetensors` |

1 files, 11.13 GiB with a known size.

### JoyAI-Video-Edit

Used by: family templates `image_joyai_image_edit`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `joyai_image_edit_int8_convrot.safetensors` | `diffusion_models/joyai_image_edit_int8_convrot.safetensors` | 15.30 | apache-2.0 | [Comfy-Org/JoyAI-Image-Edit](https://huggingface.co/Comfy-Org/JoyAI-Image-Edit/resolve/main/diffusion_models/joyai_image_edit_int8_convrot.safetensors) |
| `qwen3vl_8b_joyimage_edit_int8_convrot.safetensors` | `text_encoders/qwen3vl_8b_joyimage_edit_int8_convrot.safetensors` | 9.37 | apache-2.0 | [Comfy-Org/JoyAI-Image-Edit](https://huggingface.co/Comfy-Org/JoyAI-Image-Edit/resolve/main/text_encoders/qwen3vl_8b_joyimage_edit_int8_convrot.safetensors) |

2 files, 24.68 GiB with a known size.

### Kandinsky-5.0-T2I-Lite

Used by: family templates `image_kandinsky5_t2i`, `video_kandinsky5_i2v`, `video_kandinsky5_t2v`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `kandinsky5lite_i2v_5s.safetensors` | `diffusion_models/kandinsky5lite_i2v_5s.safetensors` | 4.26 | mit | [kandinskylab/Kandinsky-5.0-I2V-Lite-5s](https://huggingface.co/kandinskylab/Kandinsky-5.0-I2V-Lite-5s/resolve/main/model/kandinsky5lite_i2v_5s.safetensors) |
| `kandinsky5lite_t2i.safetensors` | `diffusion_models/kandinsky5lite_t2i.safetensors` | 11.22 | mit | [kandinskylab/Kandinsky-5.0-T2I-Lite](https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite/resolve/main/model/kandinsky5lite_t2i.safetensors) |
| `kandinsky5lite_t2v_sft_5s.safetensors` | `diffusion_models/kandinsky5lite_t2v_sft_5s.safetensors` | 4.26 | mit | [kandinskylab/Kandinsky-5.0-T2V-Lite-sft-5s](https://huggingface.co/kandinskylab/Kandinsky-5.0-T2V-Lite-sft-5s/resolve/main/model/kandinsky5lite_t2v_sft_5s.safetensors) |

3 files, 19.74 GiB with a known size.

### Kolors

Used by: studio templates `kolors_t2i`; family templates `kolors_t2i`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `diffusion_pytorch_model.fp16.safetensors` | `diffusers/diffusion_pytorch_model.fp16.safetensors` | 4.80 | apache-2.0 | [Kwai-Kolors/Kolors](https://huggingface.co/Kwai-Kolors/Kolors/resolve/main/unet/diffusion_pytorch_model.fp16.safetensors) |
| `kolors_vae_fp16.safetensors` | `vae/kolors_vae_fp16.safetensors` | 0.16 | apache-2.0 | [Kwai-Kolors/Kolors](https://huggingface.co/Kwai-Kolors/Kolors/resolve/main/vae/diffusion_pytorch_model.fp16.safetensors), published as `diffusion_pytorch_model.fp16.safetensors` |

2 files, 4.96 GiB with a known size.

### Krea2

Used by: workflows `worldkit_krea2_t2i_api`; 4 studio templates; 8 family templates; pipeline graphs `studio/web/pipelines/concept_to_pack/graphs/a1`, `studio/web/pipelines/concept_to_pack/graphs/a2`, `studio/web/pipelines/concept_to_pack/graphs/a3`; LoRA recipes `lora_4270d6fafd`, `lora_f51f354b69`; features `train_bases`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `krea2_darkbrush.safetensors` | `loras/krea2_darkbrush.safetensors` | 0.44 | krea-2-community-license | [Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2/resolve/main/loras/krea2_darkbrush.safetensors) |
| `krea2_identity_edit_v1_2_r128.safetensors` | `loras/krea2_identity_edit_v1_2_r128.safetensors` | 0.85 | krea-2-identity-edit-v2-license | [conradlocke/krea2-identity-edit](https://huggingface.co/conradlocke/krea2-identity-edit/resolve/main/krea2_identity_edit_v1_2_r128.safetensors) (community upload) |
| `krea2_raw_bf16.safetensors` | `diffusion_models/krea2_raw_bf16.safetensors` | 24.48 | krea-2-community-license | [Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2/resolve/main/diffusion_models/krea2_raw_bf16.safetensors) |
| `krea2_style_reference.safetensors` | `loras/krea2_style_reference.safetensors` | 0.43 | krea-2-community-license | [Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2/resolve/main/loras/krea2_style_reference.safetensors) |
| `krea2_turbo_bf16.safetensors` | `diffusion_models/krea2_turbo_bf16.safetensors` | 24.48 | krea-2-community-license | [Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2/resolve/main/diffusion_models/krea2_turbo_bf16.safetensors) |
| `krea2_turbo_fp8_scaled.safetensors` | `diffusion_models/krea2_turbo_fp8_scaled.safetensors` | 12.24 | krea-2-community-license | [Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2/resolve/main/diffusion_models/krea2_turbo_fp8_scaled.safetensors) |
| `krea2_turbo_int8_convrot.safetensors` | `diffusion_models/krea2_turbo_int8_convrot.safetensors` | 12.57 | krea-2-community-license | [Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2/resolve/main/diffusion_models/krea2_turbo_int8_convrot.safetensors) |
| `qwen3vl_4b_fp8_scaled.safetensors` | `text_encoders/qwen3vl_4b_fp8_scaled.safetensors` | 4.88 | apache-2.0 | [Comfy-Org/Qwen3-VL](https://huggingface.co/Comfy-Org/Qwen3-VL/resolve/main/text_encoders/qwen3vl_4b_fp8_scaled.safetensors) |

8 files, 80.36 GiB with a known size.

### LDM3D-4C

Used by: studio templates `ldm3d_rgbd_t2i`; family templates `ldm3d_rgbd_t2i`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `ldm3d-4c_unet.safetensors` | `diffusion_models/ldm3d-4c_unet.safetensors` | 3.20 | creativeml-openrail-m | [Intel/ldm3d-4c](https://huggingface.co/Intel/ldm3d-4c/resolve/main/unet/diffusion_pytorch_model.safetensors), published as `diffusion_pytorch_model.safetensors` |
| `ldm3d-4c_text_encoder.safetensors` | `text_encoders/ldm3d-4c_text_encoder.safetensors` | ? | unknown | No public source found |
| `ldm3d-4c_vae.safetensors` | `vae/ldm3d-4c_vae.safetensors` | ? | unknown | No public source found |

3 files, 3.20 GiB with a known size.

### LivePortrait

Used by: family templates `motion_liveportrait`; features `feature_motion`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `appearance_feature_extractor.safetensors` | `liveportrait/safetensors/appearance_feature_extractor.safetensors` | 0.00 | not stated on the card | [Kijai/LivePortrait_safetensors](https://huggingface.co/Kijai/LivePortrait_safetensors/resolve/main/appearance_feature_extractor.safetensors) |
| `spade_generator.safetensors` | `liveportrait/spade_generator.safetensors` | 0.21 | not stated on the card | [Kijai/LivePortrait_safetensors](https://huggingface.co/Kijai/LivePortrait_safetensors/resolve/main/spade_generator.safetensors) |

2 files, 0.21 GiB with a known size.

### LongCat-Avatar-15

Used by: 5 studio templates; 10 family templates; LoRA recipes `lora_08967439ec`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `LongCat-Avatar-15_bf16.safetensors` | `diffusion_models/LongCat-Avatar-15_bf16.safetensors` | 29.53 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LongCat/LongCat-Avatar-15_bf16.safetensors) |
| `LongCat-Avatar-15_dmd_distill_lora_rank128_bf16.safetensors` | `loras/LongCat-Avatar-15_dmd_distill_lora_rank128_bf16.safetensors` | 1.17 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LongCat/LongCat-Avatar-15_dmd_distill_lora_rank128_bf16.safetensors) |
| `umt5-xxl-enc-bf16.safetensors` | `text_encoders/umt5-xxl-enc-bf16.safetensors` | 10.58 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors) |
| `Wan2_1_VAE_bf16.safetensors` | `vae/Wan2_1_VAE_bf16.safetensors` | 0.24 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors) |
| `whisper_large_v3_encoder_fp16.safetensors` | `audio_encoders/whisper_large_v3_encoder_fp16.safetensors` | 1.58 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/HuMo/whisper_large_v3_encoder_fp16.safetensors) |

5 files, 43.10 GiB with a known size.

### LongCat-Image

Used by: family templates `image_longcat_image_edit`, `image_longcat_text_to_image`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `longcat_image_bf16.safetensors` | `diffusion_models/longcat_image_bf16.safetensors` | 11.68 | apache-2.0 | [Comfy-Org/LongCat-Image](https://huggingface.co/Comfy-Org/LongCat-Image/resolve/main/split_files/diffusion_models/longcat_image_bf16.safetensors) |
| `longcat_image_edit_bf16.safetensors` | `diffusion_models/longcat_image_edit_bf16.safetensors` | 11.68 | apache-2.0 | [Comfy-Org/LongCat-Image](https://huggingface.co/Comfy-Org/LongCat-Image/resolve/main/split_files/diffusion_models/longcat_image_edit_bf16.safetensors) |

2 files, 23.36 GiB with a known size.

### LTX-2.5

Used by: goals `animate_ltx`, `vfx_ltx`, `video_ltx`; workflows `campath_ltx_track_api`, `dub_ltx_api`, `ltx25_core_i2v_api`, `ltx25_core_t2v_api`, `ltx25_transition_api`, `ltx25_vfx_api`, `ltx25_vfx_clean_plate`, `ltx25_vfx_day_to_night` ...; studio templates `ltx25_core_i2v`, `ltx25_core_t2v`, `ltxv13b_098_distilled_t2v`; 27 family templates; pipeline graphs `studio/web/pipelines/world_flood/graphs/flood`; University graphs `studio/university/graphs/d_depth_moge`, `studio/university/graphs/wf_ltx25_t2v`; 9 LoRA recipes; features `feature_dub`, `feature_finish`, `feature_oneclick`, `goals`, `train_bases`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors` | `loras/gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors` | 0.59 | ltx-2-community-license-agreement | [Comfy-Org/ltx-2](https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/loras/gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors) |
| `gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors` | `text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors` | 14.32 | ltx-2.x-community-license-agreement | [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors) (gated) |
| `gemma4_e2b_it_int8_convrot.safetensors` | `text_encoders/gemma4_e2b_it_int8_convrot.safetensors` | 4.84 | apache-2.0 | [Comfy-Org/gemma-4](https://huggingface.co/Comfy-Org/gemma-4/resolve/main/text_encoders/gemma4_e2b_it_int8_convrot.safetensors) |
| `gemma_3_12B_it.safetensors` | `text_encoders/gemma_3_12B_it.safetensors` | 22.71 | ltx-2-community-license-agreement | [Comfy-Org/ltx-2](https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it.safetensors) |
| `gemma_3_12B_it_fp4_mixed.safetensors` | `text_encoders/gemma_3_12B_it_fp4_mixed.safetensors` | 8.80 | ltx-2-community-license-agreement | [Comfy-Org/ltx-2](https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors) |
| `ltx-2-19b-dev-fp8.safetensors` | `checkpoints/ltx-2-19b-dev-fp8.safetensors` | 25.22 | ltx-2-community-license-agreement | [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2/resolve/main/ltx-2-19b-dev-fp8.safetensors) |
| `ltx-2-19b-dev.safetensors` | `checkpoints/ltx-2-19b-dev.safetensors` | 40.31 | ltx-2-community-license-agreement | [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2/resolve/main/ltx-2-19b-dev.safetensors) |
| `ltx-2-19b-distilled-lora-384.safetensors` | `loras/ltx-2-19b-distilled-lora-384.safetensors` | 7.15 | ltx-2-community-license-agreement | [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2/resolve/main/ltx-2-19b-distilled-lora-384.safetensors) |
| `ltx-2-19b-distilled.safetensors` | `checkpoints/ltx-2-19b-distilled.safetensors` | 40.31 | ltx-2-community-license-agreement | [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2/resolve/main/ltx-2-19b-distilled.safetensors) |
| `ltx-2-19b-ic-lora-canny-control.safetensors` | `loras/ltx-2-19b-ic-lora-canny-control.safetensors` | 0.61 | ltx-2-community-license | [Lightricks/LTX-2-19b-IC-LoRA-Canny-Control](https://huggingface.co/Lightricks/LTX-2-19b-IC-LoRA-Canny-Control/resolve/main/ltx-2-19b-ic-lora-canny-control.safetensors) |
| `ltx-2-19b-ic-lora-depth-control.safetensors` | `loras/ltx-2-19b-ic-lora-depth-control.safetensors` | 0.61 | ltx-2-community-license | [Lightricks/LTX-2-19b-IC-LoRA-Depth-Control](https://huggingface.co/Lightricks/LTX-2-19b-IC-LoRA-Depth-Control/resolve/main/ltx-2-19b-ic-lora-depth-control.safetensors) |
| `ltx-2-19b-lora-camera-control-dolly-left.safetensors` | `loras/ltx-2-19b-lora-camera-control-dolly-left.safetensors` | 0.30 | ltx-2-community-license | [Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Left](https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Left/resolve/main/ltx-2-19b-lora-camera-control-dolly-left.safetensors) |
| `ltx-2-spatial-upscaler-x2-1.0.safetensors` | `latent_upscale_models/ltx-2-spatial-upscaler-x2-1.0.safetensors` | 0.93 | ltx-2-community-license-agreement | [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2/resolve/main/ltx-2-spatial-upscaler-x2-1.0.safetensors) |
| `ltx-2.3-22b-dev-fp8.safetensors` | `checkpoints/ltx-2.3-22b-dev-fp8.safetensors` | 27.14 | ltx-2-community-license-agreement | [Lightricks/LTX-2.3-fp8](https://huggingface.co/Lightricks/LTX-2.3-fp8/resolve/main/ltx-2.3-22b-dev-fp8.safetensors) |
| `ltx-2.3-22b-distilled-fp8.safetensors` | `checkpoints/ltx-2.3-22b-distilled-fp8.safetensors` | 27.50 | ltx-2-community-license-agreement | [Lightricks/LTX-2.3-fp8](https://huggingface.co/Lightricks/LTX-2.3-fp8/resolve/main/ltx-2.3-22b-distilled-fp8.safetensors) |
| `ltx-2.3-22b-ic-lora-dubit-0.9.safetensors` | `loras/ltx-2.3-22b-ic-lora-dubit-0.9.safetensors` | 2.30 | ltx-2-community-license | [Lightricks/LTX-2.3-22b-IC-LoRA-DubIt](https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-DubIt/resolve/main/ltx-2.3-22b-ic-lora-dubit-0.9.safetensors) (gated) |
| `ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors` | `loras/ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors` | 1.22 | ltx-2-community-license | [Comfy-Org/ltx-2.3](https://huggingface.co/Comfy-Org/ltx-2.3/resolve/main/split_files/loras/ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors) |
| `ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors` | `loras/ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors` | 0.30 | ltx-2-community-license | [Lightricks/LTX-2.3-22b-IC-LoRA-Motion-Track-Control](https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Motion-Track-Control/resolve/main/ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors) |
| `ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors` | `loras/ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors` | 0.61 | ltx-2-community-license | [Lightricks/LTX-2.3-22b-IC-LoRA-Union-Control](https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Union-Control/resolve/main/ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors) |
| `ltx-2.3-id-lora-talkvid-3k.safetensors` | `loras/ltx-2.3-id-lora-talkvid-3k.safetensors` | 1.08 | ltx-2-community-license | [Comfy-Org/ltx-2.3](https://huggingface.co/Comfy-Org/ltx-2.3/resolve/main/split_files/loras/ltx-2.3-id-lora-talkvid-3k.safetensors) |
| `ltx-2.3-spatial-upscaler-x2-1.1.safetensors` | `latent_upscale_models/ltx-2.3-spatial-upscaler-x2-1.1.safetensors` | 0.93 | ltx-2-community-license-agreement | [Lightricks/LTX-2.3](https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-spatial-upscaler-x2-1.1.safetensors) |
| `ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors` | `diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors` | 20.03 | ltx-2.x-community-license-agreement | [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-alpha-gen-0.9.safetensors` | `loras/ltx-2.5-22b-ic-lora-alpha-gen-0.9.safetensors` | 1.22 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-Alpha-Gen](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Alpha-Gen/resolve/main/ltx-2.5-22b-ic-lora-alpha-gen-0.9.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-clean-plate-1.0.safetensors` | `loras/ltx-2.5-22b-ic-lora-clean-plate-1.0.safetensors` | 0.30 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-Clean-Plate](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Clean-Plate/resolve/main/ltx-2.5-22b-ic-lora-clean-plate-1.0.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-colorization-0.9.safetensors` | `loras/ltx-2.5-22b-ic-lora-colorization-0.9.safetensors` | 0.84 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-Colorization](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Colorization/resolve/main/ltx-2.5-22b-ic-lora-colorization-0.9.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-day-to-night-0.9.safetensors` | `loras/ltx-2.5-22b-ic-lora-day-to-night-0.9.safetensors` | 0.30 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-Day-To-Night](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Day-To-Night/resolve/main/ltx-2.5-22b-ic-lora-day-to-night-0.9.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-deblur-0.9.safetensors` | `loras/ltx-2.5-22b-ic-lora-deblur-0.9.safetensors` | 0.84 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-Deblur](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Deblur/resolve/main/ltx-2.5-22b-ic-lora-deblur-0.9.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-decompression-0.9.safetensors` | `loras/ltx-2.5-22b-ic-lora-decompression-0.9.safetensors` | 0.84 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-Decompression](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Decompression/resolve/main/ltx-2.5-22b-ic-lora-decompression-0.9.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors` | `loras/ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors` | 1.22 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render/resolve/main/ltx-2.5-22b-ic-lora-layout-to-render-1.0.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-pixel-spatial-upscaler-x2-1.0.safetensors` | `loras/ltx-2.5-22b-ic-lora-pixel-spatial-upscaler-x2-1.0.safetensors` | 0.30 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler/resolve/main/ltx-2.5-22b-ic-lora-pixel-spatial-upscaler-x2-1.0.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-restore-1.0.safetensors` | `loras/ltx-2.5-22b-ic-lora-restore-1.0.safetensors` | 1.59 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-Restore](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Restore/resolve/main/ltx-2.5-22b-ic-lora-restore-1.0.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-sdr-to-hdr-1.0.safetensors` | `loras/ltx-2.5-22b-ic-lora-sdr-to-hdr-1.0.safetensors` | 1.22 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-SDR-To-HDR](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-SDR-To-HDR/resolve/main/ltx-2.5-22b-ic-lora-sdr-to-hdr-1.0.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-sdr-to-hdr-scene-emb.safetensors` | `loras/ltx-2.5-22b-ic-lora-sdr-to-hdr-scene-emb.safetensors` | 0.01 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-SDR-To-HDR](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-SDR-To-HDR/resolve/main/ltx-2.5-22b-ic-lora-sdr-to-hdr-scene-emb.safetensors) (gated) |
| `ltx-2.5-22b-ic-lora-water-simulation-0.9.safetensors` | `loras/ltx-2.5-22b-ic-lora-water-simulation-0.9.safetensors` | 0.84 | ltx-2.x-community-license | [Lightricks/LTX-2.5-22b-IC-LoRA-Water-Simulation](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Water-Simulation/resolve/main/ltx-2.5-22b-ic-lora-water-simulation-0.9.safetensors) (gated) |
| `ltx-2.5-audio-vae-bf16.safetensors` | `vae/ltx-2.5-audio-vae-bf16.safetensors` | 0.34 | ltx-2.x-community-license-agreement | [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/vae/ltx-2.5-audio-vae-bf16.safetensors) (gated) |
| `ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors` | `latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors` | 0.93 | ltx-2.x-community-license-agreement | [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors) (gated) |
| `ltx-2.5-video-vae-bf16.safetensors` | `vae/ltx-2.5-video-vae-bf16.safetensors` | 1.37 | ltx-2.x-community-license-agreement | [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/vae/ltx-2.5-video-vae-bf16.safetensors) (gated) |
| `ltx-2.5-video-vae-conv-bf16.safetensors` | `vae/ltx-2.5-video-vae-conv-bf16.safetensors` | 1.35 | ltx-2.x-community-license-agreement | [Lightricks/LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5/resolve/main/vae/ltx-2.5-video-vae-conv-bf16.safetensors) (gated) |
| `ltx-video-2b-v0.9.5.safetensors` | `checkpoints/ltx-video-2b-v0.9.5.safetensors` | 5.91 | other | [Lightricks/LTX-Video](https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b-v0.9.5.safetensors) |
| `ltx-video-2b-v0.9.safetensors` | `checkpoints/ltx-video-2b-v0.9.safetensors` | 8.73 | other | [Lightricks/LTX-Video](https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b-v0.9.safetensors) |
| `ltx2-squish.safetensors` | `loras/ltx2-squish.safetensors` | 0.40 | ltx-2-community-license-agreement | [Comfy-Org/ltx-2](https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/loras/ltx2-squish.safetensors) |
| `ltx2.3-transition.safetensors` | `loras/ltx2.3-transition.safetensors` | 0.36 | apache-2.0 | [joyfox/LTX-2.3-Transition-LORA](https://huggingface.co/joyfox/LTX-2.3-Transition-LORA/resolve/main/ltx2.3-transition.safetensors) (community upload) |
| `ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors` | `loras/ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors` | 2.55 | ltx-2-community-license | [Comfy-Org/ltx-2.3](https://huggingface.co/Comfy-Org/ltx-2.3/resolve/main/split_files/loras/ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors) |
| `ltxv-13b-0.9.8-distilled-fp8.safetensors` | `checkpoints/ltxv-13b-0.9.8-distilled-fp8.safetensors` | 14.62 | other | [Lightricks/LTX-Video](https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltxv-13b-0.9.8-distilled-fp8.safetensors) |
| `moge_2_vitl_normal_fp16.safetensors` | `geometry_estimation/moge_2_vitl_normal_fp16.safetensors` | 0.62 | mit | [Comfy-Org/MoGe](https://huggingface.co/Comfy-Org/MoGe/resolve/main/geometry_estimation/moge_2_vitl_normal_fp16.safetensors) |

45 files, 294.53 GiB with a known size.

### Lumina-2

Used by: studio templates `lumina2_core_t2i`, `lumina2_gemma2_fp16_t2i`, `newbie_exp01_t2i`; 5 family templates; features `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `gemma2-2b-fp16.safetensors` | `text_encoders/gemma2-2b-fp16.safetensors` | 4.87 | apache-2.0 | [Comfy-Org/Lumina-Image-2](https://huggingface.co/Comfy-Org/Lumina-Image-2/resolve/main/split_files/text_encoders/gemma_2_2b_fp16.safetensors), published as `gemma_2_2b_fp16.safetensors` |
| `gemma_2_2b_it_elm_bf16.safetensors` | `text_encoders/gemma_2_2b_it_elm_bf16.safetensors` | 4.87 | nsclv1 | [Comfy-Org/PixelDiT](https://huggingface.co/Comfy-Org/PixelDiT/resolve/main/text_encoders/gemma_2_2b_it_elm_bf16.safetensors) |
| `gemma_3_4b_it_bf16.safetensors` | `text_encoders/gemma_3_4b_it_bf16.safetensors` | 7.23 | newbie-nc-1.0 (non-commercial) | [Comfy-Org/NewBie-Image-Exp0.1](https://huggingface.co/Comfy-Org/NewBie-Image-Exp0.1/resolve/main/split_files/text_encoders/gemma_3_4b_it_bf16.safetensors) |
| `jina_clip_v2_bf16.safetensors` | `text_encoders/jina_clip_v2_bf16.safetensors` | 1.04 | newbie-nc-1.0 (non-commercial) | [Comfy-Org/NewBie-Image-Exp0.1](https://huggingface.co/Comfy-Org/NewBie-Image-Exp0.1/resolve/main/split_files/text_encoders/jina_clip_v2_bf16.safetensors) |
| `lumina_2_model_bf16.safetensors` | `diffusion_models/lumina_2_model_bf16.safetensors` | 4.86 | apache-2.0 | [Comfy-Org/Lumina-Image-2](https://huggingface.co/Comfy-Org/Lumina-Image-2/resolve/main/split_files/diffusion_models/lumina_2_model_bf16.safetensors) |
| `NetaYumev35_pretrained_all_in_one.safetensors` | `checkpoints/NetaYumev35_pretrained_all_in_one.safetensors` | 9.89 | apache-2.0 | [duongve/NetaYume-Lumina-Image-2.0](https://huggingface.co/duongve/NetaYume-Lumina-Image-2.0/resolve/main/NetaYumev35_pretrained_all_in_one.safetensors) (community upload) |
| `NewBie-Image-Exp0.1-bf16.safetensors` | `diffusion_models/NewBie-Image-Exp0.1-bf16.safetensors` | 6.49 | newbie-nc-1.0 (non-commercial) | [Comfy-Org/NewBie-Image-Exp0.1](https://huggingface.co/Comfy-Org/NewBie-Image-Exp0.1/resolve/main/split_files/diffusion_models/NewBie-Image-Exp0.1-bf16.safetensors) |

7 files, 39.27 GiB with a known size.

### Matrix-3D

Used by: goals `animate`, `video`; workflows `wan22_5b_i2v_api`, `wan22_5b_t2v_api`; family templates `video_wan2_2_5B_fun_control`, `video_wan2_2_5B_fun_inpaint`, `video_wan2_2_5B_ti2v`; pipeline graphs `studio/web/pipelines/anime_short/graphs/move`, `studio/web/pipelines/anime_short/graphs/move2`, `studio/web/pipelines/anime_short/graphs/move3`; University graphs `studio/university/graphs/wf_wan22_t2v`; other graphs `studio/web/res4lyf_renders/graphs/wan_res_2m`, `studio/web/res4lyf_renders/nodes/Frames_Latent_ReverseOrder`, `studio/web/res4lyf_renders/nodes/Frames_Slice_Latent`; features `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `wan2.2_ti2v_5B_fp16.safetensors` | `diffusion_models/wan2.2_ti2v_5B_fp16.safetensors` | 9.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors) |
| `wan2.2_vae.safetensors` | `vae/wan2.2_vae.safetensors` | 1.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/vae/wan2.2_vae.safetensors) |

2 files, 10.63 GiB with a known size.

### Ming-Image

Used by: family templates `image_ming_image_01_design_image_edit`, `image_ming_image_01_design_t2i`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `ming_image_0.1_design_int8_convrot.safetensors` | `diffusion_models/ming_image_0.1_design_int8_convrot.safetensors` | 5.75 | mit | [Comfy-Org/Ming-Image](https://huggingface.co/Comfy-Org/Ming-Image/resolve/main/diffusion_models/ming_image_0.1_design_int8_convrot.safetensors) |
| `ming_image_0.1_ling_mini_2.0_int8_convrot.safetensors` | `text_encoders/ming_image_0.1_ling_mini_2.0_int8_convrot.safetensors` | 18.17 | mit | [Comfy-Org/Ming-Image](https://huggingface.co/Comfy-Org/Ming-Image/resolve/main/text_encoders/ming_image_0.1_ling_mini_2.0_int8_convrot.safetensors) |
| `ming_image_vae_bf16.safetensors` | `vae/ming_image_vae_bf16.safetensors` | 0.24 | mit | [Comfy-Org/Ming-Image](https://huggingface.co/Comfy-Org/Ming-Image/resolve/main/vae/ming_image_vae_bf16.safetensors) |
| `qwen3.8_27b_w4a8.safetensors` | `text_encoders/qwen3.8_27b_w4a8.safetensors` | 16.10 | apache-2.0 | [Comfy-Org/Qwen3.8-27B](https://huggingface.co/Comfy-Org/Qwen3.8-27B/resolve/main/text_encoders/qwen3.8_27b_w4a8.safetensors) |

4 files, 40.25 GiB with a known size.

### Mini-Max-Music3

Used by: goals `music`; workflows `music3_api`, `music_music3_kit_api`; studio templates `music3_dav_full`, `music3_turbo8`; family templates `audio_minimax_music_3`, `music3_dav_full`, `music3_turbo8`; 4 pipeline graphs; University graphs `studio/university/graphs/wf_music3`; Music page `music3`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `minimax_music3_dav.safetensors` | `vae/minimax_music3_dav.safetensors` | 0.20 | apache-2.0 | [Comfy-Org/MiniMax-Music-3](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/main/vae/minimax_music3_dav.safetensors) |
| `minimax_music3_dav_full.safetensors` | `vae/minimax_music3_dav_full.safetensors` | 0.20 | apache-2.0 | [Comfy-Org/MiniMax-Music-3](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/main/vae/minimax_music3_dav.safetensors), published as `minimax_music3_dav.safetensors` |
| `minimax_music3_dit_fp16.safetensors` | `diffusion_models/minimax_music3_dit_fp16.safetensors` | 4.58 | apache-2.0 | [Comfy-Org/MiniMax-Music-3](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/main/diffusion_models/minimax_music3_dit_fp16.safetensors) |
| `minimax_music3_text_encoder_pruned_bf16.safetensors` | `text_encoders/minimax_music3_text_encoder_pruned_bf16.safetensors` | 15.56 | apache-2.0 | [Comfy-Org/MiniMax-Music-3](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/main/text_encoders/minimax_music3_text_encoder_pruned_bf16.safetensors) |
| `minimax_music3_text_encoder_pruned_int8_convrot.safetensors` | `text_encoders/minimax_music3_text_encoder_pruned_int8_convrot.safetensors` | 8.57 | apache-2.0 | [Comfy-Org/MiniMax-Music-3](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/main/text_encoders/minimax_music3_text_encoder_pruned_int8_convrot.safetensors) |
| `minimax_music3_turbo_lora_8step.safetensors` | `loras/minimax_music3_turbo_lora_8step.safetensors` | 0.18 | apache-2.0 | [guillaume127/MiniMax-Music-3-Turbo-FP8](https://huggingface.co/guillaume127/MiniMax-Music-3-Turbo-FP8/resolve/main/minimax_music3_turbo_lora_8step.safetensors) (community upload) |

6 files, 29.28 GiB with a known size.

### MiniMax-H3

Used by: goals `director`, `director_keyframes`, `h3_animate`, `h3_video`, `orbit360`, `recast`, `reshoot`; workflows `h3_fl2v_api`, `h3_i2v_api`, `h3_orbit360_api`, `h3_recast_api`, `h3_reshoot_api`, `h3_song_lock_api`, `h3_t2v_api`, `vset_h3_motion_api` ...; 11 family templates; 32 recipes and pipelines; 8 pipeline graphs; University graphs `studio/university/graphs/wf_h3_t2v`; 75 LoRA recipes; features `recipes_family`, `train_bases`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `16bit-pixel.safetensors` | `loras/minimax_h3/style/16bit-pixel.safetensors` | 0.12 | minimax-h3-community-license | [KennethFal/16bit-pixel-lora-minimax-h3](https://huggingface.co/KennethFal/16bit-pixel-lora-minimax-h3/resolve/main/16bit-pixel.safetensors) (community upload) |
| `animatediff_style_h3.safetensors` | `loras/minimax_h3/style/animatediff_style_h3.safetensors` | 0.14 | not stated on the card | [Charlietooth/Animatediff_style_Minimax_H3](https://huggingface.co/Charlietooth/Animatediff_style_Minimax_H3/resolve/main/animatediff_style_h3.safetensors) (community upload) |
| `camera_motion_h3_lora_v1_3000_pruned.safetensors` | `loras/minimax_h3/civitai2/camera_motion_h3_lora_v1_3000_pruned.safetensors` | 0.14 | apache-2.0 | [Jojocodex/minimax-h3-Camera-Motion-lora](https://huggingface.co/Jojocodex/minimax-h3-Camera-Motion-lora/resolve/main/camera_motion_h3_lora_v1_3000_pruned.safetensors) (community upload) |
| `dmad_minimax_h3_4step_full_critic_comfyui.safetensors` | `loras/minimax_h3/dmad/minimax_h3/dmad_minimax_h3_4step_full_critic_comfyui.safetensors` | 1.82 | minimax-h3-community-license-agreement | [ZhengmingYu/DMAD](https://huggingface.co/ZhengmingYu/DMAD/resolve/main/minimax_h3/dmad_minimax_h3_4step_full_critic_comfyui.safetensors) (community upload) |
| `fasth3_omniref_8step_pruned_int8_convrot.safetensors` | `diffusion_models/fasth3_omniref_8step_pruned_int8_convrot.safetensors` | 20.69 | minimax-h3-community-license-agreement | [FastVideo/FastH3-Omni-Comfy](https://huggingface.co/FastVideo/FastH3-Omni-Comfy/resolve/main/diffusion_models/fasth3_omniref_8step_pruned_int8_convrot.safetensors) (community upload) |
| `fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors` | `diffusion_models/fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors` | 20.61 | minimax-h3-community-license-agreement | [FastVideo/FastVideo-FastH3-Comfy](https://huggingface.co/FastVideo/FastVideo-FastH3-Comfy/resolve/main/diffusion_models/fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors) (community upload) |
| `fpv_headbob_h3_50.safetensors` | `loras/minimax_h3/civitai/fpv_headbob_h3_50.safetensors` | 0.07 | minimax-h3-community-license-agreement | [neph1/minimax_h3_headmounted_fpv_cam](https://huggingface.co/neph1/minimax_h3_headmounted_fpv_cam/resolve/main/fpv_headbob_h3_50.safetensors) (community upload) |
| `H3-Person-Remover-V1.safetensors` | `loras/minimax_h3/H3-Person-Remover-V1.safetensors` | 0.14 | minimax-h3-community-license-agreement | [akatz-ai/MiniMax-H3-Person-Remover-LoRA](https://huggingface.co/akatz-ai/MiniMax-H3-Person-Remover-LoRA/resolve/main/H3-Person-Remover-V1.safetensors) |
| `h3-realism-people-t2v-i2v-r2v.safetensors` | `loras/MiniMax-H3-Realism-People-LoRA/h3-realism-people-t2v-i2v-r2v.safetensors` | 0.12 | minimax-h3-community-license | [fal/MiniMax-H3-Realism-People-LoRA](https://huggingface.co/fal/MiniMax-H3-Realism-People-LoRA/resolve/main/h3-realism-people-t2v-i2v-r2v.safetensors) (community upload) |
| `h3_character_swap_pro4500_1000.safetensors` | `loras/h3_character_swap_pro4500_1000.safetensors` | 0.14 | minimax-h3-community-license-agreement | [akatz-ai/MiniMax-H3-Character-Swap-LoRA](https://huggingface.co/akatz-ai/MiniMax-H3-Character-Swap-LoRA/resolve/main/h3_character_swap_pro4500_1000.safetensors) |
| `H3_Combat_V2.safetensors` | `loras/minimax_h3/civitai_wide/H3_Combat_V2.safetensors` | 0.14 | minimax-h3-community-license | [JOKER141/MiniMax-H3-Combat-Base-V2](https://huggingface.co/JOKER141/MiniMax-H3-Combat-Base-V2/resolve/main/H3_Combat_V2.safetensors) (community upload) |
| `H3_Fight_Flow_V1.safetensors` | `loras/minimax_h3/civitai_wide/H3_Fight_Flow_V1.safetensors` | 0.14 | minimax-h3-community-license | [JOKER141/H3-Fight-Flow-Fight-Interaction-LoRA](https://huggingface.co/JOKER141/H3-Fight-Flow-Fight-Interaction-LoRA/resolve/main/H3_Fight_Flow_V1.safetensors) (community upload) |
| `h3_hero_step12000.safetensors` | `loras/minimax_h3/alvdansen_keyframe/h3_hero_step12000.safetensors` | 1.75 | h3-keyframe-animation-adapter-license-1.0.0 | [alvdansen/h3-keyframe-animation](https://huggingface.co/alvdansen/h3-keyframe-animation/resolve/main/adapters/h3_hero_step12000.safetensors) (gated) (community upload) |
| `H3_Ref2V_Anime_Slider_v1.safetensors` | `loras/minimax_h3/civitai_sfw/H3_Ref2V_Anime_Slider_v1.safetensors` | 0.07 | not stated on the card | [adf99/H3_Ref2V_Anime_Slider_v1](https://huggingface.co/adf99/H3_Ref2V_Anime_Slider_v1/resolve/main/H3_Ref2V_Anime_Slider_v1.safetensors) (community upload) |
| `h3_seq_step12000.safetensors` | `loras/minimax_h3/alvdansen_keyframe/h3_seq_step12000.safetensors` | 1.75 | h3-keyframe-animation-adapter-license-1.0.0 | [alvdansen/h3-keyframe-animation](https://huggingface.co/alvdansen/h3-keyframe-animation/resolve/main/adapters/h3_seq_step12000.safetensors) (gated) (community upload) |
| `h3_tween_step12000.safetensors` | `loras/minimax_h3/alvdansen_keyframe/h3_tween_step12000.safetensors` | 1.75 | h3-keyframe-animation-adapter-license-1.0.0 | [alvdansen/h3-keyframe-animation](https://huggingface.co/alvdansen/h3-keyframe-animation/resolve/main/adapters/h3_tween_step12000.safetensors) (gated) (community upload) |
| `handheld_h3_100.safetensors` | `loras/minimax_h3/civitai/handheld_h3_100.safetensors` | 0.07 | minimax-h3-community-license-agreement | [neph1/minimax_h3_handheld_shaky_camera](https://huggingface.co/neph1/minimax_h3_handheld_shaky_camera/resolve/main/handheld_h3_100.safetensors) (community upload) |
| `mh3-lys.safetensors` | `loras/minimax_h3/style/mh3-lys.safetensors` | 0.56 | minimax-h3-community-license-agreement | [kabachuha/mh3-morphing-helper](https://huggingface.co/kabachuha/mh3-morphing-helper/resolve/main/mh3-lys.safetensors) (community upload) |
| `MiniMax-H3_Ref2VA-LoRA-CrossView-Warp_v1_3500.safetensors` | `loras/minimax_h3/style/MiniMax-H3_Ref2VA-LoRA-CrossView-Warp_v1_3500.safetensors` | 0.56 | minimax-h3-community-license | [Cseti/MiniMax-H3_Ref2VA-LoRA-CrossView-Warp_v1](https://huggingface.co/Cseti/MiniMax-H3_Ref2VA-LoRA-CrossView-Warp_v1/resolve/main/MiniMax-H3_Ref2VA-LoRA-CrossView-Warp_v1_3500.safetensors) (community upload) |
| `minimax_h3_audio_vae_fp32.safetensors` | `vae/minimax_h3_audio_vae_fp32.safetensors` | 0.56 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_audio_vae_fp32.safetensors) |
| `minimax_h3_five_view_512_s1500.safetensors` | `loras/minimax_h3/style/minimax_h3_five_view_512_s1500.safetensors` | 0.06 | not stated on the card | [RunningHubAI/rh-minimax-h3-five-view-512-s1500.safetensors-lora](https://huggingface.co/RunningHubAI/rh-minimax-h3-five-view-512-s1500.safetensors-lora/resolve/main/minimax_h3_five_view_512_s1500.safetensors) (community upload) |
| `minimax_h3_fl2v_turbo_4step_v0.1_768p_sla_comfyui_bf16.safetensors` | `loras/minimax_h3/minimax_h3_fl2v_turbo_4step_v0.1_768p_sla_comfyui_bf16.safetensors` | 1.82 | apache-2.0 | [lightx2v/Minimax-h3-Turbo-SLA](https://huggingface.co/lightx2v/Minimax-h3-Turbo-SLA/resolve/main/minimax_h3_fl2v_turbo_4step_v0.1_768p_sla_comfyui_bf16.safetensors) |
| `minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors` | `loras/minimax_h3/minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors` | 1.82 | not stated on the card | [lightx2v/Minimax-h3-Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/main/minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors) |
| `minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors` | `loras/minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors` | 1.82 | not stated on the card | [lightx2v/Minimax-h3-Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/main/minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors) |
| `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | `loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | 1.82 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors) |
| `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | `diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors` | 19.53 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors) |
| `minimax_h3_flf2v_lora_v1.safetensors` | `loras/minimax_h3_flf2v_lora_v1.safetensors` | 0.14 | minimax-h3-community-license-agreement | [pablodawson/MiniMax-H3-360-Orbit-LoRA](https://huggingface.co/pablodawson/MiniMax-H3-360-Orbit-LoRA/resolve/main/minimax_h3_flf2v_lora_v1.safetensors) |
| `minimax_h3_fun_controlnet_union_2.0_pruned_bf16.safetensors` | `controlnet/minimax_h3_fun_controlnet_union_2.0_pruned_bf16.safetensors` | 7.81 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/model_patches/minimax_h3_fun_controlnet_union_2.0_pruned_bf16.safetensors) |
| `minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors` | `model_patches/minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors` | 2.14 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/model_patches/minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors) |
| `minimax_h3_hyperflow_8step_v1.0.safetensors` | `loras/minimax_h3/hyperflow/minimax_h3_hyperflow_8step_v1.0.safetensors` | 2.60 | minimax-h3-community-license-agreement | [VideoRebirthAI/hyperflow](https://huggingface.co/VideoRebirthAI/hyperflow/resolve/main/minimax_h3_hyperflow_8step_v1.0.safetensors) (community upload) |
| `minimax_h3_hyperflow_8step_v1.0_comfyui_pruned_bf16_resized_avg_rank_20_bf16.safetensors` | `loras/minimax_h3/minimax_h3_hyperflow_8step_v1.0_comfyui_pruned_bf16_resized_avg_rank_20_bf16.safetensors` | 0.29 | apache-2.0 | [drbaph/MiniMax-H3-Turbo-Lora-ComfyUI](https://huggingface.co/drbaph/MiniMax-H3-Turbo-Lora-ComfyUI/resolve/main/minimax_h3_hyperflow_8step_v1.0_comfyui_pruned_bf16_resized_avg_rank_20_bf16.safetensors) |
| `minimax_h3_image_training_adapter.safetensors` | `?` | 0.58 | minimax-h3-community-license-agreement | [circlestone-labs/MiniMax-H3-Image-Training-Adapter](https://huggingface.co/circlestone-labs/MiniMax-H3-Image-Training-Adapter/resolve/main/minimax_h3_image_training_adapter.safetensors) |
| `minimax_h3_lms_v1.0_r64.safetensors` | `loras/minimax_h3/alissonerdx_v2v/loras/minimax_h3_lms_v1.0_r64.safetensors` | 1.15 | mixed-asset-licenses | [Alissonerdx/Minimax-H3-ComfyUI](https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI/resolve/main/loras/minimax_h3_lms_v1.0_r64.safetensors) (community upload) |
| `minimax_h3_orb360_step1500.safetensors` | `loras/minimax_h3/civitai_wide/minimax_h3_orb360_step1500.safetensors` | 0.56 | minimax-h3-community-license-agreement | [MATLOWAI/MiniMax-H3-ORB360-CardSpin](https://huggingface.co/MATLOWAI/MiniMax-H3-ORB360-CardSpin/resolve/main/minimax_h3_orb360_step1500.safetensors) (community upload) |
| `MiniMax_H3_Paint-on-glass_rank16_step1500.safetensors` | `loras/minimax_h3/style/MiniMax_H3_Paint-on-glass_rank16_step1500.safetensors` | 0.06 | not stated on the card | [talos414/Paint-on-glass-LoRA](https://huggingface.co/talos414/Paint-on-glass-LoRA/resolve/main/weights/MiniMax_H3_Paint-on-glass_rank16_step1500.safetensors) (community upload) |
| `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors` | `loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors` | 1.82 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors) |
| `minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors` | `loras/minimax_h3/minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors` | 1.82 | not stated on the card | [lightx2v/Minimax-h3-Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/main/minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors) |
| `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | `diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors` | 19.53 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors) |
| `minimax_h3_style_transfer_v1.0_r64.safetensors` | `loras/minimax_h3/alissonerdx_v2v/loras/minimax_h3_style_transfer_v1.0_r64.safetensors` | 0.58 | mixed-asset-licenses | [Alissonerdx/Minimax-H3-ComfyUI](https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI/resolve/main/loras/minimax_h3_style_transfer_v1.0_r64.safetensors) (community upload) |
| `minimax_h3_taomate_3step_lora_avg_rank_19_bf16.safetensors` | `loras/minimax_h3/minimax_h3_taomate_3step_lora_avg_rank_19_bf16.safetensors` | 0.17 | not stated on the card | [Kijai/MiniMax-H3_comfy](https://huggingface.co/Kijai/MiniMax-H3_comfy/resolve/main/loras/minimax_h3_taomate_3step_lora_avg_rank_19_bf16.safetensors) |
| `minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors` | `loras/minimax_h3/minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors` | 0.58 | apache-2.0 | [drbaph/MiniMax-H3-Turbo-Lora-ComfyUI](https://huggingface.co/drbaph/MiniMax-H3-Turbo-Lora-ComfyUI/resolve/main/minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors) |
| `minimax_h3_vfx_edit_v1.0_r128.safetensors` | `loras/minimax_h3/alissonerdx_v2v/loras/minimax_h3_vfx_edit_v1.0_r128.safetensors` | 1.16 | mixed-asset-licenses | [Alissonerdx/Minimax-H3-ComfyUI](https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI/resolve/main/loras/minimax_h3_vfx_edit_v1.0_r128.safetensors) (community upload) |
| `minimax_h3_video_vae_fp16.safetensors` | `vae/minimax_h3_video_vae_fp16.safetensors` | 4.85 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors) |
| `minimax_h3_video_vae_int8_convrot.safetensors` | `vae/minimax_h3_video_vae_int8_convrot.safetensors` | 2.62 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_int8_convrot.safetensors) |
| `mvmt_h3_lora_v1_500.safetensors` | `loras/minimax_h3/civitai2/mvmt_h3_lora_v1_500.safetensors` | 0.29 | apache-2.0 | [vpakarinen/better-human-motion-h3-lora](https://huggingface.co/vpakarinen/better-human-motion-h3-lora/resolve/main/better_motion_h3_lora_v1_500.safetensors), published as `better_motion_h3_lora_v1_500.safetensors` (community upload) |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 14.61 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) |
| `Restore_Enhance_Improve_rank16_v1_H3-lora.safetensors` | `loras/minimax_h3/civitai_wide/Restore_Enhance_Improve_rank16_v1_H3-lora.safetensors` | 0.14 | not stated on the card | [Jacob121294/h3-restore-enhance-improve-lora](https://huggingface.co/Jacob121294/h3-restore-enhance-improve-lora/resolve/main/Restore_Enhance_Improve_rank16_v1_H3-lora.safetensors) (community upload) |
| `retro-toon-70s.safetensors` | `loras/minimax_h3/style/retro-toon-70s.safetensors` | 0.12 | minimax-h3-community-license | [KennethFal/retro-toon-70s-lora-minimax-h3](https://huggingface.co/KennethFal/retro-toon-70s-lora-minimax-h3/resolve/main/retro-toon-70s.safetensors) (community upload) |
| `rt_detr_v4-x-hgnet_fp16.safetensors` | `diffusion_models/rt_detr_v4-x-hgnet_fp16.safetensors` | 0.12 | mit | [Comfy-Org/SDPose](https://huggingface.co/Comfy-Org/SDPose/resolve/main/diffusion_models/rt_detr_v4-x-hgnet_fp16.safetensors) |
| `sdpose_wholebody_fp16.safetensors` | `checkpoints/sdpose_wholebody_fp16.safetensors` | 1.79 | mit | [Comfy-Org/SDPose](https://huggingface.co/Comfy-Org/SDPose/resolve/main/checkpoints/sdpose_wholebody_fp16.safetensors) |
| `step-10000.safetensors` | `loras/minimax/H3-World/step-10000.safetensors` | 0.12 | apache-2.0 | [t8star/Minimax-H3-World-Comfy](https://huggingface.co/t8star/Minimax-H3-World-Comfy/resolve/main/loras/minimax/H3-World/step-10000.safetensors) |
| `Transformation_style_c1-st2500_comfyui.safetensors` | `loras/minimax_h3/style/Transformation_style_c1-st2500_comfyui.safetensors` | 0.03 | minimax-community-license | [Ashmotv/transformation_lora](https://huggingface.co/Ashmotv/transformation_lora/resolve/main/Transformation_style_c1-st2500_comfyui.safetensors) (community upload) |
| `wushu_spatial_physics_clean_3000_pruned.safetensors` | `loras/minimax_h3/civitai_wide/wushu_spatial_physics_clean_3000_pruned.safetensors` | 0.14 | apache-2.0 | [Jojocodex/minimax-h3-spatial-physics-lora](https://huggingface.co/Jojocodex/minimax-h3-spatial-physics-lora/resolve/main/wushu_spatial_physics_clean_3000_pruned.safetensors) (community upload) |
| `zyj11111_MinimaxH3AuthenticCinematicTexture.safetensors` | `loras/minimax_h3/style/zyj11111_MinimaxH3AuthenticCinematicTexture.safetensors` | 0.29 | not stated | [ModelScope zyj11111/MinimaxH3AuthenticCinematicTexture](https://modelscope.cn/models/zyj11111/MinimaxH3AuthenticCinematicTexture/resolve/master/Minimax%20H3%E7%9C%9F%E5%AE%9E%E7%94%B5%E5%BD%B1%E8%B4%A8%E6%84%9F.safetensors), published as `Minimax H3真实电影质感.safetensors` |
| `30sTechnicolorMovie_minimaxh3_3339408_epoch_10.safetensors` | `loras/minimax_h3/civitai2/30sTechnicolorMovie_minimaxh3_3339408_epoch_10.safetensors` | 0.29 | see the Civitai page | Civitai only: [30s Technicolor Movie](https://civitai.com/models/886686?modelVersionId=3339781) (matched by SHA-256) |
| `acceleration_slider_v1.0.safetensors` | `loras/minimax_h3/civitai_sfw/acceleration_slider_v1.0.safetensors` | 0.00 | see the Civitai page | Civitai only: [Acceleration Slider MMH3: Rapid changes in movement speed](https://civitai.com/models/2991220?modelVersionId=3391949) (matched by SHA-256) |
| `AmateurHour_H3_000017500.safetensors` | `loras/minimax_h3/civitai2/AmateurHour_H3_000017500.safetensors` | 0.14 | see the Civitai page | Civitai only: [Amateur Hour](https://civitai.com/models/2530917?modelVersionId=3317385) (matched by SHA-256) |
| `aswhm_lora_v1_500.safetensors` | `loras/minimax_h3/civitai_wide/aswhm_lora_v1_500.safetensors` | 0.14 | see the Civitai page | Civitai only: [ASMR Trigger & Audio Minimax H3](https://civitai.com/models/2946392?modelVersionId=3336378) (matched by SHA-256) |
| `BulletTime-MMH3.safetensors` | `loras/minimax_h3/civitai2/BulletTime-MMH3.safetensors` | 0.09 | see the Civitai page | Civitai only: [[MMH3] Bullet Time](https://civitai.com/models/2934116?modelVersionId=3321093) (matched by SHA-256) |
| `cinemagrade_style_h3_ep50.safetensors` | `loras/minimax_h3/civitai_wide/cinemagrade_style_h3_ep50.safetensors` | 0.07 | see the Civitai page | Civitai only: [CinemaGrade - MiniMax H3 Style LoRA](https://civitai.com/models/2927223?modelVersionId=3312531) (matched by SHA-256) |
| `Cinematic_Fantasy_rank16_v1_H3-lora.safetensors` | `loras/minimax_h3/civitai_wide/Cinematic_Fantasy_rank16_v1_H3-lora.safetensors` | 0.14 | see the Civitai page | Civitai only: [Cinematic Fantasy](https://civitai.com/models/2957855?modelVersionId=3350636) (matched by SHA-256) |
| `Crash_Zoom_MinimaxH3_v1.safetensors` | `loras/minimax_h3/civitai2/Crash_Zoom_MinimaxH3_v1.safetensors` | 0.29 | see the Civitai page | Civitai only: [Crash Zoom / Minimax H3](https://civitai.com/models/2912041?modelVersionId=3294020) (matched by SHA-256) |
| `Dance_Choreography_minimaxh3_3394768_epoch_10.safetensors` | `loras/minimax_h3/civitai_sfw/Dance_Choreography_minimaxh3_3394768_epoch_10.safetensors` | 0.29 | see the Civitai page | Civitai only: [Dance/Choreographed Dancing LoRA for MiniMax H3](https://civitai.com/models/2991318?modelVersionId=3395440) (matched by SHA-256) |
| `DiffSynth-Studio_MiniMax-H3-LoRA-LineartAnime_comfy.safetensors` | `loras/minimax_h3/style/DiffSynth-Studio_MiniMax-H3-LoRA-LineartAnime_comfy.safetensors` | ? | unknown | No public source found |
| `dolly_zoom_minimaxh3_v1.safetensors` | `loras/minimax_h3/civitai2/dolly_zoom_minimaxh3_v1.safetensors` | 0.29 | see the Civitai page | Civitai only: [Dolly Zoom / Minimax H3](https://civitai.com/models/2913768?modelVersionId=3296179) (matched by SHA-256) |
| `dr0nesh0t_aerial_flyover_000000500.safetensors` | `loras/minimax_h3/civitai2/dr0nesh0t_aerial_flyover_000000500.safetensors` | 0.14 | see the Civitai page | Civitai only: [Drone Shot](https://civitai.com/models/2857065?modelVersionId=3226987) (matched by SHA-256) |
| `FrozenWorld_v1.safetensors` | `loras/minimax_h3/civitai_wide/FrozenWorld_v1.safetensors` | 0.29 | see the Civitai page | Civitai only: [Frozen World — Time-Freeze for MiniMax H3](https://civitai.com/models/2986051?modelVersionId=3385432) (matched by SHA-256) |
| `H3_Dutch_Angle_Slider_v1.safetensors` | `loras/minimax_h3/civitai_sfw/H3_Dutch_Angle_Slider_v1.safetensors` | 0.29 | see the Civitai page | Civitai only: [H3 Dutch Angle Slider](https://civitai.com/models/2952026?modelVersionId=3343505) (matched by SHA-256) |
| `h3_photoreal_ph0t0r34l_1024-step00003780.safetensors` | `loras/minimax_h3/civitai_wide/h3_photoreal_ph0t0r34l_1024-step00003780.safetensors` | 0.56 | see the Civitai page | Civitai only: [Minimax H3 Photorealistic Image Generator (LORA + Workflow)](https://civitai.com/models/2884206?modelVersionId=3260165) (matched by SHA-256) |
| `h3_photoreal_ph0t0r34l_1024-step00003990.safetensors` | `loras/minimax_h3/civitai_wide/h3_photoreal_ph0t0r34l_1024-step00003990.safetensors` | 0.56 | see the Civitai page | Civitai only: [Minimax H3 Photorealistic Image Generator (LORA + Workflow)](https://civitai.com/models/2884206?modelVersionId=3260165) (matched by SHA-256) |
| `h3_upscale_1920.safetensors` | `loras/minimax_h3/civitai_wide/h3_upscale_1920.safetensors` | 0.56 | see the Civitai page | Civitai only: [Minimax H3 Image Upscaler (LORA + Workflow & Batch)](https://civitai.com/models/2924512?modelVersionId=3309188) (matched by SHA-256) |
| `hand-drawn.safetensors` | `loras/minimax_h3/style/hand-drawn.safetensors` | ? | unknown | No public source found |
| `Kokoro_Bella_H3_minimax.safetensors` | `loras/minimax_h3/civitai_wide/Kokoro_Bella_H3_minimax.safetensors` | 0.29 | see the Civitai page | Civitai only: [Kokoro Female Voices LoRAs (Minimax H3)](https://civitai.com/models/2933702?modelVersionId=3320580) (matched by SHA-256) |
| `Kokoro_Heart_H3_minimax.safetensors` | `loras/minimax_h3/civitai_wide/Kokoro_Heart_H3_minimax.safetensors` | 0.29 | see the Civitai page | Civitai only: [Kokoro Female Voices LoRAs (Minimax H3)](https://civitai.com/models/2933702?modelVersionId=3320561) (matched by SHA-256) |
| `Kokoro_Nicole_H3_minimax.safetensors` | `loras/minimax_h3/civitai_wide/Kokoro_Nicole_H3_minimax.safetensors` | 0.29 | see the Civitai page | Civitai only: [Kokoro Female Voices LoRAs (Minimax H3)](https://civitai.com/models/2933702?modelVersionId=3320589) (matched by SHA-256) |
| `meridian_teacher_plus_turbo_rankcat_lora.safetensors` | `loras/minimax_h3/meridian/comfyui/meridian_teacher_plus_turbo_rankcat_lora.safetensors` | ? | unknown | No public source found |
| `minimax-h3-facial-realism-closeup-cp2000_comfy.safetensors` | `loras/minimax_h3/style/minimax-h3-facial-realism-closeup-cp2000_comfy.safetensors` | ? | unknown | No public source found |
| `MiniMax-H3-FL2VA-Acc-8Step_comfyui_pdd.safetensors` | `loras/minimax_h3/MiniMax-H3-FL2VA-Acc-8Step_comfyui_pdd.safetensors` | ? | unknown | No public source found |
| `MiniMax-H3-Ref2VA-Acc-8Step_comfyui_pdd.safetensors` | `loras/minimax_h3/MiniMax-H3-Ref2VA-Acc-8Step_comfyui_pdd.safetensors` | ? | unknown | No public source found |
| `MiniMax_H3_FL2VA_pruned_nvfp4.safetensors` | `diffusion_models/MiniMax_H3_FL2VA_pruned_nvfp4.safetensors` | ? | unknown | No public source found |
| `minimax_h3_turbo_v4_step600_ema.safetensors` | `loras/minimax_h3/minimax_h3_turbo_v4_step600_ema.safetensors` | 0.73 | see the Civitai page | Civitai only: [MINIMAX H3 TURBO LoRA ⚡](https://civitai.com/models/2838221?modelVersionId=3209318) (matched by SHA-256) |
| `MMH3-AfterlightStyle-V1.safetensors` | `loras/minimax_h3/civitai2/MMH3-AfterlightStyle-V1.safetensors` | 0.10 | see the Civitai page | Civitai only: [[MMH3] Afterlight](https://civitai.com/models/2969395?modelVersionId=3364782) (matched by SHA-256) |
| `MMH3-CelShadingStyle-V1.safetensors` | `loras/minimax_h3/civitai2/MMH3-CelShadingStyle-V1.safetensors` | 0.04 | see the Civitai page | Civitai only: [[MMH3] Cel Shading Style](https://civitai.com/models/2966038?modelVersionId=3360700) (matched by SHA-256) |
| `MMH3-DayNightSlider-V1.safetensors` | `loras/minimax_h3/civitai2/MMH3-DayNightSlider-V1.safetensors` | 0.00 | see the Civitai page | Civitai only: [[MMH3] DayNight Slider](https://civitai.com/models/2949040?modelVersionId=3339780) (matched by SHA-256) |
| `MMH3-ExposureSlider-V1.safetensors` | `loras/minimax_h3/civitai2/MMH3-ExposureSlider-V1.safetensors` | 0.00 | see the Civitai page | Civitai only: [[MMH3] Exposure Slider](https://civitai.com/models/2946844?modelVersionId=3337028) (matched by SHA-256) |
| `MMH3-FocusSlider-V1.safetensors` | `loras/minimax_h3/civitai2/MMH3-FocusSlider-V1.safetensors` | 0.00 | see the Civitai page | Civitai only: [[MMH3] FocusSlider](https://civitai.com/models/2951898?modelVersionId=3343342) (matched by SHA-256) |
| `MMH3-LOCKSTAB-MORE.safetensors` | `loras/minimax_h3/civitai_sfw/MMH3-LOCKSTAB-MORE.safetensors` | 0.06 | see the Civitai page | Civitai only: [MMH3 - Locked Stabilization (Camera locked to target)](https://civitai.com/models/2975645?modelVersionId=3372549) (matched by SHA-256) |
| `motion_speed_slider_mmh3_v1.1.safetensors` | `loras/minimax_h3/civitai2/motion_speed_slider_mmh3_v1.1.safetensors` | 0.00 | see the Civitai page | Civitai only: [Motion-Speed-MMH3-SLIDER](https://civitai.com/models/2985458?modelVersionId=3389300) (matched by SHA-256) |
| `nafasp_h3_lora_v2_500.safetensors` | `loras/minimax_h3/civitai_sfw/nafasp_h3_lora_v2_500.safetensors` | 0.29 | see the Civitai page | Civitai only: [Natural Face & Speech Minimax H3](https://civitai.com/models/2925394?modelVersionId=3339123) (matched by SHA-256) |
| `progressive_acceleration_slider_v1.0.safetensors` | `loras/minimax_h3/civitai_wide/progressive_acceleration_slider_v1.0.safetensors` | 0.01 | see the Civitai page | Civitai only: [Progressive Acceleration MMH3 Slider: Smoothly accelerates the speed of any action or motion over time.](https://civitai.com/models/2994324?modelVersionId=3395787) (matched by SHA-256) |
| `电影感loraV1.0正式版_剪枝与非剪枝通用.safetensors` | `loras/minimax_h3/civitai_sfw/电影感loraV1.0正式版_剪枝与非剪枝通用.safetensors` | 0.29 | see the Civitai page | Civitai only: [Minimax H3 Cinematic Version (Official Release) (No Tensor Errors)](https://civitai.com/models/2937713?modelVersionId=3325658) (matched by SHA-256) |

91 files, 150.87 GiB with a known size.

### Mochi

Used by: studio templates `mochi_core_t2v`; family templates `mochi_core_t2v`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `mochi_preview_bf16.safetensors` | `diffusion_models/mochi_preview_bf16.safetensors` | 18.68 | apache-2.0 | [Comfy-Org/Mochi-Preview](https://huggingface.co/Comfy-Org/Mochi-Preview/resolve/main/split_files/diffusion_models/mochi_preview_bf16.safetensors) |
| `mochi_vae.safetensors` | `vae/mochi_vae.safetensors` | 0.86 | apache-2.0 | [Comfy-Org/Mochi-Preview](https://huggingface.co/Comfy-Org/Mochi-Preview/resolve/main/split_files/vae/mochi_vae.safetensors) |

2 files, 19.53 GiB with a known size.

### Moss-Image

Used by: studio templates `moss_image_core_t2i`; 7 family templates; LoRA recipes `lora_08f8aaa8e7`, `lora_9490ecbae1`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `flux2-vae_small.safetensors` | `vae/flux2-vae_small.safetensors` | 0.23 | apache-2.0 | [Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/vae/flux2-vae_small.safetensors) |
| `moge_3_vitg_fp16.safetensors` | `geometry_estimation/moge_3_vitg_fp16.safetensors` | 2.33 | mit | [Comfy-Org/MoGe](https://huggingface.co/Comfy-Org/MoGe/resolve/main/geometry_estimation/moge_3_vitg_fp16.safetensors) |
| `moss_image_base_int8_convrot.safetensors` | `diffusion_models/moss_image_base_int8_convrot.safetensors` | 5.04 | apache-2.0 | [Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/diffusion_models/moss_image_base_int8_convrot.safetensors) |
| `moss_image_color_depth_control.safetensors` | `loras/moss_image_color_depth_control.safetensors` | 0.29 | apache-2.0 | [Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/loras/moss_image_color_depth_control.safetensors) |
| `moss_image_edit_lora_rank_64_bf16.safetensors` | `loras/moss_image_edit_lora_rank_64_bf16.safetensors` | 0.28 | apache-2.0 | [Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/loras/moss_image_edit_lora_rank_64_bf16.safetensors) |
| `moss_image_sft_int8_convrot.safetensors` | `diffusion_models/moss_image_sft_int8_convrot.safetensors` | 5.04 | apache-2.0 | [Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/diffusion_models/moss_image_sft_int8_convrot.safetensors) |
| `qwen3.5_9b_int8_convrot.safetensors` | `text_encoders/qwen3.5_9b_int8_convrot.safetensors` | 9.08 | apache-2.0 | [Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/text_encoders/qwen3.5_9b_int8_convrot.safetensors) |
| `qwen3.5_9b_w4a8_gptq.safetensors` | `text_encoders/qwen3.5_9b_w4a8_gptq.safetensors` | 6.84 | apache-2.0 | [Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/text_encoders/qwen3.5_9b_w4a8_gptq.safetensors) |

8 files, 29.13 GiB with a known size.

### Motion

Used by: features `feature_motion`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `Kimodo-SOMA-RP-v1.1/model.safetensors` | `?` | 1.06 | nvidia-open-model-license | [nvidia/Kimodo-SOMA-RP-v1.1](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1/resolve/main/model.safetensors) |
| `latentsync_unet.pt` | `?` | 4.72 | openrail++ | [ByteDance/LatentSync-1.6](https://huggingface.co/ByteDance/LatentSync-1.6/resolve/main/latentsync_unet.pt) |

2 files, 5.78 GiB with a known size.

### MOVA

Used by: goals `animate`, `reshoot_wan`, `video`; workflows `campath_wan_api`, `vset_wan22_funcontrol_api`, `wan22_5b_i2v_api`, `wan22_5b_t2v_api`, `wan_camera_api`; 8 studio templates; 38 family templates; pipeline graphs `studio/web/pipelines/anime_short/graphs/move`, `studio/web/pipelines/anime_short/graphs/move2`, `studio/web/pipelines/anime_short/graphs/move3`; University graphs `studio/university/graphs/wf_wan22_t2v`; other graphs `studio/web/res4lyf_renders/graphs/wan_res_2m`, `studio/web/res4lyf_renders/nodes/Frames_Latent_ReverseOrder`, `studio/web/res4lyf_renders/nodes/Frames_Slice_Latent`; features `train_bases`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `mova_720p_high_noise_fp8_scaled.safetensors` | `diffusion_models/mova_720p_high_noise_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [rzgar/MOVA-720p-360p-ComfyUI](https://huggingface.co/rzgar/MOVA-720p-360p-ComfyUI/resolve/main/MOVA-720p/diffusion_models_fp8/mova_720p_high_noise_fp8_scaled.safetensors) (community upload) |
| `mova_720p_low_noise_fp8_scaled.safetensors` | `diffusion_models/mova_720p_low_noise_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [rzgar/MOVA-720p-360p-ComfyUI](https://huggingface.co/rzgar/MOVA-720p-360p-ComfyUI/resolve/main/MOVA-720p/diffusion_models_fp8/mova_720p_low_noise_fp8_scaled.safetensors) (community upload) |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6.27 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors) |

3 files, 32.90 GiB with a known size.

### Music (other)

Used by: workflows `music_stable_open_api`; Music page `diffsynth_music`, `magenta_rt2`, `mulacover`, `musicgen_small`, `songgeneration`, `stable3`, `stable_open`, `tangoflux`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `flan-t5-large/model.safetensors` | `?` | 2.92 | apache-2.0 | [google/flan-t5-large](https://huggingface.co/google/flan-t5-large/resolve/main/model.safetensors) |
| `mrt2_small.safetensors` | `checkpoints/mrt2_small.safetensors` | 1.05 | cc-by-4.0 | [google/magenta-realtime-2](https://huggingface.co/google/magenta-realtime-2/resolve/main/checkpoints/mrt2_small.safetensors) |
| `MuLaCover/model-00001-of-00005.safetensors` | `?` | 1.86 | cc-by-nc-4.0 (non-commercial) | [HeartMuLa/MuLaCover](https://huggingface.co/HeartMuLa/MuLaCover/resolve/main/model-00001-of-00005.safetensors) |
| `musicgen-small/model.safetensors` | `?` | 2.20 | cc-by-nc-4.0 (non-commercial) | [facebook/musicgen-small](https://huggingface.co/facebook/musicgen-small/resolve/main/model.safetensors) |
| `SongGeneration-v2-large/model.pt` | `?` | 12.01 | unknown | [lglg666/SongGeneration-v2-large](https://huggingface.co/lglg666/SongGeneration-v2-large/resolve/main/model.pt) (community upload) |
| `stable-audio-open-1.0.safetensors` | `checkpoints/stable-audio-open-1.0.safetensors` | 4.52 | stable-audio-community | [Comfy-Org/stable-audio-open-1.0](https://huggingface.co/Comfy-Org/stable-audio-open-1.0/resolve/main/stable-audio-open-1.0.safetensors) |
| `stable_audio_3_medium.safetensors` | `checkpoints/stable_audio_3_medium.safetensors` | 8.59 | stable-audio-community | [Comfy-Org/stable-audio-3](https://huggingface.co/Comfy-Org/stable-audio-3/resolve/main/checkpoints/stable_audio_3_medium.safetensors) |
| `stable_audio_3_small_music.safetensors` | `checkpoints/stable_audio_3_small_music.safetensors` | 2.11 | stable-audio-community | [Comfy-Org/stable-audio-3](https://huggingface.co/Comfy-Org/stable-audio-3/resolve/main/checkpoints/stable_audio_3_small_music.safetensors) |
| `t5gemma_b_b_ul2.safetensors` | `text_encoders/t5gemma_b_b_ul2.safetensors` | 1.11 | stable-audio-community | [Comfy-Org/stable-audio-3](https://huggingface.co/Comfy-Org/stable-audio-3/resolve/main/text_encoders/t5gemma_b_b_ul2.safetensors) |
| `tangoflux.safetensors` | `?` | 3.20 | not stated on the card | [declare-lab/TangoFlux](https://huggingface.co/declare-lab/TangoFlux/resolve/main/tangoflux.safetensors) |
| `text_encoder/model.safetensors` | `?` | 1.11 | apache-2.0 | [DiffSynth-Studio/DiffSynth-Music](https://huggingface.co/DiffSynth-Studio/DiffSynth-Music/resolve/main/text_encoder/model.safetensors) |

11 files, 40.68 GiB with a known size.

### Omnigen-2

Used by: family templates `image_omnigen2_image_edit`, `image_omnigen2_t2i`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `omnigen2_fp16.safetensors` | `diffusion_models/omnigen2_fp16.safetensors` | 7.39 | apache-2.0 | [Comfy-Org/OmniGen-2](https://huggingface.co/Comfy-Org/OmniGen-2/resolve/main/split_files/diffusion_models/omnigen2_fp16.safetensors) |
| `qwen_2.5_vl_fp16.safetensors` | `text_encoders/qwen_2.5_vl_fp16.safetensors` | 6.99 | apache-2.0 | [Comfy-Org/OmniGen-2](https://huggingface.co/Comfy-Org/OmniGen-2/resolve/main/split_files/text_encoders/qwen_2.5_vl_fp16.safetensors) |

2 files, 14.38 GiB with a known size.

### Other

Used by: University graphs `studio/university/graphs/c_unclip`; features `foley`, `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `cav_mae_st.pth` | `ext_weights/cav_mae_st.pth` | 0.71 | cc-by-nc-4.0 (non-commercial) | [YJX-Xiaomi/ControlFoley](https://huggingface.co/YJX-Xiaomi/ControlFoley/resolve/main/ext_weights/cav_mae_st.pth) (community upload) |
| `controlfoley.pth` | `?` | 10.52 | cc-by-nc-4.0 (non-commercial) | [YJX-Xiaomi/ControlFoley](https://huggingface.co/YJX-Xiaomi/ControlFoley/resolve/main/weights/controlfoley.pth) (community upload) |
| `dav.pth` | `?` | 0.46 | not stated on the card | [MiniMaxAI/MiniMax-Music3](https://huggingface.co/MiniMaxAI/MiniMax-Music3/resolve/main/dav.pth) |
| `music_speech_audioset_epoch_15_esc_89.98.pt` | `ext_weights/music_speech_audioset_epoch_15_esc_89.98.pt` | 2.19 | cc-by-nc-4.0 (non-commercial) | [YJX-Xiaomi/ControlFoley](https://huggingface.co/YJX-Xiaomi/ControlFoley/resolve/main/ext_weights/music_speech_audioset_epoch_15_esc_89.98.pt) (community upload) |
| `sd21-unclip-h.ckpt` | `checkpoints/sd21-unclip-h.ckpt` | 7.42 | openrail++ | [Comfy-Org/stable-diffusion-2.1-unclip](https://huggingface.co/Comfy-Org/stable-diffusion-2.1-unclip/resolve/main/sd21-unclip-h.ckpt) |
| `synchformer_state_dict.pth` | `ext_weights/synchformer_state_dict.pth` | 0.88 | cc-by-nc-4.0 (non-commercial) | [HKUSTAudio/AudioX-MAF](https://huggingface.co/HKUSTAudio/AudioX-MAF/resolve/main/synchformer_state_dict.pth) (community upload) |
| `v1-44.pth` | `ext_weights/v1-44.pth` | 1.14 | cc-by-nc-4.0 (non-commercial) | [YJX-Xiaomi/ControlFoley](https://huggingface.co/YJX-Xiaomi/ControlFoley/resolve/main/ext_weights/v1-44.pth) (community upload) |
| `empty_string.pth` | `ext_weights/empty_string.pth` | ? | unknown | No public source found |

8 files, 23.32 GiB with a known size.

### Ovis-Image

Used by: family templates `image_ovis_text_to_image`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `ovis_2.5.safetensors` | `text_encoders/ovis_2.5.safetensors` | 4.79 | apache-2.0 | [Comfy-Org/Ovis-Image](https://huggingface.co/Comfy-Org/Ovis-Image/resolve/main/split_files/text_encoders/ovis_2.5.safetensors) |
| `ovis_image_bf16.safetensors` | `diffusion_models/ovis_image_bf16.safetensors` | 13.73 | apache-2.0 | [Comfy-Org/Ovis-Image](https://huggingface.co/Comfy-Org/Ovis-Image/resolve/main/split_files/diffusion_models/ovis_image_bf16.safetensors) |

2 files, 18.52 GiB with a known size.

### Pixal3D

Used by: workflows `worldkit_cutout_api`, `worldkit_trellis2_character_api`; studio templates `birefnet_cutout`, `trellis2_image_to_mesh`; 5 family templates; 6 pipeline graphs; features `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `birefnet.safetensors` | `background_removal/birefnet.safetensors` | 0.41 | mit | [Comfy-Org/BiRefNet](https://huggingface.co/Comfy-Org/BiRefNet/resolve/main/background_removal/birefnet.safetensors) |
| `dino_v3_L_naf_fp32.safetensors` | `text_encoders/dino_v3_L_naf_fp32.safetensors` | 1.13 | mit | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D/resolve/main/clip_vision/dino_v3_L_naf_fp32.safetensors) |
| `pixal3d_int8_convrot.safetensors` | `diffusion_models/pixal3d_int8_convrot.safetensors` | 5.20 | mit | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D/resolve/main/diffusion_models/pixal3d_int8_convrot.safetensors) |
| `pixal3d_multiview_int8_convrot.safetensors` | `diffusion_models/pixal3d_multiview_int8_convrot.safetensors` | 5.20 | mit | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D/resolve/main/diffusion_models/pixal3d_multiview_int8_convrot.safetensors) |
| `trellis_2_int8_convrot.safetensors` | `3d/trellis_2_int8_convrot.safetensors` | 4.89 | mit | [Comfy-Org/TRELLIS.2](https://huggingface.co/Comfy-Org/TRELLIS.2/resolve/main/diffusion_models/trellis_2_int8_convrot.safetensors) |
| `trellis_2_shape_vae_bf16.safetensors` | `vae/trellis_2_shape_vae_bf16.safetensors` | 1.02 | mit | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D/resolve/main/vae/trellis_2_shape_vae_bf16.safetensors) |
| `trellis_2_texture_vae_bf16.safetensors` | `vae/trellis_2_texture_vae_bf16.safetensors` | 0.88 | mit | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D/resolve/main/vae/trellis_2_texture_vae_bf16.safetensors) |

7 files, 18.74 GiB with a known size.

### PixArt-Sigma

Used by: studio templates `pixart_sigma_core_t2i`; family templates `pixart_sigma_core_t2i`; features `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `sdxl_vae.safetensors` | `vae/sdxl_vae.safetensors` | 0.31 | mit | [stabilityai/sdxl-vae](https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors) |
| `pixart-sigma_transformer.safetensors` | `diffusion_models/pixart-sigma_transformer.safetensors` | ? | unknown | No public source found |

2 files, 0.31 GiB with a known size.

### PixelDiT

Used by: family templates `image_pixeldit_t2i`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `pixeldit_1300m_1024px_bf16.safetensors` | `diffusion_models/pixeldit_1300m_1024px_bf16.safetensors` | 2.43 | nsclv1 | [Comfy-Org/PixelDiT](https://huggingface.co/Comfy-Org/PixelDiT/resolve/main/diffusion_models/pixeldit_1300m_1024px_bf16.safetensors) |

1 files, 2.43 GiB with a known size.

### Qwen-Image-2.1

Used by: workflows `oneclick_angles_api`, `oneclick_effect_api`, `oneclick_effect_clip_api`, `oneclick_relight_api`, `vset_keyframe_edit_api`; 18 studio templates; 41 family templates; pipeline graphs `studio/web/pipelines/product_hero/graphs/relit`, `studio/web/pipelines/tryon_clip/graphs/worn`; 12 LoRA recipes; features `feature_oneclick`, `train_bases`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `illustration-1.0-qwen-image.safetensors` | `loras/illustration-1.0-qwen-image.safetensors` | 0.72 | other | [alvdansen/illustration-1.0-qwen-image](https://huggingface.co/alvdansen/illustration-1.0-qwen-image/resolve/main/illustration-1.0-qwen-image.safetensors) (community upload) |
| `mage_flow_int8_convrot.safetensors` | `diffusion_models/mage_flow_int8_convrot.safetensors` | 3.87 | mit | [Comfy-Org/Mage-Flow](https://huggingface.co/Comfy-Org/Mage-Flow/resolve/main/diffusion_models/mage_flow_int8_convrot.safetensors) |
| `mage_flow_vae_bf16.safetensors` | `vae/mage_flow_vae_bf16.safetensors` | 0.32 | mit | [Comfy-Org/Mage-Flow](https://huggingface.co/Comfy-Org/Mage-Flow/resolve/main/vae/mage_flow_vae_bf16.safetensors) |
| `marigold_v2_albedo.safetensors` | `loras/marigold_v2_albedo.safetensors` | 1.59 | apache-2.0 | [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0/resolve/main/loras/marigold_v2_albedo.safetensors) |
| `marigold_v2_albedo_conditioning.safetensors` | `embeddings/marigold_v2_albedo_conditioning.safetensors` | 0.00 | apache-2.0 | [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0/resolve/main/embeddings/marigold_v2_albedo_conditioning.safetensors) |
| `marigold_v2_albedo_vae.safetensors` | `vae/marigold_v2_albedo_vae.safetensors` | 0.24 | apache-2.0 | [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0/resolve/main/vae/marigold_v2_albedo_vae.safetensors) |
| `marigold_v2_depth_conditioning.safetensors` | `embeddings/marigold_v2_depth_conditioning.safetensors` | 0.00 | apache-2.0 | [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0/resolve/main/embeddings/marigold_v2_depth_conditioning.safetensors) |
| `marigold_v2_depth_log_stage2.safetensors` | `loras/marigold_v2_depth_log_stage2.safetensors` | 1.59 | apache-2.0 | [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0/resolve/main/loras/marigold_v2_depth_log_stage2.safetensors) |
| `marigold_v2_depth_log_stage2_vae.safetensors` | `vae/marigold_v2_depth_log_stage2_vae.safetensors` | 0.24 | apache-2.0 | [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0/resolve/main/vae/marigold_v2_depth_log_stage2_vae.safetensors) |
| `marigold_v2_normals.safetensors` | `loras/marigold_v2_normals.safetensors` | 1.59 | apache-2.0 | [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0/resolve/main/loras/marigold_v2_normals.safetensors) |
| `marigold_v2_normals_conditioning.safetensors` | `embeddings/marigold_v2_normals_conditioning.safetensors` | 0.00 | apache-2.0 | [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0/resolve/main/embeddings/marigold_v2_normals_conditioning.safetensors) |
| `marigold_v2_normals_vae.safetensors` | `vae/marigold_v2_normals_vae.safetensors` | 0.24 | apache-2.0 | [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0/resolve/main/vae/marigold_v2_normals_vae.safetensors) |
| `qwen-360-diffusion-2512-int8-bf16-v2.safetensors` | `loras/qwen-360-diffusion-2512-int8-bf16-v2.safetensors` | 0.70 | mit | [ProGamerGov/qwen-360-diffusion](https://huggingface.co/ProGamerGov/qwen-360-diffusion/resolve/main/qwen-360-diffusion-2512-int8-bf16-v2.safetensors) (community upload) |
| `qwen-image-2.1-outfit-swap.safetensors` | `loras/qwen-image-2.1-outfit-swap.safetensors` | 0.15 | qwen-research-license (non-commercial) | [ausboss/Qwen-Image-2.1-Outfit-Swap-Consistency-LoRA](https://huggingface.co/ausboss/Qwen-Image-2.1-Outfit-Swap-Consistency-LoRA/resolve/main/qwen-image-2.1-outfit-swap.safetensors) (community upload) |
| `Qwen-Image-2512-Fun-Controlnet-Union-2602.safetensors` | `controlnet/Qwen-Image-2512-Fun-Controlnet-Union-2602.safetensors` | 3.27 | apache-2.0 | [alibaba-pai/Qwen-Image-2512-Fun-Controlnet-Union](https://huggingface.co/alibaba-pai/Qwen-Image-2512-Fun-Controlnet-Union/resolve/main/Qwen-Image-2512-Fun-Controlnet-Union-2602.safetensors) |
| `Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors` | `loras/Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors` | 1.58 | apache-2.0 | [lightx2v/Qwen-Image-2512-Lightning](https://huggingface.co/lightx2v/Qwen-Image-2512-Lightning/resolve/main/Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors) |
| `Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors` | `loras/Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors` | 0.79 | apache-2.0 | [lightx2v/Qwen-Image-Lightning](https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Edit-2509/Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors) |
| `Qwen-Image-Edit-2509-Relight.safetensors` | `loras/Qwen-Image-Edit-2509-Relight.safetensors` | 0.22 | apache-2.0 | [Comfy-Org/Qwen-Image-Edit](https://huggingface.co/Comfy-Org/Qwen-Image-Edit/resolve/main/split_files/loras/Qwen-Image-Edit-2509-Relight.safetensors) |
| `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` | `loras/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` | 0.79 | apache-2.0 | [lightx2v/Qwen-Image-Edit-2511-Lightning](https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors) |
| `qwen-image-edit-2511-multiple-angles-lora.safetensors` | `loras/qwen-image-edit-2511-multiple-angles-lora.safetensors` | 0.27 | apache-2.0 | [fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA](https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA/resolve/main/qwen-image-edit-2511-multiple-angles-lora.safetensors) (community upload) |
| `Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors` | `loras/Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors` | 0.79 | apache-2.0 | [lightx2v/Qwen-Image-Lightning](https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Edit-Lightning-4steps-V1.0-bf16.safetensors) |
| `Qwen-Image-InstantX-ControlNet-Inpainting.safetensors` | `controlnet/Qwen-Image-InstantX-ControlNet-Inpainting.safetensors` | 3.94 | apache-2.0 | [Comfy-Org/Qwen-Image-InstantX-ControlNets](https://huggingface.co/Comfy-Org/Qwen-Image-InstantX-ControlNets/resolve/main/split_files/controlnet/Qwen-Image-InstantX-ControlNet-Inpainting.safetensors) |
| `Qwen-Image-InstantX-ControlNet-Union.safetensors` | `controlnet/Qwen-Image-InstantX-ControlNet-Union.safetensors` | 3.29 | apache-2.0 | [Comfy-Org/Qwen-Image-InstantX-ControlNets](https://huggingface.co/Comfy-Org/Qwen-Image-InstantX-ControlNets/resolve/main/split_files/controlnet/Qwen-Image-InstantX-ControlNet-Union.safetensors) |
| `Qwen-Image-Lightning-4steps-V1.0.safetensors` | `loras/Qwen-Image-Lightning-4steps-V1.0.safetensors` | 1.58 | apache-2.0 | [lightx2v/Qwen-Image-Lightning](https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Lightning-4steps-V1.0.safetensors) |
| `Qwen-Image-Lightning-8steps-V1.0.safetensors` | `loras/Qwen-Image-Lightning-8steps-V1.0.safetensors` | 1.58 | apache-2.0 | [lightx2v/Qwen-Image-Lightning](https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Lightning-8steps-V1.0.safetensors) |
| `qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors` | `text_encoders/qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors` | 8.82 | qwen-research (non-commercial) | [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/text_encoders/qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors) |
| `qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors` | `text_encoders/qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors` | 8.82 | qwen-research (non-commercial) | [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/text_encoders/qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors) |
| `QWEN_EDIT_ACTION_V1.safetensors` | `loras/QWEN_EDIT_ACTION_V1.safetensors` | 0.27 | apache-2.0 | [systms/SYSTMS-ACTION-LoRA-Qwen-Image-Edit-2511](https://huggingface.co/systms/SYSTMS-ACTION-LoRA-Qwen-Image-Edit-2511/resolve/main/QWEN_EDIT_ACTION_V1.safetensors) (community upload) |
| `qwen_image_2.1_bf16.safetensors` | `diffusion_models/qwen_image_2.1_bf16.safetensors` | 13.25 | qwen-research (non-commercial) | [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_bf16.safetensors) |
| `qwen_image_2.1_int8_convrot.safetensors` | `diffusion_models/qwen_image_2.1_int8_convrot.safetensors` | 6.76 | qwen-research (non-commercial) | [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_int8_convrot.safetensors) |
| `qwen_image_2.1_turbo_bf16.safetensors` | `diffusion_models/qwen_image_2.1_turbo_bf16.safetensors` | 13.25 | qwen-research (non-commercial) | [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_turbo_bf16.safetensors) |
| `qwen_image_2.1_turbo_int8_convrot.safetensors` | `diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors` | 6.76 | qwen-research (non-commercial) | [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors) |
| `qwen_image_2.1_vae_bf16.safetensors` | `vae/qwen_image_2.1_vae_bf16.safetensors` | 0.63 | qwen-research (non-commercial) | [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors) |
| `qwen_image_2512_fp8_e4m3fn.safetensors` | `diffusion_models/qwen_image_2512_fp8_e4m3fn.safetensors` | 19.03 | apache-2.0 | [Comfy-Org/Qwen-Image](https://huggingface.co/Comfy-Org/Qwen-Image/resolve/main/split_files/diffusion_models/qwen_image_2512_fp8_e4m3fn.safetensors) |
| `qwen_image_canny_diffsynth_controlnet.safetensors` | `model_patches/qwen_image_canny_diffsynth_controlnet.safetensors` | 2.11 | apache-2.0 | [Comfy-Org/Qwen-Image-DiffSynth-ControlNets](https://huggingface.co/Comfy-Org/Qwen-Image-DiffSynth-ControlNets/resolve/main/split_files/model_patches/qwen_image_canny_diffsynth_controlnet.safetensors) |
| `qwen_image_edit_2509_fp8_e4m3fn.safetensors` | `diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors` | 19.03 | apache-2.0 | [Comfy-Org/Qwen-Image-Edit](https://huggingface.co/Comfy-Org/Qwen-Image-Edit/resolve/main/split_files/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors) |
| `qwen_image_edit_2509_int8_convrot.safetensors` | `diffusion_models/qwen_image_edit_2509_int8_convrot.safetensors` | 19.09 | apache-2.0 | [Comfy-Org/marigold-v2-0](https://huggingface.co/Comfy-Org/marigold-v2-0/resolve/main/diffusion_models/qwen_image_edit_2509_int8_convrot.safetensors) |
| `Qwen_Image_Edit_2511-SYSTMS_INFL8.safetensors` | `loras/Qwen_Image_Edit_2511-SYSTMS_INFL8.safetensors` | 0.27 | apache-2.0 | [systms/SYSTMS-INFL8-LoRA-Qwen-Image-Edit-2511](https://huggingface.co/systms/SYSTMS-INFL8-LoRA-Qwen-Image-Edit-2511/resolve/main/SYSTMS_INFL8_LoRA_Qwen_Image_Edit_2511.safetensors), published as `SYSTMS_INFL8_LoRA_Qwen_Image_Edit_2511.safetensors` (community upload) |
| `qwen_image_edit_2511_bf16.safetensors` | `diffusion_models/qwen_image_edit_2511_bf16.safetensors` | 38.05 | apache-2.0 | [Comfy-Org/Qwen-Image-Edit](https://huggingface.co/Comfy-Org/Qwen-Image-Edit/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_bf16.safetensors) |
| `qwen_image_edit_2511_fp8mixed.safetensors` | `diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors` | 19.12 | apache-2.0 | [Comfy-Org/Qwen-Image-Edit](https://huggingface.co/Comfy-Org/Qwen-Image-Edit/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors) |
| `qwen_image_edit_2511_int8_convrot.safetensors` | `diffusion_models/qwen_image_edit_2511_int8_convrot.safetensors` | 19.09 | apache-2.0 | [Comfy-Org/Qwen-Image-Edit](https://huggingface.co/Comfy-Org/Qwen-Image-Edit/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_int8_convrot.safetensors) |
| `qwen_image_edit_fp8_e4m3fn.safetensors` | `diffusion_models/qwen_image_edit_fp8_e4m3fn.safetensors` | 19.03 | apache-2.0 | [Comfy-Org/Qwen-Image-Edit](https://huggingface.co/Comfy-Org/Qwen-Image-Edit/resolve/main/split_files/diffusion_models/qwen_image_edit_fp8_e4m3fn.safetensors) |
| `qwen_image_fp8_e4m3fn.safetensors` | `diffusion_models/qwen_image_fp8_e4m3fn.safetensors` | 19.03 | apache-2.0 | [Comfy-Org/Qwen-Image](https://huggingface.co/Comfy-Org/Qwen-Image/resolve/main/split_files/diffusion_models/qwen_image_fp8_e4m3fn.safetensors) |
| `qwen_image_layered_bf16.safetensors` | `diffusion_models/qwen_image_layered_bf16.safetensors` | 38.05 | apache-2.0 | [Comfy-Org/Qwen-Image-Layered](https://huggingface.co/Comfy-Org/Qwen-Image-Layered/resolve/main/split_files/diffusion_models/qwen_image_layered_bf16.safetensors) |
| `qwen_image_layered_control_bf16.safetensors` | `diffusion_models/qwen_image_layered_control_bf16.safetensors` | 38.05 | apache-2.0 | [DiffSynth-Studio/Qwen-Image-Layered-Control](https://huggingface.co/DiffSynth-Studio/Qwen-Image-Layered-Control/resolve/main/qwen_image_layered_control_bf16.safetensors) |
| `qwen_image_layered_vae.safetensors` | `vae/qwen_image_layered_vae.safetensors` | 0.24 | apache-2.0 | [Comfy-Org/Qwen-Image-Layered](https://huggingface.co/Comfy-Org/Qwen-Image-Layered/resolve/main/split_files/vae/qwen_image_layered_vae.safetensors) |
| `qwen_image_union_diffsynth_lora.safetensors` | `loras/qwen_image_union_diffsynth_lora.safetensors` | 0.88 | apache-2.0 | [Comfy-Org/Qwen-Image-DiffSynth-ControlNets](https://huggingface.co/Comfy-Org/Qwen-Image-DiffSynth-ControlNets/resolve/main/split_files/loras/qwen_image_union_diffsynth_lora.safetensors) |
| `Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors` | `loras/Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors` | 2.20 | apache-2.0 | [Wuli-art/Qwen-Image-2512-Turbo-LoRA-2-Steps](https://huggingface.co/Wuli-art/Qwen-Image-2512-Turbo-LoRA-2-Steps/resolve/main/Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors) (community upload) |
| `qwen3vl_8b_turbo_nvfp4.safetensors` | `text_encoders/qwen3vl_8b_turbo_nvfp4.safetensors` | ? | unknown | No public source found |

49 files, 341.22 GiB with a known size.

### SAM-3D-Body

Used by: workflows `worldkit_body_photo_api`; studio templates `motion_sam3d_capture`, `motion_scail2`; 7 family templates; pipeline graphs `studio/pipelines/graphs/pipeline_video_sam3_cut`; features `feature_motion`, `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `rt_detr_v4-x-hgnet_fp32.safetensors` | `diffusion_models/rt_detr_v4-x-hgnet_fp32.safetensors` | 0.23 | mit | [Comfy-Org/SDPose](https://huggingface.co/Comfy-Org/SDPose/resolve/main/diffusion_models/rt_detr_v4-x-hgnet_fp32.safetensors) |
| `sam3.1_multiplex_fp16.safetensors` | `checkpoints/sam3.1_multiplex_fp16.safetensors` | 1.63 | sam-license | [Comfy-Org/sam3.1](https://huggingface.co/Comfy-Org/sam3.1/resolve/main/checkpoints/sam3.1_multiplex_fp16.safetensors) |
| `sam_3d_body_dinov3_bf16.safetensors` | `detection/sam_3d_body_dinov3_bf16.safetensors` | 2.64 | sam-license | [Comfy-Org/sam-3d-body](https://huggingface.co/Comfy-Org/sam-3d-body/resolve/main/detection/sam_3d_body_dinov3_bf16.safetensors) |

3 files, 4.49 GiB with a known size.

### SD15

Used by: 14 studio templates; 15 family templates; 51 University graphs; 36 other graphs; features `sampling_graph`, `train_bases`, `words_graph`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `CLIP-ViT-H-fp16.safetensors` | `clip_vision/CLIP-ViT-H-fp16.safetensors` | 1.18 | apache-2.0 | [Kijai/CLIPVisionModelWithProjection_fp16](https://huggingface.co/Kijai/CLIPVisionModelWithProjection_fp16/resolve/main/CLIP-ViT-H-fp16.safetensors) |
| `clip_vision_g.safetensors` | `text_encoders/clip_vision_g.safetensors` | 3.44 | not stated on the card | [comfyanonymous/clip_vision_g](https://huggingface.co/comfyanonymous/clip_vision_g/resolve/main/clip_vision_g.safetensors) |
| `control_v11f1p_sd15_depth_fp16.safetensors` | `controlnet/control_v11f1p_sd15_depth_fp16.safetensors` | 0.67 | not stated on the card | [comfyanonymous/ControlNet-v1-1_fp16_safetensors](https://huggingface.co/comfyanonymous/ControlNet-v1-1_fp16_safetensors/resolve/main/control_v11f1p_sd15_depth_fp16.safetensors) |
| `control_v11p_sd15_canny_fp16.safetensors` | `controlnet/control_v11p_sd15_canny_fp16.safetensors` | 0.67 | not stated on the card | [comfyanonymous/ControlNet-v1-1_fp16_safetensors](https://huggingface.co/comfyanonymous/ControlNet-v1-1_fp16_safetensors/resolve/main/control_v11p_sd15_canny_fp16.safetensors) |
| `fofr_sd15_clip_l.safetensors` | `text_encoders/fofr_sd15_clip_l.safetensors` | 0.46 | creativeml-openrail-m | [stable-diffusion-v1-5/stable-diffusion-v1-5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/text_encoder/model.safetensors), published as `model.safetensors` |
| `instruct-pix2pix-00-22000.safetensors` | `checkpoints/instruct-pix2pix-00-22000.safetensors` | 7.17 | mit | [timbrooks/instruct-pix2pix](https://huggingface.co/timbrooks/instruct-pix2pix/resolve/main/instruct-pix2pix-00-22000.safetensors) |
| `ip-adapter-full-face_sd15.safetensors` | `ipadapter/ip-adapter-full-face_sd15.safetensors` | 0.04 | apache-2.0 | [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter-full-face_sd15.safetensors) |
| `ip-adapter-plus-face_sd15.safetensors` | `ipadapter/ip-adapter-plus-face_sd15.safetensors` | 0.09 | apache-2.0 | [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter-plus-face_sd15.safetensors) |
| `ip-adapter-plus_sd15.safetensors` | `ipadapter/ip-adapter-plus_sd15.safetensors` | 0.09 | apache-2.0 | [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter-plus_sd15.safetensors) |
| `ip-adapter_sd15.safetensors` | `ipadapter/ip-adapter_sd15.safetensors` | 0.04 | apache-2.0 | [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter_sd15.safetensors) |
| `ip-adapter_sd15_light.safetensors` | `ipadapter/ip-adapter_sd15_light.safetensors` | 0.04 | apache-2.0 | [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter_sd15_light.safetensors) |
| `ip-adapter_sd15_vit-G.safetensors` | `ipadapter/ip-adapter_sd15_vit-G.safetensors` | 0.04 | apache-2.0 | [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter_sd15_vit-G.safetensors) |
| `lcm-lora-sdv1-5.safetensors` | `loras/lcm-lora-sdv1-5.safetensors` | 0.13 | openrail++ | [latent-consistency/lcm-lora-sdv1-5](https://huggingface.co/latent-consistency/lcm-lora-sdv1-5/resolve/main/pytorch_lora_weights.safetensors), published as `pytorch_lora_weights.safetensors` |
| `sd-v1-5-inpainting.ckpt` | `checkpoints/sd-v1-5-inpainting.ckpt` | 3.97 | creativeml-openrail-m | [stable-diffusion-v1-5/stable-diffusion-inpainting](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting/resolve/main/sd-v1-5-inpainting.ckpt) |
| `sd11_text_encoder_clip_l_fp16.safetensors` | `text_encoders/sd11_text_encoder_clip_l_fp16.safetensors` | 0.23 | creativeml-openrail-m | [stable-diffusion-v1-5/stable-diffusion-v1-5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/text_encoder/model.fp16.safetensors), published as `model.fp16.safetensors` |
| `sd14_text_encoder_clip_l.safetensors` | `text_encoders/sd14_text_encoder_clip_l.safetensors` | 0.46 | creativeml-openrail-m | [Intel/ldm3d-4c](https://huggingface.co/Intel/ldm3d-4c/resolve/main/text_encoder/model.safetensors), published as `model.safetensors` |
| `sd15_diffusers_unet_fp16.safetensors` | `diffusion_models/sd15_diffusers_unet_fp16.safetensors` | 1.60 | creativeml-openrail-m | [stable-diffusion-v1-5/stable-diffusion-v1-5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/unet/diffusion_pytorch_model.fp16.safetensors), published as `diffusion_pytorch_model.fp16.safetensors` |
| `v1-5-pruned-emaonly.safetensors` | `checkpoints/v1-5-pruned-emaonly.safetensors` | 3.97 | creativeml-openrail-m | [Comfy-Org/stable-diffusion-1.5](https://huggingface.co/Comfy-Org/stable-diffusion-1.5/resolve/main/v1-5-pruned-emaonly.safetensors) |
| `qzlino-sd-1-5_sd15_300_steps_79151548790e.safetensors` | `loras/parametric_trained/qzlino-sd-1-5_sd15_300_steps_79151548790e.safetensors` | ? | unknown | Trained with the studio's Train page; not published |
| `qzlino-sd-1-5_sd15_60_steps_245acc80f0ec.safetensors` | `loras/parametric_trained/qzlino-sd-1-5_sd15_60_steps_245acc80f0ec.safetensors` | ? | unknown | Trained with the studio's Train page; not published |

20 files, 24.30 GiB with a known size.

### SD3-SD3.5

Used by: 4 studio templates; 8 family templates; University graphs `studio/university/graphs/sd35_flow`; 8 other graphs; features `sampling_graph`, `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `clip_g.safetensors` | `text_encoders/clip_g.safetensors` | 1.29 | stabilityai-ai-community | [Comfy-Org/stable-diffusion-3.5](https://huggingface.co/Comfy-Org/stable-diffusion-3.5/resolve/main/text_encoders/clip_g.safetensors) |
| `ip-adapter_sd35_large.bin` | `ipadapter/ip-adapter_sd35_large.bin` | 1.49 | stabilityai-ai-community | [InstantX/SD3.5-Large-IP-Adapter](https://huggingface.co/InstantX/SD3.5-Large-IP-Adapter/resolve/main/ip-adapter.bin), published as `ip-adapter.bin` |
| `sd3.5_large.safetensors` | `checkpoints/sd3.5_large.safetensors` | 15.33 | stabilityai-ai-community | [stabilityai/stable-diffusion-3.5-large](https://huggingface.co/stabilityai/stable-diffusion-3.5-large/resolve/main/sd3.5_large.safetensors) (gated) |
| `sd3.5_large_controlnet_blur.safetensors` | `controlnet/sd3.5_large_controlnet_blur.safetensors` | 8.06 | stabilityai-ai-community | [Comfy-Org/stable-diffusion-3.5-controlnets](https://huggingface.co/Comfy-Org/stable-diffusion-3.5-controlnets/resolve/main/split_files/controlnet/sd3.5_large_controlnet_blur.safetensors) |
| `sd3.5_large_controlnet_canny.safetensors` | `controlnet/sd3.5_large_controlnet_canny.safetensors` | 8.06 | stabilityai-ai-community | [Comfy-Org/stable-diffusion-3.5-controlnets](https://huggingface.co/Comfy-Org/stable-diffusion-3.5-controlnets/resolve/main/split_files/controlnet/sd3.5_large_controlnet_canny.safetensors) |
| `sd3.5_large_controlnet_depth.safetensors` | `controlnet/sd3.5_large_controlnet_depth.safetensors` | 8.06 | stabilityai-ai-community | [Comfy-Org/stable-diffusion-3.5-controlnets](https://huggingface.co/Comfy-Org/stable-diffusion-3.5-controlnets/resolve/main/split_files/controlnet/sd3.5_large_controlnet_depth.safetensors) |
| `sd3.5_large_fp8_scaled.safetensors` | `checkpoints/sd3.5_large_fp8_scaled.safetensors` | 13.91 | stabilityai-ai-community | [Comfy-Org/stable-diffusion-3.5](https://huggingface.co/Comfy-Org/stable-diffusion-3.5/resolve/main/sd3.5_large_fp8_scaled.safetensors) |
| `sd3.5_medium.safetensors` | `checkpoints/sd3.5_medium.safetensors` | 4.76 | stabilityai-ai-community | [stabilityai/stable-diffusion-3.5-medium](https://huggingface.co/stabilityai/stable-diffusion-3.5-medium/resolve/main/sd3.5_medium.safetensors) (gated) |
| `sd3_medium.safetensors` | `checkpoints/sd3_medium.safetensors` | 4.04 | stabilityai-ai-community | [stabilityai/stable-diffusion-3-medium](https://huggingface.co/stabilityai/stable-diffusion-3-medium/resolve/main/sd3_medium.safetensors) (gated) |

9 files, 65.00 GiB with a known size.

### SDXL

Used by: 12 studio templates; 16 family templates; University graphs `studio/university/graphs/h5_sdturbo`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `CLIP-VIT-H-LAION.safetensors` | `clip_vision/CLIP-VIT-H-LAION.safetensors` | 3.67 | mit | [laion/CLIP-ViT-H-14-laion2B-s32B-b79K](https://huggingface.co/laion/CLIP-ViT-H-14-laion2B-s32B-b79K/resolve/main/model.safetensors), published as `model.safetensors` |
| `ip-adapter-plus-face_sdxl_vit-h.safetensors` | `ipadapter/ip-adapter-plus-face_sdxl_vit-h.safetensors` | 0.79 | apache-2.0 | [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus-face_sdxl_vit-h.safetensors) |
| `ip-adapter-plus_sdxl_vit-h.safetensors` | `ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors` | 0.79 | apache-2.0 | [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors) |
| `ip-adapter_sdxl.safetensors` | `ipadapter/ip-adapter_sdxl.safetensors` | 0.65 | apache-2.0 | [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter_sdxl.safetensors) |
| `ip-adapter_sdxl_vit-h.safetensors` | `ipadapter/ip-adapter_sdxl_vit-h.safetensors` | 0.65 | apache-2.0 | [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter_sdxl_vit-h.safetensors) |
| `leosamsHelloworldXL_helloworldXL70.safetensors` | `checkpoints/leosamsHelloworldXL_helloworldXL70.safetensors` | 6.46 | not stated on the card | [Maxivi/SDXLModels](https://huggingface.co/Maxivi/SDXLModels/resolve/main/leosamsHelloworldXL_helloworldXL70.safetensors) (community upload) |
| `sd_xl_base_1.0_unet_fp16.safetensors` | `diffusion_models/sd_xl_base_1.0_unet_fp16.safetensors` | 4.78 | openrail++ | [stabilityai/stable-diffusion-xl-base-1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/unet/diffusion_pytorch_model.fp16.safetensors), published as `diffusion_pytorch_model.fp16.safetensors` |
| `sd_xl_refiner_1.0.safetensors` | `checkpoints/sd_xl_refiner_1.0.safetensors` | 5.66 | openrail++ | [stabilityai/stable-diffusion-xl-refiner-1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors) |
| `sd_xl_turbo_1.0_fp16.safetensors` | `checkpoints/sd_xl_turbo_1.0_fp16.safetensors` | 6.46 | sai-nc-community (non-commercial) | [stabilityai/sdxl-turbo](https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors) |
| `sdxl_vae_fp16_fix.safetensors` | `vae/sdxl_vae_fp16_fix.safetensors` | 0.31 | mit | [madebyollin/sdxl-vae-fp16-fix](https://huggingface.co/madebyollin/sdxl-vae-fp16-fix/resolve/main/diffusion_pytorch_model.safetensors), published as `diffusion_pytorch_model.safetensors` |
| `svd_xt.safetensors` | `checkpoints/svd_xt.safetensors` | 8.90 | stable-video-diffusion-community | [stabilityai/stable-video-diffusion-img2vid-xt](https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/resolve/main/svd_xt.safetensors) |
| `xinsir_depth_sdxl.safetensors` | `controlnet/xinsir_depth_sdxl.safetensors` | 2.33 | apache-2.0 | [xinsir/controlnet-depth-sdxl-1.0](https://huggingface.co/xinsir/controlnet-depth-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors), published as `diffusion_pytorch_model.safetensors` |
| `xinsir_openpose_sdxl.safetensors` | `controlnet/xinsir_openpose_sdxl.safetensors` | 2.33 | apache-2.0 | [xinsir/controlnet-openpose-sdxl-1.0](https://huggingface.co/xinsir/controlnet-openpose-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors), published as `diffusion_pytorch_model.safetensors` |
| `xinsir_openpose_sdxl_twins.safetensors` | `controlnet/xinsir_openpose_sdxl_twins.safetensors` | 2.33 | apache-2.0 | [xinsir/controlnet-openpose-sdxl-1.0](https://huggingface.co/xinsir/controlnet-openpose-sdxl-1.0/resolve/main/diffusion_pytorch_model_twins.safetensors), published as `diffusion_pytorch_model_twins.safetensors` |
| `xinsir_scribble_sdxl.safetensors` | `controlnet/xinsir_scribble_sdxl.safetensors` | 2.33 | apache-2.0 | [xinsir/controlnet-canny-sdxl-1.0](https://huggingface.co/xinsir/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model_V2.safetensors), published as `diffusion_pytorch_model_V2.safetensors` |
| `xinsir_tile_sdxl.safetensors` | `controlnet/xinsir_tile_sdxl.safetensors` | 2.33 | apache-2.0 | [xinsir/controlnet-tile-sdxl-1.0](https://huggingface.co/xinsir/controlnet-tile-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors), published as `diffusion_pytorch_model.safetensors` |

16 files, 50.79 GiB with a known size.

### SeedVR2

Used by: family templates `utility_seedvr2_3b_int8_upscale_image`, `utility_seedvr2_3b_int8_upscale_video`, `utility_seedvr2_7b_int8_upscale_image`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `seedvr2_3b_int8_convrot.safetensors` | `diffusion_models/seedvr2_3b_int8_convrot.safetensors` | 3.22 | apache-2.0 | [Comfy-Org/SeedVR2](https://huggingface.co/Comfy-Org/SeedVR2/resolve/main/diffusion_models/seedvr2_3b_int8_convrot.safetensors) |
| `seedvr2_7b_int8_convrot.safetensors` | `diffusion_models/seedvr2_7b_int8_convrot.safetensors` | 7.76 | apache-2.0 | [Comfy-Org/SeedVR2](https://huggingface.co/Comfy-Org/SeedVR2/resolve/main/diffusion_models/seedvr2_7b_int8_convrot.safetensors) |
| `seedvr2_ema_vae_fp16.safetensors` | `vae/seedvr2_ema_vae_fp16.safetensors` | 0.47 | apache-2.0 | [Comfy-Org/SeedVR2](https://huggingface.co/Comfy-Org/SeedVR2/resolve/main/vae/seedvr2_ema_vae_fp16.safetensors) |

3 files, 11.45 GiB with a known size.

### Shared text encoders

Used by: workflows `music_stable_open_api`; Music page `stable_open`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `t5-base.safetensors` | `text_encoders/t5-base.safetensors` | 0.83 | apache-2.0 | [ComfyUI-Wiki/t5-base](https://huggingface.co/ComfyUI-Wiki/t5-base/resolve/main/t5-base.safetensors) (community upload) |

1 files, 0.83 GiB with a known size.

### Stable-Cascade

Used by: studio templates `stable_cascade_core_t2i`; family templates `stable_cascade_core_t2i`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `stable_cascade_stage_b.safetensors` | `checkpoints/stable_cascade_stage_b.safetensors` | 4.24 | stable-cascade-nc-community (non-commercial) | [stabilityai/stable-cascade](https://huggingface.co/stabilityai/stable-cascade/resolve/main/comfyui_checkpoints/stable_cascade_stage_b.safetensors) |
| `stable_cascade_stage_c.safetensors` | `checkpoints/stable_cascade_stage_c.safetensors` | 8.59 | stable-cascade-nc-community (non-commercial) | [stabilityai/stable-cascade](https://huggingface.co/stabilityai/stable-cascade/resolve/main/comfyui_checkpoints/stable_cascade_stage_c.safetensors) |

2 files, 12.83 GiB with a known size.

### SVD

Used by: studio templates `svd_xt_1_1_i2v`; family templates `svd_xt_1_1_i2v`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `svd_xt_1_1.safetensors` | `checkpoints/svd_xt_1_1.safetensors` | 4.45 | stable-video-diffusion-1-1-community | [stabilityai/stable-video-diffusion-img2vid-xt-1-1](https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt-1-1/resolve/main/svd_xt_1_1.safetensors) (gated) |

1 files, 4.45 GiB with a known size.

### TripoSplat

Used by: family templates `3d_triposplat_image_to_gaussian_splat`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `dino_v3_vit_h.safetensors` | `clip_vision/dino_v3_vit_h.safetensors` | 1.57 | mit | [VAST-AI/TripoSplat](https://huggingface.co/VAST-AI/TripoSplat/resolve/main/clip_vision/dino_v3_vit_h.safetensors) |
| `triposplat_fp16.safetensors` | `diffusion_models/triposplat_fp16.safetensors` | 0.69 | mit | [VAST-AI/TripoSplat](https://huggingface.co/VAST-AI/TripoSplat/resolve/main/diffusion_models/triposplat_fp16.safetensors) |
| `triposplat_vae_decoder_fp16.safetensors` | `vae/triposplat_vae_decoder_fp16.safetensors` | 0.54 | mit | [VAST-AI/TripoSplat](https://huggingface.co/VAST-AI/TripoSplat/resolve/main/vae/triposplat_vae_decoder_fp16.safetensors) |

3 files, 2.79 GiB with a known size.

### VLM

Used by: family templates `llm_qwen3_5_text_gen`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `qwen3.5_4b_bf16.safetensors` | `text_encoders/qwen3.5_4b_bf16.safetensors` | 8.68 | apache-2.0 | [Comfy-Org/Qwen3.5](https://huggingface.co/Comfy-Org/Qwen3.5/resolve/main/text_encoders/qwen3.5_4b_bf16.safetensors) |

1 files, 8.68 GiB with a known size.

### Voices

Used by: 54 Voices page.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `af_heart.pt` | `TTS/voices/af_heart.pt` | 0.00 | apache-2.0 | [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/voices/af_heart.pt) |
| `asr/nemotron-speech-streaming-en-0.6b/model.safetensors` | `TTS/asr/nemotron-speech-streaming-en-0.6b/model.safetensors` | 2.30 | nvidia-open-model-license | [nvidia/nemotron-speech-streaming-en-0.6b](https://huggingface.co/nvidia/nemotron-speech-streaming-en-0.6b/resolve/main/model.safetensors) |
| `asr/parakeet-tdt-0.6b-v3/model.safetensors` | `TTS/asr/parakeet-tdt-0.6b-v3/model.safetensors` | 2.34 | cc-by-4.0 | [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3/resolve/main/model.safetensors) |
| `asr/VibeVoice-ASR/model-00008-of-00008.safetensors` | `TTS/asr/VibeVoice-ASR/model-00008-of-00008.safetensors` | 1.02 | mit | [microsoft/VibeVoice-ASR](https://huggingface.co/microsoft/VibeVoice-ASR/resolve/main/model-00008-of-00008.safetensors) |
| `audio_encoders/model.bin` | `audio_encoders/model.bin` | 2.88 | mit | [Systran/faster-whisper-large-v3](https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/model.bin) |
| `audiosr_speech_fp32.safetensors` | `TTS/AudioSR/audiosr_speech_fp32.safetensors` | 5.75 | mit | [drbaph/AudioSR](https://huggingface.co/drbaph/AudioSR/resolve/main/AudioSR/audiosr_speech_fp32.safetensors) |
| `audiovae.pth` | `TTS/voxcpm2/audiovae.pth` | 0.35 | apache-2.0 | [openbmb/VoxCPM2](https://huggingface.co/openbmb/VoxCPM2/resolve/main/audiovae.pth) |
| `campplus.onnx` | `TTS/step_audio_editx/Step-Audio-EditX/CosyVoice-300M-25Hz/campplus.onnx` | 0.03 | not stated on the card | [stepfun-ai/Step-Audio-EditX](https://huggingface.co/stepfun-ai/Step-Audio-EditX/resolve/main/CosyVoice-300M-25Hz/campplus.onnx) |
| `campplus_voxceleb.bin` | `TTS/tts/FireRedTTS3/campp/campplus_voxceleb.bin` | 0.03 | apache-2.0 | [FireRedTeam/FireRedTTS3](https://huggingface.co/FireRedTeam/FireRedTTS3/resolve/main/campp/campplus_voxceleb.bin) |
| `chunk.onnx` | `TTS/speech_enhancement/voxlock/onnx/chunk.onnx` | 0.08 | apache-2.0 | [arbazsiddiqui/voxlock](https://huggingface.co/arbazsiddiqui/voxlock/resolve/main/onnx/chunk.onnx) (community upload) |
| `chunk_fp16.onnx` | `TTS/speech_enhancement/voxlock/onnx/chunk_fp16.onnx` | 0.04 | apache-2.0 | [arbazsiddiqui/voxlock](https://huggingface.co/arbazsiddiqui/voxlock/resolve/main/onnx/chunk_fp16.onnx) (community upload) |
| `chunk_int8.onnx` | `TTS/speech_enhancement/voxlock/onnx/chunk_int8.onnx` | 0.06 | apache-2.0 | [arbazsiddiqui/voxlock](https://huggingface.co/arbazsiddiqui/voxlock/resolve/main/onnx/chunk_int8.onnx) (community upload) |
| `chunk_int8_full.onnx` | `TTS/speech_enhancement/voxlock/onnx/chunk_int8_full.onnx` | 0.05 | apache-2.0 | [arbazsiddiqui/voxlock](https://huggingface.co/arbazsiddiqui/voxlock/resolve/main/onnx/chunk_int8_full.onnx) (community upload) |
| `coarse.pt` | `TTS/suno__bark/coarse.pt` | 1.17 | mit | [suno/bark](https://huggingface.co/suno/bark/resolve/main/coarse.pt) |
| `duration_predictor.onnx` | `TTS/supertonic-3/onnx/duration_predictor.onnx` | 0.00 | openrail | [Supertone/supertonic-3](https://huggingface.co/Supertone/supertonic-3/resolve/main/onnx/duration_predictor.onnx) |
| `dvae.pth` | `TTS/xtts/XTTS-v2/dvae.pth` | 0.20 | coqui-public-model-license | [coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2/resolve/main/dvae.pth) |
| `enroll.onnx` | `TTS/speech_enhancement/voxlock/onnx/enroll.onnx` | 0.01 | apache-2.0 | [arbazsiddiqui/voxlock](https://huggingface.co/arbazsiddiqui/voxlock/resolve/main/onnx/enroll.onnx) (community upload) |
| `faster-distil-whisper-large-v3/model.bin` | `TTS/faster-distil-whisper-large-v3/model.bin` | 1.41 | mit | [Systran/faster-distil-whisper-large-v3](https://huggingface.co/Systran/faster-distil-whisper-large-v3/resolve/main/model.bin) |
| `faster-whisper-tiny/model.bin` | `TTS/faster-whisper-tiny/model.bin` | 0.07 | mit | [Systran/faster-whisper-tiny](https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/model.bin) |
| `fine.pt` | `TTS/suno__bark/fine.pt` | 1.03 | mit | [suno/bark](https://huggingface.co/suno/bark/resolve/main/fine.pt) |
| `flow.pt` | `TTS/glm_tts/flow/flow.pt` | 0.57 | not stated on the card | [stepfun-ai/Step-Audio-EditX](https://huggingface.co/stepfun-ai/Step-Audio-EditX/resolve/main/CosyVoice-300M-25Hz/flow.pt) |
| `generator_jit.ckpt` | `TTS/glm_tts/vocos2d/generator_jit.ckpt` | 0.06 | mit | [zai-org/GLM-TTS](https://huggingface.co/zai-org/GLM-TTS/resolve/main/vocos2d/generator_jit.ckpt) |
| `german-HuBERT-quantizer_14_epoch.pth` | `TTS/CountFloyd__bark-voice-cloning-german-HuBERT-quantizer/german-HuBERT-quantizer_14_epoch.pth` | 0.23 | not stated on the card | [CountFloyd/bark-voice-cloning-german-HuBERT-quantizer](https://huggingface.co/CountFloyd/bark-voice-cloning-german-HuBERT-quantizer/resolve/main/german-HuBERT-quantizer_14_epoch.pth) (community upload) |
| `hift.pt` | `TTS/step_audio_editx/Step-Audio-EditX/CosyVoice-300M-25Hz/hift.pt` | 0.08 | not stated on the card | [stepfun-ai/Step-Audio-EditX](https://huggingface.co/stepfun-ai/Step-Audio-EditX/resolve/main/CosyVoice-300M-25Hz/hift.pt) |
| `higgs-audio-v2-tokenizer/model.safetensors` | `TTS/higgs-audio-v2-tokenizer/model.safetensors` | 0.75 | other | [bosonai/higgs-audio-v2-tokenizer](https://huggingface.co/bosonai/higgs-audio-v2-tokenizer/resolve/main/model.safetensors) (community upload) |
| `Humaneness-Voice-Converter/conditioning/ears-medium/medium/model.safetensors` | `TTS/Humaneness-Voice-Converter/conditioning/ears-medium/medium/model.safetensors` | 0.36 | cc-by-4.0 | [laion/Humaneness-Voice-Converter](https://huggingface.co/laion/Humaneness-Voice-Converter/resolve/main/conditioning/ears-medium/medium/model.safetensors) |
| `Humaneness-Voice-Converter/model.safetensors` | `TTS/Humaneness-Voice-Converter/model.safetensors` | 0.98 | cc-by-4.0 | [laion/Humaneness-Voice-Converter](https://huggingface.co/laion/Humaneness-Voice-Converter/resolve/main/model.safetensors) |
| `indextts-2.5/qwen0.6bemo4-merge/model.safetensors` | `TTS/indextts-2.5/qwen0.6bemo4-merge/model.safetensors` | 1.11 | not stated on the card | [IndexTeam/IndexTTS-2](https://huggingface.co/IndexTeam/IndexTTS-2/resolve/main/qwen0.6bemo4-merge/model.safetensors) |
| `japanese-HuBERT-quantizer_24_epoch.pth` | `TTS/tts/bark-voice-cloning-japanese-HuBERT-quantizer/japanese-HuBERT-quantizer_24_epoch.pth` | 0.23 | not stated on the card | [junwchina/bark-voice-cloning-japanese-HuBERT-quantizer](https://huggingface.co/junwchina/bark-voice-cloning-japanese-HuBERT-quantizer/resolve/main/japanese-HuBERT-quantizer_24_epoch.pth) (community upload) |
| `Kokoro-82M-v1.0-ONNX-fp16/model.onnx` | `TTS/Kokoro-82M-v1.0-ONNX-fp16/model.onnx` | 0.17 | not stated on the card | [speaches-ai/Kokoro-82M-v1.0-ONNX-fp16](https://huggingface.co/speaches-ai/Kokoro-82M-v1.0-ONNX-fp16/resolve/main/model.onnx) (community upload) |
| `kokoro-v1_0.pth` | `TTS/kokoro-v1_0.pth` | 0.30 | apache-2.0 | [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/kokoro-v1_0.pth) |
| `last_best_checkpoint.pt` | `checkpoints/speech_enhancement/ClearerVoice-Studio/clearvoice/checkpoints/AV_MossFormer2_TSE_16K/last_best_checkpoint.pt` | 0.21 | apache-2.0 | [alibabasglab/MossFormer2_SE_48K](https://huggingface.co/alibabasglab/MossFormer2_SE_48K/resolve/main/last_best_checkpoint.pt) |
| `last_best_checkpoint_g.pt` | `checkpoints/speech_enhancement/ClearerVoice-Studio/clearvoice/checkpoints/MossFormer2_SR_48K/last_best_checkpoint_g.pt` | 0.21 | apache-2.0 | [alibabasglab/MossFormer2_SR_48K](https://huggingface.co/alibabasglab/MossFormer2_SR_48K/resolve/main/last_best_checkpoint_g.pt) |
| `last_best_checkpoint_m.pt` | `checkpoints/speech_enhancement/ClearerVoice-Studio/clearvoice/checkpoints/MossFormer2_SR_48K/last_best_checkpoint_m.pt` | 0.20 | apache-2.0 | [alibabasglab/MossFormer2_SR_48K](https://huggingface.co/alibabasglab/MossFormer2_SR_48K/resolve/main/last_best_checkpoint_m.pt) |
| `LuxTTS/model.pt` | `TTS/LuxTTS/model.pt` | 0.46 | apache-2.0 | [YatharthS/LuxTTS](https://huggingface.co/YatharthS/LuxTTS/resolve/main/model.pt) (community upload) |
| `maya1-TTS/maya1/model-00001-of-00002.safetensors` | `TTS/maya1-TTS/maya1/model-00001-of-00002.safetensors` | 4.65 | apache-2.0 | [maya-research/maya1](https://huggingface.co/maya-research/maya1/resolve/main/model-00001-of-00002.safetensors) |
| `maya1-TTS/maya1/model-00002-of-00002.safetensors` | `TTS/maya1-TTS/maya1/model-00002-of-00002.safetensors` | 1.50 | apache-2.0 | [maya-research/maya1](https://huggingface.co/maya-research/maya1/resolve/main/model-00002-of-00002.safetensors) |
| `ming3_tts_tiny_int8_convrot.safetensors` | `TTS/ming3/ming3_tts_tiny_int8_convrot.safetensors` | 8.45 | mit | [Comfy-Org/Ming-3.0-TTS](https://huggingface.co/Comfy-Org/Ming-3.0-TTS/resolve/main/checkpoints/ming3_tts_tiny_int8_convrot.safetensors) |
| `model_1250000.safetensors` | `TTS/F5-TTS/F5TTS_v1_Base/model_1250000.safetensors` | 1.26 | cc-by-nc-4.0 (non-commercial) | [SWivid/F5-TTS](https://huggingface.co/SWivid/F5-TTS/resolve/main/F5TTS_v1_Base/model_1250000.safetensors) |
| `model_only_last.ckpt` | `TTS/megatts3/diffusion_transformer/model_only_last.ckpt` | 0.20 | apache-2.0 | [ByteDance/MegaTTS3](https://huggingface.co/ByteDance/MegaTTS3/resolve/main/aligner_lm/model_only_last.ckpt) |
| `musetalk/whisper-tiny/model.safetensors` | `TTS/musetalk/whisper-tiny/model.safetensors` | 0.14 | apache-2.0 | [openai/whisper-tiny](https://huggingface.co/openai/whisper-tiny/resolve/main/model.safetensors) |
| `OmniVoice/model.safetensors` | `TTS/OmniVoice/model.safetensors` | 2.28 | not stated on the card | [k2-fsa/OmniVoice](https://huggingface.co/k2-fsa/OmniVoice/resolve/main/model.safetensors) |
| `paradee.onnx` | `TTS/paradee-8m-v1.1/onnx/paradee.onnx` | 0.03 | apache-2.0 | [sahilmahendrakar/Paradee-8M-v1.1](https://huggingface.co/sahilmahendrakar/Paradee-8M-v1.1/resolve/main/onnx/paradee.onnx) (community upload) |
| `parakeet-ultra/model.safetensors` | `TTS/parakeet-ultra/model.safetensors` | 1.17 | cc-by-4.0 | [moondream/parakeet-ultra](https://huggingface.co/moondream/parakeet-ultra/resolve/main/model.safetensors) (community upload) |
| `polish-HuBERT-quantizer_8_epoch.pth` | `TTS/Hobis__bark-voice-cloning-polish-HuBERT-quantizer/polish-HuBERT-quantizer_8_epoch.pth` | 0.23 | not stated on the card | [Hobis/bark-voice-cloning-polish-HuBERT-quantizer](https://huggingface.co/Hobis/bark-voice-cloning-polish-HuBERT-quantizer/resolve/main/polish-HuBERT-quantizer_8_epoch.pth) (community upload) |
| `portuguese-HuBERT-quantizer_24_epoch.pth` | `audio/MadVoyager__bark-voice-cloning-portuguese-HuBERT-quantizer/portuguese-HuBERT-quantizer_24_epoch.pth` | 0.23 | not stated on the card | [MadVoyager/bark-voice-cloning-portuguese-HuBERT-quantizer](https://huggingface.co/MadVoyager/bark-voice-cloning-portuguese-HuBERT-quantizer/resolve/main/portuguese-HuBERT-quantizer_24_epoch.pth) (community upload) |
| `quantifier_V1_hubert_base_ls960_23.pth` | `TTS/GitMylo__bark-voice-cloning/quantifier_V1_hubert_base_ls960_23.pth` | 0.23 | mit | [GitMylo/bark-voice-cloning](https://huggingface.co/GitMylo/bark-voice-cloning/resolve/main/quantifier_V1_hubert_base_ls960_23.pth) (community upload) |
| `qwen3_tts/model.safetensors` | `TTS/qwen3_tts/model.safetensors` | 3.57 | apache-2.0 | [Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/resolve/main/model.safetensors) |
| `qwen3_tts/speech_tokenizer/model.safetensors` | `TTS/qwen3_tts/speech_tokenizer/model.safetensors` | 0.64 | apache-2.0 | [Qwen/Qwen3-TTS-12Hz-0.6B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base/resolve/main/speech_tokenizer/model.safetensors) |
| `ResNet293_SimAM_ASP_base.pt` | `TTS/zonos/Zonos-v0.1-speaker-embedding/ResNet293_SimAM_ASP_base.pt` | 0.37 | apache-2.0 | [Zyphra/Zonos-v0.1-speaker-embedding](https://huggingface.co/Zyphra/Zonos-v0.1-speaker-embedding/resolve/main/ResNet293_SimAM_ASP_base.pt) |
| `soulx_singer/preprocessors/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/model.pt` | `TTS/soulx_singer/preprocessors/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/model.pt` | 0.92 | apache-2.0 | [Soul-AILab/SoulX-Singer-Preprocess](https://huggingface.co/Soul-AILab/SoulX-Singer-Preprocess/resolve/main/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/model.pt) |
| `speech_tokenizer_v1.onnx` | `TTS/step_audio_editx/Step-Audio-EditX/CosyVoice-300M-25Hz/speech_tokenizer_v1.onnx` | 0.49 | not stated on the card | [stepfun-ai/Step-Audio-EditX](https://huggingface.co/stepfun-ai/Step-Audio-EditX/resolve/main/CosyVoice-300M-25Hz/speech_tokenizer_v1.onnx) |
| `tiny.pt` | `TTS/video_cont/latentsync/whisper/tiny.pt` | 0.07 | openrail++ | [ByteDance/LatentSync-1.6](https://huggingface.co/ByteDance/LatentSync-1.6/resolve/main/whisper/tiny.pt) |
| `transformers/granite-speech-5.0-470m-turboctc/model.safetensors` | `TTS/transformers/granite-speech-5.0-470m-turboctc/model.safetensors` | 0.88 | apache-2.0 | [ibm-granite/granite-speech-5.0-470m-turboctc](https://huggingface.co/ibm-granite/granite-speech-5.0-470m-turboctc/resolve/main/model.safetensors) |
| `TTS/bark/pytorch_model.bin` | `TTS/bark/pytorch_model.bin` | 4.18 | mit | [suno/bark](https://huggingface.co/suno/bark/resolve/main/pytorch_model.bin) |
| `TTS/chatterbox/English/s3gen.pt` | `TTS/chatterbox/English/s3gen.pt` | 0.98 | mit | [ResembleAI/chatterbox](https://huggingface.co/ResembleAI/chatterbox/resolve/main/s3gen.pt) |
| `TTS/chatterbox/English/t3_cfg.pt` | `TTS/chatterbox/English/t3_cfg.pt` | 0.99 | mit | [ResembleAI/chatterbox](https://huggingface.co/ResembleAI/chatterbox/resolve/main/t3_cfg.pt) |
| `TTS/chatterbox/English/ve.pt` | `TTS/chatterbox/English/ve.pt` | 0.01 | mit | [ResembleAI/chatterbox](https://huggingface.co/ResembleAI/chatterbox/resolve/main/ve.pt) |
| `TTS/F5-TTS/vocos/pytorch_model.bin` | `TTS/F5-TTS/vocos/pytorch_model.bin` | 0.05 | mit | [charactr/vocos-mel-24khz](https://huggingface.co/charactr/vocos-mel-24khz/resolve/main/pytorch_model.bin) (community upload) |
| `tts/FireRedTTS3/fireredtts3_base/model.safetensors` | `TTS/tts/FireRedTTS3/fireredtts3_base/model.safetensors` | 7.90 | apache-2.0 | [FireRedTeam/FireRedTTS3](https://huggingface.co/FireRedTeam/FireRedTTS3/resolve/main/fireredtts3_base/model.safetensors) |
| `tts/FireRedTTS3/fireredtts3_instruct/model.safetensors` | `TTS/tts/FireRedTTS3/fireredtts3_instruct/model.safetensors` | 7.89 | apache-2.0 | [FireRedTeam/FireRedTTS3](https://huggingface.co/FireRedTeam/FireRedTTS3/resolve/main/fireredtts3_instruct/model.safetensors) |
| `tts/FireRedTTS3/redae/model.safetensors` | `TTS/tts/FireRedTTS3/redae/model.safetensors` | 3.52 | apache-2.0 | [FireRedTeam/FireRedTTS3](https://huggingface.co/FireRedTeam/FireRedTTS3/resolve/main/redae/model.safetensors) |
| `TTS/glm_tts/llm/model-00002-of-00002.safetensors` | `TTS/glm_tts/llm/model-00002-of-00002.safetensors` | 1.13 | mit | [zai-org/GLM-TTS](https://huggingface.co/zai-org/GLM-TTS/resolve/main/llm/model-00002-of-00002.safetensors) |
| `TTS/glm_tts/speech_tokenizer/model.safetensors` | `TTS/glm_tts/speech_tokenizer/model.safetensors` | 1.52 | mit | [zai-org/GLM-TTS](https://huggingface.co/zai-org/GLM-TTS/resolve/main/speech_tokenizer/model.safetensors) |
| `TTS/neucodec/model.safetensors` | `TTS/neucodec/model.safetensors` | 2.35 | apache-2.0 | [neuphonic/neucodec](https://huggingface.co/neuphonic/neucodec/resolve/main/model.safetensors) (gated) |
| `TTS/phonon/phonon-31m-en/model.safetensors` | `TTS/phonon/phonon-31m-en/model.safetensors` | 0.10 | apache-2.0 | [gradium/phonon-31m-en](https://huggingface.co/gradium/phonon-31m-en/resolve/main/model.safetensors) |
| `TTS/phonon/phonon-40m-multilingual/model.safetensors` | `TTS/phonon/phonon-40m-multilingual/model.safetensors` | 0.11 | cc-by-nc-4.0 (non-commercial) | [gradium/phonon-40m-multilingual](https://huggingface.co/gradium/phonon-40m-multilingual/resolve/main/model.safetensors) (gated) |
| `TTS/phonon/phonon-mimi/model.safetensors` | `TTS/phonon/phonon-mimi/model.safetensors` | 0.04 | apache-2.0 | [gradium/phonon-mimi](https://huggingface.co/gradium/phonon-mimi/resolve/main/model.safetensors) |
| `TTS/qwen3_tts/asr/Qwen3-ASR-1.7B-hf/model.safetensors` | `TTS/qwen3_tts/asr/Qwen3-ASR-1.7B-hf/model.safetensors` | 3.80 | apache-2.0 | [Qwen/Qwen3-ASR-1.7B-hf](https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf/resolve/main/model.safetensors) |
| `TTS/qwen3_tts/Qwen3-TTS-12Hz-0.6B-Base/model.safetensors` | `TTS/qwen3_tts/Qwen3-TTS-12Hz-0.6B-Base/model.safetensors` | 1.70 | apache-2.0 | [Qwen/Qwen3-TTS-12Hz-0.6B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base/resolve/main/model.safetensors) |
| `TTS/qwen3_tts/Qwen3-TTS-12Hz-0.6B-CustomVoice/model.safetensors` | `TTS/qwen3_tts/Qwen3-TTS-12Hz-0.6B-CustomVoice/model.safetensors` | 1.69 | apache-2.0 | [Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice/resolve/main/model.safetensors) |
| `TTS/qwen3_tts/Qwen3-TTS-12Hz-1.7B-Base/model.safetensors` | `TTS/qwen3_tts/Qwen3-TTS-12Hz-1.7B-Base/model.safetensors` | 3.59 | apache-2.0 | [Qwen/Qwen3-TTS-12Hz-1.7B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base/resolve/main/model.safetensors) |
| `TTS/qwen3_tts/Qwen3-TTS-12Hz-1.7B-VoiceDesign/model.safetensors` | `TTS/qwen3_tts/Qwen3-TTS-12Hz-1.7B-VoiceDesign/model.safetensors` | 3.57 | apache-2.0 | [Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign/resolve/main/model.safetensors) |
| `TTS/rubato-codec/model.safetensors` | `TTS/rubato-codec/model.safetensors` | 0.92 | apache-2.0 | [third-intelligence/RubatoCodec](https://huggingface.co/third-intelligence/RubatoCodec/resolve/main/model.safetensors) (community upload) |
| `TTS/step_audio_editx/Step-Audio-EditX/model-00001.safetensors` | `TTS/step_audio_editx/Step-Audio-EditX/model-00001.safetensors` | 6.57 | not stated on the card | [stepfun-ai/Step-Audio-EditX](https://huggingface.co/stepfun-ai/Step-Audio-EditX/resolve/main/model-00001.safetensors) |
| `TTS/VibeVoice/VibeVoice-1.5B/model-00001-of-00003.safetensors` | `TTS/VibeVoice/VibeVoice-1.5B/model-00001-of-00003.safetensors` | 1.84 | mit | [microsoft/VibeVoice-1.5B](https://huggingface.co/microsoft/VibeVoice-1.5B/resolve/main/model-00001-of-00003.safetensors) |
| `TTS/VibeVoice/VibeVoice-1.5B/model-00002-of-00003.safetensors` | `TTS/VibeVoice/VibeVoice-1.5B/model-00002-of-00003.safetensors` | 1.85 | mit | [microsoft/VibeVoice-1.5B](https://huggingface.co/microsoft/VibeVoice-1.5B/resolve/main/model-00002-of-00003.safetensors) |
| `TTS/VibeVoice/VibeVoice-1.5B/model-00003-of-00003.safetensors` | `TTS/VibeVoice/VibeVoice-1.5B/model-00003-of-00003.safetensors` | 1.35 | mit | [microsoft/VibeVoice-1.5B](https://huggingface.co/microsoft/VibeVoice-1.5B/resolve/main/model-00003-of-00003.safetensors) |
| `TTS/VibeVoice/VibeVoice-Large/model-00001-of-00010.safetensors` | `TTS/VibeVoice/VibeVoice-Large/model-00001-of-00010.safetensors` | 1.76 | mit | [aoi-ot/VibeVoice-Large](https://huggingface.co/aoi-ot/VibeVoice-Large/resolve/main/model-00001-of-00010.safetensors) (community upload) |
| `TTS/VibeVoice/VibeVoice-Large/model-00002-of-00010.safetensors` | `TTS/VibeVoice/VibeVoice-Large/model-00002-of-00010.safetensors` | 1.74 | mit | [aoi-ot/VibeVoice-Large](https://huggingface.co/aoi-ot/VibeVoice-Large/resolve/main/model-00002-of-00010.safetensors) (community upload) |
| `TTS/VibeVoice/VibeVoice-Large/model-00003-of-00010.safetensors` | `TTS/VibeVoice/VibeVoice-Large/model-00003-of-00010.safetensors` | 1.74 | mit | [aoi-ot/VibeVoice-Large](https://huggingface.co/aoi-ot/VibeVoice-Large/resolve/main/model-00003-of-00010.safetensors) (community upload) |
| `TTS/VibeVoice/VibeVoice-Large/model-00004-of-00010.safetensors` | `TTS/VibeVoice/VibeVoice-Large/model-00004-of-00010.safetensors` | 1.74 | mit | [aoi-ot/VibeVoice-Large](https://huggingface.co/aoi-ot/VibeVoice-Large/resolve/main/model-00004-of-00010.safetensors) (community upload) |
| `TTS/VibeVoice/VibeVoice-Large/model-00005-of-00010.safetensors` | `TTS/VibeVoice/VibeVoice-Large/model-00005-of-00010.safetensors` | 1.74 | mit | [aoi-ot/VibeVoice-Large](https://huggingface.co/aoi-ot/VibeVoice-Large/resolve/main/model-00005-of-00010.safetensors) (community upload) |
| `TTS/VibeVoice/VibeVoice-Large/model-00006-of-00010.safetensors` | `TTS/VibeVoice/VibeVoice-Large/model-00006-of-00010.safetensors` | 1.74 | mit | [aoi-ot/VibeVoice-Large](https://huggingface.co/aoi-ot/VibeVoice-Large/resolve/main/model-00006-of-00010.safetensors) (community upload) |
| `TTS/VibeVoice/VibeVoice-Large/model-00007-of-00010.safetensors` | `TTS/VibeVoice/VibeVoice-Large/model-00007-of-00010.safetensors` | 1.74 | mit | [aoi-ot/VibeVoice-Large](https://huggingface.co/aoi-ot/VibeVoice-Large/resolve/main/model-00007-of-00010.safetensors) (community upload) |
| `TTS/VibeVoice/VibeVoice-Large/model-00008-of-00010.safetensors` | `TTS/VibeVoice/VibeVoice-Large/model-00008-of-00010.safetensors` | 1.84 | mit | [aoi-ot/VibeVoice-Large](https://huggingface.co/aoi-ot/VibeVoice-Large/resolve/main/model-00008-of-00010.safetensors) (community upload) |
| `TTS/VibeVoice/VibeVoice-Large/model-00009-of-00010.safetensors` | `TTS/VibeVoice/VibeVoice-Large/model-00009-of-00010.safetensors` | 1.83 | mit | [aoi-ot/VibeVoice-Large](https://huggingface.co/aoi-ot/VibeVoice-Large/resolve/main/model-00009-of-00010.safetensors) (community upload) |
| `TTS/VibeVoice/VibeVoice-Large/model-00010-of-00010.safetensors` | `TTS/VibeVoice/VibeVoice-Large/model-00010-of-00010.safetensors` | 1.57 | mit | [aoi-ot/VibeVoice-Large](https://huggingface.co/aoi-ot/VibeVoice-Large/resolve/main/model-00010-of-00010.safetensors) (community upload) |
| `TTS/voxcpm2/model.safetensors` | `TTS/voxcpm2/model.safetensors` | 4.27 | apache-2.0 | [openbmb/VoxCPM2](https://huggingface.co/openbmb/VoxCPM2/resolve/main/model.safetensors) |
| `TTS/zonos/Zonos-v0.1-transformer/model.safetensors` | `TTS/zonos/Zonos-v0.1-transformer/model.safetensors` | 3.03 | apache-2.0 | [Zyphra/Zonos-v0.1-transformer](https://huggingface.co/Zyphra/Zonos-v0.1-transformer/resolve/main/model.safetensors) |
| `turkish_model_epoch_14.pth` | `TTS/turkish-HuBERT-quantizer/turkish_model_epoch_14.pth` | 0.23 | not stated on the card | [egeadam/bark-voice-cloning-turkish-HuBERT-quantizer](https://huggingface.co/egeadam/bark-voice-cloning-turkish-HuBERT-quantizer/resolve/main/turkish_model_epoch_14.pth) (community upload) |
| `vector_estimator.onnx` | `TTS/supertonic-3/onnx/vector_estimator.onnx` | 0.24 | openrail | [Supertone/supertonic-3](https://huggingface.co/Supertone/supertonic-3/resolve/main/onnx/vector_estimator.onnx) |
| `vocoder.onnx` | `TTS/supertonic-3/onnx/vocoder.onnx` | 0.09 | openrail | [Supertone/supertonic-3](https://huggingface.co/Supertone/supertonic-3/resolve/main/onnx/vocoder.onnx) |
| `vocos.bin` | `TTS/vocoder/vocos.bin` | 0.06 | apache-2.0 | [YatharthS/LuxTTS](https://huggingface.co/YatharthS/LuxTTS/resolve/main/vocoder/vocos.bin) (community upload) |
| `TTS/chatterbox/English/conds.pt` | `TTS/chatterbox/English/conds.pt` | ? | unknown | No public source found |

95 files, 134.97 GiB with a known size.

### Wan-SCAIL-2

Used by: 4 studio templates; 19 family templates; LoRA recipes `lora_8c20f25860`, `lora_bea7f6548a`; features `feature_motion`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `clip_vision_h.safetensors` | `clip_vision/clip_vision_h.safetensors` | 1.18 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/clip_vision/clip_vision_h.safetensors) |
| `lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors` | `loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors` | 0.69 | apache-2.0 | [Comfy-Org/Wan-Animate-2](https://huggingface.co/Comfy-Org/Wan-Animate-2/resolve/main/loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors) |
| `wan2.1_14B_SCAIL_2_fp16.safetensors` | `diffusion_models/wan2.1_14B_SCAIL_2_fp16.safetensors` | 30.54 | mit | [Comfy-Org/SCAIL-2](https://huggingface.co/Comfy-Org/SCAIL-2/resolve/main/diffusion_models/wan2.1_14B_SCAIL_2_fp16.safetensors) |
| `wan2.1_14B_SCAIL_2_int8_convrot.safetensors` | `diffusion_models/wan2.1_14B_SCAIL_2_int8_convrot.safetensors` | 15.51 | mit | [Comfy-Org/SCAIL-2](https://huggingface.co/Comfy-Org/SCAIL-2/resolve/main/diffusion_models/wan2.1_14B_SCAIL_2_int8_convrot.safetensors) |
| `wan2.1_14B_SCAIL_2_nvfp4_mxpf8_mix.safetensors` | `diffusion_models/wan2.1_14B_SCAIL_2_nvfp4_mxpf8_mix.safetensors` | 10.27 | mit | [Comfy-Org/SCAIL-2](https://huggingface.co/Comfy-Org/SCAIL-2/resolve/main/diffusion_models/wan2.1_14B_SCAIL_2_nvfp4_mxpf8_mix.safetensors) |
| `wan2.1_SCAIL_2_DPO_lora_bf16.safetensors` | `loras/wan2.1_SCAIL_2_DPO_lora_bf16.safetensors` | 1.14 | mit | [Comfy-Org/SCAIL-2](https://huggingface.co/Comfy-Org/SCAIL-2/resolve/main/loras/wan2.1_SCAIL_2_DPO_lora_bf16.safetensors) |

6 files, 59.33 GiB with a known size.

### Wan2.1

Used by: 5 studio templates; 21 family templates; 5 LoRA recipes; features `feature_motion`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `causal_forcing-framewise.safetensors` | `diffusion_models/causal_forcing-framewise.safetensors` | 5.29 | apache-2.0 | [Comfy-Org/Causal-Forcing-Framewise](https://huggingface.co/Comfy-Org/Causal-Forcing-Framewise/resolve/main/split_files/diffusion_models/causal_forcing-framewise.safetensors) |
| `chrono_edit_14B_fp16.safetensors` | `diffusion_models/chrono_edit_14B_fp16.safetensors` | 30.54 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/chrono_edit_14B_fp16.safetensors) |
| `chronoedit_distill_lora.safetensors` | `loras/chronoedit_distill_lora.safetensors` | 0.35 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/loras/chronoedit_distill_lora.safetensors) |
| `lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors` | `loras/lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors` | 0.59 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors) |
| `umt5_xxl_fp16.safetensors` | `text_encoders/umt5_xxl_fp16.safetensors` | 10.59 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/text_encoders/umt5_xxl_fp16.safetensors) |
| `wan2.1_flf2v_720p_14B_fp16.safetensors` | `diffusion_models/wan2.1_flf2v_720p_14B_fp16.safetensors` | 30.54 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_flf2v_720p_14B_fp16.safetensors) |
| `wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors` | `diffusion_models/wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors` | 3.01 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors) |
| `wan2.1_fun_camera_v1.1_14B_bf16.safetensors` | `diffusion_models/wan2.1_fun_camera_v1.1_14B_bf16.safetensors` | 31.48 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_fun_camera_v1.1_14B_bf16.safetensors) |
| `wan2.1_fun_control_1.3B_bf16.safetensors` | `diffusion_models/wan2.1_fun_control_1.3B_bf16.safetensors` | 2.91 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_fun_control_1.3B_bf16.safetensors) |
| `wan2.1_fun_inp_1.3B_bf16.safetensors` | `diffusion_models/wan2.1_fun_inp_1.3B_bf16.safetensors` | 2.91 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_fun_inp_1.3B_bf16.safetensors) |
| `wan2.1_i2v_480p_14B_fp16.safetensors` | `diffusion_models/wan2.1_i2v_480p_14B_fp16.safetensors` | 30.54 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_i2v_480p_14B_fp16.safetensors) |
| `wan2.1_i2v_480p_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.1_i2v_480p_14B_fp8_scaled.safetensors` | 15.27 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_i2v_480p_14B_fp8_scaled.safetensors) |
| `wan2.1_t2v_1.3B_fp16.safetensors` | `diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors` | 2.64 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors) |
| `wan2.1_t2v_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.1_t2v_14B_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_t2v_14B_fp8_scaled.safetensors) |
| `wan2.1_vace_1.3B_fp16.safetensors` | `diffusion_models/wan2.1_vace_1.3B_fp16.safetensors` | 4.01 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_vace_1.3B_fp16.safetensors) |
| `wan2.1_vace_14B_fp16.safetensors` | `diffusion_models/wan2.1_vace_14B_fp16.safetensors` | 32.29 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/diffusion_models/wan2.1_vace_14B_fp16.safetensors) |
| `Wan21-WanMove_fp8_scaled_e4m3fn_KJ.safetensors` | `diffusion_models/Wan21-WanMove_fp8_scaled_e4m3fn_KJ.safetensors` | 15.28 | apache-2.0 | [Kijai/WanVideo_comfy_fp8_scaled](https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/WanMove/Wan21-WanMove_fp8_scaled_e4m3fn_KJ.safetensors) |
| `Wan21_CausVid_14B_T2V_lora_rank32.safetensors` | `loras/Wan21_CausVid_14B_T2V_lora_rank32.safetensors` | 0.30 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan21_CausVid_14B_T2V_lora_rank32.safetensors) |
| `Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors` | `loras/Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors` | 0.08 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors) |
| `Wan2_1-I2V-ATI-14B_fp8_e4m3fn.safetensors` | `diffusion_models/Wan2_1-I2V-ATI-14B_fp8_e4m3fn.safetensors` | 15.96 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-ATI-14B_fp8_e4m3fn.safetensors) |
| `wan_alpha_2.1_rgba_lora.safetensors` | `loras/wan_alpha_2.1_rgba_lora.safetensors` | 0.29 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/loras/wan_alpha_2.1_rgba_lora.safetensors) |
| `wan_alpha_2.1_vae_alpha_channel.safetensors` | `vae/wan_alpha_2.1_vae_alpha_channel.safetensors` | 0.24 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/vae/wan_alpha_2.1_vae_alpha_channel.safetensors) |
| `wan_alpha_2.1_vae_rgb_channel.safetensors` | `vae/wan_alpha_2.1_vae_rgb_channel.safetensors` | 0.24 | apache-2.0 | [Comfy-Org/Wan-2.1](https://huggingface.co/Comfy-Org/Wan-2.1/resolve/main/split_files/vae/wan_alpha_2.1_vae_rgb_channel.safetensors) |
| `wav2vec2-chinese-base_fp16.safetensors` | `audio_encoders/wav2vec2-chinese-base_fp16.safetensors` | 0.18 | mit | [Kijai/wav2vec2_safetensors](https://huggingface.co/Kijai/wav2vec2_safetensors/resolve/main/wav2vec2-chinese-base_fp16.safetensors) |
| `wan2.1_infinitetalk_single_fp16_from_kj.safetensors` | `model_patches/wan2.1_infinitetalk_single_fp16_from_kj.safetensors` | ? | unknown | No public source found |

25 files, 248.84 GiB with a known size.

### Wan2.2

Used by: goals `reshoot_wan`; workflows `campath_wan_api`, `vset_wan22_funcontrol_api`, `wan_camera_api`; studio templates `wan22_14b_t2v_kj`; 11 family templates; 43 LoRA recipes; features `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `[WAN2.2-I2V]EXPLOSION_REDMOND_high_noise.safetensors` | `loras/wan/2.2-i2v/high/[WAN2.2-I2V]EXPLOSION_REDMOND_high_noise.safetensors` | 0.07 | cc0-1.0 | [artificialguybr/Explosion-Redmond-WAN2-I2V-14B](https://huggingface.co/artificialguybr/Explosion-Redmond-WAN2-I2V-14B/resolve/main/%5BWAN2.2-I2V%5DEXPLOSION_REDMOND_high_noise.safetensors) (community upload) (matched by file name only) |
| `[WAN2.2-I2V]EXPLOSION_REDMOND_low_noise.safetensors` | `loras/wan/2.2-i2v/low/[WAN2.2-I2V]EXPLOSION_REDMOND_low_noise.safetensors` | 0.07 | cc0-1.0 | [artificialguybr/Explosion-Redmond-WAN2-I2V-14B](https://huggingface.co/artificialguybr/Explosion-Redmond-WAN2-I2V-14B/resolve/main/%5BWAN2.2-I2V%5DEXPLOSION_REDMOND_low_noise.safetensors) (community upload) (matched by file name only) |
| `pixel_attack_lora_v2_000001750_high_noise.safetensors` | `loras/wan/2.2-i2v/high/pixel_attack_lora_v2_000001750_high_noise.safetensors` | 0.14 | mit | [theamusing/wan2.2_pixel_attack_lora](https://huggingface.co/theamusing/wan2.2_pixel_attack_lora/resolve/main/pixel_attack_lora_v2_000001750_high_noise.safetensors) (community upload) (matched by file name only) |
| `SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors` | `loras/wan/2.2-i2v/high/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors` | 1.14 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Stable-Video-Infinity/v2.0/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors) |
| `SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors` | `loras/wan/2.2-i2v/low/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors` | 1.14 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Stable-Video-Infinity/v2.0/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors) |
| `SVI_Wan2.2-I2V-A14B_lora_HIGH_v2.0_rank_128_fp16.safetensors` | `loras/wan/2.2-i2v/high/SVI_Wan2.2-I2V-A14B_lora_HIGH_v2.0_rank_128_fp16.safetensors` | 1.14 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Stable-Video-Infinity/v2.0/SVI_Wan2.2-I2V-A14B_lora_HIGH_v2.0_rank_128_fp16.safetensors) |
| `SVI_Wan2.2-I2V-A14B_lora_LOW_v2.0_rank_128_fp16.safetensors` | `loras/wan/2.2-i2v/low/SVI_Wan2.2-I2V-A14B_lora_LOW_v2.0_rank_128_fp16.safetensors` | 1.14 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Stable-Video-Infinity/v2.0/SVI_Wan2.2-I2V-A14B_lora_LOW_v2.0_rank_128_fp16.safetensors) |
| `wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors` | 14.25 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors) |
| `wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors` | 14.25 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors) |
| `wan2.2_fun_control_5B_bf16.safetensors` | `diffusion_models/wan2.2_fun_control_5B_bf16.safetensors` | 9.32 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_fun_control_5B_bf16.safetensors) |
| `wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors) |
| `wan2.2_fun_control_low_noise_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_fun_control_low_noise_14B_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_fun_control_low_noise_14B_fp8_scaled.safetensors) |
| `wan2.2_fun_inpaint_5B_bf16.safetensors` | `diffusion_models/wan2.2_fun_inpaint_5B_bf16.safetensors` | 9.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_fun_inpaint_5B_bf16.safetensors) |
| `wan2.2_fun_inpaint_high_noise_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_fun_inpaint_high_noise_14B_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_fun_inpaint_high_noise_14B_fp8_scaled.safetensors) |
| `wan2.2_fun_inpaint_low_noise_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_fun_inpaint_low_noise_14B_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_fun_inpaint_low_noise_14B_fp8_scaled.safetensors) |
| `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors) |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` | `loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` | 1.14 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors) |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` | `loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` | 1.14 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors) |
| `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors) |
| `wan2.2_s2v_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_s2v_14B_fp8_scaled.safetensors` | 15.27 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_s2v_14B_fp8_scaled.safetensors) |
| `wan2.2_t2v_A14B_high_noise_lora_rank64_lightx2v_4step_1217.safetensors` | `loras/wan/accel/wan2.2_t2v_A14B_high_noise_lora_rank64_lightx2v_4step_1217.safetensors` | 0.57 | apache-2.0 | [lightx2v/Wan2.2-Distill-Loras](https://huggingface.co/lightx2v/Wan2.2-Distill-Loras/resolve/main/wan2.2_t2v_A14b_high_noise_lora_rank64_lightx2v_4step_1217.safetensors), published as `wan2.2_t2v_A14b_high_noise_lora_rank64_lightx2v_4step_1217.safetensors` |
| `wan2.2_t2v_A14B_low_noise_lora_rank64_lightx2v_4step_1217.safetensors` | `loras/wan/accel/wan2.2_t2v_A14B_low_noise_lora_rank64_lightx2v_4step_1217.safetensors` | 0.57 | apache-2.0 | [lightx2v/Wan2.2-Distill-Loras](https://huggingface.co/lightx2v/Wan2.2-Distill-Loras/resolve/main/wan2.2_t2v_A14b_low_noise_lora_rank64_lightx2v_4step_1217.safetensors), published as `wan2.2_t2v_A14b_low_noise_lora_rank64_lightx2v_4step_1217.safetensors` |
| `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors) |
| `wan2.2_t2v_lightx2v_4steps_lora_250928_high_noise.safetensors` | `loras/wan/accel/wan2.2_t2v_lightx2v_4steps_lora_250928_high_noise.safetensors` | 2.29 | apache-2.0 | [lightx2v/Wan2.2-Lightning](https://huggingface.co/lightx2v/Wan2.2-Lightning/resolve/main/Wan2.2-T2V-A14B-4steps-lora-250928/high_noise_model.safetensors), published as `high_noise_model.safetensors` |
| `wan2.2_t2v_lightx2v_4steps_lora_250928_low_noise.safetensors` | `loras/wan/accel/wan2.2_t2v_lightx2v_4steps_lora_250928_low_noise.safetensors` | 1.14 | apache-2.0 | [lightx2v/Wan2.2-Lightning](https://huggingface.co/lightx2v/Wan2.2-Lightning/resolve/main/Wan2.2-T2V-A14B-4steps-lora-250928/low_noise_model.safetensors), published as `low_noise_model.safetensors` |
| `wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` | `loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` | 1.14 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors) |
| `wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors` | `loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors` | 1.14 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors) |
| `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors` | `diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors` | 13.31 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors) |
| `wan2.2bullet_time_high_noise.safetensors` | `loras/wan/civitai2/wan2.2bullet_time_high_noise.safetensors` | 0.04 | not stated on the card | [wolfer45/bullettimehigh-wan22-i2v](https://huggingface.co/wolfer45/bullettimehigh-wan22-i2v/resolve/main/wan2.2bullet_time_high_noise.safetensors) (community upload) (matched by file name only) |
| `wan22-video13-CameraRotation-16-sel-2.safetensors` | `loras/wan/other/wan22-video13-CameraRotation-16-sel-2.safetensors` | 0.29 | not stated on the card | [UnifiedHorusRA/CameraRotation-Wan2.2_2.1-I2V](https://huggingface.co/UnifiedHorusRA/CameraRotation-Wan2.2_2.1-I2V/resolve/main/wan22-video13-CameraRotation-16-sel-2.safetensors) (community upload) (matched by file name only) |
| `wan22-video9-rackfocus-16-sel-1-high-000100.safetensors` | `loras/wan/2.2-i2v/high/wan22-video9-rackfocus-16-sel-1-high-000100.safetensors` | 0.29 | not stated on the card | [UnifiedHorusRA/RackFocus-Wan2.2_2.1-I2V-A14B](https://huggingface.co/UnifiedHorusRA/RackFocus-Wan2.2_2.1-I2V-A14B/resolve/main/wan22-video9-rackfocus-16-sel-1-high-000100.safetensors) (community upload) (matched by file name only) |
| `Wan2_2-T2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors` | `diffusion_models/Wan2_2-T2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors` | 13.97 | apache-2.0 | [Kijai/WanVideo_comfy_fp8_scaled](https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/T2V/Wan2_2-T2V-A14B_HIGH_fp8_e4m3fn_scaled_KJ.safetensors), published as `Wan2_2-T2V-A14B_HIGH_fp8_e4m3fn_scaled_KJ.safetensors` |
| `Wan2_2-T2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors` | `diffusion_models/Wan2_2-T2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors` | 13.97 | apache-2.0 | [Kijai/WanVideo_comfy_fp8_scaled](https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/T2V/Wan2_2-T2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors) |
| `Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_260412_rank_256_fp16.safetensors` | `loras/wan/accel/Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_260412_rank_256_fp16.safetensors` | 2.33 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan22_Lightx2v/Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_260412_rank_256_fp16.safetensors) |
| `Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_v1030_rank_64_bf16.safetensors` | `loras/wan/accel/Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_v1030_rank_64_bf16.safetensors` | 0.59 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan22_Lightx2v/Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_v1030_rank_64_bf16.safetensors) |
| `Wan_2_2_I2V_A14B_HIGH_lightx2v_MoE_distill_lora_rank_64_bf16.safetensors` | `loras/wan/accel/Wan_2_2_I2V_A14B_HIGH_lightx2v_MoE_distill_lora_rank_64_bf16.safetensors` | 0.59 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan22_Lightx2v/Wan_2_2_I2V_A14B_HIGH_lightx2v_MoE_distill_lora_rank_64_bf16.safetensors) |
| `Wan_2_2_I2V_A14B_LOW_lightx2v_4step_lora_260412_rank_256_fp16.safetensors` | `loras/wan/accel/Wan_2_2_I2V_A14B_LOW_lightx2v_4step_lora_260412_rank_256_fp16.safetensors` | 2.33 | not stated on the card | [Kijai/WanVideo_comfy](https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan22_Lightx2v/Wan_2_2_I2V_A14B_LOW_lightx2v_4step_lora_260412_rank_256_fp16.safetensors) |
| `wav2vec2_large_english_fp16.safetensors` | `audio_encoders/wav2vec2_large_english_fp16.safetensors` | 0.59 | apache-2.0 | [Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/resolve/main/split_files/audio_encoders/wav2vec2_large_english_fp16.safetensors) |
| `DestructiveKickHigh-000032.safetensors` | `loras/wan/2.2-i2v/high/DestructiveKickHigh-000032.safetensors` | ? | unknown | No public source found |
| `FPV_drone_dive_high_noise.safetensors` | `loras/wan/2.2-i2v/high/FPV_drone_dive_high_noise.safetensors` | 0.14 | see the Civitai page | Civitai only: [FPV Drone Dive Perspective - Wan 2.2](https://civitai.com/models/2191633?modelVersionId=2467713) (matched by file name and size) |
| `FPV_drone_dive_low_noise.safetensors` | `loras/wan/2.2-i2v/low/FPV_drone_dive_low_noise.safetensors` | 0.14 | see the Civitai page | Civitai only: [FPV Drone Dive Perspective - Wan 2.2](https://civitai.com/models/2191633?modelVersionId=2467768) (matched by file name and size) |
| `hard_cut_3_wan_i2v_high.safetensors` | `loras/wan/civitai2/hard_cut_3_wan_i2v_high.safetensors` | 0.29 | see the Civitai page | Civitai only: [Cinematic Hard Cut](https://civitai.com/models/2088559?modelVersionId=2446376) (matched by file name and size) |
| `LongLens_Wan2.2_T2V_High_TriggerIS-Telephoto_Photo.safetensors` | `loras/wan/civitai2/LongLens_Wan2.2_T2V_High_TriggerIS-Telephoto_Photo.safetensors` | 0.07 | see the Civitai page | Civitai only: [Long Prime Lens Lora (up to 600mm) (Wan 2.2 & Z-Image)](https://civitai.com/models/2181569?modelVersionId=2467448) (matched by file name and size) |
| `LongLens_Wan2.2_T2V_Low_TriggerIS-Telephoto_Photo.safetensors` | `loras/wan/civitai2/LongLens_Wan2.2_T2V_Low_TriggerIS-Telephoto_Photo.safetensors` | 0.07 | see the Civitai page | Civitai only: [Long Prime Lens Lora (up to 600mm) (Wan 2.2 & Z-Image)](https://civitai.com/models/2181569?modelVersionId=2467501) (matched by file name and size) |
| `mql_wink_wan22_i2v_v1_low_noise.safetensors` | `loras/wan/2.2-i2v/low/mql_wink_wan22_i2v_v1_low_noise.safetensors` | ? | unknown | No public source found |
| `wan2.2_i2v_animestyle_v2_high.safetensors` | `loras/wan/civitai2/wan2.2_i2v_animestyle_v2_high.safetensors` | 0.14 | see the Civitai page | Civitai only: [Anime Style [WAN 2.2 I2V]](https://civitai.com/models/2222779?modelVersionId=2516837) (matched by file name and size) |
| `wan2.2_i2v_animestyle_v2_low.safetensors` | `loras/wan/civitai2/wan2.2_i2v_animestyle_v2_low.safetensors` | 0.14 | see the Civitai page | Civitai only: [Anime Style [WAN 2.2 I2V]](https://civitai.com/models/2222779?modelVersionId=2516839) (matched by file name and size) |
| `wan2.2extremebodycam_000000300_high_noise.safetensors` | `loras/wan/civitai2/wan2.2extremebodycam_000000300_high_noise.safetensors` | 0.04 | see the Civitai page | Civitai only: [[LuisaP❤️] WAN 2.2 EXTREME BODYCAM](https://civitai.com/models/2105542?modelVersionId=2382055) (matched by file name and size) |
| `wan2.2extremebodycam_000000300_low_noise.safetensors` | `loras/wan/civitai2/wan2.2extremebodycam_000000300_low_noise.safetensors` | 0.04 | see the Civitai page | Civitai only: [[LuisaP❤️] WAN 2.2 EXTREME BODYCAM](https://civitai.com/models/2105542?modelVersionId=2382131) (matched by file name and size) |
| `wan2.2handheldcamxtreme_high_noise.safetensors` | `loras/wan/2.2-i2v/high/wan2.2handheldcamxtreme_high_noise.safetensors` | ? | unknown | No public source found |
| `wan2.2orbitcamv2_high_noise.safetensors` | `loras/wan/civitai2/wan2.2orbitcamv2_high_noise.safetensors` | 0.04 | see the Civitai page | Civitai only: [[LuisaP❤️] WAN 2.2 I2V ORBIT AROUND SUBJECT V2](https://civitai.com/models/2093287?modelVersionId=2373814) (matched by file name and size) |
| `wan2.2orbitcamv2_low_noise.safetensors` | `loras/wan/civitai2/wan2.2orbitcamv2_low_noise.safetensors` | 0.04 | see the Civitai page | Civitai only: [[LuisaP❤️] WAN 2.2 I2V ORBIT AROUND SUBJECT V2](https://civitai.com/models/2093287?modelVersionId=2373843) (matched by file name and size) |
| `wan22-video8-drone-16-sel-2.safetensors` | `loras/wan/civitai2/wan22-video8-drone-16-sel-2.safetensors` | ? | unknown | Civitai only; no Hugging Face copy found |
| `wan_2.2_i2v_highnoise_broken_v1.0.safetensors` | `loras/wan/2.2-i2v/high/wan_2.2_i2v_highnoise_broken_v1.0.safetensors` | ? | unknown | No public source found |
| `wan_2.2_i2v_slap_high_v2.0.safetensors` | `loras/wan/2.2-i2v/high/wan_2.2_i2v_slap_high_v2.0.safetensors` | 0.29 | see the Civitai page | Civitai only: [Slap (and Self Slap) - Wan 2.2 I2V / T2V](https://civitai.com/models/2062140?modelVersionId=2509620) (matched by file name and size) |
| `充气-high.safetensors` | `loras/wan/2.2-i2v/high/充气-high.safetensors` | ? | unknown | No public source found |
| `打脸90高.safetensors` | `loras/wan/2.2-i2v/high/打脸90高.safetensors` | ? | unknown | No public source found |

57 files, 219.30 GiB with a known size.

### Wan2.2-Animate

Used by: studio templates `motion_wan_animate2`; family templates `motion_wan_animate2`, `video_wan_animate2`, `video_wan_animate2_distilled`; features `feature_motion`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `wan_animate_2_distill_int8_convrot.safetensors` | `diffusion_models/wan_animate_2_distill_int8_convrot.safetensors` | 15.51 | apache-2.0 | [Comfy-Org/Wan-Animate-2](https://huggingface.co/Comfy-Org/Wan-Animate-2/resolve/main/diffusion_models/wan_animate_2_distill_int8_convrot.safetensors) |
| `wan_animate_2_int8_convrot.safetensors` | `diffusion_models/wan_animate_2_int8_convrot.safetensors` | 15.51 | apache-2.0 | [Comfy-Org/Wan-Animate-2](https://huggingface.co/Comfy-Org/Wan-Animate-2/resolve/main/diffusion_models/wan_animate_2_int8_convrot.safetensors) |

2 files, 31.02 GiB with a known size.

### Wan2.2-Dancer

Used by: studio templates `motion_wan_dancer`; family templates `motion_wan_dancer`, `video_wan_dancer`; features `feature_motion`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `wan2.2_dancer_14b_global_fp8_scaled.safetensors` | `diffusion_models/wan2.2_dancer_14b_global_fp8_scaled.safetensors` | 17.08 | apache-2.0 | [Comfy-Org/Wan-Dancer](https://huggingface.co/Comfy-Org/Wan-Dancer/resolve/main/diffusion_models/wan2.2_dancer_14b_global_fp8_scaled.safetensors) |
| `wan2.2_dancer_14b_local_fp8_scaled.safetensors` | `diffusion_models/wan2.2_dancer_14b_local_fp8_scaled.safetensors` | 17.08 | apache-2.0 | [Comfy-Org/Wan-Dancer](https://huggingface.co/Comfy-Org/Wan-Dancer/resolve/main/diffusion_models/wan2.2_dancer_14b_local_fp8_scaled.safetensors) |

2 files, 34.17 GiB with a known size.

### World Kit tools

Used by: workflows `h3_fl2v_api`, `h3_i2v_api`, `h3_orbit360_api`, `h3_recast_api`, `h3_reshoot_api`, `h3_song_lock_api`, `h3_t2v_api`, `vset_h3_motion_api` ...; 8 pipeline graphs; University graphs `studio/university/graphs/wf_h3_t2v`; features `worldkit/capabilities`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `3d/AniGen/ckpts/anigen/slat_flow_auto/ckpts/denoiser.pt` | `3d/AniGen/ckpts/anigen/slat_flow_auto/ckpts/denoiser.pt` | 2.29 | mit | [VAST-AI/AniGen](https://huggingface.co/VAST-AI/AniGen/resolve/main/ckpts/anigen/slat_flow_auto/ckpts/denoiser.pt) |
| `3d/AniGen/ckpts/anigen/ss_flow_solo/ckpts/denoiser.pt` | `3d/AniGen/ckpts/anigen/ss_flow_solo/ckpts/denoiser.pt` | 3.14 | mit | [VAST-AI/AniGen](https://huggingface.co/VAST-AI/AniGen/resolve/main/ckpts/anigen/ss_flow_solo/ckpts/denoiser.pt) |
| `3d/moge-vitl/model.pt` | `3d/moge-vitl/model.pt` | 1.17 | mit | [Ruicheng/moge-vitl](https://huggingface.co/Ruicheng/moge-vitl/resolve/main/model.pt) |
| `3d/shap-e/prior/diffusion_pytorch_model.fp16.safetensors` | `3d/shap-e/prior/diffusion_pytorch_model.fp16.safetensors` | 0.59 | mit | [openai/shap-e](https://huggingface.co/openai/shap-e/resolve/main/prior/diffusion_pytorch_model.fp16.safetensors) |
| `3d/shap-e/shap_e_renderer/diffusion_pytorch_model.bin` | `3d/shap-e/shap_e_renderer/diffusion_pytorch_model.bin` | 0.84 | mit | [openai/shap-e](https://huggingface.co/openai/shap-e/resolve/main/shap_e_renderer/diffusion_pytorch_model.bin) |
| `3d/SkinTokens/experiments/skin_vae_2_10_32768/last.ckpt` | `3d/SkinTokens/experiments/skin_vae_2_10_32768/last.ckpt` | 0.45 | mit | [VAST-AI/SkinTokens](https://huggingface.co/VAST-AI/SkinTokens/resolve/main/experiments/skin_vae_2_10_32768/last.ckpt) |
| `checkpoints/model.ckpt` | `checkpoints/model.ckpt` | 1.56 | mit | [stabilityai/TripoSR](https://huggingface.co/stabilityai/TripoSR/resolve/main/model.ckpt) |
| `dinov2_vitl14_reg4_pretrain.pth` | `3d/AniGen/ckpts/dinov2/dinov2_vitl14/dinov2_vitl14_reg4_pretrain.pth` | 1.13 | mit | [VAST-AI/AniGen](https://huggingface.co/VAST-AI/AniGen/resolve/main/ckpts/dinov2/dinov2_vitl14/dinov2_vitl14_reg4_pretrain.pth) |
| `dsine.pt` | `3d/AniGen/ckpts/dsine/dsine.pt` | 0.27 | mit | [VAST-AI/AniGen](https://huggingface.co/VAST-AI/AniGen/resolve/main/ckpts/dsine/dsine.pt) |
| `grpo_1400.ckpt` | `3d/SkinTokens/experiments/articulation_xl_quantization_256_token_4/grpo_1400.ckpt` | 1.05 | mit | [VAST-AI/SkinTokens](https://huggingface.co/VAST-AI/SkinTokens/resolve/main/experiments/articulation_xl_quantization_256_token_4/grpo_1400.ckpt) |
| `Meta-Llama-3-8B-Instruct/model-00001-of-00004.safetensors` | `?` | 4.63 | llama3 | [NousResearch/Meta-Llama-3-8B-Instruct](https://huggingface.co/NousResearch/Meta-Llama-3-8B-Instruct/resolve/main/model-00001-of-00004.safetensors) (community upload) |
| `Meta-Llama-3-8B-Instruct/model-00002-of-00004.safetensors` | `?` | 4.66 | llama3 | [NousResearch/Meta-Llama-3-8B-Instruct](https://huggingface.co/NousResearch/Meta-Llama-3-8B-Instruct/resolve/main/model-00002-of-00004.safetensors) (community upload) |
| `motion/kimodo/Kimodo-SOMA-RP-v1.1/model.safetensors` | `motion/kimodo/Kimodo-SOMA-RP-v1.1/model.safetensors` | 1.06 | nvidia-open-model-license | [nvidia/Kimodo-SOMA-RP-v1.1](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1/resolve/main/model.safetensors) |
| `motion/text-encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised/adapter_model.safetensors` | `motion/text-encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised/adapter_model.safetensors` | 0.16 | other | [ZeyuLing/Motius-KIMODO-SMPLX-RP](https://huggingface.co/ZeyuLing/Motius-KIMODO-SMPLX-RP/resolve/main/text_encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised/adapter_model.safetensors) (community upload) |
| `motion/text-encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp/adapter_model.safetensors` | `motion/text-encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp/adapter_model.safetensors` | 0.16 | other | [ZeyuLing/Motius-KIMODO-SMPLX-RP](https://huggingface.co/ZeyuLing/Motius-KIMODO-SMPLX-RP/resolve/main/text_encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp/adapter_model.safetensors) (community upload) |
| `motion/text-encoders/meta-llama/Meta-Llama-3-8B-Instruct/model-00003-of-00004.safetensors` | `motion/text-encoders/meta-llama/Meta-Llama-3-8B-Instruct/model-00003-of-00004.safetensors` | 4.58 | llama3 | [meta-llama/Meta-Llama-3-8B-Instruct](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/resolve/main/model-00003-of-00004.safetensors) (gated) |
| `motion/text-encoders/meta-llama/Meta-Llama-3-8B-Instruct/model-00004-of-00004.safetensors` | `motion/text-encoders/meta-llama/Meta-Llama-3-8B-Instruct/model-00004-of-00004.safetensors` | 1.09 | llama3 | [meta-llama/Meta-Llama-3-8B-Instruct](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/resolve/main/model-00004-of-00004.safetensors) (gated) |
| `qwen3-vl-32b-minimax-h3-nvfp4-awq.safetensors` | `text_encoders/qwen3-vl-32b-minimax-h3-nvfp4-awq.safetensors` | 14.61 | minimax-h3-community-license-agreement | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors), published as `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` |
| `skeleton_model.ckpt` | `checkpoints/skeleton_model.ckpt` | 1.34 | mit | [VAST-AI/UniRig](https://huggingface.co/VAST-AI/UniRig/resolve/main/skeleton/articulation-xl_quantization_256/model.ckpt), published as `model.ckpt` |
| `skin_model.ckpt` | `checkpoints/skin_model.ckpt` | 4.07 | mit | [VAST-AI/UniRig](https://huggingface.co/VAST-AI/UniRig/resolve/main/skin/articulation-xl/model.ckpt), published as `model.ckpt` |
| `slat_decoder_gs.ckpt` | `checkpoints/slat_decoder_gs.ckpt` | 0.16 | other | [facebook/sam-3d-objects](https://huggingface.co/facebook/sam-3d-objects/resolve/main/checkpoints/slat_decoder_gs.ckpt) (gated) |
| `slat_decoder_gs_4.ckpt` | `3d/sam-3d-objects/checkpoints/slat_decoder_gs_4.ckpt` | 0.16 | other | [facebook/sam-3d-objects](https://huggingface.co/facebook/sam-3d-objects/resolve/main/checkpoints/slat_decoder_gs_4.ckpt) (gated) |
| `slat_decoder_mesh.ckpt` | `checkpoints/slat_decoder_mesh.ckpt` | 0.34 | other | [facebook/sam-3d-objects](https://huggingface.co/facebook/sam-3d-objects/resolve/main/checkpoints/slat_decoder_mesh.ckpt) (gated) |
| `slat_generator.ckpt` | `checkpoints/slat_generator.ckpt` | 4.57 | other | [facebook/sam-3d-objects](https://huggingface.co/facebook/sam-3d-objects/resolve/main/checkpoints/slat_generator.ckpt) (gated) |
| `ss_decoder.ckpt` | `checkpoints/ss_decoder.ckpt` | 0.14 | other | [facebook/sam-3d-objects](https://huggingface.co/facebook/sam-3d-objects/resolve/main/checkpoints/ss_decoder.ckpt) (gated) |
| `ss_generator.ckpt` | `checkpoints/ss_generator.ckpt` | 6.23 | other | [facebook/sam-3d-objects](https://huggingface.co/facebook/sam-3d-objects/resolve/main/checkpoints/ss_generator.ckpt) (gated) |

26 files, 60.45 GiB with a known size.

### yue2

Used by: workflows `music_yue2_bf16_api`, `music_yue2_cover_api`, `music_yue2_int8_api`; family templates `audio_yue2_music_cover`, `audio_yue2_text2music`; Music page `yue2_bf16`, `yue2_int8`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `sheetsage2_bf16.safetensors` | `audio_encoders/sheetsage2_bf16.safetensors` | 1.29 | cc-by-nc-4.0 (non-commercial) | [Comfy-Org/YuE2](https://huggingface.co/Comfy-Org/YuE2/resolve/main/audio_encoders/sheetsage2_bf16.safetensors) |
| `yue2_3b_bf16.safetensors` | `checkpoints/yue2_3b_bf16.safetensors` | 7.26 | cc-by-nc-4.0 (non-commercial) | [Comfy-Org/YuE2](https://huggingface.co/Comfy-Org/YuE2/resolve/main/checkpoints/yue2_3b_bf16.safetensors) |
| `yue2_3b_int8_convrot.safetensors` | `checkpoints/yue2_3b_int8_convrot.safetensors` | 3.69 | cc-by-nc-4.0 (non-commercial) | [Comfy-Org/YuE2](https://huggingface.co/Comfy-Org/YuE2/resolve/main/checkpoints/yue2_3b_int8_convrot.safetensors) |

3 files, 12.24 GiB with a known size.

### Z-Image

Used by: workflows `oneclick_matte_api`; studio templates `image_upscale_realesrgan_x4`, `zimage_base_t2i`, `zimage_turbo_t2i`; 12 family templates; 8 pipeline graphs; University graphs `studio/university/graphs/b_unet_fp8`, `studio/university/graphs/sd15_upscale`; LoRA recipes `lora_982b704f6a`; features `feature_oneclick`, `train_bases`.

| File | Put it in | GiB | Licence | Download |
|---|---|---|---|---|
| `gemma_2_2b_it_elm_fp8_scaled.safetensors` | `text_encoders/gemma_2_2b_it_elm_fp8_scaled.safetensors` | 2.44 | nsclv1 | [Comfy-Org/PixelDiT](https://huggingface.co/Comfy-Org/PixelDiT/resolve/main/text_encoders/gemma_2_2b_it_elm_fp8_scaled.safetensors) |
| `pid_flux1_1024_to_4096_4step_bf16.safetensors` | `diffusion_models/pid_flux1_1024_to_4096_4step_bf16.safetensors` | 2.54 | nsclv1 | [Comfy-Org/PixelDiT](https://huggingface.co/Comfy-Org/PixelDiT/resolve/main/diffusion_models/pid_flux1_1024_to_4096_4step_bf16.safetensors) |
| `pixel_art_style_z_image_turbo.safetensors` | `loras/pixel_art_style_z_image_turbo.safetensors` | 0.16 | apache-2.0 | [tarn59/pixel_art_style_lora_z_image_turbo](https://huggingface.co/tarn59/pixel_art_style_lora_z_image_turbo/resolve/main/pixel_art_style_z_image_turbo.safetensors) (community upload) |
| `qwen_3_4b_fp8_mixed.safetensors` | `text_encoders/qwen_3_4b_fp8_mixed.safetensors` | 5.25 | apache-2.0 | [Comfy-Org/Z-Image-Turbo](https://huggingface.co/Comfy-Org/Z-Image-Turbo/resolve/main/split_files/text_encoders/qwen_3_4b_fp8_mixed.safetensors) |
| `RealESRGAN_x4plus.safetensors` | `upscale_models/RealESRGAN_x4plus.safetensors` | 0.06 | bsd-3-clause | [Comfy-Org/Real-ESRGAN](https://huggingface.co/Comfy-Org/Real-ESRGAN/resolve/main/RealESRGAN_x4plus.safetensors) |
| `Z-Image-Turbo-Fun-Controlnet-Union.safetensors` | `model_patches/Z-Image-Turbo-Fun-Controlnet-Union.safetensors` | 2.89 | apache-2.0 | [alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union](https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union/resolve/main/Z-Image-Turbo-Fun-Controlnet-Union.safetensors) |
| `z_image_bf16.safetensors` | `diffusion_models/z_image_bf16.safetensors` | 11.46 | apache-2.0 | [Comfy-Org/Z-Image](https://huggingface.co/Comfy-Org/Z-Image/resolve/main/split_files/diffusion_models/z_image_bf16.safetensors) |
| `z_image_int8_convrot.safetensors` | `diffusion_models/z_image_int8_convrot.safetensors` | 5.78 | apache-2.0 | [Comfy-Org/Z-Image](https://huggingface.co/Comfy-Org/Z-Image/resolve/main/split_files/diffusion_models/z_image_int8_convrot.safetensors) |
| `z_image_turbo_bf16.safetensors` | `diffusion_models/z_image_turbo_bf16.safetensors` | 11.46 | apache-2.0 | [Comfy-Org/Z-Image-Turbo](https://huggingface.co/Comfy-Org/Z-Image-Turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors) |
| `z_image_turbo_int8_convrot.safetensors` | `diffusion_models/z_image_turbo_int8_convrot.safetensors` | 5.78 | apache-2.0 | [Comfy-Org/Z-Image-Turbo](https://huggingface.co/Comfy-Org/Z-Image-Turbo/resolve/main/split_files/diffusion_models/z_image_turbo_int8_convrot.safetensors) |

10 files, 47.81 GiB with a known size.

<!-- model-files:end -->
