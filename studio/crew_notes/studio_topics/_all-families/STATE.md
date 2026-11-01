# Model families: state on 2026-11-01

This specialist's records cover 16 studio families: Boogu, Ernie-Image, Fibo-2.0, Ideogram4, Iris-3B, Kolors, Lotus, MOVA, Matrix-Game-2, Ming-Image, Moss-Image, PixArt-Sigma, PixelDiT, SDPose, SeFi-Image-2B-turbo, Stable-Cascade. 9 of them have a recorded render. Older notes in this folder can be out of date; where they disagree, this record of what ran wins. [run: studio/family_status.json]

### Boogu

Boogu is an image family, era 2026, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: Edit images using Boogu's instruction-driven model, taking one input image and generating an edited output alongside a side-by-side comparison view. [run: studio/family_status.json]

Boogu last recorded render: template boogu_turbo_t2i, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Boogu has 2 studio templates: boogu_turbo_t2i, boogu_edit_turbo. [code: studio/family_templates/index.json]

Boogu model files with a recorded render on 2026-11-01: boogu_image_edit_turbo_hotfix_1k_20260708_int8_convrot.safetensors, boogu_image_turbo_hotfix_int8_convrot.safetensors. Runs: boogu/boogu_edit_turbo (25.2 s); boogu/boogu_turbo_t2i (25.3 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### Ernie-Image

Ernie-Image is an image family, era 2026, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: Generate images from text prompts using the ERNIE-Image model. Input a text description to produce detailed, structured visuals with a broad stylistic range. [run: studio/family_status.json]

Ernie-Image last recorded render: template ernie_image_core_t2i, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Ernie-Image has 1 studio template: ernie_image_core_t2i. [code: studio/family_templates/index.json]

Ernie-Image model files with a recorded render on 2026-11-01: ernie-image.safetensors. Runs: ernie-image/ernie_image_core_t2i (30.2 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### Fibo-2.0

Fibo-2.0 is an image family, era 2026, licence CC-BY-NC-4.0, non-commercial: has a recorded render. What it does, from its notes: Bria's image model, one 8B network for instruction-based editing and text-to-image, trained on long structured captions. Weights are non-commercial only (CC BY-NC 4.0); commercial use needs a separate agreement with Bria. [run: studio/family_status.json]

Fibo-2.0 last recorded render: template fibo2_dev_t2i, 45.5 s, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Fibo-2.0 has 1 studio template: fibo2_dev_t2i. [code: studio/family_templates/index.json]

Fibo-2.0 model files with a recorded render on 2026-11-01: fibo2_dev_int8_convrot.safetensors, fibo2_edit_turbo_int8_convrot.safetensors. Runs: fibo-2-0/image_fibo2_edit_dev_pe (130.1 s); fibo-2-0/image_fibo2_edit_turbo_pe (82.9 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### Ideogram4

Ideogram4 is an image family, era 2026, licence not recorded: its server starts; no render on record. What it does, from its ComfyUI template notes: Input a text prompt or structured JSON description. Generate an image with precise layout, color, and style control using Ideogram 4.0. [run: studio/family_status.json]

Ideogram4 has 2 studio templates: ideogram4_json_t2i, ideogram4_poster_t2i. [code: studio/family_templates/index.json]

Ideogram4 model files with a recorded render on 2026-11-01: ideogram4_fp8_scaled.safetensors, ideogram4_unconditional_fp8_scaled.safetensors. Runs: ideogram4/ideogram4_json_t2i (30.2 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### Iris-3B

Iris-3B is an utility family, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### Kolors

Kolors is an image family, era 2024, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### Lotus

Lotus is an utility family, era 2026, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: One picture to a depth map, in a single step. [run: studio/family_status.json]

Lotus last recorded render: template image_lotus_depth_v1_1, 20.1 s, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Lotus model files with a recorded render on 2026-11-01: lotus-depth-d-v1-1.safetensors, vae-ft-mse-840000-ema-pruned.safetensors. Runs: Lotus/image_lotus_depth_v1_1 (families/lotus_0.webp). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### MOVA

MOVA is a video family, era 2026, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

MOVA last recorded test result: error, template generic:MOVA. Do not assume it renders. [run: studio/family_status.json]

MOVA has 1 studio template: mova_core_i2v. [code: studio/family_templates/index.json]

### Matrix-Game-2

Matrix-Game-2 is a video family, era 2025, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### Ming-Image

Ming-Image is an image family, era 2026, licence not recorded: its server starts; no render on record. What it does, from its ComfyUI template notes: Edit an existing image with Ming Image 0.1 Design, a 6B model tuned for UI, infographics, and posters. It takes one input image plus the boxes you draw on it — position, description, and colour palette — and rebuilds them into a layer-by-layer caption, returning one re-rendered image. Ideal for rest [run: studio/family_status.json]

### Moss-Image

Moss-Image is an image family, era 2026, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: Generate an image from a text prompt with the MOSS-Image base checkpoint, which reads a full scene caption and returns one finished image. The prompt upsampler expands a short request into that caption first. Use it for fine-tuning experiments and comparisons with the instruction-tuned checkpoint. [run: studio/family_status.json]

Moss-Image last recorded render: template moss_image_core_t2i, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Moss-Image has 1 studio template: moss_image_core_t2i. [code: studio/family_templates/index.json]

Moss-Image model files with a recorded render on 2026-11-01: flux2-vae_small.safetensors, moss_image_color_depth_control.safetensors, moss_image_sft_int8_convrot.safetensors. Runs: moss-image/image_moss_image_color_depth_control (30.5 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### PixArt-Sigma

PixArt-Sigma is an image family, era 2024, licence not recorded: has a recorded render. [run: studio/family_status.json]

PixArt-Sigma last recorded render: template generic:PixArt-Sigma, 10.0 s, peak 51.8 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

PixArt-Sigma has 1 studio template: pixart_sigma_core_t2i. [code: studio/family_templates/index.json]

### PixelDiT

PixelDiT is an image family, era 2026, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: Input a text prompt and optional negative prompt. Generate a 1024px image using PixelDiT's VAE-free pixel diffusion transformer. [run: studio/family_status.json]

PixelDiT last recorded render: template image_pixeldit_t2i, 10.1 s, peak 57.6 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

PixelDiT model files with a recorded render on 2026-11-01: pixeldit_1300m_1024px_bf16.safetensors. Runs: pixeldit/image_pixeldit_t2i (10.2 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### SDPose

SDPose is an utility family, era 2026, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: Whole-body pose from a picture. [run: studio/family_status.json]

SDPose last recorded render: template utility_sdpose_ood_image_to_pose, 20.1 s, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

SDPose model files with a recorded render on 2026-11-01: rt_detr_v4-x-hgnet_fp32.safetensors, sdpose_wholebody_fp16.safetensors. Runs: SAM-3D-Body/utility_sam3d_body (families/sam-3d-body_turn.webp); SDPose/utility_sdpose_ood_image_to_pose (families/sdpose_0.webp). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### SeFi-Image-2B-turbo

SeFi-Image-2B-turbo is an image family, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### Stable-Cascade

Stable-Cascade is an image family, era 2024, licence not recorded: has a recorded render. [run: studio/family_status.json]

Stable-Cascade last recorded render: template generic:Stable-Cascade, 28.1 s, peak 19.4 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Stable-Cascade has 1 studio template: stable_cascade_core_t2i. [code: studio/family_templates/index.json]

Stable-Cascade model files with a recorded render on 2026-11-01: stable_cascade_stage_b.safetensors, stable_cascade_stage_c.safetensors. Runs: stable-cascade/stable_cascade_core_t2i (20.2 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]
