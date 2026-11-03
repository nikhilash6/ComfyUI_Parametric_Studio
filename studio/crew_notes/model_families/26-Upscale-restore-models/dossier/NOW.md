# Upscale and restore models: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## Colourising a clip

The colorization family now has a recorded render, and STATE.md, rebuilt on 2026-11-03, now lists it. It reuses the LTX Finish proof: LTX-2.5 22B distilled with Lightricks' IC-LoRA Colorization, on a Wan-made jungle temple clip with every colour taken out, steered by words naming the colours. 97 frames at 960x544, 22.0 s, peak 38.4 GiB, seed 42, one run on 2026-11-02. [run: studio/family_status.json] [docs: studio/crew_notes/model_families/26-Upscale-restore-models/dossier/STATE.md]

LTX colourising brought back the greens, the grey stone and the falling orange leaves. Mean chroma came out 15 against the original's 21, and colour distance to the original fell from 13.9 to 8.2 (CIEDE2000). Fault: the original's warm golden sun rays came out neutral white. The colours are the model's guess, not a recovery. LTX-2.x Community License, free under US$10M revenue. [run: studio/family_status.json]

greyscale_to_rgba is still not rendered and cannot be: its only file, final_colorization_model.safetensors, was deleted on 2026-10-30 and has no known source or node. Colourising is shown under the colorization family instead. [run: studio/family_status.json]

## Video and picture upscaling

SeedVR2 3B int8 now has a video upscale run as well as the picture one: utility_seedvr2_3b_int8_upscale_video, 258.8 s, peak 29.9 GiB, seed 448827518. The picture template took 36.7 s at 7.1 GiB. One run each on the test machine. [run: studio/family_status.json] [claim: studio commit 0abfba0e, 2026-11-02]

CCSR, recorded as its own family, upscales a picture 2x with tiles through kijai's CCSR nodes, which passed Pack Lab. One run on 2026-11-01: 55.5 s, peak 4.5 GiB, seed 1148279331, with real-world_ccsr-fp16. Apache-2.0. [code: studio/family_templates/index.json, psn/instances.py:22] [run: studio/family_status.json] [claim: studio commit 0abfba0e, 2026-11-02]

## Frame interpolation

RIFE v4.25 now has three templates in the frame_interpolation family, each the core frame interpolation graph with a RIFE file in place of FILM: v4.25 took 50.8 s, heavy 50.7 s, lite 35.4 s, at peaks of 1.2, 1.2 and 0.8 GiB. One run each. A rife47 variant also exists and has no recorded run. [code: studio/family_templates/index.json] [run: studio/family_status.json] [claim: studio commit 2792c70f, 2026-11-02]

The rife family has its own render now: template frame_interp_rife_v4_25 on its own family server, 15.3 s, 0.9 GiB peak, on the Allegro clip, 2026-11-03. Earlier RIFE runs are recorded under frame_interpolation. [run: studio/family_status.json]

## Face restore lives with the face family

GFPGAN 1.4 face restore now runs, recorded under the face family, not here. It redraws a face rather than recovering it, and on a very small face it can change who it looks like. See the faces notes. [run: studio/family_status.json] [code: studio/family_templates/index.json]
