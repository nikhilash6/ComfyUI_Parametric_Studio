# CU-506 - History 6: Denoising diffusion arrives (DDPM, 2020)

**Objective.** Place the DDPM paper in its history, check its posterior and its loss algebra against exact answers, say precisely what the simplified loss throws away, and find the paper's sampler in ComfyUI's list. Taught by Dr. Denoise.

## The idea

Diffusion had two parents. Sohl-Dickstein et al. (2015) proposed to "systematically and slowly destroy structure in a data distribution" and then learn the reverse. Song and Ermon (2019) perturbed data with several levels of Gaussian noise and estimated the gradient of the density at each level. Ho, Jain and Abbeel posted "Denoising Diffusion Probabilistic Models" on 19 June 2020. Their abstract credits "a novel connection between diffusion probabilistic models and denoising score matching with Langevin dynamics", and the introduction calls that equivalence one of their primary contributions.

The recipe was T = 1000 steps, noise variances β rising linearly from 10⁻⁴ to 0.02, and a U-Net with self-attention at 16×16 resolution, 35.7 million parameters for CIFAR10. On CIFAR10 they report an Inception score of 9.46 and a "state-of-the-art FID score of 3.17". Their comparison table lists an unconditional GAN, StyleGAN2 with ADA (v1), at 3.26. Sampling a batch of 256 CIFAR10 images took 17 seconds on a TPU v3-8. Dr. Denoise's question, what is the noise level at this step, now had 1000 answers.

The paper is frank about likelihood: "our models do not have competitive log likelihoods". L_simple scores at most 3.75 bits per dimension on CIFAR10, against 3.03 for Gated PixelCNN and 2.80 for Sparse Transformer in the same table, and "the majority of our models' lossless codelengths are consumed to describe imperceptible image details". The abstract also says the models admit a progressive decompression "that can be interpreted as a generalization of autoregressive decoding", which links this lesson to CU-503.

## The maths

CU-202 gave the forward chain and its closed form. The new ingredient is the posterior of one forward step given the clean data (eqs. 6 and 7):

```
q(x_(t−1) | x_t, x_0) = N( μ̃_t(x_t, x_0), β̃_t · I )
μ̃_t = √ᾱ_(t−1) · β_t / (1−ᾱ_t) · x_0  +  √α_t · (1−ᾱ_(t−1)) / (1−ᾱ_t) · x_t           β̃_t = (1−ᾱ_(t−1)) / (1−ᾱ_t) · β_t
```

The model's reverse step is N(μ_θ, σ_t² I), and one term of the variational bound is (eq. 8)

```
L_(t−1) = E[ ‖ μ̃_t(x_t, x_0) − μ_θ(x_t, t) ‖² / (2σ_t²) ] + C
```

Put x_0 = (x_t − √(1−ᾱ_t) · ε) / √ᾱ_t into μ̃_t and it becomes (x_t − β_t / √(1−ᾱ_t) · ε) / √α_t (eq. 10). So let the network predict ε and set μ_θ = (x_t − β_t / √(1−ᾱ_t) · ε_θ) / √α_t (eq. 11). The term turns into (eq. 12)

```
β_t² / ( 2σ_t² α_t (1−ᾱ_t) )  ·  ‖ ε − ε_θ( √ᾱ_t x_0 + √(1−ᾱ_t) ε, t ) ‖²
```

and the simplified loss (eq. 14) keeps ‖ε − ε_θ‖² and drops the weight in front. That makes it, in the authors' words, "a weighted variational bound", one that "down-weight[s] loss terms corresponding to small t". Sampling (Algorithm 2) is x_(t−1) = (x_t − β_t / √(1−ᾱ_t) · ε_θ) / √α_t + σ_t z, which "resembles Langevin dynamics with ε_θ as a learned gradient of the data density". For σ_t² the paper tried β_t, optimal if the data are N(0, I), and β̃_t, optimal if the data are one point. Both "had similar results".

## In ComfyUI

