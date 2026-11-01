# CU-271 - Preprocessors: Canny in core, and looking at your map

**Objective.** Make a Canny map in core, preview it before you spend a render, and read a bad map for what's wrong with it. Taught by Captain Graph.

## The idea

A ControlNet does not see your picture. It sees the control image you give it. A preprocessor is whatever turned your picture into that image. If the map is wrong, the ControlNet will faithfully follow the wrong thing.

So there is one habit this lesson teaches: put a `PreviewImage` on the map, and look at it first. It costs nothing, and core's `Canny` node needs no model.

{{graph:d_canny_preview}}

## What core gives you

For edges, core has one node, "Detect Edges (Canny)", in `comfy_extras/nodes_canny.py`. CU-219 goes through how it works: blur, Sobel, thinning, then two thresholds with hysteresis. Depth has its own lesson, CU-272. For pose, core has nodes such as `SDPoseKeypointExtractor` and `SDPoseDrawKeypoints`, which we did not study for this lesson. For line art, soft edges and scribbles, a search of core's node names finds no preprocessor in v0.43.0, so you need a pack or a map you drew yourself. We make no recommendation here.

The wire is simple. The node's IMAGE output goes to the `image` input of Apply ControlNet, and it is an ordinary picture: white lines on black, three channels. Anything that makes such a picture will do, including a drawing of your own.

## What the thresholds are measured in

Here is the surprise. `low_threshold` and `high_threshold` look like fractions of white, since they run from 0.01 to 0.99. They are not. They are compared with the gradient, which the kornia function behind the node leaves unscaled. A straight edge of contrast h has a gradient of about 2.59 × h after the blur. An edge pixel must beat `high_threshold` to start a line.

```text
a straight edge of contrast h, on a scale where black is 0 and white is 1
h      largest magnitude (raw, 2.59 x h)   found at 0.4/0.8   found at 0.1/0.2   found at 0.99/0.99
0.1    0.259                               False              True               False
0.3    0.776                               False              True               False
0.31   0.802                               True               True               False
0.38   0.983                               True               True               False
0.39   1.009                               True               True               True
0.5    1.294                               True               True               True
smallest contrast that can start an edge = high_threshold / 2.59:  0.8 -> 0.309   0.2 -> 0.077   0.99 (the slider's top) -> 0.383
```

Two results follow. At the default 0.8, an edge needs a contrast of 0.31 or more to start. That is a strong edge: on a scale of 0 to 1, a difference of 0.3 is a lot. And the slider's top is 0.99, so an edge with contrast 0.39 or more always passes. You cannot use the high threshold to throw away strong edges.

So a soft, low-contrast photo at the defaults can come back nearly black, and the fix is to lower the thresholds rather than to brighten the map.

The other rule: low must not be above high. The sliders allow it, and kornia then stops the run with "Invalid input thresholds".

## What a bad map looks like

Here is a scene with a strong disc, a faint square and a little noise (0.05). Three things tell you if a map is any good: does it find what matters, does it miss the faint parts, and is it full of specks?

```text
noise 0.05, 128 x 128: what each threshold pair keeps
low   high   pixels marked   disc outline   faint square   stray pixels
0.05  0.1    32.5            1.00           1.00           0.3465
0.1   0.2    4.8             1.00           1.00           0.0310
0.2   0.4    2.0             1.00           1.00           0.0000
0.4   0.8    1.3             1.00           0.00           0.0000
0.8   0.9    1.3             1.00           0.00           0.0000
0.95  0.99   1.3             1.00           0.00           0.0000
```

Read from the top. At 0.05 and 0.1, a third of all pixels are marked, and over a third of the empty background is speckled. That's a map that says "edges everywhere". The ControlNet is told to follow noise. At the default, 0.4 and 0.8, the map is clean, and the faint square is gone. If the square mattered, the ControlNet doesn't know about it and the prompt alone decides what goes there. 0.2 and 0.4 catches both, on this scene.

Those are the three faults to look for:

- **Too busy.** Texture and noise become lines. Raise the thresholds, or blur or shrink the picture first.
- **Too empty.** Parts you care about are missing. Lower the thresholds.
- **Broken lines.** Raising low cuts the links that join a line together, and hysteresis needs those to carry a strong edge along.

Try the same thing on a real render. This browser lab uses a plain threshold on Sobel, not the node's thinning, so its numbers are close cousins of the node's and not the same. Its target of 4% to 12% is an exercise, not a rule.

{{play:edges}}

The official notes for the ControlNet 1.1 Canny model say it was trained on "Canny with random thresholds", so it has seen a range of densities. There is no single right pair.

## Size and shape

The hint doesn't need to be the size of your render. `get_control` fits it for you with `common_upscale`, and it uses crop "center". If the shapes differ, the edges of your map are cut off, with no warning.

```text
hint size against the latent's shape (common_upscale, crop center)
hint          render        part of the hint used   share kept
1024 x 1024   512 x 512    1024 x 1024             1.00
1024 x 768    512 x 512    768 x 768              0.75
768 x 1024   512 x 768    682 x 1024             0.89
1920 x 1080   512 x 512    1080 x 1080             0.56
```

A 1920 × 1080 map on a square render loses 44% of itself, and the parts that remain sit where they would in the crop. If your picture and your render have different shapes, crop or pad them yourself first, so you choose what goes. The default resize is `nearest-exact`, so a thin line in a big map can lose pixels when it shrinks. Make the map at about the render's size when you can.

## What goes wrong

- **The map is black.** Your edges are below high_threshold / 2.59 in contrast. Preview it, then lower both thresholds.
- **The map is white with noise.** The thresholds are too low for this picture. Raise them, or blur first.
- **"Invalid input thresholds."** Low is above high. Swap them.
- **Lines from the picture end up off to one side, or missing at the edges.** The hint was cropped to fit. Match the shapes first.
- **The wrong ControlNet.** A Canny map through a depth ControlNet still runs, because both are plain images. Nothing checks. Make sure the file matches the map.
- **Inverted lines.** Black lines on white is a different picture to the model. `Canny` gives white on black. If you drew yours, use `ImageInvert`.

## Lab

The lab's Canny is written out in plain torch, following kornia 0.9.0, and it matches `kornia.filters.canny` pixel for pixel on this scene at four threshold pairs. That check ran in a side script, because labs only import torch. The tables are above. The disc and square are a toy scene: use them for how to read a map, not as a setting to copy.

## Sources

- [ControlNet 1.1 nightly README](https://github.com/lllyasviel/ControlNet-v1-1-nightly/blob/main/README.md)
- [kornia v0.9.0, kornia/filters/canny.py](https://github.com/kornia/kornia/blob/v0.9.0/kornia/filters/canny.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_canny.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_canny.py)
- [ComfyUI v0.43.0, comfy/controlnet.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/controlnet.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
