# CU-310 - Cross-attention versus joint attention

**Objective.** Say who attends to whom in a U-Net block and in a transformer block, and what that changes for prompts, cost and patches. Taught by Madame Attention.

## The idea

The picture has to read the prompt somehow. There are two main designs in ComfyUI's models.

**Cross-attention.** Image tokens ask, and text tokens answer. Only the image tokens change. The text is the same at the end of the block as at the start. SD 1.5 and SDXL do this.

**Joint attention.** Image and text tokens go into one sequence. Everyone asks and everyone answers. Both change. SD3 and Flux do this.

Set the temperature and watch one cell of a picture read the prompt. That's a row of cross-attention. Joint attention adds more rows to it, as the lab shows.

{{play:attention}}

## The sums

Both use the attention sum from CU-301. Only the inputs differ.

```
cross:  Q from image,        K and V from text         output: image tokens
joint:  Q, K, V from both,   joined along tokens       output: both, split apart again
```

For 4 image tokens and 3 text tokens, the cross score table is 4 by 3. The joint table is 7 by 7.

## In ComfyUI

**Cross.** `CrossAttention` in `comfy/ldm/modules/attention.py` takes `q` from `x`, and `k` and `v` from `context`. The same class does self-attention when `context` is None. `BasicTransformerBlock` uses it twice in a row: `attn1` as self-attention, then `attn2` reading the text. That self-attention is needed, because cross-attention alone never lets image tokens see each other.

{{graph:sd15_txt2img}}

**Joint.** `_block_mixing` in `mmdit.py` shows the design plainly:

```python
qkv = tuple(... torch.cat((context_qkv[t], x_qkv[t]), dim=1) for t in range(3))
attn = optimized_attention(qkv[0], qkv[1], qkv[2], ...)
context_attn, x_attn = attn[:, :context_len], attn[:, context_len:]
```

Each side keeps its own projections, then they meet for one attention, then they split. `DoubleStreamBlock` in Flux does the same. After its double blocks, Flux joins the two streams for good and runs `SingleStreamBlock`s on the one sequence. In `MMDiT`, the last text block can be `pre_only`, which means the text is used and then dropped.

{{graph:sd35_flow}}

Esser et al. (2024) describe their MMDiT design as using separate weights for the two kinds of token, with a bidirectional flow of information between them.

## Why you might care

- **The text gets rewritten in joint models.** In a U-Net, the text rows are constant across the whole run of blocks. In Flux and SD3 they change at every double block, so a token's meaning can shift as the picture forms.
- **Text length costs more in joint models.** Every extra token, padding included unless it's masked out, joins the one sequence. The lab's pair counts show how little this really adds at this size.
- **Patches differ.** Nodes written for the U-Net's `attn1` and `attn2` don't fit a transformer. CU-322 shows PAG hitting this. Flux has its own hooks, with names like `double_block`.
- **The two designs aren't a ranking.** A model is trained as a whole, and you can't switch one for the other. Don't read "joint" as "better".

## What goes wrong

- **Calling MMDiT self-attention "image self-attention".** In `_block_mixing` the sequence holds text and image. Check the input shape if you're writing a patch.
- **A U-Net attention node on Flux.** It may do nothing, without an error. Try the same seed with and without it.
- **"Attention isn't scaled in my port."** Both use the same scaled sum, so a bug there hits both. Dividing by the square root of the width keeps scores in a sane range.
- **Assuming cross-attention costs little.** The cross step is small, but the U-Net's self-attention is not. See the counts.
- **Expecting a prompt to act at one fixed place.** Text rows change through a joint model, so a heat map from one block doesn't describe them all.

## Lab

Small versions with random weights. Same inputs for both.

```text
4 image tokens and 3 text tokens
cross-attention:  image out [1, 4, 8]   text out [1, 3, 8]   text changed: False
joint attention:  image out [1, 4, 8]   text out [1, 3, 8]   text changed: True
```

Both give the same shapes, but in cross the text passes through untouched. Here's one row of each attention table. Every row sums to 1, and the joint row spreads across 7 tokens, including the image's.

```text
cross, image token 0 over the 3 text tokens: [0.595, 0.139, 0.266]
joint, image token 0 over 3 text + 4 image:   [0.235, 0.055, 0.105, 0.093, 0.098, 0.304, 0.11]
```

And the test of who sees whom:

```text
change image token 3 only. Does image token 0's output move?
cross: False   joint: True
```

Finally the count of query-key pairs, for one block with 64 by 64 image tokens. Most of the cost in either design is images looking at images.

```text
SD 1.5 style: self + cross, 77 text tokens     17.09 million
Flux style: joint, 256 text tokens             18.94 million
Flux style: joint, 512 text tokens             21.23 million
joint, text left out, for scale                16.78 million
```

Those are only pairs in one block at one size. A real U-Net works at several sizes, and its smaller levels have far fewer tokens.

## Sources

- [Vaswani et al. 2017. Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Rombach et al. 2021. High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752)
- [Esser et al. 2024. Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206)
- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/mmdit.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/mmdit.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/layers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/layers.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/model.py)
