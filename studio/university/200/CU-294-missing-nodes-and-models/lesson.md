# CU-294 - Missing nodes and missing models, and how to fix them safely

**Objective.** Tell a missing node from a missing, broken or wrong file by its error, and fix each one without damaging your install. Taught by Captain Graph.

## The idea

You open a graph someone shared, and it fails. There are four separate problems that feel alike, each with its own error. Sort out which one you have first. The fixes differ, and one of them carries a real risk.

| Problem | When you see it | The text |
|---|---|---|
| The node class isn't installed | At queue, first check | `Node 'SuperKSampler' not found. The custom node may not be installed.` |
| The file isn't in your menu | At queue | `Value not in list: ckpt_name: 'model_a.safetensors' not in []` |
| The file is damaged | During the run | `Error while deserializing header: incomplete metadata, file not fully covered` |
| The file is the wrong kind | During the run | `ERROR: Could not detect model type of: <path>` |

All of those are real, from running ComfyUI's own code on a CPU. Practise telling them apart.

{{play:f_missing}}

## A missing node

`missing_node_type` stops everything at the first check, so you see this before any other error. Only one missing node is reported per queue, so fix one and queue again. The name in the message is the class name, unless the graph has a title for it.

**This is the risky one.** Installing a pack runs someone else's code with your account's rights, and may change libraries that other packs share. So take these in order:

1. **Is it really needed?** Many nodes have a core equivalent. Ask what this one does, and search the node menu. A core node has no install risk.
2. **Who wrote it?** Search for the exact class name. Look for a real project with real history. Be wary of a new repository, a random user name, or a single file with huge claims.
3. **Read it first.** Look through its `__init__.py` and any `prestartup_script.py`. CU-437 shows what to look for, and has a lab.
4. **Check what it would change.** Use `pip install --dry-run` on its requirements, and look for changes to `torch` or `numpy`.
5. **Have a way back.** A throw-away environment, or at least a note of your versions. Then restart.

If it says `IMPORT FAILED` at startup, the pack is present but broken, which is a different problem. Read the traceback above that line.

## A missing model

`value_not_in_list` on a file menu is the most common error from shared graphs. The check compares the name in the graph with what the menu holds today.

Read the list it prints:

```
Value not in list: ckpt_name: 'model_a.safetensors' not in []
Value not in list: ckpt_name: 'model_a.safetensors' not in ['b.safetensors']
Value not in list: ckpt_name: 'model_a.safetensors' not in (list of length 30)
```

- **Empty list:** nothing in that folder. Check you are using the right loader and folder.
- **Your file is there, under another name:** just pick it in the menu. Check it is the same file, though (below).
- **A subfolder:** `sd/model.safetensors` is a different name from `model.safetensors`. Graphs from other machines often include folders. Pick yours.

Each loader reads one folder type: `checkpoints`, `loras`, `vae`, `text_encoders` and so on. A file in the wrong folder doesn't appear in the menu. If you add a file while the server is running, refresh the editor. Check that this graph's loader sees your file.

{{graph:sd15_txt2img}}

**Getting the file safely.** Prefer `.safetensors`. A `.ckpt` or `.pt` file can hold Python pickles, which can run code if a tool loads them carelessly. ComfyUI's `load_torch_file` asks torch for `weights_only=True`, which limits that, but other tools you try may not. Get files from the model's real page, and compare the hash if the page gives one.

## A broken file

These appear during the run, when the loader opens the file. Here's what we got from four bad files we made:

| The file | The error |
|---|---|
| Cut short by a failed download | `Error while deserializing header: incomplete metadata, file not fully covered` |
| Only the first few bytes, 8 or more | `Error while deserializing header: invalid header length` |
| Fewer than 8 bytes, or empty | `Error while deserializing header: header too small` |
| A web page saved under the model's name | `Error while deserializing header: header too large` |

All of them mean the same thing: this isn't a whole safetensors file. Look at the size first. A checkpoint of a few KB is a saved web page, often a login page. Then download it again, and compare the hash.

Those words come from the safetensors library, which is what loaded the file on our CPU run. With dynamic VRAM on, `load_safetensors` in `comfy/utils.py` reads the file itself and words it differently, such as `The safetensors header is too large.` and `The safetensors header is incomplete.` We read that path, and did not run it.

The lab reads a file's first bytes itself, so you can see why it says "too large".

## A file of the wrong kind

The file opens fine and ComfyUI can't work out what it is.

- `ERROR: Could not detect model type of: <path>` in a checkpoint loader. A LoRA or a VAE was put in the `checkpoints` folder. We got this from small files of both kinds. If the file name holds `lora`, a HINT line says so.
- `Warning, This is not a checkpoint file, trying to load it as a diffusion model only.` A bare diffusion model the loader can recognise loads anyway, with no text encoder and no usable VAE, so it fails later, as in the next item. We read this in `load_state_dict_guess_config`, and did not run it. Use `UNETLoader` and the `diffusion_models` folder.
- `ERROR: clip input is invalid: None`, with the note `your checkpoint does not contain a valid clip or text encoder model`. Your checkpoint holds no text encoder. Add a text encoder loader.

Other wrong-kind mistakes appear as shape errors. See CU-292.

## What goes wrong

- **A graph from a pack's README asks for a model you can't identify.** Look for the name on the model's own page, or in the graph's notes. If you can't identify it, don't guess by file name.
- **Same name, different file.** Names aren't identities: `model.safetensors` could be anything, and a different version gives a different picture without an error. Compare hashes (CU-296).
- **You fixed one and a new error appears.** Normal. A missing class stops the check first, and only then do you see the rest.
- **A node worked before an update, and now it's missing.** Check the startup log for `IMPORT FAILED`. An update may have moved a library it depends on. Don't update everything at once to fix it.
- **Installing a pack broke others.** See CU-437. Compare versions to see what moved.
- **Running a downloaded installer because a guide says so.** Read it first. Never run `curl | bash` for a node.

## Lab

The lab reads the safetensors layout, using files made in memory: 8 bytes giving the header's length, then JSON. We checked that layout on a file written by the real library.

```text
a good file                             looks whole: 2 tensors, first key first_stage_model.decoder.conv_in.weight
cut short by a failed download          cut short or padded: header expects 219 bytes, file has 215
a web page saved under a model's name   not safetensors: first 8 bytes say a 8,029,423,821,061,908,540 byte header, the file has 120 bytes
```

That is why the real loader says "header too large". The letters of `<html>` get read as a length.

A hash shows a difference that a file name can't:

```text
sha256 of the good file  8c5b44dcce089134
sha256 of the short file 2d20da2de5c8d1a1
```

And a port of the menu check:

```text
Value not in list: ckpt_name: 'model_a.safetensors' not in (list of length 30)
same file, but the graph was saved on a machine with a folder: Value not in list: ckpt_name: 'sd/model.safetensors' not in ['model.safetensors']
```

## Sources

- [Safetensors, Hugging Face docs](https://huggingface.co/docs/safetensors/index)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, folder_paths.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/folder_paths.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