- **The sampler.** `ddpm` is in the sampler list in `comfy/samplers.py`. It calls `sample_ddpm`, which runs `DDPMSampler_step` in `comfy/k_diffusion/sampling.py`. The mean is eq. 11, and the noise it adds has variance (1−α)(1−ᾱ_prev)/(1−ᾱ), which is β̃_t, so ComfyUI took the paper's second choice. It reads ᾱ from sigma as 1/(1+σ²) and α as ᾱ/ᾱ_prev. On a shortened schedule one step therefore spans several of the paper's.
- **The schedule.** The paper's linear β is the branch named `"sqrt_linear"` in `make_beta_schedule` (`comfy/ldm/modules/diffusionmodules/util.py`), and the defaults there, 1e-4 and 2e-2, are the paper's constants. The branch named `"linear"` squares a linspace of square roots. That is the default in `ModelSamplingDiscrete`, with 0.00085 and 0.012, and it is the schedule of SD models, not of the DDPM paper.

## Lab

Everything here has an exact answer. First the posterior: Bayes' rule on a fine grid (x_0 = 0.8, ε = 0.7) against the closed form and against the ε form of the mean.

```text
t      mean by Bayes   closed-form mean   mean from eps (eq. 10)   variance by Bayes   beta-tilde_t
2      0.804680        0.804680           0.804680                 5.4532e-05          5.4532e-05
50     0.903556        0.903556           0.903556                 1.0372e-03          1.0372e-03
500    0.893374        0.893374           0.893374                 1.0031e-02          1.0031e-02
1000   0.698084        0.698084           0.698084                 2.0000e-02          2.0000e-02
```

Next the algebra from eq. 8 to eq. 12, on random data, noise and a random "network output", then the weights it produces.

```text
largest difference between the two sides of eq. 12 over 10000 random cases: 4.3e-11, while the terms reach 3.3
```

```text
t       weight in the bound   weight in L_simple   L_simple / bound
1       0.50005               1                    2.0
10      0.07372               1                    13.6
100     0.01008               1                    99.2
500     0.00550               1                    181.7
1000    0.01020               1                    98.0
```

The bound weighs the ε error by 0.50005 at t = 1 and by 0.0102 at t = 1000, and by 0.0055 near t = 500, so the weight per step is highest at the smallest t. L_simple weighs every t by 1. Relative to the bound, then, it multiplies the term at t = 1 by 2.0, at t = 10 by 13.6 and at t = 100 by 99.2, which is the paper's "down-weight loss terms corresponding to small t". The lab cannot say whether that is why samples improve. That needs images.

Last the two reverse variances. For Gaussian data N(0, s²) the exact reverse variance is known, and the table gives it as a fraction of β_t.

```text
t       beta_tilde / beta   exact reverse variance / beta_t if the data have std 0 (a point), 0.5, 1
2       0.4547              0.4547  0.9996  1.0000
5       0.7431              0.7431  0.9995  1.0000
10      0.8528              0.8528  0.9992  1.0000
50      0.9639              0.9639  0.9971  1.0000
500     0.9991              0.9991  0.9994  1.0000
1000    1.0000              1.0000  1.0000  1.0000
```

For a point (s = 0) it equals β̃_t exactly, and for unit variance it equals β_t exactly, as the paper says. For data of standard deviation 0.5 it is within 0.3% of β_t at every t shown. The two choices differ only at the smallest t: β̃_t is 0.4547 of β_t at t = 2, 0.9639 at t = 50 and equal to it to three digits by t = 500. That is why the paper found "similar results".

## What is contested

The "state-of-the-art" claim rests on one benchmark. Its margin over the unconditional GAN in the paper's own table is 0.09 FID (3.17 against 3.26), and the same table lists a conditional StyleGAN2 with ADA at 2.67.

Why the simplified loss helps is the authors' explanation, backed by one ablation. In their Table 2, ε prediction with the true bound's weighting and fixed variance gave an FID of 13.51, and L_simple gave 3.17. The lab cannot reproduce that, since it needs images. Weighting remains an open question, and CU-202 names later work on it.

Do not read "diffusion models have bad likelihoods" as a law. It is the paper's result for its own model and loss on CIFAR10.

## Sources

- [Ho, Jain, Abbeel 2020. Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239)
- [Sohl-Dickstein, Weiss, Maheswaranathan, Ganguli 2015. Deep Unsupervised Learning using Nonequilibrium Thermodynamics](https://arxiv.org/abs/1503.03585)
- [Song, Ermon 2019. Generative Modeling by Estimating Gradients of the Data Distribution](https://arxiv.org/abs/1907.05600)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/util.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/util.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
