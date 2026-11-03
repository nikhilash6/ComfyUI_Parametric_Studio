# HunyuanVideo 1.5: how to write a prompt (checked 2026-11-03)

The long version of the HunyuanVideo 1.5 notes, rewritten in plain words. Where this file and the older notes disagree, this file wins. This folder's family record has no render on record in the studio, so the facts below come from Tencent's repository, its prompt handbook, ComfyUI's template and tests on the studio this one grew from. Labels: "official" is Tencent's repository, model card and handbook; "earlier studio" is those older tests, not re-run here; "community" is forum reports we read but did not test. [run: studio/family_status.json] [inference]

## What it is good and bad at

HunyuanVideo 1.5 is one 8.3B model (Wan 2.2 A14B is a pair of 14B experts) that makes 121 frames at 24 fps, 5 seconds, by default. It keeps the first frame's face and colours well in image to video, gives lifelike small motion (hair, cloth, expressions), and can draw English or Chinese text in the video through its glyph encoder. It makes no sound. [claim: official repository, github.com/Tencent-Hunyuan/HunyuanVideo-1.5] [claim: community reports comparing it with Wan 2.2]

It needs detailed prompts: Tencent's own pipeline rewrites every prompt with a language model by default, and short prompts do worse. Community testers rate Wan 2.2 better on physics, fast action and hands, and report that it can ignore camera moves and stay still. It looks best at 1280x720. [claim: official repository] [claim: community reports]

The licence is the Tencent Hunyuan Community licence, not an open-source one, and the model card shuts out the EU. Read it before you rely on it. [claim: official model card, huggingface.co/tencent/HunyuanVideo-1.5]

## Settings for the 720p image-to-video model (CFG-distilled)

CFG 1 (the distilled model has no negative pass, so a negative prompt does nothing), flow shift 7 (text-to-video 720p uses 9, and 480p uses 5), euler with the simple scheduler, 121 frames at 24 fps (use 4n+1 frame counts) and 1280x720. Tencent says this model must run 50 steps for correct results; ComfyUI's template ships 20 for speed, so treat fewer steps as a draft. [claim: official repository settings table] [claim: ComfyUI template video_hunyuan_video_1.5_720p_i2v]

If you decode with tiles, set the temporal tile size to its maximum (4096), or it leaves artefacts. The optional cache node lowers quality and is off in the template. [claim: Tencent ComfyUI notes, github.com/Tencent-Hunyuan/HunyuanVideo-1.5 ComfyUI/README.md] [claim: ComfyUI template]

The 1080p super-resolution pass runs CFG 1, shift 2 and 8 steps; the 480p-to-720p pass runs shift 2 and 6 steps. A step-distilled model exists only for 480p image to video (8 or 12 steps, shift 7, CFG 1). [claim: official repository]

On the earlier studio, a 720x960, 61-frame image-to-video test at 50 steps, CFG 1 and shift 7 took 276 seconds including model load; it followed a head tilt, panting and a push-in, and kept the dog's identity and colours. [claim: earlier studio test]

## The official formula

Image to video: subject motion, then scene motion, then the camera move if you want one. The picture already gives the subject, style and light, so describe the change, not the picture. Text to video uses the longer form: subject, motion, scene, shot, camera, lighting, style, atmosphere. [claim: official prompt handbook, assets/HunyuanVideo_1_5_Prompt_Handbook_EN.md]

There's no official word count. Tencent says longer, detailed prompts help, and its own image-to-video examples run about 40 to 120 words; "keep it concise" in the handbook means plain sentences with many concrete details. [claim: official prompt handbook] [inference]

## Rules from Tencent's own prompt rewriter

Tencent's image-to-video rewriter (written in Chinese) follows these rules, summarised here in our words. [claim: official rewriter prompt, hyvideo/utils/rewrite/i2v_prompt.py]

1. Camera words only when you want a move, and only standard ones. Don't add a move nobody asked for, and don't write "the camera remains static" unless you mean it. 2. Make a small timeline: action A, then B, while C. 3. Subject, manner, action, described objectively: "the corners of her mouth lift", not "she is happy". 4. Say where things are: "from the right side of the frame", "in the background", "exits at the bottom". 5. No vague pronouns: name who does what. 6. Restraint: no big actions nobody asked for; light background motion is fine; don't add lighting unless asked. 7. Text in quotes stays word for word in its own language and is never spelled out letter by letter. [claim: official rewriter prompt]

The rewriter writes Chinese even for English input, but English prompts are officially supported. Whether Chinese works better on the quantised weights is untested. [claim: official prompt handbook] [inference]

## Camera words

Use the handbook's own phrases: the camera moves upward, downward, left, right, forward (dolly in) or back (dolly out); tilts up or down; pans left or right; circles around; rotates 360 degrees; follows; remains static; handheld shot. [claim: official prompt handbook]

## Text in the video

Put the words in double quotes and say where they appear: Subsequently, the text "OPEN LATE" appears in the upper left corner of the frame. [claim: official prompt handbook]

## When to pick it

Reach for HunyuanVideo 1.5 to animate an exact face, product or drawing gently, or when the clip needs on-screen text. Use Wan 2.2 for action and physics, and LTX-2.5 when you need sound. Some comparison tables online get its size and licence wrong (13B, Apache-2.0); it is 8.3B under Tencent's own licence. [claim: community reports] [claim: official repository] [inference]

## Template (image to video)

[Camera move, if any]. [The subject as seen in the picture] [manner] [first action], then [second action], while [hair, cloth or props move]. [Something in the background] [moves gently]. [Optional: the text "WORDS" appears in the upper centre of the frame.] [claim: earlier studio notes, built from the official rules] [inference]

Example, our own: The camera slowly moves forward. The old fisherman lifts his head from the net and squints toward the right side of the frame, then raises one hand to shade his eyes, while the loose ends of his scarf flutter. In the background, gulls drift across a pale sky and small waves roll onto the shingle. [inference]
