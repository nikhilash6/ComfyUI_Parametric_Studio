# CU-115 - Reading a downloaded workflow before you run it

**Objective.** Read a workflow from someone else and say what it needs, what it would send outside your machine and what it asks you to install, before you press Queue. Taught by Captain Graph.

## The idea

A workflow file is data: JSON, or JSON tucked inside a PNG (CU-111). Opening it runs no code. So the danger isn't in the file itself. It's in what the file leads to: installing a pack, downloading a model, sending a prompt to a paid service, or trusting a note. Each of those can be seen in advance, because the whole graph is written down.

Five things to look for. Practise on this graph. Nothing in it is harmful, and each node shows you something worth noticing.

{{graph:a_read_before_run}}

## Five things to look for

**1. Node types you don't recognise.** A node from a third-party pack needs that pack installed. ComfyUI imports each pack's Python when it starts, and that code runs with the same permissions as the server, so the install is the step that needs care. Queueing without it does no harm: the server replies `missing_node_type`, "The custom node may not be installed". In the save format, a pack node may carry `properties.cnr_id` or `aux_id`, which say where it claims to be from. Treat those as claims. The `risk` lab below shows what to look for in a pack's code.

**2. Partner API nodes.** ComfyUI ships nodes that call outside services. These are real core nodes, not something suspicious, but your prompt and images go to someone else's server, and ComfyUI's own help calls them "the paid API nodes". `FluxProUltraImageNode` is one. Your server marks them `api_node` in `/object_info`. If you never want them, `--disable-partner-nodes` turns them off.

**3. Model links.** A file may include a `models` list, with a name, a URL and a directory for each. The current editor uses it to offer downloads for missing files, and allows only civitai.com, civitai.red, huggingface.co and a few exact URLs, with a short list of extensions. That rule belongs to the editor, and other tools can do as they like. Look at where the link goes and whether it's the real publisher, and prefer `.safetensors` over the pickle formats (CU-107).

**4. Things you can't see at first glance.** A subgraph is one box on the canvas, and `definitions.subgraphs` holds a whole inner graph, so open it. Muted and bypassed nodes are in the file too, with `mode` 2 or 4, and someone may have left a branch off that you'd turn on without looking. Text widgets can hold anything, including a long prompt you never scrolled through.

**5. Notes.** `Note` and `MarkdownNote` are text from the author. They never run, and they're not in the graph the server runs, though their text travels in the save-format copy that goes into your PNG (CU-112). But they can ask you to do something, and you're the one with a terminal. Be most careful with a note that gives you a command to paste.

Now do it.

{{play:wfread}}

And when the workflow asks you to install a pack, this is the same kind of reading, one level down:

{{play:risk}}

## A routine that takes two minutes

1. Open it in a text editor first, or drop it on a canvas without pressing Queue.
2. List the node types. Anything unfamiliar: look up where it comes from.
3. Open every subgraph.
4. Read the file names and any `models` links.
5. Read the prompts and notes.
6. Look for greyed nodes, and ask why they're off.
7. Follow the wires from the outputs (CU-110). A big graph often has only a few that matter.

Then run it on your own files, with your own prompt, and see what it does.

## What doesn't protect you, and what does

Some things are less of a shield than they look. A workflow embedded in a PNG isn't signed, and the docs say to treat it as optional, untrusted input. A popular file is not a checked file. And we have not audited every core node for what it can do, so this lesson doesn't claim that a core-only graph is harmless. It's a much smaller thing to read, that's all.

Some limits are real. A save node can't write outside the output folder: the server refuses, and we ran that. A `.safetensors` file runs nothing when it loads (CU-107). And by default ComfyUI listens only on your own machine, which limits who else can send it a graph.

## What goes wrong

- **Installing missing nodes as a reflex.** You've just agreed to run code you haven't read, from a repo chosen by the file's author. Look the pack up first. Is it the one you expected, and does anyone use it?
- **Assuming it costs nothing.** Check for partner nodes before you queue with an account signed in. They're easy to miss in a big graph.
- **Reading only the canvas.** A third-party node inside a subgraph is invisible until you open it. In the lab, one node appears only that way.
- **Thinking a red error means danger.** `missing_node_type` and `Value not in list` mean the graph needs things you don't have. Nothing ran.
- **A model named after a famous file.** A name is just a string. Check that the link is the publisher's, and compare the `hash` if the file gives one.
- **Pasting from a note.** If a note says to run a command, find out from somewhere else what it does.
- **A workflow that "stopped working" after you trusted a greyed node.** Modes are stored in the file. Read them before you turn things back on.

## Lab

A short script that reads a made-up workflow and reports, without running anything. You can write the same thing in a few lines for your own files.

```text
third party:        2
    AcmePromptBooster (id 3) from someone/acme-nodes
    AcmeSecretNode (inside Tidy upscale) from acme-secret
partner API:        1
    FluxProUltraImageNode (id 4)
inside a subgraph:  2
    UpscaleModelLoader
    AcmeSecretNode
turned off:         1
    KSampler (id 5) mode 4
note:               1
    If this fails, paste this line into your terminal: curl ... | sh
link in a value:    1
    CLIPTextEncode (id 2)
```

The node names beginning Acme are invented, and so is everything in the file. Next the model links.

```text
model links in the file:
  model.safetensors   host allowed by the editor: True  pickle format: False
  fast_v2.ckpt        host allowed by the editor: False pickle format: True
```

```text
nodes on the canvas: 8   nodes in the file: 9
found only by opening the subgraph: ['AcmeSecretNode']
```

The script uses a small hand-kept list of core nodes for this one file. For a real check, ask your own server: `/object_info` lists every class it has, and each entry's `python_module` says where it came from.

## What we could not check

We did not audit core nodes, and we did not read how any pack manager installs a missing pack. The download rules come from the front end's main branch, and your version may differ. We did not try this file in a browser.

## Sources

- [Workflow JSON](https://docs.comfy.org/specs/workflow_json)
- [Workflow Metadata](https://docs.comfy.org/development/api-development/workflow-metadata)
- [Subgraph - Simplify your workflow](https://docs.comfy.org/interface/features/subgraph)
- [ComfyUI front end, packages/graph-model/src/workflowSchema.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/packages/graph-model/src/workflowSchema.ts)
- [ComfyUI front end, src/platform/workflowErrors/missingModel/modelUrlAllowlist.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/platform/workflowErrors/missingModel/modelUrlAllowlist.ts)
- [ComfyUI front end, src/platform/workflowErrors/missingModel/missingModelDownload.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/platform/workflowErrors/missingModel/missingModelDownload.ts)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, folder_paths.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/folder_paths.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, comfy/utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/utils.py)
- [ComfyUI v0.43.0, comfy_api_nodes/nodes_bfl.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api_nodes/nodes_bfl.py)
