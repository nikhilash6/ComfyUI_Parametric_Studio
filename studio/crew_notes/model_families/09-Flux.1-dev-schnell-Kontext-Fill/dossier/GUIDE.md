# FLUX.1: how people prompt it and what Black Forest Labs advises (checked 2026-11-03)

This file gathers Black Forest Labs' general prompting advice and a count of public FLUX.1 prompts, both from research for the studio this one grew from. STATE.md holds what has rendered here. Where this file and older notes in this folder disagree on how to write a prompt, this file wins. [inference]

## Settings

This studio's Schnell template runs 4 steps at CFG 1 with euler and simple at 1024x1024; its FluxGuidance value of 3.5 is the distilled guidance, not CFG. [code: studio/family_templates/flux1_schnell_t2i.json]

In a count of public FLUX.1 posts, 71% used distilled guidance 3.5. Dev posts ran 20 to 30 steps with euler and the simple or beta schedule, Schnell 4 steps. 85% were portrait, most often 832x1216. [claim: earlier studio community prompt count, 2026-10-18, about 48,700 distinct prompts]

## Writing for FLUX

Write sentences. Most FLUX models don't support negative prompts, so say what you want instead of what you don't. [claim: Black Forest Labs prompting docs, docs.bfl.ai]

Name the camera and lens rather than saying "professional photo", and ask for real texture: pores, fabric wear, small imperfections. Light is the biggest single lever: name its source, quality, direction and colour. Concrete descriptions beat labels like "aesthetic" or "professional". [claim: Black Forest Labs prompting docs, docs.bfl.ai and docs.bfl.ml]

What people post: 70 to 81% of FLUX.1 prompts are sentences, with a median of 79 words for Dev, 101 for Krea, 60 for Schnell and 42 for Kontext edit instructions. Old Stable Diffusion habits linger (quality tags in 54%, negatives in 14%, weight syntax in 15%), but the most-liked tenth of prompts use fewer of them (negatives 6% against 16%, weights 7% against 14%) and name light and style more. Trigger words sit anywhere in the prompt, with no single habit. Popularity is not quality. [claim: earlier studio community prompt count, 2026-10-18]

Kontext edits are short instructions, not scene descriptions: the median public Kontext prompt was 42 words. [claim: earlier studio community prompt count, 2026-10-18]
