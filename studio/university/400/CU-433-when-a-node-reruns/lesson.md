# CU-433 - When a node re-runs: fingerprints, the NaN trick, not_idempotent

**Objective.** Make a node re-run exactly when it should, and refuse bad values before the graph starts. Taught by Captain Graph.

## The idea

CU-221 showed that a node's cache key is built from its class, its inputs and everything upstream. Most nodes need nothing else. Three hooks exist for the rest:

- **A fingerprint** adds something the key can't see, such as a file's contents.
- **not_idempotent** says two copies of this node shouldn't share a result.
- **validate_inputs** rejects values before the graph starts.

| Job | V3 | V1 |
|---|---|---|
| Fingerprint | `fingerprint_inputs` classmethod | `IS_CHANGED` classmethod |
| Don't share between copies | `not_idempotent=True` in the schema | `NOT_IDEMPOTENT = True` |
| Check values | `validate_inputs` classmethod | `VALIDATE_INPUTS` classmethod |

## A fingerprint is a value, not an answer

The old name misleads people. `IS_CHANGED` doesn't answer yes or no. Whatever it returns joins the key, and the node runs if the key is new. So returning `False` every time means "nothing changed", and returning `True` every time means the same thing.

Here is what we measured: one node, three queues, nothing else changing, real engine.

| The hook returns | Runs in 3 queues |
|---|---|
| no hook | 1 |
| `False` | 1 |
| `None` | 1 |
| the same dict or list | 1 |
| a new `float("NaN")` | 3 |
| `math.nan` | **1** |
| one NaN stored in a module variable | **1** |
| a counter that goes up | 3 |
| a tensor | 3 |
| it raises an exception | 3 |

Two rows deserve a closer look. A fresh `float("NaN")` makes a node run every time, because NaN never equals itself. That is the usual trick, and core uses it. But `math.nan` is one shared object, and Python treats an object inside a container as equal to itself without comparing values. The key matches and the node stays cached. If you want "always run", write `float("NaN")` exactly.

Honest fingerprints are better than the trick. `LoadImage` is the model: it hashes the file, so it runs when the file changes, and only then. Open this graph with any picture, queue twice, then overwrite the file and queue again.

{{graph:f_fingerprint_image}}

```python
@classmethod
def IS_CHANGED(s, image):
    image_path = folder_paths.get_annotated_filepath(image)
    m = hashlib.sha256()
    with open(image_path, 'rb') as f:
        m.update(f.read())
    return m.digest().hex()
```

**A fingerprint sees constants only.** A wired input arrives as `None`. In our run, `IS_CHANGED(x=1, image=None)` was called though `image` was wired. So you can't fingerprint data from upstream, and you don't need to: a change upstream changes your key already.

**Downstream follows.** A node that runs every time gives every node after it a fresh result, so they run too. One NaN early in a graph can make a slow chain run on every queue.

{{play:f_rerun}}

## not_idempotent

Two copies of a node with the same inputs have the same key, so they share one result. For a node that draws random noise, or writes to something, that may be wrong. With `not_idempotent=True` the node id joins the key. In our run, two identical copies ran once as ordinary nodes and twice as not_idempotent.

It doesn't mean "always run". On the second queue with nothing changed, neither copy ran. That is the mix-up to avoid.

## validate_inputs

This runs at queue time, before any node. Return `True`, or a string saying what is wrong. A string shows up as `custom_validation_failed`.

```python
@classmethod
def validate_inputs(cls, p):
    return True if p % 2 == 0 else f"p must be even, got {p}"
```

Three rules that surprise people, all from `validate_inputs` in `execution.py`, and all confirmed in a run:

- **Naming an input switches off its built-in range check.** If your function takes `p`, the engine assumes you are handling `p`. A value of 100 passed with `max=10` on that input, while another input it didn't name still failed. Taking `**kwargs` turns the checks off for every input.
- **Wired inputs arrive as `None`.** Nothing has run yet. Check for that.
- **Taking `input_types` turns off the type check on wires.** Your function gets a dict such as `{'p': 'MASK'}`, and you decide. In our run, a MASK reached an IMAGE input this way.

Return exactly `True` to pass. Anything else counts as failure, including `None`, so a function that falls off the end without returning fails the graph.

## What goes wrong

- **"My random node gives the same result every time."** Nothing in its key changed. Add a seed input with `control_after_generate`, which is what users expect. Use NaN only if you really mean "always".
- **"I return `math.nan` and it stays cached."** See the table. Use `float("NaN")`.
- **"I return True to mean changed."** It's a value, not an answer. Return the thing that changes.
- **A slow node runs every queue for no reason.** Its fingerprint returns a tensor or another object the key can't compare, or it raises. A plain dict or list is fine, as the table shows. A raised error sets the key to NaN and logs a warning. Look in the console.
- **My range stopped working.** You named the input in `validate_inputs`. Check it yourself there.
- **`validate_inputs` fails with no message.** It returned `False` or `None`. Return a string saying why.
- **A validator crashes the check.** An exception gives `exception_during_validation`, and the output is dropped.

## Lab

The lab builds a key shaped like the real signature and lets Python's own `==` decide. The engine around it is a stand-in, but each count matches the real table above.

```text
what the hook returns                            runs in 3 queues
return float("NaN"), a new object each time      3
return math.nan, one shared object               1
```

The reason, in one line of plain Python:

```text
nan == nan: False   (n,) == (n,): True   (float('nan'),) == (float('nan'),): False
```

A file hash, with the file edited before the third queue:

```text
file hash, queue 4 times, file edited before the 3rd: [True, False, True, False]
```

And the range check that goes away when you name the input, which has `max=10`:

```text
p=100  q=1    passes
p=2    q=100  [('value_bigger_than_max', 'q')]
```

## Sources

- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/caching.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/caching.py)
- [ComfyUI v0.43.0, comfy_api/latest/_io.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_io.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
