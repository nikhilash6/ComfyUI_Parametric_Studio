# CU-305 - VRAM budget math: weights, activations, caches

**Objective.** Work out, from numbers you already have, the weights, the working memory and the room ComfyUI asks for before a load, and say which one moves when you change the size, the batch or the format. Taught by Bit Bandit.

## Three things, three formulas

People ask "will this model fit?" as if the file were the only thing on the card. Three different things want room.

- **Weights.** The model itself. Parameters times bytes per parameter.
- **Working memory.** What a step needs on top of the weights: the activations. It grows with the picture, not the file.
- **Results.** What finished nodes hold on to. By default these sit in system RAM, not on the card.

## Weights

```
weights = parameters × bytes per parameter
fp32 = 4 bytes      fp16 and bf16 = 2 bytes      fp8 = 1 byte
```

For a file that holds only that model, the size on disk tells you nearly the same thing, so usually you need no sum at all. A full checkpoint also holds the text encoders and the VAE. The bytes matter when the loader stores weights in another format than the file: see CU-374.

## Working memory

This is the number that surprises people, because ComfyUI estimates it from the latent. `memory_required` in `comfy/model_base.py`, on the path used with PyTorch or flash attention, is:

```
area   = batch × height × width × (frames, for video)     in latent cells, channels not counted
memory = area × dtype bytes × 0.01 × memory_usage_factor  in MB
```

`memory_usage_factor` is a constant per model family, set in `comfy/supported_models.py`. `estimate_memory` in `comfy/sampler_helpers.py` doubles the batch before asking, because guidance can run both prompts together. The source's own comment on this formula says it needs tweaking, so treat it as ComfyUI's guess, not a measured peak.

Two things follow. Double the side of the image and the estimate goes up four times. Double the batch and it doubles.

## The room asked for

`load_models_gpu` in `comfy/model_management.py` adds these up before it loads:

```
extra_mem = max(minimum_inference_memory, memory_required + reserved)
room      = total model size × 1.1 + extra_mem
minimum_inference_memory = 0.8 GB + reserved
reserved  = 400 MB on Linux, unless you set --reserve-vram
```

If that much is not free, it unloads other models. If it still does not fit, the model loads partly. CU-402 follows that path, and CU-372 turns this into a checklist.

Dynamic VRAM, which is on by default on supported cards, changes how weights arrive: see CU-402. The arithmetic here still tells you what is going to be asked of the card.

## Results and caches

Node results are the third thing, and the word cache causes real confusion here. `intermediate_device` returns the CPU unless you pass `--gpu-only`, so a finished latent or image waits in system RAM. A latent is tiny. A long video as an `IMAGE` batch is not, and it never was on the card to begin with.

{{graph:sdxl_txt2img}}

Now put numbers on it. Use the sliders on your own card.

{{play:vram}}

The lab above is a planning sheet with an overhead slider you set yourself. It does not claim to know your peak.

## What goes wrong

- **"The file is 6 GB and my card is 8 GB, so it fits."** That leaves out reserved memory, the 10% margin and the working memory. Run the sum for your size and batch.
- **A graph ran at 1024 px, then fails at 2048 px.** Working memory went up four times while the weights stayed still. Lower the size, or decode in tiles if the decoder is what failed (below).
- **It fails only when decoding.** The VAE has its own estimate, set per VAE in `comfy/sd.py`. If decoding runs out of memory, ComfyUI retries in tiles and logs a warning, and `VAEDecodeTiled` asks for that directly.
- **Batch 8 fails where batch 1 worked.** ComfyUI's own out-of-memory message suggests this first. Queue single images, or split the batch.
- **System RAM runs out, not VRAM.** That is results, or weights being kept for the next run. See `--cache-ram` and `--cache-none` in CU-371.

{{graph:sd15_tiled_vae}}

## Lab

Everything here is arithmetic from the formulas above. No model is loaded. Weights first:

```text
weights: parameters x bytes per parameter (parameter counts from Table 1 of the SDXL paper)
  SD 1.x U-Net, 860M   fp32  3.20 GB  fp16  1.60 GB  fp8  0.80 GB
  SDXL U-Net, 2.6B     fp32  9.69 GB  fp16  4.84 GB  fp8  2.42 GB
```

The working memory estimate, with the factors from `supported_models.py`:

```text
working memory estimate, fp16, CFG on (estimate_memory doubles the batch)
  SD 1.5  512 px  latent 64x64  factor 1.0:    163.8 MB
  SD 1.5  768 px  latent 96x96  factor 1.0:    368.6 MB
  SDXL   1024 px  latent 128x128  factor 0.8:    524.3 MB
  SD3    1024 px  latent 128x128  factor 1.6:   1048.6 MB
```

Look at SD3 against SDXL: same latent size, twice the estimate, because the factor is twice as large. Now the scaling rule:

```text
double the side: x4.  double the batch: x2.  channels make no difference to this estimate.
```

The room asked for on a 12 GB card, with nothing else loaded:

```text
room asked for before loading, on a 12 GB card with nothing else loaded
  SD 1.5 fp16, 512 px   weights  1.60 GB  asks for  2.95 GB  left   9.05 GB
  SDXL fp16, 1024 px    weights  4.84 GB  asks for  6.52 GB  left   5.48 GB
  SDXL fp8, 1024 px     weights  2.42 GB  asks for  3.85 GB  left   8.15 GB
```

Going to fp8 halves the weights and leaves the working memory alone. The working memory depends on the compute format, which the lab holds at fp16. And results in RAM:

```text
what a finished result costs in system RAM (node outputs live on intermediate_device, the CPU, unless --gpu-only)
  latent 128x128, 4 channels, fp32         0.25 MB
  IMAGE 1024x1024, 3 channels, fp32       12.00 MB
  IMAGE batch, 81 frames 1280x720        854.30 MB
```

## Sources

- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
- [ComfyUI v0.43.0, comfy/sampler_helpers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sampler_helpers.py)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/supported_models.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/supported_models.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [Podell et al. 2023. SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis](https://arxiv.org/abs/2307.01952)
