# CU-331 - LTX-2.5, node by node

**Objective.** Read every node of a real LTX-2.5 graph, and say what each one changes and what it costs. Taught by Reel Rascal.

## The idea

LTX-2.5 makes picture and sound together. In ComfyUI that takes two empty latents, one packed value through the sampler, and two decoders at the end. Its VAE compresses hard, 8 times in time and 32 times in space, into 128 channels. So the transformer sees few positions, one token each, and a fixed list of 8 noise levels finishes the job.

{{graph:wf_ltx25_t2v}}

## Walk the graph

**Loaders, nodes 1 to 4.** `UNETLoader` loads the distilled transformer. "Distilled" here is the name on the file and in Lightricks' README. `CLIPLoader` with type `ltxv` loads the Gemma 4 text encoder. There are two `VAELoader`s: one for video and one for audio. They aren't interchangeable.

**Prompts, nodes 5 to 7.** Two `CLIPTextEncode`s, then `LTXVConditioning`, which writes a `frame_rate` into both. This is more than a label. The model divides its time coordinates by that number when it builds positions, so it tells the model how far apart frames are in seconds. Keep it equal to the `fps` you give `CreateVideo`.

**Empty latents, nodes 8 and 10.** `EmptyLTXVLatentVideo` gives `[batch, 128, (n - 1) // 8 + 1, H / 32, W / 32]`. `LTXVEmptyLatentAudio` works out its length from `frames_number / frame_rate`, then asks the audio VAE for its channel and frequency sizes, which is why it takes the VAE as an input. Give it the same frame count and rate as the video.

**Pack, node 11.** `LTXVConcatAVLatent` makes a `NestedTensor` of the two. The sampler treats it as one latent.

**Sampling, nodes 12 to 16.** `SamplerCustomAdvanced` takes its four parts separately.

- `CFGGuider` has `cfg` 1.0. At 1, `sampling_function` skips the negative pass, and `cfg_function` then works out to the conditional result alone. So the negative prompt in this graph does nothing, and you pay for one model call per step instead of two.
- `RandomNoise` holds the seed.
- `KSamplerSelect` picks `euler_ancestral`, which adds fresh noise after every step but the last.
- `ManualSigmas` is the schedule, typed by hand: `1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0`. The same list is `DISTILLED_SIGMA_VALUES` in Lightricks' own code. Nine values make 8 steps.

**Unpack and decode, nodes 17 to 19.** `LTXVSeparateAVLatent` splits the result. `VAEDecodeTiled` decodes the picture in pieces, and `LTXVAudioVAEDecode` decodes the sound. Unlike `VAEDecodeAudio`, this node does not rescale loudness: it returns what the VAE and vocoder make, at the vocoder's sample rate.

**Save, nodes 20 and 21.** `CreateVideo` joins frames, frame rate and sound. `SaveVideo` writes the file.

## Why the list looks odd

Look at the step sizes in the lab: four tiny steps, then bigger and bigger ones. The first four cover only 2.5% of the noise range. The last two cover 72.5%. A list like this belongs to the model it came with, since a distilled model is trained for particular noise levels. Don't expect another schedule to work as well: we read this as the reason for a fixed list, and did not test alternatives.

`LTXVScheduler` is the general tool for the same model family, and its shift rises with the number of latent positions. This graph doesn't use it. Compare both below.

{{play:ltxsigmas}}

## What it looks like

These are earlier renders from our gallery, at 960 x 544 with 145 frames. One seed each.

{{video:showcase/v_ltx_ink.mp4|Text to video with sound. Recorded: 21.3 s, peak 44.3 GiB of VRAM on our test machine. The prompt asks for gold and emerald ink in black water.|showcase/v_ltx_ink.webp}}

{{video:showcase/v_ltx_shatter.mp4|Prompt: a black glass sphere shatters on a dark marble floor and the shards turn into gold butterflies. Recorded: 57.8 s, peak 44.3 GiB.|showcase/v_ltx_shatter.webp}}

{{video:showcase/v_ltx_portal.mp4|Prompt: a swirling portal of green energy tears open in a rainy alley, gold sparks spill out and light the wet walls, a figure in a long coat steps back. The portal fills the first second, then the sparks rain down on the figure. Recorded: 54.4 s, peak 44.3 GiB. One seed.|showcase/v_ltx_portal.webp}}

The same model also starts from a picture. The image-to-video graph (workflows/ltx25_core_i2v_api.json) keeps this sampler, the 8-step list and both decoders, and adds `LoadImage`, `LTXVPreprocess` and `LTXVImgToVideoInplace` to put the still at the start of the video latent.

