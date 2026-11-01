# CU-303 - DiT and MM-DiT blocks

**Objective.** Trace how a transformer replaces the U-Net: patches become tokens, a time vector scales every block, and text and image can share one attention. Taught by Madame Attention.

## The idea

Stable Diffusion 1.5's U-Net shrinks the image, works, and grows it back. A DiT (diffusion transformer) keeps one grid size and stacks identical blocks over it. Peebles and Xie (2022) showed this working on latents, and most newer image and video models in ComfyUI are some form of it.

Three things make that possible:

- **Patches.** Cut the latent into squares and flatten each square into one token. That's the idea of ViT, Dosovitskiy et al. (2020).
- **adaLN (adaptive layer norm).** The model must know the noise level. A block turns the time vector into a scale and shift, and applies them to the whole sequence.
- **A way in for the text.** Either cross-attention as in CU-301, or a joint block where text and image sit in one sequence. The second is what MM-DiT does.

## The mechanism

**Patches.** With patch size p, a latent of c channels, height h and width w becomes (h ÷ p) × (w ÷ p) tokens of width c × p × p. A linear layer then brings each token to the model's width. Cost follows CU-301: tokens squared.

{{play:patches}}

**adaLN.** Inside a block, the time vector c becomes numbers through a small network. Then:

```
x' = shift + x × (1 + scale)                  shift and scale: one value per channel, for the whole sequence
x  = x + gate × attention(x')                 gate: another output, how much of the block's result to keep
```

Each channel gets one scale and one shift, shared by all tokens. So the time vector can't aim at one token. It sets the block's general behaviour for this noise level, and attention does the per-token work. That is `modulate` in SD 3. It isn't true of every model: FLUX's `apply_mod` can take `modulation_dims`, which gives different ranges of tokens different values, and `WanModel` reshapes its time embedding so that a timestep per token gives values per token.

**adaLN-Zero.** DiT starts the network that makes these numbers at zero. Gate zero means the block returns its input, so at the start of training the stack is the identity. The lab checks that this is exactly true. That helps training only: a checkpoint you load has already moved on.

**Joint attention.** MM-DiT (Esser et al. 2024) gives text and image their own projections, then joins q, k and v along the token axis and attends over everything. Text sees the image and the image sees the text. Plain cross-attention goes one way.

## In ComfyUI

`modulate` in `comfy/ldm/modules/diffusionmodules/mmdit.py` is the formula above, and `DismantledBlock` carries the adaLN layers. `_block_mixing` runs one text block and one image block together: it collects both sets of q, k and v and sends the joined sequence through `optimized_attention`. That is SD 3, shown in this graph.

{{graph:sd35_flow}}

FLUX has its own version in `comfy/ldm/flux/layers.py`. `DoubleStreamBlock` keeps text and image apart with their own weights and modulation, and joins them only for attention. `SingleStreamBlock` treats them as one sequence with shared weights. `Modulation` is where the time vector becomes those numbers, and in `apply_mod` you can see scale and shift used. The FLUX model's `process_img` rearranges with the same pattern as the lab's patchify, `b c (h ph) (w pw) -> b (h w) (c ph pw)`.

{{graph:wf_flux2_klein}}

PixArt (`comfy/ldm/pixart/`) keeps text separate and reaches it through cross-attention. Not every DiT is joint. To learn which kind a model is, look at its block class in `comfy/ldm`.

## What goes wrong

- **Your size is off-grid.** A latent side that doesn't divide by the patch has to be padded: `pad_to_patch_size` in `comfy/ldm/common_dit.py`. Choose sizes that divide cleanly.
- **A DiT costs more than you budgeted at large sizes.** Twice the side means sixteen times the pairs, with no U-Net stage that shrinks the grid to save you. Try the play above. Then read the budget lessons.
- **A U-Net patch doesn't apply.** U-Net hooks like input and output block patches have no meaning on a block stack. Nodes written for one family can silently do nothing or fail on another. Read which family the node targets.
- **You think a token is a pixel.** At patch 2, an 8× VAE, one token covers 16×16 pixels. Fine detail has to be carried in the token's channels.
- **You assume the prompt is only cross-attended.** On joint models, text tokens also get changed in each block. Hook points that expect plain cross-attention may not exist at all.

## Lab

Patches, tested by going there and back.

```text
latent (1, 4, 16, 16) -> tokens (1, 64, 16), back again identical: True
image      latent side   patch  tokens   token pairs
512        64            2      1,024    1,048,576
1024       128           2      4,096    16,777,216
2048       256           2      16,384   268,435,456
1024       128           1      16,384   268,435,456
```

Going from patch 2 to patch 1 costs as much as doubling the image side. Now the modulation.

```text
one scale and one shift per channel, the same for all 64 tokens: largest gap from that formula 0.0e+00
another time vector changes the output: True
zero-initialised gate: the block returns its input: True
```

Last, joint attention on random vectors. We nudge one token and see who moves.

```text
joint attention: 8 text + 64 image tokens -> a matrix of 5,184 pairs
change one text token: image output moves by 41.304.  change one image token: text output moves by 0.177.  so it runs both ways
plain cross-attention, for contrast: 64 queries x 8 keys = 512 pairs, and the text tokens get no new values from it
```

Ignore the size of those two moves: the weights are random. The point is that both are above zero. Joint attention also costs more than cross-attention here, 5,184 pairs against 512, though a real block would also have a self-attention to count.

## Sources

- [Peebles, Xie 2022. Scalable Diffusion Models with Transformers](https://arxiv.org/abs/2212.09748)
- [Esser et al. 2024. Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206)
- [Dosovitskiy et al. 2020. An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale](https://arxiv.org/abs/2010.11929)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/mmdit.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/mmdit.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/layers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/layers.py)
- [ComfyUI v0.43.0, comfy/ldm/pixart/pixartms.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/pixart/pixartms.py)
