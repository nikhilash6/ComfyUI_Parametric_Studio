# CU-109 - Resolution, aspect ratio and the pixel budget

**Objective.** Derive a width and height from an aspect ratio and a pixel budget, know which sizes the VAE and the models were built for, and say which costs grow with the pixel count and how fast. Taught by Captain Graph.

## The idea

Two things limit the size of a picture. The first is the machinery. The VAE divides each side by 8, so a size that is not a multiple of 8 is rounded down (CU-103). The second is training. A model has seen pictures of certain sizes: the Stable Diffusion v1-4 model card lists its later training stages at 512 × 512, and SDXL was fine-tuned on 40 sizes that keep the pixel count as close to 1024 × 1024 as possible, with both sides in multiples of 64 (Podell et al. 2023, Section 2.3 and Appendix I).

So the useful unit is the pixel budget, the product width × height. One megapixel in ComfyUI's accounting is 1024 × 1024 = 1,048,576 pixels, and 1024 × 1024, 1344 × 768 and 768 × 1344 spend almost the same budget in three shapes.

## The mechanism

**Size from a ratio.** For a ratio r = W / H and a budget P, the sizes that satisfy W × H = P and W / H = r are W = √(P × r) and H = √(P / r). Then the sizes must be rounded to a multiple m, and the rounding rule matters. Rounding to the nearest multiple can overshoot the budget. Rounding down never does, but it wastes some pixels. The multiple m is 8 at the very least because of the VAE, 64 if you want to land on SDXL's list, and 32 in at least one model-specific helper.

**What grows with the pixel count.** Write N for the number of latent positions, N = (H / 8) × (W / 8). A latent grid costs in proportion to N. A self-attention layer that lets every position look at every other one compares N × N pairs. Storing that whole matrix would take N² numbers per head per layer, so a doubled side means four times the pixels and sixteen times the pairs. Memory-efficient kernels change the memory side of this. FlashAttention (Dao et al. 2022) computes the same exact attention but needs memory that grows linearly with N, while the number of comparisons still grows as N². The VAE decoder grows with the pixel count too.

## In ComfyUI

`EmptyLatentImage` accepts widths and heights from 16 to 16384 in steps of 8, defaulting to 1024, and builds `torch.zeros([batch_size, 4, height // 8, width // 8])`. The server checks the minimum and maximum of a value, and as far as the code shows not the step, so a size that is not a multiple of 8 passes validation and is rounded down by the integer division.

The "Scale Image to Total Pixels" node (`ImageScaleToTotalPixels`) is the formula above. It takes `megapixels` (default 1.0, counted as 1024 × 1024), scales both sides by √(budget / pixels), and rounds each to the nearest multiple of `resolution_steps`. A helper for one model family, `calculate_dimensions` in `comfy/ldm/hidream_o1/utils.py`, uses the same square root and then rounds down to a multiple of 32, so its result never exceeds the budget.

ComfyUI picks its attention implementation when it starts, from what is installed and from flags such as `--use-pytorch-cross-attention` and `--use-split-cross-attention`. Its VAE class carries a memory estimate for decoding that is linear in the number of latent positions, and when a decode runs out of memory it retries in tiles.

## Lab

First, what you type against what you get.

```text
requested   latent [1, 4, h, w]   decoded size   pixels lost
1024x1024   [1, 4, 128, 128]      1024x1024      0
1333x750    [1, 4, 93, 166]       1328x744       11,718
1920x1080   [1, 4, 135, 240]      1920x1080      0
```

A request for 1333 by 750 comes back as 1328 by 744. Next, the arithmetic of the scale node for a budget of one megapixel, with three values of `resolution_steps`.

```text
input        steps   result       pixels / budget   ratio error
1920x1080    1       1365x768     0.9998            -0.0002
1920x1080    8       1368x768     1.0020            +0.0020
1920x1080    64      1344x768     0.9844            -0.0156
3000x2000    1       1254x836     0.9998            +0.0000
3000x2000    8       1256x840     1.0062            -0.0032
3000x2000    64      1280x832     1.0156            +0.0256
1000x1000    1       1024x1024    1.0000            +0.0000
1000x1000    8       1024x1024    1.0000            +0.0000
1000x1000    64      1024x1024    1.0000            +0.0000
1080x1920    1       768x1365     0.9998            +0.0002
1080x1920    8       768x1368     1.0020            -0.0019
1080x1920    64      768x1344     0.9844            +0.0159
```

Rounding to the nearest multiple can land above the budget, as in 1.0062 and 1.0156, and the coarser the step, the larger the ratio error. A 16:9 picture at step 64 gives 1344 by 768, one of SDXL's training sizes. A 3:2 picture at step 64 gives 1280 by 832, which is over budget and is not on SDXL's list.

```text
SDXL sizes: 40, all sides multiples of 64: True, pixels between 0.9023 and 1.0000 of 1024 x 1024
a rule 'multiples of 64, between 90% and 100% of the budget, closest ratio' finds 40 of the 40 sizes from their rounded ratios
(the 90% floor was read off this same table, so this checks the rule's consistency, not the paper's method)
```

The 40 sizes typed in from Appendix I all have sides in multiples of 64 and between 90.2% and 100% of 1024 × 1024. A rule built from those two facts and a closest-ratio choice recovers every one of them from the table's ratio column. The floor came from this table, so it shows the sizes are consistent with such a rule and says nothing about how the authors chose them.

```text
wanted ratio    multiples of 64     multiples of 8      the 64 result is in the SDXL list
1:1             1024x1024           1024x1024           yes
4:3             1152x896            1152x864            yes
3:2             1216x832            1248x832            yes
16:9            1344x768            1352x760            yes
9:16            768x1344            760x1352            yes
```

With multiples of 8 the ratio can be matched more closely, as 1352 by 760 is for 16:9, but the result is not on SDXL's list. Last, how the costs grow for square images.

```text
side   pixels / 512x512   tokens N   N^2 entries        full matrix in fp16   VAE decode estimate (fp32)
512    1.00               4,096      16,777,216              0.03 GiB           2.13 GiB
768    2.25               9,216      84,934,656              0.16 GiB           4.79 GiB
1024   4.00               16,384     268,435,456             0.50 GiB           8.51 GiB
1536   9.00               36,864     1,358,954,496           2.53 GiB          19.14 GiB
2048   16.00              65,536     4,294,967,296           8.00 GiB          34.03 GiB
```

From 512 to 1024 the pixel count grows 4 times and the number of attention pairs 16 times. At 2048 one fp16 attention matrix for a single head and a single image would take 8 GiB, which is why a memory-efficient kernel matters. The last column is the estimate formula from `comfy/sd.py`, not a measurement, and the source comment says those constants need tweaking. It grows with the pixel count, so it quadruples when a side doubles.

## What is contested

Whether an off-list size gives a worse picture is not tested here, and the lab says nothing about image quality. N × N counts apply to a layer that attends over every latent position. SD 1.x has such layers at the top level, while SDXL omits transformer blocks at its highest feature level (the SDXL paper), so its largest attention covers a quarter of the positions. Models that cut the latent into patches have N divided by the patch area. The attention matrix column is also an upper bound that memory-efficient kernels avoid.

## Sources

- [Podell et al. 2023. SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis](https://arxiv.org/abs/2307.01952)
- [Dao et al. 2022. FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135)
- [CompVis/stable-diffusion-v1-4, model card](https://huggingface.co/CompVis/stable-diffusion-v1-4)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_post_processing.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_post_processing.py)
- [ComfyUI v0.43.0, comfy/ldm/hidream_o1/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/hidream_o1/utils.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
