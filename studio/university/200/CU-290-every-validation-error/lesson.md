# CU-290 - Every validation error, and what to do about it

**Objective.** Read any validation error, find the node it means, and fix it. Taught by Captain Graph.

## The idea

When you press Queue, the server checks the graph first. If the check fails, nothing runs, and you get an error instead of a picture. That is good news. These are the cheapest errors you will ever meet, and each one names what it doesn't like.

There are two kinds of reply. The whole prompt can be refused for one reason, such as no outputs. Or the reply can say `prompt_outputs_failed_validation` and hold a `node_errors` list, with an entry for each node at fault. **Read `node_errors`.** The top message often says very little: when the fault sits upstream of the output, its `details` field is empty.

In the console it looks like this. This is real text, from a graph with `image` left out of `ImageInvert`:

```
Failed to validate prompt for output 2:
* ImageInvert 1:
  - Required input is missing: image
Output will be ignored
```

Read it as: output node 2 can't run, the fault is at node 1 (`ImageInvert`), and here's why.

## The order of the checks

`validate_prompt` goes through the graph in this order:

1. Does every node have a `class_type`, and is that class installed? If not, stop at once.
2. Is there at least one output node? If not, stop.
3. For each output node, walk back along the wires. `validate_inputs` checks each node it reaches.
4. Check loop nodes, if there are any.

Nodes that don't lead to an output are never looked at. So a broken node on an unused branch gives no error.

## Every error

All of the following came from the real function on a CPU, with core nodes, unless marked otherwise. Fix them yourself in the lab below, and try them in this small graph, which passes as it stands.

{{graph:f_validation_base}}

**Refusing the whole prompt**

| Type | Real text | What to do |
|---|---|---|
| `missing_node_type` | `Node 'SuperKSampler' not found. The custom node may not be installed.` | Install the pack, or replace the node. CU-294. |
| `missing_node_type` | `Node 'ID #1' has no class_type. The workflow may be corrupted or a custom node is missing.` | The JSON is damaged, or isn't API format. |
| `prompt_no_outputs` | `Prompt has no outputs` | Add `SaveImage` or `PreviewImage`. |
| `prompt_outputs_failed_validation` | `Prompt outputs failed validation` | The wrapper. Read `node_errors`. |
| `no_prompt` | `No prompt provided` | From the server route (read in source, not run). Your API call has no `prompt` key. |
| `invalid_prompt_id` | `prompt_id must be a valid UUID` | From the server route (read in source, not run). Omit it, or send a real UUID. |

**About one input**

| Type | Real text | What to do |
|---|---|---|
| `required_input_missing` | `Required input is missing: image` | Connect it or give it a value. |
| `bad_linked_input` | `Bad linked input, must be a length-2 list of [node_id, slot_index]: images` | A list that isn't a wire. In API JSON, a wire is `["1", 0]`. |
| `return_type_mismatch` | `Return type mismatch between linked nodes: images, received_type(MASK) mismatch input_type(IMAGE)` | Wrong output plugged in. Check the slot number, or convert it (`MaskToImage`). |
| `invalid_input_type` | `Failed to convert an input value to a INT value: width, wide, invalid literal for int() with base 10: 'wide'` | Text in a number field. |
| `value_smaller_than_min` | `Value 0 smaller than min of 1: width` | Raise it. |
| `value_bigger_than_max` | `Value 999999 bigger than max of 16384: width` | Lower it. |
| `value_not_in_list` | `Value not in list: upscale_method: 'magic' not in ['nearest-exact', 'bilinear', 'area', 'bicubic', 'lanczos']` | Pick from the list. For model menus, see CU-294. |
| `custom_validation_failed` | `Custom validation failed for node: image - Invalid image file: nothing_here.png` | The node's own check said no. Read its reason. |
| `custom_validation_failed` | `End Loop has no Start Loop: End Loop 4 has no available Start Loop` | The same type, used for loop checks. Wire a matching Start Loop. |
| `invalid_dynamic_input` | `Invalid dynamic input: Invalid DynamicGroup input key 'loras.bogus.name'; expected 'loras.<index>.<template field>'.` | A hand-edited or older graph for a node with rows. Re-add the node. |

**About the graph's shape**

| Type | Real text | What to do |
|---|---|---|
| `dependency_cycle` | `Dependency cycle detected: 1 (ImageInvert) -> 3 (ImageInvert) -> 1 (ImageInvert)` | Break one wire in the chain it prints. Real loops use Start Loop and End Loop. |
| `exception_during_inner_validation` | `Exception when validating inner node: '99'` | A wire points at node 99, which isn't there. A hand-edit or a bad delete. |
| `exception_during_validation` | `Exception when validating node: '99'` | The same, on the output node itself. |
| `exception_during_validation` | `Exception when validating node: tuple index out of range` | A wire asks for an output slot that the source doesn't have. |

Those last two look alike, and they cover anything that raises during the check, including a crash in a node's own validator. When the details are just `'99'`, that is Python's `KeyError` text, and the number is a node id.

## Now fix some

These error names and messages come from `execution.py`, and a test compares this checker with the real one.

{{play:graphfix}}

## Partial success

Validation works per output. In this real run, a graph had two previews, and the chain behind the second one was broken. The first preview still ran.

```
ok: True    outputs that run: ['2']
node 3 ImageInvert | required_input_missing | Required input is missing | image
```

So "my queue ran, but one output is missing" means a validation error you may have scrolled past. Over the API, the reply is 200 with a non-empty `node_errors`.

## What goes wrong

- **You read the top line only.** `Prompt outputs failed validation` tells you nothing. Go to the per-node lines.
- **A graph from someone else fails on every model.** `value_not_in_list` on `ckpt_name`. Your file names differ from theirs, folder names included. CU-294.
- **A slot number off by one.** In API JSON, `["4", 2]` on a checkpoint loader is the VAE. `return_type_mismatch` catches most of these, unless the types happen to match, as when positive and negative are swapped.
- **Nothing is wrong with a node, but it's marked.** The real fault is upstream. Only nodes with reasons attached appear in `node_errors`, so start with those.
- **A big API graph where you edited ids.** `'99'` errors. Search the JSON for that id.
- **A check that passes and a run that fails.** Validation doesn't run your nodes. It checks types and values, not sizes or whether a file loads. Those failures come later, and they look different (CU-292).

## Lab

The lab is a small validator with the same order of checks, on a stand-in table of nodes. Each case stores the text the real function returned, and the lab asserts that it matches, including the ones below.

```text
input left out                        required_input_missing: Required input is missing: image
MASK into IMAGE                       return_type_mismatch: Return type mismatch between linked nodes: images, received_type(MASK) mismatch input_type(IMAGE)
width 0                               value_smaller_than_min: Value 0 smaller than min of 1: width
two nodes in a loop                   dependency_cycle: Dependency cycle detected: 1 (ImageInvert) -> 3 (ImageInvert) -> 1 (ImageInvert)
wire to a missing node, mid graph     exception_during_inner_validation: Exception when validating inner node: '99'
wire to a missing node, on the output exception_during_validation: Exception when validating node: '99'
wire to a missing slot                exception_during_validation: Exception when validating node: tuple index out of range
```

And the graph with one good output:

```text
two outputs, one broken: runs ['2']  reported: required_input_missing
```

## Sources

- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/validation.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/validation.py)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, comfy_api/latest/_io.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_io.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
