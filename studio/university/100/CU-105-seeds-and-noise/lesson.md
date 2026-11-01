# CU-105 - Seeds, noise and determinism

**Objective.** Say exactly what a ComfyUI seed fixes, predict which changes keep a picture's composition and which scramble it, and explain why the same seed can still give different pixels on another machine. Taught by Dr. Denoise.

## The idea

A sampler starts from noise, and a seed is what makes that noise repeatable. A pseudo-random generator is a formula with a state: seed it with the same number and it produces the same stream of numbers. In ComfyUI the seed has one job at the start of a run, which is to produce the starting noise. After that, a deterministic sampler contains no randomness at all, so the picture is a function of the noise, the model, the prompt and the sampler settings.

The question to ask at every step is the noise level. At the first step of an SD 1.x run it is about 14.6, so the image is buried, and the seed decided what it is buried in.

## The mechanism

**Start.** Draw ε from a unit normal, one number per latent value. At full denoise ComfyUI starts from x = ε √(1 + σ²), where σ is the largest sigma of the model, which gives the network unit-variance input once its own input scaling is applied. With denoise below 1 it starts, for SD 1.x style models, from x = latent + σ ε: noise added to the encoded image at a lower σ.

**Step.** A deterministic Euler step moves along d = (x − D(x, σ)) / σ, where D is the network's estimate of the clean image, and then x_next = x + d × (σ_next − σ). No random number appears in it. Two runs with the same ε and the same settings follow the same path, and a run with a different step count follows nearly the same path with other step sizes. For a deterministic sampler, Song, Meng and Ermon (2020) observed that images made from the same initial noise have similar high-level features whatever the number of steps, and that in many cases 20-step samples already resembled 1000-step ones.

**Ancestral step.** Step down to σ_down, then add fresh noise of size σ_up, where σ_up² + σ_down² = σ_next². It needs new random numbers at every step. Change the step count and the whole sequence of draws changes, so the run leaves the family of paths that the seed started.

**Rounding.** Floating-point addition is not associative, so the same numbers added in another order give a slightly different sum. Chips and libraries add in different orders. Identical output therefore needs identical software and hardware, and the seed alone cannot promise it.

## See it on a real render

These three pictures come from one prompt, one seed and 20 steps, on SD 1.5. Only the sampler changes. Euler and Heun are deterministic and follow nearly the same path, so the composition holds and the details shift. Euler ancestral adds fresh noise at each step, and here it gives a different scene from the same seed. This is one seed on one model, so read it as an example.

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-heun.jpg|euler|heun|Same seed, same prompt: the brass disc and the window stay put}}

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-euler_ancestral.jpg|euler|euler ancestral|Same seed, same prompt: a new scene}}

