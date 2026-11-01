# CU-260 - What CONDITIONING really is

**Objective.** Say what a CONDITIONING value contains in the code, trace how it reaches the model, and predict what a conditioning node can change. Taught by Madame Attention.

## The idea

On the canvas, CONDITIONING is an orange wire that looks mysterious. In the code it is the plainest thing in ComfyUI: a Python list. Each entry is a two-item list of a tensor and a dict.

```python
[ [tensor, {"pooled_output": ..., }], ... ]
```

The tensor holds the prompt's tokens: for SD 1.5, shape `[1, 77, 768]`, one row of 768 numbers per token. The dict holds everything else. Once you know this, most conditioning nodes stop being mysterious, because there are only three things they can do.

- **Change the dict.** `ConditioningSetArea`, `ConditioningSetMask`, `ConditioningSetTimestepRange` and `FluxGuidance` just write keys.
- **Change the tensor.** `ConditioningConcat`, `ConditioningAverage` and `ConditioningZeroOut` make a new tensor.
- **Change the list.** `ConditioningCombine` is one line: `conditioning_1 + conditioning_2`.

Build one and watch it change.

{{play:condkeys}}

## The route to the model

1. `CLIPTextEncode` calls `encode_from_tokens_scheduled`, which returns the list. That's the wire you see.
2. Your conditioning nodes pass it along. `conditioning_set_values` copies each dict and shares the tensor, so they are cheap and don't change the input.
3. In the sampler, `convert_cond` turns each entry into one flat dict. The tensor becomes the `cross_attn` key, and it adds `model_conds` and a `uuid`.
4. `encode_model_conds` calls the model's `extra_conds` with those keys as keyword arguments. For a model, that produces inputs such as `c_crossattn` and `y`.
5. At each step, `calc_cond_batch` takes each entry, checks whether it is active at this noise level (CU-264), crops it if it has an area (CU-263), and runs the model.

Step 4 explains a trap. A model class reads only the keys it looks for, using `kwargs.get`. Any other key is carried along and ignored, silently.

## Reading a graph with this in mind

Here's a graph where one wire carries two prompts, each active for part of the schedule. Follow it knowing what each node really does: two entries, four keys, then one list.

{{graph:sd15_cond_time}}

And the plainest case, for comparison. Its `positive` wire is a list with one entry.

{{graph:sd15_txt2img}}

## What goes wrong

- **A setting has no effect, and no error appears.** The key was written but this model class doesn't read it. `FluxGuidance` on SD 1.5 is an example.
- **A second range node "forgot" the first.** `conditioning_set_values` overwrites a key, so the last value wins. It doesn't combine with the earlier one. The lab shows it.
- **A node's effect appears on both prompts.** Nodes that set a key change every entry in the list. Apply the key before you `Combine`, if you want it on one prompt only.
- **Treating `ConditioningZeroOut` as an empty prompt.** It keeps the shape and zeroes the numbers. An encoded empty prompt is not zeros.
- **Wiring text from one model family into another.** The tensor width is part of the model's design: 768 on SD 1.5, 2048 on SDXL. We expect a shape error from a mismatch, but we didn't run one. Use the text encoder that matches the model.

## Lab

Ports of the nodes, using random tensors with real shapes. We ran the real nodes on a CPU as well, and the shapes and keys match.

```text
CLIPTextEncode                     1 entry   [1, 77, 768] ['pooled_output']
ConditioningSetArea                1 entry   [1, 77, 768] ['area', 'pooled_output', 'set_area_to_bounds', 'strength']
then SetTimestepRange              1 entry   [1, 77, 768] ['area', 'end_percent', 'pooled_output', 'set_area_to_bounds', 'start_percent', 'strength']
then Combine with a second prompt  2 entries   [1, 77, 768] ['area', 'end_percent', 'pooled_output', 'set_area_to_bounds', 'start_percent', 'strength']   [1, 77, 768] ['pooled_output']
```

The tensor shape never changed. Only the dict and the list did.

```text
SetArea made a new tensor: False    and changed the original dict: False
a second SetTimestepRange keeps (0.3, 0.9) and forgets (0, 0.5)
```

And what the sampler sees, once `convert_cond` has run:

```text
['area', 'cross_attn', 'end_percent', 'model_conds', 'pooled_output', 'set_area_to_bounds', 'start_percent', 'strength', 'uuid']
['cross_attn', 'model_conds', 'pooled_output', 'uuid']
```

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, node_helpers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/node_helpers.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/sampler_helpers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sampler_helpers.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
- [ComfyUI v0.43.0, comfy/sd1_clip_config.json](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd1_clip_config.json)
