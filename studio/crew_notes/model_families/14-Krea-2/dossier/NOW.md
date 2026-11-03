# Krea 2: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## What the records show

Krea 2 has two recorded renders, both from 2026-11-01 and unchanged since: Turbo (template krea2_turbo_t2i: bf16 loaded as fp8, 8 steps, CFG 1, euler, Qwen3-VL 4B encoder) at 25.3 s, seed 1477558560; and RAW (template krea2_raw_t2i: 52 steps, CFG 3.5, euler, with a real negative) at 60.4 s, seed 1649154201. No peak is recorded for either. [code: studio/family_templates/index.json] [run: studio/family_status.json]

## Training fails out of memory

Krea 2 RAW LoRA training failed out of memory on 1 and 2 November 2026: its own processes passed 73 GB at 512 px, rank 16, through ComfyUI's training node. There is no successful Krea 2 training record. [code: studio/train_bases.py:58] [docs: studio/crew_notes/studio_topics/04-Train/PITFALLS.md:27]

## Identity edit LoRA: downloaded, not yet in the studio

A community Krea 2 identity edit LoRA, version 1.2 at rank 128 (about 0.87 GB), was downloaded and checksum-checked on 2026-11-02 for character-swap work that is not in the studio yet. Versions up to 1.2 are under the Krea 2 Community License. Its V2 files add a separate licence that allows only non-commercial use, so V2 is not used. [claim: studio download records 2026-11-03]

## Licence

Krea 2 Community License: commercial use of the model, a LoRA or its outputs only for companies under US$1,000,000 total annual revenue, and content filtering is required. [code: studio/licences.py:65, studio/train_bases.py:26]
