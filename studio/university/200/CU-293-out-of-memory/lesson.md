# CU-293 - Out of memory: what ComfyUI tries first

**Objective.** Read an out of memory error, know what ComfyUI already tried, and change what's left, in the right order. Taught by Tinker Tune.

## The idea

Models are big, and your card has a fixed amount of memory. ComfyUI works hard not to run out. It moves models on and off the card, splits work into batches, and retries in smaller pieces. So by the time you see an error, several things already failed. Knowing them saves you from trying fixes it has already tried.

Plan the budget first. This lab gets you thinking in numbers:

{{play:vram}}

## What it does before anything fails

**Frees room.** `load_models_gpu` works out what a model needs and calls `free_memory`, which unloads models the current step doesn't need. This is why switching models takes a while.

**Loads part of a model.** If the whole model won't fit, it can load only part on the card and fetch the rest as needed. That is slow, and it works. On a recent install, dynamic VRAM (`--disable-dynamic-vram` turns it off) manages this differently, and we didn't trace that path in detail.

**Keeps a reserve.** `minimum_inference_memory` keeps about 1.2 GB back for the working sums: 0.8 GB plus the reserve, which is 400 MB on Linux and 600 MB on Windows. `--reserve-vram` sets that reserve yourself, if other programs share your card.

**Splits the conds.** With CFG, the model runs on both prompts at each step. `calc_cond_batch` runs them together only if 1.5 times the estimate is free. Otherwise it runs them one after the other, which takes longer and uses less.

**Splits the batch at decode.** `VAE.decode` works out `int(free / needed)` and decodes that many latents at a time.

## What it does when it fails

Each of these catches only an out of memory error. `raise_non_oom` passes on anything else.

| Where | What it retries |
|---|---|
| **VAE decode and encode** | Logs `Warning: Ran out of memory when regular VAE decoding, retrying with tiled VAE decoding.`, then decodes in tiles |
| **Upscale with a model** | Starts with tiles of 512, halves on failure, and gives up below 128 |
| **Split cross attention** | Empties the cache, tries once more, then splits into more slices, up to 64 |
| **The VAE's attention** | Falls back to a slower method that uses less memory |

The VAE path has a shortcut. If a VAE's estimate is reliable and doesn't fit, it skips the first try and goes straight to tiles.

A tiled decode isn't free. For a 1024 by 1024 SD image, the fallback's default tiles run three passes: the lab counts 23 tile decodes, and it averages them to hide the seams. So seeing that warning is your cue to expect a slow decode. A graph that tiles on purpose is below. Its `VAEDecodeTiled` has a smaller overlap at its own defaults, 8 latent cells and not 16, so the same image takes 19.

{{graph:sd15_tiled_vae}}

**The sampling steps have no such net.** Apart from the attention retry above, we found no fallback in `comfy/samplers.py`. If a step fails, the run fails. So the sampler is where you will usually meet this error.

## What the error looks like

When the failure gets all the way to the engine, it does this, from `execute` in `execution.py`:

1. Adds a tip to the message.
2. Logs a memory summary.
3. Logs `Got an OOM, unloading all loaded models.`, and unloads them.

We triggered this with a test node that raises the real error class. The message reached the client as:

```
CUDA out of memory. Tried to allocate 2.00 GiB.
This error means you ran out of memory on your GPU.

TIPS: If the workflow worked before you might have accidentally set the batch_size to a large number.
```

Because everything got unloaded, your next queue reloads the models, so it's slower. That's expected.

## What's left for you, in order

Try these roughly from cheap to costly.

1. **Check the batch size.** The tip is right: this is the common cause. Each extra latent adds memory.
2. **Look for what else is on the card.** Another program, or another model still loaded. Close them, or ask the server to let go of its models with the `/free` route.
3. **Lower the resolution.** Memory grows with pixels, and video adds frames on top. Doubling width and height is four times the pixels.
4. **Tile deliberately.** `VAEDecodeTiled`, and upscale in tiles. Use smaller tiles if needed.
5. **Use a smaller model file.** fp16 is half the size of fp32. Quantized files are smaller still, at some cost (CU-211).
6. **Flags.** `--reserve-vram`, `--disable-smart-memory` (offloads more eagerly), `--novram`, `--cpu-vae`. Read the help in `comfy/cli_args.py`. `--lowvram`'s own help says it does nothing when dynamic VRAM is on, and otherwise runs text encoders on the CPU. Changing a flag means a restart.

## What goes wrong

- **It worked yesterday.** Something's different: batch size, another program on the card, or a new LoRA. The tip exists because of this.
- **System memory, not VRAM.** A failure while loading, or a killed process with no message, may be RAM. The default cache also holds results in RAM. `--cache-none` or `--cache-classic` hold less (CU-221).
- **Fragmentation.** After many runs, free memory can be in pieces. Freeing the models, or a restart, can help where nothing else changed.
- **A custom node holds on to tensors.** Models or big tensors kept in a class attribute are never freed. If memory climbs on each run, suspect the last pack you added.
- **Video runs out at the end.** The VAE decode of many frames can need more than sampling did. Tile it, and look at tile size and frame overlap.
- **You raised the tile size and it failed.** Bigger tiles use more memory per tile. Smaller ones cost time. Tile settings trade one for the other.
- **The decode warning, every time.** Not an error. It works, slowly. If you want to avoid it, free more room before decoding.

## Lab

The lab uses the same formulas on made-up sizes, and a Python exception stands in for running out of memory. Nothing allocates anything.

The reserve, and how much is left for weights:

```text
minimum_inference_memory: 1.19 GB
card  8 GB: maximum_vram_for_weights  5.85 GB
card 12 GB: maximum_vram_for_weights  9.37 GB
```

The decode's batch rule:

```text
free 8 GB, 1.5 GB per latent: 5 at a time
free 2 GB, 3.0 GB per latent: 1 at a time
```

The retry:

```text
  whole decode
  Warning: Ran out of memory when regular VAE decoding, retrying with tiled VAE decoding.
  tiled decode
```

The upscaler's ladder, and its end:

```text
upscale model, the largest tile that fits is 128: ([512, 256, 128], 'ok')
nothing fits: ([512, 256, 128], 'raises the error')
```

What tiling costs:

```text
tiled decode of a 1024 by 1024 image, default tiles: 9 + 7 + 7 = 23 tile decodes
VAEDecodeTiled at its defaults, 512 and 64 pixels, so tile 64 and overlap 8: 9 + 5 + 5 = 19 tile decodes
```

And the sampler's choice:

```text
free 12 GB: 2 at a time
free  8 GB: 1 at a time
```

## Sources

- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_upscale_model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_upscale_model.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
