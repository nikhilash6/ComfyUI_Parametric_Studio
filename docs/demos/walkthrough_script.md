# Walkthrough, narrated: the script

The narration for the two walkthrough videos, word for word. `scripts/build_walkthrough.py` reads this file. Each `##` section is one stretch of the video. Its `Picture:` line lists what is on screen, in order: `tab:` is a screen capture of that studio tab, `clip:` is a render from `studio/web`, `phone` is the 390 px phone pass, `card:` is a text card. The paragraphs below it are spoken by Kokoro 82M's built-in male voice `am_michael` (Apache-2.0), on the CPU. The captions burned into the video are these same sentences.

Every figure here comes from a record in the repo: `docs/demos/numbers.json` for the counts, the page or proof file for each feature. The voice is a built-in preset, not a clone of anyone.

# Full walkthrough

## Parametric Studio
Picture: clip:showcase/v_h3_dragon.mp4, tab:create, tab:create@12

This is Parametric Studio: a creative studio built on ComfyUI that runs on your own GPU, with open-weight models, at zero credits. The code is open, under AGPL three, and each model keeps its own licence. Let's walk through all of it.

The Create page is where most people start. Pick what you want to make, describe it, and press Generate. Each app shows what it needs to download, its model's licence, and the memory it took on our card. The wall behind is our own renders in 3D. Drag it, and click any shot to see how it was made.

## Shot Board: one clip in, a whole shoot out
Picture: tab:shots, clip:docs/media/shotboard_demo.mp4@90.5, clip:showcase/vfx_same_water.mp4, clip:showcase/vfx_same_night.mp4, clip:showcase/vfx_same_cutout.mp4

The headline feature is the Shot Board. One clip in, a whole shoot out. Drop in a clip and queue the shoot: a new camera move, a frozen-time orbit, a recast lead from a single picture, then four LTX-2.5 effects: water, a clean plate, day to night, and a matte. Jobs run one at a time on your GPU, and every result keeps its exact graph and seed. Export the board as one captioned contact video. Seven jobs on one clip took about thirteen minutes on our card.

## The LTX VFX track
Picture: clip:showcase/vfx_same_transition.mp4, tab:finish, clip:campath/track_boat.mp4, tab:campath

We entered the VFX Workflow Built with LTX track, and LTX-2.5 is the core video model in every graph in that block. Each effect adds one Lightricks IC-LoRA. A transition graph bridges the last frame of one clip into the first frame of the next. LTX Finish restores, deblurs, removes compression, colorizes, upscales, and turns SDR into HDR, with HLG, EXR and ProRes masters, each measured against the clean original. Camera Paths lets you draw a line for something to follow, and it checks a take against the move you asked for: a match, a mismatch, or not enough to tell. It can also pick the best of several takes by the move.

## Swap on any model
Picture: tab:swap, clip:showcase/recipes/recast_character.mp4, clip:motion/scail2_0.mp4

Swap on any model. The Swap page lists every graph in the repo that swaps a character, a performer or an outfit, each with a render made on our card, its time, its peak memory and its licence. Recast on MiniMax H3 keeps the performance, the camera and the sound, and changes the person. There are swaps on Wan, Qwen-Image and FLUX.2 Klein too. Swap only invented adults, or people who gave you permission.

## The real graph, in 3D
Picture: tab:pro, tab:api, tab:apps

Every result is one click from the exact ComfyUI graph that made it. Open Pro and the graph appears in 3D, with data flowing along its wires. Click a node for a plain-language explanation of what it does. The same graph runs when you press Generate, and you can copy it straight into ComfyUI. The API page makes every graph callable from code, and Apps puts every graph one click from a simple form.

## Every model, its real state
Picture: tab:families, tab:atlas, tab:models, tab:fit

Families shows every model family on this machine. Each one has its own isolated ComfyUI, started on demand behind a memory check and stopped when idle. Most of them have rendered here, and the page says what the rest still need. Atlas tells the history of generative AI, model by model, with each one's licence and whether it runs here. Models shows what is ready and what to fetch, and Hardware Fit checks every goal against your card: measured where we measured it, and labelled an estimate where we did not.

## Recipes, pipelines and commercials
Picture: tab:recipes, clip:showcase/recipes/anime_opening.mp4, tab:pipelines, clip:pipelines/room_century/final.mp4, tab:commercials, clip:commercials/perfume_nocturne/commercial.mp4@12

Recipes chain models into one click: a music video from a song, a short film from one sentence, a product ad. The library holds eight hundred and eighteen recipes, and more than seven hundred of them show a result we rendered here. Pipelines go further, with many models on one card: words to an actor on a built set, or one room through a hundred years. Every stage shows its model, seed, time and peak memory, and what failed. Commercials writes, shoots and cuts a captioned TV spot in twenty-four genres, with invented brands only. Every word on screen is set by ffmpeg, never painted by a model.

## Sound and voice
Picture: tab:clipsound, tab:dub, tab:voices, tab:music, clip:music/reactive.mp4

Captions and Sound writes down what is said with Whisper and sets it in a real font, and ControlFoley makes sound for a silent clip, for non-commercial use. Dub and Voice keeps the face and changes the language. Voices reads one line with every speech model on the machine, and MiniMax H3 speaks the line you write into its prompt. Every talking recipe now carries real written words, and a test holds it to that. Music renders one song brief on every music model here, from MiniMax Music 3 to ACE-Step, each measured, and checked with Whisper.

## Motion, 3D and training
Picture: tab:motion, clip:motion/wan_animate2_1.mp4, tab:worldkit, tab:virtualset, tab:viewer, tab:train, tab:gamebuilder

