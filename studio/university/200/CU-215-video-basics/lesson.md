# CU-215 - Video basics: frames, fps and temporal latents

**Objective.** Turn seconds into frames, predict the latent shape and the frame count you get back for the video families in ComfyUI, and estimate how the cost of attention grows with duration. Taught by Reel Rascal.

## The idea

A video is a stack of frames shown at some rate. A video VAE compresses the stack in space and in time. The diffusion transformer then cuts the compressed tensor into tokens and attends over all of them. Three numbers decide what you can ask for: the frame count, the VAE's temporal factor k, and the token count.

The fps does not enter the latent shape. In ComfyUI `CreateVideo` takes the frames and an `fps` value (default 30.0). That value sets how fast the frames play, so it changes the duration, frames divided by fps, and not the content. Some models are also told a frame rate while they generate. `LTXVConditioning` writes a `frame_rate` (default 25.0) into the conditioning. That is a separate input from the playback rate of `CreateVideo`.

## The maths

```
frames = seconds × fps
latent frames = (frames − 1) // k + 1          decoded frames = k · latent frames − (k − 1)
```

The "− 1" and "+ 1" are there because the first frame gets a latent frame to itself, and the rest are grouped k at a time. The Wan paper writes the input as 1 + T frames and says Wan-VAE compresses it to 1 + T/4 latent frames of H/8 × W/8 with 16 channels. In its words, "the first frame is only spatially compressed". The LTX-Video paper describes its encoder as applying 32 × 32 × 8 compression "except the first frame, which is encoded as a separate latent frame". So the lengths that survive a round trip are 1 + k · m. Any other length is floored to one of them.

For a long clip, RGB values in over latent values out tends to 3 · k · s² / c, with s the spatial factor and c the channel count. Then the transformer turns each latent frame into (H/s/p) × (W/s/p) tokens for a patch size p, and self-attention compares every token with every other:

```
tokens n = latent frames × (H/s/p) × (W/s/p)        attention pairs ∝ n²,  everything else ∝ n
```

In one plain transformer block with width d and a feed-forward factor of 4, the attention scores and mixing cost about 4 n² d operations, and the four projections plus the feed-forward layers about 24 n d². So attention's share of the block is n / (n + 6d). This is a textbook count and not a measurement.

## In ComfyUI

Each model family has its own empty-latent node, and the latent shape is written in its code:

