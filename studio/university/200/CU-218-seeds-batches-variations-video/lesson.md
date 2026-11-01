# CU-218 - Seeds, batches and variations in video

**Objective.** Say exactly what a ComfyUI seed fixes, predict which changes to the batch, the frame count or the resolution keep the starting noise and which destroy it, and explain why an interpolated noise has to be rescaled. Taught by Reel Rascal.

## The idea

A seed is not a picture, and it is not a video. It starts a random number generator, and ComfyUI uses that generator once, to fill the starting latent with Gaussian noise. Which number lands at which position depends on the order in which the numbers are drawn and on the memory layout of the latent. So the noise stays the same only while the latent's shape stays the same. A video latent has a time axis as well as a batch axis, which makes this easy to get wrong.

## The maths

Every number of the starting noise is an independent draw from N(0, 1). Two independent noises of n numbers have a sample correlation of size about 1/√n, which is tiny for a whole frame of a video latent. So the noise of one frame carries no information about the next, and the lab measures how little.

A "variation" needs noise that is related to the old noise. The obvious recipe is linear interpolation of two noises a and b. If they are nearly orthogonal and have equal size, the result (1 − t) a + t b is shorter than either by a factor √((1 − t)² + t²), which is 0.707 at t = 0.5. The sampler assumes the noise has unit variance at its starting noise level σ (CU-202), so a short noise is a mismatch. Spherical interpolation keeps the size:

```
slerp(a, b; t) = ( sin((1 − t) θ) · a + sin(t θ) · b ) / sin θ          θ = angle between a and b
```

For two vectors of equal length its length is the same as theirs at every t.

## In ComfyUI

**From seed to noise.** `common_ksampler` in `nodes.py` calls `comfy.sample.prepare_noise(latent_image, seed, batch_inds)`. That function calls `torch.manual_seed(seed)` and then `torch.randn` with the generator, on the CPU in float32, once for the whole latent, and converts the result to the latent's dtype. The seed widget accepts 0 to 0xffffffffffffffff, and `RandomNoise` in the custom-sampling nodes has the same range.

**Batches.** If the latent carries a `batch_index`, `prepare_noise_inner` draws one item at a time up to the highest index wanted and keeps the ones asked for, so item i is the i-th draw. `LatentFromBatch` writes that index when it cuts items out of a batch, which is how an image can be redone alone with the noise it had in the batch. `LatentBatchSeedBehavior` has two modes. In "fixed", the default, it sets `batch_index` to the first item's index for every item, so all items start from the same noise. In "random" it removes the field.

**Ancestral and SDE samplers** (CU-207) add noise at every step. That noise comes from `default_noise_sampler` in `comfy/k_diffusion/sampling.py`, a generator on the same device as the latent, seeded with the seed, plus one when the latent is on the CPU. On a GPU it is the GPU's generator and not the CPU's.

**No variation node.** A search of `comfy/`, `comfy_extras/` and `nodes.py` finds no node that interpolates noise. The only slerp is `bislerp`, one of the latent resize methods in `comfy/utils.py`. A variation is not a built-in feature.

## Try it

Keep the seed. Change the shape. See how much of the old noise is still in the same place.

{{play:seedlayout}}

The seed in a real graph is one input on one sampler node. In this Wan graph, find `seed` on the `KSampler`. Nothing else in the graph holds a seed, and the frame count in `Wan22ImageToVideoLatent` above it decides how that noise is laid out.

{{graph:wf_wan22_t2v}}

## Lab

The lab reproduces `prepare_noise` on small and Wan-sized latents. First the draw, and a surprise about the seed:

```text
latent [1, 16, 21, 60, 104]: 2,096,640 numbers, mean -0.0003, std 0.9999

seed 5 against seed 5 + 2^32: identical noise True;  against 5 + 2^63: True;  against 6: False
```

Seeds that differ by a multiple of 2^32 give the same noise on this PyTorch build, so the 64-bit seed widget has only 2^32 distinct noises behind it. We observed this and did not read the cause in PyTorch's source. It fits a 32-bit generator state. Now batches, with the same seed, for four latent shapes:

