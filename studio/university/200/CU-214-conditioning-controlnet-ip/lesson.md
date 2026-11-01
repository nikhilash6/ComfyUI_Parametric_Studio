# CU-214 - Conditioning: img2img, inpaint, ControlNet, IP-Adapter

**Objective.** Place each way of steering a diffusion model, img2img, inpainting, ControlNet and an image prompt, at the point where it enters the computation, and read the numbers that set its strength. Taught by Captain Graph.

## The idea

A text prompt is one input. Every other control enters somewhere else, and where it enters decides what it can change.

| control | what is added | where it enters | the knob |
|---|---|---|---|
| img2img | an encoded image, plus noise | the starting latent | `denoise` |
| inpainting | a mask | the sampler's per-step replacement (CU-213) | the mask |
| ControlNet | residuals computed from a hint image | the U-Net's skip connections and middle block | `strength`, `start_percent`, `end_percent` |
| IP-Adapter | image tokens | extra cross-attention beside the text's | λ |

Here's the img2img entry and the ControlNet entry as graphs you can open.

{{graph:sd15_img2img}}

{{graph:sd15_controlnet}}

CU-270 goes further into the window. Try it here first: this lab counts the steps a window covers.

{{play:range}}

## The maths

**img2img.** The sampler starts from x = L + σ0 n, where L is the encoded image, n is noise, and σ0 is a noise level read off the schedule (the convention of CU-202). If L has unit variance, the correlation between the start and the clean latent is 1/√(1 + σ0²). So `denoise` is not a fraction of the noise. It chooses σ0.

**ControlNet.** Zhang and Agrawala (2023) lock a block F with parameters Θ and clone it into a trainable copy with parameters Θc. They connect the copy through "zero convolutions" Z, 1 × 1 convolutions whose weight and bias start at zero (their eq. 2):

```
y_c = F(x; Θ) + Z( F( x + Z(c; Θz1); Θc ); Θz2 )
```

At the first training step both Z terms are zero, so y_c = y and the locked model's behaviour is untouched. The gradient shows why training can still start. With L the loss, the gradient for the output convolution Z2 is (∂L/∂y_c) times the copy's output, which is not zero. The gradient that reaches the copy and Z1 must pass through the weights of Z2, which are zero. After one step Z2 is no longer zero and everything else starts to learn. The paper's main text says zero convolutions protect the backbone by "eliminating random noise as gradients in the initial training steps", and puts the gradient calculation in a supplement that we did not read. The argument above is ours, and the lab checks it.

**IP-Adapter.** Ye et al. (2023) add, beside each text cross-attention, a second one with its own key and value projections W′k and W′v applied to the image features c_i, and sum the two with a weight λ (their eq. 8):

```
Z_new = Attention(Q, K, V) + λ · Attention(Q, K′, V′)      K′ = c_i W′k     V′ = c_i W′v
```

The query Q is shared. With λ = 0 it is the original model. The paper reports that simply concatenating the image features with the text features and feeding them to the same cross-attention was "insufficiently effective" in their setting.

## In ComfyUI

**img2img** is `VAEEncode` into a `KSampler` with `denoise` below 1. `KSampler.set_steps` in `comfy/samplers.py` builds a schedule for `int(steps / denoise)` steps and keeps its last `steps + 1` values, so the sampler still runs `steps` steps, all in the low-noise tail.

**Inpainting** is its own lesson, CU-213. The per-step replacement is in the sampler, and the mask nodes are in `nodes.py` and `comfy_extras/nodes_mask.py`.

**ControlNet.** `ControlNetApplyAdvanced` in `nodes.py` takes `strength` (default 1.0), `start_percent` (0.0) and `end_percent` (1.0), and stores the ControlNet in each conditioning entry under `control`. Chained nodes keep a link to the previous one. `pre_run_control` in `comfy/samplers.py` turns the percents into noise levels with `percent_to_sigma` in `comfy/model_sampling.py`. For SD 1.x that is the noise level at timestep (1 − percent) · 999, and the ControlNet is skipped for steps outside the window. The model itself is `ControlNet` in `comfy/cldm/cldm.py`. `input_hint_block` turns the hint image into features that are added after the first input block. Each input block's output then goes through a 1 × 1 convolution called `zero_conv`, and the middle block through `middle_block_out`. ComfyUI only runs these, so their weights are whatever the file holds. `control_merge` in `comfy/controlnet.py` multiplies the residuals by `strength` (by default) and adds the residuals of any earlier ControlNet. The U-Net then adds them with `apply_control` in `comfy/ldm/modules/diffusionmodules/openaimodel.py`, to the middle block's output and to each skip connection before it is joined to the decoder.

