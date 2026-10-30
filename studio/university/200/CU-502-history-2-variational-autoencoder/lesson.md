# CU-502 - History 2: Variational autoencoders and the latent idea (2013)

**Objective.** Say what the 2013 paper added to variational inference, check its three pieces on a model where the exact answer is known, and see what the idea left unsolved. Taught by Professor Latent.

## The idea

On 20 December 2013 Kingma and Welling posted "Auto-Encoding Variational Bayes". Picture a room whose floor is the space of codes z. A decoder p(x|z) turns each spot on the floor into a picture. Training needs the reverse question, which spot did this picture come from, and for a neural-network decoder the posterior p(z|x) has no formula.

The abstract names two contributions. First, a reparameterisation of the variational lower bound gives an estimator that ordinary stochastic gradient methods can optimise. Second, for a dataset with a continuous latent variable per datapoint, inference becomes cheap if you fit a recognition model, one function q(z|x) shared by all datapoints, to the intractable posterior using that estimator. When the recognition model is a neural network, the paper says, "we arrive at the variational auto-encoder".

Rezende, Mohamed and Wierstra posted a closely related method on 16 January 2014. Kingma and Welling call it independent work, and Rezende et al. say the two approaches were "developed simultaneously".

## The maths

For any q the log-likelihood splits exactly into the lower bound L (eq. 3 of the paper) and a gap (eq. 2):

```
log p(x) = E_q[ log p(x|z) ] − KL( q(z|x) ‖ p(z) )  +  KL( q(z|x) ‖ p(z|x) )
                    L, the lower bound                   the gap, never negative
```

So L is tight exactly when q is the true posterior, and raising L over q moves q towards that posterior.

To train q by gradient you need the gradient of an expectation over q. The "usual (naive)" Monte Carlo estimator is f(z) · ∇ log q(z), which the paper says "exhibits very high variance". The reparameterisation writes z = g(ε, x) with ε drawn from a fixed distribution, for a Gaussian z = μ + σ·ε, so the gradient flows through f by the chain rule. The KL to a Gaussian prior can often be integrated analytically (appendix B), which leaves only the reconstruction term to sample. The paper's experiments used minibatches of M = 100 and one sample per datapoint.

## In ComfyUI

`VAEEncode` in `nodes.py` calls `vae.encode`, which reaches the encoder of an `AutoencoderKL`. These VAEs have `double_z` set, so the encoder ends in a `quant_conv` with twice the latent channels: for SD 1.x, 8 channels, which are 4 means and 4 log-variances. That is the paper's recognition model. `DiagonalGaussianDistribution` in `comfy/ldm/modules/distributions/distributions.py` splits them with `torch.chunk` and has the paper's draw, `sample()`, which returns mean + std · randn. But `AutoencoderKL` builds its `DiagonalGaussianRegularizer` with the default `sample=False`, which returns `posterior.mode()`, the mean. So VAE Encode in ComfyUI is deterministic: it computes the log-variance and drops it.

## Lab

The lab uses z ~ N(0, 1) and x given z ~ N(2z + 1, 0.5²). Then p(x) = N(1, 4.25) and the posterior is Gaussian with mean 2(x−1)/4.25 and standard deviation 0.2425, so every claim can be checked against the truth.

First the bound and its gap, for x = 2.5 and four choices of q. "Monte Carlo" is the mean of log p(x,z) − log q(z) over 10^6 reparameterised draws, and the lab asserts it agrees with the closed form to within four standard errors.

```text
log p(x) = -1.9071 for x = 2.5
q(z|x)            bound    Monte Carlo  gap      KL(q || p(z|x))
true posterior    -1.9071  -1.9071      0.0000   0.0000
shifted by 0.3    -2.6721  -2.6737      0.7650   0.7650
too wide          -8.4905  -8.5109      6.5834   6.5834
the prior        -12.7258 -12.7200     10.8187  10.8187
```

