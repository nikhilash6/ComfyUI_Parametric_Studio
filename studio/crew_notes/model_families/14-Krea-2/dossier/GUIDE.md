# Krea 2: settings, prompt rules and what Krea 3 is (checked 2026-11-03)

This file gathers Krea's own published guidance for Krea 2, read for the studio this one grew from on 2026-10-17 and 2026-10-18, beside what this studio's templates use. Where this file and older notes in this folder disagree, this file wins. STATE.md holds what has rendered here. [inference]

## What this studio runs

The Turbo template loads krea2_turbo_bf16 as fp8, with the qwen3vl_4b text encoder (type krea2) and the Qwen Image VAE, and samples 8 steps at CFG 1 with euler and simple at 1024x1024. The negative is zeroed, so nothing typed there would count anyway. [code: studio/family_templates/krea2_turbo_t2i.json]

The RAW template samples 52 steps at CFG 3.5, euler and simple, at 1024x1024, with an empty negative. [code: studio/family_templates/krea2_raw_t2i.json]

## What Krea publishes

Turbo: Krea's README runs 8 steps, CFG 0 and mu 1.15 at 2048x2048, and says the model makes images from 1k to 2k. The diffusers docs also give 8 steps and guidance 0 with no negative. CFG 0 there and CFG 1 in ComfyUI both mean no guidance. [claim: krea-ai/krea-2 README, github.com/krea-ai/krea-2] [claim: diffusers Krea 2 pipeline docs] [inference]

The earlier studio tried mu 1.15 against the default and called it neutral, so the default stays. It rendered at about 1 MP only. 2 MP, which Krea supports, has not been tried here. [claim: earlier studio A/B, 2026-10-10] [docs: studio/processes/image-krea2-default.md]

RAW: Krea's README says 52 steps, CFG 3.5 and up to 1k, which is what the studio's RAW template uses. The diffusers docs say 28 steps at guidance 4.5. The two official sources disagree, and the studio follows the README. [claim: krea-ai/krea-2 README] [claim: diffusers Krea 2 pipeline docs] [code: studio/family_templates/krea2_raw_t2i.json]

## Writing for Krea 2

Write natural sentences. Krea says long, detailed prompts give the best results, but the model also does well with little prompt work. Put quotation marks around any words to be drawn in the picture. [claim: Krea 2 prompting guide, github.com/krea-ai/krea-2/blob/main/docs/prompting.md]

Krea's own prompt expander follows rules a prompt writer can copy. Be faithful to the request first. Write one paragraph, with no bullets, JSON or markdown. Quote the text that was asked for. Don't invent clothing, colours or materials the request didn't name. Only polish a prompt that is already detailed. Keep the medium the user asked for. The studio's prompt kits have no Krea 2 kit, so nothing here applies these rules yet. [claim: Krea 2 expansion rules, github.com/krea-ai/krea-2/blob/main/docs/expansion.txt] [code: studio/prompt_kits.json]

The earlier studio found Krea 2 drew quoted sign text exactly, handled counting and colour binding ("five mugs in order"), and got close but not exact on crowd counts (about six for "six people"). [docs: studio/processes/image-krea2-default.md]

## Licence

Krea 2 is under the Krea 2 Community License: commercial use of the model or its outputs only for companies under US$1,000,000 total annual revenue, with content filtering required. Read the licence itself before relying on that summary. [code: studio/licences.py:65]

## Krea 3 is not a local model

Krea 3, launched on 2026-10-15, is an image editing model with no downloadable weights. ComfyUI's own docs say there is nothing to download and nothing runs on your own GPU: it runs only through paid Partner Nodes. Repositories that call themselves "Krea v3" are an unrelated community FLUX.1 checkpoint from 2025. For a local edit, use Qwen-Image or FLUX.2 Klein instead. [claim: docs.comfy.org Krea 3 partner node tutorial] [claim: earlier studio research, 2026-10-18] [inference]
