# CU-262 - Combine, Concat and Average

**Objective.** Pick the right node for using two prompts, by saying what each one does to the list, the tensor and the cost. Taught by Madame Attention.

## The idea

All three take two prompts and return one wire. They do very different work.

- **Combine** keeps two prompts. The model answers each one, and the answers get blended. It's two opinions.
- **Concat** makes one long prompt. The model answers once, attending to all the tokens. It's one long sentence.
- **Average** melts two prompts into one, number by number, before the model runs. It's one blurred sentence.

{{play:condlist}}

## Reading the source

`ConditioningCombine.combine` is one line: list plus list. Nothing happens to the numbers until the sampler. At each step `_calc_cond_batch` runs each entry and adds up the answers:

```python
out_conds[cond_index] += output[o] * mult[o]
out_counts[cond_index] += mult[o]
# ...then, at the end
out_conds[i] /= out_counts[i]
```

So with equal strengths, it's the mean of two predictions. That costs one more prediction per step for each extra entry.

{{graph:sd15_cond_combine}}

`ConditioningConcat.concat` joins along the token dimension: `torch.cat((t1, cond_from), 1)`. Two 77-token prompts become one 154-token prompt, in one prediction. It keeps the dict of `conditioning_to`, so the pooled vector comes from there, and the second prompt has no say in it.

{{graph:sd15_cond_concat}}

`ConditioningAverage.addWeighted` blends values:

```python
tw = t1 * conditioning_to_strength + t0 * (1.0 - conditioning_to_strength)
```

The pooled vectors are blended the same way. Tensors must line up, so `from` is cut to the length of `to`, or padded with zeros. Token 5 of one prompt gets mixed with token 5 of the other, whatever those words are. That's why two unrelated sentences give an odd result: word order lines up by position, not by meaning.

{{graph:sd15_cond_average}}

## Which to use

| You want | Use | Why |
|---|---|---|
| Two things in the frame, fighting less | Concat | One attention over all tokens |
| A style between two prompts | Average | Blends before the model runs |
| Two separate regions | Combine with areas | See CU-263 |
| Prompts at different times | Combine with ranges | See CU-264 |

Combine's real job is holding several entries with areas or ranges. Without those, it blends answers across the whole picture, at double the prompt cost.

These are starting points from how each node works. We have no side-by-side renders, so try them on your own seed.

## What goes wrong

- **"Combine is slow."** Each entry costs one more prediction per step. Three prompts and a negative is four predictions.
- **"Average ignored my second prompt's later words."** If `from` is longer, the extra tokens are cut. The lab shows it.
- **Average padded with zeros.** If `from` is shorter, its missing tokens are filled with zeros, and those positions get pulled towards zero.
- **"The second prompt lost its pooled vector."** Concat keeps the first prompt's only. On SDXL, where the pooled vector goes in to the model, that's a real difference.
- **Feeding a Combined conditioning as `from`.** Concat and Average use only its first entry and log a warning. The rest is dropped.
- **Strength the wrong way round.** `conditioning_to_strength` at 1 gives `to` unchanged, and at 0 gives `from`.

## Lab

A tiny cross-attention with random numbers stands in for the model, so the answer depends on its inputs in a nonlinear way. That nonlinearity is the point.

```text
node       entries  tensor           predictions for the positive, per step
Combine    2        [1, 77, 16]      2
Concat     1        [1, 154, 16]     1
Average    1        [1, 77, 16]      1
```

Now compare the answers. If the model were linear, Average and Combine would match. It isn't, so they don't.

```text
Combine against (answer A + answer B) / 2: 0.0000
Average against Combine:                   7.095
Concat against Combine:                    5.572
Concat against Average:                    9.852
```

The first line is the check that Combine really is the mean of the two answers. The other three say that these are three different methods. Their sizes mean nothing on a real model.

```text
Average, 'from' longer than 'to':  result has 77 tokens, the extra ones are cut
Average, 'from' shorter than 'to': result has 77 tokens, the gap is filled with zeros
Concat keeps the pooled vector of 'to' only: True
Average at strength 1 is 'to' unchanged: True
```

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
