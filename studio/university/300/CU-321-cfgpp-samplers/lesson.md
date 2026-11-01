# CU-321 - CFG++ samplers, and why cfg is near 1 there

**Objective.** Say the one thing a CFG++ sampler changes, why its cfg sits near 1, and what that costs. Taught by Dr. Denoise.

## The idea

An ordinary sampler step does two things with its prediction. It estimates the clean picture, then adds some noise back to move to the next noise level. With plain cfg, both of those use the guided prediction.

CFG++ separates them. The clean estimate uses the guided prediction, and the noise added back comes from the unconditional prediction. That's the whole change. The paper calls it a simple fix.

```
plain Euler   x_next = D_cfg + σ_next · (x − D_cfg) / σ
euler_cfg_pp  x_next = D_cfg + σ_next · (x − D_uncond) / σ
```

Those two lines are written for SD-style models and are the same except for one symbol. Plain Euler is usually written `x + (x − D) / σ · (σ_next − σ)`, which is the same sum rearranged. The lab checks this.

## Why cfg is near 1

Chung et al. give their strength as λ, from 0 to 1, where 0 is unconditional and 1 is conditional. In the sum it sits where cfg does:

```
D = D_uncond + (D_cond − D_uncond) · λ
```

ComfyUI passes the same `cfg` value in, so on these samplers `cfg` is λ. The paper has no formula linking the two scales. It matched them by how alike the pictures looked, at 50 steps:

| λ on CFG++ | Similar plain cfg |
|---|---|
| 0.2 | 2.0 |
| 0.4 | 5.0 |
| 0.6 | 7.5 |
| 0.8 | 9.0 |
| 1.0 | 12.5 |

So cfg 1 on a CFG++ sampler is not weak guidance, and cfg 7 is far beyond the paper's range. This is why our stored render uses cfg 1, and its note says 7 is not the comparable value.

{{wipe:sampling_lab/guidance-cfg-7.jpg|sampling_lab/guidance-cfgpp-1.jpg|euler, CFG 7|euler_cfg_pp, CFG 1|One seed on SDXL with the same 20 steps. A different arrangement of the same kinds of objects, at a similar contrast.}}

The stored figures: brightness 90.6, contrast 60.4, edge 14.98, against 81.5, 62.0 and 13.92 for euler at cfg 7. The difference between the two is 22.15. That's one seed, so read it as "not broken", not as "better".

## What it costs

Look at this line in the sampler:

```python
extra_args["model_options"] = comfy.model_patcher.set_model_options_post_cfg_function(model_options, post_cfg_function, disable_cfg1_optimization=True)
```

An ordinary sampler at cfg 1 runs one prediction. This flag keeps the second prediction running, because the sampler needs the unconditional for its noise. So cfg 1 here costs two per step, the same as plain cfg 7. Also, your negative prompt really does matter at cfg 1 on these samplers, unlike CU-209's usual case.

The core list includes `euler_cfg_pp`, `euler_ancestral_cfg_pp`, `dpmpp_2m_cfg_pp`, `dpmpp_2s_ancestral_cfg_pp`, `res_multistep_cfg_pp`, `res_multistep_ancestral_cfg_pp` and `gradient_estimation_cfg_pp`. You choose them in the normal sampler menu, so the graph is an ordinary one with one changed word and one changed number.

{{graph:c_cfgpp}}

## Try it

{{play:cfgpp}}

## What goes wrong

- **cfg 7 on a CFG++ sampler.** A burnt picture, far past the paper's range. Carry over the sampler or the cfg, not both. Start near 1 or below.
- **Expecting cfg 1 to be fast.** It isn't. Two predictions per step, as the flag above shows.
- **A negative that "shouldn't matter" does.** At cfg 1 on CFG++, it sets the noise. Choose it deliberately, or zero it out.
- **A distilled model.** A cfg 1 model trained not to need a second prediction has no meaningful unconditional. We haven't tested the combination. Be wary of it.
- **Comparing against plain cfg at the same number.** The scales differ. Compare by looking, using the table above as a starting point.

## Lab

Two blobs with exact predictions, 20 steps, the same starts each time. The prompt asks for the blob at 1.5.

```text
the prompt asks for the blob at 1.5, with width .5
cfg     euler mean   euler width   euler_cfg_pp mean   euler_cfg_pp width
0.2     0.58         1.09          1.31                0.60
0.4     0.90         0.90          1.69                0.35
0.6     1.15         0.71          1.88                0.29
0.8     1.33         0.56          2.03                0.26
1.0     1.45         0.46          2.15                0.24
1.5     1.64         0.35          2.38                0.20
2.0     1.78         0.31          2.57                0.19
5.0     2.23         0.21          3.31                0.14
7.0     2.43         0.19          3.64                0.13
12.5    2.82         0.16          4.31                0.10
```

At the same number, CFG++ always pushes harder on this toy. It reaches the target somewhere between 0.2 and 0.4, while plain Euler needs about 1. At cfg 7 it lands much further out than Euler does.

```text
same cfg number, different strength: which plain cfg lands closest to each CFG++ setting on this toy
cfg_pp 0.2   is nearest plain cfg 1.0
cfg_pp 0.4   is nearest plain cfg 1.5
cfg_pp 0.6   is nearest plain cfg 3.0
cfg_pp 0.8   is nearest plain cfg 3.0
cfg_pp 1.0   is nearest plain cfg 4.0
```

The direction matches the paper's table, but not the numbers. Its numbers came from real pictures, and these from two blobs.

```text
one step at cfg 1: same clean estimate, plain re-noises to 0.8816, CFG++ to 1.3574
```

That's the swap, on one number.

## Sources

- [Chung et al. 2024. CFG++: Manifold-constrained Classifier Free Guidance for Diffusion Models](https://arxiv.org/abs/2406.08070)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/model_patcher.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_patcher.py)
