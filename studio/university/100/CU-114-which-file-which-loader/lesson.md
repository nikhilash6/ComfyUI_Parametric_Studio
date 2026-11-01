# CU-114 - Which file goes in which loader and folder

**Objective.** Look at a model file, work out which of the common kinds it is, and put it in the folder and loader that fit. Taught by Bit Bandit.

## The idea

You download a file. ComfyUI has a dozen folders and a dozen loaders. Which one?

The thing to hold on to: a folder only decides which menu lists the file. It does nothing to the file. The question that matters is what's inside, and a model needs three jobs done: denoising (the MODEL), reading text (the CLIP), and turning latents into pixels (the VAE). A file can hold all three or just one.

- A **checkpoint** holds all three in one file. One loader, three outputs.
- A **diffusion model** holds just the denoiser. It needs a text encoder and a VAE beside it.
- A **text encoder** turns prompts into vectors. It may be one of two or three that a family uses.
- A **VAE** moves between pixels and latents.
- A **LoRA**, a **ControlNet** and an **upscale model** do other jobs on top of those.

These two graphs make the same kind of picture from different packaging. The first has one loader. The second has three.

{{graph:sd15_txt2img}}

{{graph:wf_flux2_klein}}

## The table

Each menu comes from a folder name in `folder_paths.py`. Under `models/`:

| You have | Loader node | Folder name | Looks in | Gives |
|---|---|---|---|---|
| A checkpoint | `CheckpointLoaderSimple` | checkpoints | checkpoints | MODEL, CLIP, VAE |
| A denoiser alone | `UNETLoader` | diffusion_models | unet, diffusion_models | MODEL |
| A text encoder | `CLIPLoader` | text_encoders | text_encoders, clip | CLIP |
| Two text encoders | `DualCLIPLoader` | text_encoders | text_encoders, clip | CLIP |
| A VAE | `VAELoader` | vae | vae | VAE |
| A LoRA | `LoraLoader` | loras | loras | MODEL, CLIP |
| A ControlNet | `ControlNetLoader` | controlnet | controlnet, t2i_adapter | CONTROL_NET |
| An image encoder | `CLIPVisionLoader` | clip_vision | clip_vision | CLIP_VISION |
| An upscaler | `UpscaleModelLoader` | upscale_models | upscale_models | UPSCALE_MODEL |

Old names are still honoured: `unet` means `diffusion_models`, and `clip` means `text_encoders`. Subfolders are fine, and they show up in the menu as `sub/file.safetensors`.

`CLIPLoader` also has a `type` menu, with entries such as `stable_diffusion`, `sd3`, `wan` and `flux2`. That choice has to match the model family. The same goes for the loader's other choices, so copy them from a workflow that's known to work for that model.

## Telling them apart

File names are written by people, and they often say nothing. The tensor names can't be casual: the loaders read them. CU-107 showed how little it takes to read them, because a safetensors header is a short JSON at the start of the file.

- `model.diffusion_model.` with `first_stage_model.` and a text-encoder prefix such as `cond_stage_model.`: a checkpoint.
- `input_blocks.`, `double_blocks.` or similar with nothing else: a denoiser alone.
- `text_model.encoder.layers.` or `encoder.block.`: a text encoder.
- `encoder.down.` with `decoder.up.` or `decoder.conv_in.`: a VAE.
- `lora_unet_` or `.lora_down.`, `.lora_up.`, `.lora_A.`, `.lora_B.`: a LoRA.
- `input_hint_block.` or `control_model.`: a ControlNet.

This list is a beginner's guide, not a test ComfyUI runs. Its real detector is far longer and knows many more layouts.

{{play:loaderpick}}

## What the wrong pairing does

The errors make sense once you know the loaders.

A denoiser-only file in a checkpoint loader: ComfyUI logs "This is not a checkpoint file, trying to load it as a diffusion model only" and returns a MODEL. There's no CLIP and no real VAE, so the next text encode fails with `clip input is invalid: None`, and a decode fails with `VAE is invalid: None`.

