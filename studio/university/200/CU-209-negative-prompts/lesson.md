# CU-209 - Negative prompts and cfg 1.0

**Objective.** Say what a negative prompt does in the formula, when it does nothing, and what it costs. Taught by Dr. Denoise.

## The idea

A negative prompt is not a list of things to subtract. It is whatever you put in the second branch of CFG (CU-208).

There is no list of banned concepts anywhere in the code. The model makes a prediction for your negative text, and the sampler aims away from that prediction, in proportion to cfg. Whether that removes the thing you named depends on what the two predictions have in common.

## The maths

```
D = D_neg + (D_pos − D_neg) · cfg
```

This has the same form as CFG with the unconditional branch replaced. At cfg = 1 it reduces to D_pos and the negative cancels out, so it has no effect at all. That also explains why models distilled for cfg 1 have no working negative prompt without extra tricks.

If positive and negative are the same, D_pos − D_neg = 0, so cfg has nothing to amplify. The guidance is the difference, and the size of the cfg number means nothing on its own.

Swing the arrow. At cfg 1 the result stays put however you turn the negative. Above 1, the result grows as the negative points further away.

{{play:negarrow}}

## In ComfyUI

`KSampler` takes `positive` and `negative`. `sampling_function` in `comfy/samplers.py` passes both to `calc_cond_batch`, then `cfg_function` applies the line above. When cfg is close to 1, `sampling_function` sets the second conditioning to None, so the negative is not evaluated at all.

There are exceptions, and they matter. A sampler or node can set `disable_cfg1_optimization`, which keeps the second prediction running at cfg 1.

- The CFG++ samplers set it, because they use the unconditional prediction to re-noise (CU-321). So on `euler_cfg_pp` the negative really does change the result at cfg 1.
- `SelfAttentionGuidance` sets it, because it needs the unconditional prediction to build its blurred image (CU-322).

The usual ways to fill the second branch are not the same as each other.

- An empty text box is encoded by the text encoder like any other prompt. Its numbers are not zero.
- `ConditioningZeroOut` makes every value of the tensor and the pooled vector zero, keeping the shape.

{{graph:c_zero_out}}

Which one a model wants depends on the model. Follow its model card or template. Don't assume they are equal.

## What goes wrong

- **"I added a negative and nothing changed."** Check cfg. At 1 with an ordinary sampler, the negative is never run. This catches people on distilled models and FLUX-family graphs.
- **"I added a long negative and the whole style shifted."** The negative moves everything away from itself, not only the named thing. Shorten it, or use a lower cfg. The lab shows the size of this push.
- **"I negated a thing that overlaps my prompt and lost my subject."** If you ask for a car and negate "red car", the two predictions share a lot, so their difference is small. CU-323 shows the fix made for this case.
- **Positive and negative swapped.** Both wires carry `CONDITIONING`, so validation can't catch it. You get a picture of the negative, pushed hard.
- **The same text in both.** No guidance survives, and cfg stops doing anything.

## Lab

Three classes at the corners of a triangle, with exact denoisers. Each row gives the share of samples nearest each class, and the median distance from the origin. The data sits at distance 3.

```text
settings                                 cat    dog    fox    distance
cfg 1, positive any, no negative         0.335  0.328  0.336  3.02
cfg 1, positive any, negative fox        0.335  0.328  0.336  3.02
cfg 3, positive any, negative any        0.335  0.328  0.336  3.02
cfg 1.5, positive any, negative fox      0.427  0.418  0.156  5.00
cfg 3, positive any, negative fox        0.494  0.490  0.016  12.39
cfg 7, positive any, negative fox        0.502  0.498  0.000  32.54
```

The first three rows are identical to every digit, and the lab asserts this. Then a real effect appears: the fox share drops from a third to 1.6 percent at cfg 3. But look at the last column. By cfg 3 the samples are four times further out than the data. The negative moves everything away from fox, including the samples that were never going to be foxes.

```text
cfg 3, positive dog, negative any        0.000  1.000  0.000  3.63
cfg 3, positive dog, negative fox        0.000  1.000  0.000  13.00
```

Same positive, same cfg: a specific negative pushes more than a neutral one, because the difference between dog and fox is larger than between dog and everything. That is a reason a long negative prompt can change the look of an image, not just remove things from it.

This 2-D toy probably overstates the distance. Real images have many other directions to absorb the push, and the VAE's output step clips decoded pixels into range, though that clip doesn't change the latent. We didn't measure this. Read the direction of the effect, not its size.

## What is contested

The derivation of guidance by Ho and Salimans (2022) concerns conditional and unconditional models. A negative prompt is a practical extension with no equivalent derivation in that paper. Lin et al. (2023) use different negative prompts in some of their published examples. How much a given negative helps is an empirical matter for each model.

## Sources

- [Ho, Salimans 2022. Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598)
- [Lin, Liu, Li, Yang 2023. Common Diffusion Noise Schedules and Sample Steps are Flawed](https://arxiv.org/abs/2305.08891)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_sag.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_sag.py)
