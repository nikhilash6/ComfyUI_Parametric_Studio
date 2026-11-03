# CU-273 - Choosing an inpaint route

**Objective.** Pick the right core inpaint route for your model and denoise, from what each node does to your picture and your mask. Taught by Captain Graph.

## The idea

Core has three ways of telling the sampler about a mask. All three end with the same blend at every step (CU-213). They differ in what's in the hole when sampling starts, what they do to a soft mask, and what extra they feed a model made for inpainting.

| | `SetLatentNoiseMask` | `VAEEncodeForInpaint` | `InpaintModelConditioning` |
|---|---|---|---|
| in the latent | what you gave it | your picture with the hole painted mid-grey | your picture, unchanged |
| the mask | kept as is, soft | rounded, then grown | kept soft, if `noise_mask` is on |
| extra | none | none | greyed picture and mask, in the conditioning |
| natural partner | any model, lower denoise | inpainting model, denoise 1 | inpainting model, any denoise |

## The three graphs

**`SetLatentNoiseMask`** only attaches a mask to a latent you've already made. So the hole begins as the original content, plus noise. It's a masked img2img.

{{graph:sd15_inpaint}}

**`VAEEncodeForInpaint`** rounds the mask, paints the rounded hole mid-grey, and encodes. A copy of the rounded mask, grown by `grow_mask_by`, becomes the noise mask. So the sampler's area reaches past the grey by a few pixels. The hole's original content is gone, so the model must invent everything.

{{graph:sd15_inpaint_vae}}

**`InpaintModelConditioning`** encodes twice. The latent you sample holds the original, and a greyed copy plus the mask go into both conditionings as `concat_latent_image` and `concat_mask`.

{{graph:d_inpaint_cond}}

## What happens to a soft mask

```text
one row of a soft mask, as drawn:               0.0 0.0 0.2 0.4 0.6 0.8 1.0 1.0
SetLatentNoiseMask keeps it:                    0.0 0.0 0.2 0.4 0.6 0.8 1.0 1.0
VAEEncodeForInpaint rounds and grows it (6):    0.0 0.0 1.0 1.0 1.0 1.0 1.0 1.0
InpaintModelConditioning, noise_mask:           0.0 0.0 0.2 0.4 0.6 0.8 1.0 1.0
InpaintModelConditioning, its grey-out, rounded: 0.0 0.0 0.0 0.0 1.0 1.0 1.0 1.0
```

Your feathering survives `SetLatentNoiseMask`. In `VAEEncodeForInpaint` it's gone, and the mask reaches further. So a feathered mask only feathers on the first and third route, and even there, the latent grid decides what the sampler gets (CU-213).

## What's in the hole when sampling starts

This decides how far denoise can go. For the next table, take a stand-in model that knows nothing of your picture: the exact denoiser for random content with spread 1. Anything of the original in the result must have come through the starting latent, and a mid-grey hole is 0 here.

```text
the masked part, 20 Euler steps, normal scheduler, stand-in denoiser. Correct content here has spread 1.00
denoise   first sigma   original kept in the latent: correlation, spread     greyed first (VAEEncodeForInpaint): correlation, spread
1.0       14.615        0.069        0.930                                    0.001        0.928
0.8       4.904         0.201        0.946                                    0.001        0.926
0.5       1.548         0.544        0.972                                    0.001        0.815
0.3       0.810         0.778        0.987                                    0.001        0.620
```

Read the two columns of the routes that keep your picture. Low denoise keeps content, with correlation 0.778 at denoise 0.3, as img2img should. Now the greyed route. Correlation is zero at every denoise, as it must be. And the spread falls: 0.62 at denoise 0.3, when it should be near 1. The stand-in added too little, because there wasn't enough noise to start from. In a real picture we'd expect that to look like a flat grey patch at low denoise, though we didn't render it. Use denoise 1 with it. (Even the best row misses 1.0, by about 7%, because 20 Euler steps are not exact.)

Whichever route you use, the part you kept returns exactly:

```text
sampler blend, 12 Euler steps: largest change outside the mask
SetLatentNoiseMask    denoise 1.0   0.0e+00
SetLatentNoiseMask    denoise 0.5   0.0e+00
VAEEncodeForInpaint   denoise 1.0   0.0e+00
VAEEncodeForInpaint   denoise 0.5   0.0e+00
```

