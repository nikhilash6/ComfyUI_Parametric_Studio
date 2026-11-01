# CU-241 - Latent operations, and why multiplying changes the picture

**Objective.** Predict what multiplying a latent does at each point in a run, and use the other latent nodes without surprises. Taught by Professor Latent.

## The idea

A latent is a block of numbers, and `LatentAdd`, `LatentSubtract` and `LatentMultiply` are plain arithmetic on that block. You'd think multiplying by 1.5 is like turning something up. What it does depends completely on when you do it. Before sampling, during sampling and after sampling give three different results, and on an empty latent it does nothing at all.

{{graph:nm_latent_ops}}

This graph runs on a CPU, and it holds a small joke. It multiplies an empty latent. Zero times anything is still zero, so the multiply did nothing, and neither did the upscale. An empty latent has no content yet. The noise is added later, inside the sampler.

## Two scales

The numbers on the wire are not the numbers the model sees. `comfy/latent_formats.py` holds a `scale_factor`. Sampling multiplies by it on the way in, in `process_latent_in`, and divides on the way out. For SD 1.x that's 0.18215, so 5 on the wire is about 0.91 inside. When a sampler returns, its result has been divided again. `LatentMultiply` works on wire numbers, whichever state they are in.

Inside, the model expects numbers with a spread near 1, as CU-201 explains. Multiply by 1.5 and you break that agreement.

## Why multiplying changes the picture

There are three different reasons, one for each moment.

**After sampling.** Nothing can correct it. The numbers go straight to the VAE. The decoder gets values outside what it usually sees. We can compute the effect on the preview map, because that map is a plain matrix. Every preview colour moves away from mid-grey in proportion, so contrast rises, and more values clip. A real decoder is not a plain matrix, so try it yourself and don't assume.

{{graph:b_latent_gain}}

**Near the end of a run.** The latent is nearly clean, and the sampler has few steps left. Most of the change stays. The lab shows almost the same damage here as after sampling.

**At high noise.** The latent is mostly noise, and the model is about to pull it toward something it knows, so much of the change is corrected. Some remains: the toy's spread still ends up too wide.

{{play:latentscale}}

## The other operations

- **`LatentAdd` and `LatentSubtract`.** Plain sums. If the shapes differ, the second is resized with bilinear to match the first, and its batch repeated, with no warning.
- **`LatentInterpolate`.** A plain average of two noises loses spread: 0.708 in the lab, where the model expects 1. This node normalises by the length of each cell across channels, and then restores a mix of the lengths, so it stays near 1. `ratio` 1 gives `samples1`. We found it fails on a batch of 2 with 4 channels. A batch of 4 with 4 channels runs, and by the broadcasting rules it pairs the wrong axes. Use it on single latents.
- **`LatentUpscale`.** It resizes the numbers directly. `nearest-exact` and `area` keep the spread of noise here, `bicubic` loses some, and `bilinear` loses a lot: 0.632. Lost spread means a blurrier latent, which is why a latent upscale usually goes through a second sampling pass.
- **`LatentOperationTonemapReinhard` and `LatentOperationSharpen`.** These are operations you hand to `LatentApplyOperation`, or to `LatentApplyOperationCFG`, which applies them during sampling. The Reinhard one squashes large values, which is one tidy way to tame them.

## What goes wrong

- **Multiplying an `EmptyLatentImage`.** It does nothing. To change the noise itself, use `AddNoise`, or the noise parts in CU-232.
- **A washed or harsh picture after a latent multiply.** Take the node out, then try values close to 1.
- **A multiply between two `KSamplerAdvanced` nodes.** The second sampler is told σ and handed noise of k × σ. CU-233 covers that kind of mismatch.
- **A soft result after bilinear latent upscale.** The spread fell. Send it through a sampler at a denoise below 1 (see the `sd15_hires` graph), or use another method.
- **Blending latents from two different families.** The numbers mean different things, and they may have different channels. The result won't mean anything, even if it runs.
- **`lanczos` from a pack.** The Sampling Lab found core's lanczos clips to 0 to 1 and rounds to 8 bits. `LatentUpscale` leaves it off its menu, for that reason we'd guess. A pack that calls it on a latent could wreck the numbers.

## Lab

The sums here are copied from the nodes.

```text
empty latent times 5, largest value: 0.0  upscaled twice: 128 wide, largest value: 0.0
SD 1.x: a value of 5.0 on the wire is 0.911 inside the sampler, and 1.0 inside is 5.490 on the wire
```

The preview map, using SD 1.5's `latent_rgb_factors`. The preview's spread grows exactly with the multiplier, and clipped values grow faster.

```text
multiplier  preview spread around grey  values clipped
0.5         0.158                       0.003
1.0         0.316                       0.113
1.5         0.474                       0.275
2.0         0.631                       0.412
```

Now the moments. It's a toy with a perfect denoiser, and the same 1.5 is applied at different points in a 20-step run. W1 is the distance from the data, and the plain run scores 0.055. The data's own spread is 1.032.

```text
when                           sigma then   W1 to the data   spread of the result
the starting noise             14.615       0.213            1.217
after step 4                   5.789        0.208            1.215
after step 10                  1.091        0.192            1.221
after step 16                  0.121        0.386            1.440
after step 19                  0.029        0.415            1.469
after the last step            0.000        0.418            1.472
```

The last row is the run's own result multiplied up, so an uncorrected 1.5 × gives 1.47. Early on, about half of the extra spread is corrected: 1.22 against that 1.47. By step 16 it is nearly all kept. Notice the jump between steps 10 and 16: on this toy the point of no return is between σ 1 and σ 0.1.

```text
mixing two noises half and half: plain average spread 0.708; LatentInterpolate spread 0.971; sqrt(1/2) mix 1.001
LatentInterpolate ratio 1 returns samples1: True  ratio 0 returns samples2: True
```

To mix two noises and keep their spread, weight them so the squares add to 1. Half and half becomes √½ each.

```text
nearest-exact  1.003
bilinear       0.632
bicubic        0.859
area           1.003
```

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_latent.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_latent.py)
- [ComfyUI v0.43.0, comfy/latent_formats.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/latent_formats.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, latent_preview.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/latent_preview.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
