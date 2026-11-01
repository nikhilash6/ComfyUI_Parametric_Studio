# CU-432 - Lazy inputs and check_lazy_status

**Objective.** Make a node that asks only for the inputs it will use, and read what the engine does on each visit. Taught by Captain Graph.

## The idea

Normally every wire into a node is finished before the node starts. That is wasteful for a switch. If you are going to use branch A, you don't want to wait for branch B's sampler.

A **lazy** input is a wire the engine doesn't follow until your node asks for it.

## How to write one

Two steps. Mark the input, and add a function that says what you need.

```python
class Switch(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="MySwitch", category="university",
            inputs=[
                io.Boolean.Input("use_a", default=True),
                io.Image.Input("a", lazy=True),
                io.Image.Input("b", lazy=True),
            ],
            outputs=[io.Image.Output()])

    @classmethod
    def check_lazy_status(cls, use_a, a=None, b=None):
        return ["a"] if use_a else ["b"]

    @classmethod
    def execute(cls, use_a, a=None, b=None):
        return io.NodeOutput(a if use_a else b)
```

In V1, add `{"lazy": True}` to the input options, and write `check_lazy_status` as an ordinary method with `self`.

A wired input that hasn't been computed arrives as `None`. An optional input with no wire isn't passed at all, so that one needs a default. The defaults on required inputs here are only a habit: the same node with none ran fine.

## What the engine does

This is the order from a real run, on a CPU, with a small counting node on each branch.

```
check_lazy_status   a=None    b=None     returns ['a']
branch A runs
check_lazy_status   a=value   b=None     returns ['a']
execute             a=value   b=None
```

Step by step, from `execute` in `execution.py`:

1. The node is picked to run, though its lazy inputs aren't ready.
2. The engine calls `check_lazy_status`.
3. It throws away any name that already has a value. If nothing is left, it runs `execute`.
4. For each name still needed, `make_input_strong_link` adds a real wire to the schedule. The result is `PENDING`, and the node goes back in the list.
5. The branch runs. The node comes round again, and step 2 repeats.

So your check runs at least twice when it asks for something. Keep it cheap, and don't count on how many times it runs. Notice that it returned `['a']` on the second visit too, which is fine: names that already have a value are ignored.

Walk through it yourself, then turn lazy off to compare.

{{play:f_lazy}}

## A real one to read

Core has one. `ComfySwitchNode`, shown as If/Else Switch, lives in `comfy_extras/nodes_logic.py`. Its two branches are optional and lazy. Flip `switch` in this graph. In our run with `switch` on, `ImageInvert` ran once, and with it off, `ImageInvert` did not run at all.

{{graph:f_lazy_switch}}

It uses one more trick. `MISSING` is a default it can tell apart from `None`, so "this input isn't wired" looks different from "this input hasn't run yet". Only the second should be asked for. You want the same care: if a lazy input can be unwired, handle that case.

## Lazy or ExecutionBlocker

A node can also return an `ExecutionBlocker`, which stops everything downstream of that output. With a message it reports an error, and with `None` it stops silently. The docstring in `graph_utils.py` says to avoid it where you can, and the docs agree: use lazy when you want to skip part of a graph. A blocker can't be stopped once it is flowing. Lazy never starts the work.

## What goes wrong

- **`Node 5 says it needs input a, but there is no input to that node at all`.** Your check asked for an optional input nobody wired. The whole prompt stops there. Ask only for inputs that exist: give the check a default you can test, like core's `MISSING`.
- **`Required input is missing`, on a lazy input.** Lazy changes when a wire runs, not whether it must exist. If it can be absent, make it optional too. Core's switch is both.
- **Both branches run anyway.** You forgot `lazy=True` on one, or your check returns both names every time, or an ordinary input of your node depends on that branch. A second path into the branch from another node will also run it.
- **`NoneType has no attribute` inside `execute`.** You used an input you never asked for. It is `None` unless your check named it.
- **A check that does heavy work.** It runs more than once. Read flags, not tensors.
- **The result doesn't update when you flip the switch.** Check that the switch value reaches your node's key: it's a normal input, so it should re-run. If another node feeds it, look there (CU-221).

## Lab

The lab is a stand-in for the engine with made-up classes. It isn't ComfyUI, but the order of events matches the real run above.

```text
Switch, use_a=True: result A
    check_lazy_status a=None b=None
    branch A runs
    check_lazy_status a=value b=None
    execute
```

The same graph with ordinary inputs pays for both branches:

```text
Eager, use_a=True: result A
    branch A runs
    branch B runs
    execute
```

And a check that asks for something that isn't wired, with the wording of `make_input_strong_link`:

```text
asks for an input with no wire: Node S says it needs input a, but there is no input to that node at all
```

## Sources

- [Lazy Evaluation, ComfyUI docs](https://docs.comfy.org/custom-nodes/backend/lazy_evaluation)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/graph.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph.py)
- [ComfyUI v0.43.0, comfy_execution/graph_utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph_utils.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_logic.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_logic.py)
