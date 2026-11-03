# CU-411 - Evaluating video: a flicker metric

**Objective.** Compute two flicker scores, know what fools each one, and use them with care on real clips. Taught by Reel Rascal.

## The idea

You compare two video settings and one looks calmer. How much calmer? A number helps, if you know what it measures. Flicker scores are simple statistics on pixel values over time, and each is fooled by something. So we test them on made-up clips where we know the answer before we trust them on real ones.

## Two scores

**Temporal variance.** At each pixel position, measure the variance over time, then average across the picture.

**Second difference.** At each pixel, take f(t + 1) - 2 f(t) + f(t - 1), then average the absolute values. It's near zero when a pixel changes steadily, and big when it zigzags. A fade scores zero. A strobe scores high. Our studio's quality check, `flicker_score` in `studio/vset/qc.py`, uses this on 128 x 128 luma from 0 to 255.

No core node computes either. In a graph, you'd pull frames from a video with `GetVideoComponents` and compute it in your own node or script.

{{graph:nm_video}}

## Try to fool them

{{play:flicker}}

The lab does the same with 2D clips, and it turns up something our own code's note gets wrong. The note in `qc.py` says smooth motion scores about 0. That holds for a smooth gradient, but on a textured picture panning at 1 pixel a frame, the second difference is 16.9. That is more than a noise boil, and close to a 4% strobe. Any edge crossing a pixel makes a zigzag there.

So raw scores mix motion with flicker. The fix is the one from CU-315: **align first.** Find the shift between neighbouring frames, undo it, and score what's left. The pan drops to 0. The strobe and the boil stay put.

## Real clips

We ran the plain second difference over our web copies. The clips below are compressed copies, so read this as a rough guide.

| clip | second difference, mean | worst moment |
|---|---|---|
| LTX-2.5, virtual set | 1.34 | 2.76 |
| H3, virtual set | 2.78 | 4.93 |
| LTX-2.5, ink | 2.65 | 6.02 |
| LTX-2.5, greenhouse | 3.32 | 8.24 |
| Wan 2.2, waves | 5.44 | 18.36 |
| H3, chef with fire | 6.33 | 19.01 |
| H3, dragon in a storm | 8.21 | 27.84 |

Sort by what's in the shot: a slow push-in on a still street at the top, then waves, fire and a storm at the bottom. Those may be real flicker, or just fast detail. On this score alone, you can't tell. Our check's limit of 6.0 is labelled a starting guess in the code, and the chef and dragon clips would fail it.

{{video:showcase/v_h3_dragon.mp4|H3. Prompt: a huge gold-scaled dragon uncoils around a black stone tower during a thunderstorm. It has the highest score in the table. Watch it and decide whether that's flicker or storm.|showcase/v_h3_dragon.webp}}

The studio's records hold the scores from the original renders: 3.2 for H3 and 2.0 for LTX on the virtual-set shot. Here's the pair:

{{wipe:vset_art/ltx_result.webp|vset_art/h3_result.webp|LTX-2.5, 121 frames|MiniMax H3, 124 frames|One scene, seed 4242, a still from each clip. Records: flicker 2.0 and 3.2.}}

Numbers from one scene and one seed compare these two clips. They don't rank the models.

## What goes wrong

- **Calling a moving shot a flickering one.** Use alignment, or compare only shots with similar motion.
- **Scoring 0 to 1 images with a limit set for 0 to 255.** The second difference is off by 255, and variance by 255 squared. Always state the scale.
- **Calling a short clip perfect.** `flicker_score` returns 0.0 below 3 frames. That's no measurement, not a pass.
- **Averaging away one bad frame.** A single frame 20% too bright gives a mean of 3.2 and a worst moment of 48.6. Report the worst too.
- **Scene cuts.** A cut is a large one-time change. Variance reads it as huge. Split clips at cuts before scoring.
- **Comparing across compression.** Compression changes high-frequency detail, and that's what these scores measure. Compare like with like.
- **Different sizes.** Fine texture falls away when you shrink frames. Use the same scoring size for every clip.
- **One seed.** One number from one seed says little. Score several.

## Lab

Seven clips built to have a known answer. Variance is highest on the fade, which has no flicker at all. The plain second difference is zero on the fade and high on pans. Only the aligned column separates motion from flicker:

```text
clip                             temporal variance   second difference (qc.py)   second difference after aligning
still frame                      0.00                0.000                       0.000
slow pan, 1 pixel a frame        737.37              16.898                      0.000
fast pan, 4 pixels a frame       1062.89             36.206                      0.000
fade to black                    1314.57             0.000                       0.255
brightness strobes 4%            25.26               19.427                      19.428
texture boils, noise 5 levels    24.24               9.773                       9.773
scene cut in the middle          1084.45             3.431                       2.565
```

A check that the formula behaves: a strobe of amplitude a, on mean level L, scores 4 a L.

```text
mean luma 121.4. A strobe of amplitude a scores 4 a L on the second difference:
a = 0.01  measured 4.857   predicted 4.857
a = 0.02  measured 9.714   predicted 9.714
a = 0.04  measured 19.427  predicted 19.427
```

The scale, the short-clip case and the single bad frame:

```text
same clip on 0-1 numbers instead of 0-255: second difference 0.0762 (divided by 255), variance 0.000389 (divided by 255 squared)
fewer than 3 frames: qc.py returns 0.0, which is not a pass, only no measurement

one frame 20% too bright in 32: mean 3.238, worst moment 48.568
```

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_video.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_video.py)
- [RAFT: Recurrent All-Pairs Field Transforms for Optical Flow](https://arxiv.org/abs/2003.12039)
