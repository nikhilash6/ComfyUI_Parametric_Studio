# CU-235 - Choosing a scheduler from the curves

**Objective.** Read a scheduler's list of numbers, spot the two kinds of list that broke our renders, and choose by testing instead of by name. Taught by Dr. Denoise.

## The idea

CU-206 shows the formulas. This lesson is about using them. A scheduler's whole output is a list of numbers, made before the model runs. That is a gift: you can read it without spending any GPU time, and it can warn you of trouble.

This graph needs no model at all. It prints two schedules and splits one.

{{graph:nm_sigmas}}

## What to read in a list

Three things, in this order.

- **The first number.** Does it start at the top of the model's range? If it starts lower, the first noise is smaller than a full run would have.
- **The last number before 0.** The final step jumps from here to clean in one go. A big number means a big leap at the end.
- **Where the middle lands.** That tells you where the steps are being spent.

Try it. Pick schedulers, change the model kind, and read the same three things.

{{play:sigmas}}

The [Sampling Lab's curves](#sampling/curves) show the real lists for SD and SDXL, SD 3.5 and Flux. It has buttons that set up the comparisons below.

## Two lists that warned us

Our render sweep has one seed per setup. Two renders came out broken. Both of their lists look odd, once you know what to read.

**`linear_quadratic` on SDXL.** Its last number before 0 is 2.67, where `karras` has 0.03. So the last step leaps from heavy noise straight to clean. Its step 10 is still at σ 14.25.

{{wipe:sampling_lab/scheduler-karras.jpg|sampling_lab/scheduler-linear_quadratic.jpg|karras|linear_quadratic|SDXL with dpmpp_2m, 20 steps, one seed. linear_quadratic is smeared, with rainbow speckle on the brass.}}

The formula explains it. A comment in the source points to Genmo's Mochi video model code. It builds a list running from 1 to 0, spending most of it near 1, then multiplies by `sigma_max`. On a flow model that top is 1, and the last value is 0.183 of a small range. On SDXL the same shape multiplies by 14.6.

**`karras` on SD 3.5.** It reaches σ 0.085 by step 10, where `simple` is at 0.75. Almost all the steps are spent at low noise, and only 4 of the 20 sit above σ 0.5. Karras's formula bunches steps at the low end of whatever range it gets, and this range runs from 0.003 to 1.

{{wipe:sampling_lab/flow-euler-simple.jpg|sampling_lab/flow-euler-karras.jpg|simple|karras|SD 3.5 with euler, 20 steps, one seed. simple gives a finished scene. karras is brown and unfinished.}}

On the same seed, `simple`, `beta` and `kl_optimal` held together. So a scheduler that is a fine default on one kind of model can fail on another. Names don't carry over between families.

**A milder one: `ddim_uniform`.** It starts at σ 11.03 where the others start at 14.61, because it picks every 50th table entry from index 1, and the top one it reaches is index 951. On SDXL it rendered brighter, with a new layout (mean difference 37.87 from the `normal` render).

And a reassuring one: `sgm_uniform` and `simple` have almost the same lists (mean gap 0.0027), and their SDXL renders are almost the same picture. A list that barely changes gives a picture that barely changes.

## A way to choose

1. Start with what the model's own example uses. If you have none, read the list on that family first.
2. Rule out lists with a big last jump or a start below the top, unless you want that.
3. Compare a few on several seeds at equal steps. Change only the scheduler.
4. Remember the sampler is part of the test. CU-206 shows `normal` six times worse than `exponential` with DPM++ 2M at 10 steps on a toy, and about equal with Euler.
5. Want to bend one? Use `KarrasScheduler`, which shows rho, as in this graph.

{{graph:sd15_karras_rho}}

Flow models usually add a shift, set by `ModelSamplingSD3` as here (CU-242).

{{graph:sd35_flow}}

## What goes wrong

- **A default that worked on SD fails on a flow model.** Read the two lists side by side. `karras` is the famous case.
- **Asking for 30 steps and getting 31.** `ddim_uniform` can return more steps than asked, as the lab shows. `beta` can return fewer, because it removes repeated values. Check the length of the list if timing matters.
- **`KarrasScheduler` with copied numbers.** Its sigma_max and sigma_min are plain inputs. SD 1.5 values on a flow model give nonsense, with no error.
- **A smeared picture with coloured speckle.** Look at the last number before 0 first, then at the steps. This is what our `linear_quadratic` render looks like.
- **Blaming the scheduler for one seed.** Run more seeds before you decide a scheduler is bad. Our two broken renders are one seed each.
- **Comparing names across packs.** Some packs' schedulers repeat a core one under a new name. The [Sampling Lab](#sampling/finds) lists those it found.

## Lab

The lab holds the stored lists from ComfyUI's own code, and two ports checked against them.

```text
ports of ddim_uniform and linear_quadratic match the stored lists from ComfyUI's code: True
ddim_uniform takes every 50th table entry from index 1, so its top is index 951 of 999: sigma 11.028, not 14.615
ddim_uniform steps asked for and returned: [(20, 20), (25, 25), (30, 31)]
```

The two tables hold the three things to read. The last column counts steps spent above a mark: σ 1 for SD, and σ 0.5 for flow.

```text
SD and SDXL noise prediction, 20 steps
scheduler         first    step 10   last before 0   steps above sigma 1.0
simple            14.615   1.613     0.2230          13
karras            14.615   1.091     0.0292          11
exponential       14.615   0.554     0.0292          9
ddim_uniform      11.028   1.376     0.0413          12
normal            14.615   1.481     0.0292          13
linear_quadratic  14.615   14.249    2.6745          20
```

```text
SD 3.5, flow, shift 3, 20 steps
scheduler         first    step 10   last before 0   steps above sigma 0.5
simple            1.000    0.750     0.1364          15
karras            1.000    0.085     0.0030          4
exponential       1.000    0.047     0.0030          3
beta              1.000    0.751     0.0409          14
kl_optimal        1.000    0.392     0.0030          8
```

`exponential` has a list even more extreme than `karras` on flow. We did not render it, so we cannot say what it does.

```text
SDXL ddim_uniform      37.87   106.6   16.09
SDXL linear_quadratic  34.74   75.6    22.11
SD3.5 karras           37.0    95.3    7.9
SD3.5 kl_optimal       34.89   96.5    7.85
```

Those columns are difference from the baseline, brightness and edge strength. Look at the last two rows: a broken render and one that held up have nearly the same numbers. Summary numbers can't tell you a picture is broken, so look at it.

```text
sgm_uniform and simple, mean gap between lists 0.0027; karras and exponential 0.6768; normal and karras 0.4432
```

## Sources

- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [Karras, Aittala, Aila, Laine 2022. Elucidating the Design Space of Diffusion-Based Generative Models](https://arxiv.org/abs/2206.00364)
