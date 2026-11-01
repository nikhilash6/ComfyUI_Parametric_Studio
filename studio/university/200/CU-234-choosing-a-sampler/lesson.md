# CU-234 - Choosing a sampler from real renders and measures

**Objective.** Read our sampler renders and bench without over-reading them, and choose a sampler by a method rather than a reputation. Taught by Dr. Denoise.

## The idea

There are 45 names in the sampler menu, and plenty of confident advice. We have two kinds of real evidence, and neither answers "which is best".

- **Renders.** One prompt, one seed, one model, 20 steps. They show that a choice makes a difference, and what kind.
- **The bench.** ComfyUI's own samplers on a toy problem with a known exact answer and no neural network. It shows how closely a solver follows its equation and what that costs.

Both live in the [Sampling Lab](#sampling/renders), where you can wipe any two renders against each other. CU-243 is the guide to that page. This lesson reads them for a decision. Open this graph to run your own test:

{{graph:sd15_txt2img}}

## What the renders show

All of these use SD 1.5, karras, CFG 7, 20 steps, seed 424242.

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-dpmpp_2m.jpg|euler|dpmpp_2m|Two deterministic samplers on one seed. The same scene and layout. The engraving and the instrument's details differ.}}

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-euler_ancestral.jpg|euler|euler_ancestral|Same seed, one sampler that adds noise every step. A different composition: a different viewpoint, and charts in the frame.}}

That is the clearest thing the sweep shows, and the lab measures it. Against the `euler` render, the deterministic samplers differ by 20.92 to 30.17 out of 255, leaving out `ddim`, which is the same picture (below). The ones that add noise differ by 45.92 to 75.13, with no overlap. So the first question is not which name, but whether you want noise added at each step. CU-207 explains why that moves the picture so far.

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-lcm.jpg|euler|lcm|lcm on a model not trained for it: flat shapes and little detail. A sampler can need a matching model.}}

## ddim and euler

The sweep gave one result that surprises people.

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-ddim.jpg|euler|ddim|Same pixels. Drag it and nothing changes.}}

The two renders are identical in our sweep, with the same hash, and on the bench the two rows are identical too. The code says why: `sampler_object` builds `ddim` as `ksampler("euler", inpaint_options={"random": True})`. So in this version the `ddim` name runs Euler. The one thing that differs is the noise used for masked regions. Do not read this as a claim about the DDIM paper's method, or about other software. It is what the name does here, and it has nothing to do with the `ddim_uniform` scheduler.

## What the bench shows

{{play:solvers}}

The play is a small bench of our own in your browser. The [full bench](#sampling/bench) has more names. From the lab:

- Calls at 20 steps come in a few sizes: 20 for most names, 39 for two-stage ones like `heun`, and more for `heunpp2` and `seeds_3`. At CFG above 1, double all of them.
- `dpmpp_2m` gets error 0.0119 for 20 calls. `heun` gets 0.0114 for 39. On this toy, about the same accuracy for half the work.
- Several names you may never have tried (`uni_pc`, `deis`, `ipndm`) score lower still on the toy.

Then remember what it is. A Gaussian toy has no image in it. A low number means "follows the equation closely". It does not mean "looks better". Noise-adding samplers cannot be scored this way at all, because they have no single exact path, so the bench gives them a variance error.

## A way to choose

1. Decide on noise first. If you want small changes to give small changes (a fixed composition, a seed you are tuning), use a deterministic sampler. If you want variety from step count and don't need that, try one that adds noise.
2. Set a budget in evaluations, not steps. Compare at equal cost.
3. Start from a plain one-call sampler such as `euler` or `dpmpp_2m`. Move only when you see a problem in your own pictures.
4. Test on several seeds and prompts. The lab below shows how little one seed can say.
5. Fix the seed while comparing, and change one field at a time.

## What goes wrong

- **Judging from one seed.** That is what our own renders are. Use them to see what kind of change a sampler makes. Do not rank from them.
- **"This sampler is sharper."** On one seed, the edge measure varied, but we have no second seed to compare, and a new seed could move it too. Test more than one.
- **Reading a bench row as image quality.** The bench has no image.
- **Comparing at equal steps.** `dpmpp_sde` and `heun` at 20 steps cost nearly twice `dpmpp_2m` at 20 steps.
- **Trying `ddim` and `euler` as two options.** In this version they are one, apart from masked sampling.
- **`lcm` on an ordinary model.** Our render came out flat. Its update assumes a model built for it.
- **A pack's sampler with a familiar name.** Same name, different maths is common across packs. The [Sampling Lab](#sampling) lists who wrote what.

## Lab

The lab holds the stored tables, so you can read the sums. It renders nothing.

```text
bench: 45 sampler names, 22 deterministic, 23 stochastic
calls at 20 steps, grouped: 18: 1  20: 31  39: 11  57: 1  58: 1
ddim row equals euler row: True   euler_cfg_pp equals euler: True   dpmpp_2m_sde_gpu equals dpmpp_2m_sde: True
render, ddim against euler: difference 0.0  every measure equal: True
```

The bench has no guidance, and it ran on the CPU. Our reading is that this is why `euler_cfg_pp` and the `_gpu` names match their plain versions here. They would not have to match in a real run.

```text
name           calls  error    slope  error per doubling of calls
uni_pc         20     0.0016   -0.84  x0.56
deis           20     0.0020   -2.26  x0.21
lms            20     0.0059   -2.88  x0.14
heun           39     0.0114   -2.24  x0.21
dpmpp_2m       20     0.0119   -2.26  x0.21
euler          20     0.0768   -1.01  x0.50
```

The last column is what doubling your calls buys. Euler halves its error. A second-order method cuts it to about a fifth. `uni_pc` has the lowest error at 20 calls and a weak slope, so a single row is not the whole story.

```text
render difference from euler, one seed: deterministic mean 24.7 (range 20.92 to 30.17); noise-adding mean 60.7 (range 45.92 to 75.13)
rank correlation, bench error against render edge strength, 6 samplers, one seed: -0.09. Far too few points to mean anything, and that is the point.
```

The last line is here as a warning. We could report a correlation between bench and picture, and it would look like a finding. With six points and one seed, it is noise.

## Sources

- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [Karras, Aittala, Aila, Laine 2022. Elucidating the Design Space of Diffusion-Based Generative Models](https://arxiv.org/abs/2206.00364)
