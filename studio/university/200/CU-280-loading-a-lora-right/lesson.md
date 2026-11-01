# CU-280 - Loading a LoRA right

**Objective.** Pick the right loader, set its strengths, chain LoRAs, and read the log to see whether the file actually fitted your model. Taught by Tinker Tune.

## The idea

A LoRA file is a list of named changes to layers. Loading it does two things: match names in the file to weights in your model, and record "add this much" against each match. No weights change at that moment. The change is applied later, when the model is loaded for sampling (CU-212).

The matching is where people get caught, because a failed match is not an error. Your graph runs, your picture comes out, and the only trace is a line in the log.

## The two loaders

| | "Load LoRA (Model and CLIP)", `LoraLoader` | "Load LoRA", `LoraLoaderModelOnly` |
|---|---|---|
| patches | the denoiser and the text encoder | the denoiser only |
| strengths | `strength_model`, `strength_clip` | `strength_model` |
| wires | MODEL and CLIP in, MODEL and CLIP out | MODEL in, MODEL out |

Both default to strength 1.0, and range from −100 to 100. Negative is allowed.

Core v0.43.0 also has `LoadLoraModel` and `LoadLoraTextEncoder`, which take several rows in one node. They call the same function.

With `LoraLoader`, everything after it must use its outputs. Wire the prompts to its CLIP and the sampler to its MODEL.

{{graph:sd15_lora}}

If you wire your prompt to the checkpoint's CLIP instead, the patch never touches your prompt, and nothing complains.

```text
strength_clip 1.0, prompt encoded through the loader's CLIP: output moved 0.7246   through the checkpoint's CLIP: 0.0
```

Use the model-only loader when the file has no text-encoder part, or when you don't want it. Our own trained LoRA is that kind (CU-281). Check your file's notes.

{{graph:d_lora_model_only}}

## Chains

Take the MODEL from one loader into the next. Each adds its own entry to the list for each weight, and the sum is applied in order.

```text
two LoRAs chained, in either order: largest difference 2.4e-07 (rounding). Chaining adds their changes.
```

Order doesn't matter for plain LoRAs, beyond rounding. They add, with no averaging. So two LoRAs that both push one way go twice as far, and a stack that all looked fine alone can blow out together. Lower each one, rather than the last.

## Strength and alpha

The change that gets added is:

```
weight += strength · (alpha / rank) · (up @ down)       alpha / rank is 1 when the file has no alpha
```

The file decides `alpha / rank`, and that matters when you compare files. The same numbers can be stored at very different scales:

```text
the same numbers, stored three ways, strength 1: size of the change to the weight
alpha in file   scale   change
4.0             1.0     0.6564
1.0             0.25    0.1641
None            1.0     0.6564
```

So "strength 1" doesn't mean the same across files. It means what its maker tuned it for. Common advice: start at 1, then look (CU-282).

At strength 0 on both inputs, `LoraLoader` returns what you gave it and doesn't read the file at all.

## The log lines

This is the part worth learning. Read your terminal after the first run with a new file.

The matching runs per file. `load_lora_for_models` makes a key map of names your model answers to. In `comfy/lora.py`, each key that nothing claimed gets one warning. Here are four cases on a small model:

```text
file                          loader                 keys in file   patches   warnings
denoiser + text encoder       LoraLoader             12             4         0
denoiser + text encoder       LoraLoaderModelOnly    12             2         6
denoiser only                 LoraLoader             6              2         0
made for another family       LoraLoader             6              0         6
```

Row 1 is a clean load. In row 2 the file also holds a text-encoder part, and the model-only loader never looks for it. So those keys are warned about:

```text
what the log says for row 2:
lora key not loaded: lora_te_block0.lora_up.weight
```

That's harmless if you meant it. The denoiser keys loaded.

Row 4 is the bad one. Nothing matched, and you've got zero patches. The picture is the same as with no LoRA at all, except for a wall of warnings.

```text
what the log says for row 4:
lora key not loaded: lora_transformer_block0.lora_up.weight
```

So here's how to read it:

- **No warnings at all:** every key found a home.
- **Warnings, only for text-encoder names** (`lora_te`, `lora_te1`, `lora_te2`), on a model-only loader: expected.
- **Warnings for every key, or for denoiser names:** this file isn't for this model. A LoRA for one family usually has different layer names to another, and the file's name won't save you.

There are two more lines to know. `NOT LOADED <key>` is printed when a mapped patch didn't find a weight in the model or the text encoder. And when names match but sizes don't, for example a same-named layer of a different width, the sum can't be done, and you get `ERROR lora <key> <message>`, and that weight is left alone:

```text
shape mismatch: shape '[32, 32]' is invalid for input of size 512
weight unchanged: True
```

`comfy/lora_convert.py` and the key map handle many name styles already (`lora_unet_`, diffusers-style names, and others), so a file from another trainer usually maps. Don't rename keys by hand until the log says you must.

## Try the idea behind it

Why does so small a file work at all? The next lab is the same bet in picture form: a few directions hold most of what's there. It's from CU-212.

{{play:lowrank}}

## What goes wrong

- **The LoRA does nothing.** Read the log. Every key not loaded means a wrong family. No warnings means it loaded: raise the strength, add its trigger word, and compare at a fixed seed (CU-282).
- **`strength_clip` does nothing.** The prompt's CLIP wire goes around the loader. Rewire it.
- **Too strong at 1.** The file stored no alpha, or a high alpha, or you've stacked several. Lower it.
- **A wall of warnings on a model-only loader.** Text-encoder keys. Expected, if you meant to skip them.
- **`ERROR lora ...` for some keys.** A shape mismatch. That usually means a different model family or variant. Those layers are unchanged, so the result is partial.
- **It changed nothing on a second run.** The cache. Changing the file on disk under the same name isn't noticed until you change the name or restart (CU-102).

## Lab

The lab copies the logic of `load_lora` and the sum in `calculate_weight`, on a small fake file, and uses the same wording in its warnings. We also ran the real `load_lora` on such a file: it logged exactly those warnings and patched only the matching layer. The key names in the lab are made up, because no real model is loaded.

## Sources

- [Hu et al. 2021. LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/lora.py)
- [ComfyUI v0.43.0, comfy/lora_convert.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/lora_convert.py)
- [ComfyUI v0.43.0, comfy/model_patcher.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_patcher.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/lora.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_lora_stack.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_lora_stack.py)
