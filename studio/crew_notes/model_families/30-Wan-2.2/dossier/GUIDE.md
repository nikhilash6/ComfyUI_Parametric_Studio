# Wan 2.2: how to write a prompt (checked 2026-11-03)

The long version of the Wan 2.2 prompting notes, rewritten in plain words. Where this file and PROMPTING.md disagree, this file wins. Labels: "official" is Alibaba's Model Studio guide, the Wan 2.2 repository and the model cards; "earlier studio" is tests run on the studio this one grew from, not re-run here; "community" is third-party pages we read but did not test. [inference]

## What the studio runs

The "Video" and "Animate" goals use Wan 2.2 TI2V-5B at 20 steps, CFG 5, shift 8 and uni_pc, with Wan's own Chinese negative prompt. Because CFG is above 1, the negative prompt does work on these goals. [code: studio/goals.py:153-154] [code: studio/goals.py:11] [code: workflows/wan22_5b_t2v_api.json]

Frame counts are 4k+1 at 24 fps, so 5 seconds is 121 frames. The 5B model is the 720p, 24 fps model; the larger A14B experts run at 16 fps with 81 frames. [code: studio/goals.py:16] [claim: official Wan 2.2 repository, github.com/Wan-Video/Wan2.2]

## The official formula

Text to video: entity, then scene, then motion. For more control, add aesthetic words (light, composition, colour) and a style. Image to video: only motion and camera, because the picture already gives the subject and the place. Don't describe the picture again; I2V that barely moves usually means the prompt described the image instead of what moves. [claim: Alibaba Model Studio prompt guide, alibabacloud.com/help/en/model-studio/text-to-video-prompt]

The official guide gives no word limit. The text encoder (umt5-xxl) reads 512 tokens, so 40 to 100 words is a sensible target; the often-quoted "80 to 120 words" comes from a third-party page. [claim: official Wan 2.2 repository, shared_config.py] [claim: community guide, viewcomfy.com Wan 2.2 prompt guide] [inference]

The official repository can extend short prompts with a Qwen model first. ComfyUI does no extension unless you add a language-model step, so write the detail yourself. [claim: official Wan 2.2 repository] [inference]

Avoid, per the official guide: real people by name, fast scene changes inside one clip, readable text, long chains of actions, and lip sync to exact words. Use adverbs for intensity: "quickly", "slowly". [claim: Alibaba Model Studio prompt guide]

## Aesthetic words the model was labelled with

The model cards say training data was labelled for lighting, composition, contrast and colour. The official samples put these tags first, then the subject. [claim: Wan 2.2 model cards, huggingface.co/Wan-AI/Wan2.2-TI2V-5B] [claim: community mirror of the official vocabulary, wan2.video/wan2.2-guide]

| Control | Words [claim: community mirror of the official vocabulary, wan2.video/wan2.2-guide] |
|---|---|
| Light source | daylight, artificial light, moonlight, practical light, firelight, fluorescent, overcast, mixed light, sunlight |
| Light quality | soft, hard, top, side, back, bottom, rim light, silhouette, low contrast, high contrast |
| Time of day | daytime, nighttime, dusk, sunset, dawn, sunrise |
| Shot size | close-up, medium close-up, medium shot, medium long shot, long shot, full shot, wide angle |
| Composition | centred, balanced, left or right weighted, symmetrical, short-siding |
| Lens and angle | medium focal length, wide angle, telephoto, fisheye; over-the-shoulder, high angle, low angle, tilted, aerial, top-down |
| Colour | warm, cool, high saturation, low saturation |
| Style | 3D cartoon, pixel art, anime, watercolour, oil painting |

The style must lead as the subject. "Anime cel-shaded illustration of a ribeye steak" came out anime; the same style tag in sixth place, after lighting and lens tags, came out photoreal. [claim: earlier studio tests]

## Camera

One camera move per 5-second clip, said plainly. Official words: push in, pull out, pan left or right, tilt up; advanced: handheld, following, orbit. A combined move works when it is one beat ("the camera dollies back and tilts up at the same time"). If you want no move, write "static shot" or "locked-off camera", or the camera may drift. Small orbits (10 to 20 degrees) are steadier. [claim: Alibaba Model Studio prompt guide] [claim: community guide, aikolhub.com Wan 2.2 camera guide] [code: psn/camera.py:1]

"An FPV drone races through the canyon" drew a quadcopter in the frame. For a drone point of view, write "first-person FPV view, the camera races through the canyon", and never make the drone the subject. [claim: earlier studio tests]

Depth helps: "foreground grass sways while the mountains stay still". No source covers dolly zoom; treat it as unreliable. [claim: community guide, viewcomfy.com Wan 2.2 prompt guide] [inference]

## Motion

