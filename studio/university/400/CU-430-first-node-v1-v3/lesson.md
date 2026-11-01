# CU-430 - Your first node, in V1 and in V3

**Objective.** Write one small node in both styles, say what the engine needs from each, and avoid the two mistakes a first node usually makes. Taught by Captain Graph.

## The idea

A custom node is a Python class in a folder under `custom_nodes`. It says what it takes and what it gives, and it has one function that does the work. That is all.

ComfyUI has two ways to write that class. **V1** is a plain class with special attribute names. **V3** is a class that inherits from `io.ComfyNode` and returns a schema object. Core still has both: `ImageInvert` in `nodes.py` is V1 and `ImageBlur` is V3.

If you're starting today, write V3. You get a checked schema and clearer errors. You still need to read V1, because most packs you meet use it.

## The same node, twice

This node multiplies an image by an amount. V1 first:

```python
class Brighten:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "amount": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 4.0, "step": 0.01}),
        }}
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = "university"

    def run(self, image, amount):
        return (torch.clamp(image * amount, 0, 1),)

NODE_CLASS_MAPPINGS = {"Brighten": Brighten}
```

And V3:

```python
from comfy_api.latest import ComfyExtension, io

class Brighten(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Brighten",
            category="university",
            inputs=[
                io.Image.Input("image"),
                io.Float.Input("amount", default=1.0, min=0.0, max=4.0, step=0.01),
            ],
            outputs=[io.Image.Output()],
        )

    @classmethod
    def execute(cls, image, amount):
        return io.NodeOutput(torch.clamp(image * amount, 0, 1))

class MyExtension(ComfyExtension):
    async def get_node_list(self):
        return [Brighten]

async def comfy_entrypoint():
    return MyExtension()
```

Read them side by side.

| Job | V1 | V3 |
|---|---|---|
| Describe the inputs | `INPUT_TYPES` returns a dictionary | `define_schema` returns `io.Schema` |
| Name the outputs | `RETURN_TYPES`, a tuple | `outputs=[...]` |
| Name the work function | `FUNCTION`, any name | always `execute` |
| How it is called | on an instance, with `self` | on a copy of the class, with `cls` |
| What it returns | a tuple, or a dict with `result` | `io.NodeOutput` |
| Register | `NODE_CLASS_MAPPINGS` | `comfy_entrypoint` and `get_node_list` |

Argument names must match input names exactly, in both. The engine calls your function with keywords.

## They meet in the middle

The engine has one validator, and it reads the V1 shape. So the V3 base class turns your schema into that shape for it. We ran both through the real engine on a CPU, and this is what came back from the V3 node's `INPUT_TYPES`:

```
{'required': {'image': ('IMAGE', {}), 'amount': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 4.0, 'step': 0.01})}}
```

That is exactly what the V1 node returns. Both also fail range checks the same way:

```
Value 9.0 bigger than max of 4.0
```

Try the two forms here. Change the name and the type, and watch what stays the same.

{{play:node}}

## Installing it

Put the file in a folder such as `custom_nodes/my_pack/__init__.py`, then restart ComfyUI. Packs load once, at startup, so an edit to Python does nothing until the next restart. When the loader looks inside your module, it reads `NODE_CLASS_MAPPINGS` first. If that exists, it stops there and never calls `comfy_entrypoint`.

Then test it on the smallest graph you have. This one needs no model. Swap your node in place of `ImageInvert`.

{{graph:nm_first}}

## What goes wrong

- **`TypeError: object of type 'int' has no len()`.** Your V1 function returned a number `x`, not `(x,)`. A one-item tuple needs that comma. V3 accepts a bare `io.NodeOutput(x)`, so this one mostly bites in V1.
- **Shapes go wrong one node later.** The same mistake with an image gives no error at your node. We ran `return image`: the engine indexed the tensor as if it were the tuple, so the next node got the first image alone, `[H, W, C]`, with no batch dimension. In our run `ImageScale` then failed with a `ValueError`. If a shape loses a dimension, look for the missing comma upstream.
- **The picture drifts brighter each queue.** You wrote `image *= amount` or `image += 0.25`. The tensor you got is the same object the node upstream has in the cache, so you just changed its stored result. Write `image = image * amount`. The lab shows the numbers.
- **`got an unexpected keyword argument`.** An input is called `x` and your function takes `y`. They have to match.
- **The node isn't in the menu.** Look in the startup log for `IMPORT FAILED` beside your folder, in the list of import times. The traceback is further up, printed when the pack loaded, just before `Cannot import ... module for custom nodes`. CU-437 goes through this.
- **Your edit changed nothing.** You didn't restart, or you did and the inputs are the same, so the old result came from the cache. Change a value to test.
- **The image goes in the wrong way round.** `IMAGE` is batch, height, width, channels, and values run 0 to 1. CU-103 covers it.

## Lab

The lab writes the node both ways on a small stand-in for the engine, because labs can't import ComfyUI. The stand-in follows `get_v1_info` and `merge_result_data`. The real runs above and in the verified list used the real thing.

```text
the same to the validator: True
input mean 0.1255   V1 output 0.2510   V3 output 0.2510
```

The mistake with the tuple, from the same line of logic the engine uses:

```text
return (x,) -> [[7]]
return x    -> TypeError: object of type 'int' has no len()
```

And the drift. `EmptyImage` stays in the cache between queues, and each queue only changes a later setting:

```text
image += 0.25       [0.3755, 0.6255, 0.8755]
image + 0.25        [0.3755, 0.3755, 0.3755]
```

We got the same three numbers from the real engine with the real `EmptyImage`, so this is not just a toy. The cache holds your upstream node's tensor, and nothing stops you from writing on it.

## Sources

- [ComfyUI v0.43.0, comfy_api/latest/_io.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_io.py)
- [ComfyUI v0.43.0, comfy_api/latest/__init__.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/__init__.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI docs: V3 Migration](https://docs.comfy.org/custom-nodes/v3_migration)
