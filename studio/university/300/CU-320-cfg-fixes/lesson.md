# CU-320 - RescaleCFG, CFGNorm, APG and CFG-Zero-Star

**Objective.** Say what each of these four nodes does to the cfg sum, where it hooks in, and when each is a poor choice. Taught by Dr. Denoise.

## The idea

High cfg makes numbers too large (CU-250). Each of these nodes attacks that differently, and they don't all aim at the same thing. Two limit the result's size, one limits the guidance vector, and one rescales the second branch. None of them costs an extra model call.

| Node | Hook | What it changes | Extra predictions |
|---|---|---|---|
| `RescaleCFG` | replaces the sum | The result's spread, pulled back to the positive's | 0 |
| `CFGNorm` | after the sum | Each cell's length, capped at the positive's | 0 |
| `APG` | before the sum | The guidance vector's length and direction | 0 |
| `CFGZeroStar` | after the sum | The unconditional branch, scaled by a measured number | 0 |

## What it did on one seed

All on SDXL with Euler and 20 steps, using the same prompt and seed. Compare each with the plain picture at the same cfg. CFG-Zero-Star was rendered at cfg 7, the others at 14.

| Render | cfg | Contrast | Edge | Difference from the cfg 7 picture |
|---|---|---|---|---|
| Plain | 7 | 62.0 | 13.92 | 0 |
| Plain | 14 | 71.0 | 12.34 | 30.99 |
| Rescale 0.7 | 14 | 57.1 | 15.40 | 28.69 |
| CFGNorm 1 | 14 | 18.9 | 9.67 | 60.67 |
| APG eta 1, threshold 5 | 14 | 60.1 | 16.65 | 31.20 |
| CFG-Zero-Star | 7 | 62.1 | 13.90 | 2.17 |

## RescaleCFG

This one comes from Lin et al. (2023), who list it as a fix to prevent over-exposure. The node finds the spread (standard deviation) of the positive prediction and of the cfg result, scales the result so its spread matches, then blends:

```
x_rescaled = x_cfg · (std(pos) / std(cfg))
x_final    = multiplier · x_rescaled + (1 − multiplier) · x_cfg
```

On non-flow models it does this after converting to v-prediction. On flow models, core has a separate branch that works directly on the denoised values. Multiplier 0 is plain cfg.

{{wipe:sampling_lab/guidance-cfg-14.jpg|sampling_lab/guidance-rescale-14.jpg|CFG 14|CFG 14 with Rescale 0.7|One seed. The blacks lifted and the contrast softened. The layout stayed different from cfg 7.}}

It tamed contrast from 71.0 to 57.1, below the cfg 7 picture. Notice the render's lifted blacks. If a picture goes flat, lower the multiplier.

{{graph:sd15_rescale}}

## CFGNorm

For each latent cell, it compares the length of the result with the length of the positive prediction. It shrinks any cell that is too long and never grows one. Then it multiplies the whole thing by `strength`.

```
scale = clamp(|pos| / |result|, 0, 1)        per cell, across channels
out   = result · scale · strength
```

{{wipe:sampling_lab/guidance-cfg-14.jpg|sampling_lab/guidance-cfgnorm-14.jpg|CFG 14|CFG 14 with CFGNorm 1|One seed. Washed out to pale grey, with contrast at 18.9.}}

That is the worst result of the four here. Our reading of why: it works on the denoised prediction at every step, so the shrink is repeated right along the path, and a latent pulled towards zero looks flat. This explanation is an inference from the source and this one picture. The node also has a `pre_cfg` option, which works on noise instead and can amplify. We have no render of that.

Note what `strength` is. It multiplies the whole prediction, so 0.5 halves it, as the lab shows. That is not a blend back to plain cfg, except in `pre_cfg` mode, where the source really does blend.

{{graph:sd15_cfgnorm}}

## APG

From Sadat et al. (2024). Take the guidance vector, positive minus negative. Limit its length to a threshold. Split it into the part along the positive prediction and the part at right angles to it. Multiply the part along by `eta`. The paper finds the parallel part mainly causes oversaturation, and its default is eta 0.

The node's default is eta 1, which keeps both parts whole. So at its defaults this node does not do the projection at all. Only the length limit can act. Our stored render uses those defaults.

{{wipe:sampling_lab/guidance-cfg-14.jpg|sampling_lab/guidance-apg-14.jpg|CFG 14|CFG 14 with APG eta 1|One seed. A busier scene with contrast back in range. This is the length limit alone, not the projection.}}

There is one more quirk, which we checked against the real node. The node returns a modified positive so that the normal sum gives `pos + cfg · guidance`. The paper's form is `pos + (w − 1) · guidance`. So with the limits off, the node behaves like plain cfg one higher. The tooltip says eta 1 is "Default CFG behavior", which is true of the direction, not of the size. We don't know how much this shows on a real picture, since our render has the length limit on.

