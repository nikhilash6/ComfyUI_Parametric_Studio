# CU-116 - Your own picture: the input folder, LoadImage and its mask

**Objective.** Get your own picture into a graph, say what `LoadImage` returns, and avoid the size and mask surprises that catch most people. Taught by Captain Graph.

## The idea

So far every graph started from nothing. Most real work starts from a picture you already have. ComfyUI reads it from one place, the input folder, and hands on two things: the picture and a mask.

This graph shows both, and it needs no model. Pick any picture of yours in the loader.

{{graph:a_own_picture}}

## How a picture gets in

The input folder sits beside output and temp (CU-112). `LoadImage`'s menu is a listing of the files directly in it. Files you put in a subfolder aren't listed, as our run showed. Copy a file there by hand, or use the node's upload button, which sends it to the server's `/upload/image` route.

The graph only stores the file's name. Send your graph to a friend and the picture stays behind (CU-110), and they get `Invalid image file` until they supply their own.

There's a trick for what you just made: a name written as `out.png [output]` reads from the output folder, and `[temp]` from the temp folder. `LoadImageOutput` builds on this and lists the output folder.

## What comes out

**IMAGE** is the picture as numbers from 0 to 1, shape [B, H, W, 3] (CU-103). Any alpha channel is dropped from it. A file's rotation flag is applied, so a phone picture comes out upright: a test file stored as 64 by 48 with that flag loaded as 48 wide and 64 high.

**MASK** comes from the alpha channel. It's 1 minus alpha, so 1 means the file was transparent there. The mask has no channel axis: [B, H, W]. In a sampler's inpaint mask, 1 means the part to repaint (`KSamplerX0Inpaint` in `comfy/samplers.py`), so a hole in a picture lines up with what you'd want changed.

If the file has no alpha, as with any JPEG, the mask is all zeros and, oddly, always 64 by 64, whatever the picture's size. That's the source's choice, and our run confirmed it. It catches people who wire the mask into something that wants the picture's own size.

## Using it: image to image

To start the sampler from your picture, encode it to a latent and lower `denoise`. That's the only change from the first-image graph (CU-106).

{{graph:sd15_img2img}}

`denoise` decides how much of your picture survives. At 1.0 the sampler starts at its highest noise level, about σ 14.6 for SD 1.x, with your latent still in the sum but buried. Lower it and the sampler starts part way down, from your picture with less noise added. Slide it and see what the setting does to the schedule.

{{play:denoise}}

The right value depends on the model and the picture. The lab here doesn't test that, and CU-214 goes further.

## What goes wrong

- **A huge photo runs for ever or runs out of memory.** Nothing resizes for you. A 3024 by 4032 phone photo is 46.5 times the pixels of 512 by 512. Scale it first with `ImageScaleToTotalPixels` (CU-109), or `ImageScale`.
- **The picture comes back a little smaller.** The VAE crops to a multiple of 8, from both sides (CU-103). 515 by 333 becomes 512 by 328.
- **The picture comes back unchanged.** `denoise` is low, or the output is reading the original instead of the sampler's result. Follow the wire from your Save node back.
- **The picture comes back unrelated to yours.** `denoise` is at or near 1.0, so the noise buried it. Lower it.
- **A size mismatch on the mask.** With no alpha, the mask is 64 by 64. If the next node needs it at the picture's size, paint a real one, or make one with `SolidMask` at your size.
- **The mask looks inverted.** Alpha 1 means opaque, which gives mask 0. A picture from a tool that saved it the other way round needs `InvertMask`.
- **A transparent PNG turned odd colours.** The colour under transparent pixels stays in IMAGE, because alpha is dropped and not blended. A fully clear test file still gave its hidden colour. Those pixels can be anything.
- **`Invalid image file`.** The name in the graph isn't in your input folder. Pick your own.
- **You replaced a file and got a new result, without asking.** `LoadImage` hashes the file's bytes, so any change re-runs it and what follows. That's meant to happen, and it's unlike a checkpoint (CU-102).

## Lab

A plain copy of the arithmetic on made-up pixels. The first file has a clear top half.

```text
file                  IMAGE               MASK            mask mean  mask at top, at bottom
with alpha, top clear [1, 48, 64, 3]      [1, 48, 64]     0.500      1.0 0.0
no alpha              [1, 48, 64, 3]      [1, 64, 64]     0.000      0.0 0.0
the mask of a file with no alpha is 64 x 64 whatever the picture's size: True
```

We also ran the real node on a half-transparent PNG and a JPEG. The shapes were the same, and the mask value on the PNG with alpha 128 was 0.498. Then the sizes.

```text
file          after crop    latent [B, 4, h, w]     pixels lost
1024x1024     1024x1024     [1, 4, 128, 128]        0
3024x4032     3024x4032     [1, 4, 504, 378]        0
1000x563      1000x560      [1, 4, 70, 125]         3,000
515x333       512x328       [1, 4, 41, 64]          3,559
```

```text
phone photo 3024x4032 in memory as an IMAGE: 139.5 MiB, against the 3.0 MiB of a 512x512 one, 46.5 times the pixels
```

## What the lab leaves out

`LoadImage` tries to read a file as video first and falls back to Pillow, for frames of an animation. We tested one PNG and one JPEG. We did not click upload in a browser, and we make no claim about how img2img pictures look at any `denoise`.

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, folder_paths.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/folder_paths.py)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI Custom Node Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes)
