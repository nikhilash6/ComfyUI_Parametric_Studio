# CU-217 - Upscaling and tiling math

**Objective.** Work out how ComfyUI cuts an image into tiles, count the model calls and the extra work, and say what overlap and feathering do to a seam. Taught by Professor Latent.

## The idea

A big image does not fit through a model in one piece, so ComfyUI cuts it into tiles, runs the model on each, and stitches the results. Tiling trades time for memory. The stitching has one problem to solve: near the edge of a tile the model cannot see the neighbours, so its output there is wrong. Overlap gives every pixel a second opinion, and a ramp weights the opinions so that the unreliable edge counts least.

## The maths

Along one side of length D, with tiles of length S and an overlap O, tiles start every S − O pixels. ComfyUI's list of starts is `range(0, D − O, S − O)` when D > S, and a single start at 0 otherwise. Each tile is cut off at the border, so the last tile can be short. The number of tiles on that side is:

```
n = 1                       if D ≤ S
n = ceil( (D − O) / (S − O) )   otherwise
```

An image has n × n tiles when both sides are alike. The pixels fed to the model, divided by the pixels in the image, are the square of (sum of tile lengths) / D.

Each tile's output gets a weight mask that rises linearly, (t + 1) / f for the t-th pixel from the edge, over f = overlap × upscale pixels at both ends of the tile. The output is the weighted sum of tile outputs divided by the sum of the weights, so each pixel is a weighted average of the tiles that cover it, and a pixel covered by only one tile is returned unchanged.

The reason to ramp is the receptive field. A stack of 3 × 3 convolutions sees r pixels either side, with r = 1 per layer. With zero padding, the missing neighbours at a tile's edge are replaced by zeros, and the result is wrong for about r pixels in. The other tile has the right answer there, because for that tile the pixel is well inside. A ramp gives the right answer more weight.

## In ComfyUI

`tiled_scale_multidim` in `comfy/utils.py` is the routine, with `tiled_scale` as its 2D wrapper and `get_tiled_scale_steps` counting tiles with the formula above. Three places use it.

**Model upscalers.** `ImageUpscaleWithModel` in `comfy_extras/nodes_upscale_model.py` runs tiles of 512 pixels with an overlap of 32 and the upscale model's own scale factor. If it runs out of memory it halves the tile and tries again, and it gives up once the tile would fall below 128.

**Tiled VAE decoding.** `VAEDecodeTiled` in `nodes.py` has `tile_size` 512 and `overlap` 64 pixels by default. If the tile is smaller than four times the overlap, the overlap becomes a quarter of the tile. Both are divided by the VAE's spatial compression, 8 for most image VAEs, to get latent units. For image latents, `VAE.decode_tiled_` in `comfy/sd.py` then decodes the latent three times, with tiles of (tile/2, 2 · tile), (2 · tile, tile/2) and (tile, tile), and averages the three results. The three tilings put their seams in different places.

**Latent resizing.** `LatentUpscale` takes a width and height in pixels, enforces at least 64, and divides by 8 before resizing. `LatentUpscaleBy` multiplies the latent's sides by `scale_by` (default 1.5) and rounds. Both offer the methods nearest-exact, bilinear, area, bicubic and bislerp.

## Try it

Change the side, the tile and the overlap, and watch the tiles and the cost. Each bar's fade is its weight ramp.

{{play:tiles}}

Two real graphs use this. The first decodes in tiles, and the second runs a model upscaler, which tiles for itself:

{{graph:sd15_tiled_vae}}

{{graph:sd15_upscale}}

## Lab

The first block applies ComfyUI's position rule to three sides, with tiles of 512 and an overlap of 64, and checks the count formula against the list of starts:

```text
side 1024, tile 512, overlap 64: starts [0, 448, 896], lengths [512, 512, 128], 3 tiles
side 1536, tile 512, overlap 64: starts [0, 448, 896, 1344], lengths [512, 512, 512, 192], 4 tiles
side 960, tile 512, overlap 64: starts [0, 448], lengths [512, 512], 2 tiles
ceil((D - O) / (S - O)) agrees with the number of tile starts for every D from 100 to 700, tiles of 64, 128 and 256, overlaps 0, 8 and 32
```

The last tile of a 1024 side is only 128 pixels long, and 960 fits in two tiles exactly. Now what the model-upscaler defaults cost in extra work:

```text
input side   tiles per side   tiles   pixels fed to the model / pixels in the image
512          1                1       1.000
768          2                4       1.085
1024         3                9       1.129
2048         5                25      1.129
```

Then the tiled VAE decode of a 1024 × 1024 image at its defaults, a 128 × 128 latent with tiles of 64 and an overlap of 8, where three tilings run:

```text
VAEDecodeTiled on a 1024 x 1024 image: latent 128x128, tiles ((32, 128), (128, 32), (64, 64)), decoder calls [5, 5, 9], 19 in all, against 9 for the (64, 64) tiling alone
latent positions decoded: 61,696 for 16,384 in the latent, 3.77 times the work of one untiled pass
```

Tiling saves memory, not time. Counting every latent position the decoder sees, the default does 3.77 times the work of a single untiled pass, if the decoder's cost grows with area. Last, the seam. The lab uses a toy decoder: three 3 × 3 convolutions with tanh, a 1 × 1 convolution and a 2 × upsampling, with fixed random weights. It sees 3 latent pixels on each side. The tiled result is compared with the untiled one, and the largest error is quoted as a multiple of the output's standard deviation:

```text
latent 64x64, tile 32, receptive field 3 latent pixels. Largest error of the tiled output against the untiled output, as a multiple of the output's standard deviation (0.308)
overlap   tiles   pixels fed in / pixels   plain average   feathered (ComfyUI's mask)   three tilings averaged
0         4       1.000                  2.76            2.76                         1.84
2         9       1.129                  1.90            1.61                         0.94
4         9       1.266                  1.71            0.98                         0.50
8         9       1.562                  1.51            0.39                         0.29
```

With no overlap the largest error is 2.76 times the output's spread. A plain average of overlapping tiles helps less than one might hope: at an overlap of 8 it is still 1.51, because the ruined edge pixels carry half the weight where two tiles meet. The ramp is what helps, 0.39 at the same overlap, and averaging three tilings brings it to 0.29. All of it costs pixels: an overlap of 8 on tiles of 32 feeds the model 1.562 times the image.

## What goes wrong

- **Seams show.** The overlap doesn't reach far enough past the model's sight. Raise it, up to a quarter of the tile, which `VAEDecodeTiled` enforces. Bigger tiles help too.
- **Tiled decode is slower than plain decode.** It's supposed to be: 3.77 times the work in the lab's example. It trades time for memory, so use it only when needed.
- **An upscaler slows sharply on a big image.** It halved its tile after running out of memory, so it's making many more calls. The node logs nothing when it retries, but its progress bar starts again with more steps. Free VRAM first.
- **The last tile looks different.** It's cut off at the border and can be short, 128 of 512 in the lab's first row. That's normal.
- **Latent upscale gives a mushy result.** Its methods only resize numbers. They don't add detail by themselves, so a sampler pass normally follows.
- **Tile settings do nothing on some video VAEs.** H3's ignores them. CU-334 covers video.

## What is contested

The seam errors come from a toy decoder with fixed random weights and zero padding, so the numbers say how the mechanism behaves, not how large the seams of a real VAE or upscaler are, and real networks differ in how far they reach and how they pad. The factor 3.77 assumes that the decoder's cost grows with the number of positions, which is only roughly true. Nor does the lab compare resize methods: whether a latent upscale looks better than a pixel upscale depends on the images and the model, and is not measured here.

## Sources

- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_upscale_model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_upscale_model.py)
