# CU-219 - Depth and edge preprocessors: Sobel by hand

**Objective.** Compute a Sobel gradient by hand and know what its numbers mean, explain why ComfyUI's Canny node blurs before it differentiates, and read how ComfyUI's depth nodes turn a depth map into a grey hint image. Taught by Professor Latent.

## The idea

A control model such as a ControlNet does not take a photo. It takes a simpler picture made from it, a hint: an edge map, a depth map, a pose. The ControlNet paper lists Canny edges and depth maps among the conditions it trained (its Figure 7). Making an edge map is old arithmetic, and the rest of this lesson does it by hand. Making a depth map is the job of a neural network, and the arithmetic left for us is how its output is scaled into a grey image.

## The maths

An edge is a place where the image changes quickly, so we want its derivative. The Sobel operator estimates it with two 3 × 3 stencils. The x stencil is the product of a smoothing column and a difference row, and the y stencil is its transpose:

```
Kx = [1, 2, 1]ᵀ · [−1, 0, 1] = | −1  0  1 |        Ky = Kxᵀ
                               | −2  0  2 |
                               | −1  0  1 |
Gx = Σ Kx(i, j) · I(x + j, y + i)       magnitude = √(Gx² + Gy²)       direction = atan2(Gy, Gx)
```

The sum is a correlation: the stencil is laid on the image as written and not flipped. `torch.nn.functional.conv2d` does the same. A true convolution flips the stencil and changes the sign of the answer, but not the magnitude. The gradient points across the edge, from dark to bright, so a vertical edge gives a large Gx and a Gy of zero.

The stencil is not scaled. A ramp of slope s per pixel gives 8s: the smoothing column adds up to 4, and the difference row spans two pixels. A step of height 1 gives 4. Kornia's documentation says the same, "Per unit slope Sobel answers 8".

Noise is where the smoothing earns its keep. For white noise of standard deviation σ, the sum of squared stencil entries is 12, so the noise in Gx has standard deviation σ√12. A plain difference [−1, 0, 1] has σ√2. A step of height h gives 4h with Sobel and h with the plain difference. The signal-to-noise ratio is 4h / (σ√12) against h / (σ√2), and the ratio of the two is √(8/3).

Canny's method adds three steps around the gradient. Blur the image first. Take the gradient. Keep only the ridge of each edge (non-maximum suppression). Then use two thresholds, keeping a weak edge pixel only when it connects to a strong one (hysteresis). We follow kornia's description of the algorithm here, and have not read Canny's paper.

## In ComfyUI

**Edges.** The `Canny` node, "Detect Edges (Canny)", in `comfy_extras/nodes_canny.py` passes the first three channels of the image to `kornia.filters.canny` with `low_threshold` 0.4 and `high_threshold` 0.8 as defaults, and copies the single-channel edge map into three channels. Kornia's documentation for version 0.9.0, the version used for this audit (ComfyUI's requirements say `kornia>=0.7.1`), describes what happens: a 3-channel input becomes grey, it is blurred with a 5 × 5 Gaussian of sigma 1 by default, and the unnormalised Sobel gradient is taken. The thresholds are compared with that magnitude, so they are not fractions of the image range: "a unit step reaches 4 without the blur and about 2.59 with the default one". Then comes non-maximum suppression along the gradient direction, rounded to a multiple of 45 degrees, and hysteresis through the 8 neighbours.

**Depth.** Core ComfyUI estimates depth with networks. It has Depth Anything 3 nodes (`LoadDA3Model`, `DA3Inference`, `DA3Render`) and MoGe nodes (`LoadMoGeModel`, `MoGeInference`) in `comfy_extras`. `DA3Render` turns the depth into a grey image with a `normalization` choice. In `comfy/ldm/depth_anything_3/preprocess.py`, `min_max` stretches the frame's smallest and largest depth to the range 0 to 1. `v2_style` takes the 1st and 99th percentiles of the depth, over the non-sky pixels when a sky mask exists, stretches those, and sets sky to black. Both put near at 1.0, white. The node's tooltip calls `v2_style` "mean/std normalisation", but the code uses percentiles, and the lab follows the code.

## Lab

First the stencil. A ramp gives 8 times its slope, a unit step gives 4, the sign follows correlation, and the default Canny blur lowers the step response to the 2.59 that kornia documents:

```text
Sobel x stencil = outer([1, 2, 1], [-1, 0, 1]): True
ramp of slope 0.1 per pixel: Gx = 0.800 (8 x slope = 0.800);  unit step: Gx = 4.0 and 4.0 at the two pixels beside the edge
rising edge with the stencil as it is: +4.0, with the stencil flipped (a true convolution): -4.0
unit step after the 5x5 Gaussian blur with sigma 1 (the Canny node's default): Sobel magnitude 2.59, against 4.00 without the blur
```

Then the noise argument, on a 512 × 512 image of white noise:

```text
noise std through Sobel 3.462 (sqrt(12) = 3.464), through the plain difference 1.414 (sqrt(2) = 1.414)
signal to noise for a step of height h: Sobel 1.155 h, plain difference 0.707 h, ratio 1.63
```

Now why Canny blurs first. A 64 × 64 image holds a disc of value 1.0 on a background of 0.2. The lab marks pixels with a Sobel magnitude above 0.8, the Canny node's default high threshold. It counts how many pixels within 1.5 pixels of the circle are marked, and what share of the pixels more than 3 pixels from the circle are marked by mistake. There is no non-maximum suppression and no hysteresis here, so this is a simplified stand-in for the node.

```text
noise std   blur first   true edge pixels found   false edge pixels (of the pixels far from the circle)
0.0         no           0.851                    0.0000
0.0         yes          1.000                    0.0000
0.05        no           0.846                    0.0000
0.05        yes          1.000                    0.0000
0.1         no           0.827                    0.0514
0.1         yes          0.989                    0.0000
0.2         no           0.843                    0.3547
0.2         yes          0.987                    0.0024
```

At a noise level of 0.2, 35% of the far pixels pass the threshold without the blur, and 0.24% with it. The blur averages the noise away before the stencil magnifies it, and it also widens the step, so more of the pixels beside the circle respond. The price is a wider, softer edge. Last, the depth normalisations. A scene that ramps from 2 m to 10 m has a share of pixels at 500 m, like sky. The table gives the grey value at 2 m, 6 m and 10 m:

```text
scene depth ramps from 2 m to 10 m; a share of the pixels is far away (500 m, like sky). Grey value, 1 = near, at 2 m, 6 m and 10 m
far pixels   min_max               v2_style
0.000        1.000 0.495 0.000     1.000 0.495 0.000
0.005        1.000 0.992 0.984     1.000 0.500 0.000
0.020        1.000 0.992 0.984     1.000 0.992 0.984
```

With no far pixels the two agree. With 0.5% far pixels, `min_max` squeezes the whole scene into grey values between 0.984 and 1.000, because its upper end is 500 m, while the percentile version still spreads 2 m to 10 m over the full range, since the 99th percentile ignores them. At 2% the 99th percentile is itself 500 m and `v2_style` collapses too. The sky options of `DA3Render` address this: its `apply_sky_clip` tooltip says it clips sky depth to the 99th percentile of the foreground depth before normalising.

## What is contested

The disc test is a toy: one shape, Gaussian noise and a plain threshold. It supports "blur first" for this noise, not any claim about photographs, and the real node adds thinning and hysteresis. The kornia numbers are for the 0.9.0 documentation, and another version may scale its gradient differently, which would change what the thresholds mean. We do not say that any depth hint convention, near as white or the percentile bounds, is the one a given depth ControlNet was trained on: the ControlNet paper's main text does not give it, and its supplement was not available to us.

## Sources

- [Zhang, Rao, Agrawala 2023. Adding Conditional Control to Text-to-Image Diffusion Models](https://arxiv.org/abs/2302.05543)
- [kornia v0.9.0, kornia/filters/canny.py](https://github.com/kornia/kornia/blob/v0.9.0/kornia/filters/canny.py)
- [kornia v0.9.0, kornia/filters/kernels.py](https://github.com/kornia/kornia/blob/v0.9.0/kornia/filters/kernels.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_canny.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_canny.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_depth_anything_3.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_depth_anything_3.py)
- [ComfyUI v0.43.0, comfy/ldm/depth_anything_3/preprocess.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/depth_anything_3/preprocess.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_moge.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_moge.py)
