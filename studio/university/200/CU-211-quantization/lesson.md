# CU-211 - Quantization: int8, FP8, 4-bit and GGUF

**Objective.** Compute the scale and the rounding error of a quantized weight, explain why a scale per block beats one scale per tensor when a few weights are large, and read the formats ComfyUI and GGUF use. Taught by Bit Bandit.

## The idea

Quantizing replaces each weight with a small code, an 8-bit integer, a 4-bit integer or an 8-bit float, and keeps a scale shared by a group of weights. Memory falls to the code size plus a share of the scale. The price is rounding error, and its size depends on three things: how many bits the code has, how many weights share one scale, and how large the largest weight in that group is.

## The maths

Absmax quantization on a symmetric integer grid (Dettmers et al. 2022 write it for int8 as scaling by 127 over the largest absolute value, then rounding):

```
scale = max|w| / qmax        q = round(w / scale)        ŵ = q · scale
qmax = 127 for int8,  7 for a symmetric int4
```

The grid has spacing equal to `scale`. Each weight is off by at most scale/2, and when the weights are spread smoothly over the cells the RMS error is scale/√12. So the error follows the largest weight in the group: one weight 30 times larger than its neighbours makes the step 30 times larger for every one of them. Dettmers et al. state the problem the same way: with a single scaling constant, one outlier can reduce the precision of all other values. Their remedy is more scaling constants per tensor, for example one per block.

More scales cost bits:

```
bits per weight = code bits + scale bits / weights per scale
```

GGUF stores the Q8_0 format as blocks of 32 weights with one fp16 scale and 32 int8 codes: (32 · 8 + 16) / 32 = 8.5 bits. Q4_0 is one fp16 scale and 16 bytes of 4-bit codes per 32 weights: (32 · 4 + 16) / 32 = 4.5 bits. The ggml source comment for Q4_K, a format with sub-blocks, also says "Effectively 4.5 bits per weight".

FP8 is a tiny float, not an integer grid (Micikevicius et al. 2022). E4M3 has 4 exponent bits and 3 mantissa bits, a largest normal value of 448 and a smallest subnormal of 2^-9. E5M2 has a largest normal value of 57,344. The spacing grows with the value, so the format tolerates a wide range but has only 3 (or 2) mantissa bits of precision at any size. A per-tensor scale still matters, because it moves the weights into the part of the range where the spacing is useful.

One more fact is pure algebra. A scale per tensor or per output row multiplies the whole dot product, so an integer matmul can be rescaled afterwards. A scale per block along the inner dimension varies inside the sum, so a kernel has to rescale each block's partial sum.

## In ComfyUI

ComfyUI v0.43.0 documents its own quantized checkpoint format in `QUANTIZATION.md`. A quantized module in an ordinary safetensors file has its `weight`, scale tensors such as `weight_scale`, and a `comfy_quant` tensor holding a small JSON like `{"format": "float8_e4m3fn"}`. `QUANT_ALGOS` in `comfy/quant_ops.py` is the registry:

