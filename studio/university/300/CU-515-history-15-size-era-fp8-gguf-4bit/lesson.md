# CU-515 - History 15: The size era: FP8, GGUF and 4-bit formats arrive

**Objective.** Place the formats that shrank models in the order they arrived, say what problem each one answered, read the same outlier test across all of them, and find which of them ComfyUI runs itself. Taught by Bit Bandit.

## The idea

Models grew faster than graphics cards. A 14 billion parameter model in fp16 is 26.1 GiB of weights, more than many cards hold. So from about 2019 people started asking how few bits a weight really needs. Here is the order, with the arXiv dates.

- **May 2019, bf16.** "A Study of BFLOAT16 for Deep Learning Training". Its abstract gives two reasons: the same range as fp32 and simple conversion. It costs the same 16 bits as fp16, so it saved no memory against fp16. The lab shows it rounds more coarsely too.
- **August 2022, int8.** "LLM.int8()". Their abstract says it cuts the memory "for inference by half", on a 175B model.
- **September 2022, fp8.** "FP8 Formats for Deep Learning" sets out E4M3 and E5M2. An fp8 weight still has an exponent. It only has 3 or 2 mantissa bits.
- **October 2022, 3 and 4 bits.** "GPTQ" reports going "down to 3 or 4 bits per weight", with "negligible accuracy degradation" on language models, measured against their own baseline.
- **June 2023, choosing which weights matter.** "AWQ" reports that protecting 1% of salient weights "can greatly reduce quantization error".
- **GGUF.** A file format, and not a way of rounding. The ggml specification says it stores "models for inference with GGML", in a single file with all the information needed to load, and it lists types such as `Q8_0` and `Q4_K`. The int8, GPTQ and AWQ papers are about language models, and their claims don't transfer automatically to pictures.

## The mechanism

CU-211 does the formulas. Here is the one idea that runs through this history. Every format has to answer: what do the weights share, and what happens to the rest when one is large?

```
one scale per tensor:       scale = max|w| / qmax       one outlier widens the grid for everyone
a scale per block:          scale = max|block| / qmax   an outlier hurts only its own block
a tiny float:               spacing grows with the value, and a scale moves weights to the useful part
```

So 4-bit formats got usable once they stopped sharing one scale, and paid for the extra scales in bits.

```
bits per weight = code bits + scale bits / weights per scale
```

## In ComfyUI

Formats reach ComfyUI as a small JSON tensor per layer named `comfy_quant`. It is a file entry, not a module, and `tests-unit/comfy_quant` is a test folder.

- **The registry.** `QUANT_ALGOS` in `comfy/quant_ops.py` lists `float8_e4m3fn`, `float8_e5m2`, `nvfp4` (group size 16), `mxfp8` (group size 32), `int8_tensorwise`, `convrot_w4a4`, `asym_w4a8_int8` and `w6a8_int8`. The kitchen library does the fast kernels. If it is missing, the log says that fp8 and fp4 support will not be available.
- **Choosing at load.** `UNETLoader` in `nodes.py` has `weight_dtype`, with `fp8_e4m3fn`, `fp8_e4m3fn_fast` and `fp8_e5m2`. There are also the flags `--fp8_e4m3fn-unet` and friends in `comfy/cli_args.py`.
- **Can this card do it?** `supports_fp8_compute` in `comfy/model_management.py` answers false on CPU, and for NVIDIA it wants a card with compute version 8.9 or newer. `supports_nvfp4_compute` wants 10 or newer.
- **When it can't.** `get_disabled_quant_formats` in `comfy/ops.py` lists what the device can't do. Those layers keep their small weights and set `_full_precision_mm`, so they expand for the multiply. A test checks this: `test_int8_disabled_on_unsupported_device_falls_back_to_full_precision`. You keep the saved memory and lose the fast kernel. CU-211 has more detail.
- **GGUF.** Core doesn't load it. A search finds no GGUF loader in `nodes.py` or `comfy/`. `main.py` mentions it once, in a warning that recommends native formats. You need a pack, and we name none here.

See what mantissa bits cost. Drop to fp8's three and read how much signal survives.

{{play:quant}}

This graph stores a model's weights in fp8 at load time.

{{graph:b_unet_fp8}}

## What goes wrong

