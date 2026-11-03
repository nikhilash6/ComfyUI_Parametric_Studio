# The whole studio: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## Shot Board

Shot Board VFX takes: the board offers four LTX-2.5 IC-LoRA effects (water, clean plate, day to night, matte) beside the MiniMax H3 jobs (reshoot, orbit 360, recast) and a transition job. Each LTX job names its licence on the card: free under US$10M yearly revenue. [code: studio/web/shotboard.js:8-17]

Shot Board example source: the first same-clip source smeared the woman's face as she walked toward the camera. 16 LTX-2.5 candidates were rendered (8 at 960x544, 4 at 1280x704, 4 at 1920x1088) and every frame's face was checked at full size. Every 960x544 take smeared or ghosted the face somewhere. The kept source is a 1920x1088 render (53.7 s, 38.8 GiB lane peak) scaled down to 960x544: a woman in a red coat stays whole in frame, walks a few steps, stops and looks around, and her face holds steady. [run: studio/web/showcase/vfx_same_clip.json:9-11]

Shot Board example takes: all five takes were re-rendered from the new source with the same per-effect seeds and settings. At standard quality, water took 33.2 s, day to night 38.5 s, clean plate 28.7 s and the matte 31.9 s, each at a 38.5 GiB lane peak on a 96 GB card, models loaded fresh each time. [run: studio/web/showcase/vfx_same_clip.json]

Shot Board transition job: LTX-2.5 bridges the end of one clip into the start of a second clip, joined into one take, using an LTX-2.3 style-transition LoRA with the trigger word zhuanchang. The proof joins the day source, a 49-frame bridge and its night take into 291 frames at 960x544: 16.5 s, 37.8 GiB. Both seams are continuous and the lamps come on. Extra day-to-night words made a moon rise in the bridge and vanish in the night clip, so the default prompt ships. Not tested: a run without the LoRA, so what the LoRA adds over plain first and last frame guidance is not measured. [code: studio/goals.py:73, studio/goals.py:113] [run: studio/web/showcase/transition_proof.json]

Shot Board matte take: one click turns a matte into a cutout of the source clip with real alpha, written as ProRes 4444 (yuva444p10le) by ffmpeg alphamerge, plus a preview over a checkerboard. The example cutout file is not shipped because ProRes 4444 is large. [code: studio/shot_board.py:70, studio/shot_board.py:98] [run: studio/web/showcase/vfx_same_clip.json:115]

Shot Board before/after reels: a take becomes a postable reel in three shapes (a 16:9 wipe, a 1:1 crop and a 9:16 stack), each ending on a card and carrying an AI-generated label. The side-by-side clips and the four README wipe GIFs were remade from the new takes. [code: studio/shot_board.py:107, studio/shot_board.py:152] [docs: docs/media/shotboard_gifs.json]

Shot Board time estimates: the board sums measured render seconds from the showcase and same-clip batches, and a job with no measurement is counted as unknown, never guessed. The table still holds 79 s for a transition, older than the 16.5 s re-render. [code: studio/web/shotboard_film.js:46-56] [run: studio/web/showcase/transition_proof.json:10]

## Camera Paths (P5)

Camera Paths canyon path: a drawn rising orbit to the right, rendered by Wan 2.2 Fun Camera 14B (fp8) from a FLUX.2 Klein 4B still. The checker said MATCH: the picture slid right 35% of the width, grew 45%, and the centre stayed put while the edges moved. 252.8 s, 44.9 GiB peak. Looked at: smooth, no warping. [run: studio/camera_proof.json]

Camera Paths cathedral path: a drawn level orbit to the left around a stone font. The checker said INCONCLUSIVE, never a pass: the picture slid left 28% but the centre moved with it, which reads like a pan. By eye Wan orbited a point behind the font. 216.9 s, 44.9 GiB. [run: studio/camera_proof.json:464] [run: studio/camera_proof.json:3-8]

