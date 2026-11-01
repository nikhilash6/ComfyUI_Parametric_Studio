# CU-304 - Why attention is O(n^2), and what Flash and Sage change

**Objective.** Work out the size of an attention score matrix from an image size, and tell apart the methods that hold less of it from the methods that round it. Taught by Madame Attention.

## Why it grows with the square

Attention scores every query against every key. With n tokens that is a table of n × n numbers, and in the plainest form you hold the whole table before softmax turns each row into weights.

```
scores = Q Kᵀ            shape n × n
weights = softmax(scores)    shape n × n
output = weights V       shape n × d
```

`attention_basic` in `comfy/ldm/modules/attention.py` does exactly this. Double the tokens and the table is four times larger.

Tokens come from the picture. With an 8× VAE and one token per latent cell, 1024 px gives 128 × 128 = 16,384 tokens. Double the image side and you have four times the tokens, so sixteen times the table. Real models attend at lower resolutions for this very reason, and a batch and several heads multiply the table again.

Print a latent. `PreviewAny` shows the tensor's values with the middle cut out, and no shape line, so work the size out: this graph asks for 1024 px, which is 128 × 128 cells.

{{graph:nm_latent_ops}}

Then see the numbers:

{{play:attnmem}}

## Three ways to hold less, or smaller

**Slice the queries.** The answer for one query needs only that query's row. So score a slice of queries, turn it into output, drop the scores, and go on. The sums are the same, and only less is held at once. `attention_split` works out what it needs, picks the power of two of slices that should fit free memory, and doubles it if it still runs out. It costs more passes.

**Online softmax.** The rows themselves can be built piece by piece, which is the idea of FlashAttention (Dao et al. 2022). Walk the keys and values in blocks, and for each query keep three running things: the largest score so far, the sum of exponentials so far, and the output so far.

```
m_new = max(m, max(S_block))
l_new = l × exp(m − m_new) + Σ exp(S_block − m_new)
o_new = o × exp(m − m_new) + Σ exp(S_block − m_new) V_block
final = o / l
```

Its title says exact, and our lab agrees to rounding error. The paper's reason is that on a GPU, moving data between big memory and small on-chip memory is the expensive part, so it arranges the work around that.

**Round the numbers.** SageAttention's title says 8-bit: it trades numeric precision for speed. That is a different bargain, because the numbers change. If it stays close enough for your pictures is a question to test by eye, and when a backend misbehaves, black output is a known sign (see below).

## In ComfyUI

The backend is one choice made when ComfyUI starts, read from the flags. In `attention.py` the order is:

1. `--use-sage-attention`: `attention_sage`. It falls back to `attention_pytorch` when low precision is turned off, or when a mask is present and the library can't take one.
2. `--use-flash-attention`: `attention_flash`, which uses the separate flash_attn library and raises on a mask, then falls back on error.
3. xformers, if installed and enabled.
4. PyTorch's `scaled_dot_product_attention`, through `attention_pytorch`. On an NVIDIA card with PyTorch 2 this is the default, and `model_management.py` turns on PyTorch's flash and memory-efficient backends for it.
5. Otherwise `--use-split-cross-attention` gives `attention_split`, and with no flag `attention_sub_quad`.

`--use-ck-attention` overrides that with `attention_comfy_kitchen_int8`. `optimized_attention_for_device` also has side rules: on a CPU device it uses `attention_sub_quad`, and masked calls get their own variable.

So you usually already have a form of flash attention, through PyTorch, without any flag. The console tells you which one you got: `Using pytorch attention`, and so on.

## What goes wrong

- **You installed Sage expecting less VRAM.** It is sold on speed through low precision. Test it with a timer and a peak reading before you decide it helped.
- **Black or broken images after changing backend.** Change back first. `--force-upcast-attention` has the help text "please report if it fixes black images", and several flags exist because low precision bites. One seed proves little, so test more.
- **A flag is refused or ignored.** With `--use-sage-attention` or `--use-flash-attention` and no library, ComfyUI logs an install command and exits. The attention flags are a mutually exclusive group, so two together stop at the command line. The help for the split and sub-quadratic flags says they are ignored when xformers is used. Read the line that names the backend at startup.
- **A mask-using node falls back quietly.** Sage takes masks only if its version supports them, and flash does not. You may be running PyTorch attention for those calls.
- **Out of memory at high resolution, even with flash.** The rows are smaller, not gone. Outputs, Q, K and V still have to fit. Lower the size or the batch first.

## Lab

The first table is arithmetic:

```text
score matrix for one head and one batch row, fp16 (2 bytes)
    1024 tokens:        2 MB
    4096 tokens:       32 MB
   16384 tokens:      512 MB
   65536 tokens:     8192 MB
  double the tokens: x4
```

Now the three methods on random Q, K and V, 512 tokens. The reference is the full calculation in fp64. The int8 row is a toy of ours, rounding only Q and K with one scale, not SageAttention's algorithm.

```text
512 tokens, 64 dimensions: largest difference from the full calculation, in fp32
  method                        scores held at once   difference
  full matrix                                262144     3.43e-07
  4 slices of queries                         65536     3.43e-07
  16 slices of queries                        16384     3.43e-07
  online softmax, blocks of 128                65536     2.68e-07
  online softmax, blocks of 32                16384     2.53e-07
  toy: Q and K rounded to int8               262144     9.52e-03
```

Holding a sixteenth of the scores changes nothing beyond rounding. Rounding the inputs moves the answer tens of thousands of times further.

```text
relative change from int8 Q and K: 0.0141. Exact methods stay at rounding level. Low precision is a real change.
```

Tokens from image size:

```text
tokens from an image: one token per latent cell, 8x VAE
    512 px, patch 1:   4096 tokens, matrix     32.0 MB per head per row
   1024 px, patch 1:  16384 tokens, matrix    512.0 MB per head per row
   1024 px, patch 2:   4096 tokens, matrix     32.0 MB per head per row
   2048 px, patch 2:  16384 tokens, matrix    512.0 MB per head per row
```

## Sources

- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [Dao et al. 2022. FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135)
- [Zhang et al. 2024. SageAttention: Accurate 8-Bit Attention for Plug-and-play Inference Acceleration](https://arxiv.org/abs/2410.02367)
