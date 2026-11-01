# CU-410 - Quantization error propagation through layers

**Objective.** Write the error of a quantized layer exactly, then measure how rounding every layer adds up with depth, and what makes it grow. Taught by Bit Bandit.

## One layer is exact algebra

Replace W with its rounded copy W + ΔW. For a linear layer:

```
y_q = (W + ΔW) x = W x + ΔW x
error = ΔW x
```

No mystery there. The output error is the weight error times the input. So larger inputs give larger absolute errors, and the error depends on the input as well as the weights.

## Two layers show the mechanism

Feed that error into the next layer, which also has its own rounding:

```
y₂_q = (W₂ + ΔW₂)(y₁ + ε₁)
     = W₂ y₁  +  W₂ ε₁  +  ΔW₂ y₁  +  ΔW₂ ε₁
error =          carried    new         tiny
```

Three terms. **Carried:** the earlier error, multiplied by this layer. If the layer stretches its input, the error gets stretched too. If it squashes, the error shrinks. **New:** this layer's rounding on the clean signal. **Tiny:** error on error, usually negligible.

So there are two forces. Each layer adds its own error, and each layer scales what came before.

## What that predicts

If layers neither stretch nor shrink much, and each rounding is unrelated to the others, their errors add like independent noise, so they grow with the square root of depth. If layers stretch, errors can grow quickly. The lab tests both.

{{play:quant}}

That lab shows the cost of each bit at one layer. The rest of this lesson is about what those bits do across many layers.

## In ComfyUI

Weights come from the file. `QUANTIZATION.md` describes the format, and `pick_operations` in `comfy/ops.py` picks mixed-precision operations when a file has quantization data. A checkpoint "can mix quantization formats and ordinary floating-point layers", so makers can keep sensitive layers in full precision. `full_precision_matrix_mult` keeps quantized storage and dequantizes for the multiply. Biases remain floating point.

Calibration deserves care, because people often say quantizing needs it. Weight rounding doesn't: the scale comes from the weights themselves. `QUANTIZATION.md` puts it this way: "Calibration is needed to choose representative fixed activation scales, not to use formats with dynamic activation scaling." So calibration matters when activations have a fixed scale, as in FP8 `input_scale`, and not for weight rounding on its own.

If your card can't compute a format, ComfyUI dequantizes to compute it. A test named `test_int8_disabled_on_unsupported_device_falls_back_to_full_precision` covers this for int8. That changes speed. It doesn't undo rounding, because the weight has already lost its bits in the file.

{{graph:b_unet_fp8}}

## What goes wrong

- **Testing a quantized layer alone and calling it fine.** The final output carries every layer's error. Test the whole model, on real prompts.
- **Quantizing a file twice.** Rounding again on rounded weights adds new error, which CU-374 measures. Keep the unquantized source.
- **Comparing errors from different inputs.** Output error depends on the input, so use the same seed and prompt for both files.
- **Expecting skip connections to fix bits.** In the toy they cut the error, by carrying a clean path. They don't help everything, and the lab's stack isn't a real model.
- **Blaming quantization for a washed-out picture when it is the format's scale.** A plain cast with no scale loses small weights. CU-211 shows this.

## Lab

Synthetic weights, with int8 or int4 rounding per tensor. First the exact algebra:

```text
one layer: y = W x. The error of the output is exactly dW x, which is linear in the weight error
  weight error 0.01089   output error 0.01087   |dW x| matches: 3.7e-15
```

The `matches` figure is the gap between the measured error and ΔW x. It is at floating-point rounding, so the formula is exact.

Now a stack. Each layer has a tanh after it. Gain is roughly how much each matrix stretches its input.

```text
error at the output of a stack, every layer int8, by depth and by how much each layer stretches its input
depth   gain 0.5   gain 1.0   gain 2.0   gain 4.0
    1    0.01147    0.01164    0.01243    0.01459
    2    0.01441    0.01453    0.01548    0.01963
    4    0.01993    0.01999    0.02103    0.03155
    8    0.02866    0.02870    0.02994    0.06698
   16    0.04074    0.04079    0.04199    0.23636
gain 1: depth 16 / depth 1 = 3.51.  errors that add like independent noise would give sqrt(16) = 4
```

At gains up to 2 the error grows slowly with depth, not far from the square root, and it isn't chaotic. At gain 4 it grows much faster, and depth starts to hurt. tanh limits how far values can go, which is one reason this toy doesn't explode further, so don't read too much into the exact numbers.

Does an early layer matter more?

```text
only one layer quantized, 8 layers, gain 2: does an early error matter more than a late one?
  layer 0: output error 0.01222
  layer 3: output error 0.01179
  layer 7: output error 0.00971
```

Somewhat, in this toy. And bits, and skip connections:

```text
bits: same stack, 8 layers, gain 2, every layer
  int8 0.03054   int4 0.55012   ratio 18.0   the step ratio 127/7 = 18.1
```

```text
skip connections: x + f(x), as in residual blocks, 16 layers, gain 1, int8
  plain 0.04045   with skips 0.01501
```

Going from int8 to int4 multiplied the output error by the same 18 as the step ratio. The last lines show that no input was used to pick the scale:

```text
weight rounding needs no calibration data. The scale comes from the weights themselves:
  scale for layer 0 = 0.001033, no input was looked at
```

## Sources

- [ComfyUI v0.43.0, QUANTIZATION.md](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/QUANTIZATION.md)
- [ComfyUI v0.43.0, comfy/ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ops.py)
- [ComfyUI v0.43.0, comfy/quant_ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/quant_ops.py)
- [ComfyUI v0.43.0, tests-unit/comfy_quant/test_mixed_precision.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/tests-unit/comfy_quant/test_mixed_precision.py)
- [Frantar, Ashkboos, Hoefler, Alistarh 2022. GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers](https://arxiv.org/abs/2210.17323)
