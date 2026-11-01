# CU-233 - Two samplers, one schedule: leftover noise

**Objective.** Wire two `KSamplerAdvanced` nodes so the second continues the first exactly, and recognise each way the hand-over breaks. Taught by Dr. Denoise.

## The idea

Sometimes you want one run done by two samplers. People do it to change solver part-way, to use a base model and then a refiner, or to look at a half-done latent. The job is to stop with the noise still in the latent, then carry on from precisely that noise level. If the numbers disagree, the second sampler is working from a false belief about how noisy its input is.

{{graph:sd15_two_stage}}

## The settings that matter

`KSamplerAdvanced` has four inputs a plain KSampler does not: `add_noise`, `start_at_step`, `end_at_step` and `return_with_leftover_noise`. It has no `denoise`. The two nodes' steps and scheduler must agree. Their seeds needn't, because a node with `add_noise` disabled doesn't use its seed.

| Setting | First sampler | Second sampler | Why |
|---|---|---|---|
| `steps` and `scheduler` | 20, karras | 20, karras | Together they define the one shared list of noise levels |
| `start_at_step` | 0 | 12 | Where each one begins on that list |
| `end_at_step` | 12 | 10000 | A number past the end means "to the end" |
| `return_with_leftover_noise` | enable | disable | Stop at σ, or jump to σ 0 at the end |
| `add_noise` | enable | disable | Only the first run adds noise |

`common_ksampler` and `KSampler.sample` do this:

- `end_at_step` cuts the list after that step. If leftover noise is off, the last kept value is overwritten with 0, so the last step jumps all the way to clean.
- `start_at_step` cuts the front of the list.
- `add_noise` disable makes the noise tensor all zeros. Then `noise_scaling` adds zero × σ, so the latent passes through unchanged.

So in a correct hand-over the first node stops at step 12 with noise of size σ₁₂ still in the latent. The second starts at step 12, adds nothing, and is told σ₁₂. Everyone agrees.

{{play:twostage}}

## What goes wrong

Every failing row of the lab table below is one of these.

- **Leftover noise off on the first.** It finishes to a clean result and jumps to σ 0 early. The second is then told σ₁₂ with no noise in the latent, so it removes noise that is not there. In the lab that is the largest W1 of the settings that keep 20 steps, though its RMS from one run is the smallest of the failing rows.
- **New noise on at the second.** The latent now has its old noise and a fresh one, so its noise is about √2 × σ₁₂ where the sampler assumes σ₁₂. In the toy the overall distribution survives, and each sample ends somewhere else, so you lose the match with a single run. Your seed on the second node now matters too.
- **Different step counts.** Step 12 of 30 is a different noise level from step 12 of 20. Here that is σ 2.07 against σ 0.565, and this row has the worst W1 in the table.
- **Different schedulers.** Same problem, by a different route. Compare the sigma lists before you trust it.
- **Different models with different sigma ranges.** Step 12 means whatever that model's scheduler says it means. Check both lists. If you hand from a noise-prediction model to a flow model, the two do not even use the same mixing formula (CU-242).
- **`start_at_step` past the end.** The latent comes straight back, with no error. If your second stage takes no time at all, check this first.
- **Noisy preview from the first stage.** Decoding a leftover-noise latent shows noise. That is what it is meant to contain.

## Leftover off, new noise on

One combination is a legal thing to want. First finish to a clean result, then add fresh noise and resample the end of the schedule. It is image to image by another route. It is not a continuation, so do not expect it to match a single run. The lab row marked "a restart" measures how far it lands.

## Lab

The lab copies the slicing rules from `KSampler.sample` and runs both stages with a perfect denoiser, 40,000 samples, on a toy. "RMS from one run" asks whether this is the same result as a single pass. "W1 to the true result" asks whether the whole set still looks right, against a 4,000-step reference.

```text
sigma at step 12: 0.5647
setup                                             RMS from one run   W1 to the true result
leftover on, new noise off, same steps            0.0000             0.0527
leftover OFF (first finishes, jumps to sigma 0)   0.2237             0.2127
new noise ON at the second                        0.4782             0.0554
second has steps 30, not 20                       0.4635             0.3821
leftover OFF and new noise ON (a restart)         0.5159             0.1212
one run, 20 steps, for reference                  0.0000             0.0527
```

The first row is zero for a reason: Euler's steps depend only on the current sample and σ, so cutting the run changes nothing. The two parts are the single run. A solver with memory is different, as the next lines show.

```text
leftover on: 1.121   expected from data and sigma: 1.176
leftover off: 0.831
```

Those are spreads of what the first stage hands over. With leftover on, the latent still has noise in it. Euler at this coarse step falls a little short of the expected value, as it has its own error. With leftover off the spread is below that of the data alone (1.032), because a one-step jump to clean pulls samples toward the average.

```text
dpmpp_2m split at step 12 against dpmpp_2m in one run: RMS 0.01662. Euler has no history: RMS 0.0e+00
euler then dpmpp_2m, W1 to the true result: 0.0444; euler all the way 0.0527; dpmpp_2m all the way 0.0092
start_at_step past the end hands the latent straight back: True
```

`dpmpp_2m` uses the previous step's prediction, and a second call starts with none. So a split is close to the single run, and not equal to it. Starting with Euler and finishing with `dpmpp_2m` landed between the two here. That is one toy, and it does not show that changing sampler helps a real picture.

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/sample.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sample.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
