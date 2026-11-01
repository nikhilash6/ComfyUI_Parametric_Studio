# CU-401 - Writing a custom node with the V3 API

**Objective.** Write, register and reason about a V3 node, and avoid the mistakes the engine can't see. Taught by Captain Graph.

## The idea

A V3 node is a class with classmethods. `define_schema` says what it is, and `execute` does the work. CU-430 compared it with V1. This lesson is about what happens around your code.

The main surprise is that the engine doesn't call your class. It makes a copy, locks the copy, and calls your method on that. So the usual ways of keeping state between calls fail, and that is on purpose.

## The whole node

This is read from `comfy_api/latest/_io.py` and real nodes in `comfy_extras/`:

```
class LatentContrast(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="LatentContrast", category="latent/adjust",
            inputs=[io.Latent.Input("samples"), io.Float.Input("amount", default=1.0, min=0.0, max=4.0)],
            outputs=[io.Latent.Output(display_name="samples")])
    @classmethod
    def execute(cls, samples, amount) -> io.NodeOutput:
        ...
        return io.NodeOutput(result)

class MyExtension(ComfyExtension):
    async def get_node_list(self): return [LatentContrast]

async def comfy_entrypoint(): return MyExtension()
```

`nodes.py` looks for `comfy_entrypoint` in a pack's module. It may be a plain function or an async one. It must return a `ComfyExtension`. The loader calls `on_load` first, then `get_node_list`, which must return a list. It then calls `GET_SCHEMA` on each class, so a schema mistake shows up at startup as a warning, and costs you the pack. A good test catches that sooner (CU-438).

Try writing one here. The template is checked against the real API.

{{play:node}}

Then wire it into the smallest graph you have.

{{graph:nm_first}}

## The optional methods

Each of these has its own lesson.

| Method | Old name | Role | See |
|---|---|---|---|
| `fingerprint_inputs` | `IS_CHANGED` | Extra value in the cache key | CU-433 |
| `validate_inputs` | `VALIDATE_INPUTS` | Return True or an error string, runs at queue time | CU-433 |
| `check_lazy_status` | `check_lazy_status` | Names the lazy inputs now needed | CU-432 |

The schema also has flags, such as `is_output_node`, `not_idempotent`, `is_input_list`, `enable_expand` and `accept_all_inputs`. Read the class for the full list, because each has a helpful docstring.

## What execute may return

`EXECUTE_NORMALIZED` wraps your function, and it accepts:

- `io.NodeOutput(a, b)`: what you should use. It also takes `ui=` to send data to the editor, `expand=` for expansion, and `block_execution=` to stop what's downstream. Pass an output value with it: `io.NodeOutput(None, block_execution="why")`. On its own, with no value, the block is skipped, and in our run the node failed with an `IndexError`.
- A tuple: wrapped for you.
- A dict with `result`, `ui` or `expand`: the old V1 shape.
- `None`: an empty output.
- An `ExecutionBlocker`: it becomes `NodeOutput(block_execution=...)` with no value, so it hits the same `IndexError`. In our run a tuple holding the blocker worked.

Anything else raises `Invalid return type from node`.

## State, for real

The engine calls `execute` through `make_locked_method_func`, on a clone made by `PREPARE_CLASS_CLONE`. We ran each of these through the real engine.

```
cls.calls += 1
   AttributeError: Cannot modify class attribute 'calls' on locked class 'V3StateClone'

cls.box["calls"] += 1     where box is a dict on the class
   works: 1, then 2
```

So the lock stops the obvious mistake, and it can't stop the sneaky one. A dict on the class still changes, and the cache key can't see it. If your output depends on it, you have a bug that only shows up sometimes.

V1 is different again. The engine makes one instance per node id and keeps it in `caches.objects`, so `self` survives. In our run, `__init__` ran once and `self.n` went 1, 2, 3 over three queues. That's useful for holding a loaded model, and a trap for anything that affects the result.

## Rules the engine can't enforce

1. **Don't change your inputs in place.** The cache hands the same object to every node using that output. CU-430 shows a real picture drifting because of this.
2. **Don't hide state.** The cache key can't see it. A value that matters must be an input, or be in the fingerprint.
3. **Don't read a file without a fingerprint.** Otherwise an edit on disk doesn't re-run the node.
4. **Keep your ids stable.** `node_id` is what saved graphs refer to. Rename it and old graphs fail with `missing_node_type`. Add the old name to `search_aliases` for search, and keep the id.
5. **Prefix your ids.** Between packs, the last loaded wins (CU-437).

## What goes wrong

- **`Cannot modify class attribute`.** You set something on `cls` inside `execute`. Make it an input, or use a dict only for a true cache, such as a loaded model, that doesn't change results.
- **`No execute function was defined for node class X`.** A typo, or you forgot the `@classmethod`.
- **`Input ids must be unique, but ['a'] are not.`** Two inputs share an id. Two outputs give the same message, starting `Output ids`. An input and an output sharing an id passed in our run, though the docstring says that is checked too.
- **`'NoneType' object has no attribute 'unique_id'`, in a test.** `cls.hidden` exists only inside the engine. CU-438 covers how to test this.
- **Invalid return type.** You returned a bare value or a tensor. Wrap it in `io.NodeOutput`.
- **A hidden value is `None`.** You didn't ask for it: add `hidden=[io.Hidden.unique_id]` to the schema. Fields you don't request come back as `None`, and no error appears.
- **The pack loads, and the node is absent.** `comfy_entrypoint` returned something that isn't a `ComfyExtension`, or the module also has `NODE_CLASS_MAPPINGS`, which wins.

## Lab

The lab has a tiny stand-in for `io`, so it runs without ComfyUI. Copy the node class to a pack, and only the import changes. The stand-in isn't the real library, and the real one has many more types.

```text
input std: 0.9407
output std at amount=2: 1.8784  input tensor untouched: True
validate amount=-1: amount must not be negative | amount=1: True
lazy, amount=1: [] | amount=0, wire not computed yet: ['fallback'] | amount=0, computed: []
```

The third line shows `validate_inputs` returning an error string. The last shows lazy status: the node asks for its fallback only when it needs it, and stops asking once it has it.

The stand-in copies the real lock, with the same message, and shows what gets through it:

```text
hidden state on cls: Cannot modify class attribute 'calls' on locked class 'BadClone'
hidden state in a dict on cls, same input twice: 2 3  the lock cannot see this, and the cache cannot either
```

And the return values, as `EXECUTE_NORMALIZED` handles them:

```text
execute returns tuple -> NodeOutput(*r)
execute returns int -> Invalid return type from node: <class 'int'>
```

## Sources

- [ComfyUI docs: V3 Migration](https://docs.comfy.org/custom-nodes/v3_migration)
- [ComfyUI v0.43.0, comfy_api/latest/_io.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_io.py)
- [ComfyUI v0.43.0, comfy_api/internal/__init__.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/internal/__init__.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_lotus.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_lotus.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