{{video:showcase/v_ltx_greenhouse.mp4|Image to video from a gallery still of a glowing greenhouse with a figure holding a lantern. The figure is there in the first frames, then the camera cranes up the glass wall until the roof fills the frame. 145 frames at 960 x 544, with sound. Recorded: 33.6 s, peak 43.2 GiB. One seed.|showcase/v_ltx_greenhouse.webp}}

## What goes wrong

- **Sound and picture lengths differ.** `frames_number` and `frame_rate` on the audio node are separate from the video's length. Change one and leave the other, and the two latents stop matching. Wire them from one number.
- **A changed negative prompt has no effect.** CFG is 1. That is normal for this graph. Raising `cfg` adds a second model call per step and leaves the settings the list was made for, so treat it as an experiment.
- **Motion speed looks wrong.** `frame_rate` on `LTXVConditioning` and `fps` on `CreateVideo` disagree. Set them equal.
- **Decode runs out of memory.** Use tiles, as this graph does. At 1920 x 1088 and 121 frames, the VAE's own estimate falls from 37.4 GiB to 2.3 GiB with the graph's tile settings.
- **Blurred joins between tiles in time.** The default temporal overlap of 8 frames becomes one latent frame. If you see a jump at regular intervals, raise it in steps of 8. Note that this is a suggestion from the arithmetic, and we did not test it on this model.
- **Wrong loader for the sound.** `LTXVEmptyLatentAudio` reads sizes from the audio VAE. Connect the video VAE and expect an error, because that VAE has no `latent_frequency_bins` to read. We read this in the code and did not run it.

## Lab

Shapes first. Tokens equal positions, because LTX uses one token per latent position.

```text
832x480, 81 frames -> latent (128, 11, 15, 26), one token per position: 4,290 tokens
960x544, 145 frames -> latent (128, 19, 17, 30), one token per position: 9,690 tokens
1920x1088, 121 frames -> latent (128, 16, 34, 60), one token per position: 32,640 tokens
```

The list in the graph:

```text
distilled list: 8 steps, so 8 model calls at CFG 1
step sizes: 0.0062 0.0062 0.0063 0.0062 0.0656 0.1844 0.3031 0.4219
share of the noise range removed by the first 4 steps: 0.025, by the last 2: 0.725
```

What `LTXVScheduler` would do, from its code:

```text
LTXVScheduler 8 steps,  1024 positions: shift 0.950, sigmas 1.000 0.935 0.859 0.768 0.656 0.517 0.338 0.100 0.000
LTXVScheduler 8 steps,  4096 positions: shift 2.050, sigmas 1.000 0.966 0.922 0.864 0.783 0.665 0.471 0.100 0.000
LTXVScheduler 8 steps,  4290 positions: shift 2.119, sigmas 1.000 0.967 0.924 0.868 0.789 0.671 0.478 0.100 0.000
```

`VAEDecodeTiled` divides the sizes you type by the VAE's factors. The estimate that follows is `memory_used_decode` in `comfy/sd.py`, an estimate and not a measurement:

```text
VAEDecodeTiled(512, 64, 64, 8) on an 8 x 32 x 32 VAE: spatial tile 16, overlap 2 latent units, temporal tile 8, overlap 1 latent frames
decode estimate 832x480 81 frames: whole 4.9 GiB, with the graph's tiles 2.2 GiB
decode estimate 1920x1088 121 frames: whole 37.4 GiB, with the graph's tiles 2.3 GiB
```

The audio sum, with the default config. A real checkpoint can replace these numbers. Our gallery clips have stereo sound at 48000 Hz, so read this line as the shape of the calculation:

```text
LTXVEmptyLatentAudio with those defaults: 25 latent frames a second, 81 frames at 24 fps -> [1, 8, 84, 16]
CFGGuider cfg 1.0: math.isclose(cond_scale, 1.0) is True so the negative prompt in this graph does nothing
```

## Sources

- [LTX-2 README](https://github.com/Lightricks/LTX-2)
- [LTX-2 pipeline constants](https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-pipelines/src/ltx_pipelines/utils/constants.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_lt.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_lt.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_lt_audio.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_lt_audio.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_custom_sampler.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_custom_sampler.py)
- [ComfyUI v0.43.0, comfy/ldm/lightricks/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lightricks/model.py)
- [ComfyUI v0.43.0, comfy/ldm/lightricks/vae/causal_audio_autoencoder.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lightricks/vae/causal_audio_autoencoder.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