**IP-Adapter** is not in core. A case-insensitive search of `comfy/`, `comfy_extras/`, `comfy_api/` and `nodes.py` in v0.43.0 finds no mention of it, so in ComfyUI it comes from custom nodes. Core does have two other ways to use an image as a prompt. `StyleModelApply` appends the style model's tokens after the text tokens. It has two strength types: `multiply` scales those tokens, and `attn_bias` adds log(strength) to their attention logits, with a code comment that log(0) is -inf, "which is what we want". `unCLIPConditioning` stores a CLIP vision output in the conditioning with a strength and a noise augmentation.

## Lab

The lab rebuilds the SD 1.x noise levels the way `comfy/model_sampling.py` does, then applies the same slicing as `set_steps`. For img2img it compares the formula with a measured correlation over a million samples:

```text
img2img, 20 steps, normal scheduler, SD 1.x noise levels
denoise  steps run   first sigma   signal share 1/sqrt(1+sigma^2)   measured correlation with the clean latent
0.2      20         0.552         0.875                            0.875
0.5      20         1.548         0.543                            0.542
0.8      20         4.904         0.200                            0.199
denoise 1.0 starts from sigma_max = 14.615
```

A denoise of 0.5 starts at a noise level of 1.548 and keeps a correlation of about 0.54 with the clean latent. At 0.8 the start keeps a correlation of only 0.2. The ControlNet window is set in the same units:

```text
ControlNet start_percent 0: steps (of 20) that run with the ControlNet on
end_percent   sigma where it stops   normal scheduler   karras scheduler
0.25          4.086                  5                  6
0.5           1.616                  10                 9
0.75          0.695                  15                 12
```

An end percent of 0.5 is half of the timestep range, which is 10 of 20 steps on the normal scheduler and 9 on Karras. At 0.75 the two schedulers differ by three steps. Now the zero convolution, with a locked block, a trainable copy and zero-initialised Z1 and Z2. At step 0 the output equals the locked block's exactly and only Z2 gets a gradient. After one update of Z2 the copy and Z1 receive gradients too:

```text
zero convolution            max |y_c - y|   grad of Z2   grad of trainable copy   grad of Z1
step 0                      0.0e+00         0.1596       0.0000                  0.0000
after one step on Z2        1.3e-02         0.1567       0.0019                  0.0004
```

Last, one attention layer with random weights and three ways to add four image tokens to eight text tokens. The test is what happens when the image strength is zero, and whether doubling the strength doubles the image's effect:

```text
image strength 0 against a layer with no image at all, largest difference, and a linearity test of the image's effect
design                                      strength 0 vs no image   relative error of (f(2) - f(0)) against 2 (f(1) - f(0))
decoupled cross-attention                   0.0e+00                  0.000
appended tokens, multiply                   3.4e-01                  1.596
appended tokens, attn_bias                  2.4e-07                  0.489
```

In the decoupled form λ is a clean dial: zero removes the image and the effect is linear. Appended tokens multiplied by zero are still tokens, and they take attention weight, so strength 0 does not remove the image (difference 0.34). The `attn_bias` type fixes that, because log(0) is -inf, but the effect is not linear in the strength. A zero token is not an absent one.

## What goes wrong

- **`denoise` near 1 and the picture is forgotten.** At 0.8 only a correlation of 0.2 is left. Lower it to keep more of your picture.
- **A ControlNet does nothing on img2img.** The window is on the model's scale, and low denoise can slide all your steps out of it. CU-270 shows it with numbers.
- **A hint that doesn't match the ControlNet.** A depth map through a Canny model runs without complaint, because both are plain images. Check the pair.
- **Looking for IP-Adapter in core.** It isn't there. `StyleModelApply` and `unCLIPConditioning` are core's image-prompt routes, and they need their own model types.
- **Strength 0 on `StyleModelApply` in multiply mode.** The tokens stay, so it isn't the same as no image. The lab's last table shows it. Bypass the node instead.

## What is contested

This lab shows structure with random weights, not quality. It does not say that decoupled attention gives better pictures than appended tokens. The paper reports that for its adapter on Stable Diffusion 1.5 concatenation was less effective, and `StyleModelApply` serves different models, so we make no comparison. The zero-convolution argument is about the first training steps. It does not explain everything about why ControlNet trains well. And the percent windows say where a ControlNet is active, not how much it helps: that depends on the control type and the image.

## Sources

- [Zhang, Rao, Agrawala 2023. Adding Conditional Control to Text-to-Image Diffusion Models](https://arxiv.org/abs/2302.05543)
- [Ye, Zhang, Liu, Han, Yang 2023. IP-Adapter: Text Compatible Image Prompt Adapter for Text-to-Image Diffusion Models](https://arxiv.org/abs/2308.06721)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy/controlnet.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/controlnet.py)
- [ComfyUI v0.43.0, comfy/cldm/cldm.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cldm/cldm.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/openaimodel.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/openaimodel.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
