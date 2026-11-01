# CU-251 - Embedded guidance against CFG

**Objective.** Tell cfg and embedded guidance apart, say what each costs, and work out what cfg a flux-family graph needs instead of assuming it. Taught by Dr. Denoise.

## The idea

There are two different things called guidance, and they live in different places.

- **Cfg is a sum outside the model.** Run the model twice, then push the answers apart. It costs two predictions, and a negative prompt has a job to do.
- **Embedded guidance is an input to the model.** You hand it a number, the same way it is handed the timestep. It runs once, and there is no second answer for a negative to fill.

Look at the sum from CU-208 with cfg at 1, and the second branch cancels. So a graph at cfg 1 runs one prediction per step and pays half the cost. That is why you see cfg 1 on many flux-family graphs. But the reasons differ from file to file, and some flux-family graphs do use cfg.

## What the code does

`FluxGuidance` is short. It writes one key into the conditioning's dict and does nothing else:

```python
c = node_helpers.conditioning_set_values(conditioning, {"guidance": guidance})
```

Later, `extra_conds` on the Flux model turns that key into a model input. If the key is missing it uses 3.5. `FluxDisableGuidance` sets the key to None, which turns it off. Then, in `forward_orig`:

```python
if self.params.guidance_embed:
    if guidance is not None:
        vec = vec + self.guidance_in(timestep_embedding(guidance, 256).to(img.dtype))
```

So the number becomes a 256-long vector, goes through a small learned layer, and is added to the same vector that carries the timestep. Nothing in the sampler knows about it.

`guidance_embed` is not your choice. `model_detection.py` sets it by looking in the weights file for `guidance_in` layers. If the file doesn't have them, your number is simply never used, and nothing warns you. That is true of `FluxSchnell`, which core lists with `guidance_embed: False`.

{{play:embed}}

## Four cases in the flux family

| Model | cfg | Why | Evidence |
|---|---|---|---|
| FLUX.1 dev | 1, plus a guidance number | The file has a guidance input, so guidance goes in that way. | ComfyUI's Flux examples page says to set cfg to 1.0 for the FP8 dev checkpoint. |
| FLUX.1 schnell | 1 | No guidance input. The examples page calls it a distilled 4-step model. | `guidance_embed: False` in core. Our schnell renders ran at cfg 1. |
| FLUX.2 Klein 4B, distilled | 1, with 4 steps | The FLUX.2 table marks it step-distilled and guidance-distilled. | Model card and FLUX.2 repository. |
| FLUX.2 Klein 4B Base | Above 1 | The same table marks it as neither. The card says it was trained without step or guidance distillation. | Its card shows guidance_scale 4.0 and 50 steps. |

So the honest answer to "why does a flux-family model run at cfg 1?" is: because that file was trained so that it needs no second prediction, or takes guidance another way. It is a fact about the weights, not about the family name. A flow model doesn't need cfg 1 either: our SD 3.5 renders are flow-matching and run at cfg 4.5.

Our own workflow shows this. `flux2_klein4b_t2i_api.json` has a `CFGGuider` whose cfg is a slot, not a number. The studio fills it with 1.0 and 4 steps for the distilled file, and with 5.0 and 20 steps for the Base file. Same graph, same family, different cfg, because the files differ. Here's the distilled setup.

{{graph:c_klein_fast}}

The second graph below is the Base setup, with cfg 5 and 20 steps and a real negative. Its loader names a Base file. Don't swap in the distilled file with these settings.

{{graph:wf_flux2_klein}}

And here is a FLUX.1 dev graph. `BasicGuider` takes one conditioning and has no cfg input at all, which makes the point: there's no second branch to run.

{{graph:c_flux_guidance}}

## What goes wrong

- **A negative prompt that does nothing on a flux-family graph.** At cfg 1 it is never run (CU-209). Don't spend time tuning it.
- **A guidance number that does nothing.** The file has no `guidance_in`, or a `FluxDisableGuidance` is in the chain. The value is dropped with no message.
- **cfg 5 on a distilled file.** It runs twice as slowly and gets guidance it was not trained for. Use the card's settings.
- **cfg 1 on a Base file.** The picture gets no guidance at all. The Base card uses guidance_scale 4.0.
- **Setting both high.** Cfg and embedded guidance are separate pushes. The lab's last row shows both active. We have no evidence this helps, so change one at a time.
- **Putting FluxGuidance on an SD 1.5 graph.** The key is written and ignored, because only some model classes read it.

## Lab

A stand-in model counts its own predictions. It reads the guidance number only if it has `guidance_in`, as the real one does.

```text
20 steps                                    predictions   negative matters   guidance number matters
no guidance_in, cfg 7 (SD 1.5, SDXL, SD 3.5) 40            True               False
no guidance_in, cfg 1 (a distilled file)    20            False              False
has guidance_in, cfg 1 (FLUX.1 dev)         20            False              True
has guidance_in, cfg 3.5 (both at once)     40            True               True
```

The middle two rows are the ones to remember. Both run at cfg 1 and cost the same. Only one of them listens to the guidance number, and neither listens to the negative.

```text
what the model is handed as the guidance number: a 256-long vector, like the one for the timestep
guidance 1.0   first values +0.562 +0.790 +0.440   size 11.31   difference from 3.5: 15.17
guidance 3.5   first values +0.965 -0.675 -0.724   size 11.31   difference from 3.5: 0.00
guidance 3.6   first values +0.965 +0.434 +0.531   size 11.31   difference from 3.5: 11.80
guidance 10.0  first values -0.952 +0.948 +0.157   size 11.31   difference from 3.5: 16.37
```

Notice that 3.6 is almost as far from 3.5 as 1.0 is. The number is spread across sines and cosines, multiplied by 1000 first. It isn't a volume knob inside the network. What a value does to a picture depends on what the model learned for it, and this table can't tell you that.

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_flux.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_flux.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/model.py)
- [ComfyUI v0.43.0, comfy/ldm/flux/layers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/flux/layers.py)
- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
- [ComfyUI v0.43.0, comfy/model_detection.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_detection.py)
- [ComfyUI v0.43.0, comfy/supported_models.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/supported_models.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_custom_sampler.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_custom_sampler.py)
- [ComfyUI Examples: Flux](https://comfyanonymous.github.io/ComfyUI_examples/flux/)
- [FLUX.2 repository README](https://github.com/black-forest-labs/flux2)
- [FLUX.2 klein 4B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)
- [FLUX.2 klein 4B Base model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B)
