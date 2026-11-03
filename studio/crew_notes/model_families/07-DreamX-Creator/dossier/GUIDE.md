# DreamX-Creator: how to write a prompt (checked 2026-11-03)

The long version of the DreamX-Creator notes, rewritten in plain words. Where this file and the older notes disagree, this file wins. The studio has no DreamX render on record, so everything below is from the paper, the official repository and tests on the studio this one grew from. Labels: "official" is the paper and repository; "earlier studio" is those older tests, not re-run here; "community" is third-party comments. [run: studio/family_status.json] [inference]

## What it is

DreamX-Creator 1.0 (Apache-2.0, September 2026) is a 7B model that makes video and sound together: separate video and audio streams that read each other through cross-attention. It needs a first frame; there is no text-only mode. It reuses the Wan 2.2 TI2V-5B VAE and the umt5-xxl text encoder, which reads 512 tokens. A separate one-step 2x refiner sharpens the picture and never touches the sound. [claim: official paper, arxiv.org/html/2608.31106] [claim: official repository, github.com/AMAP-ML/DreamX-Creator]

In the paper's own benchmark it led on picture quality and audio-video sync against LTX-2.3 and MiniMax H3, and trailed on audio quality and lip sync. The authors call it a trade-off, not a win. Community users describe it as "Wan 2.2 5B with audio". [claim: official paper] [claim: community comments]

On the earlier studio, talking, singing and a cartoon voice all came out right (one small word slip) with literal prompt-following and a still camera. Fast motion broke down into colour noise by about 2.5 seconds, and the sound was quieter than LTX or H3. Spoken words are not guaranteed: the pack's exact-word demo was dubbed afterwards. [claim: earlier studio tests] [claim: official node pack notes]

## Write it like its training captions

The training captions were written by a vision-language model in time order (subjects, action, scene, camera, speech, music, sound effects, ambience), with speech transcribed separately and merged back word for word into one fluent paragraph. Prompts that look like that work best. [claim: official paper, section 2.3]

The house shape, from the official example prompts: first the scene and the subject (look, clothes, setting, light); then one moderate, continuous action; then the speech, written as Man says, 'the exact line'.; then one sound sentence such as "The sound of rain on the window can be heard." [claim: official repository, audio_video_generation example cases]

Describe the start image, keep it to one continuous shot (training dropped clips with transitions), stay well under 512 tokens, and name the language: says in English, '...'. [claim: official paper] [claim: official node pack notes]

## The negative prompt works on both streams

The pack's default negative covers the picture (garish colour, overexposure, flicker, colour drift, deformation, background changes, blur, subtitles, watermark, low quality, extra fingers) and the sound (music, singing, ambient noise, other dialogue, English dialogue). Take out the parts you want: music and singing for a song, ambient noise for foley, and English dialogue when the line is in English. [claim: official node pack defaults, translated]

## Size, length and settings

Size is set in tokens of 32x32 pixels and follows the start image's shape: 576 tokens is 1024x576 at 16:9, the release default of 880 is 1248x704, and 1024 is 1344x768. Five seconds at 24 fps is 117 frames; longer is unverified. Sound is 48 kHz. [claim: official repository]

The release preset: text CFG 5, video and audio bridges 3.5 each, shifts 5 and 5, both cross-links on. The official script runs 50 steps; the ComfyUI pack's example runs 20. The guider makes three passes per step: text CFG steers prompt and speech, the video bridge sets how much the sound drives the picture (lips, impacts), and the audio bridge sets how much the picture drives the sound (foley timing). No official sweep of these exists. [claim: official repository] [claim: official node pack example]

## Keeping motion from collapsing

Only the first point is measured: fast motion broke at about 2.5 seconds. Untested ideas: shorter clips of 2 to 3 seconds, a start frame already mid-action, moderate verbs ("rolls slowly"), a camera that is said to stay still, and keeping flicker and deformation in the negative. The refiner can't rescue a clip that has already collapsed, so refine only clips you keep; it raised a sharpness score from 0.59 to 0.71 and lowered lip sync slightly. [claim: earlier studio tests] [claim: official paper] [inference]

## When to pick it

Against H3 and LTX-2.5 on the earlier studio: H3 for finished work and people, LTX-2.5 for drafts, volume, fast motion and camera moves, and DreamX for talking or still shots, optionally with the refiner. DreamX was the lightest of the three at about 26 to 28 GB. [claim: earlier studio three-way test]

## Template

[Subject, look and clothes] is [setting and light], keeping the original composition and colours. [He, she or it] [one moderate, continuous action], [one small detail]. The camera remains static. [Role noun] says in English, '[exact line]'. The sound of [ambience or foley] can be heard. [claim: earlier studio notes, built from the official example cases] [inference]
