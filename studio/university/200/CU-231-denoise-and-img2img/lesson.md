# CU-231 - Denoise and image to image

**Objective.** Work out where a denoise value starts on the schedule, explain why it costs the same as a full run, and pick a value by what you want kept. Taught by Dr. Denoise.

## The idea

Text to image starts from pure noise and walks all the way down. Image to image starts from your picture, adds some noise, and walks down from there. Denoise decides how much noise that is.

So denoise is not a strength dial on the model. The model does the same job at each noise level as it always does. What changes is how much of your picture is still readable when it starts. Add a little noise and the model can only touch fine detail. Add a lot and it can repaint the whole thing.

{{graph:sd15_img2img}}

## The mechanism

`KSampler.set_steps` in `comfy/samplers.py` does the whole trick in three lines:

```
new_steps = int(steps / denoise)
sigmas    = schedule with new_steps steps
sigmas    = the last (steps + 1) values
```

With 20 steps and denoise 0.5 it builds a 40-step schedule and runs the last 20. You still run 20 steps. They are just packed into the low-noise end, closer together.

Then the noise goes in, in `noise_scaling`:

```
denoise below 1   x = latent + σ · noise
at the very top   x = latent + √(1 + σ²) · noise
flow model        x = (1 − σ) · latent + σ · noise
```

Look at the top line: the latent is always in the sum. The middle line is chosen by `max_denoise`, which asks whether the first sigma is the model's largest. So even at denoise 1 your picture is still in there, under a great deal of noise.

## Try it

Move the slider and watch which noise levels are kept. The bright lines run. The dim ones are built and thrown away.

{{play:denoise}}

## How to choose

Start from what you want kept. These ranges are common starting points, not measurements of ours, so test them on your own picture.

- Keep the layout and fix surface detail: try a low value, such as 0.2 to 0.4.
- Keep the layout loosely and change the look: try the middle, such as 0.5 to 0.7.
- Keep little more than the colours: try 0.8 and above.

The scheduler changes what any number means. At denoise 0.5 and 10 steps, `karras` starts at σ 1.091 and `simple` at σ 1.613. If you change scheduler, retune denoise.

## What goes wrong

- **"Denoise 0.1 should be fast."** It runs all your steps. If you want a quick touch-up, lower the steps too.
- **Denoise 0 and nothing happens.** The schedule is empty and the sampler hands the latent back. It is not an error.
- **Low denoise leaves a soft, unfinished look.** There were few levels to work with and the picture's own errors stay. Raise it a little before you add steps.
- **The result is still your picture at denoise 1.** Only a trace, but the latent is in the sum. For a clean start, feed an `EmptyLatentImage`.
- **Denoise means something else on another node.** `BasicScheduler` follows the same rule as KSampler and keeps your step count. `AlignYourStepsScheduler` and a few others run round(steps × denoise) steps instead. So 0.5 at 20 steps is 20 steps on one node and 10 on another.
- **Your picture was a different size from what the model likes.** `VAEEncode` keeps its size, so large pictures cost more memory. Scale first (CU-116 and CU-217).

## Lab

The first table is the arithmetic above, at 20 steps with karras on the SD 1.5 sigma table. We checked these starting points against ComfyUI's own `KSampler` class.

```text
denoise  schedule built  steps run  starts at sigma  sigma / sqrt(1 + sigma^2)
1.0      20              20         14.6146          0.998
0.75     26              20         5.0331           0.981
0.5      40              20         1.1817           0.763
0.25     80              20         0.2311           0.225
0.1      200             20         0.0715           0.071
```

Denoise is not linear in noise. Going from 1 to 0.75 only moves the last column from 0.998 to 0.981, because the schedule spends most of its range at very high σ. All the action in that column is between 0.5 and 0.1. That is why denoise 0.9 and 1 can look so alike.

```text
same denoise 0.5, other schedulers start at: karras 1.091   simple 1.613
denoise 0 gives 0 sigmas, and the sampler hands back the latent untouched
Align Your Steps style at 20 steps, denoise 0.5: runs 10 steps; BasicScheduler runs 20
schedule length for denoise 0.50, 0.49, 0.48 at 20 steps: [40, 40, 41]
```

The last line is the truncation in `int()`: nearby values can give exactly the same run.

Now a real image to image run on a toy. There are two subjects, one on each side, and a perfect denoiser. Every sample starts as the left subject.

```text
denoise  start sigma  still the left subject  mean distance moved
0.1      0.071        1.000                   0.056
0.25     0.231        0.999                   0.153
0.4      0.640        0.953                   0.319
0.5      1.182        0.837                   0.574
0.6      2.158        0.710                   0.865
0.75     5.033        0.592                   1.136
0.9      9.759        0.546                   1.241
1.0      14.615       0.529                   1.278
```

Low values only polish. Between about 0.4 and 0.75 samples start to change subject, and the picture is free to become something else. Those exact values belong to this toy.

```text
the latent is still in the sum at denoise 1: left share 0.529 against 0.497 from an empty latent
noise multiplier at full denoise: 14.6488   sigma itself: 14.6146
```

The trace at the top is real but small: 52.9% stay left, against 49.7% from an empty latent, on 20,000 samples. CU-202 explains why SD 1.5's schedule leaves a trace at its noisiest level.

## Sources

- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_custom_sampler.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_custom_sampler.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_align_your_steps.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_align_your_steps.py)
