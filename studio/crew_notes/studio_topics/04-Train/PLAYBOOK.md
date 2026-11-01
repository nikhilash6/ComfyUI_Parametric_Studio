# Train: playbook

These Train notes describe the code as of 2026-11-01. [code: studio/train.py:1-13]

## What the Train page is

The Train page takes pictures and gives back a LoRA, using ComfyUI's own nodes: LoadImageTextDataSetFromFolder, MakeTrainingDataset, TrainLoraNode and SaveLoRA. PreviewAny prints the node's loss list so the studio can read it. The studio sends the graph to ComfyUI and watches it. It does not train anything itself. [code: studio/train.py:1-6, studio/train.py:505-513]

## Which bases Train can use

Train knows two bases: Stable Diffusion XL base 1.0 (file sd_xl_base_1.0.safetensors, 768 or 1024 px) and Stable Diffusion 1.5 (file v1-5-pruned-emaonly.safetensors, 512 px). A request naming any other base is refused. No Flux, Wan, H3 or Qwen base is in the list. [code: studio/train.py:42-45, studio/train.py:636-637] [test: tests/studio_lanes/test_train.py]

As of 2026-11-01 SDXL base 1.0 is the only Train base with a real run on record. Stable Diffusion 1.5 is wired in the code but has never trained here, so the page does not offer it. It only becomes available through the first-run switch described below. [run: studio/train_measured.json] [code: studio/train.py:458-460] [docs: README.md]

A Train base is offered only if all of this holds: ComfyUI answers, ComfyUI lists the file, the studio can open the file, its header passes the check, and a run is on record. When any of these fails, the page greys the base out and shows the reason. [code: studio/train.py:444-462, studio/web/train.js:85] [test: tests/studio_lanes/test_train.py]

The Train header check reads the safetensors header, not the file name. The file must have the tensor name prefixes of its architecture. Its diffusion model weights must be F16, BF16, F32 or F64. A file with comfy_quant or scale_weight keys counts as quantized and is refused. [code: studio/train.py:53, studio/train.py:405-421] [test: tests/studio_lanes/test_train.py]

STUDIO_TRAIN_PROVE is off by default. Setting it by hand to a base id lets that one base, with no run on record, have its first run, and the page then says "Not proved yet". The header and file checks still apply. Once that run has been recorded the switch is no longer needed for that base. [code: studio/train.py:459-461] [test: tests/studio_lanes/test_train.py] [docs: README.md]

The docstring of the Train code says TrainLoraNode has no list of architectures and that anything ComfyUI loads as a MODEL may run. That is a reading of ComfyUI's node, and only SDXL has been tried here. It is the reason a base needs a run on record before it is offered. [code: studio/train.py:8-10]

## What Train has measured

The one recorded Train run: SDXL base 1.0, 1024 px, rank 8, batch 1, 300 steps, 0.6155 seconds per step, 13.8 seconds of setup, 40.25 GiB peak on the whole card, dated 2026-11-01, job 4d13a830507c, on the test machine. [run: studio/train_measured.json]

The Train example on the empty page comes from that same run: "Brass lighthouse", 12 pictures, 187 seconds on a 96 GB card. All 300 loss values are stored. The mean loss was 0.1626 in the first tenth and 0.1849 in the last tenth, and the test holds both figures. [run: studio/web/train_example.js] [test: tests/studio_lanes/test_train_logic.mjs]

Train gives a time and VRAM figure only from a measured run on the same card, at the same size and batch, with no scaling formula. A different rank still gives a figure, marked as a close guide, and with no match the page says so and shows no number. A finished run adds its own line to measured.jsonl if its speed was seen in the log. [code: studio/train.py:489-500, studio/train.py:835-843, studio/web/train_logic.js:140-148] [test: tests/studio_lanes/test_train.py]

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
