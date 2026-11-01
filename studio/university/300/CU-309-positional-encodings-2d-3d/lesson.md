# CU-309 - Positional encodings in 2D and 3D

**Objective.** Say why tokens need a position, and pick apart the two main ways ComfyUI's models give one: a table added to the tokens, and rotation by coordinates. Taught by Madame Attention.

## The idea

CU-301 showed that attention can't see order. Shuffle the tokens and the output just shuffles with them. So a model has to be told where each token is, or a picture has no top or bottom.

Two methods are the main ones in ComfyUI's models. A third exists in the literature: a table learned in training. We did not survey which models use it here.

- **Fixed sine and cosine, added to tokens.** One table per grid.
- **RoPE from coordinates (CU-302).** No table, nothing added. Each token has ids such as (time, row, column).

## The mechanism

**One axis.** Vaswani et al. (2017) use sine and cosine at many frequencies. ComfyUI's `get_1d_sincos_pos_embed_from_grid` does the same: each frequency ω gets sin(position × ω) and cos(position × ω), and ω falls from 1 towards 1/10000.

```
ωᵢ = 1 ÷ 10000^(i ÷ (D ÷ 2))        code = [ sin(p ω₀), sin(p ω₁), ... , cos(p ω₀), cos(p ω₁), ... ]
```

Why so many? A single wave repeats, so two far positions can get the same code. Try it.

{{play:bands}}

**Two axes.** Give half the width to the row and half to the column, compute each code alone, and join them. That's `get_2d_sincos_pos_embed_from_grid` in `comfy/ldm/modules/diffusionmodules/mmdit.py`.

**Three axes.** The same, split more ways. In RoPE this shows up as `axes_dim`. WanModel splits the head width d like this: `[d − 4 (d // 6), 2 (d // 6), 2 (d // 6)]`, for time, height and width.

**A different size.** A table is built for one grid. A model that runs at another size needs a rule. PixArt divides its coordinates by a scale, `pe_interpolation`, and `base_size`, so the grid stays the same span. RoPE has no table, so it asks only for ids.

## In ComfyUI

**SD 3's file** has fixed table functions (`get_2d_sincos_pos_embed_torch` in `mmdit.py`), and `MMDiT` takes a `pos_embed_scaling_factor`. **PixArt** computes its own in `comfy/ldm/pixart/pixartms.py`. **HunYuanDiT** has both kinds in `comfy/ldm/hydit/posemb_layers.py`.

**FLUX** has no table. `process_img` builds `img_ids`, a (time index, row, column) for each token, and `EmbedND` turns them into rotations. Text tokens get ids too.

**Wan** does this over time and space, in `rope_encode`, so a video's tokens rotate by frame as well.

{{graph:wf_wan22_t2v}}

The `rope_options` settings in those functions let a caller scale and shift ids.

## What goes wrong

- **A model trained at one size is used at another, and its structure drifts.** Position isn't the only cause, but a stretched table or id grid changes what "near" means. Generate at its trained sizes first, and move away slowly.
- **You mix up the axes.** Keep height, width and frames in the order the code expects. In `process_img` rows come before columns.
- **Width doesn't split.** `get_2d_sincos_pos_embed_from_grid` asserts an even width, and each 1D half asserts too. A custom block with an odd width stops there.
- **You think adding and rotating are the same.** They aren't. An added code changes the token's numbers, and values too. RoPE changes only the score, and leaves V alone (CU-302).
- **Very long videos.** Sine waves with long wavelengths stay distinct for a long way, but a token's id can run past anything in training. The maths still works; nothing promises quality there.

## Lab

The reason for all this first.

```text
shuffle tokens then attend, against attend then shuffle: max difference 1.9e-06
```

Then a table, from the same formula as ComfyUI's. We compared the 1D formula against the real function on a CPU. The largest gap was 0 at width 8, and 3.9e-16 at width 32, which is rounding.

```text
2D table for an 8x8 grid, width 16: (64, 16), values in [-0.990, 1.000]
first 4 values for row 0, column 0: [0.0, 0.0, 0.0, 0.0]  every position different: True
frequency  wavelength in positions
0          6.3
1          62.8
2          628.3
3          6283.2
```

The first four are the sines, all zero at position 0. The wavelengths show the point of many frequencies: the short wave tells neighbours apart, and the long one keeps far positions distinct. Now see how the code's dot product falls with distance. This isn't a perfect ruler, as the last value shows.

```text
similarity of column 0 to column k, same row: [(0, 1.0), (1, 0.979), (2, 0.929), (4, 0.864), (8, 0.829), (16, 0.748), (31, 0.782)]
```

Rescaling the grid for a bigger image, as PixArt does:

```text
position grid scaled by 1/2 for a double-size image: token 2 of 32 equals token 1 of 16: True
```

And ids instead of a table, with widths that add to 128.

```text
RoPE on 3 axes, widths [16, 56, 56]: offset (0, 2, 3) near the corner 8.964835, far beyond any training grid 8.964835
head width 128: axes for time, height, width = [44, 42, 42], sum 128
head width 96: axes for time, height, width = [32, 32, 32], sum 96
latent 21x90x160, patch 1x2x2: 75,600 tokens
```

The last line is the grid of an 81-frame clip at 1280 × 720 with a 4× time and 8× space VAE. It shows how fast video grows.

## Sources

- [Vaswani et al. 2017. Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Su et al. 2021. RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/mmdit.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/mmdit.py)
- [ComfyUI v0.43.0, comfy/ldm/pixart/pixartms.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/pixart/pixartms.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/layers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/layers.py)
- [ComfyUI v0.43.0, comfy/ldm/wan/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/wan/model.py)
