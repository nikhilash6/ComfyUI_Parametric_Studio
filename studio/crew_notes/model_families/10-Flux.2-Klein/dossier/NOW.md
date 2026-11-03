# FLUX.2 Klein and FLUX.3 Klein: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## Try-on

FLUX.2 Klein 4B with the try-on LoRA (template klein4b_tryon) is the default try-on in the Fashion designer: the first ready method in a list ordered by what each did on the same invented model and garments. Person and garment go in as two reference pictures, with the Attach Outfit LoRA at strength 1 on Klein Base 4B, 20 steps, CFG 5. [code: studio/tryon.py:1, studio/tryon.py:10-12, studio/family_templates/index.json] [test: tests/test_tryon.py]

Klein 4B try-on was the cleanest on the studio's tests: it replaced the whole outfit on both the coat and the dress and kept the face. The page quotes 66 to 82 s and 21 GB; the family record is 66.2 s, peak 21.2 GiB, seed 1497448468. Klein 4B is Apache-2.0, but the LoRA is rent-only on Civitai, so the page marks the method non-commercial. [code: studio/tryon.py:12] [run: studio/family_status.json]

Klein 9B with the same kind of LoRA (template klein9b_tryon_lora) is quicker, 43.4 s at 29.1 GiB, and replaced the whole outfit, but on the dress test the colour came out paler and the hem shorter. That LoRA was made for Klein Base 9B and runs here on the distilled 9B at 4 steps and CFG 1. Klein 9B is under the FLUX Non-Commercial License. [code: studio/tryon.py:13, studio/family_templates/index.json] [run: studio/family_status.json]

Klein 9B with two references and no LoRA (template klein9b_tryon) dressed the coat well but also recoloured the trousers to match. The page quotes 41 s and 33 GB; the family record holds a different run at 79.9 s and 27.5 GiB. [code: studio/tryon.py:16] [run: studio/family_status.json]

FLUX.2 Klein Base 9B is not on the test machine. Its download is blocked because the repo is gated behind a licence click (FLUX Non-Commercial). [claim: studio download records 2026-11-03]

## Edit and file variants

Klein's ComfyUI image edit templates each have one run with the words "make it snow gently on the street": Klein Base 4B 35.7 s at 21.3 GiB, distilled Klein 9B 25.2 s at 23.1 GiB. [run: studio/family_status.json] [claim: studio commit 0abfba0e, 2026-11-02]

FLUX.3 Klein SD nvfp4 has a template now, the bf16 graph with the SD nvfp4 file swapped in. One run: 30.4 s, peak 13.4 GiB, seed 1278403381. FLUX.3 Klein is under the FLUX Kommunity License: outputs may be used commercially only by companies under US$5,000,000 gross annual revenue. [code: studio/family_templates/index.json, studio/licences.py:48] [run: studio/family_status.json] [claim: studio commit 2792c70f, 2026-11-02]

## Training

Klein LoRA training has two recorded runs on 2026-11-01, both at 512 px, rank 16, 300 steps. Klein Base 4B: 0.35 s a step, 37.28 GiB in its own processes, A/B strong on a prompt close to the set. Klein 9B: 0.81 s a step, 72.28 GiB in its own processes against a 94.65 GiB card peak, A/B strong. The 9B run leaves little room on a 96 GB card. [run: studio/train_measured.json:16-31, studio/train_measured.json:118-133] [inference]
