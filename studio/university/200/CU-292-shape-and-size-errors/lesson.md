# CU-292 - Shape and size errors: reading a traceback

**Objective.** Read a traceback from the bottom, work out which two things disagree, and find the node that made the wrong one. Taught by Captain Graph.

## The idea

A shape error means two tensors met that don't fit. Validation can't catch it, because sizes exist only while the graph runs. So it arrives mid-run, as a wall of text. The wall is easier than it looks. You only need three lines of it, and the numbers in them tell you nearly everything.

## Reading one

This came from a real run on a CPU: `LatentAdd` given an SD latent with 4 channels and an SD3 latent with 16. We cut the long code lines from the engine's own frames.

```
!!! Exception during processing !!! The size of tensor a (4) must match the size of tensor b (16) at non-singleton dimension 1
Traceback (most recent call last):
  File "execution.py", line 548, in execute
  File "execution.py", line 353, in get_output_data
  File "execution.py", line 327, in _async_map_node_over_list
  File "execution.py", line 315, in process_inputs
  File "comfy_api/internal/__init__.py", line 149, in wrapped_func
  File "comfy_api/latest/_io.py", line 2219, in EXECUTE_NORMALIZED
  File "comfy_extras/nodes_latent.py", line 43, in execute
    samples_out["samples"] = s1 + s2
RuntimeError: The size of tensor a (4) must match the size of tensor b (16) at non-singleton dimension 1
```

Read it **from the bottom up**.

1. **The last line says what.** Sizes 4 and 16, at dimension 1.
2. **The frame above it says where.** `nodes_latent.py`, the line `s1 + s2`.
3. **Everything above is the engine.** The `execution.py` frames appear in every failure. Skip them.

Now use the axes:

| Type | Axes |
|---|---|
| IMAGE | batch, height, width, channels |
| MASK | batch, height, width |
| LATENT | batch, channels, height / 8, width / 8 (for most image models) |

Dimension 1 of a latent is its channels. So 4 and 16 means two different model families met. No resize will fix that.

The error box also shows the failing node's id and type, and `current_inputs` holds its input values. That tells you which node to look at, and you can walk up from there.

{{play:f_trace}}

## The errors you'll meet

Each message here is real torch wording, made in the lab. The fix depends on which numbers appear.

**`The size of tensor a (X) must match the size of tensor b (Y) at non-singleton dimension N`.** Two tensors added or multiplied. Find N in the table above. At dimension 0 it's a batch size. On a latent, dimension 1 is the family, and the last two are height and width. On an IMAGE, dimensions 1 and 2 are height and width, and the last is channels.

**`Sizes of tensors must match except in dimension 0`.** Things being stacked into a batch. All must be the same size, apart from the batch axis.

**`expected input[1, 16, 8, 8] to have 4 channels, but got 16 channels instead`.** A layer wants 4 channels and got 16. Usually a VAE from one family fed a latent from another. Look at the VAE and the sampler's model: do they belong together?

**`mat1 and mat2 shapes cannot be multiplied (77x2048 and 768x320)`.** Text conditioning of width 2048 went into a layer built for 768. Almost always, the wrong text encoder is wired to this model. ComfyUI knows this one. When the node's class name contains `Sampler`, it adds a tip:

```
TIPS: If you have any "Load CLIP" or "*CLIP Loader" nodes in your workflow connected to this sampler node make sure the correct file(s) and type is selected.
```

**The `to have 3 channels, but got 64 channels` kind.** The axes are in the wrong order. Often a custom node passing an IMAGE (channels last) straight into a layer that wants channels second. That is a bug in the node, and `.movedim(-1, 1)` is the usual fix.

## The opposite problem: no error at all

This surprised us. We tried to make core nodes fail on mismatched sizes, and most wouldn't. They resize the second input to fit the first, and say nothing.

| Node | Inputs | Result shape |
|---|---|---|
| `ImageBatch` | 64 by 64, 128 by 128 | (2, 64, 64, 3) |
| `ImageBlend` | 64 by 64, 128 by 128 | (1, 64, 64, 3) |
| `JoinImageWithAlpha` | 64 by 64, mask 128 by 128 | (1, 64, 64, 4) |
| `LatentAdd` | 8 by 8, 16 by 16 latents | (1, 4, 8, 8) |
| `LatentBatch` | 8 by 8, 16 by 16 latents | (2, 4, 8, 8) |
| `ImageBatch` | RGB, RGBA | (2, 64, 64, 4) |

That is kind, until you wonder why your picture lost its edges. `ImageBatch`, `ImageBlend` and `LatentAdd` crop the second input to the first one's shape, then scale it: in our run, a gradient 128 wide and 64 tall kept only its middle half. `JoinImageWithAlpha` doesn't crop, so a mask of another shape gets stretched. And when a size error does appear later, the cause may be several nodes upstream. Run this graph, and read what comes out.

{{graph:f_size_silent}}

Channels are the exception: a 4 and a 16 can't be resized, so those raise the errors above.

## Finding the node that made the wrong size

1. Read the numbers. Which axis? What two values?
2. Put a probe on each input of the failing node: `PreviewAny` prints the tensors. `GetImageSize` and `GetLatentSize` give sizes, but they aren't output nodes, so wire a number from them into `PreviewAny` or they won't run. CU-295 goes further.
3. Walk upstream until the size first goes wrong. That's your node.
4. Common fixes: `ImageScale` or `LatentUpscale` to the size you need, the right VAE or text encoder for the model, or sizes on the model's grid. Try the calculator below.

{{play:latent}}

## What goes wrong

- **You read from the top.** The first frames are all the engine's. Start at the bottom.
- **Error in `KSampler` and you blame the sampler.** The sampler runs the model, so anything wrong with the model, the conditioning or the latent surfaces here. A `mat1 and mat2` error there points to the encoder.
- **Sizes that nearly match.** A width that isn't divisible by 8 becomes smaller in latent space. Sizes off the grid fail in some models and get rounded in others.
- **A control or mask at another size.** Check what the node does: some resize quietly, some fail.
- **Batch 1 works and batch 4 fails.** A batch of 1 broadcasts against anything, so that case hid a mismatch. A batch of 2 against a batch of 3 is an error, at dimension 0.
- **The error goes away when you restart.** The tensor came from a cached node. Check whether a size you changed reached it.

## Lab

The lab makes each error with plain torch, so the wording is torch's own:

```text
add a 4-channel latent and a 16-channel latent
   RuntimeError: The size of tensor a (4) must match the size of tensor b (16) at non-singleton dimension 1
batch a 4-channel latent with a 16-channel latent
   RuntimeError: Sizes of tensors must match except in dimension 0. Expected size 4 but got size 16 for tensor number 1 in the list.
text encoder width 2048 into a cross-attention layer that wants 768
   RuntimeError: addmm: mat1 and mat2 shapes cannot be multiplied (77x2048 and 768x320)
```

A batch of 1 is the quiet case:

```text
a batch of 1 against a batch of 3: no error, it broadcasts
   no error: (3, 4, 8, 8)
```

And the axes, for a picture 768 wide and 512 tall:

```text
a 768 wide by 512 tall image: (1, 512, 768, 3)  its SD latent: (1, 4, 64, 96)
```

## Sources

- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_latent.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_latent.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_preview_any.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_preview_any.py)
