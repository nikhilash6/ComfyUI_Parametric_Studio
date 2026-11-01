# CU-212 - LoRA: low-rank adaptation

**Objective.** Write the LoRA update, count its parameters, show that merging it into a weight equals adding it to the layer's output, and read how ComfyUI loads, scales and applies one, including what happens when the base weights are stored in 8 bits. Taught by Tinker Tune.

## The idea

Fine-tuning turns a weight W0 into W0 + ΔW. LoRA (Hu et al. 2021) freezes W0 and forces ΔW to be a product of two thin matrices, so that only the thin ones are trained and stored. The paper's bet is that the update needed to adapt a pretrained model has a low "intrinsic rank". If that holds, a few columns are enough.

## The maths

For a weight W0 of size d × k, with B of size d × r, A of size r × k and a rank r far below min(d, k), the paper's forward pass (its eq. 3, with the scale from the same section) is:

```
h = W0 x + ΔW x = W0 x + (α/r) · B (A x)
parameters: r · (d + k)   instead of   d · k
```

B is set to zero and A to random Gaussian numbers, so ΔW = BA is zero at the start and the model begins unchanged. The scale α/r exists so that changing r does not force a new search over hyperparameters. The paper says that with Adam, tuning α is roughly the same as tuning the learning rate if the initialisation is scaled appropriately.

Two facts follow from the algebra. First, BA has rank at most r, however large the layer is. Second, (W0 + sBA) x = W0 x + s B (A x), so the update can be merged into the weight or computed beside the layer, and the output is the same. The paper uses the first form for inference: store W = W0 + BA, and subtract BA again to switch to another adapter.

How much can rank r hold? The best rank-r approximation of a matrix, in the least-squares sense, is its truncated SVD, the result of Eckart and Young (1936). The lab uses it as a yardstick.

Here is what a low rank can hold, in a picture you can drag. It's the same bet.

{{play:lowrank}}

## In ComfyUI

**The file.** A LoRA is a set of tensors named per layer: `<layer>.lora_up.weight` is B with shape [out, r], `<layer>.lora_down.weight` is A with shape [r, in], and an optional `<layer>.alpha`. `LoRAAdapter.load` in `comfy/weight_adapter/lora.py` also accepts other spellings, such as `lora_B` and `lora_A`. The same folder holds other adapter types (LoHa, LoKr, OFT and more) that this lesson does not cover.

**The loader.** `LoraLoader` in `nodes.py` has `strength_model` and `strength_clip`, both defaulting to 1.0, and its tooltips say the value can be negative. It calls `load_lora_for_models` in `comfy/sd.py`, which clones the model, and `add_patches` in `comfy/model_patcher.py` appends the adapter to a list kept for each weight. Chaining loaders appends more entries to the list.

**The formula.** `LoRAAdapter.calculate_weight` computes:

```
scale = alpha / rank      (1.0 when the file has no alpha, whatever the rank)
weight += strength · scale · (up @ down)
```

The product is computed in float32 and added to a copy of the weight held in a working dtype that is float16 on devices where ComfyUI uses fp16 and float32 otherwise (`lora_compute_dtype`). The result is then stored in the weight's own dtype.

**Merged or beside the layer.** That depends on which patcher loads the model. With dynamic VRAM, which `main.py` turns on by default where it's supported unless a flag such as `--disable-dynamic-vram` or `--highvram` rules it out, `ModelPatcherDynamic.load` gives a patched weight a `LowVramPatch`, so the patch is applied on every forward pass and isn't merged. The exceptions are modules of 16 KB or less and a LoRA that resizes a weight, which are force-loaded through `patch_weight_to_device`. With the older `ModelPatcher.load`, it's decided per module. A module that fits in the VRAM budget is loaded completely and `patch_weight_to_device` merges the patch into its weight, keeping a backup of the original on the offload device. A module that does not fit gets a `LowVramPatch`, which applies the patch on every forward pass, and the log counts them as "lowvram patches". A third path is a separate, experimental node, "Load LoRA (Bypass) (For debugging)" in `comfy_extras/nodes_lora_debug.py`. It leaves the weights alone and computes `output = base_forward(x) + lora_path(x)`, and its description calls it useful for training scenarios. The ordinary loader does not use it.

