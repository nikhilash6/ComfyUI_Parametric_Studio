# CU-100 - Your first graph, with no model at all

**Objective.** Open a graph, run it, and say what a node, a wire and an output node are. You need no model and no GPU. Taught by Captain Graph.

## The idea

ComfyUI has a reputation for needing a big graphics card and a pile of downloads. The graph itself needs neither. A graph is a small program, and some of its parts don't involve any AI at all, so you can learn the program first.

Here is the smallest useful one. `EmptyImage` makes a solid picture. `ImageInvert` flips its colours. `PreviewImage` shows the result. Three boxes, two wires.

{{graph:nm_first}}

Three ideas are hiding in that picture.

- A **node** is a function. It takes inputs and returns outputs.
- A **wire** carries one output to one input, and it has a type. This one carries `IMAGE`.
- An **output node** is the reason anything runs. `PreviewImage` is one. Take it away and the server refuses the graph.

## Wire it yourself

Now the real thing, with no shortcuts: the seven-node graph behind almost every image you have seen from ComfyUI. Each input wants one type, and the check here uses the real type of every socket.

{{play:wire}}

Notice what the types can't tell you. Both prompts send `CONDITIONING`, so nothing stops you plugging your negative prompt into the positive socket. The graph validates and runs, and the picture comes out wrong. Types catch a wire that is impossible. They don't catch one that is silly.

## What really happens when you press Queue

Before any node runs, the server checks the graph. It looks for output nodes, walks back along the wires from each one, and checks each input it finds. It also needs every required input to be present and every number to be in range. If no output passes, nothing runs and you get a list of errors. If you have two outputs and one passes, that one still runs (CU-290 shows this).

Then it runs nodes in an order that respects the wires. In the graph below, `ImageInvert` takes a wire in, but nothing takes its output, so it never runs, even though it's sitting right there on the canvas.

{{graph:nm_dead_branch}}

That one rule explains most of the surprises new users hit. A node with no path to an output is decoration.

## What goes wrong

- **"Prompt has no outputs."** You have no output node. Add `SaveImage` or `PreviewImage` at the end of the chain.
- **A node you added did nothing.** It has no path to an output. Follow its output wire: does it reach a save or preview?
- **Red outlines on a node after Queue.** That is validation failing on that node. Read the message: it names the input. CU-290 goes through every kind.
- **Nothing happened on the second Queue.** Nothing changed, so every result came from the cache. That is the engine doing its job. CU-102 shows how it decides.
- **The colour looks wrong.** The colour input is one number that packs red, green and blue together: `0xF5C518` is 245, 197, 24. Typed as an ordinary number it is 16,106,776.

## Lab

The lab does what these nodes do, with the same formulas, and adds the rule that decides what runs.

```text
EmptyImage 0xF5C518 -> shape (1, 4, 4, 3)  values 0.9608 0.7725 0.0941
ImageInvert         -> values 0.0392 0.2275 0.9059
run twice: same numbers: True
```

The shape is batch, height, width, channels. ComfyUI's images are numbers from 0 to 1 in that order, which CU-103 goes into.

```text
nodes on the canvas: 4   nodes that ran: 3   left idle: ['ImageInvert']
without an output node: nothing runs, the server says prompt_no_outputs
```

## Sources

- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/graph.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph.py)
- [ComfyUI front end, src/scripts/app.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/scripts/app.ts)
