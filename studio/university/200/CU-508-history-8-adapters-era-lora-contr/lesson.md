# CU-508 - History 8: Adapters era: LoRA and ControlNet

**Objective.** Say what LoRA and ControlNet each train and what they freeze, check with numbers what a rank buys and what it cannot, see how both methods start as the base model and begin to learn, and find the matching code in ComfyUI. Taught by Tinker Tune.

## The idea

Full fine-tuning retrains every weight. Two papers, almost twenty months apart, froze the big model and trained something small beside it.

Hu et al. posted "LoRA: Low-Rank Adaptation of Large Language Models" on 17 June 2021. LoRA "freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture". Against GPT-3 175B fine-tuned with Adam, they report that it "can reduce the number of trainable parameters by 10,000 times and the GPU memory requirement by 3 times", with "no additional inference latency". Their hypothesis, taken from work on the intrinsic dimension of models, is that the change in weights during adaptation has a low "intrinsic rank". The paper is about language models. ComfyUI applies the same arithmetic to image and video models.

Zhang, Rao and Agrawala posted "Adding Conditional Control to Text-to-Image Diffusion Models" on 10 February 2023. ControlNet "locks the production-ready large diffusion models" and trains a copy of their encoding layers on a spatial condition such as edges, depth or pose, joined to the original by "zero convolutions". They show training to be "robust with small (<50k) and large (>1m) datasets". Their text names T2I-Adapter, which learns "simple and lightweight" adapters "while freezing the original large T2I models", as concurrent work.

## The maths

LoRA, for a frozen weight W0 of size d×k (section 4.1 of the paper):

```
h = W0 x + ΔW x = W0 x + (α/r) · B A x        B is d×r, A is r×k, r ≪ min(d, k)
```

The paper starts A "random Gaussian" and B at zero, "so ΔW = BA is zero at the beginning of training". It trains r(d+k) numbers in place of dk, and a finished LoRA can be merged, W = W0 + (α/r) BA, so there is no extra cost at inference.

ControlNet, for one block y = F(x; Θ) of the original network (eq. 2). The block is locked and cloned to a trainable copy Θc, and two zero convolutions Z, which are 1×1 convolutions with weight and bias "initialized to zeros", connect them:

```
y_c = F(x; Θ) + Z( F( x + Z(c; Θ_z1); Θ_c ); Θ_z2 )
```

At the first training step both Z terms are zero, so y_c = y (eq. 3), and "harmful noise cannot influence the hidden states of the neural network layers in the trainable copy when the training starts". For Stable Diffusion the paper copies "the 12 encoding blocks and 1 middle block", adds the outputs "to the 12 skip-connections and 1 middle block of the U-net", and encodes the 512×512 condition to 64×64 with a tiny network of four convolution layers. It measured "about 23% more GPU memory and 34% more time in each training iteration" on an A100 40GB.

## In ComfyUI

- **LoRA.** `LoRAAdapter.calculate_weight` in `comfy/weight_adapter/lora.py` takes `alpha = v[2] / mat2.shape[0]`, which is α/r, and computes `weight += (strength * alpha) * lora_diff` with `lora_diff = mm(mat1, mat2)`. That is the paper's formula times the strength you set. If the file has no alpha entry, the scale is 1.0 and not 1/r. For training, `create_train` makes `mat1` (out × rank) Kaiming-uniform and `mat2` (rank × in) zeros, so the product still starts at zero, with the two factors' roles swapped relative to the paper.
- **Merge or side path.** `comfy/weight_adapter/bypass.py` describes bypass mode as `bypass(f)(x) = g(f(x) + h(x))`, which "applies adapters during forward pass without modifying base weights".
- **ControlNet.** `ControlNet` in `comfy/cldm/cldm.py` has an `input_hint_block`, the tiny condition encoder, a list `zero_convs` and a `middle_block_out`, each a 1×1 convolution made by `make_zero_conv`. Its forward returns `{"middle": ..., "output": ...}`. In `openaimodel.py`, `apply_control` does `h += ctrl` on the middle block and on the skip connections. `control_merge` in `comfy/controlnet.py` multiplies by the strength and adds a previous ControlNet's output, so ControlNets stack by addition. `make_zero_conv` is a plain convolution there. The weights come from the file, and zero is an initial value for training.
- **T2I-Adapter.** `Adapter` and `Adapter_light` are in `comfy/t2i_adapter/adapter.py`.

What a rank buys, on a real picture instead of a weight change. The bet is the same.

{{play:lowrank}}

And both ideas on a graph. The first patches weights, and the second adds to the skip connections.

{{graph:sd15_lora}}

{{graph:sd15_controlnet}}

## What goes wrong

- **The LoRA does nothing, or only half of it works.** Everything after the loader must use the loader's outputs. Wiring the original CLIP past it is the commonest mistake. The note on the `sd15_lora` graph marks it.
- **The console says `lora key not loaded`.** The file does not match this model, usually a different family. `comfy/lora.py` logs each key it can't place. Pick a LoRA made for your base.
- **Same strength, very different effect.** With no alpha in the file, ComfyUI scales by 1.0, not 1/r. Two LoRAs at strength 1 are not comparable. Go by eye, in small steps.
- **ControlNet ignores your picture.** Check the map first. The note on `sd15_controlnet` says it: preview the edges before you trust them. Then check strength, and whether `end_percent` stops it early.
- **Two ControlNets are too strong.** `control_merge` adds outputs together, so their strengths add up too. Lower each.
- **You copy a rank number from somewhere.** The lab shows that rank is as good as the change is low-rank. The paper's "rank one" result is about its language datasets.

