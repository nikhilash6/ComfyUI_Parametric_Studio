# CU-229 - Color spaces, gamma and image math

**Objective.** Write the sRGB curve in both directions, say what ComfyUI's blend, resize and save nodes do with it, and predict how far a blend or a shrink on stored pixel values lands from the same operation on light. Taught by Bit Bandit.

## The idea

The numbers in a PNG are not amounts of light. They are codes on a curve, sRGB, that gives dark tones many more codes than a straight scale would. Averaging two codes does not give the code of the average light. ComfyUI keeps pixel values as they are stored, between 0 and 1, and its image nodes do plain arithmetic on them. So whether a blend or a shrink is right depends on what you hand it: stored values or light.

## The maths

A stored value c between 0 and 1 and the linear-light value v are related by the sRGB transfer function. The W3C's CSS Color Module Level 4 gives it as sample code:

```
decode:  c ≤ 0.04045      v = c / 12.92
         c > 0.04045      v = ((c + 0.055) / 1.055) ^ 2.4
encode:  v ≤ 0.0031308    c = 12.92 · v
         v > 0.0031308    c = 1.055 · v ^ (1 / 2.4) − 0.055
```

It is the default color space for CSS, and the standard behind it is IEC 61966-2-1. The 1996 proposal by Stokes and colleagues describes the space by "the equivalent gamma value of 2.2". The curve is close to a power of 2.2 in the middle of the range and differs from it near black, where it has a straight piece. The exponent 2.4 in the formula is not the overall gamma.

A blend (1 − f) a + f b is a correct mixture of light only when a and b are light. For stored values, decode, mix, then encode. The luminance of linear RGB is a weighted sum, Y = 0.2126 R + 0.7152 G + 0.0722 B, which are the numbers in the middle row of the CSS text's sRGB to XYZ matrix. Last, an 8-bit file holds the integer q = 255 c, and two ways of getting there are truncating and rounding.

## In ComfyUI

**Loading.** `LoadImage` in `nodes.py` applies the EXIF orientation, converts to RGB, and divides the 8-bit codes by 255 in float32. The code we read does not look at a color profile and does not linearise anything.

**The model.** `VAE` in `comfy/sd.py` multiplies the stored values by 2 and subtracts 1 on the way in, and adds 1, halves and clamps on the way out. What colour space the latents correspond to is a property of the model's training data and not of ComfyUI's code, and CU-201 showed that latents are not pixels anyway.

**Arithmetic on stored values.** `ImageBlend` in `comfy_extras/nodes_post_processing.py` computes `image1 · (1 − blend_factor) + blended · blend_factor` on the stored values, and clamps. `ImageCompositeMasked` (CU-213) does the same lerp. `ImageScale` in `nodes.py` resizes through `common_upscale` in `comfy/utils.py`, which calls `torch.nn.functional.interpolate` for nearest-exact, bilinear, area and bicubic and has its own routine for lanczos. All of them work on stored values.

**Saving.** `SaveImage` multiplies the image by 255, clips it to the range 0 to 255 and calls `astype(np.uint8)`. NumPy's cast to an integer truncates toward zero. It does not round.

**Converting.** `ImageColorSpace`, "Convert Image Color Space", is in `comfy_extras/nodes_images.py`. It converts between sRGB, linear, HDR (Rec.2020 HLG), HDR PQ, LogC3, linear ACEScg and ACEScct. Its `srgb_to_linear` function is the decode above, labelled in the code "Inverse sRGB EOTF (IEC 61966-2-1)", and its sRGB output uses the encode above. So a blend in light can be built from nodes: convert sRGB to linear, blend, convert back. The node's description says that conversion to SDR tone-maps excess luminance and compresses out-of-gamut colours, so keep values within 0 to 1. We read this node and did not run it.

## Lab

The curve first. The two pieces meet, the round trip is exact to rounding, and a plain power of 2.2 is far off near black:

```text
decode at 0.04045: linear piece 0.0031308, power piece 0.0031308;  encode at 0.0031308: linear piece 0.040450, power piece 0.040450
round trip decode then encode over the 256 codes: largest error 1.1e-16
code   sRGB linear   plain power 2.2   ratio
1      0.000304      0.000005          59.78
5      0.001518      0.000175          8.67
20     0.006995      0.003697          1.89
50     0.031896      0.027755          1.15
128    0.215861      0.219520          0.98
255    1.000000      1.000000          1.00
```

In the middle, at code 128, the two agree to 2%. At code 5 the sRGB light is nearly 9 times the power law's. Now blends and a shrink:

```text
luminance weights R, G, B: 0.2126 0.7152 0.0722
black and white, half and half: on stored values 0.5000, in linear light then encoded 0.7354   (8-bit code 127.5 against 187.5)
red and green, half and half: stored-value blend [0.5, 0.5, 0.0], light blend [0.7354, 0.7354, 0.0]
  luminance of the light that reaches the eye: stored-value blend 0.1986, light blend 0.4639, the average of the two lights 0.4639
2x area downscale of a black and white checkerboard (the ImageScale 'area' method): pixel 0.5000; averaging the same four pixels in linear light: 0.7354
```

A half-and-half mix of black and white should hand the eye half the light of white, and half the light is code 0.7354. The stored-value blend lands on 0.5. For red and green the stored-value blend delivers 0.1986 of the luminance where the mixture of the two lights has 0.4639, less than half. The checkerboard, shrunk with the `area` method, comes out at 0.5, which looks darker than the pattern did from far away. Next, where the 8-bit codes lie:

```text
codes whose light is below 1% of white: sRGB 26, if the codes were linear in light 3
codes whose light is at least half of white: sRGB 68, if the codes were linear in light 128
```

The curve spends 26 codes on the darkest 1% of the light, and a linear coding would spend 3. The same 256 codes are spread very differently over light. Last, the end of the graph. LoadImage divides by 255 in float32, and SaveImage multiplies back and truncates:

```text
load then save, all 256 codes: codes that come back changed: 0
random values in [0, 1], error of the saved code in codes: truncation mean -0.500, largest 1.000;  rounding mean +0.000, largest 0.500
a value of 0.999 is saved as code 254 by truncation and 255 by rounding
```

An untouched image survives load and save exactly. Once values have passed through a model they sit between codes. If they are spread evenly between codes, as in the random test, truncation pulls the file half a code down on average, with errors up to a full code, where rounding would be unbiased and stay within half a code.

## What is contested

Blending in light is not always the better choice. It is the physically correct mix of light, and designers and tools have long used stored-value blends for gradients and soft edges because of how they look. The lab shows how large the difference is, not which one to prefer. The sRGB assumption matters too: we assume the stored codes are sRGB, which is the usual case, and the code we read does not handle other profiles. We did not measure the latent space of any model, so the lab says nothing about what a VAE does to colour. The truncation figures are for uniformly random values. Real images are not uniform, and half a code on average is below what most people can see.

## Sources

- [W3C CSS Color Module Level 4, Candidate Recommendation Draft, 29 October 2026](https://www.w3.org/TR/css-color-4/)
- [Stokes, Anderson, Chandrasekar, Motta 1996. A Standard Default Color Space for the Internet - sRGB](https://www.w3.org/Graphics/Color/sRGB.html)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_post_processing.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_post_processing.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_images.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_images.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_mask.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_mask.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
