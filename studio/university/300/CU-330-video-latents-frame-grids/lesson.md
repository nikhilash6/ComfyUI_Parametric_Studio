# CU-330 - How video latents work, and each model's frame grid

**Objective.** Predict the frame count and latent shape a video model gives you, and choose a length that survives unchanged. Taught by Reel Rascal.

## The idea

An image model has a grid in space. Ask for a width that doesn't fit and it gets trimmed. A video model has a grid in time as well, and that one surprises people far more, because the clip comes back with a different length from the one you typed.

The reason is the video VAE. It doesn't store every frame. It packs groups of frames into one latent frame, so only certain frame counts land exactly on a group boundary. Each model has its own groups. CU-215 covers the plain sum. This lesson puts the three models we use side by side, and adds the one with a strange grid: MiniMax H3.

## Four numbers describe a model

- **Temporal grid:** which frame counts exist.
- **Spatial factor:** how many pixels one latent position covers along a side.
- **Channels:** how many numbers each latent position holds.
- **Patch:** how many latent positions make one token for the transformer.

Those come from the empty-latent node of each model, and they differ a lot:

| model | frames | space | channels | patch | node |
|---|---|---|---|---|---|
| LTX-2.5 | 8k + 1, floored | 32 | 128 | 1 | `EmptyLTXVLatentVideo` |
| Wan 2.2 5B | 4k + 1, floored | 16 | 48 | 2 x 2 | `Wan22ImageToVideoLatent` |
| Wan 2.1 and the 14B pair | 4k + 1, floored | 8 | 16 | 2 x 2 | `WanImageToVideo` |
| MiniMax H3 | 17k + 5, rounded up | 16 | 24 | 2 x 2 | `MiniMaxH3ImageToVideo` |

Notice two different directions. LTX and Wan floor: `(length - 1) // k + 1` drops any frames left over, and the clip comes back shorter. H3 goes the other way: `align_frame_count` adds frames until the count fits, so the clip comes back longer.

## H3's odd grid

Why 17k + 5? H3's latent frames don't all cover the same time. `FRAME_PER_TOKEN` is `(1, 4, 4, 4, 4)`: one latent frame holds one video frame, the next four hold four each, then it repeats. Five latent frames hold 17 video frames. The smallest clip is two latent frames, holding 1 + 4 = 5 frames. So every valid clip is 5 frames plus some number of 17-frame cycles, and it always has 5k + 2 latent frames.

## See it on real clips

Here's an LTX-2.5 clip from our gallery, asked for 6 seconds at 24 fps. That is 144 frames, which is off the grid. The file has 145 frames, which is 8 x 18 + 1, one more than the sum. Typed as 144, the node floors it to 137, so 145 is what the node was given: our studio's helper rounds to the nearest 8k + 1 first. The prompt was "Macro shot, liquid gold and emerald ink collide in black water and bloom into huge swirling clouds".

