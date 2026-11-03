# MiniMax H3: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

GUIDE.md already holds the prompt-length research, the first-and-last-frame LoRA audit and the ten H3 scenes. This file adds what the last session found about speech, sound, LoRA retries and camera moves. [docs: studio/crew_notes/model_families/16-MiniMax-H3/dossier/GUIDE.md]

## H3 speaks only the words you write

MiniMax H3 does not write speech. Fifty talking video templates told it only that a person "speaks directly to the camera" or "explains the first point". With no words, H3 voiced fluent, made-up babble, and sometimes read the stage direction aloud. Whisper on the rendered recipe clips heard 80% to 371% word error rate against what the clips were meant to say. Measured by Whisper, not listened to. [claim: studio test run 2026-11-02] [code: studio/recipe_library/video_templates.json:61]

The H3 template fix follows MiniMax's prompt guide: a speaker phrase, the speaker ID (S1), "says:", then the exact words inside <d>[English] ...</d>. The words are an editable field per shot, with a written default sized to the shot at about 2.5 words a second. Each template's tip now says the line is sent word for word. [code: studio/recipe_library/video_templates.json:61] [claim: MiniMax base writing guide]

A test keeps the H3 templates on written words. No video template may ask for speech without a <d> block; every block must hold a declared field whose default is real words ending in punctuation, at least 80 lines in all; and each line must fit its shot, at most 3 words a second for a reference shot and 4.2 for text to video. [test: tests/test_h3_dialogue.py] [code: tests/test_h3_dialogue.py:20-49]

H3 greeting card A/B: the same seed (131513) and the same graph (FL2VA pruned int8 with the turbo 8-step LoRA), with only the prompt changed to the <d>[English] form. Word error rate went from 133% to 0%. The old clip said "Prime. How do you? Happy birthday, Sam."; the new one says exactly "Happy birthday, Sam!". One run on the test machine: 140.2 s, 40.4 GiB peak for the job. Measured by Whisper, not listened to. [run: studio/recipe_renders.json:14761-14780] [claim: studio test run 2026-11-02]

H3 render records still lag the fix. 50 video templates now carry a <d> line; 30 of them have a recorded render, and only the greeting card's record holds the new wording. The other 29 records were rendered from the old wording and still carry made-up speech; they were queued to render again. [run: studio/recipe_renders.json] [code: studio/recipe_library/video_templates.json] [claim: studio test run 2026-11-03]

H3 silent shots: describe the silence, don't forbid speech. The silent-fury template now says lips pressed tight, a glare, room tone, keyboard clicks and one angry exhale, instead of a line that negates speech. An earlier set of H3 notes found that negations prime the thing they forbid. [code: studio/recipe_library/video_templates.json:6914] [claim: earlier studio notes]

## Half-precision VAE was not the cause

The first suspect for garbled H3 speech was the half-precision (bf16) VAE that the studio's main ComfyUI used until 2026-11-02, because it breaks LTX's audio encoder. It was not the cause for H3: clips that already used <d> lines measured 0% to 6% word error rate on the same bf16-VAE lanes. The greeting re-render ran on an fp32-VAE lane, so that A/B changed the VAE as well as the prompt; the bf16 clips with <d> lines are what rule the VAE out. [claim: studio test run 2026-11-02] [code: studio/feature_dub.py:52]

The studio's main ComfyUI was switched from --bf16-vae to --fp32-vae on 2026-11-02, so H3 renders after that date decode in fp32. No H3 test compares the two settings on the same seed with written words. [claim: studio launch change 2026-11-02] [inference]

## Five H3 LoRAs that came out garbled

H3 hyperflow 8-step LoRA: its file name says 8 steps, but its recipe ran 3 and came out as noise, so the recipe now runs 8. PLAYBOOK.md says hyperflow does not load on pruned bases; this file is a pruned resize, and the retry has not rendered, so neither claim is settled. [code: studio/lora_recipes.json:4881] [docs: studio/crew_notes/model_families/16-MiniMax-H3/dossier/PLAYBOOK.md:70] [inference]

H3 style LoRAs 16bit-pixel and retro-toon-70s smeared into mush on res_multistep. They now run Euler at 25 steps on the simple scheduler, like the other H3 LoRAs in the recipe list. [code: studio/lora_recipes.json:5634, studio/lora_recipes.json:6713]

The two H3 photoreal image LoRAs laid a dotted mesh over faces on the beta scheduler. Their notes ask for beta57, from a pack the studio does not install, so they now run on simple. [code: studio/lora_recipes.json:3809, studio/lora_recipes.json:3900]

None of the five H3 LoRA retries has a render on record yet; the new settings are untested. [run: studio/recipe_renders.json] [inference]

## Camera moves through the Director goal

H3 Director camera moves on three rooftop scenes, with no people and no signs: dolly in, pan left and tilt up each came out as asked, MATCH by the camera checker and by eye. One run each on the test machine: 53 to 62 s, 39.4 GiB peak. [run: studio/camera_proof.json:472-506]

H3 take picking: three takes of a lighthouse dolly in all measured MATCH. The picker chose take 2, which pushes in most clearly by eye too. The checker overstated take 3's growth (44%) because breaking waves add to the measured motion. Each take took 29.7 to 36.2 s at 39.3 GiB. [run: studio/camera_proof.json:507-562, studio/camera_proof.json:5]

## Films

Film A's sound is a Music 3 score over H3's own room and set ambience, with no dialogue, and the README now says so. [docs: README.md:27]

Film A has one known sound flaw: in shot A12, H3's own crowd babble sits about 16.5 LU under the score. It is not fixed; the choices are to drop that shot's native audio in the cut or to render it again. [claim: studio review 2026-11-03]
