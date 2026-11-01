# CU-103 - Pixels, tensors and shapes

**Objective.** Say which shape, range and number type ComfyUI uses for images and latents, move between the two layouts without scrambling pixels, and see where 8-bit levels and rounding bite. Taught by Bit Bandit.

## The idea

A tensor is a block of numbers with named axes, and its shape lists how long each axis is. The bytes do not say which axis is which. The code does, and ComfyUI keeps two conventions side by side.

| Value | Shape | Numbers |
|---|---|---|
| IMAGE | [B, H, W, C], channels last | float32 by default, 0 to 1 |
| LATENT, its "samples" entry | [B, C, H/8, W/8], channels first | float, not limited to 0 to 1 |

B is the batch size, H the height, W the width and C the channels: 3 for RGB, and 4 for the latents of SD 1.x and SDXL (16 for SD3 and Flux). PyTorch's convolution layers take [N, C, H, W], so the VAE nodes must convert. A mask has one value per pixel and no channel axis: the mask from `LoadImage` is [B, H, W], and 1 marks a transparent pixel.

Here's a graph where you can see one without any model. It makes a latent, doubles its size, multiplies it, and prints what it holds.

{{graph:nm_latent_ops}}

The size rule differs by family, and it's easier to feel than to read. Try this.

{{play:latent}}

## The mechanism

Three steps happen between pixels and the VAE, and the reverse on the way out.

1. Crop. Height and width are cut down to multiples of the VAE's downscale ratio, 8 for the usual VAE, taking the extra pixels from both sides.
2. Rescale. The encoder gets 2x − 1, so 0 to 1 becomes −1 to 1. The decoder's output goes back through (x + 1) / 2 and is clamped to 0 to 1.
3. Move the axes. `movedim(-1, 1)` turns [B, H, W, C] into [B, C, H, W], and `movedim(1, -1)` undoes it.

`movedim`, `permute` and `transpose` copy nothing. They return a view, which shares the same memory and only changes the strides, the step in memory for each axis. `reshape` is a different job: it keeps the order of the numbers in memory and relabels the axes. It gives the right shape and the wrong pixels, and no error is raised.

Memory is the shape times the width of one number: bytes = B × H × W × C × 4 for float32. Between pixels and a file there is one more conversion. An 8-bit PNG holds levels k = 0 to 255, loading divides by 255, and saving multiplies by 255 and casts to an integer. That cast truncates instead of rounding.

Number formats decide how much room the last bits have. Float32 has 1 sign, 8 exponent and 23 fraction bits, float16 has 1, 5 and 10, and bfloat16 has 1, 8 and 7 (Kalamkar et al. 2019, Table 1). `eps` is the gap between 1.0 and the next float above it. Just below 1.0 the gap is eps / 2, so between 0.5 and 1.0 a format has about 1 / eps distinct values.

## In ComfyUI

`LoadImage` turns 8-bit pixels into float32 by dividing by 255 and adds the batch axis (the Pillow fallback in `nodes.py` reads `np.array(image).astype(np.float32) / 255.0`, then `[None,]`). `SaveImage` multiplies the image by 255, clips to 0 to 255 and calls `astype(np.uint8)`, which truncates. Images between nodes are float32 unless the experimental `--fp16-intermediates` flag is set, and they sit in system RAM unless `--gpu-only` is set.

In `comfy/sd.py`, `VAE.encode` crops with `vae_encode_crop_pixels`, calls `movedim(-1, 1)` and applies `process_input`, which doubles the values and subtracts 1. `VAE.decode` ends with `process_output`, which adds 1, divides by 2 and clamps, then `movedim(1, -1)`. If either direction runs out of memory it retries in tiles. `EmptyLatentImage` makes `torch.zeros([batch_size, 4, height // 8, width // 8])`, so a size that is not a multiple of 8 is rounded down by the division.

## What goes wrong

- **`expected input to have 3 channels` or a similar error in your own node.** The tensor is channels last and the layer wants channels first. Use `movedim(-1, 1)`.
- **The picture comes out as coloured stripes or mixed-up patches, and no error.** Somewhere the axes were relabelled with `reshape` when they should have been moved. The lab shows that a convolution takes the scrambled tensor without complaint.
- **A size off by a few pixels.** A size that isn't a multiple of 8 is rounded down by the empty latent node, and cropped from both sides by VAE encode. Pick multiples of 8.
- **An error about the number of dimensions.** An IMAGE always has a batch axis, even for one picture. A mask has no channel axis. In your own node, `image[None,]` adds a batch axis and `image[0]` takes one out.
- **Treating a latent as a picture.** Its numbers aren't limited to 0 to 1 and don't mean brightness in any simple way. Decode it to look at it. CU-201 goes further.
- **A saved and reloaded picture differs by one level.** Saving truncates, as the lab shows at the end. Only worry if you need exact bytes.

