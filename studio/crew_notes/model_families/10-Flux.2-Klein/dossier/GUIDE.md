# FLUX Klein (FLUX.2 and FLUX.3): how to write a prompt (checked 2026-11-03)

How the Klein models want their prompts, rewritten in plain words from the prompt upsampler Black Forest Labs publishes for FLUX.3 Klein. The upsampler's system prompts are summarised here and linked, not copied. Where this file and older notes disagree, this file wins. The same rules are the writer's notes in the studio's prompt kits, for the Image goal (FLUX.2 Klein 4B) and the FLUX.3 and Product goals (FLUX.3 Klein). [claim: BFL FLUX.3 Klein upsampler prompts, huggingface.co/black-forest-labs/flux-3-image-klein-pup] [code: studio/prompt_kits.json] [code: studio/goals.py:152]

## Text to image

Write one continuous English caption: it is exactly what the image model reads. Without a stated style, plan a real photograph and open with the medium ("Full-color outdoor photograph,", "Studio photograph,"); keep "photorealistic" for renders. Then the scene, light and camera, then the subjects with concrete colours, materials and state. [claim: BFL FLUX.3 Klein upsampler prompts]

Give every person in focus an observable description: age range, skin tone, hair and clothes. Place things with frame words (frame-left, foreground, background) and sentence-opening anchors ("On the left, ..."). Describe up to about ten things one by one, and beyond that give the count and arrangement. The background is shapes and colours, about a sixth of the caption. [claim: BFL FLUX.3 Klein upsampler prompts]

Be definite: no hedging, no judgements of quality or mood, no closing sentence about the mood, and say what is there rather than what isn't. Never write "this image shows" or "we can see". Quote rendered text exactly, with its typography, colour and place. Add blur or depth of field only when asked. Never invent brands, logos or famous people. A few ordinary, imperfect details from the scene's own objects beat the stock-photo ideal. The upsampler's own range is 100 to 350 words. [claim: BFL FLUX.3 Klein upsampler prompts]

## Editing

One instruction. When one picture stays and gets bounded changes, use the imperative ("Remove the ...", "Change the ... to ..."); when pictures are combined into a new frame, ask for a new picture and say what to take from each one, by order. State every end state concretely, cover the knock-on effects (shadows, reflections, scale, light) and what fills a removed area, and end with one short clause naming what stays the same. 50 to 150 words. [claim: BFL FLUX.3 Klein upsampler prompts]

## Settings

Both studio graphs run at CFG 1, so a negative prompt has nothing to act on: FLUX.3 Klein at 15 steps with er_sde, and FLUX.2 Klein through its own guider. FLUX.2 Klein is guidance-distilled and its card's example uses guidance 1.0. Whether the FLUX.3 caption style suits FLUX.2 Klein as well is our inference. [code: workflows/flux3_klein_core_t2i_api.json] [code: workflows/flux2_klein4b_t2i_api.json] [claim: FLUX.2 Klein 4B model card, huggingface.co/black-forest-labs/FLUX.2-klein-4B] [inference]
