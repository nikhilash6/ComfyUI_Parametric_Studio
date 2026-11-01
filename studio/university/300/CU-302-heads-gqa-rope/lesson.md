# CU-302 - Multi-head, GQA and RoPE

**Objective.** Say what heads split, what grouped-query attention shares and saves, and why rotating by position makes attention care about gaps. Taught by Madame Attention.

## The idea

CU-301 had one attention. Real blocks change it in three ways.

- **Heads.** Cut the width into pieces and attend separately in each. 64 channels and 8 heads means 8 attentions of 8 channels. Each head makes its own weights.
- **Grouped-query attention (GQA).** Keep all the query heads, but make fewer keys and values and share them. Fewer weights and smaller caches. Same number of attention matrices.
- **RoPE (rotary position embedding).** Turn each query and key by an angle that depends on its position. Nothing is added to the token. The score ends up depending on how far apart two tokens are.

## The mechanism

**Heads.** Reshape (batch, tokens, width) into (batch, heads, tokens, width ÷ heads), run CU-301's sum, and join back. No channels are lost. Heads see different numbers because of the projection before the split, so a head has no fixed job like "grammar" unless training happens to give it one.

**GQA.** Ainslie et al. (2023) generalise multi-query attention, which uses a single key and value head. With 24 query heads and 8 key and value heads, each key head is repeated three times to line up. Their abstract reports that GQA, retrained from a multi-head checkpoint, gets close to multi-head quality with speed comparable to multi-query. That is their result, on language models, and we repeat it as theirs.

**RoPE.** Take a query or key at position m. Group its channels in pairs. Rotate pair i by the angle m × ωᵢ, where ωᵢ = 1 ÷ θ^(i ÷ (d÷2)), with θ usually 10,000. A rotation keeps length. When you take a dot product of a query at m and a key at n, each pair's contribution depends only on the angle between them, which is (n − m) × ωᵢ. So absolute position drops out. Su et al. (2021) introduced this.

```
pair i of x at position m:    x₀' = x₀ cos(m ωᵢ) − x₁ sin(m ωᵢ)
                              x₁' = x₀ sin(m ωᵢ) + x₁ cos(m ωᵢ)
```

For an image you need two or more axes. Split the head's width into a part per axis, and rotate each part by that axis's coordinate.

{{play:rope}}

## In ComfyUI

**Heads** are everywhere. `optimized_attention` takes a `heads` count, and `attention` in `comfy/ldm/flux/math.py` reads it off the tensor.

**GQA is real here.** `JointAttention` in `comfy/ldm/lumina/model.py` has `n_kv_heads` and `n_rep = n_heads // n_kv_heads`, and one `Linear` that produces (n_heads + 2 n_kv_heads) × head_dim. `model_detection.py` sets 24 and 8 for the original Lumina 2 size, and 30 and 30 for the Z image size, which is ordinary multi-head. Text encoders do it too: `comfy/text_encoders/llama.py` has `num_key_value_heads` in its configs and `num_kv_heads` in its attention.

**RoPE** is `rope` and `apply_rope` in `comfy/ldm/flux/math.py`, with `EmbedND` in `comfy/ldm/flux/layers.py` making one set per axis. FLUX.2's detection sets `axes_dim` to four axes of 32. The graph below uses that model. `comfy/ldm/hydit/attn_layers.py` has `apply_rotary_emb`, and `comfy/ldm/sam3/tracker.py` has `apply_rope_memory`.

{{graph:wf_flux2_klein}}

ComfyUI also applies RoPE to Q and K only, as `attention` shows. V isn't rotated. The score decides the mix, and the values are what get mixed.

## What goes wrong

- **You assume a head means something.** Nothing in the code gives a head a topic. Reading one head's map as "the grammar head" is a guess.
- **Head width doesn't divide evenly.** The width must split by the head count, and `rope` asserts `dim % 2 == 0`. With a custom config, an odd head width stops there.
- **Axis widths don't add up.** `Flux` raises an error if `sum(axes_dim)` differs from the positional width. If you see it, the checkpoint was detected as the wrong model or the config was edited by hand.
- **You compare GQA with multi-head by weights alone.** The lab shows weights fall to 0.556 at 24 and 8. That says nothing about picture quality. Only a trained model can show that.
- **You expect RoPE to give absolute place.** A pure dot product depends on the gap, so a token can't tell "top left" from it. Models still vary with size because scales and training data vary.

## Lab

Heads first, then shared keys.

```text
width 64, 8 heads -> 8 heads of width 8, split then join is identical: True
8 query heads, 4 key/value heads: output (1, 8, 6, 8), heads 0 and 1 share keys: True, heads 1 and 2 share keys: False
```

The same counting at Lumina 2's sizes. The projection is one layer's worth, and the formula is the one in `JointAttention`.

```text
key/value heads   weights        relative
24                15,925,248     1.000
12                10,616,832     0.667
8                 8,847,360      0.556
4                 7,077,888      0.444
```

Now RoPE. We also checked the formula against ComfyUI's own `rope` and `_apply_rope1` on a CPU: the largest gap was 2.4e-07, which is rounding between float32 and float64.

```text
query at  key at  gap  score with RoPE  score with added position
0         3       3    -15.734306       36.905059
10        13      3    -15.734306       28.187126
500       503     3    -15.734306       20.093070
0         40      40   -16.555222       18.010450
same gap, same RoPE score: True  same gap, same added-position score: False
```

The vectors are random, so the scores mean nothing alone. What counts is the first three rows matching. Adding a position vector to the token does not give that, as the last column shows.

```text
3 axes: score for offset (0, +2, -7) at two places in the grid: -20.359071 -20.359071
```

## Sources

- [Vaswani et al. 2017. Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Su et al. 2021. RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864)
- [Ainslie et al. 2023. GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints](https://arxiv.org/abs/2305.13245)
- [ComfyUI v0.43.0, comfy/ldm/flux/math.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/math.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/layers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/layers.py)
- [ComfyUI v0.43.0, comfy/ldm/lumina/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lumina/model.py)
- [ComfyUI v0.43.0, comfy/model_detection.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_detection.py)
- [ComfyUI v0.43.0, comfy/text_encoders/llama.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/llama.py)
