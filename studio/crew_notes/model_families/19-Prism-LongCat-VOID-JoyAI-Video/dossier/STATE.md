# Model families: state on 2026-11-03

This specialist's records cover 3 studio families: JoyAI-Video-Edit, LongCat-Image, Prism-Alpha. 2 of them have a recorded render. Older notes in this folder can be out of date; where they disagree, this record of what ran wins. [run: studio/family_status.json]

### JoyAI-Video-Edit

JoyAI-Video-Edit is a video family, era 2026, licence Apache-2.0: has a recorded render. What it does, from its ComfyUI template notes: Edit images by following natural language instructions with JoyAI-Image-Edit, which leverages multimodal understanding for precise, spatially aware modifications. This workflow takes one reference image and produces one edited image output plus a side-by-side comparison view. Ideal for instruction-g [run: studio/family_status.json]

JoyAI-Video-Edit last recorded render: template image_joyai_image_edit, 40.1 s, peak 49.3 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

JoyAI-Video-Edit model files with a recorded render on 2026-11-03: Wan2.1_VAE.pth, joyai_image_edit_int8_convrot.safetensors, qwen3vl_8b_joyimage_edit_int8_convrot.safetensors, wan_2.1_vae.safetensors. Runs: joyai-video-edit/image_joyai_image_edit (65.2 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### LongCat-Image

LongCat-Image is an image family, era 2026, licence Apache-2.0: has a recorded render. What it does, from its ComfyUI template notes: Edit images using the LongCat-Image-Edit model. Supports bilingual instructions for global, local, text, and reference-guided editing while preserving visual consistency. [run: studio/family_status.json]

LongCat-Image last recorded render: template image_longcat_text_to_image, 16.2 s, peak 42.9 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

LongCat-Image model files with a recorded render on 2026-11-03: longcat_image_bf16.safetensors, longcat_image_edit_bf16.safetensors. Runs: longcat-image/image_longcat_image_edit (50.2 s); looked at: thumbnail sheet, on brief; longcat-image/image_longcat_text_to_image (30.3 s); looked at: thumbnail sheet, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Prism-Alpha

Prism-Alpha is a video family, era 2026, licence No model repository is recorded for this family: its server starts; no render on record. What it does, from its knowledge base: A pipeline featuring separate video and audio diffusion transformers (DiTs) and a dual-tower bridge, supporting mixed-precision text encoding. [run: studio/family_status.json]
