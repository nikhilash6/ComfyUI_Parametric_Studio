# CU-503 - History 3: Pixel by pixel, autoregressive image models

**Objective.** Write an image's probability as a product of conditionals, see what a causal mask enforces, count what sampling one pixel at a time costs, and follow the idea from pixels to tokens to the autoregressive video sampler in ComfyUI. Taught by Madame Attention.

## The idea

Put the pixels in order, left to right and top to bottom, and ask each one: given everyone before you, what are you? That is autoregression, and it needs no approximation. In January 2016 van den Oord, Kalchbrenner and Kavukcuoglu showed in "Pixel Recurrent Neural Networks" that a network can do this for natural images. It "sequentially predicts the pixels in an image along the two spatial dimensions", and each colour value is a choice among 256 values. Because the product is exact, the paper reports exact likelihoods. In its Table 5 on CIFAR-10, in bits per dimension, a uniform guess scores 8.00, the 2015 diffusion paper of Sohl-Dickstein et al. 4.20, PixelCNN 3.14, Row LSTM 3.07 and Diagonal BiLSTM 3.00. Lower is better.

In June 2016 "Conditional Image Generation with PixelCNN Decoders" added conditioning on labels and embeddings, and gated layers that bring PixelCNN's log-likelihood "to match the state-of-the-art performance of PixelRNN on ImageNet, with greatly reduced computational cost".

## The maths

```
p(x) = Π_(i=1..n) p( x_i | x_1, …, x_(i−1) )
```

This is the chain rule of probability and holds for any order. The choices are the order and the model of each factor. PixelRNN shares the parameters "across all pixel positions", and for colour it goes red, then green, then blue.

Scoring and sampling have different costs. The paper notes that "during training and evaluation the distributions over the pixel values are computed in parallel, while the generation of an image is sequential." What allows the parallel part is a mask that cuts every path from x_j to the prediction of x_i unless j < i. PixelRNN masks its convolutions. MADE (Germain et al. 2015) does it for dense layers, so that "each input is reconstructed only from previous inputs in a given ordering". Transformers do it in attention: the decoder is modified "to prevent positions from attending to subsequent positions" (Vaswani et al.).

To sample, draw x_1, feed it back, draw x_2, and so on: n passes through the network.

## In ComfyUI

A KSampler on an SD or Flux model is not autoregressive. It updates every position at every step. The chain rule appears in two other places.

- **Language-model text encoders.** In `comfy/text_encoders/llama.py` the forward pass, when it handles more than one token at once, builds a causal mask by filling a square matrix with a large negative number and keeping only its strict upper triangle (`triu_(1)`), so a token cannot read later tokens. `generate` then draws one token at a time: `sample_token` scales the logits by temperature, trims with top-k and top-p, and calls `torch.multinomial`, with a KV cache so earlier tokens are not recomputed.
- **Video that is autoregressive over blocks of frames.** `SamplerARVideo` in `comfy_extras/nodes_ar_video.py` has a widget `num_frame_per_block`: "1 = framewise, 3 = chunkwise". Its `sample_ar_video` in `comfy/k_diffusion/sampling.py` visits the blocks in order and runs the usual sigma loop on each one. `CausalWanSelfAttention` in `comfy/ldm/wan/ar_model.py` writes a block's keys and values into a cache and attends over the cache up to and including that block, so each block sees all earlier blocks and none later. Each factor p(block | earlier blocks) is itself a diffusion run.

The price of going one token at a time, and how much a cache takes back. This is the loop that `generate` runs.

{{play:kvcache}}

The easiest autoregressive model to reach from a graph is Music 3. CU-312 follows its text encoder into `MiniMaxMusic3AR.generate`, which draws tokens one at a time. The name "text encode" hides that.

{{graph:wf_music3}}

## What goes wrong

- **You think a KSampler draws one latent cell at a time.** It updates every position at every step, so nothing here applies to it. Autoregression shows up in the language-model encoders and in the AR video sampler.
- **You set `num_frame_per_block` by taste.** Its tooltip says it "must match the checkpoint's training mode". It is a fact about the file, and not a quality dial.
- **The same settings give different output.** `sample_token` draws with `torch.multinomial`, so a run depends on its generator. Keep the seed fixed if you want to repeat a result.
- **Your own mask leaks.** An off-by-one lets a position read itself. Test it the way the lab does: differentiate each output with respect to each input. Everything at or after the position must be exactly zero.
- **You rank models by bits per dimension to find the best-looking one.** A likelihood is a compression score. CU-506 shows a model with a worse likelihood than Gated PixelCNN and the best FID of its day.
- **You budget by the training speed.** Scoring is one pass and sampling is one pass per element: 64 against 1 in the lab, with 8 × 8 pictures.

## Lab