```text
batch of 4, same seed 7:   item 0 equals the noise of a batch of 1   item 1 equals the second draw   one item redone with batch_index [2] equals item 2
  [4, 4, 64, 64]      16384 numbers per item   True                                      True                          True
  [4, 16, 5, 8, 8]     5120 numbers per item   True                                      True                          True
  [4, 3, 5, 7, 7]       735 numbers per item   False                                     False                         False
  [4, 4, 9, 9]          324 numbers per item   False                                     False                         False
LatentBatchSeedBehavior 'fixed' sets batch_index to [0, 0, 0, 0]: all four items identical: True
```

For ordinary latents, item 0 does not depend on the batch size, and redoing one item gives back its noise. That held in the lab for the two shapes whose item size is a multiple of 16 and failed for the two whose item size is not. We did not find out why, so treat the property as true for the usual latent shapes and not as a guarantee. Then video. The noise is laid out channel by channel, then frame by frame:

```text
same seed, 21 latent frames against 41: share of the 21-frame noise found unchanged in the 41-frame noise 0.0625  (channel 0 alone: 1.0000)
same seed, width 104 against 112: share unchanged 0.0000
correlation between the noise of adjacent frames, 20 pairs: mean -0.0004, largest in size 0.0065
```

Adding frames keeps only the first channel of the old noise, which is 1/16 of it, and changing the width keeps nothing. So the same seed with a different length or size is a different video. Adjacent frames have no correlation beyond chance. Last, interpolating two noises of 16,384 numbers each:

```text
angle between the two noises 89.9 degrees.   t      lerp: std  corr with a      slerp: std  corr with a
                                          0.1    0.908      0.994            1.003       0.988
                                          0.25   0.793      0.949            1.002       0.925
                                          0.5    0.708      0.709            1.000       0.709
```

The two methods stay equally close to a, but a linear blend has shrunk to a standard deviation of 0.708 at its middle, and the spherical one has not.

## What goes wrong

- **Same seed, slightly longer clip, a totally different video.** Expected. Only 1/16 of the noise stays in place on a 16-channel latent. To change the length and keep the shot, you need another method, such as a keyframe guide.
- **A comparison by seed misleads you.** Same seed at a different size or length is different noise. Keep both fixed when you compare settings.
- **All four items in a batch look identical.** `LatentBatchSeedBehavior` is on `fixed`, or you repeated one latent. Use `random` to get four different draws.
- **You can't reproduce a batch item alone.** Use `LatentFromBatch`, which keeps the index. Note the lab's warning about unusual latent shapes.
- **Same seed gives a different result with an ancestral or SDE sampler on another machine.** Those samplers add noise per step from a generator on the latent's device, so the device matters.
- **A blended noise looks soft or washed out.** Linear blending shrinks it to 0.708 of the size at the middle. Use slerp, or rescale. Core has no node for this.
- **Big seeds repeat.** On this build, seeds 2^32 apart gave the same noise. Don't expect more variety from larger numbers.

## What is contested

Whatever coherence a generated video has does not come from correlation in the starting noise, because there is none: ComfyUI draws the noise independently for every frame, and the model creates the coherence. Whether correlated noise would help is a research question: Ge et al. (2023) report that, when finetuning an image diffusion model for video, naively extending the image noise prior to video was sub-optimal and a designed prior was better. That is a different setting from today's video transformers, and ComfyUI's core does not use their prior. The observation about 32-bit seeds belongs to this PyTorch build's CPU generator. Another version or device may behave differently, and per-step noise on a GPU comes from a different generator altogether.

## Sources

- [Ge et al. 2023. Preserve Your Own Correlation: A Noise Prior for Video Diffusion Models](https://arxiv.org/abs/2305.10474)
- [ComfyUI v0.43.0, comfy/sample.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sample.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_latent.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_latent.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_custom_sampler.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_custom_sampler.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
