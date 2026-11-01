# CU-315 - Temporal consistency and optical flow basics

**Objective.** Say what optical flow measures, tell motion from flicker with a simple test, and say where ComfyUI uses each idea. Taught by Reel Rascal.

## The idea

Between two frames, things change for two very different reasons. Something moved, or something changed. A camera pan changes nearly every pixel, and nobody calls it a fault. A brightness jump of 10% changes pixels far less, and everybody sees it.

So counting changed pixels tells you little. You need to ask: after undoing the motion, what's left? That's the idea behind optical flow, and behind every useful flicker check.

## What flow is

Optical flow is a field of two numbers per pixel, (u, v), saying where that pixel went in the next frame. It rests on one assumption, called brightness constancy: a point keeps its brightness as it moves.

```
I(x + u, y + v, t + 1) = I(x, y, t)
```

A plain frame difference isn't flow. It has one number per pixel, and it can't tell you where anything went. An earlier draft of this lesson confused the two.

Move the guess until the picture goes black:

{{play:flow}}

## How flow gets computed

Two classic routes:

- **Search.** Try many shifts and keep the best. Simple and slow.
- **Solve.** Assume small motion, and turn the equation above into a straight line: Ix u + Iy v + It = 0, where Ix and Iy are how brightness changes across the picture, and It how it changes over time. Solve by least squares over a window. That is Lucas-Kanade, and it works only while motion is small, as the lab shows.

Modern tools use a trained network. RAFT is one, and core ComfyUI can load it.

## In ComfyUI

**No general flow node, but flow is there.** `OpticalFlowLoader` loads a RAFT checkpoint from `models/optical_flow`, and ComfyUI never downloads it for you. `VOIDWarpedNoise` uses flow to warp noise along the motion of a clip, for the VOID inpainting pipeline. That's the one core use we found.

**Causal convolution.** Video VAEs care about time in their own way. `VideoConv3d` pads `kernel_size - 1` frames before the clip and none after, so no output depends on a later frame. `CausalConv3d` in Wan's and in LTX's VAE code has the same goal. That's about the order of time, not about flow. CU-316 follows it through.

**Generated video isn't told about flow.** The starting noise has no correlation between frames (CU-218). Coherence comes from the model. Models in core don't get a flow field unless a node like the one above adds it.

Here's the simplest possible video: with no change between frames, flow is zero everywhere.

{{graph:nm_video}}

## What goes wrong

- **Calling a frame difference "flow".** It has no direction. Use it to find change, and not motion.
- **Judging flicker with a raw difference on a moving shot.** A pan scores far worse than a real strobe. Undo the motion first. CU-411 builds this into a score.
- **Flow on big jumps.** Lucas-Kanade breaks: in the lab, a true motion of 8 pixels reads as 0.35. Real tools work coarse to fine or use a network.
- **Flow on lighting changes.** Brightness constancy fails there, so the method finds motion that isn't there, or leaves a big residual. Fades and flashes aren't motion.
- **Looking for the VOID nodes' model and not finding it.** ComfyUI won't fetch it. Put torchvision's RAFT-large format in `models/optical_flow`, as the loader's text says.

## Lab

A textured picture, moved by a known amount. First, what a difference can't tell you, and how a search recovers the truth:

```text
frame difference: 1 number per pixel, mean -0.0000, largest 0.504. True motion (+3.0, -1.5) cannot be read from it
search over whole and half pixels: best motion (+3.0, -1.5), mean squared error left 0.000000
```

Lucas-Kanade on the whole frame. Close for small motion, useless for large:

```text
true motion   Lucas-Kanade over the whole frame
(+0.3, -0.2)  ->  (+0.29, -0.19)
(+1.0, +0.5)  ->  (+0.94, +0.44)
(+3.0, -1.5)  ->  (+0.70, -0.53)
(+8.0, +4.0)  ->  (+0.35, +0.09)
```

The test that matters. Undo the best whole-pixel shift, then see what's left:

```text
change between two frames   mean |difference|   left after the best whole-pixel shift
camera pans 3 pixels        0.1036              0.0000
brightness jumps 10%        0.0498              0.0498
fine noise re-rolled        0.0405              0.0405
still frame                 0.0000              0.0000
```

The pan has the largest raw difference, and it leaves nothing. The brightness jump and the noise have smaller raw differences, and they stay. And a causal kernel against a centred one:

```text
an impulse at frame 4 through a 3-frame kernel:
causal  output non-zero at frames [4, 5, 6]
centred output non-zero at frames [3, 4, 5]
```

## Sources

- [RAFT: Recurrent All-Pairs Field Transforms for Optical Flow](https://arxiv.org/abs/2003.12039)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/model.py)
- [ComfyUI v0.43.0, comfy/ldm/wan/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/wan/vae.py)
- [ComfyUI v0.43.0, comfy/ldm/lightricks/vae/causal_conv3d.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lightricks/vae/causal_conv3d.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_void.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_void.py)
- [ComfyUI v0.43.0, comfy_extras/void_noise_warp.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/void_noise_warp.py)
