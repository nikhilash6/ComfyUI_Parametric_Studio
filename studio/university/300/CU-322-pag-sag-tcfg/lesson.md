# CU-322 - PAG, SAG and TCFG: what the extra guidance costs

**Objective.** Say what each of these nodes changes, count its model calls, and know which model families it can work on. Taught by Dr. Denoise.

## The idea

Cfg compares two prompts. These nodes make a comparison that doesn't need a second prompt.

- **PAG and SAG** damage something on purpose, predict again, and push away from the damaged answer. That means one more prediction per step.
- **TCFG** cleans up the unconditional prediction before the normal sum. It runs no extra prediction.

## The cost, counted

From each node's source, for one step:

| Setup | Predictions per step | Why |
|---|---|---|
| cfg 1 | 1 | The second branch is dropped |
| cfg 7 | 2 | Positive and negative |
| cfg 7 + TCFG | 2 | One SVD instead of a prediction |
| cfg 1 + PAG | 2 | Positive and the damaged positive |
| cfg 7 + PAG | 3 | Those, and the negative |
| cfg 1 + SAG | 3 | SAG forces the negative back on, because it needs it |
| cfg 7 + SAG | 3 | Positive, negative, and the blurred negative |

{{play:calls}}

Here are the stored clock times of our 20-step SDXL renders. The timer polled every 1.5 s, so only large gaps mean anything. PAG's is the one gap clearly above that step.

| Render | Seconds | Contrast | Difference from plain cfg 7 |
|---|---|---|---|
| Plain cfg 7 | 3.6 | 62.0 | 0 |
| TCFG | 4.5 | 58.4 | 22.27 |
| SAG 0.5 | 4.8 | 63.7 | 11.24 |
| PAG 3 | 6.0 | 66.8 | 25.74 |

## PAG

Perturbed-attention guidance, from Ahn et al. (2024). The paper replaces the self-attention map with an identity, so each token only gets back its own value. In core it's two lines:

```python
def perturbed_attention(q, k, v, extra_options, mask=None):
    return v
```

The node installs it on the self-attention of the U-Net's middle block, predicts the positive again, and adds the difference:

```
result + (pos − pos_damaged) · scale
```

It uses the positive and not the negative, so it works at cfg 1 too, for two predictions. The paper reports using it with or without CFG.

{{wipe:sampling_lab/guidance-cfg-7.jpg|sampling_lab/guidance-pag-7.jpg|CFG 7|CFG 7 with PAG 3|One seed on SDXL. Objects look cleaner and more separate, and the layout moved. The edge figure fell from 13.92 to 11.54.}}

{{graph:sd15_pag}}

## SAG

Self-attention guidance, from Hong et al. (2022). The abstract describes it as blurring only the regions the model attends to. The node records the unconditional's middle-block attention, marks tokens whose incoming attention is above a fixed 1.0, blurs those parts of the unconditional prediction, re-noises that, and predicts again:

```
degraded = blur where attention is high, unconditional elsewhere
result + (degraded − prediction_on_degraded) · scale
```

Because it needs the unconditional, it sets `disable_cfg1_optimization`. So cfg 1 costs three, not one.

{{wipe:sampling_lab/guidance-cfg-7.jpg|sampling_lab/guidance-sag-7.jpg|CFG 7|CFG 7 with SAG 0.5|One seed on SDXL. The same layout with changed detail: the smallest shift of the three here.}}

{{graph:sd15_sag}}

## TCFG

Tangential Damping CFG, from Kwon et al. (2025). It stacks the unconditional and positive scores into a two-row matrix, takes an SVD, and keeps only the unconditional's part along the top direction:

```
A = [uncond_score, cond_score]         SVD → top right vector v1
uncond_new = (uncond_score · v1) v1
```

The paper describes this as dropping the tangential part, which may interfere with the path to the prompt. After that, the normal cfg sum runs. It's a pre-cfg hook, so it needs both predictions: at cfg 1 it has nothing to do and returns at once.

{{wipe:sampling_lab/guidance-cfg-7.jpg|sampling_lab/guidance-tcfg-7.jpg|CFG 7|CFG 7 with TCFG|One seed on SDXL. Different objects, softer contrast. This is not a subtle change.}}

{{graph:c_tcfg}}

## Which models they fit

PAG and SAG in core name a U-Net location: `"attn1"` in the `"middle"` block. Reading the code, Flux and MMDiT models take block patches from a `"dit"` key and never read `"attn1"`. So we expect two things, which we did not run:

- **Core PAG on those models** would make the extra prediction, get the same answer, and add zero. You'd pay for nothing, with no warning.
- **Core SAG on those models** would never record attention, so its blur step has nothing to read and should fail.

For SD3-style transformers, `SkipLayerGuidanceSD3` exists as a separate idea, and our Sampling Lab has a [render of it](#sampling/renders). TCFG works on predictions only, so it doesn't care about the model's shape.

## What goes wrong

- **Slow runs after adding PAG and SAG together.** Four predictions per step. Pick one.
- **SAG at cfg 1 isn't cheap.** Three predictions, as above.
- **No visible PAG effect on a transformer.** See above. Check for a difference against the same seed without it.
- **Too much PAG.** It adds to the same result that cfg made, so high scale and high cfg add up. Lower cfg when you add it.
- **PAG scale 0.** The source returns early and skips the extra prediction, so it's a real off switch.
- **Assuming TCFG is free.** It adds no prediction, but it does one SVD on the whole latent every step. On a big latent that isn't nothing, though we didn't measure it separately.

## Lab

A stand-in model counts its own predictions.

```text
setup                          predictions per step   over 20 steps
cfg 1                          1                      20
cfg 7                          2                      40
cfg 7 + TCFG                   2                      40
cfg 1 + PAG 3                  2                      40
cfg 7 + PAG 3                  3                      60
cfg 7 + PAG scale 0            2                      40
cfg 1 + SAG .5                 3                      60
cfg 7 + SAG .5                 3                      60
cfg 7 + PAG + SAG              4                      80
```

Then the three ideas on small tensors. These inputs are made up, so read what kind of change happens, not its size.

```text
PAG: normal attention moves each token by 2.41 on average. The perturbed version moves it by 0.0.
TCFG: unconditional score length 15.068, after damping 14.802, what was removed 2.817
      angle to the conditional: cosine 0.938 before, 0.986 after
      model calls added by that: 0. The cost is one SVD per step.
```

TCFG turned the unconditional towards the positive and barely changed its length.

## Sources

- [Ahn et al. 2024. Self-Rectifying Diffusion Sampling with Perturbed-Attention Guidance](https://arxiv.org/abs/2403.17377)
- [Hong et al. 2022. Improving Sample Quality of Diffusion Models Using Self-Attention Guidance](https://arxiv.org/abs/2210.00939)
- [Kwon et al. 2025. TCFG: Tangential Damping Classifier-free Guidance](https://arxiv.org/abs/2503.18137)
- [ComfyUI v0.43.0, comfy_extras/nodes_pag.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_pag.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_sag.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_sag.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_tcfg.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_tcfg.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/model.py)
