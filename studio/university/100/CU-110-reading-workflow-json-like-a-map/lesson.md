# CU-110 - Reading a workflow JSON like a map

**Objective.** Tell ComfyUI's two JSON dialects apart, follow a wire from either file back to its source, and find the values you care about, such as the seed, the prompt text and the model files. Taught by Captain Graph.

## The idea

ComfyUI describes the same graph in two ways. The save format is for the editor: nodes with positions, sizes, sockets and widget values, plus a list of links. You get it from File, Save. The API format is for the server: a dictionary from node id to the node's class and inputs, and nothing about layout. You get it from File, Export Workflow (API). The documentation puts it as "API format omits UI metadata (positions, colors, groups, node sizes) that is only needed for visual editing".

An image saved by ComfyUI usually carries both. The `workflow` field holds the save format and the `prompt` field holds the API format, written into the file as PNG text chunks unless the server was started with `--disable-metadata`. Dragging such an image onto the canvas rebuilds the graph from the `workflow` field.

## The mechanism

**The save format.** A file in the 0.4 schema has `last_node_id`, `last_link_id`, `nodes`, `links` and `version`. A node has an `id`, a `type`, `pos`, `size`, `flags`, `order`, `mode`, `inputs`, `outputs`, `properties` and `widgets_values`. Each input socket has a `link` that is the id of the link ending there, or null, and each output socket has a list `links` of the links that start there. A link is a row of six: link id, origin node, origin slot, target node, target slot, type. Version 1.0 of the schema writes each link as an object with the same fields. Keep three kinds of number apart: node ids, link ids and slot positions.

Two facts make files harder to read than they look. The wiring is written twice, once in `links` and once in the sockets, so a damaged file can disagree with itself. And `widgets_values` is a plain list in a fixed order, with no names. The names come from the node's definition, and the list can hold more entries than the server will ever see: the "control after generate" choice of a KSampler sits in it and goes no further.

**The API format.** Each entry is `{"inputs": ..., "class_type": ...}`, with an optional `_meta` title. An input is either a constant or a link, and a link is a list of two items: the source node's id as a string and the number of the output slot.

**Reading it.** Find the output nodes. Follow each input backwards: a link names the node and the output it comes from, and a constant is a setting. Everything reached this way is what the picture depends on, and it is the part of the graph the executor looks at (CU-102). What a workflow does not contain is just as important: the model files, the input images and the custom node packages must exist on the machine that runs it.

Open this graph, then export it both ways and compare the two files with this lesson beside you.

{{graph:sd15_txt2img}}

Now fix some graphs by hand. This is the API format, and the check uses the server's own error names.

{{play:graphfix}}

## In ComfyUI

The server takes a POST on `/prompt` with a body that holds the API dictionary under `prompt`, and optionally `extra_data` and a `client_id`. It validates the graph and returns a prompt id, or an error with the nodes that failed (CU-102). `SaveImage` receives the API prompt and a hidden input called `extra_pnginfo`, and writes them into the PNG as text entries: one named `prompt` and one for every key of `extra_pnginfo`. The standard names are `prompt` and `workflow`.

`is_link` in `comfy_execution/graph_utils.py` accepts a list only when it has two items, the first a string and the second a number. In v0.43.0 the repository's own `default_workflow.json` is a version 0.4 file, with links as rows of six.

The documentation says to treat embedded metadata as optional and untrusted input, and that it is not a digital signature. A file that was re-encoded by another program may have lost it.

## What goes wrong

- **You post the save format to `/prompt`.** The server expects the API dictionary. On the default workflow file, `validate_prompt` raised a `TypeError` in our test, because `last_node_id` isn't a node. Export the API format.
- **A source id written as a number.** `["4", 0]` is a wire and `[4, 0]` isn't. The lab shows the failed lookup.
- **Editing `links` alone.** The wiring is written twice, so a hand edit to one copy leaves a file that disagrees with itself. The lab finds this for you.
- **Reading `widgets_values` by position across versions.** Those lists have no names. A node whose widgets change in a new version can give an old list a new meaning.
- **A script finds nodes by title.** Titles live in `_meta` and can be edited or repeated. Search on `class_type`, then confirm.
- **The seed never changes in your script.** "randomize" stays behind in the save format, and the API format has only a number. Set a new seed each time, or the cache answers (CU-112).
- **A PNG with no workflow.** Another program re-encoded it, or the server ran with `--disable-metadata`. CU-111 lets you cut one out yourself.
- **Muted nodes are missing from your API export.** They're meant to be (CU-113).

