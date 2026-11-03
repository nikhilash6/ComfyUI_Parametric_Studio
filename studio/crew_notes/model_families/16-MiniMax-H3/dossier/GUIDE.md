# MiniMax H3: how to write a prompt (checked 2026-11-03)

This is the long version of the H3 prompting notes, rewritten in plain words. It replaces the "not in sources" gaps in PROMPTING.md: where the two disagree, this file wins. MiniMax publishes two official writing guides, one for text and keyframe modes and one for full-reference mode; read them for the full rules. This file credits them by link and does not copy them. [claim: MiniMax base writing guide, huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md] [claim: MiniMax reference writing guide, huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md]

Labels: "official" means MiniMax's guides, model card or ComfyUI's own docs. "Earlier studio" means tests run on the studio this one grew from; they were not re-run here. "Community" means a third-party guide that we read but did not test. [inference]

## Facts that shape a prompt

H3 makes 4 to 15 seconds of video at 24 frames per second with sound, in five modes: text only (T2VA), first frame (I2VA), first and last frame (FL2VA), last frame only (L2VA) and full reference (Ref2VA). The open weights run at 768p; higher resolutions are on MiniMax's hosted service. [claim: MiniMax model card, huggingface.co/MiniMaxAI/MiniMax-H3]

Write the prompt in English. Dialogue and on-screen text stay in their own language. [claim: MiniMax base writing guide]

The studio's "Video H3" goal passes your prompt to the model unchanged and offers 2 to 8 seconds. Reference goals snap the length to 17k+5 frames, so 5 seconds becomes 124 frames. [code: studio/goals.py:161] [code: studio/goals.py:186-189] [code: studio/goals.py:75-79]

| Frames | Seconds | Good for | Dialogue that fits (about 2.6 words a second) [claim: earlier studio tests] |
|---|---|---|---|
| 124 | 5.17 | one beat, an effect, a loop | about 12 words |
| 192 | 8.00 | one scene; a round number for first-and-last-frame | about 20 words |
| 243 | 10.13 | one scene with a question and an answer | about 26 words |
| 294 | 12.25 | a talking head, or a 2 to 3 shot story | 31 to 36 words |
| 362 | 15.08 | the ceiling, 3 shots | about 39 words |

The guidance scale must stay at 1.0: the model is distilled and has no negative branch. A negative prompt does nothing, and a "no X" line can add X. Describe what is there instead: "the sign above the door is blank". [claim: ComfyUI H3 prompt guide, docs.comfy.org/tutorials/video/minimax/minimax-h3-prompt-guide] [claim: MiniMax model card]

## The three fields

Every mode shares three fields: integrated_multimodal_description (picture, action, camera and dialogue), overall_soundscape (one to four sentences of ambience, action sounds, breath and laughter) and non_diegetic_music (one to three sentences about score only the audience hears, or N/A). Dialogue and music played inside the scene belong in the description, never in the sound fields. [claim: MiniMax base writing guide]

Describe what can be seen and heard, not moods. "Sparse piano at a slow tempo, low strings swell and fade" works; "sad music" doesn't. [claim: MiniMax base writing guide]

If a quiet shot comes back with speech or music you didn't want, fill both sound fields in, and use N/A only for real silence. [claim: ComfyUI H3 prompt guide]

## Mode by mode

Text only (T2VA). Open shot 1 with the style ("Live-action, cinematic", "2D-animated", "3D CG", "claymation"), then shot size and composition, the subject, the setting and key props, one camera move, the action and any line of dialogue. Don't put a time on shot 1. [claim: MiniMax base writing guide]

First frame (I2VA). The prompt starts with one fixed line saying that Picture 1 is fully referenced at 0.00 seconds, then a blank line, then the three fields. Describe what happens next, not the picture: the frame already carries the look. [claim: MiniMax base writing guide] [code: studio/recipes.py:336]

First and last frame (FL2VA). The first line says which second each picture lines up with, with the duration written to exactly two decimals (for example 8.00), then a blank line and the fields. Describe the path between the frames: the starting state, the changes in the middle, and the end state. Prefer one shot so the model moves continuously, and keep both frames in the same angle and light. [claim: MiniMax base writing guide] [claim: earlier studio notes, never rendered there]

Last frame only (L2VA). The same alignment line names the last picture at the final second; work out a believable earlier state and arrive at the picture. [claim: MiniMax base writing guide]

Full reference (Ref2VA). The official form has six sections: subject_definitions, summary, retention_analysis, detailed_description, overall_soundscape and non_diegetic_music. Labels stay the same throughout: Subject N for anything reusable (a person, an object, a place, a costume, a style), Picture N for an image used as a frame or storyboard anchor, Video N and Audio N for whole clips and sounds. The guide asks for 350 to 500 English words in detailed_description for a generation job. [claim: MiniMax reference writing guide]

