# Train: playbook

These Train notes describe the code as of 2026-11-02. [code: studio/train.py:1-16]

## What the Train page is

The Train page takes pictures, or audio clips for an audio base, and gives back a LoRA. It drives one of three trainers. ComfyUI's own nodes run LoadImageTextDataSetFromFolder, MakeTrainingDataset, TrainLoraNode and SaveLoRA, with PreviewAny printing the loss list. ostris ai-toolkit and SimpleTuner each run as a separate process, which the studio starts and follows through its own log and output folder. The studio trains nothing itself. [code: studio/train.py, studio/trainers/base.py, studio/trainers/aitoolkit.py, studio/trainers/simpletuner.py]

## Which bases Train can use

Every base Train knows is one entry in studio/train_bases.py. Each entry names its trainer, the files it needs, its licence with a link and a one-line note, the peak VRAM its family is expected to need, and how its A/B is rendered. [code: studio/train_bases.py]

Each base has one of three states on the page. Proven means its files are here and a real run is on record in train_measured.json or the studio's own runs. Not run means everything is here but no run is on record, and the first run needs a tick saying so. Blocked means something is missing, and the page names exactly which file, folder or trainer install. [code: studio/train.py] [test: tests/studio_lanes/test_train_external.py]

For a ComfyUI base, Train looks for each file by name in the folder lists ComfyUI reports, sub-folders included, and reads the model's safetensors header. Quantized weights are refused unless the entry says the base is quantized. For an external trainer, it checks the trainer's install folder and Python, then each file or folder the job file names. [code: studio/train.py, studio/trainers/aitoolkit.py, studio/trainers/simpletuner.py] [test: tests/studio_lanes/test_train_external.py]

Some bases are blocked on purpose with a known_failure line: FLUX.3 Klein, Anima and ERNIE Image fail inside ComfyUI's TrainLoraNode, because an operation they use has no gradient, and no other trainer is wired for them yet. [code: studio/train_bases.py] [run: studio/train_measured.json] [inference]

STUDIO_TRAIN_PROVE is off by default. Setting it to a base id lets that base have its first run without the page's tick. [code: studio/train.py]

## What Train has measured

Every recorded Train run is a row in studio/train_measured.json, copied from that run's own record: base, size, rank, steps, seconds per step, setup time, the whole card's peak VRAM and, where measured, the run's own peak. Most rows are 512 px, rank 16 and 150 to 300 steps on a 96 GB card, and each row's ab_effect says what a person saw in its A/B. [run: studio/train_measured.json]

The whole-card peak includes everything else on the card at that moment. The run's own peak counts only that run's processes: an external trainer and its children, or the ComfyUI serving the studio, found by its port. [code: studio/train.py] [run: studio/train_measured.json]

Train gives a time and VRAM figure only from a measured run on the same card, at the same size and batch, with no scaling formula. [code: studio/train.py] [test: tests/studio_lanes/test_train.py]

## Pictures and captions in Train

Train accepts png, jpg, jpeg and webp, with an optional .txt caption of the same name. A set needs at least 2 pictures and holds at most 500, each up to 50 MB. A picture is kept only if PIL can decode it. Pictures can be dropped on the page or imported from a folder. [code: studio/train.py:50-52, studio/train.py:198-220, studio/train.py:293-307] [test: tests/studio_lanes/test_train.py]

The Train caption check has two levels. Block, which stops Train: no caption, a word-list hit in a caption or file name, or too few pictures. Warn, which does not: trigger missing, over 65 words, picture smaller than the training size, nearly one flat colour, duplicate file, or under 10 pictures. Buttons can add the trigger to captions that lack it, fill empty captions or remove a picture. [code: studio/train.py:232-256, studio/train.py:368-392] [test: tests/studio_lanes/test_train.py]

When a Train job starts, the studio makes a copy for ComfyUI: each picture centre-cropped and scaled to one square size, saved as numbered PNGs with captions beside them, in a folder under ComfyUI's input. The originals stay as they are. The copy is deleted when the job closes. [code: studio/train.py:597-605, studio/train.py:762-764] [test: tests/studio_lanes/test_train.py]

## Train settings and starting a run

Train settings and limits: steps default 300, from 1 to 5000; rank default 8, one of 4, 8, 16, 32; batch default 1, one of 1, 2, 4; learning rate default 0.0005, from 0.000001 to 0.01; seed default 0. Size defaults to the largest the base allows. [code: studio/train.py:46-49, studio/train.py:584-594] [test: tests/studio_lanes/test_train.py]

Some Train settings are fixed in the graph and the page has no control for them: optimizer AdamW, loss MSE, training and LoRA dtype bf16, gradient checkpointing on at depth 1, offloading off, bucket mode off, bypass mode off, algorithm LoRA, one gradient accumulation step. [code: studio/train.py:510]

Train has a "See the graph it will run" button. It shows the API graph and checks each node, link and value against this ComfyUI's /object_info. If ComfyUI is down the page says the graph was not checked. The real start validates the graph again before queueing it. [code: studio/train.py:534-562, studio/train.py:664-665, studio/train.py:1053-1063, studio/web/train.js:94-95] [test: tests/studio_lanes/test_train.py]

To start Train you need a set with no blocks, a name, a one-word trigger of 2 to 40 characters, a base and the rights tick. Only one Train job runs at a time, and a second gets a refusal. The tick clears after each start, so each run asks again. [code: studio/train.py:630-645, studio/web/train_logic.js:122-132, studio/web/train.js:154] [test: tests/studio_lanes/test_train.py]

## Following a Train run

While Train runs, the curve comes from "Training LoRA" lines in ComfyUI's log, which tqdm samples, so not every step appears. When the run ends the node's own full loss list replaces it. The server sends at most 600 real points, every Nth, never averaged. The page draws a separate trailing average and labels it. [code: studio/train.py:681-711, studio/train.py:800-807, studio/train.py:876-882, studio/web/train_stage.js:33] [test: tests/studio_lanes/test_train.py]

A Train A/B renders one picture on the base and one with the LoRA: same seed, euler, normal schedule, 25 steps, CFG 7, empty negative prompt. Seed defaults to 1234 and strength to 1, up to 2. It reports the mean pixel difference out of 255 and counts "lora key not loaded" log lines. [code: studio/train.py:516-531, studio/train.py:945-963, studio/train.py:972-977, studio/train.py:1006-1007] [test: tests/studio_lanes/test_train.py]

A finished Train LoRA is copied to a parametric_trained folder inside the loras folder, with its name, base, steps and job id in the file name. The studio records its size, SHA-256 and tensor count. The file must hold lora_up weights to count. The Library's LoRAs view and the Train page list it through /api/train/loras. [code: studio/train.py:57, studio/train.py:810-832, studio/train.py:1015-1024, studio/web/train.js:127-129] [test: tests/studio_lanes/test_train.py]

## Train and the LoRA recipes

Train does not read lora_recipes.json. That file holds 162 tuned settings for third-party LoRAs, with families such as h3, wan22, qwen and ltx and none for SDXL or SD 1.5. The only thing train.py does with studio/loras.py is clear its file-list cache after a run. [run: studio/lora_recipes.json] [code: studio/train.py:846-850, studio/loras.py:21-25]