Use a concrete verb with an adverb, and name the body part and direction: "raises her right arm overhead", "turns 90 degrees to the left". For subtle life: a blink, a gentle sway, hair moving in the breeze. Keep to two or three beats in 5 seconds, joined with "then". [claim: Alibaba Model Studio prompt guide] [claim: community guide, wan-animate.com I2V guide]

A 12-second prompt with several events (a collision, then bullet time) collapsed into plain walking. Wan also could not do "giant hands come from the sides and take off the jacket" at any setting; budget for effects like that in compositing or on another model. [claim: earlier studio tests]

For a still face in I2V: small movements, a fixed lens, soft light, and an anchor line such as "her face and the room stay identical". [claim: community guide, wan-animate.com I2V guide] [claim: earlier studio tests]

## Things that go wrong

Asking for "space for a logo" produced fake neon text. Never mention logos, signs or empty text areas; leave the room implicit ("centred subject, a plain wall to the right") and add text later. Colour and era words drift ("dark green 1990s coupe" came out teal and 80s-looking), so use strong colour names such as "deep British racing green". [claim: earlier studio tests]

Static I2V: describe only motion and camera. Ghosting or blur with speed LoRAs: load one high-noise and one low-noise LoRA, never two of the same kind. Very large motion can reverse direction, as the Lightning card warns. [claim: Lightning model card, huggingface.co/lightx2v/Wan2.2-Lightning] [claim: community thread, huggingface.co/lightx2v/Wan2.2-Lightning/discussions/25]

## The negative prompt

Wan's official negative prompt is in Chinese and lists garish colour, overexposure, static frames, blur, subtitles, "artwork" and "painting", grey cast, low quality, JPEG artefacts, extra or fused fingers, badly drawn hands and faces, deformed limbs, cluttered backgrounds, three legs, crowds in the background and walking backwards. The studio sends it unchanged. [claim: official Wan 2.2 repository, shared_config.py] [code: studio/goals.py:11]

A negative prompt only works where CFG is above 1. At CFG 1, which is how four-step distilled (Lightning) setups run, there is nothing to subtract, so put any constraint in the positive prompt ("static camera", "the face stays identical"). [inference]

## Settings that change how prompts behave (A14B)

Official non-distilled defaults: image-to-video A14B uses shift 5, 40 steps, guidance 3.5 and an expert switch at 0.900; text-to-video A14B uses shift 12, 40 steps, guidance 3.0 and 4.0 and a switch at 0.875. [claim: official Wan 2.2 repository, wan_i2v_A14B.py and wan_t2v_A14B.py]

With Lightning four-step LoRAs on A14B: the v1030 high-noise LoRA gave much stronger camera motion than v1; a motion-enhancer LoRA damped camera moves; and real CFG 3.5 on the high stage drifted away from the reference room, so keep the high stage at CFG 1 for faithful I2V. Shift 5 followed camera instructions better, and shift 8 held structure and detail better. [claim: earlier studio tests]

## LoRA trigger words

Most Wan LoRAs want their trigger at the start of the prompt, followed by a normal scene sentence. Many use a whole fixed sentence as the trigger; copy it exactly, author spelling included. A trigger alone does not hold a character's look, so describe the defining features too. [claim: earlier studio research notes, from each LoRA's own card] [claim: community blog, ai-muninn.com character LoRA guide]

In I2V the first frame fixes the subject and the place, so the trigger sentence brings the motion and the camera. Some LoRAs depend on the still: a rack-focus LoRA works best when the photo already has blur, and an anime-style LoRA had no effect from a photo. [claim: earlier studio research notes]

The high-noise expert decides layout, motion and camera; the low-noise expert decides texture and detail. Camera and motion LoRAs go on high, look and texture LoRAs on low, and a paired file only works on its own expert: swapped, it gives a blurry mess. [claim: community blog, spicyapi.ai Wan 2.2 high and low noise guide] [claim: earlier studio research notes]

Never tell a camera-move LoRA "static camera". A motion LoRA and a camera LoRA fight over the same high-noise expert, so lower both or use separate clips. Don't use LoRAs trained on Wan 2.2 with Wan Animate; its model card warns against it. [claim: earlier studio research notes] [claim: Wan 2.2 Animate model card, huggingface.co/Wan-AI/Wan2.2-Animate-14B]

## Templates

Text to video: [style or medium], [shot size], [light source and quality], [time of day], [colour], [composition and lens]. [Subject with two or three visual details] in [a place with one or two props]. [Action], then [second action]. Camera: [one move, with a speed]. [What moves in the background]. [claim: Alibaba Model Studio prompt guide] [inference]

Image to video: [subject] [verb, adverb, direction]. [Optional second beat with "then"]. [Something in the place that moves]. Camera [one move, slow or fast]. [Anchor: "her face and the room stay identical"]. [claim: Alibaba Model Studio prompt guide] [inference]
