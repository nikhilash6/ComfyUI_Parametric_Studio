# Pony, Illustrious and NoobAI: tag prompts and settings (checked 2026-11-03)

These SDXL-based anime models want tag lists and their own settings, not the general SDXL defaults. This file comes from research done for the studio this one grew from: the NoobAI model card read on 2026-10-17, third-party guides and a count of public community prompts. None of these models has been rendered on this studio. Where this file and older notes in this folder disagree, this file wins. [inference]

Labels: "community count" means public prompts posted with images on a model-sharing site, counted by rule-based tags. It measures habit and popularity, not quality. [inference]

## Settings

NoobAI-XL 1.1: Euler a, CFG 5 to 6, 25 to 30 steps, a total area near 1024x1024. The card's best buckets are 768x1344, 832x1216, 896x1152, 1024x1024, 1152x896, 1216x832 and 1344x768. [claim: NoobAI-XL 1.1 model card, huggingface.co/Laxhar/noobai-XL-1.1]

Community count: Illustrious and NoobAI posts mostly use Euler a, 30 steps, CFG 5 and 832x1216. Pony posts use CFG 7. [claim: earlier studio community prompt count, 2026-10-18]

v-prediction builds are different. A mirror of the NoobAI v-pred card says Euler only, CFG 4 to 5, 28 to 35 steps. Another guide says Euler a at CFG 2 to 3.5 with a CFG rescale near 0.5. The two disagree, so read the card of the exact model. A wrong prediction type gives washed-out or burned pictures. [claim: tkj.ai NoobAI page, a mirror] [claim: lunabooru generation settings guide, third party] [inference]

Clip skip: Pony wants 2. Illustrious and NoobAI use the default, no skip. [claim: lunabooru generation settings guide, third party]

## Prompts

These models were trained on booru tags, so write comma-separated tags, not sentences. Community count: 92 to 97% of prompts on these bases are tag lists, median 58 to 72 words. [claim: earlier studio community prompt count, 2026-10-18]

NoobAI's card gives a quality prefix: "masterpiece, best quality, newest, absurdres, highres". The quality tags map to score percentiles: masterpiece above the 95th, best quality 85 to 95, good quality 60 to 85, normal quality 30 to 60, worst quality 30 and below. Date tags old, early, mid, recent and newest steer the drawing era. [claim: NoobAI-XL 1.1 model card]

A suggested tag order: subject count, character, series, artist, general tags, other, then quality. Use spaces, not underscores, and escape brackets that belong to a tag. [claim: BetterWaifu NoobAI guide, third party]

Each family has its own quality block. Pony uses score_9, score_8_up, score_7_up: 80% of Pony prompts overall, falling from 93% in 2024 to 37 to 69% in 2026 as "masterpiece, best quality" took over. Illustrious and NoobAI prompts carry "masterpiece, best quality, newest, absurdres, very aesthetic" in 88 to 98% of posts. [claim: earlier studio community prompt count, 2026-10-18]

Negatives are the norm on these bases (92 to 95% of posts), and LoRA trigger words usually sit in the middle of the prompt (64%), not first. The most-liked Illustrious prompts used far fewer trigger words than the rest (2% against 20%). [claim: earlier studio community prompt count, 2026-10-18]

Don't use the general SDXL defaults here. A photoreal SDXL setting (CFG 3 to 5, DPM++ 2M SDE, clip skip 1) or the base setting (dpmpp_2m karras at CFG 6) is not what these cards ask for. [inference]
