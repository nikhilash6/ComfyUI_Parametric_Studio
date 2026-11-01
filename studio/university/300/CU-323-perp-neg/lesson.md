# CU-323 - Perp-Neg: negatives that do not fight the prompt

**Objective.** Say what plain cfg does when two prompts overlap, what Perp-Neg does differently, and what it costs. Taught by Dr. Denoise.

## The idea

Say you ask for a lion and negate "a mane". The two predictions share nearly everything, because both describe a big cat. Plain cfg amplifies the difference between them, and that difference is small and odd. The authors of Perp-Neg describe this as the negative prompt failing when there is an overlap between the main and negative prompts.

Perp-Neg measures both prompts from an empty prompt, as arrows. It splits the negative into two parts: the part along the positive, and the part at right angles to it. It only removes the right-angle part. Whatever the negative shares with the positive, it leaves alone.

## The maths

From `perp_neg` in `comfy_extras/nodes_perpneg.py`:

```
pos  = D_pos − D_empty
neg  = D_neg − D_empty
perp = neg − (neg·pos / |pos|²) · pos
D    = D_empty + cfg · (pos − neg_scale · perp)
```

Compare plain cfg, on the same arrows: `D = D_neg + cfg · (D_pos − D_neg)`.

Since `perp` has no part along `pos`, the distance travelled along the positive is always cfg times its length, whatever the negative says. That is the lab's main result.

{{play:perp}}

## In ComfyUI

`PerpNegGuider` is a guider, so it needs `SamplerCustomAdvanced` and not `KSampler`. It takes a positive, a negative, an `empty_conditioning`, `cfg` and `neg_scale`. Encode an empty string for the empty input. The older `PerpNeg` node still exists but is marked deprecated in the source. Use the guider.

{{graph:sd15_perpneg}}

The cost is three predictions per step: positive, negative and empty. They go in one `calc_cond_batch` call, so they may share a batch. Two settings cut that down.

- `neg_scale` 0 drops the negative. The result is plain cfg against the empty prompt.
- `neg_scale` 0 and cfg 1 also drop the empty, leaving one prediction.

Here is our one render. The negative is "blurry, low quality, watermark, text", which doesn't overlap an astrolabe at all, so this isn't the case Perp-Neg was made for. It only shows the method isn't harmful with an ordinary negative on this seed.

{{wipe:sampling_lab/guidance-cfg-7.jpg|sampling_lab/guidance-perpneg-7.jpg|CFG 7|CFG 7 with the Perp-Neg guider|One seed on SDXL. Similar scene, changed objects, and almost the same contrast: 62.4 against 62.0.}}

The paper also uses this for 3D: steering views away from a canonical front view, and addressing the multi-head Janus problem in text-to-3D. We didn't try those.

## What goes wrong

- **"PerpNegGuider won't connect to KSampler."** It outputs `GUIDER`. Use `SamplerCustomAdvanced`.
- **The empty input is left out.** It is required. Encode an empty string with the same text encoder.
- **Using a zeroed conditioning for empty when your model expects the encoded one, or the reverse.** We haven't measured the difference. Follow the model's usual pairing and keep it consistent.
- **A negative that points opposite the positive has less effect than before.** Plain cfg gets an extra push from it. Perp-Neg ignores that part, by design. So a negative prompt that worked as a general booster may feel weaker. The lab's bottom row shows it.
- **High neg_scale.** It multiplies with cfg, since the sum is cfg times neg_scale times perp. So raise it slowly.
- **Batches.** The dot product in the source sums over the whole tensor and isn't per image. Images in a batch affect each other's split, as the lab shows. Test on batch size 1 if you're comparing.

## Lab

The arrows are two numbers each, drawn from the empty prediction. The positive is length 1, and so is the negative. Cfg is 7 and neg_scale is 1.

```text
negative's angle to the positive   plain along   plain sideways   perp-neg along   perp-neg sideways
0                                  1.00          0.00             7.00             0.00
15                                 1.20          -1.55            7.00             -1.81
45                                 2.76          -4.24            7.00             -4.95
90                                 7.00          -6.00            7.00             -7.00
135                                11.24         -4.24            7.00             -4.95
180                                13.00         -0.00            7.00             -0.00
```

Read the "along" columns. Perp-Neg is always 7. Plain cfg goes from 1 to 13. That's the trade in one table. When prompts overlap, plain cfg loses nearly all its push along the positive. When they oppose, it gets extra.

```text
at 0 degrees the two prompts are the same: plain cfg has nothing left to amplify, Perp-Neg still goes the full 7.
```

And the small print on batches. A batch of two random arrows:

```text
batch of 2: the part left over is at right angles to the whole batch: +4.4e-16. Image 1 alone: +1.69, image 2 alone: -1.69
```

## Sources

- [Armandpour et al. 2023. Re-imagine the Negative Prompt Algorithm: Transform 2D Diffusion into 3D, alleviate Janus problem and Beyond](https://arxiv.org/abs/2304.04968)
- [ComfyUI v0.43.0, comfy_extras/nodes_perpneg.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_perpneg.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