- **You judge a format by its bit count.** In the lab, int4 with one scale has error 0.192, and with a scale per 16 it has 0.085. Same code size, very different result. That is what block scales buy, at 1 bit per weight more.
- **You read an 8-bit error number as a picture.** These are numbers on made-up weights. Render the same seed with both files and look.
- **fp8 with no scale wrecks small weights.** A plain cast gave error 0.689 in the lab, and 0.026 with a scale. Check that your tool writes `weight_scale`.
- **You think a small file means fast everywhere.** On a card with no fast kernel the layers expand to multiply. The console's native and emulated counts show it (`pick_operations`).
- **You merge after quantizing.** Merge from unquantized parents, then quantize, so you round once. The `mergeorder` lab in the LoRA track shows it.
- **You try to load a `.gguf` with a core loader.** It won't list. You need a pack. Read it before you run it (CU-374).
- **You count only the denoiser.** The table below is weights alone. The text encoder and VAE are extra, and working memory on top of that. CU-305 does the budget.

## Lab

The weights are synthetic: a 512 × 1024 Gaussian matrix we made, with std 0.02. In the last column 0.1% of them are 30 times larger. Error is ‖W − Ŵ‖ / ‖W‖. The fp16, bf16 and fp8 rows use real torch dtypes, and the fp8 scale follows the `recalculate` branch in `comfy/quant_ops.py`. The two block rows are a simple stand-in for block formats, not any one format's exact code. Their bits assume a 16-bit scale.

```text
format                 bits per weight   error, clean weights   error, with outliers
fp16                   16.00             2.07e-04               2.11e-04
bf16                   16.00             1.66e-03               1.66e-03
fp8 e4m3, scaled       8.00              2.65e-02               2.74e-02
fp8 e5m2, scaled       8.00              5.26e-02               5.20e-02
int8, one scale        8.00              1.06e-02               1.49e-01
int4, one scale        4.00              1.92e-01               7.33e-01
int4, a scale per 16   5.00              8.51e-02               8.98e-02
int4, a scale per 32   4.50              9.70e-02               1.17e-01
```

The whole history is in that table. Eight bits with one scale goes from 0.0106 to 0.149 with outliers, because the outliers stretch everyone's grid. fp8 hardly notices them: 0.0265 and 0.0274. Four bits with one scale is ruined: 0.733. Four bits with block scales holds at 0.090. Note that clean int8 beats clean fp8 here, because fp8 spends bits on range these well-behaved weights don't use. Then the outlier line, the missing scale, and the range:

```text
one outlier in a thousand: int4 with one scale goes from 0.192 to 0.733, int4 with a scale per 16 from 0.085 to 0.090
fp8 e4m3 on weights of std 0.0008: plain cast error 0.689, with a scale 0.026
largest value: fp8 e4m3 448, fp8 e5m2 57344, fp16 65504
```

Last, sizes. Weights only.

```text
parameters   fp32 GiB   fp16 or bf16   fp8 or int8   4.5 bits
1.3          4.8        2.4            1.2           0.7
5.0          18.6       9.3            4.7           2.6
14.0         52.2       26.1           13.0          7.3
```

Those are counts of weights times bits, and real files add a little. 1.3 B and 14 B are the two sizes in Wan's abstract. On our made-up weights this says what rounding does to numbers. It doesn't say what it does to a picture.

## What is contested

How low is too low? The GPTQ and AWQ abstracts report good results on language models. Their test is language benchmarks. A picture model's errors show up differently, and we haven't measured that here.

Whether GGUF or native formats are faster on your machine is not something this lesson tested. ComfyUI's own warning in `main.py` says its native fp8, int8 and w4a8 formats "will be faster even if they are larger than your memory". That is the project's claim.

## Sources

- [Kalamkar et al. 2019. A Study of BFLOAT16 for Deep Learning Training](https://arxiv.org/abs/1905.12322)
- [Dettmers et al. 2022. LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale](https://arxiv.org/abs/2208.07339)
- [Micikevicius et al. 2022. FP8 Formats for Deep Learning](https://arxiv.org/abs/2209.05433)
- [Frantar et al. 2022. GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers](https://arxiv.org/abs/2210.17323)
- [Lin et al. 2023. AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration](https://arxiv.org/abs/2306.00978)
- [Team Wan 2025. Wan: Open and Advanced Large-Scale Video Generative Models](https://arxiv.org/abs/2503.20314)
- [ggml, the GGUF specification](https://github.com/ggml-org/ggml/blob/facdc44a67da17df4433adcc468b424f48e9ded2/docs/gguf.md)
- [ComfyUI v0.43.0, comfy/quant_ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/quant_ops.py)
- [ComfyUI v0.43.0, comfy/ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ops.py)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
