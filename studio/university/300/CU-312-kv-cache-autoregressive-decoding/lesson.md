# CU-312 - KV cache and autoregressive decoding

**Objective.** Explain why generating one token at a time wastes work, what a KV cache stores to avoid that, and what it costs in memory. Taught by Madame Attention.

## The idea

Some models write their output one piece at a time, each piece depending on what came before. This is autoregressive decoding. Large language models work this way, and so do some models inside ComfyUI.

Naively, each new token means running the whole sequence through attention again. But old tokens don't change. Their keys and values are the same numbers as last time. So keep them. That store is the KV cache.

The answer doesn't change, only the work.

## The mechanism

A new token needs only its own query, and every token's key and value so far.

```
no cache:    project all n tokens, attend n rows      work grows with the square of the step
with cache:  project 1 token, append k and v,
             attend 1 row against n stored rows       work grows in line with the step
```

Over a run of n tokens that gives:

- No cache: n(n+1)/2 projections, and n(n+1)(n+2)/6 attention pairs.
- KV cache: n projections, and n(n+1)/2 attention pairs.

So the fraction of pairs saved is 1 − 3 ÷ (n + 2). Short runs gain little. Long runs gain a lot.

{{play:kvcache}}

**The price is memory.** Each layer stores two arrays, keys and values, of tokens × kv heads × head width. They stay for the whole run. Fewer key and value heads means a smaller cache, which is why grouped-query attention (CU-302) helps here.

**Rule of use.** The cache is valid only if everything earlier stays the same. Changing an early token, or going back to try another branch, needs a rollback or a rebuild.

## In ComfyUI

Three places to read.

**Text encoders.** `BaseGenerate` in `comfy/text_encoders/llama.py` is the generation loop. `init_kv_cache` makes the store. Without the fast path it's a tuple of key, value and index. With it, it's a `FixedKV`, sized once up front so nothing has to reallocate. In the attention, new keys and values are written to the store and the query attends against all of it.

**Music.** `MiniMaxMusic3AR.generate` in `comfy/ldm/minimax_music/ar.py` runs an autoregressive text and music-code model, calling `init_kv_cache` with a capacity of prompt tokens plus a decode limit, plus one. The graph below contains that step: `MiniMaxMusic3TextEncode` reaches this class through the text encoder model. So the name "text encode" hides a whole generator here.

{{graph:wf_music3}}

**Video.** `CausalWanSelfAttention` in `comfy/ldm/wan/ar_model.py` keeps a dict of `k`, `v` and `end` per layer, and appends each block's tokens. Its comment says rotated keys and plain values go in the cache. `crossattn_caches` does the same job for text, which only needs computing once. The nodes are in `comfy_extras/nodes_ar_video.py`, whose docstring names Causal Forcing and Self-Forcing, and `ARVideoI2V` seeds the cache with a start image.

Ordinary diffusion samplers don't use this. Each sampling step changes the whole latent, so nothing from the last step's keys can be reused unchanged.

## What goes wrong

- **Out of memory at a late step, fine at the start.** A growing store is the likely reason, or a store sized too large at the beginning. Read the capacity it asks for. Shorter output means a smaller store, and for music that's the audio length you asked for.
- **Garbage after you changed an early token.** The lab shows this: a stale cache gives a very wrong answer. Clear it or roll back. Inside ComfyUI, the loops reset caches themselves, so this mainly bites when you write your own.
- **You expect KV caching to speed up image sampling.** It doesn't apply, as said above. Caching tools for diffusion reuse results between steps under other rules, and those change the picture.
- **Position drifts.** A cached model needs the right position for each new token, since it isn't re-running the old ones. `get_past_len` exists for this. In your own loop, a wrong position gives output that looks fine for a moment and then degrades.
- **You compare speeds without seeing the first step.** The first pass still has to run the whole prompt. A long prompt costs that up front however good the cache.

## Lab

The lab generates 40 tokens twice with a toy attention: with a cache, and by recomputing everything. It compares the two at every step.

```text
first token, cached against recomputed: max difference 0.0e+00
40 tokens generated, largest difference between the two outputs at any step: 1.4e-05
              token projections   attention pairs
no cache      820                 11,480
KV cache      40                  820
```

The answers agree to rounding error. The work does not. 1 − 3 ÷ 42 is 92.9%, which is what 820 against 11,480 gives. Now the memory, for one illustrative size: two arrays, 8 key and value heads, head width 128, two bytes each.

```text
tokens stored   one layer, 8 kv heads, head width 128, bf16   24 layers
256             1.0                                           0.02 GiB
1,024           4.0                                           0.09 GiB
4,096           16.0                                          0.38 GiB
16,384          64.0                                          1.50 GiB
```

And the rule of use:

```text
edit token 3 and reuse the old cache: the output is off by 8.636, so a cache must be thrown away or rolled back
cross-attention to a fixed text of 77 tokens over 40 steps: 77 key projections with a cache, 3080 without
```

This is one layer on random vectors, with one head. Real models are more complex, and this says nothing about their speed.

## Sources

- [Vaswani et al. 2017. Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [ComfyUI v0.43.0, comfy/text_encoders/llama.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/llama.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax_music/ar.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax_music/ar.py)
- [ComfyUI v0.43.0, comfy/ldm/wan/ar_model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/wan/ar_model.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_ar_video.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_ar_video.py)
