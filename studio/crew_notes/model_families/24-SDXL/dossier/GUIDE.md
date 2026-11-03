# SDXL: settings and prompts for fine-tuned checkpoints (checked 2026-11-03)

PLAYBOOK.md says it lists no steps or CFG for SDXL. This file fills that gap from research done for the studio this one grew from: checkpoint authors' own pages, read on 2026-10-17, and a count of public community prompts. Nothing here was re-rendered for this studio. Where this file and older notes in this folder disagree, this file wins. Tag-based anime bases (Pony, Illustrious, NoobAI) have their own guide in the Pony, Illustrious and NoobAI folder. [inference]

Labels: "author's page" means a checkpoint author's published card. A mirror or third-party guide gets a claim label naming it. "Community count" means public prompts posted with images on a model-sharing site, counted by rule-based tags: it measures what people post, not what renders best. [inference]

## What this studio's SDXL templates use

The studio's SDXL family templates load the SDXL 1.0 base checkpoint and sample with dpmpp_2m and the karras schedule at CFG 6, 25 to 30 steps, at buckets such as 1024x1024, 832x1216 and 1216x672. That is a sensible base-model setting. It is not what photoreal fine-tunes ask for. [code: studio/family_templates/sdxl_controlnet_depth.json, studio/family_templates/sdxl_controlnet_openpose.json, studio/family_templates/ipa_ip_adapter_sdxl.json]

## Photoreal fine-tunes: run lower CFG

Photoreal SDXL fine-tune authors ask for low CFG, which is how they avoid plastic skin. One author gives DPM++ 2M SDE with karras, 30 or more steps, CFG 3 to 5, clip skip 1, 832x1216 or 896x1152, then a 1.5x upscale at 0.3 to 0.35 denoise. [claim: CyberRealistic XL author's page, v10, read 2026-10-17]

Another author gives 832x1216, DPM++ 2M karras, 30 to 40 steps and CFG 3 to 7, with the note "lower = more realistic". The same card says to start with no negative prompt, because heavy negatives often hurt, and gives a hires pass at 1.5x, 15 steps and 0.3 denoise. [claim: Juggernaut XL v9 model card, huggingface.co/RunDiffusion/Juggernaut-XL-v9]

A survey of 16 non-distilled SDXL checkpoints on the earlier studio found 11 of them at CFG 5 or below. Five authors asked for 6 to 7.5. So CFG 6 is above most photoreal authors' range, and a new photoreal checkpoint should start near CFG 4.5 with dpmpp_2m_sde and karras unless its own card says otherwise. [claim: earlier studio checkpoint survey, 2026-10-17] [inference]

A model's page on one site can lag another. One author's Hugging Face card still showed an older version at CFG 7 to 8 while the newer card on another site said 3 to 5. Read the card for the exact version you have. [claim: earlier studio research, 2026-10-17]

## Distilled SDXL builds

Fast distilled builds (DMD2, Lightning) run very differently: an LCM sampler with an exponential or karras schedule, 4 to 12 steps and CFG 1 to 2. At CFG 1 the negative prompt does nothing. [claim: CyberRealistic XL author's page, DMD2 variant] [claim: Juggernaut Lightning author post]

## Prompts

For photoreal fine-tunes: short prose or prose with a few camera tags, subject first, then light, then camera. Keep the negative short, for example "cartoon, illustration, anime, painting, CGI, 3D render, low quality, watermark, logo, label". [claim: CyberRealistic XL author's page]

Faces far from the camera and hands come out soft or wrong at base resolution. A hires pass at 1.4 to 1.5x and 0.3 to 0.4 denoise, or a face detailer, is the authors' fix. SDXL miscounts and garbles text, so don't ask it for lettering. [claim: earlier studio research, 2026-10-17] [inference]

Clip skip stays at 1 for SDXL photoreal models. Only Pony-based models want clip skip 2. [claim: lunabooru generation settings guide, third party]

## What people post

Community count, SDXL 1.0 and its distilled variants: prompts are mixed, 44 to 61% tag lists and the rest sentences. Negatives are the norm (86%), emphasis weights are common (40 to 48%) and LoRA stacking is heavy: 74% use at least one, 38% three or more. The most-liked prompts use fewer LoRA trigger words and are slightly shorter than the rest. [claim: earlier studio community prompt count, 2026-10-18, about 115,000 distinct SDXL-family prompts]
