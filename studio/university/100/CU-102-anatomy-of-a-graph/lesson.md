# CU-102 - Anatomy of a ComfyUI graph

**Objective.** Read a graph as a program: say what a node, a typed wire and an output node are, work out which nodes will run, and predict which results come from the cache when you change one value. Taught by Captain Graph.

## The idea

To the engine, a workflow is a chart of dependencies and nothing else. Each node is a function, and each wire carries one result from an output socket of one node to an input socket of another. Every wire has a type, such as MODEL, CLIP, VAE, CONDITIONING, LATENT or IMAGE. The editor generally refuses to join sockets of different types, and the server checks again when it receives the graph.

Two rules explain most of what you see in the queue.

- Nothing runs unless an output node needs it. `SaveImage` and `PreviewImage` are output nodes, and a branch that leads to neither is never started.
- A node runs only after everything wired into it has arrived, and it is skipped when the same job has already been done.

## The mechanism

**Order.** For every waiting node, count the inputs that have not arrived yet. A node whose count is zero is ready. Run one ready node, lower by one the count of every node that was waiting for it, and repeat. If nodes are still waiting and none is ready, they are waiting for each other: a cycle. This counting form of topological sorting is usually credited to Kahn (1962).

The order is not unique. Any order that respects the wires is correct, and the lab counts 8 of them for its 7-node graph. ComfyUI does not search for the best one. It takes a ready node by a simple rule: an output node first, then a node that leads to one, then the first ready node.

**Memory.** A node's result is stored under a key made of three things: the node's class, its constant inputs, and the same description of every node upstream of it. A wire is written as "the k-th ancestor, output slot s", not as a node id.

```
key(n) = [ own(n), own(a1), own(a2), ... ]      a1, a2, ... are the ancestors of n, in a fixed order
own(x) = class of x, its constant inputs, and for each wire: which ancestor and which output slot
```

Two things follow. Change a value and every node with that value upstream gets a new key, while nodes on other branches keep theirs. And because node ids are not in the key, renumbering the nodes changes nothing.

## In ComfyUI

The server receives the graph as a dict from node id to `class_type` and `inputs`. A constant is a plain value, and a wire is a two-item list: source id and output slot. `validate_prompt` in `execution.py` collects the nodes whose class sets `OUTPUT_NODE`, and `validate_inputs` walks upstream from each of them. It reports `required_input_missing`, `return_type_mismatch` and, in v0.43.0, `dependency_cycle`, all before any node runs. A graph with no output node fails with `prompt_no_outputs`. Despite its name, `validate_loops` in `comfy_execution/validation.py` is for the loop-start and loop-end nodes, not for accidental cycles.

`PromptExecutor.execute_async` hands each output node to `ExecutionList.add_node`, which walks upstream and stops at any node whose result is already cached. `TopologicalSort` keeps `blockCount` and `blocking`, the counts and the lists of waiting nodes from the mechanism above. `ux_friendly_pick_node` makes the choice among ready nodes, and a comment in the source marks that rule as unfinished. The editor is told which nodes were served from the cache by an `execution_cached` message.

`CacheKeySetInputSignature` builds the key. Besides the class and the inputs it includes whatever a node's `IS_CHANGED` hook returns. `LoadImage` returns a SHA-256 of the file, so editing the file on disk changes its key. `CheckpointLoaderSimple` has no such hook, so its key rests on the file name alone. The node id enters the key only for classes that set `NOT_IDEMPOTENT` or take the `UNIQUE_ID` hidden input.

How long results stay is a launch option, chosen in `main.py` from flags in `comfy/cli_args.py`. The default keeps results until system RAM runs short. `--cache-classic` keeps only what the latest graph used, `--cache-lru N` keeps N results, and `--cache-none` runs every node every time. One more trap is the seed widget's "control after generate" setting. The KSampler documentation lists Random, Inc, Dec and Keep, and with a random choice the seed changes after each queue, so the KSampler and everything after it run again every time.

## Lab

The lab is a small engine that follows these rules on the classic seven-node text-to-image graph, plus an eighth node wired to nothing. No model runs, and every result is a label, so you can check each count by hand. Each row changes one more thing than the row above it, and the cache keeps what the earlier rows stored.

```text
nodes that feed the output: 7 of 8   valid execution orders: 8
```

The node numbers are 1 checkpoint loader, 2 positive prompt, 3 negative prompt, 4 empty latent, 5 KSampler, 6 VAEDecode, 7 SaveImage, 8 the unconnected latent.

```text
what                                  ran              found in cache                    not needed
first run                             1 4 3 2 5 6 7    -                                 8
same prompt again                     -                1 2 3 4 5 6 7                     8
seed 42 -> 43                         5 6 7            1 2 3 4                           8
positive text changed                 2 5 6 7          1 3 4                             8
checkpoint file name changed          1 3 2 5 6 7      4                                 8
latent 512 -> 768 wide                4 5 6 7          1 2 3                             8
second SaveImage added                9                1 2 3 4 5 6 7                     8
every node id renumbered (+100)       -                101 102 103 104 105 106 107 109   108
```

Read it row by row.

- The first run starts seven nodes and never touches node 8, which no output needs.
- Changing the seed re-runs the KSampler and the two nodes after it. The four nodes before it are found in the cache.
- Changing the checkpoint re-runs six nodes, not seven. Node 4, the empty latent, has no wire from the loader, so its key did not change. Editing the first node in the chain does not always re-run everything.
- A second output node costs one run, because the result it needs is already stored.
- Renumbering every node runs nothing, because the key never contained the ids.

The same lab checks the graph before running it.

```text
CLIP wire into the MODEL socket    return_type_mismatch  |  Return type mismatch between linked nodes: model, received_type(CLIP) mismatch input_type(MODEL)
two samplers feeding each other    dependency_cycle  |  Dependency cycle detected: 5 (KSampler) -> 10 (KSampler) -> 5 (KSampler)
KSampler without latent_image      required_input_missing  |  Required input is missing: latent_image
no output node                     prompt_no_outputs  |  Prompt has no outputs
```

These are the error names and wording `validate_prompt` uses. The real function also checks value ranges and list membership, which the lab skips.

## What the lab leaves out

The lab handles eager nodes only. Real nodes can be lazy, run asynchronously, or expand into a subgraph while they run, and then both the order and the cache are more involved (CU-220 and CU-221 return to this). The "found in cache" column describes a cache that never evicts, and under `--cache-none` every row would show every needed node running. The order the lab prints is its own choice, so do not read it as the order ComfyUI would use.

## Sources

- [Kahn 1962. Topological sorting of large networks](https://doi.org/10.1145/368996.369025)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/graph.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph.py)
- [ComfyUI v0.43.0, comfy_execution/caching.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/caching.py)
- [ComfyUI v0.43.0, comfy_execution/validation.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/validation.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI Custom Node Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes)
- [ComfyUI Server Routes (HTTP and WebSocket API)](https://docs.comfy.org/development/comfyui-server/comms_routes)
- [KSampler - ComfyUI Built-in Node Documentation](https://docs.comfy.org/built-in-nodes/KSampler)
