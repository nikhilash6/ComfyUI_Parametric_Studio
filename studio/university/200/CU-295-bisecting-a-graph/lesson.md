# CU-295 - Bisecting a broken graph: previews are your print statement

**Objective.** Find the first bad node in a graph with as few checks as you can, and see what's really on a wire. Taught by Captain Graph.

## The idea

The worst bugs don't raise an error. The picture is just wrong. Don't stare at the whole graph, and don't change settings at random. Treat it like a leak in a long pipe: check the middle. If the water is clean there, the leak is downstream, and you can forget the first half. If it's dirty, forget the second half. Each check throws away half of what's left.

For a chain of 16 nodes, with the first known good and the last known bad, walking from the start takes up to 14 checks, and halving takes at most 4.

{{play:f_bisect}}

## Your probes

A node's output is invisible until something shows it. You have four good probes:

| To see | Use | It shows |
|---|---|---|
| A picture | `PreviewImage` | The image, with no file kept |
| A mask | `MaskPreview` | The mask |
| Anything | `PreviewAny` (shown as Preview as Text) | Text: numbers, strings, even tensors |
| A size | `GetImageSize`, `GetLatentSize` | Width, height, batch |

The three previews are output nodes, so wiring one in makes its branch run. The size nodes aren't: a graph with only `GetImageSize` at the end gets `prompt_no_outputs`, so wire a number from them into `PreviewAny`. A preview also turns "a node with no path to an output" into one that runs, which is useful when you are unsure whether a branch is doing anything at all.

This graph has a preview at the midpoint and a text probe at the end. Open it, and move the probes about.

{{graph:f_bisect_probes}}

## Reading text probes

`PreviewAny` wired to an image gives real numbers. This is a real result for a small image:

```
tensor([[[[0.1255, 0.1255, 0.1255],
          [0.1255, 0.1255, 0.1255]],

         [[0.1255, 0.1255, 0.1255],
          [0.1255, 0.1255, 0.1255]]]])
```

Four square brackets deep means four axes: batch, height, width, channels. Values should be 0 to 1. A latent comes out as a dict with `samples` and other fields. So this is the way to see a stray `noise_mask` or a batch index you didn't know about.

**The trap.** A big tensor is printed in short form, with `...` in the middle. One NaN in the middle of a 64 by 64 latent does not appear in the text. So a clean-looking probe doesn't prove a clean tensor. Luckily NaN spreads (CU-291), so a real fault fills the tensor soon after it starts. For wiring and numbers, it's enough.

## How to bisect

1. **Write down what's wrong in one sentence.** "The output is too dark." "The face is missing." You need a test you can apply at any probe.
2. **Find the middle.** Count the nodes on the path from the input to the bad output.
3. **Add a probe. Queue.** Thanks to the cache, only what changed runs, so this is cheap (CU-221).
4. **Good there?** The fault is later. **Bad?** It's earlier. Move the probe to the middle of what remains.
5. **Stop at the first bad node**, where its input looks right and its output doesn't. That is your node. Now look at its settings.

Things that help:

- **Fix the seed.** With a random seed, each run is a new picture and you can't compare. Use `fixed`.
- **Make it small and fast.** Lower the steps and size while you hunt, if the fault still shows.
- **Fewer branches.** On a graph with branches, cut one: bypass it or delete a wire, and see if the fault goes. A branch you can remove isn't the cause.
- **Keep what's good.** `SaveLatent` and `LoadLatent` let you skip an expensive sampler while you test what comes after.
- **Change one thing at a time.** Two changes and you can't tell which one did it.

## A graph with no error and no result

A node doing nothing is its own class of bug. Follow its output wire: does it reach an output? In this graph, `ImageInvert` looks busy and never runs.

{{graph:nm_dead_branch}}

## What goes wrong

- **You check the end again and again.** The end tells you only that it's wrong, which you knew. Go to the middle.
- **The probe ran, and shows an old result.** Nothing upstream changed, so it came from the cache. That is correct. If you think something did change, ask whether it reached this node.
- **The seed moved between probes.** `control_after_generate` set to random gives a new image each queue. So what you see differs, and it isn't due to your probe.
- **A preview hides the fault.** A preview shows pixels. It can't show a mask's shape, a value range, or conditioning. Use a text probe for those.
- **PreviewAny on a model or a CLIP.** It prints whatever the object says about itself, which tells you little. Probes work best on images, latents, numbers and text.
- **A probe changes what runs.** It adds an output, so a dead branch starts running. That's what you want while hunting, but delete probes afterwards, because they cost time.
- **A wire that looks right.** Positive and negative can be swapped with no error, and a type check won't help. A text probe on the prompts, or a look at where each wire goes, will.
- **The fault only comes with the whole graph.** Then it's an interaction, such as memory. Halve by removing branches, not by probing.

## Lab

The lab counts the checks, walking and halving, on a chain where node 0 is fine and the last is bad:

```text
chain length   walking: worst, average    halving: worst
8              6       3.9              3
16             14      7.9              4
32             30      16.0             5
64             62      32.0             6
```

Then the text trap. `PreviewAny` sets `edgeitems=6` and calls `str`, so the lab does the same:

```text
small latent         one NaN in the middle: the word nan appears in the text: True   ('...' summary: False)
512 by 512 latent    one NaN in the middle: the word nan appears in the text: False   ('...' summary: True)
512 by 512 latent    one NaN in a corner: appears: True
512 by 512 latent    all NaN: appears: True
```

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_preview_any.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_preview_any.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
