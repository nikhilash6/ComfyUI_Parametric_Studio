# CU-281 - Train a LoRA with core nodes

**Objective.** Run ComfyUI's own training nodes, say what each does, and read the loss curve for what it can and can't tell you. Taught by Tinker Tune.

## The idea

You don't need a separate trainer to make a LoRA. ComfyUI has training nodes in core. They are marked experimental. Six nodes do the whole job.

{{graph:sd15_train_lora}}

| node | what it does |
|---|---|
| `CheckpointLoaderSimple` | gives the model to train against, its text encoder and its VAE |
| `LoadImageTextDataSetFromFolder` | reads pictures from a subfolder of input, and a `.txt` of the same name as each caption. A missing caption becomes an empty one |
| `MakeTrainingDataset` | encodes each picture to a latent and each caption to conditioning, once, before training |
| `TrainLoraNode` | the training loop |
| `SaveLoRA` | writes the file into your output folder, with steps in the name |
| `LossGraphNode` | draws the loss to a picture |

The training itself needs a free GPU and a checkpoint. CU-412 covers the pictures and captions.

## What a step does

Here's the loop in `comfy_extras/nodes_train.py`, in plain words.

1. Pick `batch_size` pictures at random (`torch.randperm`), afresh each step.
2. Draw random noise, and a random noise level: a random number between 0 and 1 through `percent_to_sigma`.
3. Make the noisy latent. Ask the model for the clean picture.
4. The loss is how far that prediction is from the real clean latent. By default that's mean squared error.
5. Backpropagate. Only the LoRA's numbers are trainable, since the model was frozen with `requires_grad_(False)`.
6. Every `grad_accumulation_steps` steps, the optimizer updates them.

Before the loop, `_setup_lora_adapters` adds an adapter to every weight that has one, at rank `rank`, with alpha 1.0. So the scale is 1/rank, as CU-212 explains. The `down` matrix starts at zero, so the LoRA begins with no effect at all.

Four things the node doesn't do: it has no learning-rate schedule. It saves no mid-run checkpoint, so a crash loses the run. It makes no sample pictures. And text encoders are not trained: `MakeTrainingDataset` encoded them already, so your LoRA patches only the denoiser. That's why `LoraLoaderModelOnly` fits the file (CU-280).

## Our real run

We ran this path once, on the Train page of our studio, on SDXL base 1.0 rather than the SD 1.5 of the graph above. The job is named Brass lighthouse, and its test prompts use the word `brasslight`. It used 12 pictures, 300 steps, rank 8, batch 1, at 1024 pixels.

```text
the run's other numbers, from studio/train_measured.json and train_example.js
pictures 12   steps 300   average sightings per picture 25.0 at batch 1
rank 8   size 1024   seconds per step 0.6155   300 x 0.6155 = 184.7 s   peak memory 40.25 GiB   setup 13.8 s
```

That's on our test machine, on a large workstation card. 187 seconds in all, by the job's record. The memory peak of 40.25 GiB is what this run used on a 96 GB card. It's not a minimum for SDXL.

Here's the same prompt and seed with the LoRA off and on, at strength 1.

{{wipe:train_art/lighthouse_base.webp|train_art/lighthouse_lora.webp|Base|LoRA|brasslight, a weathered brass lighthouse on a rocky coast at golden hour, detailed photograph. Seed 1234, one seed.}}

With the LoRA on, the tower is taller and a brighter polished gold, with bands round it, and the sea and the light differ too.

And on a prompt that wasn't about lighthouses, a small harbour town in the rain:

{{wipe:train_art/harbour_base.webp|train_art/harbour_lora.webp|Base|LoRA|brasslight, a small harbour town in the rain, photograph. Seed 77, one seed.}}

The base is a dark harbour with boats. With the LoRA, stone towers and buildings in brass tones take over and the boats are gone. So the LoRA did pull toward what it learned. It also pulled hard on a prompt it wasn't for. CU-282 is about judging that.

That's what this run shows: the path produces a file that changes pictures. It doesn't show that 300 steps or rank 8 are the right settings. We did one run.

## Reading the loss

