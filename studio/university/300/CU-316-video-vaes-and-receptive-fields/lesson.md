# CU-316 - Video VAEs and receptive fields

**Objective.** Work out how far one output of a convolution stack can see, explain the first-frame rule from causal padding, and say what that means for tile overlap. Taught by Professor Latent.

## The idea

One latent value in a video VAE was computed from some region of the input frames. That region is its receptive field. Nothing outside it can affect that value. Three everyday facts follow from this: why video lengths are 1 + k x m, why changing a late frame leaves early latents alone, and why tiles need overlap.

## The formula

A stack of layers, each with kernel k and stride s. Let j be the product of the strides so far, starting at 1. Then:

```
r = 1 + sum over layers of (k - 1) x j
```

Each layer adds (k - 1) steps, measured in input samples, and j says how far apart its inputs are. With stride 1, you gain k - 1 per layer: slow growth. With stride 2, j doubles each time, so reach roughly doubles per layer. Set your own stack here:

{{play:rf}}

The lab checks this formula by experiment, tracing which inputs reach one output. It matches on every stack.

## Time is different

In space, a convolution looks both ways. In time, video VAEs usually look only backward. In `VideoConv3d` and in Wan's `CausalConv3d`, padding goes before the clip and not after, so an output has no dependence on later frames. LTX's `CausalConv3d` has a `causal` flag and can run either way.

This produces the rule from CU-215. With padding of 2 before and stride 2, repeated twice, the output count is exactly `(n - 1) // 4 + 1`. The first frame gets a latent of its own, because nothing comes before it to group with. The lab confirms this with real `conv3d` calls, not arithmetic. The same stack shows no future leak: change frame 20 of 21, and only the last latent moves.

Why bother? It lets a VAE decode a long clip chunk by chunk, holding a small cache of past features, as Wan's `CausalConv3d` does with `cache_x`. That's why the Wan 2.2 decode estimate in `comfy/sd.py` has no frame count (CU-333).

{{graph:wf_wan22_t2v}}

Follow the wire from `Wan22ImageToVideoLatent` to `VAEDecode`. The latent's first frame stands for one video frame, and the rest stand for four each.

## Why tiles need overlap

When a tile is decoded alone, values within the receptive field radius of its edge are missing their neighbours, so they're wrong. Overlap gives every position a tile where it's far from the edge. So the overlap needs to be at least the radius. The lab shows this directly. With radius 3, error is large at overlaps 0 and 2, and gone at 4.

CU-217 covers the blending that hides what's left.

## What goes wrong

- **Treating a stride as a small change.** Each stride multiplies the reach of every later layer. A stack of six layers with three strides of 2 sees 29, where six plain layers see 13.
- **Mixing up receptive field and output spacing.** r is how far one output sees. j is how far apart outputs sit. Both matter, and they grow differently.
- **Off-by-one lengths.** The first-frame rule isn't a bug. Ask for 1 + k x m frames.
- **Assuming the full region matters equally.** Real values fall off towards the edge of the region: the formula gives an outer limit, and what matters most is usually smaller. We read this as common knowledge and did not measure it here.
- **Seams at a regular spacing with a tile overlap under the reach.** Raise the overlap until the seam stops changing.
- **Copying advice across VAEs.** Some VAEs chunk for themselves. H3's ignores tile settings entirely.
- **Applying a tiny kernel's numbers to a real VAE.** These stacks are plain convolutions. Real VAEs add attention and residual paths.

## Lab

The formula against an experiment that traces gradients:

```text
layers (kernel, stride)                        formula r  measured  output spacing j
[(3, 1)]                                       3          3         1
[(3, 2)]                                       3          3         2
[(3, 2), (3, 2)]                               7          7         4
[(3, 1), (3, 1), (3, 1), (3, 1)]               9          9         1
[(3, 2), (3, 2), (3, 2), (3, 2)]               31         31        16
[(3, 1), (3, 2), (3, 1), (3, 2), (3, 1), (3, 2)] 29         29        8
```

Note r and the spacing j. An earlier version of this lesson's lab got sizes wrong, so here is the sum for two layers of kernel 3, stride 2, on 7 pixels:

```text
spatial size with kernel 3, stride 2, no padding: 7 -> 3 after one layer, 1 after two
```

The first-frame rule, from real causal convolutions:

```text
frames in -> latent frames from two causal stride-2 layers, against (n - 1) // 4 + 1:
   1 ->   1   1
   5 ->   2   2
   9 ->   3   3
  17 ->   5   5
  21 ->   6   6
  81 ->  21   21
 120 ->  30   30
 121 ->  31   31
```

No leak from the future:

```text
change frame 20 of 21: the 6 latent frames that move are [5]
```

And the overlap a tile needs, for a stack that reaches 3 on each side:

```text
two tiles of a 64-long latent, zero padding at each tile edge, hard join in the middle of the overlap
overlap   largest error at the join
0         0.136897
2         0.036592
4         0.000000
6         0.000000
8         0.000000
12        0.000000
```

## Sources

- [ComfyUI v0.43.0, comfy/ldm/lightricks/vae/causal_conv3d.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lightricks/vae/causal_conv3d.py)
- [ComfyUI v0.43.0, comfy/ldm/wan/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/wan/vae.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/model.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax/vae.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