The data are 8×8 black and white images of a vertical bar two pixels wide, in one of 7 positions, with every pixel then flipped with probability 0.05. The generator is known, so the exact conditionals can be computed. First the chain rule, on 20000 images: the 64 exact conditionals, each a Bayes average over the bar position, multiply to the joint probability.

```text
largest gap between sum_i log2 p(x_i | x_<i) and log2 p(x), over 20000 images: 9.2e-14
```

Next a mask. The lab builds a small dense network with the MADE masks and one without, and differentiates every output logit with respect to every input pixel.

```text
largest |d logit_i / d x_j|    j >= i (future and self)   j < i (past)
masked network                 0.00e+00                   0.074
unmasked network               1.19e-01                   0.095
```

In the masked network no output reads its own pixel or any later one, and the derivative is exactly zero. The unmasked one leaks.

Now train the masked network by maximum likelihood. One forward pass scores all 64 conditionals, so there is no loop over pixels. Bits per pixel on 20000 fresh images:

```text
model                        bits per pixel on 20000 fresh images
uniform: every image equally likely  1.0000
independent pixels                   0.8371
learned autoregressive               0.3404
exact autoregressive (the truth)     0.3300
```

The independent model has every pixel's marginal right and still pays 0.8371 against a true 0.3300, because it cannot see that pixels agree with each other. The learned model comes within 0.0104 bits per pixel of the truth. By row:

```text
bits per pixel by image row       1     2     3     4     5     6     7     8
learned                        0.62  0.33  0.30  0.30  0.30  0.29  0.30  0.29
exact                          0.61  0.31  0.29  0.29  0.29  0.28  0.29  0.29
the flip noise alone costs 0.29 bits per pixel
```

Row 1 is expensive because the bar's position is not yet known. Later rows cost about the flip noise, since the pixel above tells nearly everything.

Sampling cannot be parallel. A pixel can be drawn only after the pixels before it exist. A bar here means two adjacent columns with at least 6 of 8 pixels lit and every other column with at most 3. Four of the learned model's samples are drawn below.

```text
network passes to draw 4000 images: 64 (one per pixel), against 1 pass to score them
share that look like a bar:  real data 0.988   autoregressive samples 0.842   independent-pixel samples 0.001
...##...   ...##...   ......##   ......##
....#...   ...##...   ...#..##   ......##
...##...   ...##...   ......##   ##....##
...#.#..   .#.##...   ......##   #.....##
...##...   ...##...   ......##   ......##
...###..   ...##...   ......##   ....#.##
...##...   .#.##...   ......##   ......##
...##...   ...##...   ......##   ......##
```

The model's 0.0104 bits per pixel is 0.67 bits per image, and it shows: 0.842 of its samples are well-formed bars, against 0.988 of real images and 0.001 for independent pixels. Finally, the number that moved the field from pixels to tokens:

```text
values in a 256x256 RGB image: 196,608; image tokens in DALL-E's 32x32 grid: 1,024; ratio 192
```

## What is contested

Why did pixels give way to tokens? The authors of DALL·E say that using pixels directly as image tokens "would require an inordinate amount of memory for high-resolution images", and that likelihood objectives "tend to prioritize modeling short-range dependencies between pixels", so that capacity goes to high-frequency detail. They compress each 256×256 RGB image into a 32×32 grid of tokens from a vocabulary of 8192, which "reduces the context size of the transformer by a factor of 192", in a two-stage procedure they call similar to VQ-VAE. Those are their reasons, and this lab cannot test them.

Autoregression against diffusion is not a settled contest. ComfyUI ships both, and its AR video sampler uses both at once.

The lab is a binary toy. It checks the mathematics and the cost accounting, not how an image model behaves on photographs.

## Sources

- [van den Oord, Kalchbrenner, Kavukcuoglu 2016. Pixel Recurrent Neural Networks](https://arxiv.org/abs/1601.06759)
- [van den Oord et al. 2016. Conditional Image Generation with PixelCNN Decoders](https://arxiv.org/abs/1606.05328)
- [Germain, Gregor, Murray, Larochelle 2015. MADE: Masked Autoencoder for Distribution Estimation](https://arxiv.org/abs/1502.03509)
- [Vaswani et al. 2017. Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Sohl-Dickstein, Weiss, Maheswaranathan, Ganguli 2015. Deep Unsupervised Learning using Nonequilibrium Thermodynamics](https://arxiv.org/abs/1503.03585)
- [van den Oord, Vinyals, Kavukcuoglu 2017. Neural Discrete Representation Learning](https://arxiv.org/abs/1711.00937)
- [Ramesh et al. 2021. Zero-Shot Text-to-Image Generation](https://arxiv.org/abs/2102.12092)
- [ComfyUI v0.43.0, comfy/text_encoders/llama.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/llama.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_ar_video.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_ar_video.py)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy/ldm/wan/ar_model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/wan/ar_model.py)
