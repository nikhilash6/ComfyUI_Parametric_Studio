# CU-384 - Weights that can run code: pickle, safetensors, torch.load

**Objective.** Tell which model files can run code when loaded, what protects you in ComfyUI's loaders, and what to search a pack for. Taught by Bit Bandit.

## Why a weights file can be a program

A safetensors file is numbers with a label. A `.ckpt`, `.pt`, `.pth`, `.bin` or `.pkl` is usually a Python pickle, and a pickle isn't only data. It is a small list of instructions for rebuilding objects, and one instruction can be "call this function with these arguments". The Python docs say it flatly: "It is possible to construct malicious pickle data which will execute arbitrary code during unpickling."

So loading can be running. That's the whole lesson, and the lab shows it with a line that only prints.

## What each loader does

**ComfyUI core, at v0.43.0.** `load_torch_file` in `comfy/utils.py` chooses by file extension:

- `.safetensors` or `.sft`: read through safetensors. There's no pickle step on this path.
- Anything else: `torch.load(ckpt, map_location=device, weights_only=True)`.

`weights_only=True` restricts the unpickler to tensors, primitive types, dictionaries and an allow-list. Our lab's payload is refused. Note that the function has a `safe_load` argument which this version doesn't read: the limit is always on. We also searched core and found no `weights_only=False` and no `pickle.load`. That's core at this version, and not every tool you might use.

**Old versions.** ComfyUI's `SECURITY.md` puts `torch.load` problems "in old PyTorch versions" out of scope, as upstream issues, and recommends recent ones. Keep PyTorch current.

**Packs.** A pack is free to call whatever it likes, and core's choice doesn't bind it. This is the gap to check. A pack can load a helper model with its own `torch.load` or `pickle.load`, on a file it downloaded for you.

## Rules that work

1. **Prefer safetensors.** No pickle step. It's the same weights.
2. **Treat other formats as programs.** Get them from people you trust, or don't get them.
3. **Check what a file is, not what it's called.** A name is only a name. The first bytes say more, and the lab does this.
4. **Search packs as text** for the strings below. Each one needs a decision, not a panic.

```
pickle.load       torch.load(        weights_only=False
trust_remote_code=True               numpy.load(   allow_pickle=True
```

`trust_remote_code=True` is the bluntest of these. It tells a loader to run Python from the model's repository. That can have legitimate reasons, but then that code needs reading too.

{{play:loadfile}}

The graph below loads two files through `load_torch_file`, so both take core's protected path. Wherever you can, make them safetensors:

{{graph:sd15_lora}}

## What goes wrong

- **"It's only a LoRA."** LoRAs load through the same function, and a pack's LoRA loader may not. Check the format.
- **A converted file from a stranger.** A safetensors file can't run code when loaded, but it can still hold anything as weights. It's just not a program.
- **A refused file and the urge to turn the limit off.** If `weights_only=True` refuses a file, the file wants classes it doesn't allow. Don't remove the check to make it load. Find a safetensors copy, or inspect it in an isolated environment.
- **A pack downloads a model for you, on first use.** Now you're trusting that download. Look at what it fetches and how it loads it.
- **Assuming a scan of the file proves it's clean.** See CU-381. Use a format with no code path if you can.

## Lab

The payload here only prints a line. This is the whole trick, and it's why you never load strangers' pickles.

```text
a pickle, 145 bytes. Loading it with pickle.loads:
  >>> this line was printed by loading a file. It could have been anything.
```

The same thing in a `torch.save` file, and the limit ComfyUI uses:

```text
the same trick in a file torch.save wrote
torch.load(weights_only=True), which is what comfy/utils.py load_torch_file passes:
  refused: UnpicklingError
torch.load(weights_only=False):
  >>> this line was printed by loading a file. It could have been anything.
  loaded, keys ['extra', 'weight']
```

The limit says no. With it off, the file's code runs before you've touched a single weight. Plain weights pass the limit:

```text
plain weights pass the limit
  keys ['state_dict'], tensor [1.0, 1.0]
```

Safetensors, by hand. There's nothing to execute here: an 8-byte length, some JSON, and numbers.

```text
safetensors has no code path to attack this way: an 8 byte length, JSON, then raw numbers
  header {'dtype': 'F32', 'shape': [2], 'data_offsets': [0, 8]}  numbers (1.0, 2.0)
```

And the name decides nothing:

```text
the word in a filename does not decide anything. Read what the bytes start with
  a.ckpt from torch.save       zip, the torch.save format, holds a pickle
  b.pt that is a raw pickle    raw pickle
  c.bin that is safetensors    looks like safetensors
```

## Sources

- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, folder_paths.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/folder_paths.py)
- [ComfyUI v0.43.0, SECURITY.md](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/SECURITY.md)
- [Python docs, pickle](https://docs.python.org/3/library/pickle.html)
- [PyTorch 2.15, torch.load](https://docs.pytorch.org/docs/2.15/generated/torch.load.html)
- [safetensors README, Format section](https://github.com/huggingface/safetensors/blob/62e4d8b86063a6e5f8967547fa09a09f67420e2a/README.md)
