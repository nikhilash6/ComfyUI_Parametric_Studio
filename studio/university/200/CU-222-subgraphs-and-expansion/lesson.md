# CU-222 - Sub-graphs and node expansion

**Objective.** Tell the two apart: one is a front-end packaging feature, the other lets a node create nodes while the prompt runs. Taught by Captain Graph.

## The idea

**A sub-graph** packages nodes into one reusable node on the canvas. The docs compare it to a folder. **Node expansion** lets a running node return new nodes for the engine to run.

They look related, and they work in different places, at different times.

| | Sub-graph | Expansion |
|---|---|---|
| Who made it | You, in the editor | A node's Python |
| Where it lives | In the workflow file | Only in the running prompt |
| When it becomes real nodes | Before the prompt is sent | While the prompt runs |
| Does the executor know? | No | Yes |
| Does the canvas change? | It shows one box | Nothing appears |
| Can it decide the count at run time? | No | Yes |

So if you want to tidy your canvas, use a sub-graph. If you want a loop, or a node whose shape depends on data, that takes expansion.

## The mechanism

**Sub-graphs.** A saved workflow keeps definitions in `definitions.subgraphs`, each with a UUID, its own nodes and links, and input and output lists. The blueprints folder of ComfyUI holds real examples. `SubgraphManager` in `app/subgraph_manager.py` serves such files, and that is its job. Inner nodes run under compound execution ids such as `1:2:3`, per the Subgraph Developer Guide.

The sub-graph node itself can't reach the executor: `validate_prompt` rejects any `class_type` that isn't in `NODE_CLASS_MAPPINGS`, and a UUID type isn't there. So the front end must flatten it first, and its `graphToPrompt` does, walking each node's inner nodes. We read that on the front end's main branch, and did not test it by hand.

**Expansion.** A node returns `{"result": ..., "expand": graph}`. V3 nodes use `io.NodeOutput(..., expand=graph)`, and the schema must flag the node as expandable. In `execute` in `execution.py`:

1. each new node goes into `dynprompt.add_ephemeral_node`, with this node as its parent
2. new output nodes and the links in the result are added to the `ExecutionList`
3. the node stores its pending result in `pending_subgraph_results` and returns PENDING
4. once the new nodes finish, the parent is visited again and resolves the links into values

`GraphBuilder` in `comfy_execution/graph_utils.py` writes such a graph, and prefixes ids with the parent id so that repeated runs stay unique. The name `pending_subgraph_results` is older than the front-end feature, which is a common source of confusion. It has nothing to do with sub-graphs in the editor.

Try it: move the slider and see the nodes appear. CU-435 shows how to write one.

{{play:f_expand}}

## See one of each

Core's Start Loop is built on expansion. A graph can't have a cycle, so it adds a copy of the loop body per pass while running. In a run on a CPU, this inverted a picture three times. Our no-server checker can only validate this one, because Start Loop reports progress through the running server.

{{graph:f_core_loop}}

For a sub-graph, open this small graph, select two nodes and convert them to a sub-graph in the editor. It should run the same as before. We didn't test that by hand.

{{graph:nm_first}}

## What goes wrong

- **Looking for `pending_subgraph_results` to debug your sub-graph.** Wrong feature. That's expansion.
- **A node inside a sub-graph is reported with a strange id.** `5:2` is the inner node's compound id. Open the sub-graph to find it. Errors name that id.
- **An API client sends a sub-graph node.** A UUID in `class_type` gives `missing_node_type`. Use "Export (API)", which gives a flat graph, or expand it yourself.
- **A sub-graph doesn't save time.** It's only packaging, and each inner node caches and runs as if the box weren't there.
- **You expect a loop from a sub-graph.** It can't. Its nodes are fixed when you queue.
- **An expansion fails partway.** Validation doesn't check nodes created later, so a bad class name fails mid-run (CU-435).
- **The canvas doesn't show the new nodes.** That's normal for expansion. They exist only during the run.

## Lab

```text
the server sees 4 nodes and no sub-graph node at all
```

The lab's flatten step is our own small version of what the front end must do. It turns one instance into its inner nodes with ids `5:2` and `5:3`, and rewires the links crossing the boundary. Then a node that expands:

```text
expansion: result 13  nodes after running: ['a', 'r', 'r.0.0.1', 'r.0.0.2', 'r.0.0.3']  parents: {'r.0.0.1': 'r', 'r.0.0.2': 'r', 'r.0.0.3': 'r'}
functions that ran: ['Const', 'AddOne', 'AddOne', 'AddOne']
the same node with times=50: result 50 , graph grew to 52 nodes
```

A graph has no loops, but a node can decide at run time how many steps to create, so loops can be written this way. The lab is a simplified copy, with recursion in place of the real list. The id form `r.0.0.1` follows the real `GraphBuilder`: parent id, call index, builder index, then a counter.

## Sources

- [ComfyUI docs: Subgraph](https://docs.comfy.org/interface/features/subgraph)
- [ComfyUI docs: Subgraph Developer Guide](https://docs.comfy.org/custom-nodes/js/subgraphs)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/graph_utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph_utils.py)
- [ComfyUI v0.43.0, app/subgraph_manager.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/app/subgraph_manager.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_loop.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_loop.py)
- [Node Expansion, ComfyUI docs](https://docs.comfy.org/custom-nodes/backend/expansion)
