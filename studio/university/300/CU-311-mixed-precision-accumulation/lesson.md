# CU-311 - Mixed precision: where accumulation hides

**Objective.** Predict when a sum in a small float format stops moving, find where such sums hide in a model, and choose formats for training. Taught by Bit Bandit.

## The rounding that loses numbers

A float keeps a fixed number of mantissa bits. So the gap between neighbouring numbers grows with the size of the number. Near 1 in fp16 that gap is 2^-10, about 0.001. Add something smaller than half a gap and the result rounds straight back.

```
1.0 + 0.0001 = 1.0 in fp16
```

Nothing fails, and nothing warns you. The penny fell through a hole that is too wide for it.

One add loses almost nothing. A long sum is different, because the running total gets larger while each new number stays small. Sooner or later every add falls through. That is accumulation error, and it is the reason this lesson exists.

{{play:accum}}

## Where the sums are

**Inside a matmul.** Each output of a linear layer is a dot product: a sum of thousands of terms. PyTorch can compute terms in fp16 and add them up in a wider format. ComfyUI has a switch for the narrow way: `--fast fp16_accumulation`, under a flag whose help says "untested and potentially quality deteriorating optimizations". It sets `torch.backends.cuda.matmul.allow_fp16_accumulation`. Code in `comfy/ops.py` and `comfy/ldm/seedvr/vae.py` has its own fast path for it. `_fp16_linear_wanted` asks for that flag, an fp16 input and CUDA, and the plain linear path also checks that training is off. The lab shows what the narrow sum can do. Whether it matters for your picture is a test for your eyes.

**Between steps, in a training loop.** Gradient accumulation sums gradients over batches. The total is a running sum, so keep it wide. An `fp16` accumulator loses small late gradients after large early ones.

**In one gradient.** The smallest positive number fp16 can hold is about 6e-8. A gradient smaller than that becomes exactly 0. `GradScaler` multiplies the loss by a big number first to lift gradients into range, then undoes it. bf16 has fp32's range, so it doesn't underflow like that, but it has only 7 mantissa bits. A comment in `nodes_train.py` notes that GradScaler handles float16 gradients, not bfloat16. The same file logs a warning if you train an fp16 model with `fp16_accumulation` on: it "can be numerically unstable during training and may cause NaN values".

## In ComfyUI

For image making, formats mainly mean memory. fp16 or bf16 weights and activations are the normal path, and flags like `--bf16-vae` choose one. `--fp16-vae` warns that it "might cause black images", which is range rather than accumulation.

For training, the core nodes let you choose. `training_dtype` is `bf16`, `fp32` or `none`, and `lora_dtype` is `bf16` or `fp32`, both defaulting to `bf16`. Run the graph with these in mind:

{{graph:sd15_train_lora}}

`lora_compute_dtype` in `model_management.py` decides the format for merging LoRA patches: fp16 when `should_use_fp16` says so, otherwise fp32. That is the same concern in a place you might not look.

## What goes wrong

- **A LoRA barely changes after many steps at a very low learning rate.** Compare the size of an update with the gap between numbers at the weight's size. A format with few mantissa bits can swallow an update. Try `lora_dtype` fp32.
- **`lora_dtype` bf16 with a tiny learning rate.** bf16's gap near 1 is 0.0078, so a small update to a weight near 1 rounds away entirely. Weights in LoRAs tend to be small, which helps. Check by measuring whether weights move.
- **Loss becomes NaN in fp16.** fp16's largest number is 65,504. That is range, not accumulation. Try bf16 or fp32.
- **A `--fast` flag changed your pictures.** It says it may. Turn it off and compare the same seed.
- **Treating fp16 as "unsafe".** The lab shows a real effect in long sums. It does not show that fp16 inference is bad. Most of the time fp16 inference looks fine: test it on your own graph.

## Lab

All numbers here are from a run on a CPU.

```text
format   mantissa bits   spacing just above 1 (eps)   smallest normal   largest
fp16     10              9.766e-04                    6.104e-05         6.550e+04
bf16     7               7.812e-03                    1.175e-38         3.390e+38
fp32     23              1.192e-07                    1.175e-38         3.403e+38
```

```text
1.0 + 0.0001 in fp16 = 1.000000    in fp32 = 1.000100
```

The running sum. The true totals are 0.1 and 2.0.

```text
add 0.0001 again and again, rounding after each add. The true total is count x 0.0001
format   count     result     stopped moving at
fp16     1000      0.1058     never
fp16     20000     0.2500     add number 2181
bf16     1000      0.0312     add number 273
bf16     20000     0.0312     add number 273
fp32     1000      0.1000     never
fp32     20000     2.0002     never
```

fp16 stalls at exactly 0.25. Above 0.25, half a gap is 2^-13 = 0.000122, which is larger than 0.0001. bf16 stalls far earlier. fp32 doesn't stall inside this range.

The same thing inside one dot product: 4096 terms, each computed in fp16, summed two ways.

```text
the same loss inside one matmul: a dot product of 4096 terms, summed in the format named
true -0.16062   fp16 terms summed in fp32 -0.16061   fp16 terms summed in fp16 -0.15454
error: fp32 sum 0.00000   fp16 sum 0.00608
```

This is a plain loop on a CPU. A real GPU kernel may order its sum differently. A toy gradient sum, with one large early batch followed by small ones:

```text
a toy gradient sum: 64 small batches on one weight tensor
relative error of the summed gradient: fp16 1.88e-03   fp32 2.30e-07
```

And why `GradScaler` exists:

```text
gradients small enough to vanish: the reason GradScaler exists
  1e-05 stored as fp16: 1.001e-05   scaled by 65536 first, then back: 9.999e-06
  1e-07 stored as fp16: 1.192e-07   scaled by 65536 first, then back: 1.000e-07
  1e-08 stored as fp16: 0.000e+00   scaled by 65536 first, then back: 9.997e-09
```

## Sources

- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ops.py)
- [ComfyUI v0.43.0, comfy/ldm/seedvr/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/seedvr/vae.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_train.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_train.py)
- [Micikevicius et al. 2022. FP8 Formats for Deep Learning](https://arxiv.org/abs/2209.05433)
- [PyTorch 2.15, torch.backends](https://docs.pytorch.org/docs/2.15/backends.html)
