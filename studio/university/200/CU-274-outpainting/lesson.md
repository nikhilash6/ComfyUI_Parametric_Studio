# CU-274 - Outpainting with ImagePadForOutpaint

**Objective.** Extend a picture past its edge, and know exactly which pixels your settings allow the model to change. Taught by Captain Graph.

## The idea

Outpainting is inpainting with the hole outside the picture. You make the canvas bigger, mark the new part as "generate this", and sample. `ImagePadForOutpaint` does the first two jobs at once. It returns a bigger picture and a mask. Everything after that is an inpaint route, from CU-273.

Look at both outputs. This one needs no model.

{{graph:d_outpaint_mask}}

And the whole route:

{{graph:d_outpaint}}

## What the pad node makes

New pixels are mid-grey, 0.5. The mask is 1 over them. Inside your picture the mask is 0, except for a ramp beside each padded side, so that the new part and the old part can blend.

```text
512 x 512 picture, 128 added on the right, feathering 40 (the default)
output size (512, 640)   new pixels hold 0.5 (mid grey)
columns                 440  472  482  492  502  508  511  512  600
mask                    0.00 0.00 0.06 0.25 0.56 0.81 0.95 1.00 1.00
rounded (VAE route)     0.00 0.00 0.00 0.00 1.00 1.00 1.00 1.00 1.00
rounded and grown by 6  0.00 0.00 0.00 0.00 1.00 1.00 1.00 1.00 1.00
```

The ramp falls away from the join as a square: ((f − d) / f)², with d the distance from the join and f the `feathering`. It's quadratic, so it falls quickly. At feathering 40 it has already dropped to 0.25 by column 492, 20 pixels in.

Now look at the second and third rows. `VAEEncodeForInpaint` rounds the mask (CU-273), so most of the ramp is lost. Only the part above one half survives, and that's about 29% of the feathering's width, because √0.5 is 0.71. Then the growth adds 2 pixels, this way.

```text
pixels of your own picture that get repainted, counted from the join
feathering   soft mask above 0   rounded   rounded, grown by 6   feather on?
0            0                   0         2                     no: hard edge
8            7                   2         4                     yes
16           15                  4         6                     yes
40           39                  11        13                    yes
80           79                  23        25                    yes
255          254                 74        76                    yes
256          0                   0         2                     no: hard edge
```

So feathering isn't how far the blend goes on this route. It's how many of your pixels get wiped and redrawn: 13 at the default, with the pad on the right, as here. A pad on the bottom also gives 13. On the left or top the real node gives 15: d starts at 0 there, not 1, so rounding keeps 12, and the even box reaches 3 pixels that way. Our `d_outpaint` graph sets `grow_mask_by` to 8, which makes it 14 on the right. A soft route like `InpaintModelConditioning` keeps the ramp.

{{play:outpad}}

## When the feather turns itself off

A rule inside the node, and no warning:

```text
the feather switches off without warning: feathering x 2 must be smaller than both sides of the picture
picture       feathering 40
512 x 512      feathered
96 x 96       feathered
80 x 512      hard edge
64 x 64       hard edge
```

If feathering × 2 isn't smaller than both the height and the width, the ramp is skipped, and you get a hard edge. The default of 40 is fine at 512, but it turns off on a picture 80 pixels on a side.

Only padded sides are feathered. If you pad the left, the other three edges are left alone:

```text
only padded sides feather. 64 added on the left only, feathering 16: first and last rows and columns of the old picture
join column value 1.0   far right column 0.0   top row, middle 0.0
```

## The grid

The side inputs step by 8, but your picture may not be a multiple of 8. A VAE route crops from the centre to a multiple of 8, and you'd lose a few pixels of the picture.

```text
the grid: pad widgets step by 8, but the picture need not. VAE routes crop to a multiple of 8, from the centre
size after padding   kept after the crop   pixels lost
640                  640                   0
644                  640                   4
767                  760                   7
```

Pick a padded size that's a multiple of 8.

## Doing it well

Choose your route from CU-273. With `VAEEncodeForInpaint`, use an inpainting checkpoint at denoise 1. The grey fill would otherwise remain.

Your prompt should describe the whole bigger picture, not just the new part. And add a bit at a time if the area is large, since the model has more to go on when the new part is small next to the old. Both of those are common advice, and we did not test them.

If you have to use an ordinary checkpoint, grey fill plus denoise 1 gives it almost nothing to go on but the per-step blend. An inpainting checkpoint sees the mask and the surroundings in its extra channels, and that's why it's the usual partner.

## What goes wrong

- **A hard line at the join.** The feather turned itself off. Check that feathering × 2 is less than each side, or the route rounded it. Use a soft route, or composite after decoding (CU-213).
- **A grey band.** The new area kept its fill. Use denoise 1 on the greyed route.
- **Your picture's edge changed.** That's the feather and the growth doing their job. Lower `feathering` or `grow_mask_by`, or paste your original back over the result.
- **The new part doesn't match.** The prompt only described the new part, or you added too much at once, or the checkpoint isn't for inpainting.
- **The size came out a little smaller.** The picture wasn't a multiple of 8.
- **A seam with `SetLatentNoiseMask`.** Its latent holds the grey fill as content. At denoise below 1 the fill shows through.

## Lab

The lab's `expand_image` follows `nodes.py` line by line, and gave the same mask as the real node at three settings in a side script. The tables are above.

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
