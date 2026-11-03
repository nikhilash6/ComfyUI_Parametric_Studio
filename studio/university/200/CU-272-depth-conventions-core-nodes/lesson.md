# CU-272 - Depth: conventions and core's depth nodes

**Objective.** Make a depth map with a core node, say which end is near and how the grey steps are spaced, and spot a map that a far sky has flattened. Taught by Professor Latent.

## The idea

A depth map is a grey picture. It tells a ControlNet how far away each part of the scene is, so the layout stays and the surfaces are free.

A grey picture has no room for a label. Is white near or far? Do equal grey steps mean equal metres? Is it the whole range of the scene, or the middle of it? These are conventions, and a model trained on one will read another wrongly and say nothing about it. So let us look at what core really makes.

{{graph:d_depth_moge}}

## What core really has

We read these from `object_info` and from the source of v0.43.0. All are in core, so no pack is needed, but each needs its model file.

| route | nodes | what comes out |
|---|---|---|
| Depth Anything 3 | `LoadDA3Model`, `DA3Inference`, `DA3Render` | `DA3Render` output `depth`: grey, with `normalization` v2_style, min_max or raw |
| MoGe | `LoadMoGeModel`, `MoGeInference`, `MoGeRender` | `MoGeRender` output `depth`: grey, spaced by 1/depth. Also normals and a mask |
| Lotus | `LotusConditioning`, plus a Lotus U-Net run with ordinary sampling nodes | a decoded picture |

Lotus works differently. `LotusConditioning` has no inputs at all: a comment in the source says it inlines a fixed result, because Lotus uses "null conditioning". `LotusD` in `comfy/supported_models.py` is how core recognises the checkpoint. Then it's a normal one-step run: core ships a blueprint, "Image Depth Estimation (Lotus Depth)", that encodes your picture, sets the first sigma to 999, takes one Euler step with no added noise, decodes, and ends with `ImageInvert`. That last node is a hint that what comes out of the decoder has the opposite brightness of what the blueprint wants. We read that from the blueprint and did not run it.

If you already have a depth picture, from a 3D program or anywhere else, `LoadImage` is all you need. That's what `sd15_controlnet_depth` does.

{{graph:sd15_controlnet_depth}}

Don't confuse these with `DA3GeometryToMesh` and `MoGePointMapToMesh`. Those go on to make 3D meshes, which a ControlNet can't take.

## Three renders, one scene

The same scene, from 2 m to 10 m, through each render:

```text
a scene from 2 m to 10 m. Grey value at each distance; 1 is white
distance   DA3 v2_style   DA3 min_max   MoGe disparity
2 m       1.000          1.000         1.000
3 m       0.883          0.875         0.586
4 m       0.755          0.750         0.377
6 m       0.500          0.500         0.167
8 m       0.245          0.250         0.063
10 m       0.000          0.000         0.000
all three put near at white. Depth-linear greys spend even steps per metre, disparity spends most of its range up close
half of the grey range covers: v2_style from 2 m to 6.0 m   disparity from 2 m to 3.3 m
```

All three put near at white. That's the good news. But the steps mean different things. `v2_style` and `min_max` are linear in depth, so 6 m is middle grey. MoGe's is linear in 1/depth, so 6 m is already dark, at 0.167, and half of its grey range goes on the first 1.3 m. Close things get lots of detail. Far things are squashed together. A map from each looks different on the same scene, and neither is wrong: they're different scales.

The official notes for the ControlNet 1.1 depth model say it was trained on Midas, Leres and Zoe depth at three resolutions, and that it's "highly robust and can work on real depth map from rendering engines". They don't state a near or far convention. Near-is-white is what we assume in our graphs. Test it with one render on any depth ControlNet you haven't used.

## The sky problem

Now let a few pixels be very far. A far sky can use up the whole grey range, leaving the scene a few shades of near-white.

```text
add pixels at 500 m (sky). Distinct 8-bit grey levels left for the 2 m to 10 m part
sky share   min_max   v2_style   v2_style with a sky mask   disparity
0.0         256       256        256                        256
0.005       5         256        256                        206
0.02        5         5          256                        206
0.3         5         5          256                        206
```

`min_max` stretches from nearest to farthest, so half a percent of sky leaves the scene with 5 of 256 grey levels. It will look like a flat pale picture. `v2_style` cuts at the 1st and 99th percentile, so it survives 0.5% of sky and collapses at 2%. It only does better than that with a sky mask, which is what the model variants with a sky output give it. (`DA3Render` also has `apply_sky_clip`.) MoGe's scale barely cares, since 1/500 is close to zero anyway. That's also why it loses some levels in the first place: 206, and they hold steady.

Move the sky yourself.

{{play:depthnorm}}

## Check your map by eye

You need no tools. Look for something you know is near and something you know is far.

```text
by-eye check: near object 0.95, far wall 0.05: near is brighter, this map is near-white
after ImageInvert: near object 0.05, far wall 0.95: the same geometry as a negative. correlation with the original -1.000
```

If the near thing is darker, you have a far-is-white map. `ImageInvert` turns one into the other exactly, as the correlation of −1 says. If everything is one pale shade, the range has been used up by a far outlier. Try another `normalization`.

![Lotus depth from a pack, on our rainy street test picture. The woman in front is white and the far end of the street is dark, so this map is near-is-white. One seed.](families/lotus_0.webp)

## What goes wrong

- **Depth is inverted, so the layout comes out inside out.** Look at it first. Use `ImageInvert` if it's far-is-white. Depth-map files from other programs vary.
- **A flat pale map.** Sky or a far outlier used up the range. Switch `normalization`, use a sky mask, or use a MoGe render.
- **`raw` output.** It isn't scaled, so values can be metres, far above 1. Use it for measuring, not for a ControlNet.
- **Coloured depth.** `depth_colored` is a false-colour view for your eyes. Send the grey one to a ControlNet.
- **Depth picture saved at a low bit depth, then stretched.** A file with few levels bands. Keep the original and render at the size you need.
- **A MoGe or DA3 file in the wrong loader.** `LoadMoGeModel` and `LoadDA3Model` list the same folder, `geometry_estimation`, so both menus show every file there. Pick the one that fits.

## Lab

The lab's three functions give the same values as ComfyUI's on a test ramp, a check we ran in a side script. All numbers are from a synthetic ramp. No depth model ran.

## Sources

- [Lotus: Diffusion-based Visual Foundation Model for High-quality Dense Prediction](https://arxiv.org/abs/2409.18124)
- [ControlNet 1.1 nightly README](https://github.com/lllyasviel/ControlNet-v1-1-nightly/blob/main/README.md)
- [ComfyUI v0.43.0, comfy_extras/nodes_depth_anything_3.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_depth_anything_3.py)
- [ComfyUI v0.43.0, comfy/ldm/depth_anything_3/preprocess.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/depth_anything_3/preprocess.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_moge.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_moge.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_lotus.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_lotus.py)
- [ComfyUI v0.43.0, comfy/supported_models.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/supported_models.py)
- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
- [ComfyUI v0.43.0, blueprints/Image%20Depth%20Estimation%20(Lotus%20Depth).json](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/blueprints/Image%20Depth%20Estimation%20(Lotus%20Depth).json)
