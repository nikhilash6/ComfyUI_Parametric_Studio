# CU-263 - Regions: ConditioningSetArea and ConditioningSetMask

**Objective.** Place a prompt on part of the picture, predict how it blends with what else covers that part, and pick between an area and a mask. Taught by Madame Attention.

## The idea

Both nodes put a prompt on part of a picture. They do it differently.

- An **area** is a real crop. At each step, the model is handed only that box of latent, so it can't see the rest of the picture.
- A **mask** keeps the whole latent. The model answers for the whole picture, and the mask decides how much of that answer each cell keeps.

## How cells blend

Every entry's answer goes into the same sum, cell by cell:

```
cell = sum(answer · weight) / sum(weight)
```

From this one line come three facts that catch people out.

- **Strength is a share, not a volume.** A box at strength 1 over a whole-picture prompt gets half the cell. At strength 3 it gets three quarters. With nothing else there, strength does nothing, because the sum divides it away. The lab asserts this.
- **Bare cells get nothing.** If no entry covers a cell, its prediction is zero. So always include a whole-picture prompt alongside your boxes.
- **Edges fade by themselves.** An area without a mask fades its weight in over up to 8 cells, except where the box meets the picture's own edge.

{{play:regions}}

## ConditioningSetArea

The sizes are in pixels and become latent cells by dividing by 8:

```python
{"area": (height // 8, width // 8, y // 8, x // 8), "strength": strength, "set_area_to_bounds": False}
```

That 8 is fixed. On a family whose latent is 16 times smaller than the picture, such as FLUX.2, the box comes out twice the size you asked for. `ConditioningSetAreaPercentage` takes fractions and uses the real latent size, so prefer it there.

There's a hidden cost. `create_cond_with_same_area_if_none` adds a same-area copy of the negative, so the crop has a matching second branch. One box and one negative on the whole picture is four predictions per step: whole, box, negative, and the negative's copy. And crops of different sizes can't share a batch, so these are likely to be separate trips through the model.

{{graph:sd15_cond_area}}

## ConditioningSetMask

```python
{"mask": mask, "set_area_to_bounds": set_area_to_bounds, "mask_strength": strength}
```

The mask is resized to the latent with bilinear filtering, then used as the weight. A mask has no automatic fade, so its edges are as hard as you drew them. Grey values are partial shares.

The `set_cond_area` input has two settings.

- `default` shows the model the whole latent.
- `mask bounds` finds the mask's bounding box and crops to it, so that part fills the model's whole input. The part has the same number of cells as before, because nothing is enlarged. It's a crop, with the area's blindness to what's around it.

{{graph:c_cond_mask}}

## Which to use

| Situation | Choice |
|---|---|
| A simple rectangle, and you want the fade | Area |
| A family that isn't 8 times smaller | Area by percentage |
| Any shape, or it should relate to the scene around it | Mask, default |
| Any shape, and the model should see only that part | Mask bounds |

## A picture from elsewhere

This one comes from a third-party pack, RES4LYF, using its own regional node on FLUX.1 schnell. It's not made with the core nodes above, but it shows what the goal looks like. The data says: a lighthouse prompt on the left half, a snowy pine forest on the right, split by a plain mask.

![Two prompts in one frame, from the RES4LYF pack: a lighthouse on the left half, a snowy forest on the right. One seed, FLUX.1 schnell.](res4lyf_renders/flux_regional.jpg)

## What goes wrong

We rendered none of these with the core nodes. The looks described are what we expect from the code.

- **Strange colours outside your boxes.** You only supplied boxes, so bare cells get zero. Add a whole-picture prompt.
- **"Strength 5 did nothing."** The box is alone in those cells, so strength divides away. It only acts against other entries there.
- **The box prompt looks pasted in.** A crop can't see its surroundings. Try a mask at default, so the model sees the whole picture.
- **A box in the wrong place on a newer family.** The 8 is fixed. Use the percentage node.
- **A hard seam with a mask.** Masks don't fade by themselves. Blur the mask first.
- **Slow runs.** Each box costs two predictions per step at cfg above 1. See the play.
- **A tiny box.** Fade width is a quarter of the size, up to 8 cells, and the model gets very few cells to draw with.

## Lab

A port of `get_area_and_mult`, compared with the real function on four boxes. Answers here are constants, so each number is simply the box's share.

```text
the area tuple for w 256, h 256, x 256, y 200: (32, 32, 25, 32)
first 10 cells across the box: 0.125 0.250 0.375 0.500 0.625 0.750 0.875 1.000 1.000 1.000
```

Now the blend, with a whole-picture prompt at strength 1:

```text
strength   box centre   box edge   outside
0.5        0.333        0.059      0.000
1.0        0.500        0.111      0.000
3.0        0.750        0.273      0.000
10.0       0.909        0.556      0.000
entries run: 2   model input sizes in cells: [(64, 96), (32, 32)]
```

The second entry's model input is 32 by 32 cells. That's the crop. Next, the box alone, and then a mask over the same square:

```text
only the box, nothing whole-picture: centre 1.0   with strength 5: 1.0   outside the box: 0.0
a mask over the same square: centre 0.5  edge 0.5  outside 0.0   model input sizes: [(64, 96), (64, 96)]
```

The mask has no fade at its edge, and its model input is the whole latent. Finally, the fixed 8:

```text
ConditioningSetArea still divides by 8: a 256 pixel box becomes 32 cells, which is 512 pixels there
ConditioningSetAreaPercentage uses the real latent size: 0.33 of a 64-cell side is 21 cells
```

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
