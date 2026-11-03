# CU-501 - History 1: GANs, the adversarial game (2014)

**Objective.** State the game that Goodfellow et al. defined, show why the best discriminator is a density ratio, and see where the theory holds and where real training only approximates it. Taught by Dr. Denoise.

## The idea

On 10 June 2014 Goodfellow and seven co-authors posted a way to train a generative model without writing down its density. Two networks play a game. The generator G turns random noise z into a sample. The discriminator D says how likely a sample is to come from the training data rather than from G. The paper's picture is counterfeiters against police, each forcing the other to improve.

Dr. Denoise would ask for the noise level at this step. Here there are no steps: z goes in once and one pass through G gives the sample. The paper lists "Markov chains are never needed" among its advantages.

## The maths

The game has a value function (the paper's eq. 1). D tries to make it large and G tries to make it small:

```
min_G max_D  V(D, G) = E_(x~data)[ log D(x) ] + E_(z~p_z)[ log( 1 − D(G(z)) ) ]
```

Let p_g be the distribution of the samples G(z). For a fixed G the best discriminator can be written down (Proposition 1), because at each x the function a·log y + b·log(1−y) peaks at y = a/(a+b):

```
D*(x) = p_data(x) / ( p_data(x) + p_g(x) )
max_D V(D, G) = −log 4 + 2 · JSD( p_data ‖ p_g )          (Theorem 1)
```

JSD is the Jensen–Shannon divergence, never negative and zero only when the two distributions are equal. So the generator's best possible score is −log 4, reached only when p_g = p_data. There the best discriminator outputs 1/2 everywhere, a coin flip. That is the "unique solution" in the abstract.

One practical fix from the same paper. Early on D rejects G's samples with confidence, so log(1 − D(G(z))) saturates and its gradient almost vanishes. The paper trains G to maximise log D(G(z)) instead, which has "the same fixed point of the dynamics of G and D" but gives "much stronger gradients early in learning".

All of this holds for models of unlimited capacity, in the space of density functions. For neural networks the paper offers no such guarantee. Its section 6 warns that D must be kept in step with G, or G collapses many values of z onto the same x, which it calls the Helvetica scenario.

## In ComfyUI

ComfyUI samples, so it only needs the generating half of a GAN. That half turns up in three places.

- **The VAE.** Rombach et al., the latent diffusion paper behind Stable Diffusion, train their autoencoder with a perceptual loss and a patch-based adversarial objective, which they say avoids the blur of pixel losses such as L2 or L1 alone. Their appendix G describes the discriminator. It plays no part when you press Queue, but the autoencoder was shaped by it.
- **Audio vocoders.** The docstring of `Vocoder` in `comfy/ldm/lightricks/vocoders/vocoder.py` says it is based on the HiFi-GAN code and supports HiFi-GAN and BigVGAN v2. `comfy/ldm/ace/vae/music_vocoder.py` has a `HiFiGANGenerator`. HiFi-GAN is a GAN by its own title, and its abstract reports 22.05 kHz audio at 167.9 times faster than real time on one V100.
- **Upscale models.** `UpscaleModelLoader` in `comfy_extras/nodes_upscale_model.py` hands the file to the `spandrel` library, whose README lists ESRGAN among its architectures. The ESRGAN abstract says it improves the network, the adversarial loss and the perceptual loss of SRGAN.

The judge never runs. The only class named `Discriminator` in the core source is in `comfy/ldm/cascade/stage_a.py`, and nothing calls it.

Try the game yourself. The judge here is rebuilt perfectly for every position of the generator, which real training never has.

{{play:ganvalue}}

The nearest thing to a GAN you can queue is an upscale model. If the file you load was trained with an adversarial loss, as ESRGAN was, the `ImageUpscaleWithModel` node of this graph runs the generator half of that game.

{{graph:sd15_upscale}}

![GFPGAN 1.4, a face restorer from a pack, whose paper says it draws on the priors in a pretrained face GAN. Left: an invented adult's face shrunk to 160 px, blurred and saved as a JPEG at quality 30. Middle: GFPGAN's result. Right: the clean original. The eyes, brows and lips come back sharp, and the face comes out a little rounder and younger: detail that looks real, not detail that was there.](families/face_1.webp)

## What goes wrong

- **You read 50% discriminator accuracy as success.** In the lab all four seeds sat near chance, 0.461 to 0.515, while the samples were still 7 to 21 times further from the data than two real samples are. Judge the samples, or a distance like W1, and not the judge's score.
- **In your own training loop the generator hardly learns at the start.** That is the saturating loss. log(1 − D) gave a gradient of 0.4386 in the lab, and −log D gave 13.0146 against the same judge. Use the second one, as the paper does.
- **The samples look good but say the same few things.** The paper warns about this: if G trains too far ahead of D, it collapses many values of z on to one x. Spot it by counting. In the lab the share in the right hump should be 0.700. Train the judge in step with G.
- **An upscaler invents detail.** The ESRGAN abstract itself calls these "hallucinated details". An adversarial loss rewards what looks real, not what was there. For text, faces of real people or measurements, compare with a plain resize before trusting it.
- **An upscaler runs out of memory.** `ImageUpscaleWithModel` starts with tiles of 512 and halves them when memory runs out, and it gives up below 128. If it fails, shrink the input image, because the tiles are already as small as it will go.
- **You look for the discriminator in a node list.** Core never runs one when sampling. A GAN's judge is thrown away after training.

## Lab

Part one uses six points, so everything is exact. The lab evaluates V for the best discriminator against several generators and compares with −log 4 + 2 JSD. The last column is a discriminator that ignores its input and says 1/2.

```text
generator           JSD      V(D*, G)   -log4 + 2 JSD   V(D=1/2, G)
uniform             0.0529   -1.280510  -1.280510        -1.386294
the data itself     0.0000   -1.386294  -1.386294        -1.386294
D* for the data itself: 0.50 0.50 0.50 0.50 0.50 0.50   -log 4 = -1.386294
```

The two agree to 1e-12, and 2000 random nudges to the best discriminator never scored higher. A constant D = 1/2 earns −log 4 against every generator, so the best discriminator does no better than ignoring its input only when the generator is perfect.

Part two is the saturation. Here a is the logit that D gives a fake, so D = sigmoid(a):

```text
logit a   D = sigmoid(a)   |d log(1-D) / da|   |d (-log D) / da|
 -8.0     0.00034          0.00034              0.99966
```

The gradient of log(1−D) with respect to a has size D, so when D is sure the sample is fake the generator hears almost nothing. The gradient of −log D has size 1−D. On a real network, after training D for 300 steps against an untrained G and changing only the loss:

```text
after 300 discriminator steps against an untrained generator, mean D(G(z)) = 0.0154
generator gradient norm with loss log(1 - D): 0.4386
generator gradient norm with loss -log D    : 13.0146
ratio 29.7
```

Part three trains a small GAN on the two-hump data of CU-101, one step for D and then one for G, with the second loss. W1 is the average gap between matching sorted samples of model and data, so lower is better. Over seed 0, D(real) and D(fake) stayed between 0.491 and 0.517, near the 1/2 where the theory ends, while W1 fell from 0.432 at step 500 to 0.117 at step 2000. Four seeds after 2000 steps:

```text
seed  W1      right hump  share in the gap  discriminator accuracy
0     0.113   0.694       0.022             0.501
1     0.338   0.705       0.029             0.461
2     0.234   0.718       0.019             0.515
3     0.161   0.710       0.021             0.493
two real samples of this size differ by W1 0.016; the gap holds 0.016 of the real data; 0.500 is a discriminator that cannot tell
```

Every discriminator scored near chance, yet W1 is 7 to 21 times the 0.016 that two real samples would differ by. A discriminator at chance is not proof that the generator is right: a small network trained for 2000 steps may not see what is left. Seed 1 has the worst W1 and an accuracy below one half, so at that step D is wrong more often than right. Both networks keep moving, and the end state is one frame of a chase. This generator is a continuous function of z, so it must put some mass between the humps: 0.019 to 0.029 of its samples, against 0.016 of the real data.

## What is contested

The theorem is about unlimited capacity. It does not say how many steps, which learning rate or which seed give a good generator, and the lab shows the spread.

The paper scored samples with Parzen-window likelihood estimates and warns that this "has somewhat high variance and does not perform well in high dimensional spaces". Do not rank models by those numbers.

"Diffusion beat GANs" is a statement about benchmarks. Dhariwal and Nichol (2021) reported image quality "superior to the current state-of-the-art generative models" and matched BigGAN-deep with as few as 25 forward passes per sample. That narrowed the one-pass advantage. It did not remove GAN-trained parts from the pipeline.

## Sources

- [Goodfellow et al. 2014. Generative Adversarial Networks](https://arxiv.org/abs/1406.2661). The PDF itself is titled "Generative Adversarial Nets".
- [Rombach et al. 2021. High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752)
- [Kong, Kim, Bae 2020. HiFi-GAN: Generative Adversarial Networks for Efficient and High Fidelity Speech Synthesis](https://arxiv.org/abs/2010.05646)
- [Wang et al. 2018. ESRGAN: Enhanced Super-Resolution Generative Adversarial Networks](https://arxiv.org/abs/1809.00219)
- [Dhariwal, Nichol 2021. Diffusion Models Beat GANs on Image Synthesis](https://arxiv.org/abs/2105.05233)
- [spandrel, a library for loading PyTorch super-resolution, restoration and inpainting architectures](https://github.com/chaiNNer-org/spandrel)
- [ComfyUI v0.43.0, comfy/ldm/lightricks/vocoders/vocoder.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lightricks/vocoders/vocoder.py)
- [ComfyUI v0.43.0, comfy/ldm/ace/vae/music_vocoder.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/ace/vae/music_vocoder.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_upscale_model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_upscale_model.py)
- [ComfyUI v0.43.0, comfy/ldm/cascade/stage_a.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/cascade/stage_a.py)
