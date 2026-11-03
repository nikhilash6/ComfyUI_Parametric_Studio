# Recipes and Processes: pitfalls

## What the proof words do not say

Recipe state on 2026-11-01. Recipe "ready" is not "it renders". The check reads graphs against node definitions and looks for model files. It does not queue anything, judge output or measure memory. Wired and ready can still fail at run time. [code: studio/recipe_check.py:1, studio/recipe_check.py:87-95]

The recipe ready count cannot be quoted from the repo. It is worked out live from the user's ComfyUI and model files, so it differs per install, and it is None when ComfyUI cannot be asked. [code: studio/recipes.py:633-643, studio/recipe_check.py:91]

Recipe "Our own render" is one run with one seed and one set of default words. It shows the recipe worked once on the test machine. It does not show other prompts, other seeds or other machines work, and the row stays status "untested". [run: studio/recipe_renders.json] [test: tests/test_recipe_renders.py]

The stored proof note on a library recipe can look wrong next to a render. Many rows with a render still hold the note "Never rendered through this recipe". The page hides that note when a render exists, and the render row is the newer fact. [code: studio/web/recipes.js:91] [run: studio/recipe_library/pictures.json, studio/recipe_renders.json]

Recipe levels verified and load-tested describe the earlier studio, not this one. Their notes say "Not re-rendered on this studio's graph" or "Not rendered through this recipe". Load-tested also means the output was not judged. [run: studio/lora_recipes.json] [code: studio/web/recipes.js:23]

All 10 flagships carry a tested record. A tested record is one run with one seed: the notes in it say what stayed weak (product_ad's second camera barely moves, open_lane's first move is gentle). [run: studio/recipes.json] [code: studio/recipes.py:564-565]

## Reading the render numbers

Recipe render peak_vram_gib depends on peak_scope. It is the recipe's own lane for 482 rows, the whole card for 3 rows and none for the 48 sounds. The whole-card peak reached 82.3 GiB in one row while the highest own figure is 56.4 GiB. Do not read card peak as what the recipe needs. [run: studio/recipe_renders.json]

Recipe render seconds can hold waiting or sharing we cannot separate. pic_art_oil_impressionism took 814.7 s against a picture median of 12.6 s, and it is a whole-card row. That one figure is likely not its normal speed. [run: studio/recipe_renders.json] [inference]

## What blocks a run

The recipe run gate only applies to library rows. A library row whose check is False gets a 409 with the reason, and None is allowed through. Flagship recipes skip this check, so a missing model shows up when the step runs. [code: studio/recipes.py:673-677]

A recipe reference card cannot run. Reasons on record: 43 wait on a download because this edition has no Wan 2.2 14B LoRA graph and the files are absent, 43 have no tuned settings, 19 need a special graph, 12 need reference media, 12 name a Ref2VA base, 3 need chosen first and last frames, 1 has no recorded strength. [run: studio/lora_recipes.json] [code: studio/recipes.py:47, studio/recipes.py:672]

The recipe shot list needs a language model awake. A sleeping server is skipped. If none answers, the film runs on a fixed pattern with repeated words, and the plan says so. [code: studio/recipes.py:277-291] [test: tests/test_studio_recipes.py]

## Processes

Process status "old" is not proof here. It means tested on the author's old stack, and 33 of the 66 say only "Partly tested there". Do not read it as working in this studio. [run: studio/processes.json]

A process "Opens here" link means a tool opens, not that the process was run in this studio. Of the 71 that open, 49 are old, 19 are untested and 3 are here. A "Closest match" opens a page with the same main model, without the pipeline. [run: studio/processes.json] [code: studio/processes.py:9-10, studio/web/processes.js:63]

Process status and recipe status can disagree. The music-video process says untested in processes.json, while the music_video recipe it opens has a tested record. The process file was not updated from the recipe; trust the recipe's record for the recipe. [run: studio/processes.json, studio/recipes.json]

## Final session findings, 2026-11-03

The older recipe render pitfall gives peak_scope counts of 482 own-lane rows and 3 whole-card rows. In the current file those are 621 and 12, with 65 rows that have no GPU peak. Still read a card peak as the whole card, not what the recipe needs. [run: studio/recipe_renders.json]

Five H3 LoRA recipes that came out garbled have new settings but no new render. The hyperflow LoRA ran 3 steps although its name says 8, and gave noise; 16bit-pixel and retro-toon-70s smeared on res_multistep and now run Euler at 25 steps; the two photoreal image LoRAs laid a dotted mesh over faces on beta and now run on simple. Their notes ask for beta57, which the studio does not install. None of the five has a row in recipe_renders.json. [run: studio/lora_recipes.json, studio/recipe_renders.json] [code: studio/recipes.py:78]

The fourteen Wan 2.2 14B LoRA cards cannot start yet: their LoRA files were still downloading when they were wired, and each card says it is waiting. 43 Wan 2.2 LoRA rows carry that download wait. [run: studio/lora_recipes.json] [code: studio/recipe_check.py:107]

Recipe 3D downloads were wrong before 2026-11-02: every World Kit run names its mesh the same, and the build searched the whole output folder by that name, so five picture-to-mesh recipes shared one file, three places another and two word recipes a third. The test that each download is unique now guards this. [test: tests/test_recipe_renders.py] [claim: studio commit log, 2026-11-02]

Naming a thing in an H3 prompt, even to say it is absent, tends to make H3 draw it. Recipe videos that named signs, shop fronts or gloves drew them, so those lines were removed. Two redo shorts still drew gibberish lettering (a bottle label, a shopping bag) and were kept off the page. [claim: studio commit log, 2026-11-02]
