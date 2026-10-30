# CU-213 - Inpainting masks and edge blending

**Objective.** Write the blend ComfyUI applies through a mask, predict what resolution and shape a mask has by the time the sampler uses it, and choose grow and feather settings that hide a seam. Taught by Captain Graph.

## The idea

A mask gives each pixel a number between 0 and 1: how much of the new content to take. ComfyUI blends twice when it inpaints. Inside the sampler the blend happens at every step, in latent space, with a mask eight times coarser than the picture. After decoding, a compositing node can blend again in pixel space. Seams come from the mask's shape, its resolution, and how far apart the two images are.

## The maths

The blend is a convex combination, with weights that sum to 1:

```
out = m · new + (1 − m) · old        0 ≤ m ≤ 1
```

Two neighbouring pixels of the output differ by the difference between new and old, times the difference between their mask values. A hard mask puts the whole difference into one step. A ramp that is w pixels wide divides it by w, at the price of w pixels where both images show through.

Inside the sampler the same blend is applied to the model's prediction at every step. With m = 1 where content is generated and 0 where the original is kept, L the original latent, n a noise tensor and σ the current noise level, `KSamplerX0Inpaint` in `comfy/samplers.py` does:

```
x_in = m · x + (1 − m) · (L + σ n)          the kept part is the original plus noise at the current level
out  = m · D(x_in, σ) + (1 − m) · L         the kept part is replaced by the original again
```

D is the model's denoised prediction. With a sampler whose last step goes to σ = 0, like Euler, the last step lands on `out`, so the final latent is m · D + (1 − m) · L: the original where m = 0. The noise n is one tensor for the whole run. It is the sampling noise, or for the sampler named `ddim` a second tensor seeded with the seed plus one.

RePaint (Lugmayr et al. 2022) has the same shape. At each reverse step it takes the known pixels from the forward process of the known image, N(√ᾱ_t x0, (1 − ᾱ_t) I), the unknown pixels from the model, and combines them with the mask (its eq. 8). ComfyUI's code does not cite it, so we only say the mechanism is of the same kind. The code differs in two visible ways: it reuses one noise tensor instead of drawing fresh noise at every step, and it makes a single pass, whereas RePaint's added contribution is resampling, which diffuses a result back and denoises it again to harmonize it.

## In ComfyUI

In every node below, a mask value of 1 means new content.

**Reaching the sampler.** `common_ksampler` in `nodes.py` takes `noise_mask` from the latent dictionary. `reshape_mask` in `comfy/utils.py`, called by `prepare_mask`, resizes it to the latent grid with `interpolate(mode="bilinear")`. That call does no antialiasing, so with a factor of 8 each latent cell reads two pixels per axis, the 4th and 5th of its 8, and nothing else.

**Three ways to attach a mask.** `SetLatentNoiseMask` stores the mask as given, soft values included. `VAEEncodeForInpaint` rounds the mask, grows it by `grow_mask_by` (default 6), paints the masked pixels mid-gray (0.5) before encoding, and returns the rounded grown mask, so any feathering you drew is discarded. Its source comment says the growing is "to keep things seamless in latent space". `InpaintModelConditioning` keeps the resized mask unrounded as the latent's `noise_mask` when its `noise_mask` option is on, and also writes `concat_latent_image` and `concat_mask` into the conditioning. Only models that take the masked image and the mask as extra input channels use them (`concat_cond` in `comfy/model_base.py`). The option's tooltip says it "Might improve results or completely break things depending on the model".

**Shaping a mask.** `GrowMask` in `comfy_extras/nodes_mask.py` runs `expand` rounds of a 3 × 3 maximum filter, without the corners when `tapered_corners` is on, and a negative `expand` erodes. It is a maximum, not a blur. `FeatherMask` multiplies the columns and rows next to the four borders of the mask image by a linear ramp that starts at 1/n. It does not soften the edge of a shape inside the image. For that, the core route is `ImageBlur`, which blurs images, so a mask goes through `MaskToImage` and `ImageToMask`. In `ImageBlur` the kernel grid runs from -1 to 1, so `sigma` is measured in half-widths of the kernel and the blur grows with `blur_radius` at a fixed sigma. `ImagePadForOutpaint` builds its own mask with a quadratic ramp, ((feathering − d) / feathering)², inside the original image next to each padded edge.

**Compositing after decoding.** `ImageCompositeMasked` computes `mask · source + (1 − mask) · destination` on the stored pixel values. `LatentCompositeMasked` does the same on latents, with x and y in steps of 8. The decoded image will not equal the original outside the mask, because the VAE is lossy (CU-201). Compositing the decoded result over the original with a feathered mask restores the original pixels there. The values are blended as stored, so the blend is not done in linear light (CU-229).

