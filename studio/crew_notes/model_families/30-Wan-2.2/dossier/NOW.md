# Wan 2.2 fast builds, talking clips and LoRA pairing: state on 2026-11-03

This file collects what the studio this one grew from learned about LightWan, TurboWan, Wan 2.2 S2V and Wan LoRAs, beside what this studio can really run. Where this file and older notes in this folder disagree, this file, STATE.md and GUIDE.md win. GUIDE.md holds the prompting rules. [inference]

## None of these three runs here yet

LightWan, TurboWan and Wan 2.2 S2V each have a guide card on the Processes tab and no studio route. LightWan and TurboWan are marked "tested on the author's old stack"; S2V is untested. Their cards open the Wan 2.2 family page, or the TurboWan family page, as the nearest thing. [run: studio/processes.json] [code: studio/processes.py:1]

TurboWan was checked on 2026-11-02 and did not render: both 14.5 GB quantised experts are missing, and the earlier copies failed in the core UNETLoader with a KeyError, because TurboDiffusion's int8 checkpoints need TurboDiffusion's own runner. [run: studio/family_status.json:10138]

Wan 2.2 S2V's fp8 weights are not present, so its ComfyUI template cannot run. [run: studio/family_status.json:11780]

## What the earlier studio measured

LightWan, image to video and text to video at 720p: Wan 2.2 A14B experts in NVFP4 with a four-step DMD2 distill baked in, so no speed LoRA. Shift 7 for image to video and 5 for text to video, KSamplerAdvanced with euler and simple at CFG 1, the high expert for steps 0 to 2 and the low expert for 2 to 4. 81 frames at 16 fps, about 70 s and a 33 to 34 GiB peak. It ran with dense attention, because LightX2V's sparse attention has no ComfyUI node, so the card's speed figures do not apply. NVFP4 needs a Blackwell card. [docs: studio/processes/video-lightwan.md]

TurboWan, image to video at 720p: TurboDiffusion's own sampler with sla attention at top-k 0.10, 4 steps, boundary 0.9, sigma max 200, and its own VAE loader, because the core VAE lacks a field it needs. 85 to 90 s warm, about 200 s cold, 27.2 GiB peak. It was trained only on long English prompts; the tested ones were 60 to 80 words. Top-k 0.15 looked the same and ran slower. [docs: studio/processes/video-turbowan.md]

Wan 2.2 S2V, a portrait still plus a voice clip to a talking clip: shift 3, euler and simple, 20 steps, CFG 4.5 with the official Chinese negative, 480x832, 16 fps, up to 4.8 s per 77-frame chunk. 191 s and about 49 GB. A Lightning version with the text-to-video speed LoRA took 13 s at CFG 1, but that LoRA was not trained for S2V and moved less, so it is a preview setting only. uni_pc broke on that torch build. [docs: studio/processes/video-wan-s2v.md]

For S2V prompts: describe how the person speaks and the scene, never the face or clothes, which the picture already carries. The first 2 s may not move. Use one face in a clean portrait. [docs: studio/processes/video-wan-s2v.md]

## Wan LoRAs: pairs, halves and versions

Many Wan 2.2 LoRAs come as half a pair. The earlier studio's library held about 41 high-noise-only and 11 low-noise-only files. A missing partner is normal, not an error: set the other expert's LoRA to 0, and don't route a speed LoRA to the unpaired expert to fill the gap. A paired file belongs to its own expert and can't be swapped to the other. [claim: earlier studio library count and notes, 2026-10-16]

Wan 2.1 LoRAs on Wan 2.2: Wan 2.1 speed LoRAs left about 290 attention keys unmapped on a 2.2 expert, so they only half apply. Use them only in the stack their author tested. One note from that studio says a 2.1 LoRA on a 2.2 expert needs about three times its strength; that was never checked. A Wan 2.1-based model such as SCAIL-2 binds the matching 2.1-era LoRA with no unmapped keys. [claim: earlier studio key-binding check, 2026-10-16] [inference]

One earlier text-to-video graph ran the lightx2v 250928 preview LoRA with the high expert at 1.5 and the low at 1.0, shift 5, 4 steps, CFG 1. This studio's text-to-video template uses the lightx2v v1.1 pair at 1.0 on both. The earlier graph's test record was not kept, so treat 1.5 as a lead, not a setting. [claim: earlier studio graph, 2026-10-17] [code: studio/family_templates/wan22_14b_t2v_kj.json]

## Prompts that describe no motion give still pictures

On the earlier studio's LoRA test bench, briefs with no motion made video models render near-stills. Briefs need actions in time order and what the camera does, and rewriting them that way fixed the bench. This matches Wan's own advice that image-to-video prompts describe motion and camera. [claim: earlier studio LoRA bench, 2026-10-16] [docs: studio/crew_notes/model_families/30-Wan-2.2/dossier/GUIDE.md]

## What people post

A count of about 41,000 distinct public Wan 2.2 prompts found short, plain English prose: median 67 words for image to video, 90 for text to video and 38 for TI2V-5B, with no sections and almost no dialogue or sound text. LoRA triggers came first in 60% of prompts, stacking was rare (9%), and most runs used 4 to 8 step distilled samplers at CFG 1. The most-liked prompts used fewer look words (lighting 11% against 21%) and led with the action. Popularity is not quality. [claim: earlier studio community prompt count, 2026-10-18]