**Quantized base weights.** The merge path dequantizes, adds the patch, and stores again. For plain bf16 or fp16 weights that last step is a normal cast. For FP8, `comfy/float.py` uses stochastic rounding, seeded by a CRC-32 of the weight's key so that the same merge gives the same result every time, and for FP8 weights with a stored scale `set_weight` in `comfy/ops.py` recalculates the scale first (CU-211). A layer that gets its patch at run time through `LowVramPatch` is dequantized and patched in the compute dtype instead, so the lab's last table is about the merge path and not about that layer.

**Training.** "Train LoRA" in `comfy_extras/nodes_train.py` is marked experimental. Its defaults are rank 8, 16 steps, learning rate 0.0005, AdamW and an MSE loss. A new adapter gets alpha 1.0, so its scale is 1/rank.

Here's a LoRA in a graph, and CU-280 goes through loading it right.

{{graph:sd15_lora}}

## Lab

The first block counts parameters for three layer shapes. At rank 128 on a 320 × 320 layer the LoRA is 80% of the layer, so most of the saving is gone. It disappears once r · (d + k) reaches d · k.

```text
layer (out x in)   rank   full weights   LoRA weights   LoRA / full
320 x 320          128    102,400        81,920         0.8000
4096 x 4096         4      16,777,216     32,768         0.0020
4096 x 4096         16     16,777,216     131,072        0.0078
4096 x 4096         128    16,777,216     1,048,576      0.0625
```

Then the algebra, with random matrices, tested in two precisions. A 256 × 256 product of 256 × 8 and 8 × 256 matrices has exactly 8 nonzero singular values, and merged and beside-the-layer outputs agree to rounding:

```text
B (256x8) times A (8x256) is a 256x256 matrix; singular values above 1e-10 of the largest: 8
torch.float32  strength 0.5, 1, 2: 8.3e-07 8.3e-07 9.5e-07   doubling the strength doubles the change: 4.8e-07   two LoRAs in either order: 1.5e-08
torch.float64  strength 0.5, 1, 2: 1.8e-15 1.6e-15 2.2e-15   doubling the strength doubles the change: 6.7e-16   two LoRAs in either order: 2.8e-17
scale alpha/r: alpha 8, r 8 -> 1.0   alpha 1, r 8 -> 0.125   file with no alpha -> 1.0 whatever the rank
```

The differences fall from around 1e-06 in float32 to around 1e-15 in float64, so they are rounding, not a different calculation. Strength is linear, and stacking is order-free.

Initialisation. Both starts give ΔW = 0, but at step 0 only the factor that is zero gets a gradient, because the other factor's gradient passes through that zero. If G is the gradient of the loss with respect to ΔW, the gradient for A is BᵀG and the gradient for B is GAᵀ. ComfyUI's trainer (`create_train`) sets the factors up the other way round from the paper, with the up matrix random and the down matrix zero, and in this lab both starts end at the same error:

```text
init                    |B A| at start   |grad up|   |grad down|   relative error after 300 Adam steps
B = 0, A Gaussian       0.0000           0.0648     0.0000       0.8391
up random, down = 0     0.0000           0.0000     0.1170       0.8390
```

What rank can hold. Gradient descent fits B A to a target update T. The "best possible" columns are the truncated SVD:

```text
relative error |B A - T| / |T| for a 96 x 64 update T
rank   T = rank 4 + noise: trained   best possible     T = full rank: trained   best possible
1      0.8179                      0.8179            0.9735                  0.9735
2      0.6190                      0.6190            0.9483                  0.9483
4      0.0192                      0.0192            0.9027                  0.9027
8      0.0175                      0.0174            0.8168                  0.8168
16     0.0143                      0.0141            0.6648                  0.6648
32     0.0087                      0.0085            0.4058                  0.4058
```

Training reaches the best possible error to within 0.0003 at every rank, so the SVD is a fair yardstick. When the update really has rank 4, the error falls from 0.6190 at rank 2 to 0.0192 at rank 4 and then only slowly, because what remains is the noise we added. A random full-rank update is not compressible: rank 32 of a possible 64 still leaves a residual of 0.4058 of its norm. LoRA works when the update is compressible, and this lab builds a compressible one on purpose.

Last, merging into base weights that are stored in a low-precision format and stored again. The weights have standard deviation 0.02 and the update B A is scaled to the standard deviation in the first column. `share kept` is how much of the intended update is found in the stored weights on average.

```text
update std   stored as   rounding     share of the update kept   RMS error / update RMS   output correlation
1e-05        bf16        nearest      0.306                      0.89                     0.497
0.0001       fp16        nearest      1.000                      0.04                     0.999
0.0001       bf16        nearest      0.987                      0.32                     0.953
0.0001       FP8         nearest      0.200                      1.00                     0.325
0.0001       FP8         stochastic   1.005                      3.36                     0.293
0.001        FP8         nearest      0.937                      0.46                     0.901
0.001        FP8         stochastic   1.000                      0.69                     0.827
```

```text
FP8, rounding to nearest: share of weights whose 8-bit code is unchanged by the merge, for update std 1e-05, 0.0001, 0.001: 0.993 0.928 0.476
```

With an update 0.5% the size of the weights (std 0.0001), rounding FP8 to nearest keeps 0.200 of the update, because 0.928 of the weights get back the same 8-bit code they had. Stochastic rounding keeps the mean (1.005), at the price of noise 3.36 times as large as the update. At 5% the roles blur: nearest is closer (output correlation 0.901 against 0.827). Even bf16 keeps only 0.306 of a very small update. So stochastic rounding trades a bias for noise and does not make the merge exact.

## What goes wrong

- **The prompt's CLIP goes round the loader.** Your text-encoder patch never reaches it. See CU-280.
- **A high rank, and a big file with little gain.** The lab's table shows where the saving goes. Rank 128 on a 320 × 320 layer is 80% of the layer.
- **A file with no alpha is much stronger than you expect.** Scale is 1.0 with no alpha, whatever the rank.
- **A small LoRA vanishes when merged into FP8.** The last table shows 0.2 of an update kept, by rounding to nearest. Merge into bf16 or fp16, and quantize afterwards (CU-403).
- **Keys didn't load.** Read the log. CU-280 shows each line.

## What is contested

The low intrinsic rank of adaptation updates is the paper's hypothesis, tested there on language models. This lab does not test it for diffusion models: the low-rank target is made by hand. How rank and α should be chosen is empirical, and the paper's settings (r = 4 on the query and value matrices of GPT-3 175B, where it reports a 35 MB checkpoint instead of 350 GB) belong to that model. We do not know how large the updates of real image LoRAs are against their weights, which is why the last table sweeps three sizes. And we make no claim about which rounding looks better in a picture.

## Sources

- [Hu et al. 2021. LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [Eckart, Young 1936. The Approximation of One Matrix by Another of Lower Rank](https://doi.org/10.1007/BF02288367)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/lora.py)
- [ComfyUI v0.43.0, comfy/weight_adapter/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/weight_adapter/lora.py)
- [ComfyUI v0.43.0, comfy/model_patcher.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_patcher.py)
- [ComfyUI v0.43.0, comfy/float.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/float.py)
- [ComfyUI v0.43.0, comfy/ops.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ops.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_lora_debug.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_lora_debug.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_train.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_train.py)