A whole checkpoint in `UNETLoader`: this works. The source says "Allow loading unets from checkpoint files". You get the denoiser and ignore the rest, which still has to be read from disk.

A file ComfyUI can't place: `Could not detect model type`, along with a hint.

## What goes wrong

- **The file isn't in the menu.** Check the folder against the table, and the extension: the list is `.ckpt`, `.pt`, `.pt2`, `.bin`, `.pth`, `.safetensors`, `.pkl`, `.sft`. A `.gguf` is not on it. The docs say GGUF needs community custom nodes. Then press `r` in the editor to refresh, as the docs say.
- **`Value not in list` when you open someone's workflow.** The graph names a file you don't have, or have under another subfolder. The message lists what you do have. Pick yours in the menu.
- **Two copies under different folders.** With `models/clip/x.safetensors` and `models/text_encoders/x.safetensors` the menu shows one `x.safetensors`, and the one in `text_encoders` loads. Delete one so you know which you're running.
- **Mixed families.** The folder won't warn you when a VAE, a LoRA or a text encoder is from another family. A LoRA whose names don't fit logs `lora key not loaded` and has little effect, so read the console. Layers of another shape can't be applied (CU-107). We didn't try every mix, so keep a note of what each file is for.
- **A pickle file from a stranger.** `.ckpt`, `.pt`, `.bin` and `.pth` are not data-only formats, unlike `.safetensors` (CU-107). Prefer safetensors.
- **Models on another disk.** Don't move your models folder by hand. Copy `extra_model_paths.yaml.example` to `extra_model_paths.yaml`, add your folders, and restart. The docs say the file is read at start.

## Lab

First the table above, printed from what the code says. Then menus for a made-up disk holding a `.gguf`, a `.txt`, a subfolder, and one name in two places.

```text
checkpoints menu:      ['a.safetensors', 'e.sft', 'sub/b.ckpt']
diffusion_models menu: ['u1.safetensors', 'u2.safetensors']
text_encoders menu:    ['same.safetensors', 't1.safetensors', 't2.safetensors']
same name in two folders loads: models/text_encoders/same.safetensors
the old name unet gives the same list: True
```

We ran ComfyUI's real listing functions on the same tree in a throw-away folder, and they returned these same lists. Then the reading test, on tensor names only.

```text
file    what the names say      holds
file_1  checkpoint              denoiser, text encoder, VAE
file_2  denoiser only           denoiser
file_3  denoiser with a prefix  denoiser
file_4  text encoder            text encoder
file_5  text encoder            text encoder
file_6  VAE                     VAE
file_7  LoRA                    changes to another model
file_8  ControlNet              control
```

`file_3` is the odd one. Its names carry the checkpoint prefix, yet it holds only a denoiser. The loader code allows for this, and the prefix doesn't prove a text encoder is present. Finally the pairings, which come from reading `comfy/sd.py`, not from loading real files.

```text
the file                the loader               what happens
whole checkpoint        CheckpointLoaderSimple   MODEL, CLIP and VAE
denoiser only           CheckpointLoaderSimple   warns, gives a MODEL; using CLIP or VAE then fails
whole checkpoint        UNETLoader               takes the denoiser out of it; you still need the other two
denoiser only           UNETLoader               gives a MODEL
file of no known kind   either                   Could not detect model type
```

## What the lab leaves out

Real files hold many more names than these short lists. The lab's test knows nothing of the many layouts ComfyUI handles, including text encoders and VAEs saved under other prefixes, so treat a surprising result as a reason to read further. We did not press `r` in a browser or load the real files in the last table.

## Sources

- [ComfyUI Models: Files, Folders, and Loader Nodes](https://docs.comfy.org/development/core-concepts/models)
- [ComfyUI v0.43.0, folder_paths.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/folder_paths.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/model_detection.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_detection.py)
- [ComfyUI v0.43.0, comfy/controlnet.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/controlnet.py)
- [ComfyUI v0.43.0, comfy/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/lora.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, extra_model_paths.yaml.example](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/extra_model_paths.yaml.example)
