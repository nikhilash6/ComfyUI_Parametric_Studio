# LTX-2.5: how to write a prompt (checked 2026-11-03)

The long version of the LTX-2.5 notes, rewritten in plain words. PROMPTING.md says the sources give no structure; they do, and this file has it. Where the two disagree, this file wins. Labels: "official" is Lightricks' prompting guide, model card, repository and ComfyUI templates; "earlier studio" is tests run on the studio this one grew from, not re-run here; "community" is third-party reports we read but did not test. [inference]

## What LTX-2.5 is

LTX-2.5 (Lightricks, August 2026) is one model that makes video and its sound together, with a custom Gemma 4 12B text encoder. Stock Gemma 4 is not a substitute. It ships as a distilled transformer (a fixed 8-step schedule at CFG 1) and a full "dev" transformer for training. [claim: official model card, huggingface.co/Lightricks/LTX-2.5] [code: studio/goals.py:159-160]

The licence is the LTX-2.x Community License, not Apache. Use is free below a company revenue threshold, LoRAs and fine-tunes count as derivatives under the same licence, and there is an acceptable-use policy that includes saying content is machine-generated. Read the licence itself; this is not legal advice. [claim: official licence text, github.com/Lightricks/LTX-2 LICENSE]

## What the studio runs

The "Video + sound" and "Animate + sound" goals run one distilled stage: euler_ancestral, CFG 1, and the official sigma list from 1.0 down to 0.0 in nine values. For image to video, the start picture goes through LTXVPreprocess at compression 18 (a video-codec round trip that matches the training data) and in at strength 0.7, which leaves room for motion. No prompt enhancer runs, so your prompt goes to the model as you wrote it. [code: workflows/ltx25_core_t2v_api.json] [code: workflows/ltx25_core_i2v_api.json] [claim: official ComfyUI template video_ltx2_5_i2v]

Frame counts are 8k+1 (121 frames is 5 seconds at 24 fps), and width and height must divide by 32, so 1280x720 becomes 1280x704. [code: studio/goals.py:15] [claim: official model card]

Raising CFG on the distilled model doesn't help; if you must, stay between 1.0 and 1.5. At CFG 1 the negative prompt has no branch to work on, so the studio's negative is there for completeness. [claim: official ComfyUI-LTXVideo notes] [code: studio/goals.py:10] [inference]

## The official shape

One flowing paragraph in the present tense, four to eight sentences for one shot. Cover six things in order: the shot, the scene (light, colours, textures), the action from start to end, the characters (age, hair, clothes, a distinguishing feature, and emotion shown as physical cues), the camera (one move and how the frame ends) and the sound (ambience, music, and speech in quotes with the voice and accent). [claim: official LTX prompting guide, docs.ltx.io] [claim: official LTX blog, ltx.video/blog/how-to-prompt-for-ltx-2]

Start straight with the action, never "The scene opens" or "We see". Describe objectively: "her eyebrows angle downward", not "she is sad". Use time connectors: "Initially", "A moment later", "At the same time". Don't add "Audio:" or "Visual:" labels. The enhancer's own captions run 150 to 220 words, which shows the length the model knows best. [claim: official enhancer system prompt in ComfyUI-LTXVideo] [claim: official LTX prompting guide]

Speech: put the words in quotes with the voice before them: she says in a calm, warm voice: "...". Tie each sound to the action it belongs to, in order, and make it concrete ("soft footsteps on tile"). For music, give the type, mood and how the volume changes. On the earlier studio, scripted lines came back word for word by speech recognition, and lyrics were sung. [claim: official LTX prompting guide] [claim: earlier studio tests]

Image to video: open by matching the first frame exactly, then describe motion, camera and sound, and end with "single continuous take, no hard cuts". Describe what happens next, not what is visible. [claim: official enhancer system prompt in ComfyUI-LTXVideo]

Multishot (new in 2.5): still one chronological paragraph. Name each edit ("A hard cut transitions to..."), then say again the scale, the angle, who is there and the light, reuse the same names, and say whether the sound carries on. Two to four shots per clip. Stay single-shot for lip-synced dialogue in one framing and for image to video. [claim: official LTX prompting guide]

