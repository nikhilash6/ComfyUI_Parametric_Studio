# CU-232 - KSampler taken apart: SamplerCustomAdvanced

**Objective.** Rebuild a KSampler from its parts, name the one case where the two routes give different results, and use the parts for something the widget cannot do. Taught by Dr. Denoise.

## The idea

A KSampler bundles five decisions into one box. `SamplerCustomAdvanced` has exactly those five as sockets, and nothing else.

{{graph:sd15_custom}}

| Socket | Type | The question it answers | Usual node |
|---|---|---|---|
| noise | NOISE | What are the starting random numbers? | `RandomNoise` |
| guider | GUIDER | How do model calls become one prediction? | `CFGGuider` |
| sampler | SAMPLER | What is the rule for each jump? | `KSamplerSelect` |
| sigmas | SIGMAS | Which noise levels do the jumps land on? | `BasicScheduler` |
| latent_image | LATENT | Where do we start? | `EmptyLatentImage` |

Nothing new happens inside. Both routes end at `CFGGuider.sample` in `comfy/samplers.py`. The gain is that each part is now a wire, so you can replace, split or inspect it.

{{play:takeapart}}

## Why you would bother

- **See the schedule.** SIGMAS is a list of numbers on a wire. You can print it, and cut it with `SplitSigmas`. CU-235 and the `nm_sigmas` graph do this with no model at all.
- **Use a scheduler with its dials showing.** `KarrasScheduler` exposes rho and `BasicScheduler` does not. See the `sd15_karras_rho` graph.
- **Change the sampler's own settings.** `SamplerEulerAncestral` exposes eta and `s_noise`, and the sampler menu cannot.
- **Change guidance.** Put a different guider on the wire: `BasicGuider` for no CFG at all, `DualCFGGuider` for two conditionings. One run can even use one guider for the first half and another for the second.
- **Get the running estimate.** Both `SamplerCustom` and `SamplerCustomAdvanced` have a second output, `denoised_output`, the model's last estimate of the clean latent. KSampler has only the first.

`SamplerCustom` is the halfway house: it still takes model, seed, CFG and conditionings as plain inputs, and only the sampler and sigmas come in on wires.

## The one real difference

`KSampler` has a list called `DISCARD_PENULTIMATE_SIGMA_SAMPLERS`: `dpm_2`, `dpm_2_ancestral`, `uni_pc` and `uni_pc_bh2`. For those four it builds one extra step and then deletes the second to last sigma. `BasicScheduler` knows nothing about this. So the same names and the same numbers give two different schedules. The lab prints them.

## What goes wrong

- **Same settings, different picture, and the sampler is one of those four.** That is the difference above. It is not a bug in your graph. For a match, build the schedule with one more step and cut it the same way, or just use a sampler outside that list.
- **Two wires from the loader look wrong.** They are right. `CFGGuider` needs the model to predict, and `BasicScheduler` needs it to read the sigma range. If you patch the model with `ModelSamplingSD3` or similar, send the patched one to both. If the scheduler gets the unpatched one, its schedule is computed for the wrong shift.
- **`KarrasScheduler` with SD 1.5 numbers on another family.** It takes sigma_max and sigma_min as plain numbers and does not ask the model. Flow models use a range of about 0 to 1. Those numbers will be wrong, with no error.
- **`dpm_fast` or `dpm_adaptive` ignore your careful schedule.** They only use the ends of the list (and `dpm_fast` its length). That is in `ksampler()` in `comfy/samplers.py`.
- **`DisableNoise` by accident.** The sampler then starts from the latent as it is. That is correct when you continue a part-way latent (CU-233), and wrong for a fresh start.

## Lab

The lab writes the five parts as small functions, then builds KSampler from them the way the source does, with a perfect model on a toy.

```text
euler, 20 steps: KSampler and the four parts give identical numbers: True
```

Then the difference. For most samplers the two lists match. For `dpm_2` the KSampler route has moved its last sigmas up:

```text
euler  KSampler      0.0779 0.0485 0.0292
euler  BasicScheduler 0.0779 0.0485 0.0292
dpm_2  KSampler      0.1137 0.0744 0.0473
dpm_2  BasicScheduler 0.0779 0.0485 0.0292
dpm_2, same seed: RMS difference between the two routes 0.00269
```

Now something a KSampler cannot do: one run, cut at step 12 with `SplitSigmas`, and the guider changed at the cut.

```text
split at step 12: first half 12 steps, sigma 14.615 to 0.565; second half 8 steps, sigma 0.565 to 0.000
guider changed from cfg 7 to cfg 3 at that split: mean result +2.555, against +3.236 for cfg 7 throughout, RMS change 0.681
```

The cut shares one value, σ 0.565, so nothing is skipped or repeated. Lowering CFG for the last stretch pulled the result back from the overshoot in this toy. That is a demonstration of the wiring. It is not advice about real images.

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_custom_sampler.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_custom_sampler.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
