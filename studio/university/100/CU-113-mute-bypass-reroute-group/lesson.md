# CU-113 - Mute, bypass, reroutes and groups: what the server really gets

**Objective.** Predict what the server receives when a node is muted or bypassed, or when a graph uses reroutes and groups, and use that to fix the errors they cause. Taught by Captain Graph.

## The idea

The canvas holds more than the server ever sees. Modes, reroute dots, notes and coloured group boxes all live in the editor. When you press Queue, the editor rewrites your graph into the API format (CU-110), and the server only gets the result. It has no idea a node was bypassed, because the node simply isn't there.

So each of these is a question about what the editor writes down. Here is a graph to try them on.

{{graph:a_modes_chain}}

## The four things

**Bypass (Ctrl+B).** The node is left out, and whatever wanted its output gets one of its inputs instead. The editor picks the input in this order: the input with the same slot number if the types fit, then the first input of the type wanted, then the first that fits. If none does, the wire is dropped.

**Mute (Ctrl+M).** The menu calls this mode Never. The node is left out and gives nothing, so the wire is dropped. The docs say "as if it's been deleted", and that is close, with one catch: nodes after it stay on the canvas, still expecting an input.

The rule of thumb: bypass passes through, and mute cuts.

**Reroute.** A reroute node is purely for the editor, and its source comment says it "does not impact the resulting prompt". The wire is followed through it, so the next node is wired directly to the real source. Our server check shows the other side: send a `Reroute` by hand and you get `missing_node_type`, because the server has no such class. The save format also has a newer kind of reroute, a point on a link listed in a top-level `reroutes` array, which isn't a node at all.

**Group.** A group is a title, a box and a colour in the save format. It is never sent. Its menu has "Set Group Nodes to Always", "Set Group Nodes to Never" and "Bypass Group Nodes", and those just set the mode of each node inside. So a group is a way to select nodes, not a thing the graph runs. Notes are similar: `Note` and `MarkdownNote` are virtual and are not sent.

Try it. The right column updates as you change a mode, using the same rules.

{{play:modes}}

## The two errors you will meet

**`Required input is missing`** usually means something upstream was muted, or was bypassed with no input of the right type. Follow the input the error names back up the canvas and look for a greyed node. Muting one node in a chain tends to break the node after it, so to turn off a step in the middle, bypass it.

**`Prompt has no outputs`** means you muted or bypassed the last output node, or a group holding all of them.

To skip a whole branch, mute or bypass its output node, and leave the rest alone. Nodes that no output needs don't run (CU-100), so nothing else has to change. That is usually the cleanest switch in a big graph.

## What goes wrong

- **A bypassed node changes the wrong thing.** Bypass picks by type and position. A node with two IMAGE inputs passes on the one in the same slot as the output, which may not be the one you meant. Read the exported JSON to be sure.
- **Bypassing a loader or a starting node.** It has no inputs to pass on, so the wire is dropped and the next node reports a missing input. Same for any node whose output type differs from all its inputs, such as `VAEDecode`.
- **An old workflow has a greyed-out node and "does nothing".** Someone left it muted or bypassed. The mode is stored in the save format as `mode`: 0 is normal, 2 is Never, 4 is Bypass. Reading the file shows it (CU-115).
- **A script edits a node that is not there.** An API export has no muted or bypassed nodes. If your script sets the seed on node 5 and node 5 was bypassed at export, you get a `KeyError` in your own code, not an error from the server.
- **Sending API JSON with a Reroute or Note in it.** The export never does this. Hand-written JSON can, and it gets `missing_node_type`.
- **Thinking a group protects its contents.** A group has no effect on running, and moving a node out of the box only changes which nodes the group's menu touches.

## Lab

A short port of the editor's `graphToPrompt`, on the graph above plus a reroute between the blur and the invert, and a note. The wires column shows each input name and the node it reads from. The node numbers: 1 EmptyImage, 2 ImageBlur, 3 Reroute, 4 ImageInvert, 5 PreviewImage, 6 Note.

```text
blur then invert      nodes sent    wires                       server says
as drawn              1 2 4 5       image<-1 image<-2 images<-4 valid
bypass 2 ImageBlur    1 4 5         image<-1 images<-4          valid
mute 2 ImageBlur      1 4 5         images<-4                   required_input_missing: image of ImageInvert
bypass 2 and 4        1 5           images<-1                   valid
mute 2 and 4          1 5           -                           required_input_missing: images of PreviewImage
mute 5 PreviewImage   1 2 4         image<-1 image<-2           prompt_no_outputs
bypass 1 EmptyImage   2 4 5         image<-2 images<-4          required_input_missing: image of ImageBlur
```

Nodes 3 and 6 are never in the list. "As drawn" shows the invert reading straight from node 2. Mute and bypass of node 2 send the same three nodes, and only the wire differs. The next two lines are a group holding 2 and 4. Now a node with no input of the type its output promises.

```text
latent to picture     nodes sent    wires                       server says
as drawn              1 2 3 4       samples<-2 vae<-1 images<-3 valid
bypass 3 VAEDecode    1 2 4         -                           required_input_missing: images of PreviewImage
mute 3 VAEDecode      1 2 4         -                           required_input_missing: images of PreviewImage
```

Here bypass and mute give the same result. And the point of the lesson, in one line:

```text
the word mode appears in it: False
```

We separately ran ComfyUI's real `validate_prompt` on the same shapes of graph. It accepted the bypassed form, gave `required_input_missing` for the muted form and `prompt_no_outputs` without an output, and refused a `Reroute` as `missing_node_type`.

## What we could not check

We read the editor's code on its main branch and did not press these keys in a browser, so export a graph yourself if it matters. Your installed version may differ from main. The port leaves out subgraphs and uses plain type equality in place of the editor's own connection test. Bypassing a subgraph node takes a code path we did not fully read.

## Sources

- [ComfyUI Nodes: Types, Inputs, and Outputs](https://docs.comfy.org/development/core-concepts/nodes)
- [Workflow JSON](https://docs.comfy.org/specs/workflow_json)
- [Workflow API Format](https://docs.comfy.org/development/api-development/workflow-api-format)
- [ComfyUI front end, src/utils/executionUtil.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/utils/executionUtil.ts)
- [ComfyUI front end, src/lib/litegraph/src/subgraph/ExecutableNodeDTO.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/lib/litegraph/src/subgraph/ExecutableNodeDTO.ts)
- [ComfyUI front end, packages/graph-model/src/globalEnums.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/packages/graph-model/src/globalEnums.ts)
- [ComfyUI front end, src/extensions/core/rerouteNode.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/extensions/core/rerouteNode.ts)
- [ComfyUI front end, src/extensions/core/noteNode.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/extensions/core/noteNode.ts)
- [ComfyUI front end, src/extensions/core/groupOptions.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/extensions/core/groupOptions.ts)
- [ComfyUI front end, src/platform/keybindings/defaults.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/platform/keybindings/defaults.ts)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
