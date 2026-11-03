# VLM captioning and tagging: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## Qwen3-VL reads a picture

The VLM family has its first recorded render, and STATE.md, rebuilt on 2026-11-03, now lists it. [run: studio/family_status.json] [docs: studio/crew_notes/model_families/27-VLM-captioning-tagging/dossier/STATE.md]

Qwen3-VL 4B (template vlm_qwen3vl_caption) reads a picture through ComfyUI's core TextGenerate node, with no node pack, and says what it sees and what looks physically wrong. It uses the 4.88 GB fp8 scaled file. The answer comes back as text through PreviewAny, and the 400-token limit can cut a long list short. [code: studio/family_templates/index.json]

Qwen3-VL's run on 2026-11-02, on the family's own instance: asked for three sentences on subject, setting and light, then a list of anything physically wrong, about the studio's Iris-3B fox picture. 9.5 s, peak 6.0 GiB, seed 20261102. The answer was read against the picture. [run: studio/family_status.json]

Qwen3-VL gave an accurate description and caught the picture's real fault, the stylised steam plume. It also made two errors: it put the steam at the fox's nose, when it floats well above, and it said breath only shows below -20 C, which is wrong. The list was cut at 400 tokens. Licence Apache-2.0. Check a VLM caption before you train on it or publish it. [run: studio/family_status.json] [inference]

## Where the test picture came from

Iris-3B, recorded as its own family, made the fox: Sperid Labs' 3B pixel-space model with no VAE, through the Iris-3B nodes (Apache-2.0, Pack Lab shortlist), 50 steps at CFG 3, 1024x1024. One run on 2026-11-02 on its own instance: 50.1 s, peak 8.5 GiB, seed 20261102. Sharp fur, snow and low sun; the asked-for breath vapour came out as a large smoke curl hanging above the fox. [code: studio/family_templates/index.json] [run: studio/family_status.json]

Iris-3B reads its words with Qwen3-VL-4B-Instruct, which the pack wants as a Hugging Face folder. The studio builds that folder from the repo's config and tokenizer plus Comfy-Org's single bf16 file, which holds the same 713 tensors under the same names. It is a different file from the fp8 one the caption template uses. [code: psn/instances.py:68-70, studio/family_templates/index.json]

## Still untested

The VLM family also lists ComfyUI's text templates for Gemma 4, Qwen3.5, Qwen3 and Qwen3-VL text generation. Only the caption template above has a recorded run. [run: studio/family_status.json]
