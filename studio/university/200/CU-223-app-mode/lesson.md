# CU-223 - App Mode: a graph with a form on top

**Objective.** Explain what App Mode does and does not change, and choose a good set of fields for one. Taught by Captain Graph.

## The idea

A finished workflow may have dozens of settings, and the person using it may need three. App Mode shows chosen inputs and outputs as a simple page. The graph stays as it was.

So App Mode is not a new kind of workflow. Think of a form taped to the front of the machine. Each field reaches in and sets one value.

{{graph:sd15_txt2img}}

This seven-node graph has 13 settings that are plain values. The one you ship could show three.

## What the docs say

The [official guide](https://docs.comfy.org/interface/app-mode) describes App Mode as a way to define custom input and output interfaces, so people can use a workflow without editing nodes. It is officially supported from front-end version 1.41.13, and earlier versions are an early test.

You can enter it from the top-left menu or from the breadcrumb. If the workflow has never been set up, the builder opens. It has four steps:

1. **Select inputs.** Click highlighted nodes to turn their values into fields.
2. **Select outputs.** Choose which output nodes to show.
3. **Preview.** Check the layout.
4. **Set a default view.** Choose whether the file opens as an app or as a graph.

Save with Ctrl+S. The guide says share links work only on Comfy Cloud.

## What it is underneath

We read the front-end source on its main branch, at the commit in our sources list. Your installed version may differ.

- **It is saved with the workflow.** The file's `extra` part gets `linearMode` and `linearData`. `linearData` has an `inputs` list of a widget id and a name, with optional settings, and an `outputs` list of node ids.
- **Inputs are widgets, not wires.** A field points at one widget on one node. `nodeTypeValidForApp` keeps `Note` and `MarkdownNote` out.
- **The Run button queues the ordinary way.** `LinearControls.vue` runs the `Comfy.QueuePrompt` command, the same one the normal Run button uses.

So a run should go through `POST /prompt` and meet the same validation and the same cache as any other run. We read that from the code, but we did not watch a run in a browser. ComfyUI's Python code has no mention of `linearMode` or `linearData`, so the server does not treat an app differently. The form lives entirely in the page.

## Try it

Choose the fields. Each one shows what it costs when changed.

{{play:appform}}

## Lab

The lab acts out what a form has to do. It is our model, not the front end's code.

```text
the graph has 7 nodes and 13 widget values; the app shows 3 of them
values changed by the form: [('3', 'seed'), ('5', 'width'), ('6', 'text')]
wires changed by the form: 0
```

The form changes three values and no wires.

```text
width=768 valid: True   width=4 valid: False
```

A form does not remove the rules. If a field can take a value the node rejects, the user sees a validation error they may not understand.

Now what each field costs, with everything already cached:

```text
Describe the image    4 of 7
Seed                  3 of 7
Width                 4 of 7
File prefix           1 of 7
Checkpoint            6 of 7
```

A new seed re-runs the sampler and what follows. A new checkpoint re-runs nearly everything, and with a real model that means loading a file too.

```text
saved with the workflow: {"linearMode": true, "linearData": {"inputs": [["6", "text"], ["3", "seed"], ["5", "width"]], "outputs": ["9"]}}
the prompt graph holds it: False
```

The real saved ids can be longer widget ids, so read that line for its shape. The prompt graph has no trace of the form.

## Choosing fields

These are our recommendations, not rules from the docs:

- Expose what the user decides: the subject, the seed, the size. Hide what the author decided: sampler, schedule, model.
- A field near the end of the chain re-runs less than one near the start.
- If a setting only makes sense with another, expose neither until you have tested both together.
- Give the graph a sensible default for every hidden value. A person using the form can't reach it to fix it.

## What goes wrong

- **A validation error nobody understands.** A field accepted a value the node refuses, such as a width of 4. Test the extremes of each field yourself.
- **The app breaks after someone edits the graph.** A field points at a node and a widget. Delete the node and `pruneLinearData` in the store drops the field when the app loads, so the form quietly loses it. Check the form after any change.
- **Every run gives the same picture.** Nothing changed, so the cache answered. Show the seed, or leave it randomising.
- **"It is locked down now."** It isn't. Hiding a field hides it from the page. Anyone who can reach the server can still post any graph (CU-463).
- **A share link that won't make.** The guide says links are for Comfy Cloud. On your own machine, share the workflow file.

## Sources

- [ComfyUI docs: ComfyUI APP mode guide](https://docs.comfy.org/interface/app-mode)
- [ComfyUI front end, appModeStore.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/stores/appModeStore.ts)
- [ComfyUI front end, comfyWorkflow.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/platform/workflow/management/stores/comfyWorkflow.ts)
- [ComfyUI front end, LinearControls.vue](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/renderer/extensions/linearMode/LinearControls.vue)
- [ComfyUI front end, ComfyQueueButton.vue](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/components/actionbar/ComfyRunButton/ComfyQueueButton.vue)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