More pairs are in the [Sampling Lab](#sampling/renders). Now do the same test on a toy, where you can change the steps and the seed.

{{play:seedwalk}}

The seed sits on `KSampler`, or on its own `RandomNoise` node in the custom form, which makes it plain that the seed only feeds the noise.

{{graph:sd15_custom}}

## In ComfyUI

The KSampler seed is an integer from 0 to 0xffffffffffffffff, with a "control after generate" setting that the documentation lists as Random, Inc, Dec or Keep. With a random choice the seed changes after each queue, so the KSampler's cache key from CU-102 is new on every run.

`common_ksampler` in `nodes.py` calls `comfy.sample.prepare_noise`, which seeds PyTorch's generator and draws `torch.randn(..., dtype=torch.float32, device="cpu")`. The starting noise is made on the CPU in float32, whatever device the model runs on, and is then cast to the latent's dtype. A batch is one draw of shape [B, C, H, W], and in the lab image 0 of a batch of four equals the noise of a single image. `RandomNoise` in `comfy_extras/nodes_custom_sampler.py` offers the same recipe to the custom-sampler nodes.

`sample_euler` in `comfy/k_diffusion/sampling.py` is the Euler form of Algorithm 2 of Karras et al. (2022), with the stochastic churn off unless `s_churn` is set, so by default it adds no noise. `sample_euler_ancestral` takes the seed from `extra_args` and builds its noise source with `default_noise_sampler`: a `torch.Generator` on the same device as the latent, seeded with the seed, plus one when that device is the CPU. On a GPU the extra noise therefore comes from a GPU generator, and PyTorch's reproducibility notes say that results may not match between CPU and GPU even with identical seeds.

## What goes wrong

- **Same seed, different picture.** Something else changed. Compare the two PNGs' `prompt` data (CU-110): model, sampler, scheduler, steps, cfg, size, denoise, prompt. If all of it matches, the software or hardware may differ, as PyTorch warns.
- **You can't get a good picture back.** With "control after generate" on Random, the seed widget has already moved on. The number you want is stored in the saved PNG, so drop it on the canvas, or read its `prompt` entry.
- **You expected seed 43 to look like seed 42.** It's unrelated noise, as the lab's correlation shows. To make small variations, keep the seed and change something else.
- **Same seed at a new size gives a new picture.** The noise has a new shape, so its numbers land in different places. Don't expect the composition to carry over.
- **Changing steps on an ancestral sampler scrambles the picture.** Each step count draws its own noise. Use a deterministic sampler while you tune steps.
- **The seed won't re-run the graph.** Same seed, same everything: the cache serves it and nothing happens (CU-112). That's usually what you asked for.
- **A batch and a single don't line up.** Image 0 of a batch matches the single-image noise, as the lab shows, but images 1, 2, 3 have no seed of their own to reuse.

## Lab

Part one and two use PyTorch's CPU generator the way `prepare_noise` does, on the latent of a 512 by 512 image.

```text
same seed twice: identical True
seed 42 against seed 43: correlation 0.0058 over 16384 values
noise from seed 42: mean 0.0091, std 1.0040
batch of 4 from seed 42: image 0 equals the single-image noise True, correlation of images 0 and 1: 0.0042
```

The same seed gives the same numbers exactly. Seed 43 gives numbers with no resemblance to seed 42, so a neighbouring seed is not a nearby starting point.

```text
a CPU generator seeded 42 repeats the starting noise: True; seeded 43, which ComfyUI does on the CPU: correlation 0.0058
sum of the 16384 numbers in float32: forward 149.764481, reverse 149.764572, torch.sum 149.764816; exact 149.764800
```

The first line shows what the extra +1 avoids: with the same seed on the CPU, the first extra noise would be a copy of the starting noise. The second line adds the same 16384 numbers three ways and gets three answers.

The toy comes next. The data is two blobs at plus and minus 2 along one axis (16 dimensions, spread 0.5), chosen because its exact denoiser has a closed form, so no network is involved. The lab runs the Euler and ancestral-Euler update rules from 4000 starting noises on an exponential sigma schedule from 14.6146 down to 0.0292, and compares each short run with an 80-step run from the same noise.

```text
steps           Euler: same blob   mean distance   ancestral: same blob  mean distance
5               1.000              0.707           0.554                 3.048
10              1.000              0.317           0.573                 3.200
20              1.000              0.132           0.608                 3.162
40              1.000              0.044           0.711                 2.573
unrelated noise 0.504              3.723           0.498                 3.682
```

Read the Euler column first. From the same noise, every sample lands in the same blob whatever the step count, and the distance to the 80-step result shrinks as steps grow. With unrelated noise the blob agrees half the time, which is chance. The ancestral column is different: its agreement with the 80-step run is only 0.554 to 0.711, and the distances stay large, 2.6 to 3.2 against 3.7 for unrelated noise, because each step count draws its own sequence of extra noise.

```text
same seed, same steps, run twice: identical for Euler and for ancestral
starting noise scaled by 1 + 1e-6 (Euler, 20 steps): samples that change blob 0 of 4000, largest change of any number 0.000002
```

A seeded ancestral run repeats exactly when nothing else changes. A starting noise nudged by one part in a million moved no sample out of its blob here.

## What is contested

The toy is smooth by construction, and a real network owes no such stability. The nudge test says only that the toy absorbs a tiny change. It does not say that real images are as steady, and the PyTorch notes quoted above give no such guarantee across platforms. The DDIM observation is about DDIM-style deterministic sampling. The lab does not test samplers such as the multistep ones, or real images, and it does not say how closely a given ComfyUI sampler follows the pattern.

## Sources

- [Song, Meng, Ermon 2020. Denoising Diffusion Implicit Models](https://arxiv.org/abs/2010.02502)
- [Karras et al. 2022. Elucidating the Design Space of Diffusion-Based Generative Models](https://arxiv.org/abs/2206.00364)
- [Reproducibility, PyTorch 2.15 documentation](https://docs.pytorch.org/docs/2.15/notes/randomness.html)
- [KSampler - ComfyUI Built-in Node Documentation](https://docs.comfy.org/built-in-nodes/KSampler)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/sample.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sample.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_custom_sampler.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_custom_sampler.py)
