# CU-415 - Reproducibility and provenance: hashing graphs and seeds

**Objective.** Record enough to explain later why two runs differ: a hash of the graph, the files it used, the versions, and the limits of what a seed fixes. Taught by Captain Graph.

## The idea

"Use the same seed" isn't reproducibility. A picture depends on the graph, the weights, the code, the libraries and sometimes the hardware. A seed fixes one input among them.

Provenance is the record of those things. You'll want two levels.

- **What you can recompute**: the graph, by hash.
- **What you must look up at the time**: file hashes, versions, hardware.

## What the file already knows

`SaveImage` writes a `prompt` text chunk in the PNG and one more for each key of `extra_pnginfo`, unless the server started with `--disable-metadata`. The browser UI puts `workflow` there, so its files have both. A graph queued through the API with no `extra_pnginfo` gets only `prompt`. That's why dropping a PNG on the canvas restores a graph. So a saved PNG holds the API graph, including the seed. It doesn't hold the weights, a file hash, or the version.

Anyone you send the file to gets the prompt too. Clear it, or use that flag, if that matters.

## Hashing a graph

Sort the keys, and use fixed separators, and hash the text. Now the same graph always gets the same hash.

{{play:provhash}}

Two things catch people. The graph holds only a file's name, so new weights under an old name don't change the hash. And node ids are in the graph, though the engine's cache key ignores them unless a node asks for its own id (CU-102), so a renumbered copy has a new hash and doesn't re-run.

{{graph:sd15_txt2img}}

## What a seed fixes

`prepare_noise` in `comfy/sample.py` calls `torch.randn` with a generator from `torch.manual_seed(seed)`, on the CPU. We ran that function here: same seed and same shape gave equal noise. The first image of a batch of 2 matched a batch of 1. A wider image got different noise in the same place. So changing the size changes the picture, even at one seed.

Noise is one thing. Beyond it:

- **Hardware and backends.** Different GPUs, drivers and attention backends may not round the same way. `--deterministic` asks PyTorch for slower deterministic algorithms where it can, and its help text says it may not always make images deterministic. Read yours.
- **Stochastic samplers** draw more noise in the loop (CU-207), from the seed too, so the seed still matters.
- **Packs and versions.** An update can change a node's code with the graph untouched.

## A record that helps

```
graph_sha256       sorted JSON of the API graph
weights_sha256     each file by hash, not by name
comfyui            version or commit
torch              /system_stats gives the version
GPU driver         nvidia-smi on NVIDIA cards, /system_stats does not report it
packs              the git commit of each pack
seed, size, batch  already in the graph
hardware           GPU model
```

To check a run later, compare records first. If they differ, you've found your first lead. If they match and the pictures differ, it's rounding or an unseen input. A pixel compare (CU-404) tells you how far apart they are.

## What goes wrong

- **The picture isn't the same with the same seed.** Check the size, batch index, sampler, weights file and versions, in that order. A size change alone did it in our test.
- **Hashing without sorting keys.** The same graph can give different text. Use a sorted dump.
- **Trusting a file name.** A file called `model.safetensors` tells you nothing. Hash it, once, and store that value. Hashing large files is slow, so cache by path and modified time.
- **Comparing PNG file hashes.** Metadata changes the bytes. The lab's two files hold the same picture and hash differently. Compare decoded pixels.
- **Sending prompts by accident.** Metadata travels with the file. Sites may also strip it, so don't rely on it as your only record.
- **Losing the record.** `/history` is held in memory and capped, and it's gone after a restart. Save your record next to the output.

## Lab

Hash a graph, then change it.

```text
change                               hash changes?
same graph, keys in another order    False
seed 42 -> 43                        True
node id 4 -> 40 (and the wire)       True
cfg 7 -> 7.0                         True
new weights under the same file name False, the graph only holds the name
```

Note `cfg 7 -> 7.0`. Same value to a sampler, different text. If you care, normalise numbers before hashing, or accept a false alarm. Now a real PNG, built and read back by the lab with the same kind of chunk.

```text
PNG with metadata: 346 bytes, keys ['prompt']  hash of what's stored: 9425a1b0d601
with --disable-metadata: 69 bytes, keys []
hash of the file differs between the two: True
```

And the noise. The lab runs the same call as `prepare_noise`, and we ran the real function too, with the same three results.

```text
same seed, same shape, equal noise: True
first image of a batch of 2 equals a batch of 1: True
same seed, wider image, same noise in the same place: False
```

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/sample.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sample.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
