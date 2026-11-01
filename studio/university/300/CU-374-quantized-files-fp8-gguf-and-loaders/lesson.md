# CU-374 - Quantized files: fp8, GGUF, and how loaders treat them

**Objective.** Tell what kind of quantized file you have and how ComfyUI will treat it, and explain with numbers why merging comes before quantizing. Taught by Bit Bandit.

## Three roads

CU-211 covers the maths of each format. This lesson is about the files and what a loader does with them.

**1. A plain file, stored smaller at load.** `UNETLoader` has a `weight_dtype` input under its advanced options: `default`, `fp8_e4m3fn`, `fp8_e4m3fn_fast` and `fp8_e5m2`. Choosing one sets the storage format when the model loads, from a file of any float type. The `fast` one also asks for fp8 operations where the card supports them. You can also set it for every model with `--fp8_e4m3fn-unet`. You need no special file for this.

{{graph:b_unet_fp8}}

**2. A native quantized file.** `QUANTIZATION.md` describes it: an ordinary safetensors file with normal names, the quantized `weight`, scale tensors, and a small `comfy_quant` tensor on each module holding JSON such as `{"format": "float8_e4m3fn"}`. A file can mix formats, and leave some layers as plain floats. The normal loaders read it. They spot the data, and `pick_operations` logs the split:

```
Using mixed precision operations
Native ops: float8_e4m3fn, int8_tensorwise, ...
```

Those formats have `emulated ops` if your card can't compute them. Emulated layers keep small storage and dequantize for the multiply.

For a plain fp8 file, `unet_dtype` makes the choice. fp8 stays if the card has fp8 compute, or if twice the parameter count won't fit. Otherwise it falls through to other types and you don't save the memory, so a fp8 file on a card with lots of room can end up in a larger format.

**3. GGUF.** A different container, from the llama.cpp world. Core does not read it. `.gguf` isn't among the extensions the model folders list. You need a pack. One we read as text is calcuis/gguf (MIT). Its loader reads tensors with a GGUF reader, then defines its own layer classes on top of `comfy.ops.manual_cast`, which decode each weight when the layer is called. Other packs may differ. So a GGUF file travels a pack's code path, not core's.

Be aware of what core says about this. When dynamic VRAM is turned off by a flag, `main.py` warns: "If you use gguf we recommend keeping dynamic vram enabled and using native ComfyUI model formats instead. ComfyUI native formats like fp8, int8 and w4a8 will be faster even if they are larger than your memory." That's the developers' statement, and we didn't test it. If you have both forms of a model, time both on your own card.

## Which to use

| you have | do this |
|---|---|
| a plain fp16 file, and memory is tight | try `weight_dtype` fp8 first, no new file needed |
| a native quantized file | use the normal loader, and read the `Native ops` line |
| only a GGUF | use a pack you've read (CU-380) |
| both a GGUF and a native file | test both, on one seed |

## Why merge first, quantize after

Rounding is permanent. A merged model is arithmetic on weights, so if the inputs are already rounded, you do the arithmetic on errors and then round again. For a blend the extra error is modest. For a difference it is large, because subtracting two similar models leaves a small result, while the rounding errors stay their full size.

The rule is simple: merge unquantized fp16, bf16 or fp32, then quantize the result once. Keep the unquantized source, since you can't get those bits back later.

{{graph:d_merge_add_difference}}

{{play:quant}}

## What goes wrong

- **A `.gguf` doesn't show in a core loader menu.** Core doesn't list it. That's not a broken install.
- **An fp8 file used more memory than expected.** On a card with room and no fp8 compute, `unet_dtype` may pick another type. Read the `model weight dtype` line.
- **Merging quantized files.** It runs, and the result is worse than it looks in a single test. Go back to unquantized sources.
- **A LoRA on quantized weights looks weaker or different.** A LoRA's change can be close to the size of the rounding already there, as the lab shows. Try with the unquantized model, and compare.
- **Saving a "smaller" model and throwing out the source.** Quantizing twice adds error. Keep the source.

## Lab

Real torch fp8, synthetic weights. Memory first, from published layouts:

```text
bytes per weight, and one billion weights
  fp32               4.0000   3.73 GB
  fp16 or bf16       2.0000   1.86 GB
  fp8 e4m3 or e5m2   1.0000   0.93 GB
  GGUF Q8_0          1.0625   0.99 GB
  GGUF Q4_0          0.5625   0.52 GB
  nvfp4              0.5625   0.52 GB
```

The `comfy_quant` entry is plain:

```text
the comfy_quant entry from QUANTIZATION.md: one small uint8 tensor holding JSON
  stored as torch.uint8, shape (27,), reads back as {'format': 'float8_e4m3fn'}
```

What a loader must do with one fp8 layer:

```text
what the loader does, step by step, with one fp8 layer
  on disk or in memory: torch.float8_e4m3fn, 262144 bytes, scale 0.000208
  for a plain matmul: cast to fp32, multiply by the scale. weight error 0.0265
```

Now merge order. Quantizing inputs first raises a blend's error, and ruins a difference: 12% against none.

```text
merge first, quantize after, against the other way round
  case                               weight error against the true unquantized merge
  50/50 merge, then quantize once     0.0263
  quantize both, merge, quantize      0.0371
  add-difference term (A - base), from unquantized:   0.0000
  add-difference term (A - base), from fp8 inputs:    0.1212
```

A LoRA-sized change, added at three points:

```text
a small LoRA-sized change on a weight: added before or after rounding
  add, then quantize once             0.0264
  quantized weight, add at run time   0.0265
  quantized weight, add, requantize   0.0318
```

```text
does the change survive? the size of the change against the size of the rounding
  change 0.256   rounding error already in the file 0.271
```

That last pair says something uncomfortable: on this synthetic case, the change is smaller than the rounding error already in the file. They are spread differently, so the change isn't lost, but it isn't a small signal against a clean background either. Finally `unet_dtype`'s choice, ported:

```text
unet_dtype's choice for a file whose weights are fp8, ported: fp8 stays if the card computes in fp8, or if double the size would not fit
  fp8 compute True  params 6e+09 room 2e+10: stays fp8
  fp8 compute False params 6e+09 room 2e+10: falls through to the other types
  fp8 compute False params 6e+09 room 8e+09: stays fp8
```

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, QUANTIZATION.md](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/QUANTIZATION.md)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ops.py)
- [ComfyUI v0.43.0, comfy/quant_ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/quant_ops.py)
- [ComfyUI v0.43.0, folder_paths.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/folder_paths.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [calcuis/gguf, pig.py](https://github.com/calcuis/gguf)
- [ggml, docs/gguf.md (commit facdc44)](https://github.com/ggml-org/ggml/blob/facdc44a67da17df4433adcc468b424f48e9ded2/docs/gguf.md)