Retention markers say how much of each reference to keep: fully_preserved, partially_preserved, attribute_transfer or weak_reference for pictures, and fully_copy, partially_copy, reference or weak_reference for audio. The summary opens with a task tag such as [reference generation] or [audio reuse], joined with a plus sign when there are several. [claim: MiniMax reference writing guide]

You don't have to write all six sections. A short plain prompt that starts with "Use Picture 1 to Picture 4 as the exact reference for the woman's face, hair and identity" worked on the earlier studio, and so did "Image 1 is Picture 1" as a binding line before plain "Image 1" wording. Keep the long form for jobs with many references. [claim: earlier studio tests]

## Dialogue and sound

Speech goes inside d tags with a language tag, and only the spoken words go inside: <d>[English] First batch of the morning.</d>. Who speaks, their voice and how they say it go outside, before the tag. Never translate or reword what is inside. [claim: MiniMax base writing guide]

Speaker IDs (S1, S2) number voices, not characters: the same voice keeps the same ID in every shot, and someone who never speaks has none. A bare (S1) with no voice description gives H3's default narrator, so always describe the voice: age, pitch, timbre, pace or accent. On the earlier studio, writing "she says" for a man pushed the voice up, from 118.7 Hz to 166.7 Hz. [claim: MiniMax base writing guide] [claim: earlier studio tests]

Off-screen narration: say "in an off-screen voiceover", and if the person is on screen, that their lips stay closed. When a line crosses a cut, mark both sides with scenetrans and say the audio carries on; when the video ends mid-word, use cutoff. [claim: MiniMax base writing guide]

On-screen text (a sign, a label, a subtitle) goes in English double quotes, word for word: a neon sign reading "OPEN". Keep it short; long strings come out garbled. [claim: MiniMax base writing guide] [claim: earlier studio tests]

Breath, sighs and mouth sounds go in overall_soundscape. Wrapping every spoken line in d tags made Whisper transcribe it word for word on the earlier studio, and untagged lines drifted. Speak early in the shot: a long action lead-in pushed lines two seconds late in one community test. [claim: earlier studio tests] [claim: community test, fuser.studio/articles/minimax-h3-prompt-guide]

## Camera

Write a camera move as one natural sentence with three parts: the move, how far (with small or large amplitude) and how fast (at slow or fast speed). Leave out amplitude and speed when they are ordinary. Moves: zoom in or out (the lens), push in or pull out (the camera travels), pan, truck, tilt, pedestal up or down, arc, tracking, static, slight or strong shake, point of view, and roll. Example: "The camera pushes in with small amplitude at slow speed toward the folded letter in her hands." [claim: MiniMax base writing guide]

Bracket commands such as [Push in] belong to the older Hailuo Director models. H3's official guide uses plain sentences. [claim: community guide, kapwing.com H3 guide] [claim: MiniMax base writing guide]

One move per shot. For a bigger move, name the start and end framing ("from a wide shot to a close-up, medium amplitude"); a bare "slow dolly-in" barely moved in one community test. Orbits and cranes make the model invent more geometry, so start with static, pan, tilt and truck. [claim: community test, fuser.studio/articles/minimax-h3-prompt-guide] [inference]

Keep subject motion and camera motion apart: "she walks forward; the camera tracks backward holding a medium shot". The word "tripod" was drawn as a tripod on the earlier studio; say "locked-off camera far back, nothing in the foreground" instead. [claim: earlier studio tests]

## Cuts

Shot 1 has no time. Every later shot starts "[Shot N] At MM:SS.mmm, the camera cuts to", with times that only go up, and each cut must show something new. If only the distance or angle changes, use a camera move instead. [claim: MiniMax base writing guide]

Chaining moves with "then" can turn one take into hard cuts. For one take, write "one continuous shot, no cuts". Repeat props and the setting in the same words in every shot to stop the set drifting. [claim: community test, fuser.studio/articles/minimax-h3-prompt-guide] [claim: earlier studio tests]

## People, clothes and props

Styling in the prompt beats the reference pictures. If the look in your references must survive, don't describe hair, make-up or clothes; write "dressed and styled exactly as in the reference images". The one exception is a product you are selling: then describe it, and give it its own close reference picture. [claim: earlier studio tests]

The hand budget: if the person holds a phone or a prop, every gesture uses the one free hand. Say "exactly two arms and two hands"; the first render without it grew a third hand. [claim: earlier studio tests]

A blank garment gets invented brand text: write "a plain grey hoodie with no print or logo". Thin white tops read as see-through in golden backlight; use opaque clothes. [claim: earlier studio tests]

Faces need medium or close framing; wide shots lose detail. For two people, say there are exactly two different people, fix each to one side of the frame, and give each a contrast that matches their references (taller and on the left, smaller and on the right). [claim: community guide, kapwing.com H3 guide] [claim: earlier studio tests]

