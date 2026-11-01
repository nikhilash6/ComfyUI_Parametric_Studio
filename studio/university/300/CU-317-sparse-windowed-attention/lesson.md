# CU-317 - Sparse and windowed attention

**Objective.** Cut attention's cost by limiting who sees whom, count what that saves, and say what it gives up. Taught by Madame Attention.

## The idea

Full attention costs tokens squared (CU-301). Two ways around this.

- **Windows.** Split the grid into blocks. A token attends only inside its block. Swin Transformer (Liu et al. 2021) made this common in vision, and shifted the blocks between layers so information could cross borders.
- **Sparse tokens.** Don't make a token for empty space at all. In 3D, most of a volume is empty, so only the occupied cells become tokens.

A third thing has a similar name but saves nothing by itself. **A mask** on full attention gets the same output as windows, but the backend may still build the full matrix.

## The mechanism

With n tokens and window size w, per layer:

```
full:     n × n pairs
windows:  (n ÷ w²) windows × w² × w²  =  n × w²  pairs
```

So at n = 16,384 and w = 8, the share is 64 ÷ 16,384, about 0.4% of full. Cost now grows in line with tokens.

**What you give up is reach.** A fixed grid of windows can never pass information past its border, however many layers you stack. Two ways to fix it:

- Shift the windows every second layer, as Swin does.
- Use a few global layers. Longformer (Beltagy et al. 2020) adds global tokens to its sliding windows, for text. SAM 3's image encoder mixes windowed and full blocks.

Try the reach for yourself.

{{play:windows}}

## In ComfyUI

**Windows.** `window_partition` and `window_unpartition` in `comfy/ldm/sam3/sam.py` are the plain form: reshape, pad, attend, restore. In `Block`, the attention runs with a window when `window_size` is set, and otherwise on the whole grid. The default image-encoder config has `window_size=24` with `global_att_blocks=(7, 15, 23, 31)`: most blocks are windowed, and four see everything.

**Shifted 3D windows.** `make_shifted_720Pwindows_bysize` in `comfy/ldm/seedvr/model.py` computes windows over time, height and width, with a half-window offset where a window is smaller than the grid. The SeedVR2 nodes are in `comfy_extras/nodes_seedvr.py`. This is in the same family as Swin's shift. We have no graph for it in this course.

**Sparse.** `SparseMultiHeadAttention` in `comfy/ldm/trellis2/model.py` works on a `SparseTensor`, where only occupied voxels are tokens.

**Not this.** `attention_sub_quad` in `comfy/ldm/modules/attention.py` sounds like a window, but it's a memory-saving way to compute attention, through `sub_quadratic_attention.py`. Also Wan's `window_size=(-1, -1)` in `comfy/ldm/wan/model.py` is a setting that is not in use: tokens attend the whole video grid. Don't read those names as windows.

For a graph, the 3D mesh one is the closest we have to sparse data, and it's a stand-in: see the unchecked list. It needs a Hunyuan3D 2 checkpoint.

{{graph:hunyuan3d_mesh}}

## What goes wrong

- **Seams along block edges.** Without a shift or global step, information can't cross a border. If you write a windowed model and see a grid pattern, check that first.
- **Sizes don't divide.** `window_partition` pads when the grid isn't a multiple of the window, and `window_unpartition` has to remove it. A hand-written version that forgets gives misaligned tokens.
- **You mask, and expect a saving.** The lab shows that masked full attention and separate windows agree, at 256 against 64 pairs. A mask changes the output, not necessarily the cost.
- **A sparse model runs out of memory anyway.** Occupied tokens still cost tokens squared. A denser object means many more pairs: 2% of 64³ is already 5,242 tokens.
- **You compare only cost.** Models pick windows because of what they trained on. You can't switch a trained full-attention model to windows and expect the same pictures.

## Lab

First, the partition and its inverse. We checked this rule against the real `window_partition` on a CPU, and the largest gap was 0.

```text
grid (1, 16, 16, 8) -> 16 windows of 4x4, back again identical: True
```

Now the counts.

```text
grid side  tokens    full pairs        window 8 pairs   share of full
32         1,024     1,048,576         65,536           0.0625
64         4,096     16,777,216        262,144          0.0156
128        16,384    268,435,456       1,048,576        0.0039
256        65,536    4,294,967,296     4,194,304        0.0010
window pairs grow with the tokens (n x 64). full pairs grow with the square of the tokens.
```

Next, reach. Start from the corner token, spread through a window each layer, and count how far it gets.

```text
layers  tokens reachable, fixed windows  tokens reachable, shifted every second layer   (grid 32x32, window 8, 1024 tokens)
1       64                               64
2       64                               144
4       64                               400
8       64                               1024
12      64                               1024
```

Fixed windows never leave the first block. Shifted ones cover the whole grid by layer 8, on this size. Now the mask and sparse counts.

```text
masked full attention against four separate windows: max difference 2.4e-07. pairs computed: 256 against 64
3D grid 64^3 = 262,144 cells, 2% occupied: 5,242 tokens, 27,478,564 pairs against 68,719,476,736 if every cell were a token
3D grid 128^3 = 2,097,152 cells, 1% occupied: 20,971 tokens, 439,782,841 pairs against 4,398,046,511,104 if every cell were a token
```

The occupancy percentages are examples we chose, not measurements of a real object.

## Sources

- [Liu et al. 2021. Swin Transformer: Hierarchical Vision Transformer using Shifted Windows](https://arxiv.org/abs/2103.14030)
- [Beltagy et al. 2020. Longformer: The Long-Document Transformer](https://arxiv.org/abs/2004.05150)
- [ComfyUI v0.43.0, comfy/ldm/sam3/sam.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/sam3/sam.py)
- [ComfyUI v0.43.0, comfy/ldm/seedvr/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/seedvr/model.py)
- [ComfyUI v0.43.0, comfy/ldm/trellis2/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/trellis2/model.py)
