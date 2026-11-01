# CU-210 - Precision: fp32, fp16, bf16, fp8

**Objective.** Read a float format's limits from its bits, predict where each format fails, and justify the rule "merge first, quantize after". Taught by Bit Bandit.

## In plain words

A computer stores a number in a fixed number of bits. Fewer bits save memory and lose exactness. There are two ways to lose: rough numbers, and numbers that can't be big or small enough. Models have billions of numbers, so saving half the memory matters a lot, and most small rounding errors go unseen. Then a certain sum goes wrong and you get a black picture. This lesson shows where.

{{play:quant}}

## The idea

A float stores a sign, an exponent that sets the range, and a mantissa that sets the precision. Spacing between neighbouring values grows with size. So a number can be stored only approximately, and a small number added to a big one may disappear.

## The maths

```
value = ± (1 + m / 2^p) · 2^e      p mantissa bits
machine epsilon = 2^(−p)           gap between 1 and the next value
```

```text
format  bits  mantissa  epsilon      largest      smallest normal
fp32    32    23        1.1921e-07   3.4028e+38   1.1755e-38
fp16    16    10        9.7656e-04   6.5504e+04   6.1035e-05
bf16    16    7         7.8125e-03   3.3895e+38   1.1755e-38
```

The formats fail differently. fp16 has more precision, but its largest value is 65,504, and from 65,520 up it overflows to inf. bf16 has the range of fp32 and only 7 mantissa bits. They are not "the same size, so the same". FP8 E4M3 (Micikevicius et al. 2022) has 3 mantissa bits, and a maximum of 448.

## In ComfyUI

`unet_dtype`, `vae_dtype` and `should_use_bf16` in `comfy/model_management.py` choose formats. You can force them, with flags such as `--bf16-unet`. The flag `--fp8_e4m3fn-unet` says "store": weights stay in FP8, and `manual_cast` in `comfy/ops.py` casts them when they are used, so computation runs in a wider format unless the device supports FP8 compute. The help text for `--fp16-vae` warns it "might cause black images". The third experiment below shows one way that can happen.

You can also choose per model. `UNETLoader` has a `weight_dtype` menu with `default`, `fp8_e4m3fn`, `fp8_e4m3fn_fast` and `fp8_e5m2`.

{{graph:b_unet_fp8}}

## What goes wrong

- **Black images or NaN after switching to fp16.** An inf or NaN spreads through everything after it. Try without `--fp16-vae`, or use bf16. CU-291 walks through it.
- **Merging quantized models.** Small updates turn into rounding noise, as experiment 1 shows. Merge unquantized weights, in bf16 or fp16 at the lowest, and quantize afterwards. The bf16 row shows that an update this small is already as big as the rounding there, so use fp16 or fp32 for very small changes if you can.
- **A LoRA seems weak or noisy on an fp8 model.** Its small changes meet coarse weights. Compare with the same LoRA at default precision before you blame the LoRA.
- **Assuming fp8 means fp8 compute.** It stores in fp8 and usually computes wider, through `manual_cast`. Memory and speed aren't halved in the same way.
- **Reading "16-bit" as one thing.** fp16 and bf16 fail differently. fp16 runs out of range and bf16 runs out of precision.
- **Summing many tiny values in a low-precision float.** Experiment 2 lost the entire total. Sum first in a wider format.

## Lab

**1. A small update to a weight.** This is what a LoRA or a merge does.

```text
weight std 0.05, update std 1e-4: how much of the update survives when the sum is stored in each format
fp32   captured share of the update 1.0000   RMS error of the update 1.26e-09
fp16   captured share of the update 1.0000   RMS error of the update 1.46e-05
bf16   captured share of the update 0.9983   RMS error of the update 1.01e-04
fp8    captured share of the update 0.9830   RMS error of the update 5.18e-04
```

Rounding is unbiased on average, so the update survives in the mean. But look at the noise. The update has size 1e-4. In bf16 the rounding error is as large as the update, and in FP8 it is five times larger. So merge in full precision and quantize afterwards. Quantizing first turns small updates into noise (the same applies to LoRA on stored FP8 weights, if patches are not computed before the conversion).

**2. Accumulation.**

```text
start at 1.0 and add 0.0001 ten thousand times; the exact answer is 2.0
fp32   2.00017
fp16   1.00000
bf16   1.00000
bf16 with the sum done in fp32 first: 2.00000
```

In 16 bits, each addition is too small to change the value, so a hundred percent of the total is lost. The order of operations matters, and fp32 has a small error too.

**3. Range.**

```text
value 70000 stored as
  fp16: inf
  bf16: 70144.0
fp16: 300^2 = inf   then normalising: [nan, 0.0]
```

One overflow gives an inf, then a NaN, and a NaN spreads through every later operation. In an image pipeline that can end as a black or broken result. bf16 rounds to 70144 but stays usable, which is one reason it is the safer 16-bit choice for many models.

```text
the value 1e-8 stored in fp16, below its smallest step: 0.0  bf16 keeps it: 1.001e-08
```

## What is contested

Whether bf16 or fp16 gives better results on a given model is an empirical matter, and speed depends on the hardware. Do not generalise from these isolated operations to a whole network.

## Sources

- [Micikevicius et al. 2022. FP8 Formats for Deep Learning](https://arxiv.org/abs/2209.05433)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ops.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
