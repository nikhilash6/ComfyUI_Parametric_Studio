# Model families: state on 2026-11-01

This specialist's records cover 7 studio families: FlashVSR-v1.1, SeedVR2, colorization, frame_interpolation, greyscale_to_rgba, rife, upscale_models. 4 of them have a recorded render. Older notes in this folder can be out of date; where they disagree, this record of what ran wins. [run: studio/family_status.json]

### FlashVSR-v1.1

FlashVSR-v1.1 is an utility family, era 2025, licence not recorded: has a recorded render. What it does, from its knowledge base: A video super-resolution decoder operating in fp32. [run: studio/family_status.json]

FlashVSR-v1.1 last recorded render: template hand:MiniMaxH3FlashVSR, 25.0 s, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

### SeedVR2

SeedVR2 is an utility family, era 2025, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: Upscale images using SeedVR2 3B Int8, a one-step diffusion-based video restoration model that produces high-quality results with improved temporal consistency. Ideal for restoring degraded footage, upscaling low-resolution videos, and enhancing archival media. [run: studio/family_status.json]

SeedVR2 last recorded render: template utility_seedvr2_3b_int8_upscale_image, 36.7 s, peak 7.1 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

SeedVR2 model files with a recorded render on 2026-11-01: seedvr2_3b_int8_convrot.safetensors, seedvr2_ema_vae_fp16.safetensors. Runs: seedvr2/utility_seedvr2_3b_int8_upscale_image (36.7 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### colorization

colorization is an utility family, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### frame_interpolation

frame_interpolation is an utility family, licence not recorded: has a recorded render. What it does, from its ComfyUI template notes: Upload a video and select either RIFE or FILM frame interpolation model to generate smoother, higher frame rate video output. [run: studio/family_status.json]

frame_interpolation last recorded render: template utility_video_frame_interpolation, 2.0 s, peak 7.0 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

### greyscale_to_rgba

greyscale_to_rgba is an utility family, licence not recorded: its server starts; no render on record. [run: studio/family_status.json]

### rife

rife is an utility family, licence not recorded: its server starts; no render on record. What it does, from its notes: Makes in-between frames, so a clip plays smoother. [run: studio/family_status.json]

rife model files with a recorded render on 2026-11-01: film_net_fp16.safetensors. Runs: rife/utility_video_frame_interpolation (80.7 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]

### upscale_models

upscale_models is an utility family, licence not recorded: has a recorded render. What it does, from its notes: Upscalers for stills and frames. [run: studio/family_status.json]

upscale_models last recorded render: template image_upscale_realesrgan_x4, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

upscale_models has 2 studio templates: image_upscale_realesrgan_x4, birefnet_cutout. [code: studio/family_templates/index.json]

upscale_models model files with a recorded render on 2026-11-01: RealESRGAN_x4plus.safetensors. Runs: upscale-models/utility-gan_upscaler (271.6 s). [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv]
