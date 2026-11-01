# CU-403 - Model merging: weighted, SLERP, task arithmetic

**Objective.** Write the three common merges as sums, predict the result of ModelMergeSimple's ratio, and explain from the numbers why you merge unquantized files and quantize afterwards. Taught by Tinker Tune.

## The idea

A checkpoint is a long list of numbers. Two checkpoints of the same architecture line up, number for number. So you can do arithmetic on them. The result is one file, and it runs at the cost of one model.

Whether it's any good is a separate matter. It works best when the models are close, such as fine-tunes of one base. The Model Soups paper says fine-tuned models "often appear to lie in a single low error basin", and that averaging them "often improves accuracy and robustness". It's about classifiers. We don't know of a result like it for image checkpoints, so treat that as a reason to try, and not a promise.

## Three sums

With W for all the weights, and base the model two fine-tunes started from:

```
weighted (lerp):   W = (1 − t) · A + t · B
slerp:             W = [ sin((1 − t) θ) · Â + sin(t θ) · B̂ ] / sin θ     Â, B̂ scaled to length 1, θ the angle between them
task arithmetic:   W = base + x · (A − base) + y · (B − base)
```

Lerp walks a straight line between them. Slerp walks an arc, so the result has the same length as its parents. A − base is a task vector in the paper by Ilharco et al., whose abstract says these can be combined "through arithmetic operations such as negation and addition".

Do these differ? Only when the parents are far apart.

```text
weights of the same size at an angle: size of the halfway blend, against the parents' 1.0000
angle (degrees)   lerp     slerp
1                 1.0000   1.0000
10                0.9962   1.0000
45                0.9239   1.0000
90                0.7071   1.0000
135               0.3827   1.0000
```

A lerp at 90 degrees has lost 29% of its length. But fine-tunes of one base are close. Here are two stand-ins, each moved about 10% from a shared base:

```text
our two fine-tunes: angle 8.05 degrees, size of A 20.0959, of B 20.0983
lerp size 20.0474   slerp scaled to the mean size 20.0970   largest difference between them 2.36e-04, against typical weight 0.02
task arithmetic 0.5 and 0.5 against lerp: largest difference 7.5e-09 (the same sum)
```

The angle is 8 degrees. Lerp and slerp differ by at most 0.00024 per weight, on weights of about 0.02. So the choice hardly matters here. And task arithmetic at 0.5 and 0.5 is just lerp, by algebra. What task arithmetic adds is that x and y are free:

```text
task arithmetic 1 and 1 keeps each change whole: share of A's change present 1.002   lerp 0.5 keeps 0.501
```

Lerp halves each change. Adding both at 1 keeps them whole. That's its use: "put B's change on top of A", or negative to take one away.

## In ComfyUI

Core does these with `ModelMergeSimple`, `ModelMergeSubtract`, `ModelMergeAdd`, and `ModelMergeBlocks` for a ratio per block. There are per-family block nodes such as `ModelMergeSDXL`. `CLIPMergeSimple` and friends handle text encoders. `CheckpointSave` writes the result. There's no SLERP node in these files. Nothing happens until sampling or saving: merging adds patches to a clone, as a LoRA does.

{{graph:sd15_merge}}

Now watch the ratio. `ModelMergeSimple` calls `add_patches(..., 1.0 - ratio, ratio)`, and `calculate_weight` multiplies the model by the second number and adds the patch times the first. So:

```text
ModelMergeSimple, model1 = 10, model2 = 2
ratio   result
1.0     10.0
0.7     7.6
0.3     4.4
0.0     2.0
```

**Ratio is model1's share, not model2's.** Its default, 1.0, gives you model1 unchanged. If your merge looks exactly like your first model, this is why.

Task arithmetic in core is subtract and add. `ModelMergeSubtract` gives multiplier × (model1 − model2), and `ModelMergeAdd` adds that on:

{{graph:d_merge_add_difference}}

## The rule: merge unquantized, quantize after

Here's why. A quantized weight isn't the original number: it's the nearest one on a coarse grid (CU-211). Call the rounding error e, with size v per weight.

If you merge in full precision and then quantize, you've rounded once. The final error is about v.

