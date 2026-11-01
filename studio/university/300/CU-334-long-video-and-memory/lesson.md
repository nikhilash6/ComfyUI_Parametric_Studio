# CU-334 - Long video and memory: chunks, tiled decode, and what truly helps

**Objective.** Say which part of a long-video run is short of memory, choose the fix that touches that part, and plan a chain of clips. Taught by Reel Rascal.

## The idea

A video run has three separate memory problems, and they happen at different moments.

1. **Sampling.** The model attends over all tokens, so it grows with resolution and length.
2. **Decoding.** The VAE turns latents into frames, using VRAM.
3. **The frames themselves.** Finished frames sit in system RAM as a big float32 batch.

Most bad advice comes from fixing the wrong one. Tiled decode is the classic case. It's a real fix for problem 2, and it does nothing at all for 1 or 3. If the error appears during sampling, no tile setting can help you.

## Find which one is failing

Watch where it stops. A sampler progress bar that fails on the first step is problem 1. A failure after the bar finishes, at the decode node, is problem 2. A slow crawl or a killed process around `CreateVideo`, with VRAM fine, is often problem 3. Then read the tables in the lab below.

## Fix by fix

**Shorter or smaller.** The only direct fix for problem 1. Tokens grow in line with length, and attention pairs with the square. Twice the length means about 3.8 times the pairs. Halving both sides of the picture divides tokens by 4.

**Tiled decode.** For LTX the estimate counts all frames and all positions, so tiles make a big difference: at 1920 x 1088 it falls from 37.4 GiB to 2.3 GiB. A long clip costs no more per tile. Tiled decode saves memory but not work, as CU-217 showed.

**But not for every VAE.** Wan 2.2's estimate has no frame count. H3's clamps to one chunk, and its `decode_tiled` ignores your settings and calls `decode`. On H3, tile settings do nothing.

**A chain of clips.** No setting makes one model call shorter than the clip you asked for, so long videos are made of short clips. Render a clip, use its last frame or frames to start the next, join them, and drop the repeated frames. Peak sampler memory is one clip's, however long the chain gets. The cost moves from memory to seams.

**Sequential tools built for it.** `MiniMaxH3AddGuide` can anchor a frame or a short clip at a chosen frame, which is the natural tool for carrying motion across a join. `LTXVAddGuide` does a similar job for LTX, and we've only read that node's code here.

**Context windows.** Core has `ContextWindowsManual`, marked experimental, which samples long latents in overlapping windows. Our earlier studio's notes record one attempt on Wan that rendered black, on another stack. So try it, but test it on something small first.

**Things that don't help.** Fewer steps don't reduce peak sampler memory, only time. CFG 1 reduces time per step, and a lower peak only if the two passes were not already being run in separate batches. We haven't measured that here.

## The join, with no model

Here's the last step of a chain, on a CPU. Clip 2 begins on clip 1's last frame, so the graph keeps that frame only once.

{{graph:e_chain_join}}

{{play:longchunks}}

## What it looks like

Our gallery's short film came from such a recipe, with a prompt about a lamplighter rowing through a flooded city. It's 544 frames against 124 for one H3 shot, so it can't be a single render at that clip length. Recorded peak on our test machine: 76.2 GiB, with the whole recipe taking 689.8 s. That recipe does more than video generation, so don't read the peak as a video figure.

{{video:showcase/short_film.mp4|A short film from a recipe, 544 frames with sound. Watch the cuts: those are where one clip hands to the next.}}

## What goes wrong

- **Out of memory on the first sampling step, and you add tiles.** Tiles only act at decode. Lower the length or the size.
- **Tiles change nothing on H3.** They can't: see above. Use plain `VAEDecode`.
- **A jump about every 2.3 seconds in a tiled LTX decode.** Those are likely the temporal tile joins: at 24 fps, tiles of 8 latent frames with an overlap of one start every 56 frames. That overlap, the graph's, blends a single frame at each join. Try more, with `temporal_overlap` 16, which is two latent frames and blends 9, and see if it clears.
- **Each clip drifts further from the first.** Every link in a chain starts from a generated frame, so errors build up. Our earlier notes record identity falling in a 2-clip test on H3, and colour drift being a known issue. Restate the description in each prompt and use a fixed reference where the model allows it.
- **A stutter at every join.** A frame is repeated. Drop the first frame of each new clip, as the graph above does.
- **RAM runs out at the end, with VRAM fine.** 60 seconds at 1920 x 1088 is 33.6 GiB of float32. Save each clip to disk and join files, not batches.

## Lab

Tokens and pairs by length, at 960 x 544:

```text
seconds at 24 fps   LTX tokens   Wan 5B tokens   H3 video tokens   attention pairs against 5 s
5                   8,160        15,810          18,870            1.0x
10                  15,810       31,110          36,720            3.8x
20                  31,110       61,710          72,420            14.5x
40                  61,710       122,910         146,370           57.2x
```

Decode estimates, from `comfy/sd.py`, at 1920 x 1088, in 2-byte weights. These are the numbers ComfyUI plans with:

```text
decode memory estimate, GiB, 1920 x 1088:
frames   LTX whole   LTX temporal tile 8   LTX + spatial tile 16   Wan 5B   H3
121      37.4        18.7                  2.3                     31.1     1.7
241      72.4        18.7                  2.3                     31.1     1.7
481      142.4       18.7                  2.3                     31.1     1.7
```

Read across a row. With tiles, LTX's cost stops growing with length. Wan and H3 don't grow to begin with. Then the frames in RAM:

```text
the finished frames in system RAM as a float32 IMAGE:
960x544, 5 s at 24 fps: 0.7 GiB
1344x768, 15 s at 24 fps: 4.2 GiB
1920x1088, 60 s at 24 fps: 33.6 GiB
```

A chain's cost. Each extra overlap frame costs little work, so seams matter more than render time when choosing:

```text
a chain to reach 60 s at 24 fps (1440 frames) with H3-sized clips of 124 frames
overlap  1 frames: 12 clips, 1488 frames rendered for 1477 kept, 1.007 times the work, 11 seams
overlap  5 frames: 13 clips, 1612 frames rendered for 1552 kept, 1.039 times the work, 12 seams
overlap 22 frames: 14 clips, 1736 frames rendered for 1450 kept, 1.197 times the work, 13 seams
```

And how many pieces a temporal tile setting makes:

```text
16 latent frames, temporal tile 8, overlap 1: 3 decodes, starts [0, 7, 14]
31 latent frames, temporal tile 8, overlap 1: 5 decodes, starts [0, 7, 14, 21, 28]
61 latent frames, temporal tile 8, overlap 1: 9 decodes, starts [0, 7, 14, 21, 28, 35, 42, 49, 56]
```

## Sources

- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax/vae.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_context_windows.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_context_windows.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_images.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_images.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
