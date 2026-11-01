# CU-291 - Black images, NaN and grey mush

**Objective.** Tell a NaN from a truly dark image, find where it started, and use the precision flags that exist. Taught by Bit Bandit.

## The idea

NaN means "not a number". It is what a float becomes after a sum with no answer, such as infinity minus infinity. It has two nasty habits:

- **It spreads.** NaN plus anything is NaN. Each layer of a network mixes each value with its neighbours, so one NaN grows until it fills the tensor.
- **It hides.** The last step turns it into pixel value 0. A black picture comes out, with no error.

We checked that last part on the real `SaveImage`, with a test node feeding it an image of all NaN, then read the PNG back:

```
image of NaN      pixels [0, 0, 0]        warning: invalid value encountered in cast
image of 5.0      pixels [255, 255, 255]  no warning
image of -5.0     pixels [0, 0, 0]        no warning
```

So the only trace is one line in the console, from numpy, at the save step. Look for it. Our search found no check in core's sampling loop that stops a run on NaN.

See how fast it spreads:

{{play:f_nan}}

## Is it NaN at all?

Don't guess. Put a probe on the latent, before the VAE. This is the usual graph with `PreviewAny` wired to the sampler's output.

{{graph:f_txt2img_probe}}

Read the text. If you see `nan`, the fault is in the sampler or the model. If the latent looks like ordinary numbers and the image is black, look at the VAE. Be careful: on a big tensor the text leaves out the middle, so a few NaN can hide. CU-295 shows that. A full spread is easy to see.

If there is no `nan` anywhere, your picture may really be dark. Numbers near 0 in the image mean the model made something black, or a mask or composite did.

## How NaN gets in

**The VAE in fp16.** The best-known case. The model card for the SDXL fp16 fix says: "SDXL-VAE generates NaNs in fp16 because the internal activation values are too big". fp16's largest value is 65504. Anything bigger becomes infinity, and infinity soon becomes NaN. The fix is a modified VAE, or a wider type. In the source, the help for `--fp16-vae` warns: "might cause black images".

ComfyUI chooses for you. `vae_dtype` goes in this order: a flag if you gave one, then the first type in the VAE's `working_dtypes` that the card suits, then fp32. The default list is bf16 then fp32, and some VAE families add fp16 to it in the source. As we read the code, the standard SD and SDXL VAEs keep the default list, so plain ComfyUI doesn't choose fp16 for them. You get there by forcing it. We read this, and did not test it on an SDXL VAE.

**A low-precision model.** Each type has a limit (CU-210 and CU-211). This is a place to look, though we didn't produce a NaN this way in a test.

**A strange setting.** Very high CFG scales up a difference at each step, so values grow. An extreme LoRA strength multiplies weights too. Worth checking, though again we didn't produce a NaN this way.

**A bad file.** A cut-short download fails to load at all (CU-294), so it won't get as far as a black picture. A file with NaN inside its weights would load. We didn't make one to test.

## The flags, as they exist

All of these are in `comfy/cli_args.py` at v0.43.0.

| Flag | What it does | When to try |
|---|---|---|
| `--fp32-vae` | Runs the VAE in fp32 | Latent looks fine, image is black. First thing to try. |
| `--bf16-vae` | Runs the VAE in bf16 | Same, on less memory |
| `--fp16-vae` | Forces fp16. The help warns of black images | Only if you know this VAE copes |
| `--cpu-vae` | Runs the VAE on the CPU | To rule out the card. Slow |
| `--force-fp32` | fp16 and bf16 checks answer no, for everything that asks them | To test whether precision is the cause at all. Uses much more memory |
| `--force-upcast-attention` | Upcasts attention. The help says "please report if it fixes black images" | Black images, when the others didn't help |

Change one, restart, and test on a small graph. Restarts interrupt jobs, so wait until the queue is empty. A flag isn't a fix to leave on forever. It's a test, and it tells you where the fault is.

## Grey mush

Grey, washed-out or smeared pictures have no NaN. They are valid numbers that mean little. These causes come from the code. **We didn't render them all for this lesson, so read the "looks like" parts as what the numbers suggest.**

- **Too little noise.** With denoise below 1, the sampler starts partway down. On an empty latent there's no picture underneath, and the model expects one. The lab prints the numbers. At denoise 0.25 on SD 1.5, it starts from sigma 0.231, against a possible 14.615. Expect little more than a smear. For text to image, use denoise 1.
- **Denoise of 0.** `set_steps` makes no sigmas at all, so no sampling happens.
- **The wrong VAE.** An SD 1.5 VAE and an SDXL VAE both take 4 channels, so nothing errors. Their scale factors differ, though, 0.18215 and 0.13025, so decoding through the wrong one starts 1.398 or 0.715 times off, on top of having learned a different space. Expect wrong colours and contrast.
- **A sampler that doesn't suit the model.** We have a real example. LCM is meant for models trained for it. On plain SD 1.5, with one seed, it gave a smooth blob rather than the astrolabe we asked for.

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-lcm.jpg|euler|lcm|Same SD 1.5 model, prompt and seed, one seed only. Lcm's edge measure is 6.51 to euler's 20.17 in the Sampling Lab's data. It is not grey, but detail is gone.}}

- **CFG 1 with a negative prompt.** At CFG 1 the negative isn't used (CU-208). That isn't mush, but it can look flat.
- **Too few steps.** See the [Sampling Lab](#sampling/renders) for what sampler and step choices do with one seed.

## What goes wrong

- **Black image, nothing in the error box.** Normal for NaN. Look in the console for `invalid value encountered in cast`, then probe the latent.
- **Black from one VAE decode, fine from another path.** Try a tiled decode, as in `sd15_tiled_vae` below. If only one path fails, you've learned the fault is in the decode.
- **You changed a flag and nothing changed.** You didn't restart, or the graph came from the cache, because flags aren't part of a node's key. Change the seed to force a new run.
- **A preview looks fine and the saved file doesn't.** Previews during sampling come from a quick approximation, not your VAE, so they can look fine while the real decode goes black.

{{graph:sd15_tiled_vae}}

## Lab

The lab shows the arithmetic in plain torch, with no model. A small convolution stands in for a VAE layer, and one NaN gets into everything:

```text
start: 1 NaN of 3072 values
after  1 layers:    27 NaN of 3072
after  8 layers:   867 NaN of 3072
after 24 layers:  3072 NaN of 3072
```

Clamping, as the VAE's output step does, keeps NaN. It has no way to fix it:

```text
clamp((v + 1) / 2, 0, 1) of nan, -5, 5, 0.5: [nan, 0.0, 1.0, 0.75]
to 8 bits, torch: 0  so NaN pixels land on 0: black
```

How fp16 gets there, and why bf16 doesn't at this size:

```text
in fp16: [60000.0, inf]  in bf16: [59904.0, 70144.0]  in fp32: [60000.0, 70000.0]
inf - inf: nan   inf * 0: nan
```

The two numbers from the grey section:

```text
latent scale, SD15 0.18215  SDXL 0.13025: decoding through the wrong one multiplies the latent by 1.398 or 0.715
d=1.0   start sigma  14.615  of a possible 14.615
d=0.25  start sigma   0.231  of a possible 14.615
```

## Sources

- [madebyollin/sdxl-vae-fp16-fix, Hugging Face](https://huggingface.co/madebyollin/sdxl-vae-fp16-fix)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/latent_formats.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/latent_formats.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_preview_any.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_preview_any.py)
