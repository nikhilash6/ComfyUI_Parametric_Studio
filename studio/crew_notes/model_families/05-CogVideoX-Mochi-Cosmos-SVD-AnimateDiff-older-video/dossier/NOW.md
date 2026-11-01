# Older video models: what is true today

State on 2026-11-01. Where older notes in this folder disagree, this file and STATE.md win. Older notes here came from a knowledge base and can be out of date, including what they say about AnimateDiff. [run: studio/family_status.json]

## AnimateDiff

AnimateDiff is not wired in this studio. The atlas lists it as status missing, with no family, no goals, not in Comfy's lists and licence not verified, "listed by date only". Missing means no family folder and no goal; it is not a claim the model cannot be added. [code: studio/atlas_models.json:90-101] [docs: docs/COVERAGE.md:7, docs/COVERAGE.md:26, docs/COVERAGE.md:52]

AnimateDiff has no family row, no studio template, no goal, no recipe, no process and no render. A search of family_status.json finds the word only inside this specialist's own name, and the other files do not contain it at all. [code: studio/family_status.json:331, studio/family_templates/index.json, studio/models_manifest.json, studio/recipes.json, studio/processes.json, studio/recipe_renders.json]

AnimateDiff in the specialist's name is a topic, not a feature. The crew greeting says this specialist looks after AnimateDiff, which only means questions about it come here. [code: studio/crew.py:375]

The LoRA animatediff_style_h3 is not AnimateDiff. It is a third-party MiniMax H3 LoRA for nonstop surreal morphing "AnimateDiff-like", run through the h3_video goal. Its proof level is recipe: never rendered through this recipe. Licence and strength are unverified, and its trained mode is not stated. [code: studio/lora_recipes.json:5606-5614, studio/lora_recipes.json:5633, studio/lora_recipes.json:5680, studio/lora_recipes.json:5688] [run: studio/recipe_renders.json]

The pack ComfyUI-AnimateDiff-Evolved appears in the Sampling Lab atlas as a source of sampling methods that were read. That entry credits and describes code. It does not show the pack is installed or wired here. [code: studio/sampling_lab/atlas.json] [inference]

## SVD

SVD is wired through one studio template, svd_xt_1_1_i2v, on the Families page: one picture to a clip. It runs on the family's own ComfyUI instance through a generated form. Weights are not in this repo. [code: studio/family_templates/index.json:1636-1648, studio/families_api.py:1, studio/families_api.py:368]