Camera Paths paper boat line: LTX-2.5 with the LTX-2.3 Motion-Track-Control IC-LoRA moved a red paper boat along a drawn line in 31.8 s at 39.2 GiB. Followed by colour, the boat stayed a mean 24.9 px (max 40.1 px) from the line over 121 frames, and was never lost. The render needs both sides in multiples of 64 (960x576). [run: studio/camera_proof.json:300] [code: studio/feature_camera.py:19]

Camera Paths object follower: the first follower, Lucas-Kanade on points around the start, stayed on the pebbles while the boat moved away and reported 274 px. Template matching replaced it; the render was not repeated. [run: studio/camera_proof.json:6] [code: studio/feature_camera.py:171]

Camera Paths rooftop checks: three MiniMax H3 Director clips (dolly in, pan left, tilt up, 53 to 62 s each at 39.4 GiB) all came out MATCH, 3 of 3. [run: studio/camera_proof.json]

Camera Paths take picker: three H3 lighthouse takes asked to dolly in all matched, and the picker chose take 2 (grew 53%, centre still), which matched the eye. The checker overstates take 3's growth at 44% because breaking waves add to the measured growth. [run: studio/camera_proof.json:509] [run: studio/camera_proof.json:3-8]

Camera Paths checker caution: on the older showcase test clips three of four came out INCONCLUSIVE, including the poppy clip that is a plain mismatch by eye. The thresholds were written before measuring. [run: studio/camera_proof.json:3-8] [code: studio/camera_verify.py]

## LTX Finish (P1) and one-click edits

LTX Finish: six fixes on LTX-2.5 IC-LoRAs, each measured on a fresh clip damaged on purpose. Restore lifted VMAF from 0.5 to 38.6 but invents what the fade destroyed (khaki shirts came back patterned). Deblur went from VMAF 8 to 66 with PSNR up 2.1 dB. Remove compression raised SSIM and VMAF (12.7 to 50.5) but lost 1.7 dB PSNR by adding sharpening. Colorize brought colour back from grey but brighter and greener than the original. SDR to HDR wrote HLG 10-bit, ProRes 4444 HLG and half-float EXR masters, all checked. [run: studio/finish_proof.json]

LTX Finish x2 upscale: exactly twice the guide (960x512 from 480x256) in 14.4 s at 39.8 GiB, with crisp threads, but the weave is redrawn. Against the original, a plain Lanczos x2 scored VMAF 96.4 and the LTX x2 scored 14.7. Use it on drafts, not on footage that must stay faithful. [run: studio/finish_proof.json:569-623]

One-click coverage set: Qwen-Image-Edit-2511 with the Lightning 4-step and Multiple-Angles LoRAs makes four camera angles from one still. Example: 42.4 s, 29.2 GiB; the three-quarter turn is gentle, the wide and the close-up moved most. [run: studio/web/oneclick_art/index.json] [code: studio/feature_oneclick.py:87]

One-click relight: Qwen-Image-Edit-2509 with Lightning and a relight LoRA. Example golden hour on an invented man: 28.3 s, 29.1 GiB. The light, shadows and wall changed as asked, and the face changed a little too, so check a likeness. [run: studio/web/oneclick_art/index.json] [code: studio/feature_oneclick.py:90]

One-click photo effects: inflate (a LoRA) or prompt-only marble and gold statues on Qwen-Image-Edit-2511, optionally followed by an LTX-2.5 clip from the photo to the edit. The first clip graph kept Qwen loaded beside LTX (66.0 GiB) and cross-faded. The fix starts the clip in place on the photo with a guide only on the last frame, and unloads Qwen before LTX loads: 69.4 s at 38.9 GiB. The face drifts a little toward the edited still by the end; nobody has listened to its sound. [run: studio/web/oneclick_art/index.json] [code: studio/feature_oneclick.py:83-84, studio/feature_oneclick.py:93]

