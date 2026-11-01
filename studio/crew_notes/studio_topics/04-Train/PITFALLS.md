# Train: pitfalls

These Train notes describe the code as of 2026-11-01. [code: studio/train.py:1-13]

## What Train has not proven

Train has one real run behind it: one SDXL LoRA at 1024 px, rank 8, batch 1. Rank 4, 16 and 32, batch 2 and 4, 768 px, Continue and every SD 1.5 path are wired and covered only by tests on a stand-in, with no recorded run of them. [run: studio/train_measured.json] [test: tests/studio_lanes/test_train.py]

The Train server tests never touch a real ComfyUI. test_train.py replaces the ComfyUI call and every folder, its object_info fixture is copied from a real one with the model lists cut down, and its loss values are test data. They prove the page's logic and graph shape, not that a LoRA trains well. [test: tests/studio_lanes/test_train.py]

## Train numbers that are easy to misread

Train's peak VRAM is the whole card, not the training's own share. It polls nvidia-smi's used memory, or ComfyUI's report if that fails, and keeps the highest value. So the 40.25 GiB figure includes anything else on the card at that moment. It is not a minimum requirement. [code: studio/train.py:130-140, studio/train.py:743-744] [run: studio/train_measured.json] [inference]

Train loss is expected to look messy, because each step uses a random noise level. A flat line does not mean failure and does not prove success. In the recorded run the mean rose from 0.1626 to 0.1849 and the pictures still changed. The A/B is the real test. [code: studio/web/train_stage.js:49-57, studio/web/train_logic.js:96-101] [test: tests/studio_lanes/test_train_logic.mjs]

The one Train loss reading that means trouble is not-a-number. The job sets loss_nan, the page shows an alarm, the bad value is sent as null and the line breaks instead of joining across it. The run is not stopped for you. [code: studio/train.py:711, studio/train.py:893, studio/web/train_stage.js:74] [test: tests/studio_lanes/test_train.py, tests/studio_lanes/test_train_logic.mjs]

The Train A/B pixel difference shows that the LoRA changed the render, not that the change is good. Under 0.05 of 255 the page warns that the LoRA did nothing visible. It also warns if ComfyUI could not place some LoRA weights, or if the log could not be read. [code: studio/web/train_logic.js:157-167] [test: tests/studio_lanes/test_train_logic.mjs]

## Train limits on saving and resuming

TrainLoraNode has no mid-run checkpoints, so Cancel or a crash loses all the steps of that run and no LoRA is saved. Continue is not a resume: it feeds a finished LoRA into the node's existing_lora input without the optimizer state, so it is a new run on old weights. It needs a finished job on the same base whose file is still there. [code: studio/train.py:11-12, studio/train.py:652-655, studio/web/train_stage.js:80] [test: tests/studio_lanes/test_train.py]

A Train job can end as "lost" if ComfyUI forgets it for over 30 seconds, most likely after a restart, and no LoRA was saved. If ComfyUI just stops answering, the job keeps its state and is marked unreachable. A "successful" run with no loss value, or with SaveLoRA's file missing or lacking LoRA weights, ends in error, and no path is made up. [code: studio/train.py:59, studio/train.py:730-733, studio/train.py:751-752, studio/train.py:788-794, studio/train.py:813-818] [test: tests/studio_lanes/test_train.py]

Train holds the GPU for its whole run, and other ComfyUI jobs wait behind it. A job can also wait behind other jobs in ComfyUI's queue, and the page shows its position. Cancel removes or interrupts only this job. [code: studio/web/train_stage.js:80, studio/train.py:745-748, studio/train.py:926-937] [test: tests/studio_lanes/test_train.py]

## Train checks that are not safety guarantees

Train does not look at pictures, because the studio has no image classifier yet. Only words are checked: captions, file names, LoRA name, trigger and test prompt, against a word list that also reads file-name forms. So "ready" means words and file details passed, not that the set is good, and the page says a word list misses plenty and is not a safety guarantee. [code: studio/web/train.js:176, studio/train.py:160-166, studio/train.py:233] [test: tests/studio_lanes/test_train.py]

Train's rights tick is a statement by the user that nothing can check: that they own or have rights to the pictures, and that no real person's likeness is trained without consent. The server refuses to start without it being exactly true, and stores it in the job record. [code: studio/train.py:631, studio/train.py:671, studio/web/train.js:178] [test: tests/studio_lanes/test_train.py]

## Train output quality traps

Train LoRAs can overfit. In the recorded run a prompt for a harbour town gave brass towers, because 12 pictures of one subject teach one idea. Under 10 pictures gets a warning that the LoRA tends to copy them, yet 2 is enough to run. The graph makes no sample pictures on the way, so the A/B at the end is your first look. [code: studio/web/train_stage.js:55, studio/web/train_stage.js:101, studio/train.py:254]

Train centre-crops every picture to one square, and bucket mode is off, so anything near the edges of a wide or tall picture may be cut. Pictures below the training size are scaled up, and the check warns they may go soft. [code: studio/train.py:510, studio/train.py:603, studio/train.py:246] [inference]

## Train and other LoRA lists

A LoRA made by Train does not show up in the "Search every LoRA" box, despite that label. The box uses /api/loras, which lists only files with a curated recipe and counts the rest as other_files. A trained LoRA has no such recipe. It is listed by /api/train/loras instead. [code: studio/train.py:1015-1024, studio/web/train.js:129-134, studio/loras.py:322-324, studio/loras.py:342] [inference]

Recipes cannot be applied to a Train LoRA. loras.apply_to_graph only takes an id from the curated list with a run block, and all 29 such rows are H3. Those recipes are not proof of a render here either: of 162 rows, 85 are level "recipe" and were never rendered, 70 "load-tested", 6 "verified" and 1 "warned", recorded on the earlier studio. [code: studio/loras.py:22, studio/loras.py:30-39] [run: studio/lora_recipes.json]

## Train folder import limits

Train's folder import only reads inside the home folder, ComfyUI's input and output folders, or STUDIO_TRAIN_IMPORT_ROOTS. It refuses relative paths and any path through a hidden folder. It reads only pictures and .txt files directly in that folder, skips links, and stops after 1000 files. Subfolders are not read. [code: studio/train.py:310-324, studio/train.py:333-342] [test: tests/studio_lanes/test_train.py]

Train needs ComfyUI's input folder on the same machine, because LoadImageTextDataSetFromFolder cannot read anywhere else. If the studio cannot find it, the start fails with a 503 asking for STUDIO_COMFY_INPUT. A ComfyUI on another machine would not see the prepared copy. [code: studio/train.py:55, studio/train.py:657-658] [inference]
