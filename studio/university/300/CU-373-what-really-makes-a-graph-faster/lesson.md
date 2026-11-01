# CU-373 - What really makes a graph faster

**Objective.** List what really speeds up a graph, say what each lever costs, and report a speed-up only after measuring it on your own graph. Taught by Tinker Tune.

## The rule first

**If you didn't measure it on your graph, you don't know.** Speed claims travel well and apply badly. A number from someone else's card, model and step count tells you what to try, not what you'll get. That goes for this lesson as well, so most numbers below are counts, and the few timings are labelled.

A fair measurement is simple:

1. Same graph, same seed, same size, on an otherwise idle machine.
2. Change one thing.
3. Leave out the first run, which includes loading.
4. Run each side at least three times, and take the median.
5. Look at the picture. A faster wrong answer isn't faster.

## The levers, biggest first in most graphs

**A distilled model, or a distilled LoRA.** Fewer steps and often CFG 1, so the biggest count saving there is: 40 calls down to 4. It costs the look of that model, plus a new set of settings to learn. CU-308 explains how they are trained.

{{graph:d_lcm}}

**CFG 1 when the model allows it.** Half the calls for free, on models made for it. On a model that wants guidance, the picture falls apart. Don't do this on a normal model and call it speed.

**Smaller latents.** A step's cost goes with area at least, so 768 px costs a little over half of 1024 px, and 512 px costs a quarter. Generate small, then upscale only what you keep. Attention's cost grows faster than area, so the saving can be larger than this.

**Fewer steps.** Fine until the picture breaks. Find the knee by looking at results at 10, 15, 20, 30, for your model and sampler.

**A step cache.** `EasyCache` skips model calls where little is changing. It's an approximation, so inspect results. It helps most at high step counts. The one figure we have is from our own process notes: one video graph at 40 steps went from 419 s to 189 s. It is one graph, and it is why you should try it, not what you should expect.

{{graph:g_easycache}}

**Cached conditioning.** Text encoding happens once for a prompt anyway, thanks to the node cache, so this only matters across restarts or when a huge encoder is what you're fighting. `SaveConditioning` writes a prompt's result to a safetensors file. Move it to `models/embeddings` and `Load Conditioning` feeds a sampler with no encoder in the graph at all. It doesn't make sampling any faster. It saves the encoder's load and its memory.

{{graph:g_cond_save}}

**Tiled VAE.** This one surprises people: it isn't a speed-up. It trades time for memory. Each tile is smaller, but `decode_tiled_` decodes with three different tile shapes and averages them, so it does far more decodes. Use it because a decode doesn't fit, or falls back anyway. If your normal decode fits, tiled is slower.

{{graph:sd15_tiled_vae}}

## Which part to attack

Before choosing, split your run into stages. Use this to see why it matters. A huge improvement on a small stage is a small improvement.

{{play:amdahl}}

## What goes wrong

- **Comparing a first run with a second.** Our own Sampling Lab shows a 66 s first render and many at 1.5 s after it. That difference is loading, not sampling.
- **A timer too coarse for the job.** Those same renders were polled every 1.5 s, so they can't rank samplers. Check your clock is finer than the thing you're comparing.
- **Stacking three levers, and crediting one.** Change one, measure, then the next.
- **Tiled VAE everywhere "for speed".** See above. It's for memory.
- **A smaller format to go faster.** Smaller storage isn't necessarily faster computing. Formats your card can't compute natively get dequantized at each use. Check the `Native ops` line.
- **Reporting only the clock.** Say what the picture did too.

## Lab

Real timings first: six of the 44 renders in `renders.json` in our Sampling Lab, picked to show the first run. One graph family, one seed, polled every 1.5 s, and other renders in that file read 3 s or more.

```text
timed renders of one graph on our test machine, from sampling_lab/renders.json, seconds
  sampler-euler (first render of this model)    66.0
  sampler-euler_ancestral                        1.5
  sampler-heun                                   1.5
  sampler-dpmpp_2m                               1.5
  sampler-ddim                                   1.5
  sampler-lcm                                    1.5
  mean 12.2 s, median 1.5 s. The first run measures the loader.
```

```text
measure on identical terms: with the polling used there, 1.5 s is the smallest step a timing can show, so these renders can't rank samplers
```

Counting what each lever changes. These are counts, not seconds:

```text
what each lever changes, by counting. One image, SD-like, baseline 20 steps at CFG 7, 1024 px
  baseline                               calls x cells =   655360   100.0% of baseline
  distilled: 4 steps, CFG 1              calls x cells =    65536    10.0% of baseline
  fewer steps on a normal model: 10      calls x cells =   327680    50.0% of baseline
  smaller latent: 768 px                 calls x cells =   368640    56.2% of baseline
  smaller latent: 512 px                 calls x cells =   163840    25.0% of baseline
  cached prompt: no change to sampling   calls x cells =   655360   100.0% of baseline
```

A cached prompt saves nothing on this count because it doesn't touch sampling. Now tiling, with `get_tiled_scale_steps` ported from `comfy/utils.py`:

```text
tiled VAE: get_tiled_scale_steps, ported. Memory falls with the tile, passes rise
  a 1024 px image is a 128 x 128 latent. decode_tiled_ decodes three times, with tiles of three shapes, and averages
  tile 64, overlap 16:  23 tile decodes, each 25.0% of the whole latent's cells
  tile 64, overlap 8:  19 tile decodes, each 25.0% of the whole latent's cells
  tile 32, overlap 8: 115 tile decodes, each  6.2% of the whole latent's cells
```

Twenty-three decodes, each a quarter the area, instead of one decode of the whole. That's the memory bought and the time paid. The one cache figure we have:

```text
from our own process notes, not re-run here: one video graph, 40 steps, core EasyCache at 0.2 / 0.15-0.95: 419 s to 189 s
  that is 2.22 times faster on that graph, and we have no number for any other
```

And what a report should say:

```text
an honest small report
  graph, seed, steps, card, what changed, first run left out, three runs each, median, and did the picture change?
```

## Sources

- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_cond.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_cond.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_easycache.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_easycache.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