One-click alpha matte: the VFX goal's Alpha-Gen pass composites a clip onto a new Z-Image Turbo set and writes ProRes 4444 and VP9 WebM with alpha. Example: 88.8 s, 51.9 GiB. The matte is soft: a little background shows between the legs and the subject casts no shadow on the new set. [run: studio/web/oneclick_art/index.json] [code: studio/feature_oneclick.py:97]

## Dub, sound and captions

Dub & Voice (P6): Whisper writes down the words, they are translated, and either DubIt (an LTX-2.3 IC-LoRA run on LTX-2.5) redraws the mouth and speaks the line, or a Qwen3-TTS voice is followed by LatentSync. A voice clone needs a consent choice (own, permission or synthetic), written to a file beside the result. [code: studio/feature_dub.py:1-5, studio/feature_dub.py:22, studio/feature_dub.py:267-272]

Dub & Voice proof numbers, measured by programs, not heard: the voiceover master landed at -14.1 LUFS, -1.5 dBTP, with the music ducked 15.3 dB (12 dB asked). DubIt said the Spanish line at WER 0 (53.2 s, 43.1 GiB) but its voice likeness to the speaker was only 0.63 against 0.87 for the Qwen3-TTS clone, and its sound came out unmastered at -11.5 LUFS. The clone route carried "es claro" from the source's half sentence into the new line (WER 0.2). [run: studio/dub_proof.json:26-92, studio/dub_proof.json:119-170]

Captions & Sound captions: Whisper writes the words and ffmpeg sets them in a real font, read back off the frames by OCR. On a voice-over with a script it matched 94.7% of the words (it wrote ffmpeg as "FFM peg"); on H3's own speech it wrote what it heard where H3 was unclear. Whisper ran on the CPU, so no VRAM was used. [run: studio/clipsound_proof.json:4-50]

Captions & Sound add sound: ControlFoley gives a silent clip generated ambience. It is labelled non-commercial (CC BY-NC 4.0 weights, a research-only Apple image encoder) and the person must tick a non-commercial box. Sync was measured as no better than chance (r 0.02 and 0.04 against 2000 shifted copies), so the page says it is ambience, not event sound. Output is levelled to -16 LUFS under a -1.5 dBTP ceiling, after one take came out at +0.5 dBTP. [code: studio/foley.py:25-27, studio/foley.py:77, studio/foley.py:95] [run: studio/clipsound_proof.json:106, studio/clipsound_proof.json:176]

## Commercials

Commercials library: 24 genre templates, each with beats, shots, camera moves, sound, voice-over, on-screen text, which beats a 15, 30 or 60 s cut keeps, the end card and the legal text. A brief fills a genre into a full script and shot list. [docs: studio/commercial_genres.json] [code: studio/commercials.py:12, studio/commercials.py:136]

Commercials hard rules, enforced in code on the brief, the script and any language-model rewrite: invented brands, products and people only, with a list and a near-miss check against real names; no celebrities, politicians or parties; adults only, fully clothed and family-friendly, no alcohol or tobacco; pharma parodies claim nothing. Every word on screen is drawn by ffmpeg, never by an image model, and every spot carries an AI-generated label. [code: studio/commercial_safety.py:1-3, studio/feature_commercials.py:12-13, studio/commercials.py:3]

Commercials political parody: a parody genre gets a PARODY card and a PARODY badge (for the political one, "PARODY · FICTIONAL CANDIDATE") beside the AI-generated label for the whole spot. The 15 s proof shows an invented candidate, party and town, satirises only the format, and is recorded as flawed on its second take (Whisper heard 82.1%). [code: studio/commercials.py:39-41] [run: studio/commercial_proof.json:705]

