# CU-314 - Flow-matching losses and velocity targets

**Objective.** Write the flow matching target and loss, explain why the loss has a floor, convert an error between velocity, clean latent and noise, and read what ComfyUI's own trainer minimises. Taught by Dr. Denoise.

## The idea

CU-204 explains the field you integrate. This lesson is the training side. It is one regression. Take a clean latent and a noise sample, draw the straight line between them, pick a point on the line, and ask the network for the direction.

{{graph:sd35_flow}}

That graph is a flow model at sampling time. Its shift also appears below, because it can decide which noise levels get trained.

## The target

Symbols: x₀ is a clean latent, ε is noise, t is between 0 and 1.

```
x_t = (1 − t) x₀ + t ε        the point on the line
v   = ε − x₀                  the target, which is the same all along the line
L   = E ‖ v_θ(x_t, t) − v ‖²  the loss
```

This is the same mix as `CONST.noise_scaling` in `comfy/model_sampling.py`, with t written as σ. Try it on a real picture: choose the flow formula and find where signal equals noise.

{{play:noise}}

## Why the loss doesn't go to zero

The network sees x_t and t, and never the pair. Many pairs pass through the same point. So the best it can do is the average of their targets, and CU-204 calls that average u(x, t). Anything left over can't be removed by training:

```
floor at t = E ‖ v − u(x_t, t) ‖²
```

A flow matching loss that stops falling may well be at its floor. It isn't telling you the model is finished, or that it's bad. A loss value on its own says little, and you can't compare it across datasets.

## The same error in other units

Given a velocity estimate, the other estimates follow by algebra:

```
clean estimate   x̂₀ = x_t − t · v̂
noise estimate   ε̂  = x_t + (1 − t) · v̂
```

So a velocity error of δ is a clean-latent error of t·δ and a noise error of (1 − t)·δ. At low t the same velocity error barely moves the clean estimate. At high t it moves it nearly fully. That means choosing what to regress on is choosing a weight for each noise level.

```
loss on clean estimate  = t²       × loss on velocity
loss on noise estimate  = (1 − t)² × loss on velocity
```

## Which noise levels get trained

Weight can also come from how often each t is drawn. Esser et al. (2024) write this as an equivalent weighted loss, and aim to train intermediate timesteps more often. One of their options is logit-normal sampling: draw u from a normal distribution with parameters m and s, then map it through the logistic function. In their rank table, `rf/lognorm(0.00, 1.00)` comes first overall.

## In ComfyUI

Core does have a trainer, in `comfy_extras/nodes_train.py`, and it's worth reading. `TrainSampler.fwd_bwd` does this:

```
xt      = noise_scaling(σ, noise, latent)
x0      = the latent
x0_pred = model(xt, σ)            the clean estimate after calculate_denoised
loss    = loss_fn(x0_pred, x0)    MSE, L1, Huber or SmoothL1
```

So it does not compare velocities at all. It compares clean estimates, whatever the model's type. On a flow model, x0_pred = x_t − σ·v̂, so with MSE the loss equals σ² × velocity loss. The lab confirms that exactly. Low noise levels count for very little.

Its noise levels come from `_generate_batch_sigmas`: `percent_to_sigma` of a uniform random number. On a flow model with shift 3, that bends the draw so half of all samples have σ above 0.75.

The same arithmetic applies to a noise-prediction model, where x0_pred = x − σ·ε̂, so this trainer's weight on noise error is σ² there too. That's a design choice, and we can't tell you from reading it whether it helps or harms. Training a LoRA with these nodes is covered in the LoRA track.

## What goes wrong

- **Waiting for the loss to approach zero.** It won't. The lab's small model settles at 2.20, and its floor is 2.19. That model works.
- **Comparing loss numbers between trainers.** Velocity loss, clean-latent loss and noise loss are different sizes on the same model. In the lab, one perfect model scores 1.92 and 0.48 at the same t.
- **Getting the direction of t backwards.** Here t = 1 is noise. Some papers run the other way, and then v changes sign. Check before you copy a formula.
- **Ignoring t when reading errors.** A good average can hide a poor fit at one end, since that end may carry little weight in the loss you're watching.
- **Assuming a straight target means straight sampling.** Each pair is straight. The field isn't. See CU-204.
- **Forgetting shift when you resume or sample.** Training with one shift and sampling with another moves the noise levels in use. That is legal, and worth knowing about.

## Lab

One pair first. The target is the same at all t, and `x_t − t v` returns x₀ every time.

```text
one pair: x0 1.5, noise -0.7
t     x_t      target v  x_t - t v  (the CONST.calculate_denoised formula)
0.1   +1.280   -2.200    +1.500
0.5   +0.400   -2.200    +1.500
0.9   -0.480   -2.200    +1.500
```

Now the floor, on a mixture where the perfect model has a formula. The last column is what a model that ignores x would score.

```text
t     floor (perfect model)  constant guess
0.05  1.0914                 3.7710
0.2   1.1554                 3.7710
0.5   1.9241                 3.7710
0.8   3.6701                 3.7710
0.95  3.0493                 3.7710
```

At high t the point on the line says almost nothing about x₀, so a perfect model only beats a constant by a little.

```text
t     clean-latent error (t x 0.1)   noise error ((1 - t) x 0.1)
0.05  0.005                          0.095
0.5   0.050                          0.050
0.95  0.095                          0.005
```

ComfyUI's loss against velocity loss, with one perfect model at the same t:

```text
sigma  velocity loss  clean-latent loss  ratio  sigma^2
0.2    1.1554         0.0462             0.040  0.040
0.5    1.9241         0.4810             0.250  0.250
0.8    3.6701         2.3489             0.640  0.640
```

How often each noise level is drawn. Logit-normal puts more in the middle. Core's trainer with shift 3 leans high.

```text
sampling                                  t<0.25   0.25-0.75  t>0.75
uniform                                   0.249    0.501      0.250
logit-normal m 0, s 1 (Esser et al.)      0.136    0.729      0.135
uniform through shift 3 (core's trainer)  0.100    0.401      0.499
```

Then a real small training run, on the per-pair target.

```text
floor of the loss averaged over uniform t: 2.190
step   running velocity loss
500    2.345
1000   2.230
2500   2.201
32 Euler steps from that model: W1 to the data 0.057, two real samples of this size differ by 0.007
```

The loss flattens just above the floor, and the model samples close to the data. A small remaining gap in sampling is not visible in the loss, which is another reason not to judge a model by its loss alone.

## Sources

- [Lipman et al. 2022. Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747)
- [Esser et al. 2024. Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_train.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_train.py)
