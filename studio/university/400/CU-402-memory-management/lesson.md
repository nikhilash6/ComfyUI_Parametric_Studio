# CU-402 - Memory management: who gets the GPU

**Objective.** Read the load and unload lines in a ComfyUI log, predict an eviction, and know which flags change what. Taught by Bit Bandit.

## The idea

There are several models, one card, and activations that need room as well. ComfyUI budgets before each load, and evicts only what it has to. Models stay loaded after a run, and this is why the second run is fast.

Nothing here is a setting you need to touch for a normal graph. You learn it so that when a graph slows down or fails, the log means something.

## The mechanism

From `load_models_gpu` and `free_memory` in `comfy/model_management.py`:

```
inference_memory = 0.8 GB + EXTRA_RESERVED_VRAM          (400 MB on Linux, or --reserve-vram)
extra_mem        = max(inference_memory, memory_required + reserved)
free_memory( total_model_size × 1.1 + extra_mem )
```

`memory_required` is what the caller estimates its run will need, so it grows with latent size and batch. CU-305 has the formula.

Eviction is a sort, then a walk. Candidates sort by offloaded memory, largest first, then reference count, then size, smallest first. `free_memory` walks that list and stops as soon as enough is free. So a small model you are not using can leave before a large one, and a model that survived the walk stays loaded for next time.

If a model still cannot fit whole, it loads partly. `partially_load` places what fits, and the rest stays in RAM and travels to the card as layers need it. It works, slowly. On NVIDIA `MIN_WEIGHT_MEMORY_RATIO` is 0, so very little of the model is guaranteed to be on the card when memory is tight.

**Two regimes.** `enables_dynamic_vram` in `comfy/cli_args.py` turns dynamic VRAM on unless you pass `--disable-dynamic-vram`, `--highvram`, `--gpu-only`, `--novram` or `--cpu`. `main.py` then also needs a supported card and PyTorch. In that mode `free_memory` skips unloading dynamic models for other dynamic models, as the code's comment says this "works on-demand". The help text says `--lowvram` does nothing when it is on. The lab models the estimate-based path. We did not study the dynamic path in depth, and we make no timing claims about it.

**Other flags and events.** `--reserve-vram` keeps room for other software. On an out-of-memory error, `execute` in `execution.py` logs a memory summary, then calls `unload_all_models`. `POST /free` is the manual route.

## Try it

{{play:evict}}

This graph has three models in it, loaded at three different times: text encoder, then model, then VAE. Watch your console when you run it.

{{graph:sd15_txt2img}}

## Reading your log

On the estimate-based path a load ends in one of these lines. The wording is from `comfy/model_patcher.py`:

```
loaded completely; 7000.00 MB usable, 4900.00 MB loaded, full load: True
loaded partially; 5120.00 MB usable, 4890.00 MB loaded, 2377.00 MB offloaded, 128.00 MB buffer reserved, lowvram patches: 0
```

Those numbers are examples. Partial means slower and is not an error. With dynamic VRAM on you see a different line, this one from a run on our test machine:

```
Model AutoencoderKL prepared for dynamic VRAM loading. 160MB Staged. 0 patches attached. Force pre-loaded 110 weights: 187 KB.
```

The `Staged` figure is the size set up for on-demand loading, so it does not tell you how much is on the card at that moment. CU-370 goes through the whole console.

## What goes wrong

- **Every run reloads the model.** Something else is pushing it out. Look for `Requested to load` lines on every queue. Common causes are `--disable-smart-memory`, another large model in the graph, or another program on the same card.
- **`loaded partially`, and steps are many times slower.** The model does not fit next to everything else. Unload other models with `POST /free` between jobs, use a smaller format, or lower the size.
- **Out of memory, then everything is slow on the next run.** The error unloaded all models, so they have to load again. That is not a second problem.
- **Another program crashes when ComfyUI runs.** ComfyUI has no idea what that program will need. Give it room with `--reserve-vram`, and see `--vram-headroom` for the dynamic path in CU-371.
- **`--lowvram` changed nothing.** With dynamic VRAM on, its help text says it does nothing. Check the startup line that says dynamic VRAM is enabled.

## Lab

The sizes are examples, not measurements. The arithmetic and order come from the code, simplified: this model unloads whole models, ignores reference counts, and ignores dynamic VRAM.

```text
minimum_inference_memory: 1.191 GB
start, a 24 GB card                          free  24.00 GB   loaded: nothing
encode the prompt                            free  19.00 GB   loaded: text_encoder 5.0
    evict text_encoder (5.0 GB)
sample                                       free  12.00 GB   loaded: unet 12.0
decode                                       free  11.70 GB   loaded: unet 12.0, vae 0.3
```

The text encoder had to go, even on a 24 GB card, because 12 GB × 1.1 plus 6.4 GB does not fit beside it. Then the VAE fits with no eviction. A small card:

```text
    unet does not fit: 4.61 of 12.00 GB on the GPU, the rest is streamed from RAM per layer
```

```text
model share on the GPU: 38%. It runs, and each step copies the rest across PCIe.
```

Weights are simple arithmetic:

```text
  SD 1.x U-Net         fp32:   3.2 GB  fp16:   1.6 GB  fp8:   0.8 GB
  SDXL U-Net           fp32:   9.7 GB  fp16:   4.8 GB  fp8:   2.4 GB
```

The parameter counts, 860 million and 2.6 billion, are from Table 1 of the SDXL paper.

## Sources

- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/model_patcher.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_patcher.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [Podell et al. 2023. SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis](https://arxiv.org/abs/2307.01952)
