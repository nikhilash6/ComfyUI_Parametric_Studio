# CU-420 - Rank, alpha, DoRA, LoKr and the other adapters

**Objective.** Read any adapter in `comfy/weight_adapter` as a sum, count what it stores and what it can reach, and say what alpha means in each. Taught by Tinker Tune.

## The idea

A LoRA is only one way of storing a change to a weight. The folder `comfy/weight_adapter` holds six. They're all answers to one question: how do you describe a big change with few numbers? Every answer limits what the change can be, in its own way.

`load_lora` tries them in turn on each layer's keys, so a file doesn't need a type label. The names decide.

| adapter | keys in the file | the change | train it in core? |
|---|---|---|---|
| LoRA | `lora_up`, `lora_down` (and spellings) | s · (α / r) · up @ down | yes |
| LoHa | `hada_w1_a`, `hada_w1_b`, `hada_w2_a`, `hada_w2_b` | s · (α / r) · (w1a @ w1b) ⊙ (w2a @ w2b) | yes |
| LoKr | `lokr_w1`, `lokr_w2`, or their factored forms | s · scale · w1 ⊗ w2 | yes |
| OFT | `oft_blocks`, `rescale` | rotate the weight | yes |
| GLoRA | `a1`, `a2`, `b1`, `b2` and more | a general form | no (commented out in `adapter_maps`) |
| BOFT | `oft_blocks` with another shape | rotate the weight, stacked | no (commented out) |

Here ⊙ is multiply element by element, and ⊗ is the Kronecker product: every number of w1 times a whole copy of w2. DoRA is not a separate row, because it's a change of how any of the six is applied: each one calls `weight_decompose` when the file has a `dora_scale`.

{{graph:sd15_train_lora}}

## What each one stores and reaches

Rank here means the true mathematical rank of the change: how many independent directions it holds.

```text
how much each format stores for one 1280 x 1280 layer. Full weight: 1,638,400 numbers
format                   numbers stored   share of full   largest rank it can reach
LoRA rank 8              20,480           0.0125          8
LoRA rank 32             81,920           0.0500          32
LoHa rank 8              40,960           0.0250          64
LoKr factor 4 (4 x 320)  102,416          0.0625          1280
LoKr factor 8 (8 x 160)  25,664           0.0157          1280
LoKr factor 16 (16 x 80) 6,656            0.0041          1280
LoKr factor 32 (32 x 40) 2,624            0.0016          1280
```

Check it. Here are the true ranks, measured, on a smaller layer:

```text
measured rank of the change on a 96 x 96 layer, random factors (singular values above 1e-5 of the largest)
LoRA rank 4: 4   LoHa rank 4: 16 (up to 4 x 4)   LoKr 8 x 12, full factors: 96, from 208 numbers against LoRA's 768
```

So LoHa multiplies two rank 4 pieces element by element and reaches rank 16 at twice the cost. The paper behind it, FedPara, says in its abstract that it's "not restricted to low-rank constraints". And LoKr, from 208 numbers, reaches full rank.

Try the sizes.

{{play:adapters}}

Rank isn't the same thing as power. A Kronecker product is one small shape repeated over the layer, so it can reach high rank and still miss most things:

```text
the price of that rank: a Kronecker product is one shape repeated. Relative error of the best possible fit to two 96 x 96 targets, about the same budget of numbers
target                  LoKr 8 x 12 (208 numbers)   LoRA rank 1 (192 numbers)
made of a Kronecker     0.057                       0.937
made of rank 4          0.962                       0.781
```

When the target really is a Kronecker shape, LoKr fits it, with error 0.057 and LoRA at 0.937. When the target is low rank, LoRA does better, at 0.781 and LoKr at 0.962. These targets are built by hand, on purpose. We don't know which shape the change a real image LoRA needs is closest to, and this lab doesn't settle it.

## What alpha means

Don't assume alpha works the same way for all of them.

```text
alpha: the same factors, scale alpha / rank
format and file            alpha   scale
LoRA rank 8                8       1.0
LoRA rank 8                1       0.125
LoRA rank 8, no alpha      none    1.0
LoKr, full w1 and w2       1       1.0  (no rank to divide by: alpha is ignored)
OFT                        1       norm limit, not a scale
```

- **LoRA, LoHa:** scale is alpha / rank, or 1 with no alpha.
- **LoKr:** scale is alpha / dim only if a factor was split into two thin matrices. A file with plain `lokr_w1` and `lokr_w2` ignores alpha, and that's what core's trainer makes.
- **OFT, BOFT:** alpha is a limit on the size of the rotation (`if q_norm > alpha`), not a scale.

Core's trainer always creates new adapters with alpha 1.0, so a rank 8 LoRA has scale 1/8. Learning rate and rank are therefore tied together in that trainer, a thing to keep in mind when you compare runs at different ranks.

## Rank in the trainer

`TrainLoraNode`'s `rank` widget is passed to `create_train`, and it means something different per algorithm:

```text
what TrainLoraNode's rank widget means, per algorithm, for a 1280 x 1280 layer at rank 8
algorithm   rank widget used as   result
LoRA        rank                  up 1280 x 8, down 8 x 1280: 20,480 numbers
LoHa        rank                  two such pairs: 40,960 numbers
LoKr        factor                w1 8 x 8, w2 160 x 160: 25,664 numbers
OFT         factor                160 blocks of 8 x 8: 10,240 numbers
```

For LoKr and OFT the widget is a factor for splitting the layer's size, by `factorization` in `base.py`. If the size doesn't divide by it, the function falls back to a nearby split. So "rank 8" can't be compared across algorithms.

## DoRA

The DoRA paper's abstract says it "decomposes the pre-trained weight into two components, magnitude and direction". In ComfyUI's code a file adds a `dora_scale` key to a layer, and `weight_decompose` uses it: add the change, then rescale each column to the stored size. So a DoRA file stores a size per column as well as the factors.

```text
DoRA: the file also stores a size for each column. Column sizes of a 64 x 64 weight after the patch
strength   mean column size   wanted size   mean size of the LoRA version
0.0        0.8004             1.2007        0.8004
0.5        1.0002             1.2007        0.8002
1.0        1.2007             1.2007        0.8004
```

Strength 1 gives exactly the stored size. A plain LoRA doesn't manage sizes at all. In DoRA the scale can change the weight even with no up or down change, so strength 0.5 goes halfway between old and new.

One detail, from the code. If `dora_scale`'s first dimension matches the weight's first dimension, the branch rescales using the old weight's norm, along the other axis. Then sizes don't come out exact: we saw that in our test on the real function. The lab shows the column form. Also, DoRA is load-only in core's trainer path: `create_train` passes `None` for it, so `TrainLoraNode` won't make one.

## OFT

OFT doesn't add a low-rank piece. It builds a rotation matrix R from a skew-symmetric block, per group of rows, and applies it to the weight. A rotation keeps sizes, which is the point:

```text
OFT: the change is a rotation of the weight, built from a skew-symmetric block. It keeps the size of each row group
rotation check |R Rt - I|: 2.4e-07   weight size before 16.6791, after 16.6791
```

The OFT abstract says it preserves "hyperspherical energy", the relationship between neurons' directions. That is its aim. Because the change depends on the weight it rotates, the file doesn't work as a fixed thing to add.

## Bypass

There's a second way to apply all of these. `load_bypass_lora_for_models` and the "Load LoRA (Bypass) (For debugging)" nodes leave weights alone, and hook each layer's forward pass: output = g(f(x) + h(x)). `h` is the adapter's change, and `g` is OFT's rotation. A docstring in `comfy/weight_adapter/lora.py` says bypass mode "is designed for quantized models where weights may not be accessible". That's the same trouble CU-212 measures for merges: a small change can't survive rounding into 8 bits. `TrainLoraNode` has a `bypass_mode` too.

## What goes wrong

- **"Rank 8" LoKr has a different size from rank 8 LoRA.** The widget's a factor there. Count numbers, not labels.
- **Alpha seems to do nothing on your LoKr.** Plain `lokr_w1` and `lokr_w2` ignore it. Change the strength.
- **Your DoRA file's strength feels odd.** At strength 0.5 you're also halfway to the stored sizes, not just to the change.
- **A file's keys aren't recognised.** Read the log (CU-280). A LoCon-type file with `lora_mid` loads through the LoRA adapter, whose own comment says it wasn't properly tested.
- **You compare adapters by file size.** They're limited differently. A smaller LoKr may fit worse or better, and only your target decides.
- **Bypass gives a slightly different picture from a merged LoRA.** Merging rounds into the stored format, while bypass doesn't. That's expected (CU-212).

## Lab

The lab writes out each sum. In a side script its `lora`, `loha`, `lokr`, `dora` and `factorization` gave the same results as ComfyUI's real adapters on test tensors, a difference of 0.0, and the real `OFTAdapter` kept the weight's norm. The targets and weights are made up.

## Sources

- [DoRA: Weight-Decomposed Low-Rank Adaptation](https://arxiv.org/abs/2402.09353)
- [FedPara: Low-Rank Hadamard Product for Communication-Efficient Federated Learning](https://arxiv.org/abs/2108.06098)
- [KronA: Parameter Efficient Tuning with Kronecker Adapter](https://arxiv.org/abs/2212.10650)
- [Controlling Text-to-Image Diffusion by Orthogonal Finetuning](https://arxiv.org/abs/2306.07280)
- [One-for-All: Generalized LoRA for Parameter-Efficient Fine-tuning](https://arxiv.org/abs/2306.07967)
- [Navigating Text-To-Image Customization: From LyCORIS Fine-Tuning to Model Evaluation](https://arxiv.org/abs/2309.14859)
- [ComfyUI v0.43.0, comfy/weight_adapter/__init__.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/__init__.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/base.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/lora.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/loha.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/loha.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/lokr.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/lokr.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/oft.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/oft.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/glora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/glora.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/boft.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/boft.py)
- [ComfyUI v0.43.0, comfy/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/lora.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_train.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_train.py)