## Ten rules that held on the earlier studio

1. One main action and one camera decision per shot. 2. Name the setting again in every shot, or the references win over the action. 3. Let references carry identity. 4. Voice outside the d tags, words inside. 5. Keep to the hand budget. 6. For an effect, describe the physical sequence: start, movement, contact, end, camera. 7. Keep sound in its own lane and never repeat dialogue there. 8. Cuts get times; one take says so. 9. Camera as move plus amplitude plus speed. 10. Pace dialogue at about 2.6 words a second and speak early. [claim: earlier studio tests]

## LoRA trigger words

A trained H3 trigger is a caption prefix: trainers put it at the start of every training caption. So it belongs at the very start of integrated_multimodal_description, before the scene; in the six-section form, on the first line of detailed_description. Never put it in the sound fields or inside d tags. [claim: fal H3 LoRA training guide, fal.ai/learn/devs/how-to-train-a-lora-for-minimax-h3] [claim: community guide, civitai.com/articles/35774]

The studio's own LoRA recipes already put a LoRA's required trigger words at the start of the shot text, and skip any the text already contains. [code: studio/recipes.py:65-66]

Not every LoRA works the same way. A camera event LoRA (bullet time, crash zoom, dolly zoom) wants its word as the label of the beat it triggers, mid-description; a slider has no trigger at all, only a strength; and an edit or upscale LoRA wants its fixed sentence as the whole prompt. Write the trigger exactly as trained, once, and never contradict it ("static camera" with a camera-move LoRA, a competing style word with a style LoRA). [claim: earlier studio research notes, from each LoRA's own card]

Short, flowing prompts suit LoRAs best, because they were trained on one-paragraph captions. No test has compared the same LoRA with a short and a very long prompt, so no strength rule exists for long prompts. [claim: fal H3 trainer page, fal.ai/models/minimax/h3/t2v/trainer] [inference]

## How long a prompt should be

MiniMax's reference guide asks for 350 to 500 English words in detailed_description, and gives no token cap beyond that. The earlier studio's old long mode asked for 950 to 1,100 words, which no official source supports. [claim: MiniMax reference writing guide] [claim: earlier studio research, 2026-10-17]

Length was not the problem; filler was. A rule-based count of the earlier studio's writer output found 47% of 8,295 words were filler: breathing and blinking, hair and cloth drift, ambient hums, repeated light. The 50 most-liked safe-for-work community prompts had a median of 11% filler at 131 words. Cutting a prompt from 1,006 to 332 words lowered the filler share by only 5 points and removed purposeful words with it. The classifier was hand-checked on three samples by the person who wrote its rules, at about 8% wrong labels. [docs: studio/processes/video-h3-modes.md:115-130]

The fix the earlier studio wrote: 3 to 5 beats inside one take, each saying who does what to what, where the camera is and why, and what changed by its end, inside a budget of 30 + 14 s to 50 + 24 s words (100 to 170 words for 5 s). It was never rendered, so it is a plan with a measured reason, not a proven setting. [docs: studio/processes/video-h3-modes.md:134-138] [claim: earlier studio research, 2026-10-18]

What people post: in a count of public H3 prompts, base H3 prompts had a median of 173 words (90th percentile 579). 84% described sound, 64% set non_diegetic_music (46% to N/A), and 92% of posts ran at CFG 1, where the negative prompt does nothing. Dialogue appeared in 42 to 48% of prompts, mostly as a bare quote or "she says"; only a minority used the d tag or a speaker tag. Popularity is not quality. [claim: earlier studio community prompt count, 2026-10-17]

## First-and-last-frame LoRAs

An audit of about 14 LoRA recipes built on the FL2VA base found only about 3 that really need both a first and a last still, such as a loop or an orbit. The rest run better as first-frame-only (I2VA). Forcing a last frame on them pins the clip towards a still picture. [claim: earlier studio recipe audit, 2026-10-17]

## When it goes wrong

Slideshow pacing or timid motion: give a timed shot list and name the start and end framing. A reference is ignored: give every file one job ("Image 2 defines the green jacket"). Garbled text: quote it and keep it short. A plastic look: name real imperfections rather than saying "realistic". Unwanted cuts: drop the "then" chains. Music when you wanted ambience: describe the sounds and set the music to N/A. [claim: community guides, rundiffusion.com and pixo.video H3 guides] [claim: earlier studio tests]

## Where to start

The recipe library has ten H3 scenes written to these rules, each one a single text-only shot with blanks to fill in: a product hero, a door to another world, an interior walkthrough, a cooking montage, a coastal aerial, an anime rooftop, a storybook fox, a street interview, a narrated explainer and a seed-to-sapling time-lapse. None has been rendered here yet. [code: studio/recipe_library/h3_scenes.json]