Keep in mind that's the latent. The VAE decode doesn't return your pixels exactly (CU-213 covers pasting back).

## What an inpainting checkpoint sees

Ordinary checkpoints only see the noisy latent. A checkpoint whose U-Net takes more than 4 channels gets `set_inpaint`, which sets `concat_keys` to `mask` and `masked_image`. The SD 1.5 inpainting file has 9 input channels. `concat_cond` in `comfy/model_base.py` fills them like this:

```text
an inpainting checkpoint takes 4 + 1 + 4 = 9 channels. Where the last 5 come from
route                     mask channel           masked_image channels
SetLatentNoiseMask        noise_mask, rounded    the latent, not blanked
VAEEncodeForInpaint       noise_mask, rounded    the latent, greyed first
InpaintModelConditioning  concat_mask, rounded   concat_latent_image, greyed first
```

Look at the first row. With `SetLatentNoiseMask`, the masked_image channels get the latent as it is, so an inpainting model is told "here's the picture", with the hole's content still there. A source comment says that channel should be masked in pixel space. That's why this pairing is not the natural one. An ordinary checkpoint has no `concat_keys`, so it ignores these values. `InpaintModelConditioning` adds nothing for it, beyond the soft noise mask.

## So which?

- **An ordinary checkpoint, changing what's there** (a new colour, a fix): `SetLatentNoiseMask`, with denoise below 1. The content guides the result.
- **An inpainting checkpoint, replacing what's there, at denoise 1**: `VAEEncodeForInpaint` is the simple route.
- **An inpainting checkpoint, at lower denoise or with a soft mask**: `InpaintModelConditioning`. The original guides the sampler and the model still gets its extra channels.
- **Another model family**: read its notes. The `noise_mask` tooltip itself warns it "might improve results or completely break things depending on the model".

These follow from what each route feeds the model. We did not compare pictures for this lesson. Try the denoise row by row for yourself, here:

{{play:denoise}}

### Removal with no mask at all

One more route sits outside core. LTX-2.5's clean-plate IC-LoRA, in the studio's VFX graph, removes people from a moving shot with no mask drawn: its prompt asks for the same place with no one in it, and the LoRA is made for that edit.

{{video:showcase/vfx_same_plate.mp4|Clean plate on the red coat clip from CU-214: the woman is gone, and the street, the shutters and the plants stay. Recorded: 28.7 s, peak 38.5 GiB. One seed.|showcase/vfx_same_plate.webp}}

{{video:showcase/vfx_clean_plate.mp4|Clean plate on another clip, asked to paint a violinist out of a moving shot: an empty stone bridge at dusk with its lamps lit. Only the result is shown here. 97 frames at 960 x 544, with sound. Recorded: 49.0 s, peak 44.8 GiB. One seed.|showcase/vfx_clean_plate.webp}}

## What goes wrong

No real model ran on core's three routes for this lesson, so the looks below come from the arithmetic and the source, not from pictures.

- **A flat grey patch in the hole.** You used `VAEEncodeForInpaint` below denoise 1. Set denoise to 1, or switch route.
- **A hard seam despite a feathered mask.** The route rounded it. Use a soft route, or composite after decoding (CU-213).
- **The hole keeps looking like what was there.** You used `SetLatentNoiseMask` at low denoise. Raise denoise.
- **`InpaintModelConditioning` looks no different on an ordinary checkpoint.** It has no extra channels to read, so those values go unused.
- **The result is messy on an ordinary checkpoint at denoise 1.** Nothing tells it what's around the hole beyond the blend at each step. Try an inpainting checkpoint.
- **Black or broken output with an unusual model.** Turn `noise_mask` off, as the tooltip warns. We have not tested this ourselves.

## Lab

The VAE here is an identity, so that each number can be followed: a real one would not leave pixels unchanged. In a side script the lab's `VAEEncodeForInpaint` gave the same mask and pixels as the real node with a pass-through VAE. The tables are above. The stand-in model is exact for random Gaussian content, and it knows nothing of pictures, so the lab shows arithmetic and not quality.

## Sources

- [Lugmayr et al. 2022. RePaint: Inpainting using Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2201.09865)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
- [ComfyUI v0.43.0, comfy/model_detection.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_detection.py)
- [ComfyUI v0.43.0, comfy/sampler_helpers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sampler_helpers.py)