The gap equals KL(q ‖ posterior) in every row, and it is zero when q is the posterior. The last row is a q that ignores x altogether.

Second, two unbiased estimators of the gradient of L with respect to the mean of q, which is 0.3 away from the posterior mean. One differentiates through z = μ + σ·ε. The other is the score-function estimator the paper calls naive.

```text
std of q   exact gradient   reparameterised: mean    std     score function: mean    std     variance ratio
0.5000     -5.1000          -5.0981                8.498  -5.1038               17.451       4.2
0.2425     -5.1000          -5.1003                4.120  -5.0938               13.174      10.2
0.1000     -5.1000          -5.0976                1.701  -5.0480               26.284     238.6
```

Both agree with the exact −5.1000 on average, within noise. A single draw is another matter. The reparameterised standard deviation shrinks as q narrows, 8.498 to 1.701, but the score-function one does not (17.451, 13.174, 26.284), and its variance ends up 238.6 times larger. Training pushes q towards the posterior, whose standard deviation here is 0.2425, so the middle row is the one that matters: ten times the variance means ten times the batch for the same noise.

Third, amortised inference. One encoder N(a·x + b, σ²) serves every x and is trained only by the reparameterised bound, with M = 100 and one sample each. The last column is the average gap over 200,000 fresh x.

```text
encoder q(z|x) = N(a x + b, sigma^2)    a        b        sigma    mean gap log p(x) - bound
exact posterior                 +0.4706  -0.4706  0.2425   0.0000
learned, may use x              +0.4681  -0.4686  0.2432   0.0002
learned, ignores x              +0.0000  +0.0021  0.2428   7.9758
```

The learned encoder lands within 0.003 of the exact slope and offset, and the gap is 0.0002 nats. An encoder forbidden to look at x leaves 7.9758, because the posterior mean moves with x.

Last, the blur. Take two images whose edge is at pixel 3 or pixel 6, equally likely, and a decoder that cannot tell which it faces. For real-valued data the paper's decoder is Gaussian, so with a fixed variance its loss is squared error up to a constant.

```text
image A       0.00 0.00 0.00 1.00 1.00 1.00 1.00 1.00 1.00
image B       0.00 0.00 0.00 0.00 0.00 0.00 1.00 1.00 1.00
best output   0.00 0.00 0.00 0.50 0.50 0.50 1.00 1.00 1.00
largest jump between neighbouring pixels: best output 0.50, either real image 1.00
expected squared error: best output 0.75, a sharp image picked at random 1.50
```

Squared error rewards the average of the candidates, and the average is not a real image.

## What is contested

Do not say "the VAE made diffusion possible". Rombach et al. describe diffusion models as typically operating "directly in pixel space" and bring in an autoencoder to cut the cost. Their autoencoder is a compressor with what they call a "slight" KL penalty, trained with an adversarial loss. It borrows the 2013 machinery without being the 2013 model.

The blur is not a law of VAEs. In this lab it comes from asking for squared error from a decoder that is unsure. Rombach et al. blame pixel losses such as L2 or L1 for blur, and Larsen et al. say element-wise errors like squared error are "not very suitable for image data" and show plain VAEs blurring off-centre. How much of the blur in a real model is the loss and how much is the code is not settled by a toy.

The lab model is linear and Gaussian. It checks the mathematics, not how a deep decoder behaves on photographs.

## Sources

- [Kingma, Welling 2013. Auto-Encoding Variational Bayes](https://arxiv.org/abs/1312.6114)
- [Rezende, Mohamed, Wierstra 2014. Stochastic Backpropagation and Approximate Inference in Deep Generative Models](https://arxiv.org/abs/1401.4082)
- [Rombach et al. 2021. High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752)
- [Larsen et al. 2015. Autoencoding beyond pixels using a learned similarity metric](https://arxiv.org/abs/1512.09300)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/ldm/models/autoencoder.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/models/autoencoder.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/distributions/distributions.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/distributions/distributions.py)
