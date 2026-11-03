# Checking a batch of generated images

How others score a batch of generated pictures on one GPU, in the order the research suggests, and why an "AI detector" score can't be used as a pass or fail. This comes from research for the studio this one grew from (2026-10-17). Each source was fetched then; none of these tools is installed or wired into this studio, and nothing here was run on it.

All of these are triage. The contact sheet and a person's eye stay the final judge.

## A suggested order

1. **Prompt adherence:** does the picture show what was asked? Use VQAScore first.
2. **Exact text:** run OCR on any words quoted in the prompt.
3. **Identity:** for a character job, compare face embeddings against the reference.
4. **Preference:** use a preference scorer only to choose between takes of the same prompt.
5. **A person last:** hands, faces, finger and limb counts, jewellery and garment edges, and whether it looks real.

## The tools

**VQAScore** (`t2v_metrics`, ECCV 2024) checks prompt adherence by asking a vision-language model "does this image show <prompt>?" and taking the probability of yes. Version 3.1 (2026-06-04) supports Qwen3-VL from 2B to 32B, Qwen3.5 and Gemma 3. A small Qwen3-VL scorer could sit beside a render model, but its memory use was not measured. Source: github.com/linzhiqiu/t2v_metrics.

**OCR text check.** A VLM or an OCR engine reads the picture's text, then you measure the Levenshtein edit distance to the quoted string. Count a string as passing only at edit distance 0, and count a case mismatch as an edit. That is how OneIG-Bench scores text (NeurIPS 2025 datasets track, with Qwen2.5-VL-7B as the reader). Source: arxiv.org/abs/2506.07977.

**GenEval** checks counting, colour, position and co-occurrence with an object detector, so it suits "five mugs in a row" prompts. It needs mmdet 2.x in its own environment. Source: github.com/djghosh13/geneval.

**HPSv3** (ICCV 2025) is a human-preference score built on Qwen2-VL-7B and trained on 1.08 million images. It ranks takes but doesn't test adherence. Its install pins flash-attn, so it needs its own environment. Source: github.com/MizzenAI/HPSv3.

**ImageReward** (NeurIPS 2023) is the lightest preference scorer, trained on 137,000 expert pairs. It is older, and probably weaker on current models; that last part is our guess. Source: github.com/THUDM/ImageReward.

Install any of these into a separate environment, never into the ComfyUI one: several pin libraries that ComfyUI also uses.

## Why a detector score is not a gate

**Detectors are unreliable.** A 2026 benchmark tested 16 detectors (23 variants) on 12 datasets: 2.6 million images from 291 generators. The best mean accuracy was 75% and the worst 37.5%. Pictures from FLUX.1 Dev were caught 21% of the time on average, and the rankings changed a lot from dataset to dataset. Source: arxiv.org/abs/2602.07814.

**Ordinary post-processing breaks them.** After JPEG compression or resizing, detectors fall back to calling a picture real. One detector scored 99.9% on real pictures but caught only 21.5% of FLUX pictures. Another fell from catching 95.9% of fakes to 12.2% after post-processing. Source: arxiv.org/abs/2606.10309.

So a public detector score proves nothing either way. Don't use one to pass or refuse a release.
