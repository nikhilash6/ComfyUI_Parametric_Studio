# FLUX.1 dev, schnell, Kontext and Fill: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## FLUX.1 Fill now runs

FLUX.1 Fill has two recorded runs on flux1-fill-dev, from ComfyUI's own Fill examples: inpaint 40.6 s at a 34.2 GiB peak, seed 845048950, and outpaint 40.8 s at 37.2 GiB, seed 219174185. One run each, looked at. STATE.md lists only each family's latest run, so these two do not appear there. [run: studio/family_status.json:1622-1651] [claim: studio commit 2792c70f, 2026-11-02]

## Training

FLUX.1 dev LoRA training has one recorded run on 2026-11-01 through ai-toolkit: 512 px, rank 16, 200 steps, 0.66 s a step, 22.98 GiB in its own processes against a 30.42 GiB card peak. The A/B effect was small. [run: studio/train_measured.json:50-65]

FLUX.1 schnell training through ComfyUI's training node failed out of memory after its processes passed 70 GB, at 512 px and rank 16. [docs: studio/crew_notes/studio_topics/04-Train/PITFALLS.md:27] [run: studio/train_measured.json]

## FLUX.1 dev as a base for other families

HunyuanWorld's panorama LoRA runs on FLUX.1-dev, and InstantCharacter's adapter needs it too; see the 3D and faces notes. Anything built on FLUX.1-dev inherits its FLUX.1 [dev] Non-Commercial License. [code: studio/family_templates/index.json:194-197, studio/licences.py:46] [run: studio/family_status.json:4035]

PuLID-FLUX v0.9.1 is in the studio's face-swap download plan, with EVA02-CLIP-L and antelopev2. The PuLID weights are Apache-2.0, but they need FLUX.1-dev, so results are non-commercial. FLUX.1-dev itself was already on disk, its checksum verified on 2026-11-02. No studio template uses PuLID yet. [claim: studio download records 2026-11-03]
