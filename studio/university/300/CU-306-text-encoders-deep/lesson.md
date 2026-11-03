# CU-306 - Text encoders: CLIP, T5 and LLM encoders

**Objective.** Say what each encoder hands to the diffusion model, how long a prompt it takes, and what a token can see while it is encoded. Taught by Madame Attention.

## Why this matters

The diffusion model never sees your words. It sees a tensor from a text encoder, and it was trained with one particular encoder. So the encoder decides how long your prompt can be, whether brackets mean anything, and how much memory the text costs.

## Who can see whom

All of these are stacks of self-attention (CU-301): each token looks at other tokens and mixes in what it finds. The difference is a mask, which sets which tokens each may look at.

| Encoder | Mask in ComfyUI | So token 3 can see |
|---|---|---|
| CLIP | Causal: `triu` of the scores | Tokens 0 to 3 only |
| T5 | Padding only | Every real token, before and after it |
| Llama-family LLMs | Causal, when encoding a sequence | Tokens 0 to 3 only |

CLIP is often called a bidirectional encoder. In ComfyUI's code it isn't:

```python
causal_mask = torch.full((x.shape[1], x.shape[1]), -torch.finfo(x.dtype).max, ...).triu_(1)
```

The lab shows what that means. Change the last token, and the earlier tokens' CLIP output doesn't move at all, while T5's does.

## What gets handed on

Here is the other thing people get wrong. The model gets a **row for every token**, not a single summary from the last one. A summary vector does exist, for some families, as a second output called pooled.

| Family | Encoders | Tensor | Pooled |
|---|---|---|---|
| SD 1.5 | CLIP-L | `[1, 77, 768]` per chunk | Not used by the model |
| SDXL | CLIP-L + CLIP-G, side by side | `[1, 77, 2048]` per chunk | CLIP-G's |
| SD3 | CLIP-L, CLIP-G, T5 | `[1, 154, 4096]` at the shortest | Both CLIPs' |
| FLUX.1 | T5, with CLIP-L for its pooled only | `[1, 256, 4096]` at the shortest | CLIP-L's |
| FLUX.2 Klein 4B | Qwen3, three layers side by side | `[1, 512, 7680]` at the shortest | Not used by the model, as we read it |

The pooled vector in CLIP is the row at the end token, `x[..., eos_index]`. In a causal model, that row has seen the whole prompt, which is a good reason to use it as a summary. SD3 and FLUX.1 use the text encoders' output in two ways at once, then: rows for attention, plus one vector for the model's global input.

Which layer also matters. SD 1.5 uses the last layer by default, and SDXL takes the second to last. Klein reads layers 9, 18 and 27 of its Qwen3, and stacks them side by side, which is why the width is 3 × 2560. It also wraps your text in a chat template before encoding.

## Prompt length

CLIP has 77 positions, because its position table has 77 rows. So `tokenize_with_weights` cuts long prompts into chunks: start token, 75 of yours, end token. Each chunk is encoded alone, then the rows are joined. A word in chunk 2 can't see a word in chunk 1 while being encoded.

T5 and Qwen3 use `max_length=99999999` with a minimum, so a long prompt stays one sequence. T5 on Flux is padded to at least 256, and Qwen3 on Klein to at least 512.

{{play:chunks}}

## Three real graphs

SD 1.5, where `CheckpointLoaderSimple` hands you the one CLIP:

{{graph:sd15_txt2img}}

SD 3.5, with three encoders:

{{graph:sd35_flow}}

Klein, with one LLM encoder through `CLIPLoader`:

{{graph:c_klein_fast}}

![Another LLM encoder: Lumina 2 with plain Gemma 2 2B reading the prompt, a weathered brass lighthouse on a rocky coast at golden hour. 1024 x 1024, 30 steps, cfg 4. Recorded peak 12.3 GiB. One render.](families/lumina-2_4.webp)

## What goes wrong

- **A word past token 75 seems ignored on SD 1.5.** It went into a new chunk, and it can't see the words of the first one while encoded. Move it earlier, or shorten the prompt.
- **`clip skip` copied from another family.** Each family already picks its own layer. Check before changing it. SDXL's choice is the second to last by default.
- **Weights on an LLM encoder.** Many of these turn weights off (CU-261).
- **An out-of-memory error at the text stage.** T5-XXL has 24 layers at width 4096 with 64 heads, far bigger than CLIP-L's 12 at 768. This is separate from the diffusion model's memory (CU-305).
- **Mixing up encoders.** Each family's tokenizer and encoder are a pair. `CLIPLoader`'s `type` input picks how the file is read, so set it to match.
- **Assuming the last token is what the model uses.** It uses every row. Only the pooled vector comes from one row, and only on families that use it.

## Lab

The first part is an experiment on the mask, using random weights. It changes only the last of 6 tokens.

```text
change only the last of 6 tokens. How far does each token's output move?
token   with CLIP's causal mask   with no mask, as in T5
0       0.0000                    0.1054
1       0.0000                    3.7270
2       0.0000                    5.1937
3       0.0000                    4.7433
4       0.0000                    5.3531
5       12.7101                   12.7101
```

Where the pooled vector comes from: the end token, the first place its id appears.

```text
tokens [49406, 320, 1125, 49407, 49407, 49407] -> row 3
```

The chunking rule, for single-token words. Real words can use several tokens.

```text
tokens in the prompt    chunks   tensor for SD 1.5   tensor for SDXL
1                       1        [1, 77, 768]        [1, 77, 2048]
75                      1        [1, 77, 768]        [1, 77, 2048]
76                      2        [1, 154, 768]       [1, 154, 2048]
150                     2        [1, 154, 768]       [1, 154, 2048]
151                     3        [1, 231, 768]       [1, 231, 2048]
```

And the joins each family does, with the shapes from the source.

```text
SDXL        CLIP-L and CLIP-G side by side    [1, 77, 2048]
SD3         padded to 4096, T5 on the end     [1, 154, 4096]
FLUX.1      T5 tokens, CLIP-L's pooled vector [1, 256, 4096] and [1, 768]
Klein 4B    three hidden layers side by side  [1, 512, 7680]
```

## Sources

- [Radford et al. 2021. Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020)
- [Raffel et al. 2019. Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer](https://arxiv.org/abs/1910.10683)
- [ComfyUI v0.43.0, comfy/clip_model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/clip_model.py)
- [ComfyUI v0.43.0, comfy/sd1_clip.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd1_clip.py)
- [ComfyUI v0.43.0, comfy/sd1_clip_config.json](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd1_clip_config.json)
- [ComfyUI v0.43.0, comfy/sdxl_clip.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sdxl_clip.py)
- [ComfyUI v0.43.0, comfy/text_encoders/sd3_clip.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/sd3_clip.py)
- [ComfyUI v0.43.0, comfy/text_encoders/flux.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/flux.py)
- [ComfyUI v0.43.0, comfy/text_encoders/t5.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/t5.py)
- [ComfyUI v0.43.0, comfy/text_encoders/t5_config_xxl.json](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/t5_config_xxl.json)
- [ComfyUI v0.43.0, comfy/text_encoders/llama.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/llama.py)