| node | defaults | latent shape |
|---|---|---|
| `EmptyHunyuanLatentVideo` | 848 × 480, 25 frames, step 4 | [16, (n−1)//4+1, H/8, W/8] |
| `EmptyMochiLatentVideo` | 848 × 480, 25 frames, step 6 | [12, (n−1)//6+1, H/8, W/8] |
| `EmptyCosmosLatentVideo` | 1280 × 704, 121 frames, step 8 | [16, (n−1)//8+1, H/8, W/8] |
| `EmptyLTXVLatentVideo` | 768 × 512, 97 frames, step 8 | [128, (n−1)//8+1, H/32, W/32] |
| `WanImageToVideo` | 832 × 480, 81 frames, step 4 | [16, (n−1)//4+1, H/8, W/8] |

Every default is 1 plus a multiple of the node's step. The nodes themselves only floor, they do not check. On the other side, `comfy/sd.py` gives each video VAE its ratios as functions of the latent frame count a. For the Wan 2.1 and CogVideoX VAEs the upscale is a · 4 − 3 frames with spatial factor 8 (the Wan 2.2 VAE has the same frame rule with factor 16), for Mochi a · 6 − 5 with factor 8, for the Cosmos tokenizer a · 8 − 7 with factor 8, and for LTXV a · 8 − 7 with factor 32. The matching downscale is the floor of (frames + k − 1) / k. The transformer side is set in the model code. Wan's default patch size is (1, 2, 2) in `comfy/ldm/wan/model.py`, and the LTXV model uses `SymmetricPatchifier(1)`, so one token per latent position.

## Try it

Pick a model. Set seconds and frame rate until what you ask for lands exactly on the grid.

{{play:frames}}

MiniMax H3, in that lab, follows a different rule from the table above: it rounds up to 17k + 5. CU-330 compares all of them.

A video in ComfyUI is an image batch with a frame rate. Here is the smallest one, with no model at all: `batch_size` is the frame count.

{{graph:nm_video}}

{{video:families/frame-interpolation_3.mp4|Frame rate changed after the fact: RIFE v4.25 interpolation with a multiplier of 2, on a clip of a woman in a yellow raincoat walking toward the camera. The file has 247 frames at 48 fps, which fits one new frame between each pair of a 124-frame clip at 24 fps: 2 x 124 − 1. Peak 1.2 GiB.|families/frame-interpolation_3.webp}}

## Lab

The lab is arithmetic on those constants. First, five seconds at three frame rates, then what happens to a requested length for each temporal factor:

```text
seconds x fps = frames:   5 s at 16 fps = 80,  at 24 fps = 120,  at 30 fps = 150

frames asked for -> latent frames -> frames after decoding
asked   k=4 (Wan, Hunyuan)   k=6 (Mochi)    k=8 (LTXV, Cosmos)
80      20 ->  77            14 ->  79     10 ->  73
81      21 ->  81            14 ->  79     11 ->  81
97      25 ->  97            17 ->  97     13 ->  97
120     30 -> 117            20 -> 115     15 -> 113
121     31 -> 121            21 -> 121     16 -> 121
122     31 -> 121            21 -> 121     16 -> 121
125     32 -> 125            21 -> 121     16 -> 121
lengths that come back unchanged below 130:  k=4 has 33 of them, k=6 has 22, k=8 has 17;  121 is in all three
```

Five seconds at 24 fps is 120 frames, which is not a valid length for any of the three factors. By these formulas it comes back as 117, 115 or 113 frames. One extra frame fixes it: 121 = 1 + 120, and 120 is a multiple of 4, 6 and 8. Next, compression from the nodes' default sizes:

```text
model                                    k  s   ch   default size      latent shape (ch, T, H, W)   RGB values / latent values   long-clip limit
Wan 2.1 (WanImageToVideo)                4  8   16   832x480x81    (16, 21, 60, 104)            46.29                        48
HunyuanVideo (EmptyHunyuanLatentVideo)   4  8   16   848x480x25    (16, 7, 60, 106)             42.86                        48
Mochi (EmptyMochiLatentVideo)            6  8   12   848x480x25    (12, 5, 60, 106)             80.00                        96
Cosmos (EmptyCosmosLatentVideo)          8  8   16   1280x704x121   (16, 16, 88, 160)            90.75                        96
LTXV (EmptyLTXVLatentVideo)              8  32  128  768x512x97    (128, 13, 16, 24)            179.08                       192
```

The long-clip limits agree with what the papers state. The Wan paper gives 4 × 8 × 8 with 16 channels, which is 48, and the LTX-Video paper's Table 1 lists 1:48 for HunyuanVideo and 1:192 for LTX-Video. The Wan paper's figure note lists 6 × 8 × 8 with a latent dimension of 12 for Mochi, which is 96. The Cosmos row comes from ComfyUI's code only. A short clip falls below its limit: 81 frames use 21 latent frames, which stand for 81 and not 84 frames, so Wan gives 46.29. Then tokens and attention:

```text
Wan, 832x480: 81 frames -> 21 latent frames -> 32,760 tokens.  161 frames -> 41 latent frames -> 63,960 tokens
doubling the frames (81 -> 161) multiplies the tokens by 1.95 and the number of attention pairs by 3.81
LTXV, 768x512, 97 frames: 4,992 tokens
```

The LTXV model gets far fewer tokens because its VAE already compresses by 32 × 32 and it uses no patching. Doubling the frames does not quite double the tokens, because the extra latent frame at the start does not double, so the pair count grows by 3.81 and not 4. Finally the attention share for one block, with HunyuanVideo's width and feed-forward factor as listed in the LTX-Video paper:

```text
attention share of a block's operations, width d = 3072 (HunyuanVideo, feed-forward factor 4, patch 2x2x1 as listed in the LTX-Video paper), 848x480
frames  latent frames  tokens    attention share n/(n+6d)
25      7              11,130    0.376
49      13             20,670    0.529
97      25             39,750    0.683
121     31             49,290    0.728
```

At 25 frames attention is about a third of the block's operations. At 121 frames it is nearly three quarters. This is why long clips cost more than their length suggests, and why window or sparse attention appears in video models.

## What goes wrong

- **The clip comes back a few frames short.** Your length is off the grid, and the node floored it. 120 becomes 117 on Wan. Use 1 + k x m. 121 fits all three factors.
- **The clip is the right length and the wrong duration.** `CreateVideo` defaults to 30 fps. Frames made for 24 and played at 30 run fast. Set it yourself.
- **Doubling the length costs far more than double.** Attention pairs grow with the square of the tokens. Check the last table in the lab before queueing a long clip.
- **Moving a graph from one model to another breaks the shape.** Channels and spatial factors differ: 16 at 8x on Wan 2.1, 128 at 32x on LTX. A latent belongs to its VAE. Use the family's own empty-latent node.
- **`LTXVConditioning` says 25, and your video plays at 24.** They're separate values. Set them equal.

## What is contested

The frame counts after decoding come from ComfyUI's ratio functions and the description in the Wan paper. We did not run a VAE, so we have not confirmed each family's decoder against them. The attention share is a count for a plain block. Real models add text tokens, cross-attention, windows and fused kernels, and a fast kernel changes memory use more than operation counts. We say nothing about which frame rate a given model was trained at, or how motion quality depends on it.

## Sources

- [Team Wan et al. 2025. Wan: Open and Advanced Large-Scale Video Generative Models](https://arxiv.org/abs/2503.20314)
- [HaCohen et al. 2024. LTX-Video: Realtime Video Latent Diffusion](https://arxiv.org/abs/2501.00103)
- [ComfyUI v0.43.0, comfy_extras/nodes_wan.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_wan.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_hunyuan.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_hunyuan.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_mochi.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_mochi.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_cosmos.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_cosmos.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_lt.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_lt.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_video.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_video.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/ldm/wan/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/wan/model.py)
- [ComfyUI v0.43.0, comfy/ldm/lightricks/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lightricks/model.py)
