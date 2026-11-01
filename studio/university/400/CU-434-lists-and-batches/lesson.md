# CU-434 - Lists and batches: INPUT_IS_LIST, OUTPUT_IS_LIST

**Objective.** Tell a batch from a list, predict how many times a node is called, and write nodes that produce or take a whole list. Taught by Captain Graph.

## The idea

Between any two nodes, the engine carries a Python list. Normally that list holds one item, and the engine unwraps it before calling your function, so you never see it.

Two different things can hold several images, and they aren't alike:

- A **batch** is one tensor with a first axis of 4. To the engine that is **one item**. Your node runs once and handles all 4 together.
- A **list** is 4 separate items. Your node runs **4 times**, once per item, unless it asks otherwise.

All the images in a batch must be the same size, and the model handles them together, which is usually faster on a card (we did not measure it here). Lists can hold different sizes, because each item stands alone.

## Three rules

From `_async_map_node_over_list` in `execution.py`:

1. Your function is called once per item of the **longest** input list.
2. A **shorter** list repeats its last item. A widget is a list of one, so it repeats for every call. That is why it just works.
3. Outputs from all those calls are gathered into one list per output.

Try the counts yourself.

{{play:f_lists}}

Rule 2 is the trap. With lists of 3 and 2, the third call uses `b`'s last item again. You get no warning, and the pairs may not be the ones you meant.

## Making a list: OUTPUT_IS_LIST

If your function returns a list, the engine treats it as **one item that happens to be a list**, unless you say otherwise.

```python
# V1
RETURN_TYPES = ("INT",)
OUTPUT_IS_LIST = (True,)         # one flag per output

# V3
outputs=[io.Int.Output(is_output_list=True)]
```

The return value is still a tuple of outputs: `return (list_of_things,)` in V1 and `io.NodeOutput(list_of_things)` in V3.

## Taking a whole list: INPUT_IS_LIST

A node that combines many items wants them together, in one call.

```python
# V1, a class attribute
INPUT_IS_LIST = True

# V3, in the schema
is_input_list=True
```

This applies to **every** input of the node, widgets too. So a number widget arrives as a list of one, and you must read `k[0]`. In our run, a node got `v=[0, 10, 20]` and `k=[1]`. Core's `ImageMergeTileList` does exactly this with `final_width[0]`.

## A real one to read

`SplitImageToTileList` outputs a list. `ImageInvert` is an ordinary V1 node that knows nothing about lists. `ImageMergeTileList` takes the whole list. In our run on a CPU, this graph ran `ImageInvert` exactly 4 times and gave back one image.

{{graph:f_list_tiles}}

That is the point of lists. An ordinary node works on tiles without any changes, because the engine calls it once per tile.

## Which to use

- Same size, and you want speed: a **batch**.
- Different sizes, or items you want processed one by one to save memory: a **list**.
- Your node must see everything at once: `INPUT_IS_LIST`.
- Turning one into the other: core has `RebatchImages` and `ImageBatch` for batches. For anything else, write a small node with the flags above.

## What goes wrong

- **A node runs many more times than you expected.** Something upstream outputs a list. A list that meets a slow sampler runs the sampler once per item. Look for a node with `OUTPUT_IS_LIST`.
- **`'list' object has no attribute 'shape'` inside your node.** Either you set `INPUT_IS_LIST` and forgot that every input is now a list, or you returned a list without the flag and the next node got it as one item.
- **`'<' not supported between 'list' and 'int'`, or a similar error, on a widget.** The same cause: read `k[0]`.
- **Pairs that make no sense.** Two lists of different lengths: rule 2. Print them with `PreviewAny`, or make them the same length.
- **`Sizes of tensors must match` when you batch a list.** A list can hold different sizes and a batch can't. Resize first.
- **Only one file saved from a list?** Not a bug to expect: `SaveImage` is an ordinary node, so it runs once per item. Check the numbering in the output folder.
- **`OUTPUT_IS_LIST` tuple the wrong length.** It needs one flag per output, in the same order as `RETURN_TYPES`.

## Lab

The lab ports the list rules of `_async_map_node_over_list` and `merge_result_data`, with made-up nodes. It matches our real run: a node makes 3 items, a second runs once each, a third takes them all.

```text
  call ('make', 3)
  call ('each', 0, 10, 's')
  call ('each', 1, 10, 's')
  call ('each', 2, 10, 's')
  call ('whole', [0, 10, 20], [1])
```

Rule 2:

```text
lists of 3 and 1: [(1, 1), (2, 1), (3, 1)]
lists of 3 and 2: [(1, 10), (2, 20), (3, 20)]
```

The flag:

```text
return a list with OUTPUT_IS_LIST: [[1, 2, 3]]  3 items
return a list without the flag:    [[[1, 2, 3]]]  1 item, which is a list
```

Batch and list:

```text
batch: 1 list item, shape (4, 8, 8, 3): a node is called 1 time
list:  4 list items, each shape (1, 8, 8, 3): a node is called 4 times
a batch may not: Sizes of tensors must match except in dimension 0
```

## Sources

- [Data lists, ComfyUI docs](https://docs.comfy.org/custom-nodes/backend/lists)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_api/latest/_io.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_io.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_images.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_images.py)
