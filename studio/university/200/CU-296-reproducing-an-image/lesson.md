# CU-296 - A result that doesn't match: reproducing someone's image

**Objective.** Work through the settings in the order that matters, and know when an exact match is possible at all. Taught by Captain Graph.

## The idea

A picture is the result of a long list of settings. Change any of them and the picture changes, often a lot. So when yours doesn't match, the job isn't to adjust things until it looks closer. It's to find what's different.

Start by asking for the graph. Without it you are guessing.

## Get the graph

`SaveImage` writes the whole graph into a PNG as text, under the keys `prompt` and `workflow`. Drag the PNG onto the editor, and the graph opens. Many things remove that text: a screenshot, a re-save as JPEG, most social sites. `--disable-metadata` turns it off at the source.

With the graph, you can compare yours and theirs line by line. The lab does it in a few lines of code, and it's a good habit: API-format graphs are plain JSON, so a text diff works.

A graph gives you settings. It doesn't give you the same files, and it can't tell you what custom nodes did inside.

## The checklist

Go in this order. The first items change the most, and are easiest to check.

**1. The model file itself.** A file name isn't an identity. Two files called `model.safetensors` can be different versions. Compare hashes with `sha256sum` if you have theirs. Check the VAE and text encoder as well, especially a separate VAE.

**2. The seed and the batch.** The seed sets the noise. In a batch, all the noise comes from one generator, so the third image of a batch of 4 isn't what you get from a batch of 1 with that seed, or with seed plus 2. To rebuild it, use the same batch size, or `LatentFromBatch`, which sets a `batch_index` the noise step uses. Also check that `control_after_generate` didn't move the seed: the value shown after a run may be the next seed, not the one used.

**3. Size.** A different width or height means different noise in different places, and a different picture.

**4. Sampler, scheduler, steps, CFG, denoise.** Each changes the result. How much varies, and sometimes it doesn't change at all. These are real, with one seed and one prompt, on a 0 to 255 scale:

| Change | Model | Mean pixel difference |
|---|---|---|
| euler to ddim | SD 1.5 | 0, files are identical |
| euler to dpmpp_2m | SD 1.5 | 20.92 |
| euler to euler_ancestral | SD 1.5 | 61.95 |
| scheduler normal to karras | SDXL | 23.26 |
| CFG 7 to 14 | SDXL | 30.99 |

{{wipe:sampling_lab/sampler-euler.jpg|sampling_lab/sampler-euler_ancestral.jpg|euler|euler_ancestral|One seed, one prompt, same model. Changing only the sampler gave a different scene: euler shows an astrolabe face on, and euler_ancestral a close view of one on a chart.}}

Ancestral and SDE samplers add new noise at each step, so a different sampler can lead somewhere else entirely. See more in the [Sampling Lab](#sampling/bench).

**5. The prompt, exactly.** A space or comma can change the result, as can weights. Copy it from the graph. Check you haven't swapped positive and negative: validation can't catch that.

**6. LoRAs, ControlNets and other patches.** Same files, same strengths, same order. Check `strength_model` and `strength_clip` separately. A patch in the graph that you bypassed is a difference too.

**7. Custom nodes and versions.** Their code affects the result. A pack update can change a default. A ComfyUI update can too.

**8. The machine.** This is the one you may not be able to fix. Noise is drawn on the CPU in `prepare_noise`, so it doesn't depend on the card. The sums after that do run on the card, in floating point, so a different card, driver or precision can give slightly different results. `--deterministic` asks torch for slower deterministic algorithms, and its own help says it "might not make images deterministic in all cases". We haven't measured how big this is across cards. Expect close, and not always byte for byte.

Try these out:

{{play:f_repro}}

## How close is close?

Bytes matching is the strict test: `sha256sum` on two PNGs. Their metadata has to match too, so comparing the pixels is often better. If two images look alike and differ only slightly, you've likely matched settings and hit the machine's limits. If the scene differs, a setting is still wrong. Keep going down the list.

Then work by halves. Rebuild from their graph, not yours. If theirs gives their result, the fault is in what you changed. Move your settings across a group at a time (CU-295).

{{graph:sd15_txt2img}}

## What goes wrong

- **You changed nothing and got a new image.** The seed moved. Set it to fixed.
- **Your own image from last month won't reproduce.** A pack or ComfyUI updated, or a file was replaced. Keep the PNG, and note versions and hashes for work that matters.
- **The same settings differ in another program.** Their noise or prompt handling may differ. We read ComfyUI's code only, so we can't tell you each difference. Don't expect a match across tools.
- **A file you replaced under the same name.** `CheckpointLoaderSimple` has no change hook, so its cached result stays until the cache clears (CU-221). You might be seeing the old model.
- **The size was rounded.** Sizes off the model's grid get rounded (CU-109). Their number and yours can differ without either of you seeing it.
- **Sampling on CPU versus card, or fp16 versus fp32.** Precision changes values slightly. Check that flags and file types match if you need a close result.
- **A graph with a random part you missed.** Some nodes have their own seed, such as second stages, detailers and noise injectors. Fix them all.

## Lab

The lab ports `prepare_noise`, with no model. It shows what the seed fixes and doesn't:

```text
same seed twice, same noise: True   seed + 1, same noise: False
first of a batch of 4 equals a single: True
third of a batch of 4 equals a single with that seed: False
third of a batch of 4 equals seed + 2: False
third, rebuilt with batch_index [2] (LatentFromBatch): True
```

Then it writes a tiny PNG with a graph in a text chunk, as `SaveImage` does, and reads it back with no special tools:

```text
read from the PNG: {'seed': 424242, 'steps': 20, 'cfg': 7.0, 'sampler_name': 'euler', 'scheduler': 'karras'} {'ckpt_name': 'model.safetensors'}
a screenshot, or a re-saved JPEG, has no such chunk: {}
```

And a diff of two graphs, which is the checklist as code:

```text
differs: ('5', 'cfg', 7.0, 8.0)
differs: ('5', 'scheduler', 'karras', 'normal')
```

## Sources

- [ComfyUI v0.43.0, comfy/sample.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sample.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