## Lab

The lab builds the classic seven-node graph in the 0.4 schema, with made-up positions and sizes, and reads it.

```text
save format, version 0.4: 7 nodes, 9 links
id  type                    inputs wired (name<-link id)                        widgets_values
4   CheckpointLoaderSimple  -                                                   ['model_a.safetensors']
5   EmptyLatentImage        -                                                   [512, 512, 1]
6   CLIPTextEncode          clip<-1                                             ['a red fox in snow']
7   CLIPTextEncode          clip<-2                                             ['blurry']
3   KSampler                model<-3, positive<-4, negative<-5, latent_image<-6 [156680208700286, 'randomize', 20, 8, 'euler', 'normal', 1]
8   VAEDecode               samples<-7, vae<-8                                  []
9   SaveImage               images<-9                                           ['ComfyUI']
```

The rows are sorted by the `order` field, which is why id 3 comes after id 7, and the `inputs` list shows only the wired sockets. Everything else on a node is a widget. Now the check of the wiring that is written twice, on the file and on four damaged copies.

```text
wiring written twice agrees: True
link 4 deleted from links     1 found: node 3 input 'positive' says link 4, which is not in links
link 6 re-pointed to slot 2   2 found: node 3 input 'negative' says link 5, but link 6 ends there
link 9 typed MODEL            1 found: link 9 is typed MODEL, but joins an output of type IMAGE to an input of type IMAGE
link 1 joins node 42          1 found: link 1 joins node 42 to node 6, and one of them does not exist
```

A reader that trusts only one copy of the wiring can miss every one of these. Next the translation to the API format, using a table of widget names for the six node types.

```text
save format -> API format: 7 entries, keys ['3', '4', '5', '6', '7', '8', '9']
KSampler has 7 widget values but 6 widget inputs in the API format
API entry 3: {"inputs":{"model":["4",0],"positive":["6",0],"negative":["7",0],"latent_image":["5",0],"seed":156680208700286,"steps":20,"cfg":8,"sampler_name":"euler","scheduler":"normal","denoise":1},"class_type":"KSampler"}
```

The four wired sockets became lists, the widget values got names, and "randomize" disappeared. The node ids became strings, which is how the API format spells them. Now the same questions asked of both dialects.

```text
positive text and seed from the save format: ('a red fox in snow', 156680208700286)
positive text and seed from the API format:  ('a red fox in snow', 156680208700286)
nodes the SaveImage depends on: ['3', '4', '5', '6', '7', '8']
model files named in the graph: ['model_a.safetensors']
```

Both routes reach the same text and seed. In the save format you go from the KSampler's `positive` socket to a link id, then to the origin node. In the API format the input itself names the source. The SaveImage depends on six nodes, which is every node but itself, and the only model file is the checkpoint.

```text
source id written as 3 instead of '3': looking up the node gives KeyError 3
```

Object keys in JSON are strings, so a source id typed as a number finds nothing. `is_link` does not count `[3, 0]` as a link, and the lookup in `validate_inputs` would raise, which `validate_prompt` reports as a failed validation. This follows from reading the code, and the lab only shows the failed lookup.

## What is contested

The lab's file is built from the schema, not exported from ComfyUI, and real exports carry more fields, such as properties for custom nodes, groups and, in the 1.0 schema, reroutes. The table of widget names covers six node types. The true source is the node definition, so a node whose widgets are reordered or renamed in a new version changes the meaning of old `widgets_values` lists. The lab does not cover muted or bypassed nodes, subgraphs, or the Primitive and Reroute nodes, which the datatypes page says exist only on the client side.

## Sources

- [Workflow JSON](https://docs.comfy.org/specs/workflow_json)
- [Workflow JSON 0.4](https://docs.comfy.org/specs/workflow_json_0.4)
- [Workflow API Format](https://docs.comfy.org/development/api-development/workflow-api-format)
- [Workflow Metadata](https://docs.comfy.org/development/api-development/workflow-metadata)
- [ComfyUI Server Routes (HTTP and WebSocket API)](https://docs.comfy.org/development/comfyui-server/comms_routes)
- [ComfyUI Custom Node Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes)
- [ComfyUI v0.43.0, default_workflow.json](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/default_workflow.json)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, comfy_execution/graph_utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph_utils.py)
- [ComfyUI v0.43.0, script_examples/basic_api_example.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/script_examples/basic_api_example.py)