## Lab

First the arithmetic. A LoRA replaces the update of a d×d layer, d² numbers, by 2dr:

```text
layer 1280 x 1280: full update has 1,638,400 numbers
rank r   LoRA numbers   share of the full update   reduction
1        2,560          0.0016                     640x
4        10,240         0.0063                     160x
16       40,960         0.0250                     40x
64       163,840        0.1000                     10x
```

Next, how well can rank r follow a change? For inputs of unit variance the squared error of BA against the wanted change `ΔW*` is proportional to `|BA − ΔW*|²`, so training a LoRA is a rank-r approximation of `ΔW*`. The best possible rank-r matrix is the truncated SVD, whose error is the part of the singular values of `ΔW*` beyond r (the Eckart–Young–Mirsky theorem). The lab trains B and A with Adam from the paper's start and compares.

```text
relative error |BA - DW*| / |DW*| of a trained LoRA, against the best rank-r matrix
change DW*                  r=1              r=2              r=4              r=8              r=16           
rank 4 (4, 3, 2, 1)         0.6831 / 0.6831  0.4082 / 0.4082  0.0000 / 0.0000  0.0000 / 0.0000  0.0000 / 0.0000
decaying (2 x 0.75^i)       0.7500 / 0.7500  0.5625 / 0.5625  0.3164 / 0.3164  0.1001 / 0.1001  0.0100 / 0.0100
(each cell: trained / best possible)
```

A change of rank 4 is followed exactly from r = 4 up, and r = 1 or 2 leave 0.6831 and 0.4082. A change with a long tail of singular values never is: r = 2 leaves 0.5625, r = 8 leaves 0.1001 and r = 16 still leaves 0.0100. In every cell the trained LoRA matches the best possible matrix to four decimals. A LoRA is as good as the change is low-rank, and no better.

Now the zero start. For LoRA with B = 0:

```text
LoRA at step 0: largest difference from the base layer 0.0
step   |grad A|   |grad B|
0      0.0000    0.1637
1      0.0023    0.1631
2      0.0046    0.1626
```

The adapted layer equals the base layer exactly at step 0. The gradient with respect to A is exactly zero then, because B is zero, while B's is not. After one step both move. ControlNet is the same story one level up, with a large random condition of standard deviation 10:

```text
ControlNet at step 0: largest difference from the locked block 0.0, with a condition of standard deviation 10
step   |grad Z2|   |grad copy|   |grad Z1|
0      0.1267      0.0000       0.0000
1      0.1252      0.0003       0.0022
2      0.1237      0.0006       0.0043
```

The output equals the locked block's exactly, the zero convolution Z2 gets a gradient straight away, and the trainable copy and Z1 get theirs only once Z2 has left zero, a step later. The paper's Figure 4 describes something at a larger scale: ControlNet "always predicts high-quality images during the entire training", and at a certain step "the model suddenly learns to follow the input condition".

Last, the two ways to apply a LoRA, merged into the weights or kept as a side path. They compute the same function, and for the 1280×1280 layer of the first table the side path costs a little more per token:

```text
merged against side path, float32: largest difference 4.3e-06 on outputs of size 8
extra multiply-adds per token for the side path, rank 16: 40,960 on top of 1,638,400, which is 2.5%
```

## What is contested

Low rank is a hypothesis about the change, not a law. The LoRA paper says "we do not expect a small r to work for every task or dataset", and gives the thought experiment of a downstream task in a different language from the pre-training one, where retraining the whole model "could certainly outperform LoRA with a small r". The lab shows the mechanism: what a rank cannot follow is lost.

The paper's Table 6 reports that "a rank as small as one suffices for adapting both Wq and Wv" on its two language datasets, "while training Wq alone needs a larger r". That is a result on those datasets. Nothing in the paper gives a default rank for image models, so do not carry one over from folklore.

Which is better, ControlNet or T2I-Adapter, or a LoRA for the same job, is not something a lab on matrices can settle.

## Sources

- [Hu et al. 2021. LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [Zhang, Rao, Agrawala 2023. Adding Conditional Control to Text-to-Image Diffusion Models](https://arxiv.org/abs/2302.05543)
- [Mou et al. 2023. T2I-Adapter: Learning Adapters to Dig out More Controllable Ability for Text-to-Image Diffusion Models](https://arxiv.org/abs/2302.08453)
- [Low-rank approximation, Wikipedia: the Eckart–Young–Mirsky theorem](https://en.wikipedia.org/wiki/Low-rank_approximation)
- [ComfyUI v0.43.0, comfy/weight_adapter/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/lora.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/bypass.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/bypass.py)
- [ComfyUI v0.43.0, comfy/cldm/cldm.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cldm/cldm.py)
- [ComfyUI v0.43.0, comfy/controlnet.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/controlnet.py)
- [ComfyUI v0.43.0, comfy/ldm/modules/diffusionmodules/openaimodel.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/diffusionmodules/openaimodel.py)
- [ComfyUI v0.43.0, comfy/t2i_adapter/adapter.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/t2i_adapter/adapter.py)
