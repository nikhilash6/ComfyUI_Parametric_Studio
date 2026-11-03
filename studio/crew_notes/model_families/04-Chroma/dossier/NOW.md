# Chroma: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## Chroma1-HD runs in the studio

Chroma is now a studio family with a recorded render. The studio's records describe it as an 8.9B text-to-image model based on FLUX.1-schnell, under Apache-2.0. This folder has no STATE.md, because the family is filed under the general records rather than this specialist. [run: studio/family_status.json:13225-13264] [code: studio/licences.py:121]

Chroma1-HD (template chroma1_hd_t2i) runs the fp8mixed Chroma1-HD file with the T5-XXL fp16 encoder and the FLUX VAE, 40 steps at CFG 3, as its card recommends. The files total about 19.3 GB. [code: studio/family_templates/index.json:2266-2294]

Chroma1-HD's run on 2026-11-01: 56.1 s, peak 19.8 GiB, seed 1956336289. One run on the test machine; the record holds no note on how the picture looked. [run: studio/family_status.json:13229-13243]

## What is still missing

Chroma has no other template, no LoRA run and no training record in the studio. The older notes in this folder that name other Chroma files or settings are from the knowledge base and were not run here. [run: studio/family_status.json:13148-13187, studio/train_measured.json] [inference]
