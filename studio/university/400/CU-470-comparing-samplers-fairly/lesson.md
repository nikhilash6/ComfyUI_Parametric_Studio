# CU-470 - Comparing two samplers fairly

**Objective.** Run a fair test of two samplers: the same seeds, enough of them, a measure chosen first, a cost in model calls, and honest limits on what you can claim. Taught by Tinker Tune.

## The idea

You render one image with each sampler, and one looks better. Have you learned anything? Almost nothing. A seed changes a picture far more than most sampler choices do, so one render can name either winner.

A fair test has five parts.

1. **One change.** Same model, prompt, size, guidance and scheduler, unless the scheduler is part of the test.
2. **The same seeds for both.** Each seed gives one pair. Compare within the pair.
3. **Enough seeds.** More than feels necessary, then a range around the result.
4. **A measure chosen first.** Decide before you look. Then you can't pick the measure that suits you.
5. **Cost in model calls.** Some samplers call the model twice per step.

## Why the same seeds

Let score = seed effect + sampler effect + noise. If both samplers use the same seeds, the seed effect cancels in the difference. Otherwise it stays in, and you need many more seeds to see past it.

```
range of a mean difference ≈ ± 2 × sd ÷ √n
seeds needed for a range of ± d:  n ≈ (2 × sd ÷ d)²
```

This sum is a rule of thumb. It assumes independent seeds and a rough bell shape. But it shows why more seeds pay off slowly: four times the seeds halve the range.

{{play:seeds}}

## A worked example, and its limits

Our [Sampling Lab](#sampling/bench) has two kinds of numbers.

**Toy-problem measurements.** Each core sampler ran on a problem whose exact answer is known, using ComfyUI's own code. That tells you how well a solver follows an ODE, and the script that made them says plainly that the toy problem "says nothing about pictures". It's a fair test of the solver, not of your image. See the first table in the lab below.

**Renders.** 44 pictures of one prompt and one seed, in the [Sampling Lab](#sampling/renders). Each row has brightness, contrast, an edge measure and seconds. Useful for seeing how far a sampler moves a picture. Useless for ranking, since n is 1.

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-dpmpp_2m.jpg|euler|dpmpp_2m|One prompt, one seed, karras, 20 steps. This shows a difference, and can't rank them.}}

Some things are learned from a single seed, though. Its data show that `ddim` gave the same pixels as `euler`, which is a fact about the code, not a matter of noise. A fact like that needs one test.

## Which measure?

- **Stable to the method?** For a solver: error against a very long run of a similar solver. On pictures, a measure from CU-404 between a short run and a long run at the same seed. This asks about convergence, not beauty.
- **Does it look better?** Ask people, without telling them which is which. A few readers rating many pairs beats one person looking at one.
- **Does it follow the prompt?** Use a checklist (CU-413).
- **Speed.** Time per model call, on your own hardware, after the first run has loaded the model. Our render timing is polled every 1.5 s and the first includes loading, so it's not fit for ranking.

## In ComfyUI

Use a plain graph and change only `sampler_name`. In the graph below, the seed and sampler are on `KSampler`. Change the seed with a script (CU-460), not the "randomize" widget, so that the same list of seeds goes through both samplers.

{{graph:sd15_txt2img}}

Note that stochastic samplers (ancestral, SDE) use fresh noise drawn in the loop, so they don't converge to the same picture as you add steps. The toy table shows this: `same_answer_with_other_noise_seed` is false for `euler_ancestral`, and its error against the exact ODE answer doesn't shrink. That isn't a flaw. It's the wrong measure for it. Don't rank an SDE sampler by its distance from an ODE's answer.

## What goes wrong

- **Equal steps, unequal cost.** `heun` calls the model about twice per step. At 20 steps it beats `euler`, but it spent 39 calls. Compare at equal calls.
- **One seed, one winner.** With our made-up sizes a single seed points the wrong way 24% of the time when a true gain exists. Yours may differ. It's not zero.
- **Best of many samplers.** Try 15 equal samplers and one wins by chance. Test the winner again on new seeds.
- **A convergence test used as a beauty test.** A sampler nearest the long-run image isn't always the one people prefer.
- **The first render's time.** It includes loading. Our data show euler at 66 s and the others at 1.5 s, which is not about the sampler.
- **Different schedulers by accident.** A sampler and scheduler pair is a two-part change. Change one thing.

## Lab

The first two tables copy values from the course's measurement files. The lab can't read files, so we checked these against them by hand.

```text
sampler    steps  calls  rmse
euler      10     10     0.1548
euler      20     20     0.0768
heun       10     19     0.0558
heun       20     39     0.0114
dpmpp_2m   10     10     0.0541
dpmpp_2m   20     20     0.0119
```

```text
same steps (20): heun 0.0114 beats euler 0.0768, for 39 calls against 20
same calls (about 20): heun at 10 steps 0.0558, euler at 20 steps 0.0768, dpmpp_2m at 20 steps 0.0119
```

Those answer a toy problem. Now the renders, one seed.

```text
sampler           brightness  contrast  edge    seconds
euler             102.4       72.1      20.17   66.0
heun              106.4       80.5      23.38   1.5
dpmpp_2m          105.1       77.2      22.93   1.5
euler_ancestral   81.6        51.7      12.16   1.5
seconds are polled every 1.5 s, and euler's 66 includes loading the model, so these can't rank speed
```

Now a simulation. The sizes are ours: seed effect 5, noise 1, true difference 1.

```text
seeds per sampler   same seeds: diff +/- range   different seeds: diff +/- range
1                   +0.79, no range               +0.08, no range
4                   +1.25 +/- 0.77              +5.78 +/- 12.23
16                  +0.66 +/- 0.73              -0.55 +/- 4.57
64                  +1.05 +/- 0.39              +0.48 +/- 1.78
256                 +1.05 +/- 0.17              +1.09 +/- 0.90
```

```text
seeds for a range of +/- the true difference: same seeds (sd of difference 1.41): 9, different seeds (sd 7.21): 208
same seed, one render each, true difference +1 in favour of b: a looks better 24% of the time
15 equal samplers, 8 seeds each, noise sd 1: the winner's lead over the true mean averages 0.62, so test the winner again on new seeds
```

We ran no real comparison of samplers on pictures for this lesson. The method is what you take away.

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
