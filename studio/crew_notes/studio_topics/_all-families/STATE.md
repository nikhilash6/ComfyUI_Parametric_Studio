# Model families: state on 2026-11-03

This specialist's records cover 22 studio families: AnimateDiff, Boogu, CCSR, Chroma, Ernie-Image, Fibo-2.0, FireRed-Image-Edit, IC-Light, Ideogram4, Iris-3B, Kolors, LivePortrait, Lotus, MOVA, Matrix-Game-2, Ming-Image, Moss-Image, PixArt-Sigma, PixelDiT, SDPose, SeFi-Image-2B-turbo, Stable-Cascade. 19 of them have a recorded render. Older notes in this folder can be out of date; where they disagree, this record of what ran wins. [run: studio/family_status.json]

### AnimateDiff

AnimateDiff is a video family, era 2023, licence AnimateDiff motion modules: Apache-2.0; AnimateDiff-Lightning: CreativeML OpenRAIL-M. The checkpoint's own licence also applies: has a recorded render. What it does, from its notes: Short looping clips from an SD 1.5 or SDXL checkpoint, by adding a motion module to the sampler. [run: studio/family_status.json]

AnimateDiff last recorded render: template animatediff_sd15_lightning, 35.6 s, peak 3.7 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

AnimateDiff has 4 studio templates: animatediff_sd15_v3, animatediff_sd15_v2, animatediff_sd15_lightning, animatediff_sdxl_beta. [code: studio/family_templates/index.json]

AnimateDiff model files with a recorded render on 2026-11-03: animatediff_lightning_4step_comfyui.safetensors, mm_sd_v15_v2.ckpt, mm_sdxl_v10_beta.ckpt, v3_sd15_mm.ckpt. Runs: animatediff/animatediff_sd15_lightning (35.6 s); looked at: real motion clip; animatediff/animatediff_sd15_v2 (40.7 s); looked at: real motion clip; animatediff/animatediff_sd15_v3 (40.6 s); looked at: real motion clip; animatediff/animatediff_sdxl_beta (70.8 s); looked at: real motion clip. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Boogu

Boogu is an image family, era 2026, licence Apache-2.0 (ComfyUI repackage): has a recorded render. What it does, from its ComfyUI template notes: Edit images using Boogu's instruction-driven model, taking one input image and generating an edited output alongside a side-by-side comparison view. [run: studio/family_status.json]

Boogu last recorded render: template boogu_turbo_t2i, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Boogu has 2 studio templates: boogu_turbo_t2i, boogu_edit_turbo. [code: studio/family_templates/index.json]

