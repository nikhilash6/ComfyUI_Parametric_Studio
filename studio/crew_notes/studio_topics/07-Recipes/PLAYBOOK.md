# Recipes and Processes: playbook

## What a recipe is

Recipe state on 2026-11-01. A recipe is a multi-step chain. Each step is a studio goal, a local ComfyUI template, a small ffmpeg step or a written plan, and a step's output is uploaded as the next step's input. [code: studio/recipes.py:1, studio/recipes.py:415-419]

Recipes have one worker thread, so one recipe runs at a time and the others wait in line with a position number. [code: studio/recipes.py:536-546, studio/web/recipes.js:88] [test: tests/test_studio_recipes.py]

The recipe VRAM gate runs before every GPU step. Free memory must cover the step's peak_gib plus 4 GiB, or 90% of the card on a smaller card. The gate unloads ComfyUI, waits up to 10 minutes showing why, then fails the step with the numbers. [code: studio/recipes.py:11, studio/recipes.py:380-395] [test: tests/test_studio_recipes.py]

Recipe run state is a JSON file next to the outputs. A run that was queued or running when the server restarted reads back as "interrupted", with its finished steps kept. A failed step stops the chain and says why, and each step keeps its exact graph next to the run. [code: studio/recipes.py:312-314, studio/recipes.py:319-326, studio/recipes.py:427-430, studio/recipes.py:525-528] [test: tests/test_studio_recipes.py]

## The ffmpeg and CPU steps

Recipe CPU steps are frame, join, beat_cut, cut_between, loop, compare, mux and sound. They use no model. The sound op makes a file on the CPU with no ffmpeg check; the others need ffmpeg. [code: studio/recipes.py:475-492, studio/recipes.py:598, studio/recipe_check.py:76-78]

The beat_cut step measures tempo and beats in the song, picks its loudest section, cuts each clip on a beat at 24 fps, and normalizes loudness to -14 LUFS. The loop step fades a clip's tail into its head and reports SSIM across the seam; the loop gets shorter by the fade. Tests run both for real on generated signals. [code: studio/recipes.py:12, studio/recipes.py:160-180, studio/recipes.py:194-203] [test: tests/test_studio_recipes.py]

## The 10 flagship recipes

The file recipes.json holds 10 flagship recipes: short_film, seamless_loop, seasons_shot, vfx_stack, product_ad, music_video, anime_opening, recast_character, multicam and open_lane. All 10 carry a tested record. [run: studio/recipes.json]

The short_film recipe rendered on 2026-10-30: 690 s of step time, 1226 s of wall time, 76.2 GiB peak, 22.7 s of video, cut at 160.1 BPM, with a local language model writing the shot list. The music_video recipe took 781 s and 68.6 GiB the same day. One run each, in windows shared with other jobs, so those peaks are whole-card figures, not what a recipe needs alone. [run: studio/recipes.json]

The other flagships rendered on 2026-11-01 and 2026-11-02 through the real recipe route on a dev studio and a private ComfyUI lane, one at a time through the shared GPU gate: seamless_loop 91.8 s of step time, 8009.6 s wall, 41 GiB, 4.67 s of video; seasons_shot 227.5 s of step time, 242.9 s wall, 41.2 GiB, 10.08 s of video; vfx_stack 126.4 s of step time, 1975.4 s wall, 38.3 GiB, 4.04 s of video; product_ad 260 s of step time, 1392.4 s wall, 41.2 GiB, 9.29 s of video; anime_opening 248.2 s of step time, 2361.3 s wall, 41.1 GiB, 12 s of video; recast_character 558.2 s of step time, 1556.9 s wall, 39.7 GiB, 5.17 s of video; open_lane 471.5 s of step time, 4106.3 s wall, 29.3 GiB, 12.75 s of video; multicam 221.8 s of step time, 4201.3 s wall, 41.2 GiB, 5.2 s of video. Wall time includes waiting for the gate. Their peaks are the lane's own ComfyUI memory, not the whole card. Each note in the tested record says what was checked frame by frame and what stays weak. [run: studio/recipes.json]

The measured table in recipes.json holds seconds and peak GiB per goal from real renders on one 96 GB card with a cold load, for example image 10 s and 23 GiB, h3_video 112 s and 46 GiB, music 19 s and 27 GiB. A recipe's expected time is the sum of its steps' rows. [run: studio/recipes.json] [code: studio/recipes.py:564-565]

## The recipe library

The recipe library has 783 rows: 621 ported from the author's earlier studio plus 162 from curated LoRAs. By file: pictures 419, video_templates 82, stylizers 50, sounds 48, timelapses 12, loops 10. By kind: picture 469, video 104, sound 48, lora 162. [run: studio/recipe_library/pictures.json] [code: studio/recipes.py:24-32]

Library picture recipes use the image goal (407) or the krea2 goal (12). Stylizers draw a source with the image goal, then redraw it with a Klein edit template. Sounds are one CPU step. Video templates use h3_video steps, and 34 end in a join. Loops and timelapses chain a still, director_keyframes and a CPU step. [run: studio/recipe_library/pictures.json, studio/recipe_library/stylizers.json, studio/recipe_library/video_templates.json, studio/recipe_library/loops.json, studio/recipe_library/timelapses.json]

