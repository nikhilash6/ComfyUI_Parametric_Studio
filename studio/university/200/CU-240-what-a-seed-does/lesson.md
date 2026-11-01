# CU-240 - What a seed does

**Objective.** Say what a seed fixes and what it does not, reproduce one image from a batch and know when that fails, and read a noise spectrum. Taught by Professor Latent.

## The idea

A latent is a grid in a small space, and the sampler starts by filling that space with random numbers. A seed picks which numbers. That is its entire job. It has no idea what's in your prompt, so a good seed for one prompt is not a good seed for another.

## On the CPU, and why

`prepare_noise` in `comfy/sample.py` is short:

```
generator = torch.manual_seed(seed)
noise = torch.randn(shape, dtype=float32, generator=generator, device="cpu")
```

The `device="cpu"` matters. Random number generators differ between CPU and GPU, so drawing on the CPU gives everyone the same starting noise, whichever card they own.

That is only the starting noise. A seed does not promise the same picture on another machine, for two reasons.

- **Samplers that add noise.** `default_noise_sampler` makes a new generator on the latent's own device, seeded with your seed (or seed + 1 on the CPU). So `euler_ancestral` draws its per-step noise on the GPU. Another kind of device draws different numbers. The `dpmpp_sde` family differs: its plain names use a Brownian tree on the CPU, and only the `_gpu` names use the device.
- **Floating point.** Different hardware and settings can round differently. Our test machine has one card, so we can't measure how much this matters.

## Batches

A batch is not several seeds. `batch_size` 4 draws one block of noise with four rows. Item 0 matches a single image with that seed. Item 1 does not match seed + 1.

To render just item 2 again, `LatentFromBatch` records `batch_index` in the latent. `prepare_noise` then draws the items one by one, keeps the ones you asked for and throws the rest away.

{{graph:b_batch_pick}}

This has a trap we found while writing this lesson. It only works if each item has a multiple of 16 values. A 512 by 512 SD latent has 16,384 values, so it works. A latent of 65 × 65 cells with 4 channels has 16,900, so the picked item comes out different from the one in the batch. Our guess is that torch fills large tensors in blocks of 16. We measured this, and did not read torch's source. Stay on widths and heights that are multiples of 16 pixels, and an SD latent has a multiple of 16 values. A 16-channel latent always does.

To get the same noise for every item, use `LatentBatchSeedBehavior` set to `fixed`. That is how you compare prompts fairly in one batch.

{{graph:b_batch_fixed}}

## Colours of noise

Noise has a spectrum: how much of it sits at each size, from big soft blobs to fine grain. **White** noise has the same power at every size. That is what ComfyUI draws by default, and our measurement agrees. Each of 16 bands holds its fair share, within about 6%.

Other colours tilt that balance. Some nodes in packs let you choose one. But names here are loose. We read one popular noise pack whose "blue", "green" and "pink" are one formula with different numbers, all of which reduce the high frequencies. Real blue noise rises with frequency, so its "blue" is the opposite. Trust a measured spectrum over a name.

{{play:spectrum}}

The Sampling Lab shows [core's measured spectra](#sampling/bench).

## What goes wrong

- **Same seed, different picture on another machine.** Check your sampler first. A noise-adding one draws on the device. For a closer match, try a deterministic sampler or a `dpmpp_sde` name without `_gpu`.
- **Same seed, a totally different picture at a new size.** A new shape is a new grid, so the numbers land in new places. A larger latent does start with the same values (the lab shows this), and they mean something different there.
- **Item 3 of a batch won't reproduce.** Make sure you used `LatentFromBatch` and not seed + 3. Then check the size is on the 16 grid, as above.
- **Saving a seed from another tool.** Other tools may draw their noise differently, so the number does not carry over.
- **A "lucky seed".** A seed that suits one prompt says little about another. Prompts and seeds act together.
- **Trying to multiply the empty latent to get more noise.** It is all zeros, and the noise is added later. CU-241 covers this.

## Lab

The lab copies `prepare_noise`. We checked the batch results against the real function.

```text
512x512 SD latent: values 16384  mean +0.0091  std 1.0040
seed 42 twice, identical: True   seeds 42 and 43, correlation: +0.0058
first three values, seed 0: [-1.1258, -1.1524, -0.2506]  seed 1: [-1.5256, -0.7502, -0.654]
same seed, 512x768 against 512x512, shared opening values: 16384 of 16384
```

The noise has mean near 0 and spread near 1. Neighbouring seeds are unrelated, so seed 43 is not "close to" seed 42. The last line shows the taller latent opening with the same 16,384 values as the shorter one.

```text
batch item 0 equals the single image with that seed: True
batch item 1 equals seed 43: False
shape                  values per item  multiple of 16  picked item equals the batch item
(4, 4, 64, 64)         16384            True            True
(4, 16, 128, 128)      262144           True            True
(4, 4, 65, 65)         16900            False           False
(4, 4, 66, 65)         17160            False           False
(4, 16, 65, 65)        67600            True            True
seed_behavior fixed, batch_index [0,0,0,0], all four the same: True
```

Now spectra, computed with a real FFT, eight bands, low frequency first.

```text
white, torch.randn              0.98  1.01  0.99  1.01  0.99  1.01  1.00  1.00
pink, power 1/f                 3.92  1.34  0.79  0.57  0.44  0.36  0.31  0.27
named blue by one pack, 1/f^2   7.25  0.42  0.15  0.07  0.04  0.03  0.02  0.02
real blue, power rises with f   0.16  0.39  0.62  0.87  1.11  1.37  1.61  1.86
```

The third row uses that pack's formula at its default. It has less high frequency than pink, while the fourth has what the word usually means.

```text
default_noise_sampler (torch.randn)    lowest 0.941  highest 1.017
BrownianTreeNoiseSampler increment     lowest 0.962  highest 1.018
default_noise_sampler seeds: on the CPU seed + 1 = 43 , on any other device seed = 42
```

Both of core's sources are white within the wobble you'd expect. A Brownian tree does not make noise a different colour. It makes the noise between two sigmas stay the same when you change step count (CU-207).

## Sources

- [ComfyUI v0.43.0, comfy/sample.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sample.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_latent.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_latent.py)
- [Reproducibility, PyTorch documentation](https://docs.pytorch.org/docs/2.15/notes/randomness.html)
