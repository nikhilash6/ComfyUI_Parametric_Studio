# CU-301 - Attention from scratch

**Objective.** Write scaled dot-product attention, explain the square root of d, and trace how a word in the prompt reaches a pixel. Taught by Madame Attention.

## The idea

Each token asks a question (query), each token offers a label (key) and some content (value). A token takes a weighted average of the content, weighted by how well its question matches the labels. All of it is differentiable, and every token may look at every other. Bahdanau et al. (2014) introduced attention for translation, and Vaswani et al. (2017) built a whole architecture from it.

## The maths

Scaled dot-product attention (Vaswani et al. 2017, eq. 1):

```
Attention(Q, K, V) = softmax( Q Kᵀ / √d ) V
```

Q is n×d, K and V are m×d. The result is n×d: one output per query. Self-attention takes Q, K and V from the same tokens. Cross-attention takes Q from one sequence and K, V from another.

**Why √d?** If query and key entries are independent with mean 0 and variance 1, then q·k has variance d (the paper's footnote makes this argument). Large products push softmax to a near one-hot output, where its gradients are tiny. Dividing by √d brings the variance back to 1.

## Try it

Before the numbers, move a query around and watch who it listens to. Temperature is what happens if you change the divisor: a smaller one sharpens the softmax.

{{play:attention}}

## In ComfyUI

`CrossAttention` in `comfy/ldm/modules/attention.py` is the U-Net's block. `optimized_attention` is one function name that points at one of several backends, picked once when the module loads: `attention_pytorch` when PyTorch's own function is allowed, or `attention_split`, `attention_sub_quad` or `attention_basic`. They are meant to agree on the answer and differ in memory and speed. FLUX-style models call `attention` in `comfy/ldm/flux/math.py`, which adds position first and then calls the same `optimized_attention`.

Rombach et al. (2021) conditioned Stable Diffusion this way: Q comes from the latent, and K, V from the text encoder, so the text reaches the image only through these weights. In the graph below, `CLIPTextEncode` makes those keys and values, and `KSampler` runs the blocks that attend to them.

{{graph:sd15_txt2img}}

## Reading a tensor shape

Most of the architecture code is easier once you read its shapes. In `CrossAttention.forward` you will see three linear layers, then a call that passes q, k and v along with a head count. A prompt's text is usually 77 tokens per chunk in SD 1.5, so a 64×64 latent block has 4,096 rows against 77 columns. Self-attention at the same place has 4,096 rows against 4,096 columns. That is why a block's self-attention costs far more than its cross-attention, and why the prompt's length matters little for memory while the image's size matters a lot.

## Lab

A hand example you can check on paper:

```text
weights: [0.4458, 0.1084, 0.4458]  output: 20.0
```

The query [2, 0] scores 2, 0 and 2 against the keys, each divided by √2. The output is an average of the values 10, 20 and 30.

Next, measurement of the footnote:

```text
d       var(q.k)  var after /sqrt(d)  largest weight, no scale  largest weight, scaled
4       4.0       1.002               0.344                     0.159
512     510.2     0.996               0.940                     0.166
4096    4113.6    1.004               0.979                     0.165
```

Without the scale, at d = 4096, softmax is nearly one-hot over 32 keys. With it, the behaviour does not depend on d.

**Attention has no idea of order:**

```text
self-attention, permute then attend against attend then permute: max difference 9.5e-07
```

Shuffling the tokens only shuffles the outputs. Position has to be added separately, which is the job of positional encodings. Now cross-attention, with eight latent patches planted to resemble the word "fox":

```text
cross-attention shapes: image (1, 64, 32), text (1, 4, 32), weights (1, 64, 4), output (1, 64, 32)
mean weight on each word, fox patches:   {'a': 0.0, 'red': 0.0, 'fox': 0.999, '<pad>': 0.001}
mean weight on each word, other patches: {'a': 0.243, 'red': 0.247, 'fox': 0.23, '<pad>': 0.28}
```

The weight matrix has one row per patch and one column per word. This is what attention-map tools visualise. The vectors here are random and planted, so this shows the mechanism and says nothing about a trained model's maps.

**Cost:**

```text
1024        128          4,096             16,777,216               0.03 GiB
2048        256          16,384            268,435,456              0.50 GiB
doubling the side quadruples the tokens and multiplies the pairs by 16
```

Those rows assume patch size 2 on an 8× latent, which is what FLUX-style models use. They are one head, one layer, and only the matrix: a real model has many, and running out of memory at high resolution starts here. FlashAttention (Dao et al. 2022) computes the same result without storing that matrix at once.

## What goes wrong

- **Out of memory at a large size, fine at a small one.** Doubling the side multiplies the pairs by 16. Read the last table: the size is what grew. Try a tiled pass or a smaller size first.
- **A tool's attention map looks meaningful, so you trust it.** It's one matrix from one layer at one step. It shows what the layer weighted, not why the picture came out. Compare several steps before you conclude anything.
- **You expect word order to matter by itself.** Attention alone ignores order, as the permutation line shows. Order arrives through position in the text encoder.
- **Black output after changing attention backend.** Backends should agree, but a precision or driver problem can still give NaN. Test the same seed on the default backend before you blame the prompt. Our check here is only that they share a signature; we did not compare their pixels.
- **Padding gets weight.** If a mask is missing, padding is just another token to the softmax. The lab shows the weight it takes without a mask.

## Sources

- [Bahdanau, Cho, Bengio 2014. Neural Machine Translation by Jointly Learning to Align and Translate](https://arxiv.org/abs/1409.0473)
- [Vaswani et al. 2017. Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Rombach et al. 2021. High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752)
- [Dao et al. 2022. FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135)
- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/math.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/math.py)
