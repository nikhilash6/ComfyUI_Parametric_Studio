# CU-261 - Prompt weights: what the brackets really do

**Objective.** Predict the weight any bracketed prompt produces, say what a weight does to the numbers, and tell when weights are ignored. Taught by Madame Attention.

## The idea

You type `(brass:1.3)` and expect brass to count for more. Two things happen in order. A parser reads your text and gives each piece a weight. Then the encoder changes the weighted tokens' rows, after it has run.

## The parser

`token_weights` in `comfy/sd1_clip.py` follows two rules.

- Each pair of brackets without a number multiplies the current weight by 1.1.
- A number replaces the weight outright. It does not multiply with the brackets around it.

So `((brass))` is 1.21, `((brass:1.3))` is 1.3, and in `((a (b:1.5) c))`, a and c are 1.21 while b is 1.5. If what follows the colon isn't a number, the text stays as it is, with weight 1.1 from the brackets.

To type a real bracket, write `\(` and `\)`. The tokenizer hides those before parsing and restores them after.

{{play:weights}}

## What a weight does

Here is the line, from `encode_token_weights`:

```python
z[i][j] = (z[i][j] - z_empty[j]) * weight + z_empty[j]
```

`z_empty` is the empty prompt encoded with the same length. So a weight doesn't scale the token's row. It takes the arrow from the empty prompt's row to this token's row, and scales that. Three settings show it:

- Weight 1 leaves the row where it was. If no token is weighted, the empty prompt isn't even encoded.
- Weight 0 lands on the empty prompt's row at that position. The token is not removed, and the tensor keeps its length.
- Weight 1.5 goes half as far again, past the token, in the same direction.

The encoder runs first, so every other token already saw this word at its normal strength. The weight only changes this word's own row, as the sampler sees it. The pooled vector comes from the same unweighted pass, so weights leave it alone.

## Some encoders ignore all this

A tokenizer can pass `disable_weights=True`, and then your whole prompt counts as one piece at weight 1. `KleinTokenizer` does this for FLUX.2 Klein, and so does the tokenizer for Qwen Image. On those, brackets are just characters in your prompt. The model reads them as text.

So look before you tune. On our list, Klein's brackets carry no weight at all.

{{graph:c_weights}}

## What goes wrong

- **`((word:1.3))` doesn't reach 1.57.** A number replaces the weight. It stays 1.3.
- **Weights on a Klein or Qwen Image graph do nothing, or the brackets seem to end up in the picture's meaning.** Weights are off there, so the characters are passed on as text.
- **"Weight 0 removes the word."** It doesn't. The token is still there, on the empty prompt's row, and it has already influenced its neighbours in the encoder.
- **A very high weight breaks the picture.** The row goes far beyond its real range: at 3 the lab's row is three times as far from the empty row. Cfg then amplifies the result again. Stay modest.
- **Literal brackets in a title you wanted kept.** Escape them with a backslash.
- **`(word:high)`.** Not a number, so the text `word:high` is encoded at 1.1.

## Lab

The parser is a port of the real one, and it matched on seven test strings. Check each row by hand against the rules.

```text
what you type                     what the parser hands on
a (brass) b                       'a ' 1.0  'brass' 1.1  ' b' 1.0
a ((brass)) b                     'a ' 1.0  'brass' 1.21  ' b' 1.0
a (brass:1.3) b                   'a ' 1.0  'brass' 1.3  ' b' 1.0
a ((brass:1.3)) b                 'a ' 1.0  'brass' 1.3  ' b' 1.0
((a (b:1.5) c))                   'a ' 1.21  'b' 1.5  ' c' 1.21
(brass:high)                      'brass:high' 1.1
(a) (b:0)                         'a' 1.1  ' ' 1.0  'b' 0.0
```

Now the weighting line, on random rows. Read the second and third columns: they change by the same amount in step, because the row moves along one straight line through both points.

```text
weight   distance from this token's row   distance from the empty prompt's row   length
0.0      3.661                            0.000                                  1.042
0.5      1.830                            1.830                                  1.784
1.0      0.000                            3.661                                  3.462
1.21     0.769                            4.430                                  4.204
1.5      1.830                            5.491                                  5.243
3.0      7.322                            10.983                                 10.686
```

## Sources

- [ComfyUI v0.43.0, comfy/sd1_clip.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd1_clip.py)
- [ComfyUI v0.43.0, comfy/text_encoders/flux.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/flux.py)
- [ComfyUI v0.43.0, comfy/text_encoders/qwen_image.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/qwen_image.py)
