# Anima: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## What the records show

Anima has no new render since 2026-11-01. Its family record holds ten runs: the studio's Base (er_sde, 30 steps, CFG 4.5), Aesthetic (euler, 30 steps, CFG 3.0) and Turbo (euler, 10 steps, CFG 1.0) templates, all with the Qwen 3 0.6B encoder and the Qwen Image VAE, plus ComfyUI's preview, base v1 and two Lllite control templates, and three runs of the core graph. Times run from 8.6 s to 40.0 s. Where the family's own server recorded a peak, it was 6.4 to 7.1 GiB. [code: studio/family_templates/index.json] [run: studio/family_status.json]

Anima's Lllite inpainting template is listed on the family and has no recorded run. [run: studio/family_status.json]

## Training does not work yet

Anima LoRA training does not run here: ComfyUI's training node fails on this base (a compiled rope split with no gradient formula), and no external trainer is wired for it yet. [code: studio/train_bases.py:64]

## Licence

Anima is under the CircleStone Labs Non-Commercial License v1.2: you may not be paid for its use, though outputs may be used for any purpose. [code: studio/licences.py:33, studio/train_bases.py:25]
