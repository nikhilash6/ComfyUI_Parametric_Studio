# Model families: state on 2026-11-03

This specialist's records cover 2 studio families: Flux.2, Flux.3-Klein. 2 of them have a recorded render. Older notes in this folder can be out of date; where they disagree, this record of what ran wins. [run: studio/family_status.json]

### Flux.2

Flux.2 is an image family, era 2025, licence Klein 4B and Klein Base 4B: Apache-2.0. Klein 9B and Dev: FLUX Non-Commercial License (text gated): has a recorded render. What it does, from its ComfyUI template notes: Generate photorealistic images with multi-reference consistency and professional text rendering. [run: studio/family_status.json]

Flux.2 last recorded render: template klein9b_t2i, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Flux.2 has 9 studio templates: klein9b_t2i, klein9b_edit, klein9b_style, klein9b_mesh2photo, klein4b_edit, klein4b_base_edit, klein9b_tryon, klein9b_tryon_lora. [code: studio/family_templates/index.json]

Flux.2 model files with a recorded render on 2026-11-03: KleinBase4B_TryOn.safetensors, KleinBase9B_TryOn.safetensors, full_encoder_small_decoder.safetensors, qwen_3_4b.safetensors, qwen_3_8b_fp8mixed.safetensors. Runs: flux-2/image_flux2_klein_image_edit_4b_base (35.7 s); looked at: WEAK: snow added, but the person and street were redrawn; flux-2/image_flux2_klein_image_edit_9b_distilled (25.2 s); looked at: thumbnail sheet, snow added, scene kept; flux-2/image_flux2_klein_text_to_image (25.2 s); looked at: thumbnail sheet, on brief; flux-2/klein4b_tryon (66.2 s); looked at: dress and coat replaced cleanly; flux-2/klein9b_tryon_lora (43.4 s); looked at: dress replaced, paler, shorter hem. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Flux.3-Klein

Flux.3-Klein is an image family, era 2026, licence FLUX Kommunity License (text gated): outputs may be used commercially only by companies under US$5,000,000 gross annual revenue: has a recorded render. What it does, from its ComfyUI template notes: Edit an existing image with FLUX 3 Image Klein by pairing one input image with one text prompt, producing a single edited result and a side-by-side comparison view. Ideal for targeted retouching, restyling a photo, or swapping details while keeping the rest of the scene intact. [run: studio/family_status.json]

Flux.3-Klein last recorded render: template flux3_klein_core_t2i_api, 10.0 s, peak 25.1 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Flux.3-Klein has 3 studio templates: flux3_klein_bf16_t2i, flux3_klein_nvfp4_t2i, flux3_klein_sd_nvfp4_t2i. [code: studio/family_templates/index.json]

Flux.3-Klein model files with a recorded render on 2026-11-03: flux2-vae.safetensors, flux3_image_klein_bf16.safetensors, flux3_image_klein_nvfp4.safetensors, flux3_image_klein_sd_nvfp4.safetensors, qwen3vl_4b_bf16.safetensors. Runs: fibo-2-0/image_fibo2_edit_dev_pe (130.1 s); looked at: thumbnail sheet, on brief; flux-3-klein/flux3_klein_bf16_t2i (20.2 s); looked at: thumbnail sheet, on brief; flux-3-klein/flux3_klein_nvfp4_t2i (20.2 s); looked at: thumbnail sheet, on brief; flux-3-klein/flux3_klein_sd_nvfp4_t2i (30.4 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]