Now the part that surprises people. Here's the real list of 300 numbers.

```text
steps 300   lowest 0.0016   highest 1.1148   mean 0.2035   spread (sd) 0.1326

by tenths of the run
steps       mean     sd       min      max
  1-30      0.1626   0.1506   0.0036   0.5771
 31-60      0.1794   0.1186   0.0198   0.4858
 61-90      0.2082   0.0850   0.0445   0.4147
 91-120     0.2425   0.1015   0.0412   0.4747
121-150     0.2068   0.1157   0.0017   0.4156
151-180     0.1863   0.1306   0.0041   0.4352
181-210     0.2618   0.2239   0.0016   1.1148
211-240     0.1965   0.1104   0.0022   0.3836
241-270     0.2061   0.0950   0.0075   0.4051
271-300     0.1849   0.1091   0.0056   0.3936

first tenth 0.1626, last tenth 0.1849: it went up by 0.0223
```

The first tenth averages 0.1626 and the last 0.1849. It went up, and the pictures still changed. Does it mean anything? Shuffle the same 300 numbers and see how often chance gives a gap that wide:

```text
shuffled order, 5000 tries: a gap this wide came up 0.514 of the time
```

About half the time. So that gap is no evidence of anything, up or down. The noise in the list is far bigger than any trend, for a reason you already know. Each step is one picture at one random noise level, and some levels are harder than others. The list jumps between 0.0016 and 1.1148, and we'd put that down to those draws rather than to how well the training is going. The record doesn't hold each step's noise level, so that's a reading of the code and not a measurement.

Averaging shrinks the jumps, but slowly:

```text
window   largest step between neighbouring windows (not overlapping)
1        0.9361
5        0.1753
10       0.1097
30       0.0755
60       0.0544
```

Slide the window yourself over the real numbers.

{{play:lossread}}

So: a flat, messy curve doesn't mean failure. Nor does it prove success. A `NaN` (not-a-number) does mean trouble. The real test is a picture at a fixed seed, with the LoRA off and on.

## Settings

The node's defaults are for trying it out: 16 steps won't do much. Our run used 300. The widgets:

- `steps`: how many updates. Each step sees `batch_size` pictures, so 300 steps at batch 1 on 12 pictures is 25 sightings each on average (CU-412 shows the spread).
- `rank`: file size and capacity (CU-212, CU-420).
- `learning_rate`: default 0.0005, and it stays fixed for the whole run.
- `training_dtype`: bf16 by default. `none` leaves the model's compute dtype alone, and training then autocasts to fp16 for an fp16 model and to bf16 for anything else. `bypass_mode` is for quantized models, which CU-420 mentions.
- `existing_lora`: continues from a saved LoRA. The optimizer state isn't saved, so it's a new run on top of old weights, not a resume. The menu lists your loras folder, while `SaveLoRA` writes to the output folder, so move the file over. Keep `_N_steps_` in its name too: the node reads the step count from there, and stops with a ValueError on a name without it.
- `gradient_checkpointing`, on by default, lowers memory for some speed.

## What goes wrong

- **Out of memory at once.** The node loads the model fully. Free the card, lower the size, keep `gradient_checkpointing` on, or turn on `offloading`.
- **"Number of texts ... does not match number of images".** `MakeTrainingDataset` wants as many captions as pictures, or one, or none.
- **The folder isn't in the menu.** It must be a subfolder of input.
- **A caption file isn't read.** It must have the same base name as its picture, ending in `.txt`. A missing one gives an empty caption and no error.
- **Loss goes to `NaN`.** Something has blown up. Lower the learning rate, and check `training_dtype`. Our run had none of this, so that advice is general, not tested.
- **You stop it, and get nothing.** There's no mid-run save. Plan shorter runs, then continue with `existing_lora`.
- **You judge by the curve.** Judge by pictures.

## Lab

The lab reads the real loss list, the one in our Train page's example, and computes the tables above. No training happens in it. The shuffle test uses a fixed seed.

## Sources

- [Hu et al. 2021. LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [ComfyUI v0.43.0, comfy_extras/nodes_train.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_train.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_dataset.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_dataset.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/lora.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