Boogu model files with a recorded render on 2026-11-03: boogu_image_edit_turbo_hotfix_1k_20260708_int8_convrot.safetensors, boogu_image_turbo_hotfix_int8_convrot.safetensors. Runs: boogu/boogu_edit_turbo (25.2 s); looked at: thumbnail sheet, on brief; boogu/boogu_turbo_t2i (25.3 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### CCSR

CCSR is an image family, era 2024, licence Apache-2.0 (the code repository and the weights' repackage): has a recorded render. What it does, from its notes: Picture upscaling through kijai's CCSR nodes. [run: studio/family_status.json]

CCSR last recorded render: template ccsr_upscale_x2, 55.5 s, peak 4.5 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

CCSR has 1 studio template: ccsr_upscale_x2. [code: studio/family_templates/index.json]

CCSR model files with a recorded render on 2026-11-03: real-world_ccsr-fp16.safetensors. Runs: ccsr/ccsr_upscale_x2 (55.5 s); looked at: thumbnail sheet, same scene upscaled. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Chroma

Chroma is an image family, era 2025, licence Apache-2.0: has a recorded render. What it does, from its card: An 8.9B text-to-image model based on FLUX.1-schnell, under Apache-2.0. [run: studio/family_status.json]

Chroma last recorded render: template chroma1_hd_t2i, 56.1 s, peak 19.8 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Chroma has 1 studio template: chroma1_hd_t2i. [code: studio/family_templates/index.json]

Chroma model files with a recorded render on 2026-11-03: Chroma1-HD-fp8mixed.safetensors, Chroma1-HD.safetensors. Runs: chroma/chroma1_hd_t2i (56.1 s); looked at: lighthouse painting as prompted. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Ernie-Image

Ernie-Image is an image family, era 2026, licence Apache-2.0 (ComfyUI repackage): has a recorded render. What it does, from its ComfyUI template notes: Generate images from text prompts using the ERNIE-Image model. Input a text description to produce detailed, structured visuals with a broad stylistic range. [run: studio/family_status.json]

Ernie-Image last recorded render: template ernie_image_core_t2i, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Ernie-Image has 1 studio template: ernie_image_core_t2i. [code: studio/family_templates/index.json]

Ernie-Image model files with a recorded render on 2026-11-03: ernie-image.safetensors, ministral-3-3b.safetensors. Runs: ernie-image/ernie_image_core_t2i (30.2 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Fibo-2.0

Fibo-2.0 is an image family, era 2026, licence CC-BY-NC-4.0, non-commercial (Bria FIBO licence; text gated): has a recorded render. What it does, from its notes: Bria's image model, one 8B network for instruction-based editing and text-to-image, trained on long structured captions. Weights are non-commercial only (CC BY-NC 4.0); commercial use needs a separate agreement with Bria. [run: studio/family_status.json]

Fibo-2.0 last recorded render: template fibo2_dev_t2i, 45.5 s, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Fibo-2.0 has 2 studio templates: fibo2_dev_t2i, fibo2_dev_turbo_lora_t2i. [code: studio/family_templates/index.json]

Fibo-2.0 model files with a recorded render on 2026-11-03: fibo2_dev_int8_convrot.safetensors, fibo2_edit_turbo_int8_convrot.safetensors, fibo_2.0_turbo_lora_avg_rank_270_bf16.safetensors, qwen3vl_8b_int8_convrot.safetensors. Runs: fibo-2-0/fibo2_dev_turbo_lora_t2i (40.7 s); looked at: thumbnail sheet, on brief at 8 steps; fibo-2-0/image_fibo2_edit_dev_pe (130.1 s); looked at: thumbnail sheet, on brief; fibo-2-0/image_fibo2_edit_turbo_pe (82.9 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### FireRed-Image-Edit

FireRed-Image-Edit is an image family, era 2026, licence Apache-2.0: has a recorded render. What it does, from its card: An image editing model: words and up to three reference pictures in, an edited picture out. [run: studio/family_status.json]

FireRed-Image-Edit last recorded render: template firered_image_edit_11, 30.2 s, peak 47.8 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

FireRed-Image-Edit has 1 studio template: firered_image_edit_11. [code: studio/family_templates/index.json]

FireRed-Image-Edit model files with a recorded render on 2026-11-03: FireRed-Image-Edit-1.1-Lightning-8steps-v1.2.safetensors, FireRed-Image-Edit-1.1-transformer.safetensors. Runs: firered-image-edit/firered_image_edit_11 (30.2 s); looked at: thumbnail sheet, coat turned red, scene kept. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### IC-Light

IC-Light is an image family, era 2024, licence Code: Apache-2.0. The weights' own card names no licence: has a recorded render. What it does, from its notes: Relights a foreground cut-out on SD 1.5, following a light map and words. [run: studio/family_status.json]

IC-Light last recorded render: template iclight_fc_relight, 20.1 s, peak 5.0 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

IC-Light has 1 studio template: iclight_fc_relight. [code: studio/family_templates/index.json]

IC-Light model files with a recorded render on 2026-11-03: iclight_sd15_fc_unet_ldm.safetensors. Runs: ic-light/iclight_fc_relight (20.1 s); looked at: WEAK: light from the left as asked, but the black mug came back beige. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Ideogram4

Ideogram4 is an image family, era 2026, licence Ideogram 4 Non-Commercial licence (ComfyUI repackage of ideogram-ai/ideogram-4-fp8; text gated): has a recorded render. What it does, from its ComfyUI template notes: Input a text prompt or structured JSON description. Generate an image with precise layout, color, and style control using Ideogram 4.0. [run: studio/family_status.json]

Ideogram4 last recorded render: template image_ideogram4_t2i, 28.6 s, peak 33.2 GiB, 2026-11-03, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Ideogram4 has 2 studio templates: ideogram4_json_t2i, ideogram4_poster_t2i. [code: studio/family_templates/index.json]

### Iris-3B

Iris-3B is an utility family, licence Apache-2.0: has a recorded render. [run: studio/family_status.json]

Iris-3B last recorded render: template iris3b_t2i, 50.1 s, peak 8.5 GiB, 2026-11-02, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Iris-3B has 1 studio template: iris3b_t2i. [code: studio/family_templates/index.json]

### Kolors

Kolors is an image family, era 2024, licence Kolors model licence (the card is tagged Apache-2.0): over 100 million monthly users, or a cloud platform, needs a licence: has a recorded render. [run: studio/family_status.json]

Kolors last recorded render: template kolors_t2i, 24.8 s, peak 12.7 GiB, 2026-11-02, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Kolors has 1 studio template: kolors_t2i. [code: studio/family_templates/index.json]

### LivePortrait

LivePortrait is a video family, era 2024, licence MIT; its InsightFace face finder (buffalo_l) is for non-commercial research only: has a recorded render. What it does, from its LivePortrait's model card: A still face takes its expressions and head turns from a driving clip of another face. [run: studio/family_status.json]

LivePortrait last recorded render: template motion_liveportrait, 79.6 s, peak 2.2 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

LivePortrait has 1 studio template: motion_liveportrait. [code: studio/family_templates/index.json]

LivePortrait model files with a recorded render on 2026-11-03: spade_generator.pth. Runs: LivePortrait/motion_liveportrait (motion/liveportrait_0.mp4); looked at: thumbnail sheet, two frames, face moved little. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Lotus

Lotus is an utility family, era 2026, licence Apache-2.0: has a recorded render. What it does, from its ComfyUI template notes: One picture to a depth map, in a single step. [run: studio/family_status.json]

Lotus last recorded render: template image_lotus_depth_v1_1, 20.1 s, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Lotus model files with a recorded render on 2026-11-03: lotus-depth-d-v1-1.safetensors, vae-ft-mse-840000-ema-pruned.safetensors. Runs: lotus/image_lotus_depth_v1_1 (20.1 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### MOVA

MOVA is a video family, era 2026, licence Apache-2.0: its server starts; no render on record. [run: studio/family_status.json]

MOVA has 1 studio template: mova_core_i2v. [code: studio/family_templates/index.json]

### Matrix-Game-2

Matrix-Game-2 is a video family, era 2025, licence MIT: its server starts; no render on record. [run: studio/family_status.json]

### Ming-Image

Ming-Image is an image family, era 2026, licence MIT (ComfyUI repackage): has a recorded render. What it does, from its ComfyUI template notes: Edit an existing image with Ming Image 0.1 Design, a 6B model tuned for UI, infographics, and posters. It takes one input image plus the boxes you draw on it — position, description, and colour palette — and rebuilds them into a layer-by-layer caption, returning one re-rendered image. Ideal for rest [run: studio/family_status.json]

Ming-Image last recorded render: template image_ming_image_01_design_t2i, 21.4 s, peak 23.6 GiB, 2026-11-03, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

### Moss-Image

Moss-Image is an image family, era 2026, licence Apache-2.0 (ComfyUI repackage): has a recorded render. What it does, from its ComfyUI template notes: Generate an image from a text prompt with the MOSS-Image base checkpoint, which reads a full scene caption and returns one finished image. The prompt upsampler expands a short request into that caption first. Use it for fine-tuning experiments and comparisons with the instruction-tuned checkpoint. [run: studio/family_status.json]

Moss-Image last recorded render: template moss_image_core_t2i, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Moss-Image has 1 studio template: moss_image_core_t2i. [code: studio/family_templates/index.json]

Moss-Image model files with a recorded render on 2026-11-03: flux2-vae_small.safetensors, moss_image_color_depth_control.safetensors, moss_image_sft_int8_convrot.safetensors, qwen3.5_9b_int8_convrot.safetensors. Runs: moss-image/image_moss_image_color_depth_control (30.5 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### PixArt-Sigma

PixArt-Sigma is an image family, era 2024, licence CreativeML OpenRAIL++-M: has a recorded render. [run: studio/family_status.json]

PixArt-Sigma last recorded render: template generic:PixArt-Sigma, 10.0 s, peak 51.8 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

PixArt-Sigma has 1 studio template: pixart_sigma_core_t2i. [code: studio/family_templates/index.json]

PixArt-Sigma model files with a recorded render on 2026-11-03: diffusion_pytorch_model.safetensors, sdxl_vae.safetensors. Runs: pixart-sigma/pixart_sigma_core_t2i (25.7 s); looked at: thumbnail sheet, on brief; sdxl/sdxl_vae_fp16_fix_t2i (30.4 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### PixelDiT

PixelDiT is an image family, era 2026, licence NVIDIA Source Code License: non-commercial, research or evaluation only: has a recorded render. What it does, from its ComfyUI template notes: Input a text prompt and optional negative prompt. Generate a 1024px image using PixelDiT's VAE-free pixel diffusion transformer. [run: studio/family_status.json]

PixelDiT last recorded render: template image_pixeldit_t2i, 10.1 s, peak 57.6 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

PixelDiT model files with a recorded render on 2026-11-03: gemma_2_2b_it_elm_bf16.safetensors, pid_flux1_1024_to_4096_4step_bf16.safetensors, pixeldit_1300m_1024px_bf16.safetensors. Runs: pixeldit/image_pixeldit_t2i (10.2 s); looked at: thumbnail sheet, on brief; z-image/utility_pid_latent_upscale_dit (57.3 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### SDPose

SDPose is an utility family, era 2026, licence MIT (ComfyUI repackage): has a recorded render. What it does, from its ComfyUI template notes: Whole-body pose from a picture. [run: studio/family_status.json]

SDPose last recorded render: template utility_sdpose_ood_image_to_pose, 20.1 s, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

SDPose model files with a recorded render on 2026-11-03: rt_detr_v4-x-hgnet_fp16.safetensors, rt_detr_v4-x-hgnet_fp32.safetensors, sdpose_wholebody_fp16.safetensors. Runs: minimax-h3/video_minimax_h3_fun_controlnet_union (385.6 s); looked at: thumbnail sheet, two frames differ, on brief; sam-3d-body/utility_sam3d_body (255.2 s); looked at: body mesh viewed. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### SeFi-Image-2B-turbo

SeFi-Image-2B-turbo is an image family, licence CC BY-NC 4.0: its server starts; no render on record. [run: studio/family_status.json]

### Stable-Cascade

Stable-Cascade is an image family, era 2024, licence Stability AI Non-Commercial Research Community License: has a recorded render. [run: studio/family_status.json]

Stable-Cascade last recorded render: template generic:Stable-Cascade, 28.1 s, peak 19.4 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Stable-Cascade has 1 studio template: stable_cascade_core_t2i. [code: studio/family_templates/index.json]

Stable-Cascade model files with a recorded render on 2026-11-03: stable_cascade_stage_b.safetensors, stable_cascade_stage_c.safetensors. Runs: stable-cascade/stable_cascade_core_t2i (20.2 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]
