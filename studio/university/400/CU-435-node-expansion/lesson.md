# CU-435 - Writing a node that expands into a subgraph

**Objective.** Write a node that returns new nodes, keep their ids stable, and predict how it fails. Taught by Captain Graph.

## The idea

A normal node gets values and returns values. An **expanding** node can return a small graph as well: "run these, and my output is what that one produces". The engine adds those nodes to the running prompt, runs them, and comes back.

Your canvas doesn't change. The new nodes exist only during the run.

Why do this? A graph can't have a cycle, but a node can decide at run time how many steps to add. So this is how loops work. It also lets one friendly node stand in for a chain of smaller ones, each cached separately. CU-222 explains how this differs from the sub-graphs you see in the editor. This lesson is about writing one.

## How to write one

```python
from comfy_execution.graph_utils import GraphBuilder

class Repeat(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="RepeatInvert", category="university",
            enable_expand=True,                # V3 needs this
            inputs=[io.Image.Input("image"), io.Int.Input("times", default=3, min=1)],
            outputs=[io.Image.Output()])

    @classmethod
    def execute(cls, image, times):
        g = GraphBuilder()
        last = None
        for _ in range(times):
            last = g.node("ImageInvert", image=last.out(0) if last else image)
        return io.NodeOutput(last.out(0), expand=g.finalize())
```

In V1, return a dict: `{"result": (last.out(0),), "expand": g.finalize()}`.

Three things to notice.

- `g.node` takes a class name and inputs. An input can be a value, or `.out(n)` of another new node, which gives a wire.
- The result you return is a **wire** to the new node, not a value. The engine resolves it once that node has run.
- `image` is a real tensor here, and it goes straight into the new node's inputs as a value.

## What the engine does

From `execute` in `execution.py`:

1. Your function returns. Each new node is added with `dynprompt.add_ephemeral_node`, with your node as its parent.
2. New output nodes, and the wires in your result, are added to the schedule.
3. Your node is put in `pending_subgraph_results`, and returns `PENDING`.
4. The new nodes run. Your node is visited again, and the wires become values.

In our real run with `times=3`, on a picture with mean 0.1255:

```
new node ids:  2.0.0.1  2.0.0.2  2.0.0.3
result mean:   0.8745
```

The second queue ran nothing, because every part was cached.

{{play:f_expand}}

## Ids must be stable

The docs ask for two things: ids must be unique across the graph, and they must be the same from one run to the next. `GraphBuilder` handles both. Its prefix is `parent.call.builder.`, and the engine sets the first two before each call.

- `2.0.0.` is node 2, first call, first builder.
- `2.1.0.` is node 2, second call. A list input calls you more than once.
- `2.0.1.` is a second `GraphBuilder` in the same call.

Don't use random ids or a global counter. A new id means a new key, and the cache for those inner nodes never hits.

## A real one to read

Core's Start Loop and End Loop in `comfy_extras/nodes_loop.py` are built on this. In a run on a CPU, with a small stub for the server object it reports progress to, this graph ran the loop body three times. Start Loop also reaches into the running engine through hidden inputs (`dynprompt`, `execution_list`), which you should leave alone until you need them.

{{graph:f_core_loop}}

One thing to know if you test it yourself: validation writes notes about the loop into the prompt object, so run the same object you validated. A fresh copy fails with `KeyError: '_loop_body'`. That caught us out.

## What goes wrong

- **`Node X is not expandable, but expand included in NodeOutput`.** Add `enable_expand=True` to your V3 schema. V1 has no such flag.
- **`KeyError: 'NoSuchNode'`, mid-run.** A class name is misspelled, or its pack isn't installed. Validation only sees the graph you queued, not what you create later, so this reaches the user as a failure in the middle of the run. Check the names yourself in a test (CU-438).
- **The inner nodes re-run whenever your node does.** A second queue with nothing changed runs nothing, as above. But when your node runs again, inner nodes that hold a tensor as a value can't reuse their results: changing `times` from 3 to 4 ran 3 inverts and then 4 more in our run. Changing ids do the same. The docs suggest passing wires where you can, with `rawLink` on the input in V1 or `raw_link=True` in V3.
- **Hundreds of nodes.** Each one has its own cache entry and its own progress events. If the steps are simple, a plain loop in Python inside one node is cheaper.
- **Progress shows on the wrong node.** New nodes display under your node by default: `execute` uses `override_display_id` if set, and your id if not. Call `set_override_display_id` on a node from `GraphBuilder` to show it elsewhere.
- **Your node appears to run twice.** That is the second visit in step 4. Your function isn't called again, but the node is visited again.

## Lab

The lab ports `GraphBuilder`'s id rule on a much simplified engine with a stand-in for `ImageInvert`. The ids and the result match our real run.

```text
times=3, picture mean 0.1255
  node 2 added: ['2.0.0.1', '2.0.0.2', '2.0.0.3']
  result 0.8745  inverts that ran: 3
```

Six inverts bring back the original value:

```text
  result 0.1255  inverts that ran: 6
```

The prefixes change with the call and the builder:

```text
  node 2 added: ['2.1.0.1', '2.1.0.2']
   2.0.0. 2.0.1.
```

And an unknown class fails with the error the real engine gave:

```text
a class that does not exist: KeyError: 'NoSuchNode'
```

## Sources

- [Node Expansion, ComfyUI docs](https://docs.comfy.org/custom-nodes/backend/expansion)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/graph_utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph_utils.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_loop.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_loop.py)
- [ComfyUI v0.43.0, comfy_api/latest/_io.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_io.py)
