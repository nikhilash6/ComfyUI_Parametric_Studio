# LongCat-Video-Avatar 1.5: state on 2026-11-03

Where this file and older notes disagree, this file and STATE.md win. The older notes in this folder and in the Prism, LongCat, VOID and JoyAI folder repeat the model card's audio CFG tip of 3 to 5. The earlier studio's side-by-side test found the opposite, so keep audio CFG at 1. [docs: studio/processes/avatar-longcat.md] [inference]

## It does not run here yet

LongCat-Avatar-15 rendered on 2026-11-03 on its own family server, after its DiT and DMD LoRA were downloaded: template longcat_avatar15_talk, seed 20261102, 295 s, 20.8 GiB peak with 24 blocks swapped to system memory. Every frame was looked at. One run on the test machine. [run: studio/family_status.json] [code: psn/instances.py:64]

## What the earlier studio measured

A still of a person plus a voice clip gave a 3.72 s, 93-frame, 25 fps lip-synced clip with the voice muxed in. The graph: the LongCat-Avatar-15 DiT in bf16 with the DMD distill LoRA (rank 128) at 1.0, the Whisper-large-v3 encoder feeding the LongCat audio embeds (loudness normalised), the longcat_distill_euler schedule, 8 steps, shift 7, sampler CFG 1. [docs: studio/processes/avatar-longcat.md]

Audio CFG 1 against 4, same still, line and seed: at 4 the lips inflated into a glossy round "O" on open vowels; at 1 they moved naturally. A second run of the studio's own graph reproduced the CFG 4 clip frame for frame. Audio CFG 1 is also the value in the official inference script, while the card's text says 3 to 5. One visual comparison, never judged by ear for lip sync. [docs: studio/processes/avatar-longcat.md]

Timings on that studio: 132 s at 480x832 with audio CFG 1 and a peak of 55,670 MiB, 296 s at 768x1280 after a first try ran out of memory on a full card. Audio longer than 3.72 s was cut at one segment. [docs: studio/processes/avatar-longcat.md]

LongCat-Avatar 1.5 is an 8-step distilled model with hidden size 4096, so it is not a Wan 14B and Wan 14B LoRAs and settings don't carry over. [claim: earlier studio notes, 2026-10-16]

## Final session findings, 2026-11-03

The face family now has two recorded renders, a GFPGAN restore and InsightFace landmarks. STATE.md, rebuilt on 2026-11-03, now lists the GFPGAN run as the latest. [run: studio/family_status.json] [docs: studio/crew_notes/model_families/08-Faces-identity-portrait-animation/dossier/STATE.md]

### GFPGAN 1.4 restore

GFPGAN 1.4 restore (template face_gfpgan_restore) runs comfyorg's GFPGAN node, Apache-2.0 and on the Pack Lab shortlist, on the face family's own instance. facexlib's RetinaFace detector and two parsers find and parse the face; GFPGAN 1.4 redraws it and pastes it back. The rest of the picture is left as it was. [code: studio/family_templates/index.json, psn/instances.py:64, psn/instances.py:73-74]

GFPGAN 1.4 was tested on 2026-11-02 on a damaged copy of an invented adult: the face shrunk to 160 px, blurred and saved as a JPEG at quality 30. One run, 3.1 s warm, peak 0.5 GiB, compared with the clean original. Eyes, brows, lips and hair edges came back sharp and the face still read as the same invented person, a little rounder and younger. The collar and background stayed as blurred as they came in. [run: studio/family_status.json]

GFPGAN 1.4 redraws a face rather than recovering it. On a harsher test (100 px, JPEG quality 18) it drew a visibly different person. The template says so: use it on generated faces or with the person's consent. Licences: GFPGAN Apache-2.0, facexlib MIT. [run: studio/family_status.json] [code: studio/family_templates/index.json]

### InsightFace landmarks

InsightFace buffalo_l runs as a small CPU runner for the face family: the det_10g detector and the 2d106det landmark model. On an invented adult from World Kit's character library it found one face at score 0.80 and put the 106 points on the jaw, brows, eyes, nose and lips, in 0.8 s. Detection and landmarks only. [code: scripts/family_face_landmarks.py:1-12] [run: studio/family_status.json]

InsightFace model zoo files are for non-commercial research only. The studio labels them that way and does not ship them. [code: studio/licences.py:141-142] [run: studio/family_status.json]

### Other identity routes

InstantCharacter is still not rendered (checked 2026-11-02). The adapter, SigLIP and FLUX.1-dev are on disk; DINOv2-giant (facebook/dinov2-giant, 4.55 GB) is missing, and the InstantCharacter pack still needs a read. [run: studio/family_status.json]

LivePortrait, recorded as its own family, rendered on 2026-11-01 on its own family server: an invented man follows an invented woman's clip. One run, 79.6 s, peak 2.2 GiB. LivePortrait is MIT, but its InsightFace face finder is non-commercial research only. [run: studio/family_status.json] [code: studio/licences.py:125, psn/instances.py:23]

IP-Adapter face references now run on SD 1.5 (full-face and plus-face) and on SDXL (plus-face vit-h). Each template says to use only invented people or yourself. See the SD 1.5 and SDXL notes for settings and timings. [code: studio/family_templates/index.json] [run: studio/family_status.json]

### Swap weights: what was missing and what was fetched

Face-swap weights were audited on 2026-11-02. The InsightFace inswapper, the antelopev2 set and EVA02-CLIP-L had been on disk in late October and were deleted in a clean-up on 31 October. PuLID-FLUX, DreamID-V, SeC-4B, Wan2.2-Animate-14B and FLUX.2 Klein Base 9B had never been downloaded. [claim: studio download records 2026-11-03]

Face-swap re-fetch plan, as the download records list it, with licences: PuLID-FLUX v0.9.1 (Apache-2.0, but it needs FLUX.1-dev, which is non-commercial) with EVA02-CLIP-L (MIT) and antelopev2; ReActor's inswapper_128 (InsightFace weights, non-commercial research only, though the dataset card says MIT for the repo); CodeFormer v0.1.0 (NTU S-Lab License, non-commercial, a pickle .pth); DreamID-V (Apache-2.0, a pickle .pth); the Wan2.2-Animate 14B fp8 set with SeC-4B and a yolov10m detector (AGPL-3.0); FLUX.2 Klein Base 9B, blocked because it is gated behind a licence click (FLUX Non-Commercial). [claim: studio download records 2026-11-03]

Face-swap re-fetch status when these notes were written: the buffalo_l recogniser (w600k_r50) and 3D landmark file, and antelopev2's glintr100, had landed; two antelopev2 files are hard links to byte-identical buffalo_l files. EVA02-CLIP-L was downloading. PuLID-FLUX, inswapper, CodeFormer, DreamID-V and the Wan Animate weights were not on disk yet, and no studio template uses them yet. [claim: studio download records 2026-11-03]