To try what the paper describes, set eta to 0. The paper lists a threshold of 15 for SDXL, while the node's default is 5. Our graph uses eta 0 and has not been rendered.

{{graph:c_apg}}

## CFG-Zero-Star

From Fan et al. (2025). Each step, it measures how much of the positive noise prediction lies along the unconditional one. That number is alpha. Then it scales the unconditional branch by alpha:

```
alpha = dot(x − pos, x − uncond) / |x − uncond|²
D     = alpha · uncond + cfg · (pos − alpha · uncond)
```

The paper is about flow-matching models and has a second part, zero-init, which zeroes the first solver steps. The core node has no such option. So what core gives you is half of the paper's method.

{{wipe:sampling_lab/guidance-cfg-7.jpg|sampling_lab/guidance-cfgzerostar-7.jpg|CFG 7|CFG 7 with CFG-Zero-Star|One seed on SDXL. Nearly the same picture, with a difference figure of 2.17.}}

On this SDXL render it hardly changed anything. On SD 3.5, the stored difference from its own baseline is 7.58. We didn't log alpha on that run. If it sits near 1, as it does in the lab, that small effect is what the formula predicts. It is not a tool for rescuing a burnt picture. It doesn't try to limit size.

We also found that the core node applies alpha to the denoised prediction, while the paper's formula applies it to the velocity. The lab shows the difference is exactly x · (1 − w) · (1 − alpha). We don't know whether that was intended, or how much it matters on real pictures.

{{graph:c_cfgzero}}

## Try the sums

{{play:cfgfix}}

## What goes wrong

- **Grey, flat pictures from CFGNorm.** Lower the strength? That shrinks further. Use a lower cfg, or a different fix. It is marked experimental in core.
- **Rescale looks washed out.** Lower the multiplier. 0.7 is the node's default, not a law.
- **"I added APG and saw no projection."** At eta 1 there is none. Set eta below 1.
- **A fix with cfg left at 1.** With an ordinary sampler the second branch isn't run and arrives as zeros. Rescale, CFGNorm at strength 1 and Zero-Star then change nothing. APG does change the result, because it treats those zeros as a real prediction: tested against the node at eta 1, it made the result longer. Don't use APG at cfg 1.
- **Stacking several.** They run in hook order on each other's output. Add one, look, then decide.
- **Expecting Zero-Star to save cfg 14.** It didn't try to. See the table in the lab.

## Lab

Made-up latents and exact ports of each sum, which we also compared with the real nodes. This shows what the sums do to size. It can't show how a picture will look, and the numbers aren't comparable with the render table.

```text
method                          spread     largest    mean size of a cell
the positive prediction         1.01       3.73       1.90
plain cfg 7                     2.66       8.71       5.02
plain cfg 14                    4.82       15.12      9.08
RescaleCFG 0.7                  2.20       6.94       4.14
CFGNorm strength 1              1.01       3.77       1.90
APG eta 1, threshold 5          2.94       9.48       5.54
APG eta 0, threshold 5          1.96       5.89       3.68
CFG-Zero-Star                   4.76       14.91      8.96
```

CFGNorm lands on the positive's size. Zero-Star barely moves plain cfg 14. APG with eta 0 is smaller than with eta 1, because the parallel part really is gone.

```text
CFGNorm: can a cell ever come out larger than the positive's cell? False
CFGNorm strength 0.5 against strength 1: everything is multiplied by 0.5
```

The APG quirk, measured:

```text
APG with its limits off: eta 1, threshold 0, node cfg s
s = 3.0   largest difference from plain cfg s: 0.968    from plain cfg s + 1: 0.000001
s = 7.0   largest difference from plain cfg s: 0.968    from plain cfg s + 1: 0.000002
s = 14.0  largest difference from plain cfg s: 0.968    from plain cfg s + 1: 0.000004
```

And Zero-Star against the paper:

```text
CFG-Zero-Star: alpha here is 1.0105. Near 1 it barely differs from plain cfg: largest change 0.420
node against the paper's formula applied to x - D: largest difference 1.799, which is x * (1 - w) * (1 - alpha): True
```

## Sources

- [Lin, Liu, Li, Yang 2023. Common Diffusion Noise Schedules and Sample Steps are Flawed](https://arxiv.org/abs/2305.08891)
- [Sadat, Hilliges, Weber 2024. Eliminating Oversaturation and Artifacts of High Guidance Scales in Diffusion Models](https://arxiv.org/abs/2410.02416)
- [Fan et al. 2025. CFG-Zero-Star: Improved Classifier-Free Guidance for Flow Matching Models](https://arxiv.org/abs/2503.18886)
- [ComfyUI v0.43.0, comfy_extras/nodes_model_advanced.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_model_advanced.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_cfg.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_cfg.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_apg.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_apg.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
