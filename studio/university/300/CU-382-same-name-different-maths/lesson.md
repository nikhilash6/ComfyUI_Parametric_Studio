# CU-382 - Same name, different maths

**Objective.** Compare two nodes with the same name by reading their formulas, and convert settings between them when they differ. Taught by Captain Graph.

## Why this happens

Nothing stops two people using the same name. Some start from different papers. Some simplify. Some take a shortcut and keep the name, and sometimes the name was never accurate. So a setting you learned on one node may not mean the same thing on another, and a graph that moves a number between them changes the result.

We read many packs' sampling code as text for our [Sampling Lab](#sampling/finds). It has more of these, each with its evidence. Here are the ones you can check for yourself. None of them says a pack is bad, only that a name doesn't tell you the maths.

## NAG: the same slider, off by one

Normalized attention guidance has a strength setting in two places we read.

```
core nodes_nag.py:                  z = z₊ φ − z₋ (φ − 1)
sd-perturbed-attention nag_nodes.py: z = z₊ + φ (z₊ − z₋)
```

Rewrite the first as z₊ + (φ − 1)(z₊ − z₋) and they are the same shape, one step apart. So on that line, core at 5 equals that pack at 4. Neither is wrong. They count from different places. If you move a graph between them, change the number, and don't expect the same picture: core patches the output of `attn1` and blends the two halves of a CFG batch, while this pack replaces `attn2` and runs the negative itself, and their defaults differ. We compared only the formula.

{{graph:g_nag}}

## Shift: a number with two meanings

Both of these are in core, in `comfy/model_sampling.py`, and both are called shift in everyday talk.

```
time_snr_shift(α, t)  = α t / (1 + (α − 1) t)
flux_time_shift(μ, σ, t) = e^μ / (e^μ + (1/t − 1)^σ)
```

With σ = 1, the second equals the first when α = e^μ. So μ is the logarithm of the other shift. Type 3 into each and you get very different curves. To match an SD3-style shift of 3, μ is 1.10. Try it.

{{play:samename}}

## Perp-Neg: the same word, the reverse geometry

Perp-Neg removes the part of the negative prompt that conflicts with the positive one. Core's `perp_neg` computes the part of the negative at right angles to the positive. bvhari's pack has a variable with the same name, `perp`, that holds the positive's projection on the negative, which is the parallel part and a different vector. The lab shows both on a small example, one at right angles to the positive and one not.

## "Blue" noise that isn't blue

In signal terms, blue noise has more power at high frequencies. PowerNoiseSuite's `blue_noise`, at its default alpha, divides the spectrum by a rising function of frequency, so high frequencies get less power, the reverse of that definition. Our lab reproduces the formula and measures it. The noise can be perfectly useful, but its name won't tell you what it does. The [Sampling Lab](#sampling/finds) goes further.

## Inside core too

Names can mislead in core as well.

**The sampler called `ddim`** runs `euler` with one inpaint option: see `samplers.py`. Our render on one seed came out pixel for pixel the same as euler, per `renders.json`. The wipe below shows it. Drag it: nothing changes.

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-ddim.jpg|euler|ddim|One prompt, one seed, SD 1.5. The data says these are identical.}}

**`denoise`** means two things. `BasicScheduler` keeps your step count and takes it from a longer schedule. `AlignYourStepsScheduler` cuts to round(steps × denoise), so denoise 0.5 at 20 steps runs 10.

{{graph:nm_sigmas}}

## How to check a name

1. Find the node's class in the pack, as text. Search for its name in the `NODE_CLASS_MAPPINGS` or the schema.
2. Find the line with the actual formula. Ignore the comments for now.
3. Write it out next to the one you know, and simplify.
4. Test it on small numbers, in your own code, if you can't tell by eye.
5. Note the pack's version. It can change.

## What goes wrong

- **Moving a tuned number to a same-named node.** The graph runs, and looks off. Convert the number, or tune it again.
- **Trusting a tooltip.** Tooltips can be out of date, or written from the paper rather than the code.
- **Calling a difference a bug.** It may be deliberate. Only call it a bug if the code contradicts what its author says it does.
- **Assuming a paper's name means the paper's method.** Read the code. Some are looser than their names suggest.
- **Comparing from one render.** One seed says one thing. Use the formula first.

## Lab

Each formula below was read as source text and written again in our own code. Nothing from a pack ran.

```text
NAG. Core: z+ phi - z- (phi - 1). sd-perturbed-attention: z+ + phi (z+ - z-)
  phi 1.0: same result False.  core with phi 1.0 equals pack with phi 0.0: True
  phi 3.0: same result False.  core with phi 3.0 equals pack with phi 2.0: True
  phi 5.0: same result False.  core with phi 5.0 equals pack with phi 4.0: True
```

```text
shift. SD3 style: a t / (1 + (a - 1) t). Flux style: e^mu / (e^mu + (1/t - 1)^s), with s = 1
   t     sd3 a=3    flux mu=3   flux mu=ln 3
  0.10    0.2500      0.6906        0.2500
  0.25    0.5000      0.8700        0.5000
  0.50    0.7500      0.9526        0.7500
  0.75    0.9000      0.9837        0.9000
  0.90    0.9643      0.9945        0.9643
```

```text
perp-neg. Core's perp: the part of neg at right angles to pos. bvhari's: the part of pos along neg
  core [-0.40000009536743164, 1.2000000476837158]  dot with pos -0.0000
  pack [2.0, 2.0]  dot with pos +8.0000
```

The first has a dot product of zero with the positive, and the other doesn't: different vectors under one word.

```text
"blue" noise. PowerNoiseSuite's default divides the FFT by (f^2)^(alpha/4), which with alpha 2 is amplitude 1/f, power 1/f^2.
  low frequency power / high frequency power: white 0.93, this 'blue' 24.41
  above 1 means more power at low frequency. Textbook blue noise has more at high frequency, so below 1.
```

```text
denoise, inside core. BasicScheduler keeps the step count. AlignYourSteps shortens it
  denoise 1.0: BasicScheduler runs 20 steps from a 20 step schedule. AYS runs 20 steps.
  denoise 0.5: BasicScheduler runs 20 steps from a 40 step schedule. AYS runs 10 steps.
  denoise 0.25: BasicScheduler runs 20 steps from a 80 step schedule. AYS runs 5 steps.
```

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_nag.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_nag.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_perpneg.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_perpneg.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_custom_sampler.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_custom_sampler.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_align_your_steps.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_align_your_steps.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [pamparamm/sd-perturbed-attention, nag_nodes.py](https://github.com/pamparamm/sd-perturbed-attention)
- [bvhari/ComfyUI_PerpNeg, perpneg.py](https://github.com/bvhari/ComfyUI_PerpNeg)
- [WASasquatch/PowerNoiseSuite, modules/latent_noise.py](https://github.com/WASasquatch/PowerNoiseSuite)
