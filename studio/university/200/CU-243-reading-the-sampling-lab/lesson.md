# CU-243 - Reading the Sampling Lab

**Objective.** Open the [Sampling Lab](#sampling), say what each label promises, and answer a real question with its curves, bench and renders. Taught by Professor Latent.

## The idea

The Sampling Lab is our catalogue of what samplers, schedulers, guidance tricks, noise and latent maths really do. Someone read the source of each one. Its job is to stop you having to trust a method's name. It is also honest about how much proof each thing has, and that's what you need to learn to read.

It has six views, in the bar at the top:

| View | Holds | Use it when |
|---|---|---|
| [Atlas](#sampling) | Every method with its working, proof and author | "What does this node really do?" |
| [Curves](#sampling/curves) | Real sigma lists per model type | "Where do this scheduler's steps go?" |
| [Bench](#sampling/bench) | Samplers on a toy with an exact answer | "How accurate is this solver for its cost?" |
| [Renders](#sampling/renders) | Real pictures you can wipe | "What kind of difference does this make?" |
| [Surprises](#sampling/finds) | Things that were not what the name says | "Is there a catch?" |
| Credits | Who wrote what, and its licence | "Whose work is this?" |

## The labels

Every claim carries one of four labels. They are not grades of quality. They say how anyone knows.

- **From code.** "Read in the source. A script found its file and line on disk." That proves the code exists there. A person's reading of what it means can still be off.
- **Measured here.** "Ran on this machine, with the numbers kept." Bench numbers come from a toy, and renders come from one seed. It shows that this happened, and it doesn't show that one method is better.
- **README claim.** "What an author says. Not checked here."
- **Inference.** "Our reasoning, not read or measured."

Other pills on a method: **In core, runs here**, **Live pack**, **Needs a pack**. "Here" means the machine that built the page, so read those for yourself as "in core" or "needs a pack". And **Second reader checked**: another reader went through that entry against the code.

{{play:readlabel}}

## How much to trust it

The lab prints the real figures. About half of the entries had a second reader. Of those, 22% needed a fix or a caveat. 69 of those 82 were then corrected, and the other 13, all minor, still carry the reader's note. The other half have not had that chance, and our guess is they have a similar rate of faults. So open an entry's file and line before you stake a day's work on it.

No method from outside core is proven by a render yet. The sandbox failed its control render, so all six attempts failed. A pack's entry tells you what the code says, and not that it works on your model.

## Using the curves

Pick a model type and up to several schedulers. The readout has two numbers worth knowing:

- **Sigma here** is the value at the step you're on. Step through, and compare.
- **Last before 0** is the one that warned of `linear_quadratic` in CU-235.

The log scale shows the low end, and the linear scale shows where the high steps go. The "Set up a comparison" buttons load the known traps.

To do the same with no page at all:

{{graph:nm_sigmas}}

## Using the bench

Each row is one sampler at 5, 10, 20 and 40 steps, against a problem with an exact answer. The columns:

- **Model calls, 20 steps.** Multiply by 2 for CFG above 1.
- **Kind.** Deterministic, or stochastic if it adds noise.
- **Error to exact.** Only meaningful for deterministic ones.
- **Slope.** How fast the error falls as calls grow. −1 means double the calls, half the error. −2 means double the calls, a quarter.
- **Variance error.** For stochastic ones, how far the result's spread is from the truth.

The page says this in bold, and we repeat it: the bench says nothing about how pictures look.

Below it, one small panel asks whether core's noise is really white (CU-240). The Curves view has a matching panel that shows how an ancestral sampler splits each step (CU-207).

## Using the renders

Pick a set, then pick A and B from the contact sheet. The wipe shows both, and the figure above it is the mean difference out of 255, worked out in your browser. The bar under each frame is its recorded distance from the baseline. Zero means pixel for pixel, as with `ddim` and `euler`. Each set shares one model, one seed and one prompt.

## A worked question

The question: "My flow model's output looks brown and unfinished, and I use karras."

1. **Surprises** mentions karras on SD 3.5. It is measured, one seed.
2. **Curves**: press "karras on a flow model". Karras falls long before the others.
3. **Renders**, flow set: wipe karras against simple.
4. **Atlas**: search karras, and read its working.
5. Try `simple` on your own model, on a few seeds. The page has given you a lead. Your test decides it.

## What goes wrong

- **Reading "measured here" as "better".** It only says it ran. Look for how many seeds. Here it's one.
- **Reading "from code" as "works".** It says what the code does, and it hasn't been run.
- **Treating low bench error as good pictures.** No image is involved.
- **Taking a brightness or edge number as a verdict.** CU-235 shows a broken render with the same numbers as a good one.
- **Reading "runs here" as "runs on your machine".** It describes the machine that built the page.
- **Copying a value between packs because the name matches.** Same name, different maths is one of the page's main findings.
- **Installing a pack from the list.** The page describes what the code does. It is not a safety review. Read a pack's code before you run it.

## Lab

These are the page's own numbers, recomputed from stored tables.

```text
atlas: 720 methods; 183 in core; 13 in a live pack only; 524 need a pack; 44 rendered
by family: guidance 174, latent 91, math 12, noise 79, patch 86, sampler 164, scheduler 114
by label: from code 692, from pack README claim 2, inference 26
second reader looked at 378: 296 right, 68 imprecise, 14 wrong, so 22% needed a fix or a caveat. Share of all methods checked this way: 52%
of those 82, corrected in the atlas: 69
renders: 44 real, all in core. Pack methods proven by a render: 0 of 6 tried
```

The curve readout, on two lists:

```text
karras step 0: 14.61464  step 10: 1.09079  last before 0: 0.02917
linear_quadratic step 0: 14.61464  step 10: 14.24928  last before 0: 2.67448
```

The bench's slope is a straight-line fit. We recompute it and it matches.

```text
euler: -1.01, stored -1.01.  Double the calls and the error is multiplied by 0.50
heun:  -2.24, stored -2.24.  Double the calls and the error is multiplied by 0.21
```

The noise panel, and one row of the ancestral panel. From σ 14.6146 to 11.7254, it steps down to 9.4073 and adds noise of size 6.9991, and those two square-add back to 11.7254.

```text
bands 16, lowest 0.941, highest 1.017, mean 1.000
ancestral panel, karras, first step [from, to, sigma down, sigma up]: [14.6146, 11.7254, 9.4073, 6.9991]
```

## Sources

- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