Commercials proofs: 15 genres have a recorded spot in the proof file. Two passed (fashion and bank, 15 s each), twelve are complete but flawed with their flaws labelled (pharma, big-game and perfume at 30 s; mattress, pet food, airline, political parody, cleaner, energy drink, real estate, game trailer and travel at 15 s), and one failed: the car spot showed a real maker's badge and is not published. A person looked at first, middle and last frames; nobody listened. [run: studio/commercial_proof.json:3]

## Pages that explain models

Experts page: real top-8 routing from a 30-billion-parameter mixture of experts (48 layers, 128 experts), recorded once on one GPU; the page only reads the record. [code: studio/feature_moe.py:11] [run: studio/moe/index.json]

Model Anatomy page: what each model file is made of, read from its safetensors or GGUF header with no GPU and no weights loaded: parameters, blocks, number formats, attention and MLP split, LoRA rank. Pickles are listed, not opened. [code: studio/feature_anatomy.py:10] [run: studio/anatomy/index.json]

Which word painted what: two studio nodes record SD 1.5 and SDXL cross-attention and turn it into one heatmap per prompt word; DiT models are refused. On the recorded renders the expected word-region checks passed 9 of 14 by plain lift and 11 of 14 above each map's floor. [code: studio/feature_words.py:1-2] [run: studio/sampling_lab/attention.json]

## Building blocks

Game Builder: prompts pick a hand-written genre kit and fill a checked spec, Godot checks it and a bot plays it to the end. Godot's own file logging is off in every kit after one error loop filled a 308 GB log, and the runner stops a run whose log passes 20 MB. Arena waves were eased, and light now follows the time of day with AgX tonemapping after one game came out washed out. [code: studio/feature_gamebuilder.py:15, studio/gamebuilder/template/project.godot:19-21, studio/gamebuilder/assemble.py:181, studio/gamebuilder/levels.py:161, studio/gamebuilder/template/core/world.gd:34] [claim: commits c4164a20 and e79c6846, 2026-11-02]

Pipelines: 24 multi-step pipelines ship, each a JSON file of steps. [code: studio/pipelines]

Prompt kits and look library: seven per-model writer kits (FLUX.3 Klein, FLUX.2 Klein, Qwen-Image 2.1, Z-Image, Wan 2.2, LTX-2.5, MiniMax H3) feed the Create page's Improve button; if the language model is off or its answer fails the checks, a fixed formula writes the prompt and the reply says so. The look library holds 461 looks in 21 groups and six sections, one pick per group. [code: studio/feature_prompt_kits.py:1-4] [docs: studio/prompt_kits.json, studio/look_library.json]

## Families, map and audits

Model families: the family record lists 95 families. 80 are at "rendered here", 2 have a template that checks out, and 13 have a server that starts with no render yet. [run: studio/family_status.json]

Model map totals: 373 of 1129 model files have a recorded render, with 184 more reachable by a graph and 416 unreachable; 95 of 156 voice files are rendered. The commit that set these counts records 250 of the renders as viewed by a person. [run: studio/web/future_numbers.json] [claim: commit 12f49f22, 2026-11-02]

Licence audit: one table of licences for every family, read on 2026-11-02 from each model's own page and, where use is limited, the licence text. Goal tiles, family cards and the Create form show the short limit words (non-commercial, research only, revenue cap, territory limits). A test keeps the labels honest and another checks every graph against the paid partner nodes. [code: studio/licences.py:1-12] [test: tests/test_licences.py, tests/test_open_edition_no_paid_apis.py]

Dockerfile and Windows installer: the Dockerfile installs ComfyUI and the studio with install.py, runs as an unprivileged user, and keeps both servers on the local address only. The Windows installer dry-runs first and says UNTESTED ON WINDOWS; it was only checked on Linux. The commit records that the image itself was not built (about 10 GB of downloads). [code: Dockerfile:3-6, Dockerfile:22, scripts/install_windows.ps1:3] [test: tests/test_dockerfile.py] [claim: commit 724b9bc8, 2026-11-02]