SVD rendered once: template svd_xt_1_1_i2v, model svd_xt_1_1.safetensors (4.78 GB), seed 1556311833, 65.7 s, peak 27.8 GiB, on 2026-11-01 on the test machine. The output is families/svd_0.mp4. [run: studio/family_status.json, studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

SVD template settings: 1024x576, 25 frames, motion_bucket_id 127, fps 6, augmentation 0, 20 steps, cfg 2.5, euler with karras, min_cfg 1.0. That is about 4 seconds of video. The settings follow the SVD step of ComfyUI's own txt_to_image_to_video template. [code: studio/family_templates/svd_xt_1_1_i2v.json:29-33, studio/family_templates/svd_xt_1_1_i2v.json:44, studio/family_templates/svd_xt_1_1_i2v.json:67-70, studio/family_templates/index.json:1639] [inference]

SVD is not proven beyond that one run. Other seeds, motion values and pictures have no record, and the 14-frame mode the family notes mention has no template. The record says the render succeeded; it holds no verdict on quality. [run: studio/family_status.json] [inference]

SVD's other listed template, ComfyUI's txt_to_image_to_video, needs svd_xt.safetensors and sd_xl_base_1.0.safetensors, 16.5 GB in all. It has no render on record. [code: studio/family_status.json:8918, studio/family_status.json:8935]

SVD licence: the atlas records the Stable Video Diffusion Community licence as verified, while the family row says only "Own licence". Read the licence before commercial use. [code: studio/atlas_models.json:124, docs/COVERAGE.md:86, studio/family_status.json:8879]

## CogVideoX

CogVideoX has no plain template in the studio. Its family row lists no templates. Its one recorded render is the edit tool VOID, which is built on CogVideoX: 240 s, peak not recorded, output families/cogvideox_0.mp4. [code: studio/family_status.json:851, studio/family_status.json:866-868, studio/family_status.json:882-886, studio/edits.py:9] [run: studio/family_status.json]

CogVideoX on its own is not proven here. Text to video, video continuation and image to video through CogVideoX itself have no render on record. Its model files also have no row in the 2026-11-01 evidence table. For VOID itself, ask the Prism, LongCat, VOID and JoyAI specialist. [run: studio/family_status.json, studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

CogVideoX licence records disagree in form: the atlas says Apache-2.0, verified, and the family row says "Own licence". Check the model card for the build you use. [code: studio/atlas_models.json:328, docs/COVERAGE.md:96, studio/family_status.json:855]

## Mochi

Mochi is wired through one studio template, mochi_core_t2v, using ComfyUI core nodes: 640x384, 25 frames, 20 steps, cfg 4.5, euler with simple, 24 fps, tiled decode. That is about 1 second of video. It needs mochi_preview_bf16, t5xxl_fp16 and mochi_vae, 28.7 GB in the index. [code: studio/family_templates/index.json:112-137, studio/family_templates/mochi_core_t2v.json:46-48, studio/family_templates/mochi_core_t2v.json:60-63, studio/family_templates/mochi_core_t2v.json:103] [inference]

Mochi has a recorded render labelled generic:Mochi: 31.1 s, peak 40.8 GiB, kind video, with families/mochi_1.mp4 and a still. Its prompt matches the template's, so it was probably this graph. One record only. It has no row in the 2026-11-01 evidence table. Licence Apache-2.0. [code: studio/family_status.json:6058-6064, studio/family_status.json:6088] [run: studio/family_status.json, studio/crew_notes/evidence/model_proof_2026-11-01.tsv] [inference]

Mochi longer clips, larger sizes and other settings are not proven. Nothing on record goes past the template's short test size. [code: studio/family_templates/mochi_core_t2v.json:46-48] [inference]

## Cosmos

Cosmos is listed as a video family, but what is wired and rendered here is a picture. The one template, cosmos_core_t2i, is Cosmos Predict2 14B text to image at 1024x1024, 20 steps, cfg 4. It needs 31.4 GB, including cosmos_predict2_14B_t2i, an old T5 encoder and the Wan 2.1 VAE. [code: studio/family_status.json:909, studio/family_templates/index.json:77-97, studio/family_templates/cosmos_core_t2i.json:46-47, studio/family_templates/cosmos_core_t2i.json:59]

Cosmos has a recorded render labelled generic:Cosmos: 36.0 s, peak 41.0 GiB, kind image, with two pictures. Cosmos video has no template and no render on record. It has no row in the 2026-11-01 evidence table. [code: studio/family_status.json:923-927, studio/family_status.json:940, studio/family_status.json:953] [run: studio/family_status.json, studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

Cosmos licence: the atlas records the NVIDIA Open Model License as verified, while the family row records none. [code: studio/atlas_models.json:566, docs/COVERAGE.md:105]

## What all of them lack

SVD, CogVideoX, Mochi and Cosmos have no goal in the Create page: the atlas lists empty goals for them and no goal maps to these families. So they have no row in models_manifest.json and no recipe, library recipe, recipe render or process that uses them. They run only from the Families page. [code: studio/atlas_models.json:124, studio/families_api.py:14, studio/models_manifest.json, studio/recipes.json, studio/processes.json, studio/recipe_renders.json]

Every recorded time and peak in this file comes from one run on the test machine with a 96 GB card, not a promise for other machines. A run that needs more memory than a card has may fail or offload; we have no record for smaller cards. [run: studio/family_status.json] [inference]

Allegro and SANA-Video also sit with this specialist. Their servers start, but no template validates because no candidate's models are on disk, so they have no render. [code: studio/family_status.json:326] [run: studio/family_status.json]