The curated LoRA rows number 162: 76 for H3, 48 for Wan 2.2, 12 for Qwen, 9 for LTX, 6 for Wan 2.1, the rest small groups. Only 29 can run, all of them H3. The other 133 are reference cards that say why not. [run: studio/lora_recipes.json] [code: studio/recipes.py:42-47]

## What rendered: recipe_renders.json

The file recipe_renders.json lists 533 library recipes with one passed run each, all dated 2026-11-01. By family: picture 417, stylizer 50, sound 48, video 6, lora 6, loop 5, timelapse 1. The other 250 library rows have no render: 2 pictures, 92 videos, 156 LoRAs. [run: studio/recipe_renders.json]

Recipe render numbers for pictures: 417 rows, 8.5 to 814.7 s, median 12.6 s, peak 16.7 to 56.1 GiB. Stylizers: 50 rows, 6.0 to 53.7 s, median 8.05 s, peak 11.5 to 16.9 GiB. Sounds: 48 rows, under 1 s, no GPU. [run: studio/recipe_renders.json]

Recipe render numbers for video chains: 6 video templates took 190.9 to 552.4 s, peak 39.6 to 56.4 GiB. 5 loops took 92.4 to 198.5 s, peak 41.0 to 41.4 GiB. 1 timelapse took 228.2 s, peak 41.1 GiB. 6 LoRA recipes took 81.2 to 495.5 s, peak 31.9 to 41.8 GiB. [run: studio/recipe_renders.json]

## Proof levels

Recipe "tested" means a row in recipes.json has a tested record with media and numbers from a real run. Only rows in recipes.json hold one today, and all 10 do. The page words it "Tested by the author". [code: studio/recipes.py:565, studio/recipes.py:609-614, studio/web/recipes.js:24] [test: tests/test_studio_recipes.py]

Recipe "Our own render" means the recipe has a row in recipe_renders.json: one run in this studio, made once and reviewed. It does not make the recipe tested: its status stays "untested". [code: studio/recipes.py:19-23, studio/web/recipes.js:24, studio/web/recipes.js:125] [test: tests/test_recipe_renders.py]

Recipe "ready" means an offline check passed: every step's graph is built and read against ComfyUI's object_info for node types, required inputs, links and choices, and model files of at least 4096 bytes are on disk. The result is True, False, or None when ComfyUI could not be asked. It renders nothing. [code: studio/recipe_check.py:8-19, studio/recipe_check.py:31-51, studio/recipe_check.py:87-95]

Recipe library "ported" means the row came from the author's earlier studio with the proof level that studio recorded. The stored levels are verified, load-tested, recipe and warned. The note in each library file says nothing counts as tested until it renders here. [code: studio/recipes.py:25, studio/recipes.py:577] [docs: studio/recipe_library/loops.json]

Recipe proof level counts: all 621 ported rows say "recipe". The 162 LoRA rows say recipe 85, load-tested 70, verified 6, warned 1. On the card these read "Recipe: no render shown", "Load-tested on the earlier studio", "Verified on the earlier studio" and "Earlier verdict: see the notes". [run: studio/recipe_library/pictures.json, studio/lora_recipes.json] [code: studio/web/recipes.js:24]

## How a user runs a recipe

The Recipes tab shows the flagship cards, then the library with chips for All, Pictures, Video, Sound and LoRAs, plus "Can start here" and a filter for our own renders. Library rows with a render sort first, 60 to a page. [code: studio/web/app.js:279, studio/web/recipes.js:120-126, studio/recipes.py:641-643]

A recipe page shows steps, models with licences, fields to fill, expected time and peak, and Run. A step marked swappable takes the user's own upload in place of rendering, and the step shows as skipped. Cancel stops a running chain. [code: studio/web/recipes.js:76-100, studio/recipes.py:504-506, studio/recipes.py:679-680] [test: tests/test_studio_recipes.py]

## Processes

The Processes tab lists 97 production methods from the author's earlier studio. Status counts: old 66 ("Tested on the author's old stack"), untested 28, here 3. By kind: video 25, image 19, 3D 12, audio 12, helper 12, character 6, finish 6, prompt 5. [run: studio/processes.json] [code: studio/processes.py:1]

The 3 processes tested here are image-flux3-klein, music-minimax and video-h3-modes. For video-h3-modes only text to video and image to video rendered here; the other modes in its guide did not. [run: studio/processes.json] [test: tests/test_studio_processes.py]

Process open links: 50 rows in processes.json name something to open (28 family pages, 10 goals, 5 designers, 4 recipes, 3 edits), and 21 more get a family page from a NEAR table when loaded. That makes 71 that open and 26 that show as coming soon. 93 of 97 have a guide. [run: studio/processes.json] [code: studio/processes.py:10, studio/processes.py:12-16]

A process card reads "Tested here", "Opens here", "Closest match" or "Coming soon". "Closest match" means the same main model, with the full pipeline still to come. [code: studio/web/processes.js:56-57, studio/web/processes.js:63]