Graph audit: a static check of every graph the studio ships against a ComfyUI node list, the way ComfyUI validates inputs: unknown nodes, empty required inputs, broken or mistyped links, choices, ranges and model files on disk. Nothing is queued. A graph that needs a pack or weights says so under "needs". CI runs it on a saved snapshot. [code: studio/graph_audit.py:1-3] [test: tests/test_graph_audit.py]

Graph audit, not shipped: Capybara is not shipped because the Tencent Hunyuan Community License limits territories and user counts. The SD 2.1 unCLIP lesson graph is not shipped because the only copy found is a community mirror's pickle checkpoint. [code: studio/edits.py:27, studio/university/graphs/c_unclip.json:7]

Pack Lab picks: 131 reviewed picks, read from each pack's text without running pack code: 73 install candidates, 43 borrow-the-idea and 15 docs-only. Their sandbox column reads 73 ok, 44 untested, 10 with no nodes seen and 4 failed. 62 flagged packs are kept only as salted hashes and refused; that list is not exhaustive, so "not refused" does not mean cleared. [run: studio/pack_lab_picks.json] [code: studio/feature_packlab.py:1-3]

## Gate and render lessons

Honest peaks: declare each job's real peak. The VOID object remover measured 54.6 GiB against 38 declared, and the declaration was raised to about 58. Wan Fun Camera peaked 0.9 GiB over its declared 44 and now declares 48 for the proof and 46 on the page. One-click tools declare the measured peak plus a tenth. [claim: studio test run 2026-11-02] [run: studio/camera_proof.json:3-4] [code: studio/feature_oneclick.py:83-84]

Half-precision VAE and LTX audio: when ComfyUI forces the VAE to half precision, LTX's audio encoder stops with a bf16/float mismatch, so DubIt cannot encode the speaker's voice. A ComfyUI started with an fp32 VAE runs it, and the Dub page refuses DubIt with a plain message instead of failing mid-render. [code: studio/feature_dub.py:52-64] [run: studio/dub_proof.json:169] [test: tests/test_feature_dub.py]

H3 garbled voices, corrected: the half-precision VAE was first suspected of garbling H3's speech. The repo records the real cause: talking templates gave H3 no words, so it voiced fluent babble (80 to 371% WER), while clips that used exact words inside the d tag measured 0 to 6% on the same half-precision lanes. Templates now send each line word for word. A greeting re-rendered with the same seed and only the prompt changed went from 133% to 0% WER, measured by Whisper, not listened to. [code: studio/recipe_library/video_templates.json:61] [run: studio/recipe_renders.json:14761-14781] [claim: commits b60c9e34 and ca01c901, 2026-11-02]

One reservation per job: each job takes its own GPU reservation at its own peak, so a small job can backfill and nothing holds more than it uses. A short sequence may run under one reservation at the largest of its peaks to avoid re-queuing. A long batch held under one 48 GiB reservation for about 89 minutes kept 19 other jobs waiting. [code: scripts/prove_camera.py:30-31] [claim: studio test run 2026-11-02]

Idle servers caching models: a ComfyUI that has finished keeps its models cached and blocks other jobs. At one point 23 jobs waited with the GPU at 2% use while about 37 GB sat in idle servers' caches; freeing idle servers got the queue moving. Inside one graph the same rule holds: unloading Qwen before LTX loads cut the one-click clip peak from 66.0 to 38.9 GiB. [claim: studio test run 2026-11-03] [code: studio/feature_oneclick.py:83-84]

Text encoder load sets the low-memory peak: under an emulated 14 GiB budget the Shot Board matte job peaked at 19.6 GiB while the Gemma text encoder loaded, and at 10.4 GiB when the prompt encoding came from cache. Every new prompt needs the encoder, so 16 GB cards are not claimed. [run: studio/web/showcase/vfx_same_clip.json:188-215]

## Docs

Openings doc: nine graded ways to open a short clip in its first three seconds, from the earlier studio's research. None was rendered or measured here, and nothing in it predicts reach. [docs: docs/OPENINGS.md]

