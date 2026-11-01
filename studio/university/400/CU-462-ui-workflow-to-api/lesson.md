# CU-462 - From a UI workflow to API format, and setting values by node id

**Objective.** Get an API-format graph out of a workflow, change its values by node id without breaking it, and say why a converter of your own is a last resort. Taught by Captain Graph.

## The idea

`POST /prompt` takes the API format. File, Save gives you the save format. CU-110 shows how each reads. This lesson is about moving from one to the other and then editing with a script.

The short answer: let the editor do it. Choose File, then Export Workflow (API). Keep that file next to your script, and change only the values.

{{graph:sd15_txt2img}}

In the API format, this graph is a dict of seven entries. The keys "1" to "7" are node ids. The ids in the export come from the graph, so they stay as long as nobody deletes and re-adds the node.

## What the export does

`graphToPrompt` in the front end builds the API form. Read in order, it does this:

- It walks the nodes, and skips virtual ones such as a `Note` and any that are muted or bypassed.
- It writes each widget by name, unless the widget is marked not to be sent.
- For each input, it asks where the value really comes from. That is how a bypassed node or a reroute vanishes: the wire is followed through to its true source.
- It wraps any array value as `{"__value__": [...]}`, because a plain array means a wire. `execution.py` unwraps it again.
- It adds `_meta` with the title. The comment in the code says the backend ignores it.

Everything about the page drops out: positions, sizes, colours and groups.

## Why a converter is harder than it looks

`widgets_values` has no names. It's a list, and you must know the order. You'd think the order is just the node's widget inputs. But a seed widget has a partner, the "control after generate" setting, and that value sits in the list right after the seed. The front end marks that partner not to be sent, so it never reaches the API form.

The KSampler in ComfyUI's own `default_workflow.json` has this list: `[42, "fixed", 8, 1, "res_multistep", "simple", 1]`. Name them yourself.

{{play:uitoapi}}

We tested the idea on that stock file. A converter using widget order from `object_info` and a seed partner passed `validate_prompt` on every node, except for the three loaders whose model files aren't on our test machine. Setting `steps` to `fixed`, as a shift by one would, gave `invalid_input_type` from the real function.

A real workflow can hold more: subgraphs, reroutes, bypassed nodes that need rewiring, and widgets that a pack's own JavaScript creates. The server doesn't know any of those exist. If you need a converter for files you did not make, this lab is enough for a simple one and no more.

## Setting values safely

Three rules for your script:

- **Copy first.** Then the loaded graph stays clean for the next job.
- **Look a node up once, and check that you found exactly one.** Using a node id is fine if the file is yours. Otherwise search by `class_type`, plus the title in `_meta` if there are several. A title can be edited or repeated, so raise an error unless one node matches.
- **Never write over a wire.** A list means a connection. Setting `model` to text would break the graph. Check first.

## Lab

The lab converts a small save-format file with the widget orders from `object_info`. That file has a muted save node and a `Note`.

```text
nodes in the file: 9   nodes in the API graph: 7   left out: ['8', '9']
node 5: {"seed": 424242, "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "karras", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}
```

`randomize` has gone. The API format holds the number and nothing about what to do next.

Now the same converter without the seed's partner:

```text
forget the editor-only value: {'seed': 424242, 'steps': 'randomize', 'cfg': 20, 'sampler_name': 7.0, 'scheduler': 'euler', 'denoise': 'karras'}
the check says: [('5', 'steps', 'invalid_input_type'), ('5', 'denoise', 'invalid_input_type')]
```

Every value moved over by one. Here the type check catches it. If a value had been a number too, nothing would.

Then the edit, with its guard rails. Only two values changed:

```text
changed: [('2', 'text'), ('5', 'seed')]
find by class alone: CLIPTextEncode None: 2 matches
set a wire: model on node 5 is a wire
mistyped name: 'node 5 has no input sed'
```

The last check matters more than it looks. The real server ignores input names it doesn't know. We ran a graph through the real `validate_prompt` and executor with two extra inputs, `colr` and `wdth`, on an `EmptyImage`. It passed, ran, and reported nothing. So a mistyped `sed` next to the real `seed` would leave the seed as it was. Check your names yourself.

## What goes wrong

- **Your edit did nothing.** A mistyped input name. See above.
- **`seed` won't change between jobs.** The word "randomize" is in the save file only. Your script sets the number.
- **A node vanishes in the export.** It was muted or bypassed, or it's a `Note`. Bypassed nodes are bridged, so look at what the wire now leads to. CU-113 has the details.
- **Node ids changed.** Someone deleted and re-added a node, and the id is new. Lookup by class and title will notice; a hard-coded id may hit the wrong node.
- **A value that looks like `{"__value__": ...}`.** Leave the wrapper in place, and put your new array inside it.
- **A file from another machine.** A file name in a loader may not exist there. The server replies `value_not_in_list`. Compare it with `GET /object_info/{class}` first.

## Sources

- [ComfyUI docs: Workflow API format](https://docs.comfy.org/development/api-development/workflow-api-format)
- [ComfyUI front end, src/utils/executionUtil.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/utils/executionUtil.ts)
- [ComfyUI front end, valueControlWidgets.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/core/graph/widgets/valueControlWidgets.ts)
- [ComfyUI v0.43.0, default_workflow.json](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/default_workflow.json)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