## Lab

First the layout. The image is all red, so any scrambling shows as a number.

```text
IMAGE [2, 6, 8, 3] strides (144, 24, 3, 1)   after movedim(-1, 1): [2, 3, 6, 8] strides (144, 1, 24, 3)
movedim shares memory with the IMAGE: True   contiguous: False
share of channel 0 that is red:  movedim 1.000   reshape 0.333
Conv2d(3, 4, 3) on the [B, C, H, W] tensor gives [2, 4, 4, 6]
Conv2d on the [B, H, W, C] tensor: RuntimeError
Conv2d on the reshaped tensor: accepted, gives [2, 4, 4, 6], computed from scrambled pixels
```

After `movedim`, channel 0 is entirely red and nothing was copied. After `reshape`, the shape is the same but only a third of channel 0 is red. A convolution accepts both of those tensors, and the second one is computed from scrambled pixels with no error. Only the raw [B, H, W, C] tensor is refused, and only because its second axis is not 3.

Next, the size rules of the VAE nodes, with the crop written as `comfy/sd.py` writes it.

```text
requested   after crop  latent shape       numbers in image / latent
512x512     512x512     [1, 4, 64, 64]     786432 / 16384 = 48x
515x333     512x328     [1, 4, 41, 64]     503808 / 10496 = 48x
1000x563    1000x560    [1, 4, 70, 125]    1680000 / 35000 = 48x
1024x1024   1024x1024   [1, 4, 128, 128]   3145728 / 65536 = 48x
```

An image of 515 by 333 loses a few border pixels on encode. Nothing is resized. The latent holds 48 times fewer numbers in each case, because 3 × 64 / 4 = 48.

```text
decoder output  -1.20 -1.00  0.00  0.50  1.00  1.30
(x + 1) / 2      -0.10  0.00  0.50  0.75  1.00  1.15
after clamp       0.00  0.00  0.50  0.75  1.00  1.00
```

The clamp keeps pixels inside 0 to 1 even when the decoder pushes a value past −1 or 1.

```text
batch 1    512x512        3,145,728 bytes =       3.0 MiB   (as uint8:      0.8 MiB)
batch 4    1024x1024      50,331,648 bytes =      48.0 MiB   (as uint8:     12.0 MiB)
batch 100  1920x1080   2,488,320,000 bytes =    2373.0 MiB   (as uint8:    593.3 MiB)
```

Four bytes per value is why a long video held as one IMAGE batch is expensive. Now the part where I, Bit Bandit, live.

```text
an 8-bit image has 127 levels between 0.5 and 1.0
add 0.1, subtract 0.1, then save (worst error in 8-bit levels; kept = how many of the 256 levels come back unchanged)
dtype     eps             values in [0.5, 1)   worst error   kept by rounding   kept by truncating
float32   1.1920929e-07   8388608              0.0000        256                237
float16   0.0009765625    1024                 0.1250        256                189
bfloat16  0.0078125       128                  1.0000        243                237
```

The assertions in the lab confirm that storing the 256 levels and saving them again loses nothing in any of the three formats. The trouble starts after arithmetic that should cancel out. In float32 the worst error is far below a thousandth of a level (the table prints 0.0000), yet saving by truncation still loses 19 of the 256 levels, because some results land a hair below a whole number and the cast takes them down one level. Rounding keeps all 256. Bfloat16 has 128 values between 0.5 and 1.0, about as many as an 8-bit image has levels there, so a rounding can move a pixel by a whole level, and its worst error is 1.0000. Float16 has 1024 values there, eight times as many, and its worst error is an eighth of a level.

## What is contested

This is not a measurement of any particular workflow. Real pixels come from a VAE and rarely sit exactly on a level, and the one-level shifts are far below what an eye can see. The lab shows what a number format and a truncating cast do to a clean ramp, and why "load, do arithmetic that cancels, save" is not guaranteed to give back the same file. Do not infer a visible loss from it.

## Sources

- [Kalamkar et al. 2019. A Study of BFLOAT16 for Deep Learning Training](https://arxiv.org/abs/1905.12322)
- [ComfyUI Custom Node Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [Tensor Views, PyTorch 2.15 documentation](https://docs.pytorch.org/docs/2.15/tensor_view.html)
- [torch.movedim, PyTorch 2.15 documentation](https://docs.pytorch.org/docs/2.15/generated/torch.movedim.html)
- [Conv2d, PyTorch 2.15 documentation](https://docs.pytorch.org/docs/2.15/generated/torch.nn.Conv2d.html)
- [Type Info, PyTorch 2.15 documentation](https://docs.pytorch.org/docs/2.15/type_info.html)
