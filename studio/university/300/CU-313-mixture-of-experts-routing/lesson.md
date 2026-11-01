# CU-313 - Mixture of experts routing

**Objective.** Explain how a gate picks a few feed-forward networks for each token, why that adds capacity without adding much work per token, and how to read it in ComfyUI. Taught by Madame Attention.

## The idea

After attention, each block has a small network applied to every token: the feed-forward, or MLP. A mixture of experts (MoE) keeps several such networks and uses only a few per token. A small gate decides which.

Storage grows with the number of experts. Work per token grows only with how many a token uses. So you can have a model with many more weights without paying for them all on each token. You do still pay for storing them.

## The mechanism

For a token x of width D, with E experts and top-k K:

```
scores = softmax( W x )                W is E×D, the gate's weights
ids, weights = top K of scores
output = Σ weightᵢ × expertᵢ(x)        plus, in many designs, a shared network that always runs
```

Shazeer et al. (2017) introduced the sparsely-gated layer. Fedus et al. (2021), in Switch Transformers, simplified it to one expert per token.

**Training issues.** `top K` has no gradient: only the weights do. The lab prints this. And a gate may fall into always choosing the same few experts. The literature's fix is a load-balancing loss during training. For inference that loss doesn't matter. The route is just arithmetic.

{{play:gate}}

## In ComfyUI

Three real examples.

**HiDream.** `comfy/ldm/hidream/model.py` has `MoEGate`, defaults of 4 routed experts and 2 activated, and `MOEFeedForwardSwiGLU`. Its `forward` repeats each token K times, runs each expert on the tokens routed to it, and sums with the gate's weights. It then adds `shared_experts`, which always runs. `norm_topk_prob` is False, so weights do not sum exactly to 1. The lab's first lines show this. `aux_loss` is `None` here: this is inference code. The comment says the design was modified from DeepSeek-V3's.

**Hunyuan 3D v2.1.** `comfy/ldm/hunyuan3dv2_1/hunyuandit.py` has its own `MoEGate`, `MoEBlock` and `AddAuxLoss`. Only the last `num_moe_layers` blocks use it, by `use_moe=True if depth - layer <= num_moe_layers`. The graph below is for the 3D family: it says Hunyuan3D 2, and we use it to show where such a block would live. Check which model you've got, because the code path depends on it.

{{graph:hunyuan3d_mesh}}

**Text encoders.** `comfy/text_encoders/gpt_oss.py` has `num_local_experts` 32 and `num_experts_per_tok` 4 in its config. `moe_experts_forward` is in `comfy/text_encoders/llama.py`.

## What goes wrong

- **You budget VRAM as if only K experts existed.** All E experts are loaded. "Sparse" saves compute, not storage, unless something offloads them.
- **You expect speed to fall with E.** Per token, calls depend on K. But each expert still has a small overhead, as the loop in `forward` visits all of them. A branch in HiDream's `forward` carries a TODO asking which of its two routes is faster, so the code doesn't settle that either.
- **You check "sum of weights equals 1".** It doesn't, with `norm_topk_prob` False. Don't treat that as a bug.
- **You try to edit the "right" expert.** A patch or LoRA on expert 2 only affects tokens routed there. Which tokens is decided by the gate, so results can look patchy. There's no fixed "face expert" unless someone has shown it for that model.
- **The load looks lopsided, so you assume a broken model.** We show only toy tokens here. On a trained model, a skewed load can be fine.

## Lab

The lab builds the layer with random weights. That shows the mechanics, and tells you nothing about trained routing.

```text
tokens 1000, experts 4, each token uses 2: output (1000, 32)
first 4 tokens, expert ids and weights:
  [3, 2]  [0.833, 0.151]  weights sum to 0.984
  [0, 2]  [0.725, 0.157]  weights sum to 0.882
  [0, 1]  [0.577, 0.419]  weights sum to 0.996
  [3, 1]  [1.0, 0.0]  weights sum to 1.000
load on each expert: [490, 484, 503, 523]  total 2000 = 1000 x 2
routed against compute-all-then-pick: max difference 0.0e+00
```

The routed code gives exactly what brute force gives. The total is always tokens × K.

```text
experts  top-k  expert parameters stored   expert calls per token
1        1      4,192                      1
4        2      16,768                     2
6        2      25,152                     2
16       2      67,072                     2
```

Going from 4 to 16 experts quadruples storage, with the same number of calls per token. Now a gate pointed the wrong way, and the fact that makes training awkward.

```text
top-1 load when one expert's gate weights line up with the data: [997, 2, 0, 1]
gradient flows through the weights: True  through the chosen ids: False
```

## Sources

- [Shazeer et al. 2017. Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer](https://arxiv.org/abs/1701.06538)
- [Fedus et al. 2021. Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity](https://arxiv.org/abs/2101.03961)
- [ComfyUI v0.43.0, comfy/ldm/hidream/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/hidream/model.py)
- [ComfyUI v0.43.0, comfy/ldm/hunyuan3dv2_1/hunyuandit.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/hunyuan3dv2_1/hunyuandit.py)
- [ComfyUI v0.43.0, comfy/text_encoders/gpt_oss.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/gpt_oss.py)
