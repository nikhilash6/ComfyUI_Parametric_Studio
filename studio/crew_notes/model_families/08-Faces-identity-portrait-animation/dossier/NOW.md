# LongCat-Video-Avatar 1.5: state on 2026-11-03

Where this file and older notes disagree, this file and STATE.md win. The older notes in this folder and in the Prism, LongCat, VOID and JoyAI folder repeat the model card's audio CFG tip of 3 to 5. The earlier studio's side-by-side test found the opposite, so keep audio CFG at 1. [docs: studio/processes/avatar-longcat.md] [inference]

## It does not run here yet

LongCat-Avatar-15 was checked on 2026-11-02 and did not render: the 31.7 GB DiT and its DMD LoRA are missing. The Whisper audio encoders are present. [run: studio/family_status.json:4639]

## What the earlier studio measured

A still of a person plus a voice clip gave a 3.72 s, 93-frame, 25 fps lip-synced clip with the voice muxed in. The graph: the LongCat-Avatar-15 DiT in bf16 with the DMD distill LoRA (rank 128) at 1.0, the Whisper-large-v3 encoder feeding the LongCat audio embeds (loudness normalised), the longcat_distill_euler schedule, 8 steps, shift 7, sampler CFG 1. [docs: studio/processes/avatar-longcat.md]

Audio CFG 1 against 4, same still, line and seed: at 4 the lips inflated into a glossy round "O" on open vowels; at 1 they moved naturally. A second run of the studio's own graph reproduced the CFG 4 clip frame for frame. Audio CFG 1 is also the value in the official inference script, while the card's text says 3 to 5. One visual comparison, never judged by ear for lip sync. [docs: studio/processes/avatar-longcat.md]

Timings on that studio: 132 s at 480x832 with audio CFG 1 and a peak of 55,670 MiB, 296 s at 768x1280 after a first try ran out of memory on a full card. Audio longer than 3.72 s was cut at one segment. [docs: studio/processes/avatar-longcat.md]

LongCat-Avatar 1.5 is an 8-step distilled model with hidden size 4096, so it is not a Wan 14B and Wan 14B LoRAs and settings don't carry over. [claim: earlier studio notes, 2026-10-16]
