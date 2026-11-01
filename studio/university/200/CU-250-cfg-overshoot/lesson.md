# CU-250 - CFG overshoot, measured on real renders

**Objective.** Spot cfg overshoot in a real picture, read what the numbers say it did, and choose what to do about it. Taught by Dr. Denoise.

## The idea

Overshoot means going past the prompt rather than further towards it. CU-208 showed the sum: cfg multiplies the difference between two predictions, and nothing limits the result. This lesson looks at what that does to a real picture, then repeats it on a problem small enough to check.

## Look first

Same prompt, same seed, SDXL base, Euler, 20 steps. Only cfg changed. Drag across.

{{wipe:sampling_lab/guidance-cfg-7.jpg|sampling_lab/guidance-cfg-14.jpg|CFG 7|CFG 14|One prompt, one seed. The whole scene was re-arranged, and the wood went a hotter orange with deeper shadows.}}

Three things changed that you can see. The desk objects moved, so this is not the same picture with more contrast. The colour got hotter. The shadows got deeper.

Here are the figures stored with each render. The difference column compares each one against the cfg 7 picture.

| Setting | Brightness | Contrast | Edge | Difference from cfg 7 |
|---|---|---|---|---|
| cfg 7 | 81.5 | 62.0 | 13.92 | 0 |
| cfg 14 | 84.0 | 71.0 | 12.34 | 30.99 |

Contrast rose by 9. Brightness barely moved. The edge figure went down, from 13.92 to 12.34, which is the opposite of what many people expect. On this seed, doubling cfg did not produce more fine detail by this measure. It produced heavier tones and a different layout.

Those figures rest on one seed, so read them as an example of the kinds of change, not as a rule.

## Why the layout moves

The sampler takes its early steps at high noise, when the broad layout is being decided. The cfg sum applies at every step, so doubling cfg doubles the push on those early steps too. Different early steps lead to a different picture, even from the same starting noise. That's why turning up cfg for a stronger look can lose a composition you liked.

## Predict it yourself

The dots are samples and the circles are what each prompt asks for. Find where samples land inside the circle, then push cfg until they fly past it.

{{play:cfg}}

The graph to try it on is the plain SDXL one. Change `cfg` on the sampler and nothing else, and keep the seed fixed.

{{graph:sdxl_txt2img}}

## What to do about it

- **Lower cfg first.** It costs nothing, and it is the only fix that removes the push itself.
- **Change one thing at a time.** Keep the seed fixed, or you can't tell cfg's effect from the seed's.
- **Don't raise steps to fix it.** The push is in the sum, and steps don't change the sum. In the lab, nothing in the cost column warns you.
- **If you need high cfg for prompt strength,** try a fix from CU-320. They limit the size of the result, but they don't all behave well. One of them washed this very picture out to grey.

## What goes wrong

- **Fried colours and crushed shadows.** Classic overshoot. Lower cfg by a third and look again.
- **"I raised cfg and the composition changed."** Expected. Cfg acts from the first step. Lock the composition with a lower cfg, or see CU-264 for changing the prompt part-way through.
- **"Higher cfg must mean more detail."** On this seed the edge figure fell. Measure on your own picture before you believe it either way.
- **Judging from a thumbnail.** A contrast bump looks good small. Check at full size.
- **Comparing across seeds.** A new seed changes the starting noise as well, so you can't tell its effect from cfg's. Fix the seed.

## Lab

The lab can't decode a picture, so it uses sixteen independent cells, each of which is a small problem with a known answer. All the pictures put a cell at one of two values, and the prompt always picks a fixed one of the two. Predictions are exact, so any overshoot comes from the sum alone.

```text
the target row has spread 1.00 and largest value 1.82
cfg    spread   largest cell   distance from target   moved from cfg 7   largest prediction   calls
1      1.06     2.05           0.45                   0.99               3.0                  20
2      1.29     2.24           0.42                   0.65               3.6                  40
3      1.45     2.39           0.54                   0.46               5.5                  40
5      1.70     2.62           0.77                   0.20               8.7                  40
7      1.89     2.80           0.96                   0.00               11.7                 40
10     2.11     3.02           1.18                   0.23               16.2                 40
14     2.35     3.25           1.42                   0.48               22.2                 40
20     2.64     3.53           1.71                   0.77               31.4                 40
```

Read the columns left to right. Spread is this toy's stand-in for contrast, and it grows with cfg, like the contrast figure above. Distance from the target is lowest at cfg 2 and climbs after that, so more cfg takes samples further from what was asked for. The largest prediction grows nearly in step with cfg, far past the real range of 1.82. The calls column is 40 from cfg 2 to cfg 20, so the bill doesn't tell you when you have gone too far.

```text
spread at cfg 14 is 1.25 times the spread at cfg 7. Steps and calls did not change, so cost does not warn you.
```

The toy's best cfg means nothing for a real model. It has exact predictions and no text encoder, so don't take cfg 2 as advice.

## Sources

- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [Chidambaram et al. 2024. What does guidance do? A fine-grained analysis in a simple setting](https://arxiv.org/abs/2409.13074)
- [Lin, Liu, Li, Yang 2023. Common Diffusion Noise Schedules and Sample Steps are Flawed](https://arxiv.org/abs/2305.08891)
