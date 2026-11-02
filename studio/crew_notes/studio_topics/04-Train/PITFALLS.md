# Train: pitfalls

These Train notes describe the code as of 2026-11-02. [code: studio/train.py:1-16]

## What Train has not proven

Train's proofs are short runs on one small invented style set, so they prove that a trainer runs and that its LoRA loads. They do not prove quality. Several A/Bs showed a clear change only on a prompt close to the training set, and some showed little. ab_effect in train_measured.json records which. [run: studio/train_measured.json]

Video bases (Wan 2.2 5B, LTX-2.5, MiniMax H3) were trained on still pictures and tested on one frame, so motion is untested. [code: studio/train_bases.py] [run: studio/train_measured.json]

Cancel and resume on an external trainer are tested only against a stand-in trainer process, not on a real ai-toolkit or SimpleTuner run. [test: tests/studio_lanes/test_train_external.py]

The Train server tests never touch a real ComfyUI or GPU. ComfyUI's answers, every folder and the trainer process are stand-ins. [test: tests/studio_lanes/test_train.py, tests/studio_lanes/test_train_external.py]

## Train numbers that are easy to misread

Train's whole-card peak VRAM is not the training's own share; see the run's own peak instead where it was measured. It polls nvidia-smi's used memory, or ComfyUI's report if that fails, and keeps the highest value. So the 40.25 GiB figure includes anything else on the card at that moment. It is not a minimum requirement. [code: studio/train.py:130-140, studio/train.py:743-744] [run: studio/train_measured.json] [inference]

Train loss is expected to look messy, because each step uses a random noise level. A flat line does not mean failure and does not prove success. In the recorded run the mean rose from 0.1626 to 0.1849 and the pictures still changed. The A/B is the real test. [code: studio/web/train_stage.js:49-57, studio/web/train_logic.js:96-101] [test: tests/studio_lanes/test_train_logic.mjs]

The one Train loss reading that means trouble is not-a-number. The job sets loss_nan, the page shows an alarm, the bad value is sent as null and the line breaks instead of joining across it. The run is not stopped for you. [code: studio/train.py:711, studio/train.py:893, studio/web/train_stage.js:74] [test: tests/studio_lanes/test_train.py, tests/studio_lanes/test_train_logic.mjs]

The Train A/B pixel difference shows that the LoRA changed the render, not that the change is good. Under 0.05 of 255 the page warns that the LoRA did nothing visible. It also warns if ComfyUI could not place some LoRA weights, or if the log could not be read. [code: studio/web/train_logic.js:157-167] [test: tests/studio_lanes/test_train_logic.mjs]

## Train and VRAM

ComfyUI's training node can take far more VRAM than a base's render needs. At 512 px and rank 16 our FLUX.2 Klein 9B run used about 72 GB in its own processes, and runs on FLUX.1 schnell and Krea 2 passed 70 GB before failing out of memory. Our recorded peaks were sampled every 3 seconds, so a short spike can be missed. [run: studio/train_measured.json] [code: studio/train_bases.py]

A per-process memory cap such as torch's memory fraction does not hold this down. It limits only PyTorch's own allocator, and three runs went 13 to 22 GB past their caps. On a shared card, reserve the real worst case for one of these runs, about 75 GB and in effect the whole card, through whatever queue the card's users share, and run nothing else beside it. [inference]

## Train limits on saving and resuming

TrainLoraNode has no mid-run checkpoints, so Cancel or a crash loses that run, and Continue is a new run on a finished LoRA's weights without the optimizer state. External trainers save as they go: a stopped run keeps its saves, and Resume starts the trainer again, which picks up its newest save. A run stopped before its first save has nothing to resume from. [code: studio/train.py, studio/trainers/aitoolkit.py] [test: tests/studio_lanes/test_train_external.py]

Stopping an external trainer sends SIGINT to its own process group, then SIGTERM after a minute. The pid is checked against its start time first, so a recycled pid is never signalled. [code: studio/trainers/base.py] [test: tests/studio_lanes/test_train_external.py]

A Train job can end as "lost" if ComfyUI forgets it for over 30 seconds, and a "successful" run with no loss value or no LoRA file ends in error. No path is made up. [code: studio/train.py] [test: tests/studio_lanes/test_train.py]

## Train checks that are not safety guarantees

Train does not look at pictures, because the studio has no image classifier yet. Only words are checked: captions, file names, LoRA name, trigger and test prompt, against a word list that also reads file-name forms. So "ready" means words and file details passed, not that the set is good, and the page says a word list misses plenty and is not a safety guarantee. [code: studio/web/train.js:176, studio/train.py:160-166, studio/train.py:233] [test: tests/studio_lanes/test_train.py]

Train's rights tick is a statement by the user that nothing can check: that they own or have rights to the pictures, and that no real person's likeness is trained without consent. The server refuses to start without it being exactly true, and stores it in the job record. [code: studio/train.py:631, studio/train.py:671, studio/web/train.js:178] [test: tests/studio_lanes/test_train.py]

## Train output quality traps

Train LoRAs can overfit. In the recorded run a prompt for a harbour town gave brass towers, because 12 pictures of one subject teach one idea. Under 10 pictures gets a warning that the LoRA tends to copy them, yet 2 is enough to run. The graph makes no sample pictures on the way, so the A/B at the end is your first look. [code: studio/web/train_stage.js:55, studio/web/train_stage.js:101, studio/train.py:254]

Train centre-crops every picture to one square, and bucket mode is off, so anything near the edges of a wide or tall picture may be cut. Pictures below the training size are scaled up, and the check warns they may go soft. [code: studio/train.py:510, studio/train.py:603, studio/train.py:246] [inference]

## Train and other LoRA lists

A LoRA made by Train shows up in the "Search every LoRA" box, read from Train's run records, with its trigger, base family and a link to its run. Other unknown files are still only counted. [code: studio/loras.py] [test: tests/studio_lanes/test_train_external.py]

An external trainer's A/B is its own first sample against its last, same seed and prompt, so ComfyUI has not loaded that LoRA file. The page says so. [code: studio/train.py, studio/web/train_logic.js] [inference]

## Train folder import limits

Train's folder import only reads inside the home folder, ComfyUI's input and output folders, or STUDIO_TRAIN_IMPORT_ROOTS. It refuses relative paths and any path through a hidden folder. It reads only pictures and .txt files directly in that folder, skips links, and stops after 1000 files. Subfolders are not read. [code: studio/train.py:310-324, studio/train.py:333-342] [test: tests/studio_lanes/test_train.py]

Train needs ComfyUI's input folder on the same machine, because LoadImageTextDataSetFromFolder cannot read anywhere else. If the studio cannot find it, the start fails with a 503 asking for STUDIO_COMFY_INPUT. A ComfyUI on another machine would not see the prepared copy. [code: studio/train.py:55, studio/train.py:657-658] [inference]