Don't paste prompts written for other video models. Avoid abstract emotion words, text and logos (fix them later), complex physics, crowds, mixed lighting and long lists of numbers. [claim: official LTX prompting guide]

## Camera

Official camera words: follows, tracks, pans across, circles around, tilts upward, pushes in, pulls back, overhead view, handheld, over-the-shoulder, wide establishing shot, static frame. Pacing words: slow motion, time-lapse, lingering shot. [claim: official LTX prompting guide]

Name one move and rule out the rest, as the official templates do: "The camera performs a single, smooth push-in only; no other camera movement." Then say how the frame ends. If you don't name a move, write "the camera remains static". [claim: official ComfyUI templates] [code: psn/camera.py:1]

LTX leans toward pushing in. On the earlier studio, an orbit request became a push-in; the fix is the direction plus what comes into view: "circles around her from left to right, ending on her profile against the window". Community users report the same for orbits and for dollies in image to video. [claim: earlier studio tests] [claim: community reports on LTX-2.3]

In image to video, the first frame fixes the viewpoint. Angle words describe that frame and cannot change it; only a move changes the view over time, so write the angle as a move with an end state: "cranes down to ground level and tilts up until the tower fills the frame". For a strong angle, make it in the first picture. [inference] [claim: earlier studio tests]

No primary source lists dutch angle, whip pan, rack focus, point of view or drone. Treat them as untested. [claim: earlier studio research notes]

## When it goes wrong

Faces drift on a talking person: keep clips short and repeat a fixed character description of 50 to 80 words in every shot. Glass and physics warp: ask for simpler, believable motion. Image to video barely moves: write a longer, more specific motion description; more steps don't help a distilled model. Text in the frame: keep it short and fix it later. [claim: official LTX blog] [claim: official LTX prompting guide] [claim: earlier studio tests] [claim: community reports]

## Adapters worth knowing

LTX-2.5 has official IC-LoRA editing adapters, which change an existing clip. Earlier-studio measurements, one seed each: Colorization, Deblur and Restore were clearly better (Deblur took PSNR from 26.8 to 29.7); Clean-Plate removed people at a lower cost than the H3 alternative, with a similar look; Decompression removed blocking but re-synthesised texture; Refine-Details showed no gain on clean renders; and Ingredients and the pixel upscaler were worse as wired. Day-to-Night, Water and Alpha were still being judged. [claim: earlier studio tests, IC-LoRA batch]

Triggers sit in the edit prompt: COLORIZE for Colorization, ADD WATER for Water (above strength 1.5 it warps faces) and CINEMAGRAPH_MOTION for Cinemagraph. The studio's own VFX goal writes each IC-LoRA's prompt in its card's two-panel form. [claim: official adapter cards, huggingface.co/Lightricks] [code: studio/goals.py:63-65]

The Day-to-Night and Water authors use a dev-style setup (30 steps, guidance around 3 to 4 for Day-to-Night and 2.5 for Water, with spatio-temporal guidance), not the distilled CFG 1 setup. That probably explains why the earlier studio's distilled single-stage runs gave only a partial dusk and subtle water. [claim: adapter authors' READMEs, read in the earlier studio's capability notes] [inference]

A batch trap: one LTX image-to-video conditioning node writes into the cached empty latent in place, so a cached run can start from the previous picture. In a run with many images, vary the size or length each time, or clone the latent. [claim: ComfyUI-LTXVideo issue 569, github.com/Lightricks/ComfyUI-LTXVideo]

For LoRAs on LTX-2.5, load them model-only on every sampling stage. A standard LoRA works from 0.5 to 1.5 and an IC-LoRA from 0 to 1.0; test each one alone first. [claim: official ComfyUI-LTXVideo notes]

## Template (image to video, no enhancer)

[Shot type] frames [subject: age, hair, clothes, one distinguishing feature] in [setting, materials, one light source, colours], seen from a [front, side or low] viewpoint, matching the first frame exactly. Initially, [action, with emotion as physical cues], while [one concrete sound]. [One camera move, its speed and its end framing]; no other camera movement. A moment later, [second action]; she says in a [voice] voice: "[exact words]". [The sound of that action.] [End state.] Single continuous take with no cuts. [claim: earlier studio notes, built from the official guide] [inference]