| format | codes | scales (from the file's table) |
|---|---|---|
| `float8_e4m3fn`, `float8_e5m2` | FP8 | one scalar |
| `int8_tensorwise` | int8 | a scalar, or one per row |
| `mxfp8` | FP8 E4M3 | power-of-two scale per 32 weights |
| `nvfp4` | 4-bit float | FP8 scale per 16 weights, plus one global scalar |
| `convrot_w4a4`, `asym_w4a8_int8`, `w6a8_int8` | 4 to 6 bits | see the file |

For FP8 the scale is stored in the file as `weight_scale`. When ComfyUI has to quantize a weight again, for example after merging a LoRA into it (CU-212), `comfy/quant_ops.py` recalculates it as the largest absolute value divided by the format's maximum, `torch.finfo(dtype).max`, and with no scale given it uses 1. The quantize step in comfy-kitchen's eager backend multiplies by 1/scale, clamps to ± the format maximum and casts.

Not every card has a fast kernel for every format. `get_disabled_quant_formats` in `comfy/ops.py` lists the formats a device cannot compute natively, and `pick_operations` logs the split as native and emulated ops. A layer in a disabled format keeps its weights quantized in memory but dequantizes them to the compute dtype for the matrix multiply, which `QUANTIZATION.md` describes as dequantizing "for compute-dtype execution when a format's fast path is disabled". The same dequantizing path is taken when a layer has patch functions attached, such as a LoRA computed at run time (CU-212).

GGUF is a separate world. The specification in the ggml repository defines it as a binary file format for models, with metadata, tensor descriptions and a `ggml_type` for each tensor. ComfyUI's own loaders do not read it: `.gguf` is not in the list of file extensions the model folders accept, and a case-insensitive search of the v0.43.0 sources finds the word only in a MIME table, a cloud-deploy extension list, tests, and a startup warning in `main.py`. When dynamic VRAM is switched off by a command-line argument, `main.py` prints a warning that tells GGUF users to keep it on and to prefer native model formats, and says ComfyUI's native fp8, int8 and w4a8 formats "will be faster even if they are larger than your memory". That is the developers' statement. This lab measures no speed.

## Try it

Rounding costs about 6 dB of signal per bit you remove. Drop to fp8's three mantissa bits and read how much survives.

{{play:quant}}

And the graph that stores a model's weights in fp8 at load time, from a floating-point file that isn't fp8 already. It needs `UNETLoader`'s `weight_dtype`, which is under the node's advanced inputs.

{{graph:b_unet_fp8}}

## What goes wrong

- **A "4-bit" file is not half of an 8-bit file.** Scales cost bits too. GGUF Q4_0 is 4.5 bits per weight and not 4, and mxfp8 is 8.25 bits.
- **fp8 stored with no scale, on small weights.** A plain cast with scale 1 gave an error 0.69 times the size of the signal at std 0.0008 in the lab below. Formats and tools add the scale for this reason. Check that your conversion tool writes `weight_scale`.
- **Expecting a quantized file to be fast on every card.** `get_disabled_quant_formats` lists what your device cannot compute natively. Those layers are dequantized for the multiply, so you keep the small storage and lose the fast kernel. The console prints `Native ops: ... emulated ops: ...`.
- **Trying to load `.gguf` with a core loader.** Core's model folders don't list that extension. You need a pack, and the startup warning in `main.py` recommends native formats instead. CU-374 covers how the loaders differ.
- **Judging a format from the error number alone.** The numbers below are about weights, not pictures. Render the same seed with both files and look.

## Lab

The weights are synthetic: a 512 × 1024 Gaussian matrix with standard deviation 0.02. In the "with outliers" column we multiply 0.1% of the entries by 30 ourselves. Error is ‖W − Ŵ‖ / ‖W‖, and the last column applies the same measure to W X with random inputs X. First the √12 rule:

```text
int8, one scale: step 7.336e-04   predicted RMS error step/sqrt(12) 2.118e-04   measured 2.117e-04
```

Then granularity and bit width. The Q8_0 and Q4_0 rows re-implement the ggml reference quantizers, fp16 scale included:

```text
weights: Gaussian std 0.02, 512x1024.  outliers: 524 entries (0.1%) multiplied by 30, largest |w| 0.093 -> 1.768
format                bits/weight   weight error: clean   with outliers   output error with outliers
int8, one scale       8.00          0.0106                 0.1476          0.1457
int8, scale per row   8.03          0.0079                 0.0451          0.0446
int8, scale per 32    8.50          0.0053                 0.0094          0.0094
GGUF Q8_0             8.50          0.0053                 0.0094          0.0094
int4, one scale       4.00          0.1920                 0.7393          0.7413
int4, scale per row   4.03          0.1427                 0.4703          0.4733
int4, scale per 32    4.50          0.0970                 0.1157          0.1135
GGUF Q4_0             4.50          0.0859                 0.1074          0.1054
FP8 E4M3, one scale   8.00          0.0265                 0.0265          0.0265
FP8 E5M2, one scale   8.00          0.0526                 0.0520          0.0519
```

Read it in four steps. First, planting outliers turns the single-scale int8 error from 0.0106 into 0.1476, while a scale per 32 weights only moves from 0.0053 to 0.0094, for half a bit more per weight. Second, the output error follows the weight error closely. Third, going from 8 to 4 bits at a scale per 32 multiplies the error by about the ratio of the grid steps:

```text
clean data, scale per 32: int4 error / int8 error = 18.2   the step ratio 127/7 = 18.1
```

Fourth, FP8 has the same 0.0265 with and without outliers, because its spacing grows with the value. On clean data it is less precise than int8 with one scale (0.0265 against 0.0106), and with outliers it is far better (0.0265 against 0.1476). Neither format wins in general.

Q4_0 ties the sign of its scale to the largest weight in the block, so that weight takes the extreme code and comes back almost exactly:

```text
Q4_0: largest-magnitude weight of each block, worst relative error after the round trip 4.79e-04
```

That is the rounding of the fp16 scale. Now why FP8 needs a scale, by shrinking the weights:

```text
FP8 E4M3 error by weight size    std:   0.1000   0.0200   0.0040   0.0008
  scale 1 (plain cast)                0.0265   0.0330   0.1410   0.6905
  scale = amax/448                    0.0265   0.0265   0.0265   0.0265
```

At a standard deviation of 0.0008 a plain cast to E4M3 puts the weights almost entirely in the subnormal range, where the step is 2^-9, about 0.002 and larger than the weights themselves, so the error reaches 0.6905. With the scale, the error does not depend on the weight size. And the algebra: an int8 matmul accumulated in int64 and rescaled afterwards matches dequantize-then-multiply.

```text
int8 matmul with int64 accumulation, then rescaled, against dequantize-then-multiply: largest difference 8.9e-07 on outputs of size 0.516
```

Last, the memory for a billion weights from the published layouts:

```text
layout                                       bits/weight   GiB per billion weights
fp16 or bf16                                 16.00         1.86
ComfyUI float8_e4m3fn, scalar scale          8.00          0.93
ComfyUI mxfp8, 8-bit scale per 32            8.25          0.96
ComfyUI nvfp4, 8-bit scale per 16            4.50          0.52
GGUF Q8_0, fp16 scale per 32                 8.50          0.99
GGUF Q4_0, fp16 scale per 32                 4.50          0.52
GGUF Q4_K, 144 bytes per 256                 4.50          0.52
```

## What is contested

This lab measures weight and matmul error on synthetic Gaussian weights. It does not say how an image changes. Real checkpoints have their own weight distributions, and the outliers here are planted by us. Dettmers et al. report large outlier features in the hidden states of big language models, and we make no claim that image models have the same. Whether a given format keeps a given model's pictures good enough, and which one runs fastest, are empirical questions per model and per card. Rounding to the nearest code is also only one rule: GPTQ (Frantar et al. 2022) uses second-order information about the layer to choose the roundings, and we do not cover it.

## Sources

- [Dettmers, Lewis, Belkada, Zettlemoyer 2022. LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale](https://arxiv.org/abs/2208.07339)
- [Micikevicius et al. 2022. FP8 Formats for Deep Learning](https://arxiv.org/abs/2209.05433)
- [Frantar, Ashkboos, Hoefler, Alistarh 2022. GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers](https://arxiv.org/abs/2210.17323)
- [ggml, docs/gguf.md (commit facdc44)](https://github.com/ggml-org/ggml/blob/facdc44a67da17df4433adcc468b424f48e9ded2/docs/gguf.md)
- [ggml, src/ggml-common.h (commit facdc44)](https://github.com/ggml-org/ggml/blob/facdc44a67da17df4433adcc468b424f48e9ded2/src/ggml-common.h)
- [ggml, src/ggml-quants.c (commit facdc44)](https://github.com/ggml-org/ggml/blob/facdc44a67da17df4433adcc468b424f48e9ded2/src/ggml-quants.c)
- [ComfyUI v0.43.0, QUANTIZATION.md](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/QUANTIZATION.md)
- [ComfyUI v0.43.0, comfy/quant_ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/quant_ops.py)
- [ComfyUI v0.43.0, comfy/ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ops.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, folder_paths.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/folder_paths.py)
- [comfy-kitchen v0.2.40, eager backend quantization.py](https://github.com/Comfy-Org/comfy-kitchen/blob/v0.2.40/comfy_kitchen/backends/eager/quantization.py)