If you quantize the parents and merge those, then the merged value is off grid, and storing it rounds again. For a half-and-half merge the error is (e_A + e_B) / 2 + e_final. If e_final were an ordinary rounding error, that would be √1.5 ≈ 1.22 times v. It isn't. Halfway between two grid values is either on the grid, which costs nothing, or exactly between two neighbours, which costs half a step. On an even grid that makes e_final √1.5 times v by itself, and the total √2 ≈ 1.41 times v. In a side script the parents' errors in this lab were unrelated (correlation 0.006), and the measured factor was 1.38, not 1.22. Parents so close that both round to the same value do better, since their midpoint is already on the grid: at a 1% change in FP8 the factor fell to 1.04. You paid for extra rounding and got nothing for it.

```text
halfway merge of two fine-tunes. Error against the merge done in full precision, as a share of the weights' size
parents stored as   merged, then stored in the same format   merged from those parents, then stored
float32             0.00000                                  0.00000
fp16                0.00021                                  0.00029
bf16                0.00166                                  0.00232
FP8                 0.02644                                  0.03642
```

FP8's error grows by a factor of 1.38. fp16 and bf16 also grow, but their errors start more than ten times smaller, so it hardly matters. That's why the rule says bf16 or fp16 parents, and that's why FP8 parents are the ones to avoid.

It's worse for a difference. The task vector is the small thing you want, and two rounding errors land right on top of it:

```text
the task vector B - base, read from stored parents. The change is 10% of the weight's size here. Error as a share of the change
parents stored as   error / change   share of the change kept   correlation with the true change
float32             0.000            1.000                      1.000
fp16                0.003            1.000                      1.000
bf16                0.024            1.000                      1.000
FP8                 0.372            0.999                      0.937
```

Then make the change smaller, as with a fine-tune that barely touched a weight:

```text
the same difference with a smaller change (what happens to fine-tunes that barely moved a weight), FP8 parents
change / weight   error / change   correlation with the true change
0.1               0.374            0.937
0.03              1.100            0.673
0.01              2.248            0.408
```

At 1% the "change" you read back from FP8 files is more than twice as big in error as it is in signal. This is the size of update that CU-212 found rounding can swallow. Here it's the merge itself that does damage.

And errors build up along a chain:

```text
rounding errors add along a chain of merges. Four parents, FP8. Error as a share of the weights' size
four parents, rounded at every merge          0.04025
four parents, full precision, rounded once    0.02640
```

Find the crossover yourself.

{{play:mergeorder}}

So:

1. Merge from fp32, fp16 or bf16 files.
2. Keep the merged file at that precision.
3. Quantize a copy, once, at the end.

And when you quantize, keep the unquantized one. It's your only source for the next merge. The same goes for merging a LoRA into a checkpoint.

## What goes wrong

- **The merge looks exactly like model1.** Ratio is 1.0, its default. It's model1's share.
- **You've merged FP8 or GGUF files.** The parents' rounding is in there for good. Find the unquantized files, and merge again.
- **Grainy or odd results from add-difference on quantized files.** That's the task vector full of rounding. See the tables.
- **Different architectures.** `add_patches` only patches a key the model has, and a mismatched shape logs "WARNING SHAPE MISMATCH ... WEIGHT NOT MERGED". Nothing is added, but `calculate_weight` has already multiplied model1's weight by the ratio, so that weight isn't left alone: at ratio 0.5 a weight of 10 came out as 5. So you can get a half-merged model with no error. Read the log.
- **You merged only the model, and the prompts stopped matching.** The text encoder comes from whichever CLIP you wired to `CheckpointSave`. Merge it too if the two differ.
- **You've lost the base.** Add-difference needs the same base both fine-tunes started from. With another base, the "change" holds the whole gap between bases.

## Lab

The stand-in weights are Gaussian with standard deviation 0.02. The fine-tunes move each by 10%, FP8 is E4M3 with a scale of largest value / 448, and rounding is to nearest. ComfyUI uses stochastic rounding when it stores FP8 again, and CU-212 shows that keeps the mean at the cost of more noise. Nothing here is a real model. We rewrote this lab: the earlier draft compared lengths on a 10-number vector and then claimed things about pictures it had no way to see.

## Sources

- [Model soups: averaging weights of multiple fine-tuned models improves accuracy without increasing inference time](https://arxiv.org/abs/2203.05482)
- [Editing Models with Task Arithmetic](https://arxiv.org/abs/2212.04089)
- [ComfyUI v0.43.0, comfy_extras/nodes_model_merging.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_model_merging.py)
- [ComfyUI v0.43.0, comfy/lora.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/lora.py)
- [ComfyUI v0.43.0, comfy/model_patcher.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_patcher.py)
- [ComfyUI v0.43.0, comfy/float.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/float.py)