Motion makes a body move from words, follows a performance, animates a portrait and lip-syncs a clip, and it shows only what ran here. World Kit builds real-scale 3D places, props and rigged characters. Virtual Set steers a video model with what Blender renders, and the 3D viewer lets you orbit any result. Train turns your pictures into a LoRA, and LoRA Showcase packages the proof. Game Builder goes from a few prompts to a game that a bot has played to the end.

## Learn by doing
Picture: tab:university, tab:sampling, tab:words, tab:anatomy, tab:moe

Then there is the teaching. ComfyUniversity has a hundred and sixty-three lessons, from your first wire to reading the sampler's source. Each has a graph you can open, a lab that runs in the browser with no GPU, and a quiz. Sampling Lab explains samplers and schedulers with real renders. Which Word shows where each prompt word looked while the picture was drawn. Model Anatomy opens a model file and shows what it is made of, without loading a single weight. And Experts replays real routing from a thirty-billion-parameter mixture of experts: for every word piece, each of its forty-eight layers picks eight of a hundred and twenty-eight experts.

## Tools that keep you honest
Picture: tab:packlab, tab:doctor, tab:prove, tab:project

Pack Lab is where you try a node pack away from your work, with its risks in plain sight, and reviewed never means safe. Tonight our ComfyUI took on Pool 51, over two hundred reviewed node packs in fifty-one sections, and now loads more than six thousand six hundred node classes. Installed is not the same as proven. Graph Doctor checks a broken workflow against the nodes you really have. Prove It reruns our exact graph and seed on your machine, and lists what differs. Project File packs a whole shoot into one file: never weights, never your folders.

## And the rest of the studio
Picture: tab:library, tab:design, tab:edit, tab:auto, tab:site, tab:crew, tab:director

There is more. Library keeps everything you have made. Designers makes whole concept sheets from a few choices. Edit does AI edits, then a timeline. Auto schedules creations for when the machine is idle. The Site builder turns facts into a clean website. And the Crew, led by Comfy Prime, answers from cited notes, out loud, in a local voice. Live Director builds a Shot Board as you talk, and nothing renders until you press the button yourself.

## Held to its claims
Picture: card:checks, tab:prove@3

All of this is held to its claims. Every release goes through a privacy scan of every file, for private paths, secrets and private strings, a licence check, and the full test suite, more than seven thousand tests, on the exact tree that ships. Every number in this video comes from the repo's own records.

## In your pocket
Picture: phone

And it fits in your pocket. Add the studio to your phone's home screen over Tailscale, with private HTTPS and a QR code. The layout folds down to one column, and your GPU at home still does the work.

## What comes next
Picture: tab:future, clip:pipelines/room_century/final.mp4, tab:future@10, clip:pipelines/anime_short/final.mp4, clip:showcase/v_ltx_ink.mp4, card:end

Where next? First, what we learned. Owning a model is not using it: of the more than eleven hundred model files on our map, fewer than four hundred have rendered. Installed is not proven, either. So here is what we want to build, as plans, not promises. Swap a stage: when a new model lands, drop it into a working pipeline, rerun that stage and everything after it, and compare the two side by side. Proof that travels: the graph, seed, models and licences carried inside each file. Smaller cards: which pipelines fit which memory, from measured peaks. A class for each chain, so every pipeline becomes a lesson. And a way in for every model we hold but cannot reach yet. We think graphs will outlast apps, models will become parts that pass the same depth map and character sheet down a chain, and one local GPU will become a small studio. Parametric Studio. Real graphs, your GPU, open weights, zero credits.

# Short cut

The cut for the contest form, under two minutes. It names the contest's three inspiration prompts, says how the studio is built, and says what is new.

## Cinematic Studio
Picture: tab:shots, clip:showcase/director_wide.mp4, clip:docs/media/shotboard_demo.mp4@90.5

This is Parametric Studio, on your own GPU. What's new: one clip becomes a whole shoot in a single queue, and every result keeps the exact ComfyUI graph and seed that made it. For Cinematic Studio, direct a shot like a film set, or queue a whole shoot on the Shot Board. Seven jobs on one clip took about thirteen minutes.

## Re-shoot a video
Picture: clip:showcase/reshoot_orbit_take.mp4

Re-shoot a video: Reshoot makes a new take of your clip with a new camera move, on MiniMax H3.

## Openjutsu: swap a character in a video
Picture: clip:showcase/recipes/recast_character.mp4, tab:swap

Openjutsu, swap a character in a video: Recast keeps the performance, camera and sound, and changes the person. The Swap page lists every swap graph in the repo, with its render and licence.

## VFX built with LTX
Picture: clip:showcase/vfx_same_water.mp4, clip:showcase/vfx_same_night.mp4, tab:finish

In the VFX workflow, LTX-2.5 is the core video model. Each effect adds one Lightricks IC-LoRA: water, a clean plate, day to night, a matte, transitions, and LTX Finish for HDR masters.

## How it's built
Picture: tab:pro, card:built, tab:packlab

How it's built: the apps run real ComfyUI graphs on your local ComfyUI server, and the graph you open in 3D is the graph that runs. The studio is FastAPI and Preact, with no build step. We audited every one of our custom nodes, and the Pool 51 node packs are pinned to checked commits. Open weights, run locally, at zero credits.

## In your pocket, and next
Picture: phone, card:end

It works on your phone too, with your GPU doing the work. Next: swap one stage when a new model lands, and carry the proof inside every file. Parametric Studio.
