# CU-101 - What generative AI actually is

**Objective.** Say what a generative model is in one sentence, and tell learning a distribution from memorising data, with numbers. Taught by Professor Latent.

## The idea

A generative model learns the distribution your data came from, then draws new samples from it. That is the whole job. Everything else in this university is about how to do that for something as large as an image.

Three plain words are doing the work there.

- **Distribution.** A description of which things are likely. Out of all possible grids of pixels, nearly all are static, and the tiny share that look like photographs is what we'd like to describe.
- **Learn.** Adjust a large pile of numbers, the weights, until the model gives high likelihood to real examples.
- **Sample.** Use those numbers to draw a new example. Draw again and you get a different one.

So a picture from a model is a draw and not a lookup. Three questions tell models apart. How many numbers does it store? Do its samples look like the data? Can it assign a sensible probability to data it never saw?

{{play:fitgap}}

## The mechanism

Take a dataset drawn from an unknown distribution p(x). Fit a model p_θ(x), which means choosing parameters θ that make the data likely:

```
θ* = argmax_θ  E_(x~data) [ log p_θ(x) ]
```

Then sample x ~ p_θ. The usual test is the log-likelihood on data held back from training, since a model that only memorised scores well on the training set and fails on new data.

The lab fits one model by expectation-maximisation (Dempster, Laird, Rubin 1977), which is the classic recipe for mixtures: assign each point softly to a component, refit the components, and repeat.

## In ComfyUI

The file you download holds θ: the weights. `Load Checkpoint` reads numbers from it, and it doesn't fetch stored pictures. The KSampler draws a sample: it starts from noise made with your seed, and calls the denoiser again and again to walk that noise towards something likely (CU-202).

{{graph:sd15_txt2img}}

Here's one such draw, on our test machine, from one prompt and one seed.

![An SD 1.5 sample of a brass astrolabe on a wooden table, seed 424242](sampling_lab/sampler-euler.jpg)

Three ideas from the toy carry straight over.

- **A prompt narrows the distribution.** The model is trained on pictures with text, so it learns which pictures are likely given some words. Your prompt says which part of the distribution to draw from (CU-104). A different seed is a different draw from that same part.
- **Running isn't learning.** The sampler runs inside `torch.inference_mode`. Queue a thousand times and the weights don't change. Changing them takes training, and that's the lora-training track.
- **Weights set the limit.** The sample comes from what the weights hold, your prompt and your seed. A model can only draw what it learned, which is why a model family and its training data matter more than any setting.

## What goes wrong

- **Thinking the same prompt should give the same picture.** It's a new draw each time unless the seed is fixed. CU-105 says exactly what a seed holds still.
- **Thinking the model looks things up.** It has no gallery and no internet. A subject it rarely saw in training tends to come out vague or wrong, and a better prompt can't always fix that. We state this from the idea and didn't test it. Try another model, or train a LoRA.
- **Judging a model by a few good samples.** The lab's copier looks excellent by distance and has learned nothing. One striking picture is one draw.
- **Saying a model can't copy.** See below. It's not a database, and it isn't proven free of copying either.
- **Blaming the blur on settings.** The one-Gaussian model puts a third of its samples in the empty gap, and no setting can fix that because it has too few numbers. Some limits are in the model.
- **Expecting a model to improve with use.** Nothing you do at Queue updates it.

## Lab

Three models learn from the same 2000 points of a two-humped distribution, and the true distribution is known, so we can grade them.

```text
fitted mixture: weights 0.308 0.692  means -2.020 1.485  stds 0.301 0.496   truth: .300 .700  -2.000 1.500  .300 .500
```

Expectation-maximisation found the truth from data alone, with five free numbers.

```text
model        numbers stored  new samples  W1 to truth  log-likelihood on unseen data
copier       2000            0.000        0.0665       undefined: it gives unseen values no density
one Gaussian 2               1.000        0.6521       -1.9255
mixture      5               1.000        0.0612       -1.1826
the truth itself                                       -1.1812
```

Read this table slowly, as it contains the whole subject.

- **The copier** looks excellent by distance (W1, lower is better), but none of its samples are new. Sample quality alone does not show that a model has learned anything.
- **One Gaussian** makes new samples and is wrong: it has too few parameters.
- **The mixture** makes new samples, matches the distance of the copier, and scores nearly the same as the truth on unseen data, using five numbers in place of 2000.

The Gaussian's mistake is concrete:

```text
share of one-Gaussian samples in the empty gap between the modes (-1 < x < 0.5): 0.326   truth: 0.016
```

A third of its samples land where the data almost never goes. This is what an underfit model looks like: blur between things that are really separate.

```text
why images need more: a 512x512 RGB image has 256^(3*512*512) possible values, a number with 1,893,916 digits
```

You cannot tabulate that, which is why deep networks are used, and why most of them work in a compressed space (CU-201).

## What is contested

How much do real image models memorise? They do not store images as files, but "not a copier" does not mean "never copies". Carlini et al. (2023) extracted some training images from Stable Diffusion, mostly ones duplicated in the training data, and Somepalli et al. (2022) studied replication too. So do not claim that a model cannot reproduce its training data. How much this happens depends on the model and the data.

## Sources

- [Dempster, Laird, Rubin 1977. Maximum Likelihood from Incomplete Data via the EM Algorithm](https://doi.org/10.1111/j.2517-6161.1977.tb01600.x)
- [Carlini et al. 2023. Extracting Training Data from Diffusion Models](https://arxiv.org/abs/2301.13188)
- [Somepalli et al. 2022. Diffusion Art or Digital Forgery? Investigating Data Replication in Diffusion Models](https://arxiv.org/abs/2212.03860)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy/sample.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sample.py)
