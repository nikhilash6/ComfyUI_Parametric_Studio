# CU-372 - Budgeting VRAM before you press Queue

**Objective.** Build a VRAM budget for a graph from file sizes, then decide what to change before it runs out. Taught by Bit Bandit.

## A sheet, not a guess

CU-305 gave the formulas. This lesson is the routine. You need your card's size and a file listing, and about two minutes.

**1. Your card.** Take the total and subtract what other programs use. `nvidia-smi` shows it, or `/system_stats`. ComfyUI also keeps a reserve back: 400 MB on Linux by default.

**2. Your files.** List every model the graph loads: diffusion model, text encoder, VAE, ControlNets, LoRAs. On disk, the size is close to what the weights take in memory at that format. To see more, read the header, which costs a few kilobytes, however big the file is. The lab does this by hand. It tells you the parameter count and the format of each tensor.

**3. What's on the card at the same time.** Not everything is. Models load when needed, and get unloaded when room is needed (CU-402). So the text encoder usually doesn't have to fit next to the diffusion model. It only needs to fit when it runs. If you're tight, it helps to think of each stage:

```
encode:  text encoder
sample:  diffusion model + LoRA patches + ControlNet + working memory
decode:  VAE + its working memory
```

**4. The working memory.** It depends on your size and batch. Use the estimate from CU-305. Decoding is often the moment that fails at high resolution, and tiled decoding is the cure.

**5. Compare.** Take your largest stage, add the 10% margin that `load_models_gpu` asks for, and compare with your card.

Try it. Keep your real numbers beside you.

{{play:vram}}

## If it doesn't fit

Do these in order, cheapest first, and only as far as you need to.

1. **Close other things on the card.** Free. `nvidia-smi` lists what is using it.
2. **Lower the size or batch.** Working memory falls with the area.
3. **Decode in tiles.** Costs time at decode, and leaves sampling alone.
4. **Use a smaller format for the diffusion model.** See CU-374. This one costs some quality, so compare the results yourself.
5. **Use a smaller model.** Sometimes the honest answer.

{{graph:b_unet_fp8}}

{{graph:sd15_tiled_vae}}

A partial load isn't failure. With a model too large for the card, ComfyUI can still run it, slowly. Dynamic VRAM's on-demand path is designed for this, and the startup warning in `main.py` claims native formats are fast even larger than memory. We haven't tested that claim, so measure yours.

## What goes wrong

- **Adding every file together.** They aren't all on the card at once, and you may rule out a graph that runs fine. Think in stages.
- **Forgetting the VAE's decode at the end.** A graph samples perfectly and then dies at the last node. Tiled decode is the fix.
- **A ControlNet or second model in the sampling stage.** It sits on the card with the main model. Add it to that stage.
- **Using GB and GiB interchangeably.** A file listed as 12 GB may be 11.2 GiB. The difference is 7%, which is a lot when you're tight.
- **Trusting a number that says the job will fit.** This is planning, not measurement. When your margin is thin, run it and read the console.

## Lab

The lab builds a tiny safetensors file in memory, reads only the header, and counts. This is the same layout as the real thing. Only a real file's size differs.

```text
header 364 bytes read, data 4259904 bytes not touched
tensors 4, parameters 2,113,552, by type {'F16': 2097152, 'F32': 16400}
```

Then a worksheet. Every size here is an example, so put in your own.

```text
budget sheet. Every size here is an example. Replace them with your own files' sizes
  card 24 GB, reserved 0.39 GB
    diffusion model file              11.60 GB
    text encoder file                  8.00 GB
    VAE file                           0.34 GB
    working memory (your estimate)     2.00 GB
    total 22.33 GB, left over 1.67 GB
  card 12 GB, reserved 0.39 GB
    diffusion model file              11.60 GB
    text encoder file                  8.00 GB
    VAE file                           0.34 GB
    working memory (your estimate)     2.00 GB
    total 22.33 GB, left over -10.33 GB
  card 12 GB, reserved 0.39 GB
    diffusion model file              11.60 GB
    VAE file                           0.34 GB
    working memory (your estimate)     2.00 GB
    total 14.33 GB, left over -2.33 GB
```

Read it the way the card sees it. On 24 GB, all of it fits at once. On 12 GB, the sheet with everything on the card is hopeless. Take the text encoder out, because it only needs to fit when it runs, and it is still 2.33 GB short. Only a smaller format fits:

```text
    the same model, fp8                5.80 GB
    VAE file                           0.34 GB
    working memory (your estimate)     2.00 GB
    total 8.53 GB, left over 3.47 GB
```

What each format costs for a given size:

```text
the same model in other forms, weights only. File size is about parameters x bytes
  6 billion parameters, fp16                  11.18 GB
  6 billion parameters, fp8                    5.59 GB
  6 billion parameters, 4-bit, with scales     3.14 GB
```

And the numbers that change with your settings:

```text
the sizes that move with your settings: working memory estimate for a model with factor 1, fp16, CFG on
  1024 px, batch 1:    655.4 MB
  1024 px, batch 2:   1310.7 MB
  1536 px, batch 1:   1474.6 MB
  2048 px, batch 1:   2621.4 MB
```

## Sources

- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [safetensors README, Format section](https://github.com/huggingface/safetensors/blob/62e4d8b86063a6e5f8967547fa09a09f67420e2a/README.md)