## Lab

The functions in the lab follow the ComfyUI code named in their docstrings, applied to small tensors. First the two ramps ComfyUI builds:

```text
FeatherMask, left=8, all-ones mask, first 10 columns:  0.125 0.250 0.375 0.500 0.625 0.750 0.875 1.000 1.000 1.000
ImagePadForOutpaint, feathering=8, rows from the padded edge:  1.000 0.766 0.562 0.391 0.250 0.141 0.062 0.016 0.000 0.000
```

The seam. A flat 0.8 image is composited onto a flat 0.2 image, 64 pixels wide, through a mask that is 1 on columns 16 to 47:

```text
mask                                          largest step in the output   pixels with mask strictly between 0.1 and 0.9 (both seams)
hard edge                                     0.600                        0
patch feathered with left=8 right=8           0.075                        14
ImageBlur radius 8 sigma 1.0                  0.042                        24
ImageBlur radius 8 sigma 0.3                  0.100                        12
ImageBlur radius 16 sigma 0.3                 0.050                        24
```

A hard edge puts all 0.6 into one step. The 8-pixel ramp gives 0.075, which is 0.6 divided by 8, and the blurs trade step size against the number of mixed pixels. At a fixed sigma of 0.3, doubling the radius from 8 to 16 doubles the mixed band from 12 to 24 pixels.

Growing a mask, with one masked pixel at column 20:

```text
growing one masked pixel at column 20:  grow_mask_by 4: 19..22   grow_mask_by 5: 18..22   grow_mask_by 6: 18..23   grow_mask_by 7: 17..23
GrowMask expand 3 on the same pixel: columns 17..23, pixels set 25 with tapered corners, 49 without
```

With an even `grow_mask_by`, the box is off-centre. The default 6 reaches 2 pixels to the low side and 3 to the high side.

What the sampler sees. A hard pixel mask that is 1 from column e on, shown as its 8 latent cells:

```text
latent mask (8 cells of 8 pixels) for a hard pixel mask that is 1 from column e on
  e = 24 0.00 0.00 0.00 1.00 1.00 1.00 1.00 1.00
  e = 21 0.00 0.00 0.00 1.00 1.00 1.00 1.00 1.00
  e = 20 0.00 0.00 0.50 1.00 1.00 1.00 1.00 1.00
  e = 28 0.00 0.00 0.00 0.50 1.00 1.00 1.00 1.00
```

An edge at column 21 behaves like an edge at 24, and an edge at 28 becomes a half-strength cell. The edge of a mask is only resolved to about the size of a cell. Thin features fare worse. A stripe 3 pixels wide, at each of the 8 offsets inside a cell:

```text
a stripe 3 pixels wide, starting at offset s inside one latent cell: largest latent mask value
  s =              0    1    2    3    4    5    6    7
  stripe as drawn  0.00 0.50 1.00 1.00 0.50 0.00 0.00 0.00
  after grow_mask_by 6 1.00 1.00 1.00 1.00 1.00 1.00 0.50 1.00
```

At 4 of the 8 offsets the stripe is invisible to the sampler, because it misses the pixels the interpolation reads. After the growth in `VAEEncodeForInpaint` it is never invisible, and at the worst offset it is a half-strength cell.

Last, the sampler's bookkeeping, with a fixed random network standing in for the model, because the point is the arithmetic and not the picture. The mask is 0, then 0.5, then 1 over three parts of a 32-value latent:

```text
sampler bookkeeping, 12 Euler steps, stand-in model, mask 0 / 0.5 / 1
  mask 0:   largest |final - original latent|                          0.0e+00
  mask 1:   largest |final - last model output|                        0.0e+00
  mask 0.5: largest |final - (0.5 last model output + 0.5 original)|   0.0e+00
```

Where the mask is 0 the result is the original, whatever the model does. Where it is 0.5 the result is half model and half original in latent space, so a soft latent mask acts as a strength per latent cell.

## What is contested

The lab uses a stand-in model, so it says nothing about how good the generated content looks or whether the seam is visible in a real image. That depends on the model, the content and the prompt. Whether a feathered mask or a grown one hides a seam better is an empirical question for each image. The ramp widths in the table are arithmetic on flat images and say nothing about textures, where a wide ramp also shows a ghost of the old content. Nor do we claim that the sampler-side blend is better than pasting a separately generated patch. RePaint's authors argue that conditioning on the known region matters, and we have not tested it here.

## Sources

- [Lugmayr et al. 2022. RePaint: Inpainting using Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2201.09865)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/sampler_helpers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sampler_helpers.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_mask.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_mask.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_post_processing.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_post_processing.py)
