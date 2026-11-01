# CU-220 - The execution model: what runs, and in what order

**Objective.** Predict which nodes run and in what order, and read a validation error by its type. Taught by Captain Graph.

## The idea

A graph doesn't run from left to right. ComfyUI starts at the output nodes and works backwards through the links, so a node nothing depends on never runs. Data flows forward, but the demand for data flows backward.

That one fact explains a lot of odd behaviour. Where a node sits on the canvas means nothing. A node with no path to an output does nothing, however busy it looks.

{{graph:nm_dead_branch}}

## The mechanism

These steps are read from `execution.py` and `comfy_execution/graph.py` at v0.43.0.

1. **Validate.** `validate_prompt` checks every `class_type` is known and collects the nodes marked as outputs. No outputs means `prompt_no_outputs`. It then walks back from each output and checks required inputs, link types, value ranges and cycles. CU-290 lists each error.
2. **Partial success is allowed.** An output whose ancestors are invalid is dropped, and the rest still runs. The prompt only fails if no output survives. We ran this: of two previews, the good one ran and the bad one was reported.
3. **Build the list.** `ExecutionList` extends `TopologicalSort`. Each pending node has a count of the nodes still blocking it.
4. **Dissolve.** Take a node with count 0, run it, and subtract 1 from everything it blocks.
5. **Pick kindly.** `ux_friendly_pick_node` prefers an output or an async node, then something feeding an output directly, then one link away, so previews appear early. The comment there says this doesn't change total time.
6. **Stop at the first failure.** If a node raises, the loop breaks. Nodes that haven't run don't run, but results already finished stay in the cache, so the next queue picks up from there.

## Three ways a node's turn can end

`execute` returns one of three results (`ExecutionResult`):

- **SUCCESS**: it ran, or came from the cache.
- **FAILURE**: it raised. You get an `execution_error` holding the node, the exception and the traceback.
- **PENDING**: it isn't finished. It goes back in the list, to be visited again.

PENDING happens in three cases: a lazy input was requested, the node expanded into new nodes (CU-435), or an async task is running.

## Lazy inputs

**Lazy inputs** change the shape of this. A lazy input creates no link at first. The node is staged, `check_lazy_status` returns the names it now needs, `make_input_strong_link` adds those as blockers, and the node goes back in the list. So a node may be visited twice, and a branch nobody asks for never runs.

Step through it:

{{play:f_lazy}}

Core's If/Else Switch works this way. Change `switch` and only one branch runs.

{{graph:f_lazy_switch}}

`ExecutionBlocker` is the blunt version. A node can return one, and whatever depends on that output is stopped. With a message it's reported as an error. With `None` it's silent: in our run, a downstream node never ran, and the prompt still counted as a success. The docstring recommends lazy inputs where they can do the job. CU-432 covers writing them.

## What goes wrong

- **A node didn't run, and there's no error.** It has no path to an output. Follow its wire.
- **Only some of your outputs appeared.** A validation error dropped the rest. Read the console, or `node_errors` in the reply.
- **You expect a left-to-right order.** The order is whatever the wires allow, with outputs first among ready nodes. Don't write nodes that count on anything else, such as one node writing a file another reads with no wire between them.
- **The side effect happens too late, or not at all.** Same cause. If node B needs something A does, wire A to B.
- **A run stops and later nodes are skipped.** A node failed. Read the error for that node, not the last one you see in the graph.
- **Nothing happens on queue.** Everything came from the cache. That is the engine working (CU-221).
- **A node appears to run twice.** It's a lazy or expanding node, on its second visit. Your function ran once.

## Lab

A small copy of the scheduler, in plain Python.

```text
order: ['1', '2', '3', '4']  ran: ['Load', 'Text<a fox>', 'Sample', 'Save']
```

Node 9 exists in the graph and didn't run, because it feeds nothing. The validation errors have the same names the server uses:

```text
no output node: prompt_no_outputs
wrong type on a link: return_type_mismatch: node 4 input latent wants LATENT, got COND
cycle: dependency_cycle: 4 -> 1 -> 2 -> 1
unknown class: missing_node_type: Nope
```

Now a switch with two expensive branches:

```text
lazy switch, use_a=True  order: ['7?', '1', '2', '3', '7', '8']
lazy switch, use_a=False order: ['7?', '1', '5', '6', '7', '8']
the same graph without lazy inputs: ['1', '2', '3', '5', '6', '7', '8'] (2 sampler runs)
```

`7?` marks the first visit, where the switch asks for its branch and goes back into the list. Lazy inputs save one full sampler run here.

The lab leaves out caching (CU-221), async nodes and `ExecutionBlocker`.

## Sources

- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/graph.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph.py)
- [ComfyUI v0.43.0, comfy_execution/graph_utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph_utils.py)
