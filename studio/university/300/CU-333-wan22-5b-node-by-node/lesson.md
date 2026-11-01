# CU-333 - Wan 2.2 5B, node by node, and how it differs from the 14B pair

**Objective.** Read the Wan 2.2 5B graph, and explain from Wan's own configs how the 5B model and the two-model 14B route differ. Taught by Reel Rascal.

## The idea

Two Wan 2.2 releases share a name and differ in design. TI2V-5B is a single small model with a stronger VAE. T2V-A14B is a pair: one model for high noise and one for low noise, handing over in the middle of the run. Both have the same patch size, so the VAE's compression decides how many tokens they see. A 14B run at the same picture size has four times as many.

{{video:showcase/v_wan_waves.mp4|Wan 2.2, 121 frames at 960 x 528, silent. Prompt: golden sunset waves crash in slow motion on black volcanic rocks, spray lit from behind. Recorded: 105.4 s, peak 34.5 GiB on our test machine. One seed.}}

## Side by side

From Wan's own config files:

| | TI2V 5B | T2V A14B |
|---|---|---|
| VAE stride | 4, 16, 16 | 4, 8, 8 |
| latent channels (ComfyUI) | 48 | 16 |
| patch | 1, 2, 2 | 1, 2, 2 |
| width, layers | 3072, 30 | 5120, 40 |
| models | one | high noise and low noise |
| shift | 5 | 12 |
| steps | 50 | 40 |
| guidance | 5.0 | 3.0 low, 4.0 high |
| boundary | none | 0.875 |

## Walk the graph

{{graph:wf_wan22_t2v}}

**Loaders, nodes 1 to 3.** `UNETLoader` loads the model. When ComfyUI sees an output width of 48 channels, `WAN22_T2V` matches, with its own latent format. `CLIPLoader` with type `wan` loads umT5. `VAELoader` loads the Wan 2.2 VAE, which `comfy/sd.py` recognises by its layout.

**Shift, node 4.** `ModelSamplingSD3` with shift 8. Shift bends the noise schedule: sigma = shift x t / (1 + (shift - 1) x t). Our graph uses 8. Wan's own config says 5. See the lab for what that does to the steps.

**Prompts, nodes 5 and 6.** Two `CLIPTextEncode`s. CFG is 5 here, so unlike the LTX and H3 graphs, the negative prompt truly runs, and each step costs two model calls.

**Latent, node 7.** `Wan22ImageToVideoLatent` takes the VAE, the size and the length. With no start image it returns zeros, shaped `[1, 48, (n - 1) // 4 + 1, H / 16, W / 16]`. Give it `start_image`, and the node encodes it into the first latent frames and marks them with a mask. That is how one model does both text and image to video: "TI2V" in its name. `WAN22.process_timestep` then gives each latent frame its own timestep from the mask, so the frames you gave it count as already clean.

**Sampling, node 8.** A plain `KSampler`: 20 steps, cfg 5, `uni_pc`, `simple`. All of it runs on one model, so this works like an image graph.

**Decode and save, nodes 9 to 11.** `VAEDecode`, `CreateVideo` at 24 fps, `SaveVideo`. No sound: the gallery's Wan files have no audio stream.

## The 14B route

Wan's code uses the boundary to pick a model at each step: at high noise it uses the high-noise model, then it swaps to the low-noise model. ComfyUI has no single node for this. You load both with two `UNETLoader`s and chain two `KSamplerAdvanced` nodes, using `start_at_step` and `end_at_step`, with leftover noise passed from the first to the second. Our studio's earlier notes used that pattern, with 2 + 2 steps and a speed LoRA.

The split depends on shift. Try Wan's own numbers.

{{play:highlow}}

## What goes wrong

- **`batch_size` does nothing.** Without a start image, this node hardcodes the batch at 1. It's only used on the start-image branch. To get several takes, run several seeds.
- **A size off the grid.** The node's width and height step by 32, but the latent divides by 16. A size typed by hand is floored to a multiple of 16.
- **The wrong VAE.** The 5B needs the Wan 2.2 VAE with 48 channels. The 14B pair's config names the Wan 2.1 VAE with 16. Don't copy a loader across.
- **Advice from the wrong model.** Settings written for the pair, like shift 12, a boundary and 40 steps, don't apply to 5B. Wan's 5B config has shift 5 and no boundary.
- **Everything looks over-smooth or under-done against other people's results.** Check steps and shift. Wan's 5B config uses 50 steps at shift 5, and our graph uses 20 at 8 for speed. We have not compared them.
- **Out of memory with the pair.** Two 14B models take more memory than one 5B. Check the budget first (CU-305).

## Lab

Tokens at the same picture size:

```text
model             VAE            latent at 832x480x81       values       tokens
TI2V 5B           4x16x16, 48ch  (48, 21, 30, 52)           1,572,480    8,190
T2V A14B          4x8x8, 16ch    (16, 21, 60, 104)          2,096,640    32,760
the 14B route has 4.00 times the tokens and 16 times the attention pairs at the same picture size
values per pixel of the picture: 5B 64:1, 14B 48:1 for long clips

transformer in Wan's configs:  TI2V 5B dim 3072, 30 layers, 24 heads   T2V A14B dim 5120, 40 layers, 40 heads, two of them
```

What shift does on a plain even grid:

```text
shift changes where a plain even grid of 20 steps spends its time (a plain even grid: real samplers may space it differently)
shift  5.0: first sigmas 1.000 0.990 0.978, steps above 0.875:  9 of 20, steps below 0.5:  3
shift  8.0: first sigmas 1.000 0.993 0.986, steps above 0.875: 11 of 20, steps below 0.5:  2
shift 12.0: first sigmas 1.000 0.996 0.991, steps above 0.875: 13 of 20, steps below 0.5:  1

14B with its own numbers on the plain grid: boundary 0.875, 26 steps on the high-noise model, 14 on the low-noise model
```

And two facts from the source. `batch_size` has no effect with no start image, and the VAE's decode estimate has no frame count in it at all, because the Wan VAE decodes step by step through time.

```text
Wan22ImageToVideoLatent batch_size 4: no start image -> (1, 48, 21, 30, 52)  with a start image -> (4, 48, 21, 30, 52)
decode estimate at 832x480: 6.0 GiB in bfloat16, any length
decode estimate at 1280x704: 13.4 GiB in bfloat16, any length
```

## Sources

- [Wan2.2 README](https://github.com/Wan-Video/Wan2.2)
- [Wan2.2 config, wan_ti2v_5B.py](https://github.com/Wan-Video/Wan2.2/blob/main/wan/configs/wan_ti2v_5B.py)
- [Wan2.2 config, wan_t2v_A14B.py](https://github.com/Wan-Video/Wan2.2/blob/main/wan/configs/wan_t2v_A14B.py)
- [Wan2.2 text2video.py](https://github.com/Wan-Video/Wan2.2/blob/main/wan/text2video.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_wan.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_wan.py)
- [ComfyUI v0.43.0, comfy/supported_models.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/supported_models.py)
- [ComfyUI v0.43.0, comfy/model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_base.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_model_advanced.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_model_advanced.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