Checking outputs doc: a suggested order for scoring a batch of generated images (VQAScore, OCR, face embeddings, a preference scorer, then a person), and why a public AI-detector score proves nothing either way. None of these tools is installed or wired in. [docs: docs/CHECKING_OUTPUTS.md]

## Pool 51 node packs, installed 2026-11-03

Pool 51 node packs: 223 packs were linked into the studio's main ComfyUI on 2026-11-03. 160 came from a read-only triage of the 51 sections of the node-pack pool, 62 from the earlier studio's own pack list, and one was approved on its own (DepthPro, whose weights carry a research-only licence). The node list grew from 3,416 to 6,635 classes, with 0 import failures, and the server was ready about 27 s after a restart. [claim: studio install record 2026-11-03]

Pool 51 staging: before any pack reached the main ComfyUI, all 223 loaded on a separate test ComfyUI beside every pack already installed, in 15 groups of up to 20, each group on a fresh restart. Result: 0 import failures, 0 tracebacks and 0 node-name collisions; ready time 28.6 s before and 28.1 s after; idle memory 1.92 GiB before and 2.45 GiB after; idle graphics memory unchanged at 0.54 GiB. [claim: studio install record 2026-11-03]

Pool 51 exclusions: ten packs that passed triage were dropped after staging. Three loaded a second, older cuDNN library into the process because they import diffusers pipelines when ComfyUI starts, the known cause of broken samplers here. One took 15.5 s to import and doubled the start time. One registered its loader in a way that broke the node list for that node. Packs that need a paid service, a browser tab to render, or that write into model folders at import were rejected in triage, and so were all Ollama packs. [claim: studio install record 2026-11-03] [inference]

Pool 51 graph check: with the packs loaded, the studio's graph audit went from 666 graphs ok and 351 missing a node to 669 ok and 350 missing a node. No graph that was ok got worse. The IC-Light relight family graph went from missing a node to ok. [claim: studio install record 2026-11-03] [code: scripts/graph_audit.py:1]

Pool 51 proof prompts: three SDXL pictures at 1024 x 1024, 25 steps, through the GPU gate on the test ComfyUI, peak 11.0 GiB. The plain core picture took 19.8 s. Detail Daemon at 0.15 kept the composition and added fine detail; at 0.5 it overcooked the picture into a stipple, which is the setting, not the node. A Darkroom film-stock grade with halation and grain came out as a warm film look. Looked at by a person; one run each. [claim: studio install record 2026-11-03]

Pool 51 packs needed 16 new Python packages, installed against the studio's constraints file; no protected package moved and nothing was downgraded. Installed is not proven: most of the new nodes have not yet run inside a studio graph, so describe them as available, not as tested. [claim: studio install record 2026-11-03] [inference]

## Families rendered in the last hours

Ideogram4 and Ming-Image each rendered once on 2026-11-03 on their own family servers, from ComfyUI's own templates, and were looked at full size. Ideogram4: 28.6 s, 33.2 GiB, with the 8B Qwen3-VL text encoder in bf16 in place of the template's fp8 file; its licence is non-commercial. Ming-Image: 21.4 s, 23.6 GiB, with the prompt expander bypassed; MIT. [run: studio/family_status.json:3909, studio/family_status.json:5942]

MOVA was tried on 2026-11-03 and still gives all-black frames through core Wan nodes (832 x 480, 49 frames, 20 steps, peak 42 GiB), even with its own VAEs. It needs MOVA's own pipeline, and the only ComfyUI node for it is its author's unfinished alpha. [run: studio/family_status.json:6966]

LongCat-Avatar 1.5, HunyuanVideo 1.5, InstantMesh, SAM 3 and the rife family also gained their first renders on 2026-11-03; their own specialists' NOW.md files have the numbers. [run: studio/family_status.json] [inference]
