# CU-107 - Models on disk: safetensors and families

**Objective.** Read a safetensors file by hand, say why loading one cannot run someone else's code while loading a pickle can, and explain how ComfyUI tells Stable Diffusion 1.5 from SDXL by looking at names and shapes alone. Taught by Bit Bandit.

## The idea

A model file is a bag of named tensors. A loader asks two questions in order: what is in here, and where do the bytes live? The safetensors format makes the first question cheap by putting a small index, the header, in front of the data.

The second idea is the family. The tensors in a checkpoint fit one architecture, and SD 1.x, SDXL, SD3 and Flux differ in their text encoders, their latent channels and the shapes of their layers. ComfyUI works out the family from the names and shapes of the tensors, not from the file name.

## The mechanism

The layout is short enough to hold in your head (the safetensors README).

- 8 bytes: N, an unsigned 64-bit integer, little-endian, the size of the header.
- N bytes: a JSON header that begins with `{` and may be padded with trailing spaces. Each tensor name maps to a dtype, a shape and `data_offsets` [BEGIN, END). A special key `__metadata__` may hold free-form strings. Duplicate keys are not allowed.
- The rest of the file is the byte buffer. The offsets count from its start, the buffer must be fully indexed with no holes, and the values are little-endian in row-major order.

The bytes of a tensor are the product of its shape times the bytes per value, and END − BEGIN must equal that. Little-endian means the least significant byte comes first: the bytes e0 00 00 00 00 00 00 00 read as 224, not as a huge number. Reading one tensor takes the header plus one slice, so a loader can list what a file of many gigabytes contains by reading only its start.

Now mend some damaged headers. These are the checks a loader does, on a file small enough to hold in your head.

{{play:sfheader}}

**Safe to load, and what that means.** A safetensors file contains data and no instructions. A loader reads N, parses JSON, checks the ranges and slices bytes. The README lists the checks, among them a header limit of 100 MB and a guarantee that the ranges do not overlap. A pickle is different: the file names a callable and its arguments, and unpickling calls it. The Python documentation says that the pickle module is not secure, that it is possible to construct malicious pickle data which will execute arbitrary code during unpickling, and that you should only unpickle data you trust. PyTorch's `torch.load` defaults to `weights_only=True`, which restricts the unpickler to tensors, primitive types, dictionaries and types you register, and its documentation still says never to load data from an untrusted source. "Safe" here means that the load step runs no code. It does not mean the weights are what the label claims.

## In ComfyUI

`comfy.utils.load_torch_file` opens `.safetensors` and `.sft` files in one of two ways. With DynamicVRAM active, which is the default on NVIDIA and on recent AMD drivers when comfy-aimdo works, its own `load_safetensors` reads the header and maps the file. Otherwise `safetensors.safe_open` reads the tensors one by one. Any other extension goes to `torch.load(..., weights_only=True)`.

`load_state_dict_guess_config` in `comfy/sd.py` then finds the prefix of the denoiser's keys, counts parameters, notes the dominant dtype, and calls `model_config_from_unet`. For the classic UNets, `detect_unet_config` in `comfy/model_detection.py` reads shapes: the first dimension of `input_blocks.0.0.weight` gives the channel count, `label_emb.0.0.weight` gives the size of the extra conditioning vector, and the cross-attention weight `attn2.to_k.weight` gives the width of the text context. Each family class in `comfy/supported_models.py` lists the values it expects, and `matches` in `supported_models_base.py` requires every listed entry to be equal. `SD15` expects a context of 768 and no extra vector. `SDXL` expects a context of 2048 and an extra vector of 2816. If nothing matches, ComfyUI warns that the file is not a checkpoint and tries it as a bare diffusion model, and if that fails it reports that it could not detect the model type.

These two graphs are the same seven nodes. The checkpoint loader finds out which family it has from the file, so the family asks you to change only the file and the size. The cfg and the sampler also differ here, because we chose them, not because the family needs it.

{{graph:sd15_txt2img}}

{{graph:sdxl_txt2img}}

The family also fixes what surrounds the denoiser. The latent has 4 channels for SD 1.x and SDXL and 16 for SD3 and Flux (`comfy/latent_formats.py`), and the text encoders differ (CU-104). A file trained against layers of one shape, a LoRA or a ControlNet for example, cannot be applied to layers of another shape.

## What goes wrong

