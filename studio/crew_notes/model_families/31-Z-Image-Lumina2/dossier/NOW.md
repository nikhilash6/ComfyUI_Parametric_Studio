# Z-Image and Lumina 2: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## New recorded runs

Z-Image int8 (ComfyUI template image_z_image_int8) has one recorded run: 40.4 s, peak 21.7 GiB, seed 153952292. The record names z_image_bf16.safetensors as its model file, which was not checked further. [run: studio/family_status.json] [claim: studio commit 0abfba0e, 2026-11-02]

Lumina 2 with the plain Gemma 2 2B encoder (template lumina2_gemma2_fp16_t2i) is the core Lumina 2 graph with gemma2-2b-fp16 in place of the usual Gemma 2 file. One run: 35.4 s, peak 12.3 GiB, seed 1383721100. It shows that encoder file loads; it is not a quality comparison. [code: studio/family_templates/index.json] [run: studio/family_status.json] [claim: studio commit 2792c70f, 2026-11-02]

## Training

Z-Image LoRA training has one recorded run on 2026-11-01: 512 px, rank 16, 300 steps, 0.47 s a step, 53.8 GiB in its own processes against a 67.27 GiB card peak. The A/B effect was moderate. [run: studio/train_measured.json:33-48]

Lumina 2 LoRA training has one recorded run on 2026-11-01: 512 px, rank 16, 300 steps, 0.20 s a step, 26.45 GiB in its own processes against a 37.17 GiB card peak. The A/B effect was weak. [run: studio/train_measured.json:84-99]

## Licences

Z-Image is Apache-2.0. Lumina Image 2 is Apache-2.0, but its Gemma 2 encoder is under the Gemma Terms of Use, and the NewBie template adds jina-clip-v2, which is CC BY-NC 4.0 (non-commercial). [code: studio/licences.py:113, studio/licences.py:70]