{{video:showcase/v_ltx_ink.mp4|LTX-2.5 at 960 x 544, 145 frames, with sound. One seed. The file's size and frame count were read with ffprobe.|showcase/v_ltx_ink.webp}}

Its size also fits the grid: 960 and 544 are both multiples of 32. A Wan 2.2 clip has 121 frames at 960 x 528. Those are multiples of 16, and 528 isn't a multiple of 32, so that size couldn't come from the LTX node without being trimmed.

{{video:showcase/v_wan_waves.mp4|Wan 2.2 at 960 x 528, 121 frames, silent. Prompt: golden sunset waves crash in slow motion on black volcanic rocks.|showcase/v_wan_waves.webp}}

Two more from our gallery, one per rule. H3 asked for 5 seconds at 9:16, and an LTX-2.5 clip at a square size:

{{video:showcase/director_portrait.mp4|MiniMax H3 at 672 x 1216, 124 frames. That is 5 + 7 x 17, on the 17k + 5 grid, and both sides are multiples of 32. Prompt: a dancer in a flowing emerald silk dress spins on a black mirrored stage, made with the studio's Director goal on the h3_t2v graph. Recorded: 67.3 s, peak 45.5 GiB. One seed.|showcase/director_portrait.webp}}

{{video:showcase/v_ltx_watch.mp4|LTX-2.5 image to video at 704 x 704, again 145 frames, 8 x 18 + 1. A square changes nothing about the grid: 704 is 22 x 32. The first frame was a gallery still of a watch movement; the camera moves in and the gold bridge turns. With sound. Recorded: 21.3 s, peak 44.6 GiB. One seed.|showcase/v_ltx_watch.webp}}

## Try it

{{play:frames}}

{{graph:nm_video}}

That graph is a video with no model at all: eight frames in an image batch, a frame rate, a file. A video in ComfyUI is an image batch until `CreateVideo` wraps it. `batch_size` is the frame count. Everything else in this lesson happens before those frames exist.

{{graph:wf_ltx25_t2v}}

In the full LTX graph, find `EmptyLTXVLatentVideo`, `CreateVideo` and `SaveVideo`. The first sets the grid and the second sets the playback rate. Neither checks the other.

## What goes wrong

- **The clip is a few frames short.** You typed a length off an LTX or Wan grid, and the node floored it. Type 8k + 1 or 4k + 1. For H3, type 17k + 5. A count that fits comes back as typed.
- **Your H3 clip is longer than you asked.** It snapped up. 100 frames becomes 107.
- **The picture is a slightly different size.** The width and height were floored to the spatial grid. At 850 wide, LTX keeps 832. Wan 2.2 5B keeps 848. Use the node's step and the problem goes away.
- **You used a Wan 2.1 VAE with a 5B latent.** Channels and space differ: 16 at 8x against 48 at 16x. Expect a shape error; we didn't try it. A VAE belongs to its latent format, however similar the names.
- **Sped-up or slowed motion.** The `fps` in `CreateVideo` sets playback, and doesn't change the frames. Frames made for 24 and played at 16 take longer and look slower. Some models are told a rate while sampling too, which CU-331 covers.

## Lab

The lab runs each family's rule on the same request. Five seconds at 24 fps is 120 frames, off every grid:

```text
You ask for 5 seconds at 24 fps, 120 frames, at 832 x 480.
model             frames you get   seconds   latent (C, T, H, W)      latent values   video tokens
LTX-2.5           113              4.708     (128, 15, 15, 26)        748,800         5,850
Wan 2.2 5B        117              4.875     (48, 30, 30, 52)         2,246,400       11,700
Wan 2.1 and 14B   117              4.875     (16, 30, 60, 104)        2,995,200       46,800
MiniMax H3        124              5.167     (24, 37, 30, 52)         1,385,280       14,430
```

Same request, three different lengths. Token counts differ a lot too, and those decide the sampling cost. The 14B route has four times the tokens of 5B at the same picture size. Next, the frame counts available on each grid:

```text
Frame counts on each grid, up to 130:
LTX-2.5       17 counts, the last few [105, 113, 121, 129]
Wan 2.2 5B    33 counts, the last few [117, 121, 125, 129]
MiniMax H3     8 counts, the last few [73, 90, 107, 124]
```

H3 has few choices, so plan its lengths around them. Then H3's cycle, summed by hand:

```text
H3 frames per latent frame, summed:
   5 frames ->   2 latent frames ->   5 frames back
  22 frames ->   7 latent frames ->  22 frames back
  39 frames ->  12 latent frames ->  39 frames back
 124 frames ->  37 latent frames -> 124 frames back
```

And the real clips:

```text
Frame counts of real clips in our gallery, against the grid:
LTX-2.5, 6 s asked        145 frames  on the grid: True
LTX-2.5, virtual set      121 frames  on the grid: True
Wan 2.2, 5 s asked        121 frames  on the grid: True
MiniMax H3, 5 s asked     124 frames  on the grid: True
```

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_lt.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_lt.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_wan.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_wan.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_minimax_h3.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_minimax_h3.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax/model.py)
- [ComfyUI v0.43.0, comfy/latent_formats.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/latent_formats.py)
