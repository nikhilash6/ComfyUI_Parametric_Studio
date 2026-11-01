# CU-265 - Reference images: CLIP vision, unCLIP and style models

**Objective.** Say which core node uses a picture how, where its numbers go in the model, and which model each one needs. Taught by Madame Attention.

## The idea

A prompt becomes numbers through a text encoder. A picture can too, through an image encoder. The question is where to put them. Core has two doors.

- **A style model** turns the picture into extra tokens on the end of the prompt.
- **unCLIP** uses the picture's single summary vector. The tensor doesn't change.

Both begin at the same node, `CLIPVisionEncode`. It doesn't generate anything. It just describes a picture in numbers.

{{play:condref}}

## CLIPVisionEncode

Its `crop` input has two settings. `center` crops to the square the vision model expects, and `none` skips that crop. It returns an output object with fields including these two:

- `image_embeds`: one vector summing up the picture. unCLIP uses this.
- `last_hidden_state`: one row per patch of the picture. Style models use this.

## Door one: style models

`StyleModelApply` does what `ConditioningConcat` does, with a picture:

```python
cond = style_model.get_cond(clip_vision_output)...
c_out.append([torch.cat((txt, cond), dim=1), keys])
```

So the text's rows aren't touched, and the model attends to the picture's rows just as it does to words. `load_style_model` picks one of two architectures by reading the file's keys.

- `style_embedding` means `StyleAdapter`, which makes 8 tokens of width 768.
- `redux_down.weight` means `ReduxImageEncoder`, which maps each vision token from 1152 numbers to 4096, the width FLUX.1's T5 tokens have.

The strength input has two kinds. `multiply` scales the picture's rows, and at 0 the zero rows are still there. `attn_bias` leaves the rows alone and edits an attention mask.

{{graph:c_style_redux}}

Our gallery has a real one. The data says it used core's `StyleModelApply`, with the style reference joining the prompt as extra image tokens, on FLUX.1 schnell at cfg 1 with a pack's sampler.

![Redux on FLUX.1 schnell: a style reference joined to the prompt as extra tokens, using core's StyleModelApply and a pack's sampler. One seed.](res4lyf_renders/flux_redux.jpg)

## Door two: unCLIP

`unCLIPConditioning` adds an entry to a list in the dict, with the vision output, a strength and a noise amount. It's a list, so several pictures can stack. At strength 0 it returns the input untouched.

It only does something on a model class that reads the key. Two classes do.

- `SD21UNCLIP` uses `unclip_adm` to build its vector input. A real unCLIP checkpoint comes with its vision model, which is why `unCLIPCheckpointLoader` has a fourth output.
- `SDXL`'s `sdxl_pooled` swaps the pooled text vector for the image's when the key exists.

`noise_augmentation` adds noise to the image vector, and blurs what it says about the picture. The idea of generating from CLIP's image vector goes back to Ramesh et al. (2022).

{{graph:c_unclip}}

## Which to use

| You have | Use |
|---|---|
| A model with a matching style model file, such as FLUX.1 and Redux | `StyleModelApply` |
| An SD 2.1 unCLIP checkpoint | `unCLIPConditioning` |
| Neither | Not these. See CU-214 for other routes |

## What goes wrong

- **unCLIP does nothing.** Your model class doesn't read that key. It's silently ignored (CU-260).
- **An invalid style model error.** `load_style_model` raises it when the file has neither key. The file isn't a style model it knows.
- **A shape error on a style model.** The width must match the model's text width: 768 for the adapter, 4096 for Redux. We expect this from the shapes, and haven't run it.
- **A vision model that doesn't match.** Redux's input is 1152 wide, so it needs a vision model with that width. Check the model's card.
- **Faces or edges cut off.** `center` crops to a square. Crop your picture first, or use `none`.
- **Strength 0 on a style model is not off.** With `multiply`, the zero rows stay in, so attention still sees them. Bypass the node to turn it off.
- **Expecting a copy of the picture.** These pass on what the vision model summed up. They don't pass pixels.

## Lab

Ports of the two nodes, with random numbers shaped like the real thing. The vision output here is a stand-in.

```text
start                 [1, 77, 768] ['pooled_output']
StyleModelApply       [1, 85, 768] ['pooled_output']
unCLIPConditioning    [1, 77, 768] ['pooled_output', 'unclip_conditioning']
unCLIP twice: entries in the key: 2
unCLIP at strength 0 returns the input untouched: True
```

One grew the tensor and one grew the dict. That's the two doors.

```text
style strength 0, multiply: tokens are still there, 85 of them, all zeros: True
text tokens untouched by the style model: True
```

```text
Redux maps each vision token from 1152 to 4096 numbers: the same width as T5-XXL's tokens
so 4 vision tokens become [1, 4, 4096]
```

```text
SDXL global vector without the key: pooled text
SDXL global vector with the key:    image embedding through unclip_adm, first 1280 numbers
```

## Sources

- [Ramesh et al. 2022. Hierarchical Text-Conditional Image Generation with CLIP Latents](https://arxiv.org/abs/2204.06125)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/clip_vision.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/clip_vision.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/redux.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/redux.py)
