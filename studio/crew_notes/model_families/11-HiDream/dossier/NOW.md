# HiDream: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## What the records show

HiDream has no new render since 2026-11-01. Two O1 templates have one run each: O1 full (hidream_o1_full_t2i: noise scale 8, patch seam smoothing, dpmpp_2m_sde_gpu, 40 steps, CFG 5, 2048 px) at 40.2 s, and O1 dev fp8 (hidream_o1_dev_t2i: noise scale 7.6, LCM, 28 steps, CFG 1, 2048 px) at 20.2 s. No peak is recorded. The O1 checkpoint carries its own encoder, so the official template's Gemma 4 prompt enhancer is not needed. [code: studio/family_templates/index.json] [run: studio/family_status.json]

HiDream E1.1 editing shows only a sample picture from ComfyUI's template library; it has not been rendered in the studio. The I1 templates listed on the family have no recorded run either. [run: studio/family_status.json]

HiDream E1 template readiness changed on 2026-11-02: the check now accepts the substitute and upgrade file names the run step already resolves, so HiDream E1 is no longer shown as missing files. Readiness is not a render. [code: studio/families_api.py:117-120] [claim: studio commit e162c772, 2026-11-02]

## Training is wired, not measured

HiDream-O1 LoRA training is wired through ai-toolkit (28 sample steps, guidance 5.0), but there is no measured training run for it. [code: studio/train_bases.py:59-60] [run: studio/train_measured.json]

HiDream-O1 is MIT. [code: studio/licences.py:51]
