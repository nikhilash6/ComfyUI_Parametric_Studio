# Prism, LongCat, VOID and JoyAI: corrections on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## LongCat-Video-Avatar audio CFG

PROMPTING.md, RECIPES.md and PITFALLS.md in this folder say LongCat-Video-Avatar 1.5's audio CFG works best at 3 to 5. That is the model card's tip. On the earlier studio a side-by-side at audio CFG 4 inflated the lips into a glossy round "O" on open vowels, while CFG 1, the official inference script's value, moved them naturally. Keep audio CFG at 1. The talking-avatar model belongs to the Faces specialist, whose NOW.md has the full record. [docs: studio/processes/avatar-longcat.md, studio/crew_notes/model_families/08-Faces-identity-portrait-animation/dossier/NOW.md]

## Final session findings, 2026-11-03

VOID, the studio's "Remove objects or people" edit tool, ran on 2026-11-02 in the graph audit on a private ComfyUI lane. The graph is two VOID passes built on CogVideoX: a SAM 3.1 mask from the detection prompt "person", noise warped along RAFT optical flow, then 30 steps at CFG 6 for each pass. It ran on the studio's own 5 s clip of an invented adult chef flambéing at a stove, at 672x384 and 120 frames. [code: studio/edits.py:9] [claim: studio graph audit 2026-11-02]

VOID took 236.9 s and peaked at 54.6 GiB on the lane, against the 38 GiB declared for it, so its reservation was raised to 58 GiB. One run, on a 96 GB card. [claim: studio graph audit 2026-11-02]

VOID's result, checked on 12 frames against the input: the chef is gone in every frame, with no head, torso or arm left, and the kitchen behind her is filled in steadily, while the pan, the flames and their motion stay. Pass 2 is slightly cleaner than pass 1. [claim: studio graph audit 2026-11-02]

VOID's flaw: the towel and ladle the chef held are not "person", so they stay in the mask's gap and float in mid-air by the pan for the whole clip. Naming them in the detection prompt ("person, towel, ladle") should remove them too; that has not been tried. Name everything the person holds or wears that should go. [claim: studio graph audit 2026-11-02] [inference]

VOID's repo record has not caught up. The family records file VOID under CogVideoX, with an older 240 s render and no peak; the 2026-11-02 run is not recorded in the repo yet. For CogVideoX itself, ask the older-video specialist. [run: studio/family_status.json] [inference]

Prism-Alpha still has no render. Checked on 2026-11-02: its four DiT files and the text encoder are on disk, but its video and audio VAEs (1.0 GB) are missing and no Prism node pack is in the library. [run: studio/family_status.json]

JoyAI-Video-Edit and LongCat-Image gained no new run in the last session; their single recorded renders in STATE.md still stand. [run: studio/family_status.json]