- **`The safetensors file is corrupt/incomplete`.** ComfyUI adds this when the file is shorter than the header says, which usually means a cut-off copy or download. Compare the file's size with the source, and download it again. On the `safe_open` route it only adds it if the library's error contains `MetadataIncompleteBuffer`, and the safetensors 0.9.0-rc.1 we ran words it differently, so there you see `incomplete metadata, file not fully covered` alone.
- **`The safetensors file is corrupt or invalid`.** The first eight bytes read as an absurd size, which often means it isn't a safetensors file. Its message suggests a ckpt or pt renamed by hand. On the `safe_open` route it depends on the name `HeaderTooLarge` in the same way, and our run showed only `header too large`.
- **`Could not detect model type`.** No family matched the names and shapes. Your ComfyUI may be too old for this model, or the file may not be a denoiser at all (CU-114).
- **A LoRA or ControlNet won't apply.** It was made for another family, and the layer shapes differ.
- **You took a name at face value.** The family comes from the tensors, and "sdxl" in a file name proves nothing. Nor does `__metadata__`, since the author wrote that too.
- **A `.ckpt` from someone you don't know.** Prefer `.safetensors`. If there's no choice, remember that the safety of `weights_only=True` is limited and that PyTorch still warns against untrusted files.
- **Thinking `.safetensors` means safe to use.** The load step runs no code. The model can still be mislabelled, or a pack beside it can run code.

## Lab

The lab writes a real file into memory with `struct` and `json`, reads it back, damages it, and then does the family test on mock headers.

```text
file: 304 bytes = 8 (header length) + 224 (JSON header) + 72 (tensor bytes);  first 8 bytes: e0 00 00 00 00 00 00 00
```

```text
name           dtype  shape   offsets    bytes
layer1.weight  F32    [2, 3]  [0, 24]    24
layer1.bias    F16    [4]     [24, 32]   8
ids            I64    [5]     [32, 72]   40
__metadata__: {'format': 'pt'}
```

The offsets run on without a gap, 0 to 24, 24 to 32, 32 to 72, and the three byte counts add up to the 72 tensor bytes in the first line.

```text
one 1000 x 1000 float16 tensor: file 2,000,080 bytes, and 8 + 72 = 80 bytes are enough to learn its name, dtype and shape
```

Now the damaged copies. Each one is refused by the checks from the README before any value is read.

```text
checks on damaged copies
offsets shifted by 4               refused: hole or overlap before layer1.bias
shape no longer fits the bytes     refused: layer1.weight: byte range does not match shape and dtype
file cut short by 10 bytes         refused: the buffer is not the size the header says
header length claims 10^12 bytes   refused: header larger than the 100 MB limit
metadata value is a number         refused: __metadata__ values must be strings
```

A pickle is a program. The payload below only appends a string to a list, but it could have called anything.

```text
after pickle.loads on a harmless payload: ran = ['a function the loader never meant to call']
```

Last, the family test. The key names are the ones ComfyUI's detector reads, and the shapes are those of the SD 1.5 and SDXL base files. No weights are involved, only a name and a shape per tensor.

```text
file               read from the shapes                                                        family
SD 1.5 style file  {'model_channels': 320, 'context_dim': 768, 'adm_in_channels': None}        SD 1.x
SDXL style file    {'model_channels': 320, 'context_dim': 2048, 'adm_in_channels': 2816}       SDXL
VAE-only file      None                                                                        no match
```

The two UNets share the first number and differ in the other two, which is enough. A VAE-only file has no `input_blocks.0.0.weight`, so nothing matches.

```text
1,000,000,000 values stored as   bytes            GiB
F32                              4,000,000,000     3.73
F16                              2,000,000,000     1.86
BF16                             2,000,000,000     1.86
```

File size is values times bytes per value. Halving the width of the number halves the file, and CU-210 shows what it costs in precision.

## What is contested

The lab's matcher reads three shapes and knows two families. The real `detect_unet_config` runs for over a thousand lines in v0.43.0, with its own test for many architectures, so do not take the lab as a description of how complete the detection is. A header is also text written by the file's author, and `__metadata__` is free-form. Treat it as data, not as instructions. A data-only format is safe to parse, but whether a model does what its name says is a separate question, and no format answers it.

## Sources

- [safetensors README, Format section](https://github.com/huggingface/safetensors/blob/62e4d8b86063a6e5f8967547fa09a09f67420e2a/README.md)
- [pickle, Python object serialization, Python 3.15 documentation](https://docs.python.org/3/library/pickle.html)
- [torch.load, PyTorch 2.15 documentation](https://docs.pytorch.org/docs/2.15/generated/torch.load.html)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/model_detection.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_detection.py)
- [ComfyUI v0.43.0, comfy/supported_models.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/supported_models.py)
- [ComfyUI v0.43.0, comfy/supported_models_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/supported_models_base.py)
- [ComfyUI v0.43.0, comfy/latent_formats.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/latent_formats.py)
