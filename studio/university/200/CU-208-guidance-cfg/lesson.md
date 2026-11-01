# CU-208 - Guidance: CFG and what it really does

**Objective.** State the CFG formula as ComfyUI computes it, explain why it costs two predictions per step, and show numerically that it does not sample the distribution people usually say it does. Taught by Dr. Denoise.

## The idea

Run the model twice, with and without the prompt. The difference points towards the prompt. Exaggerate that difference.

That is the whole method. It is one line of code, and it is why almost every image graph has a number called cfg. Try the sum yourself before reading how it fails. The blobs below stand for kinds of picture, and the dots are samples from a real solver.

{{play:cfg}}

## The maths

ComfyUI computes it on denoised predictions, in `cfg_function`:

```
D_cfg = D_uncond + (D_cond − D_uncond) · cfg
```

Read it at three settings. At cfg 0 you get only the unconditional prediction. At cfg 1 the two uncond terms cancel and you get only the conditional one. Above 1 you go past the conditional, in the direction away from the unconditional. Nothing in the formula keeps the result inside the range real pictures have.

Ho and Salimans (2022) write the same thing as ε̃ = (1+w) ε_c − w ε_u, so their w equals cfg − 1, and w = 0 means no guidance. Keep that in mind when you read papers: cfg 7.5 is their w = 6.5.

Why people call this sampling a sharper distribution: by Bayes' rule, ∇log p(x|c) = ∇log p(x) + ∇log p(c|x). Scale the second term by cfg, and the score looks like that of a tilted density:

```
p_cfg(x) ∝ p(x) · p(c|x)^cfg
```

This motivation is fine, but the conclusion does not follow. At noise level σ, the guided field is not the score of the noised version of that tilted density, and it may not be the score of anything. Ho and Salimans say so: "there in general may not exist a classifier for which Eq. (6) is the classifier-guided score." Bradley and Nakkiran (2024) state that neither DDPM nor DDIM with CFG generates this tilted distribution. Chidambaram et al. (2024) analyse simple mixtures, and prove that large guidance moves samples to the boundary of the support, and beyond it once the score has any error.

## In ComfyUI

`sampling_function` in `comfy/samplers.py` runs the conditional and unconditional model, then calls `cfg_function`. When cfg is 1 it drops the unconditional run completely. So cfg above 1 costs two predictions per step, and cfg 1 costs one. Models distilled for cfg 1, such as turbo variants, depend on this (CU-209).

The two predictions are not always two trips through the model. `_calc_cond_batch` puts them in one batch when it estimates that memory allows, and splits them when it does not. So cfg above 1 is twice the work, and on a tight card it can also be twice the trips.

The formula has three places where other nodes can step in, and most of the rest of this track lives in them.

- `sampler_pre_cfg_function` sees both predictions before the sum. APG and TCFG sit here.
- `sampler_cfg_function` replaces the sum. RescaleCFG sits here.
- `sampler_post_cfg_function` sees the result. CFG-Zero-Star, PAG and SAG sit here, and so does CFGNorm by default. With its `pre_cfg` input on, CFGNorm uses `sampler_cfg_function` instead.

Here is the graph to change it in. The number is the `cfg` input on `KSampler`.

{{graph:sd15_txt2img}}

And here is the same prompt and seed at cfg 7 and cfg 14, on SDXL with 20 Euler steps. CU-250 measures what changed.

{{wipe:sampling_lab/guidance-cfg-7.jpg|sampling_lab/guidance-cfg-14.jpg|CFG 7|CFG 14|One prompt, one seed. Higher cfg changed the layout as well as the contrast.}}

## What goes wrong

- **Burnt, over-contrasty pictures.** The cfg is too high for this model. Lower it first. If you need the extra push, CU-320 covers the fixes.
- **A grey or vague picture.** The cfg may be too low, or below 1. At cfg 0 the prompt plays no part at all.
- **Twice as slow as you expected.** You are above cfg 1. A distilled model set to cfg 1 skips the second prediction.
- **A setting copied from another model looks awful.** cfg numbers do not travel. Our SD 3.5 renders use 4.5, the SDXL baseline uses 7, and FLUX.1 schnell runs at 1. See CU-251.
- **A paper's number looks wrong.** Check whether it uses w. Add 1 to get ComfyUI's cfg when the paper writes (1+w).

## Lab

Two classes, known densities, a 200-step Heun solve from the same noise for each value of cfg (written w in the table). The last two columns are the mean and standard deviation of the tilted density above, computed on a grid:

```text
w      sample mean  sample std   tilted mean  tilted std
1.0    1.4871       0.5029       1.5000       0.5000
3.0    2.0074       0.3134       1.5173       0.4814
7.5    2.5536       0.2477       1.5292       0.4710
12.0   2.9146       0.2263       1.5359       0.4657
```

At cfg 1 sampling is correct. Above that the samples leave the tilted density behind: at 7.5 the mean is one full unit past it, and the spread is half. So guidance both shifts and narrows.

```text
w      largest |predicted x0| along the path   true data range is about +-3
1.0    2.95
7.5    11.84
30.0   41.32
```

The predicted clean sample leaves the data range long before the end. This is the mechanism behind burnt, saturated images at high CFG, and the reason for clipping and rescaling methods (CU-320).

## What is contested

Why does CFG give good images, given that it is not sampling its nominal target? There is no settled answer. Bradley and Nakkiran's predictor-corrector account and the Chidambaram et al. analysis are recent attempts. The cfg values in common use, such as the w = 7.5 in Lin et al. (2023), are found by looking at results.

## Sources

- [Ho, Salimans 2022. Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598)
- [Dhariwal, Nichol 2021. Diffusion Models Beat GANs on Image Synthesis](https://arxiv.org/abs/2105.05233)
- [Bradley, Nakkiran 2024. Classifier-Free Guidance is a Predictor-Corrector](https://arxiv.org/abs/2408.09000)
- [Chidambaram et al. 2024. What does guidance do? A fine-grained analysis in a simple setting](https://arxiv.org/abs/2409.13074)
- [Lin, Liu, Li, Yang 2023. Common Diffusion Noise Schedules and Sample Steps are Flawed](https://arxiv.org/abs/2305.08891)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/model_patcher.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_patcher.py)
