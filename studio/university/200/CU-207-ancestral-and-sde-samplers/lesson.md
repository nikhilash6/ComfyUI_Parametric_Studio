# CU-207 - Ancestral and SDE samplers: adding noise back

**Objective.** Compute an ancestral step, explain why these samplers do not settle as steps grow, and say honestly when added noise helps. Taught by Dr. Denoise.

## In plain words

A plain sampler commits at the start. Once the first noise is drawn, the result is decided. An ancestral sampler keeps stirring. At each step it goes a little further than it should, then adds some fresh static to get back to the right noise level. So the end result depends on every step's random numbers. It can produce more variety. It also means that changing the step count gives you a different picture and not a more refined one.

## The idea

An ancestral sampler steps past the target noise level, then adds fresh noise to get back to it. Each step forgets some of the path so far. In ComfyUI's menu these are the names containing `ancestral` or `sde`, and a few others such as `seeds_2`, `sa_solver` and `ddpm`.

## The maths

To go from σ_from to σ_to, `get_ancestral_step` splits the target into two parts:

```
σ_up   = min( σ_to, η · √( σ_to² (σ_from² − σ_to²) / σ_from² ) )
σ_down = √( σ_to² − σ_up² )

x ← x + d · (σ_down − σ_from) + σ_up · z        z ~ N(0, I)
```

The bookkeeping is the point: σ_down² + σ_up² = σ_to², so the sample has exactly the noise level the schedule expects. η = 0 gives back the deterministic step.

## In ComfyUI

`sample_euler_ancestral` does this, and flow models go to `sample_euler_ancestral_RF`, which uses the same idea with different algebra because the interpolant scales the signal too. `dpmpp_sde` and the `dpmpp_2m_sde` family use `BrownianTreeNoiseSampler` in place of independent draws, so the noise between two sigmas depends only on those sigmas, and not on how many steps you took.

The `eta` dial sets how much noise goes back in. `euler_ancestral` from the menu uses eta 1. With the separate parts you can set it yourself, as in this graph. At eta 0 it is plain Euler.

{{graph:b_ancestral_eta}}

Pick `euler_ancestral` in the lab below and press for new noise. The dots land somewhere new every time, and the error reads "random by design".

{{play:solvers}}

## What goes wrong

- **Raising steps to refine an ancestral image.** The picture changes as well as sharpens, because a different number of noise draws happen. The lab's N against 2N table shows the change never settles. To refine a fixed picture, use a deterministic sampler or an SDE sampler with its Brownian path.
- **Nudging the start noise and seeing little happen.** Later noise outweighs the start, as the lab's nudge line shows. For a change in proportion to the nudge, use a deterministic sampler. A new seed is not a nudge on any sampler: it redraws all the starting noise, and the per-step noise too.
- **Expecting a match between machines.** Ancestral samplers draw per-step noise on the latent's device (CU-240). `dpmpp_sde` names without `_gpu` draw theirs on the CPU.
- **Thinking extra noise fixes errors by itself.** See the counter-example below.
- **A custom noise node that seems to do nothing with `euler`.** `s_churn` on `euler` and `heun` uses `randn_like` and ignores any noise sampler. Noise-sampler options only reach the samplers that take one.
- **Mixing up two kinds of "ancestral".** Flow models go to a different function, `sample_euler_ancestral_RF`, with a separate rule, so `eta` numbers may not mean the same thing there.

## Lab

```text
from    to      sigma_down  sigma_up   down^2+up^2  to^2
14.0    8.0     4.5714      6.5652     64.0000      64.0000
1.0     0.2     0.0400      0.1960     0.0400       0.0400
```

Most of each step down is noise put back in: going from 14 to 8 means stepping to 4.57, then adding noise of 6.57.

Both kinds reach the data distribution, at their own pace:

```text
steps  W1 euler   W1 ancestral
10     0.2623     0.3801
80     0.0393     0.0696
320    0.0130     0.0129
```

But do they settle on one image? Same seed, N against 2N steps:

```text
N      euler     ancestral  ancestral(eta=0.5)
10     0.2390    1.8318     1.2426
160    0.0349    2.1342     1.5741
```

Euler converges. Ancestral does not, and this is not a bug: its noise is drawn per step, so more steps means a different sequence. With a fixed noise path, an SDE sampler does settle, which is what the Brownian tree buys:

```text
10     1.5425
640    0.0658
```

Noise also forgets the start. Nudge the first noise, and only the deterministic result moves much:

```text
nudged start, same sampler seed: RMS change of the result   euler 0.3399   ancestral 0.0424
```

The start only partly decides an ancestral result, and a nudge there barely shows. If you want a small change of start noise to give a matching change of image, use a deterministic sampler. The lab holds the sampler's own seed fixed. In ComfyUI a new seed changes that too, and we did not measure strength changes.

## What is contested

"Noise fixes errors" is half true. Karras et al. (2022) write that stochasticity is effective in correcting errors made by earlier steps but has its own drawbacks, and that the optimal amount should be determined empirically. This lab has a counter-example, with a steady bias added to the denoiser:

```text
biased denoiser, 80 steps, W1 to data   euler 0.2869   ancestral 0.4843
```

Here the ancestral sampler does worse. This is one toy and one kind of error, so it refutes only the unconditional claim. It is not evidence that ancestral samplers are worse on real models.

## Sources

- [Karras, Aittala, Aila, Laine 2022. Elucidating the Design Space of Diffusion-Based Generative Models](https://arxiv.org/abs/2206.00364)
- [Song et al. 2020. Score-Based Generative Modeling through Stochastic Differential Equations](https://arxiv.org/abs/2011.13456)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
