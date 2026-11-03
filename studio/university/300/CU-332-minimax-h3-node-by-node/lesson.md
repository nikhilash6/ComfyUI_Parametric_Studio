# CU-332 - MiniMax H3, node by node, with sound in the same latent

**Objective.** Read the H3 graph, explain how one sampling run produces both picture and sound, and pick lengths and settings that fit the model. Taught by Reel Rascal.

## The idea

Most video models make silent frames, and sound comes later from something else. H3 doesn't work that way. It denoises picture and sound together, in one sequence of tokens, with both streams placed on one shared clock. So a door that slams on screen can slam in the audio without anyone lining them up.

{{video:showcase/v_h3_chef.mp4|H3, 5 seconds asked, 124 frames, stereo at 32000 Hz. The prompt asks for a chef flambeing a pan, with sizzling sounds and a low flame roar. One seed. Recorded: peak 45.4 GiB on our test machine. Play it with sound on.|showcase/v_h3_chef.webp}}

## Walk the graph

{{graph:wf_h3_t2v}}

**The length, nodes 133 and 132.** A `PrimitiveFloat` holds seconds. A `ComfyMathExpression` turns it into a frame count on the grid: `max(5, round(a * 24)) + (5 - (max(5, round(a * 24)) % 17)) % 17`. The node would snap it anyway, and the lab shows the two agree. Doing it here means the number is visible.

**Check that value before you run it.** In the graph as saved it is 5, which is 124 frames. The node's own tooltip gives a trained range of about 124 to 362 frames, roughly 5 to 15 seconds. At 30 you would ask for 736 frames, far past that.

**Size, node 115.** A `ResolutionSelector` with multiple 32 gives width and height. The VAE's spatial factor is 16, and the transformer patch is 2 x 2, so the node's sizes step by 32.

**Loaders, nodes 127, 128, 119 and 120.** `UNETLoader` loads the model. `CLIPLoader` with type `minimax` loads a vision-language model, Qwen3-VL-32B, cut to 50 layers. Two `VAELoader`s: one for video, one for audio.

**The main node, 131.** `MiniMaxH3ImageToVideo` takes the prompt and returns two things: conditioning and the latent. With no images it is text to video. Give it `first_frame`, `last_frame`, or both, and they are encoded and held fixed as keyframes while the rest is denoised. The latent it returns is a pair:

```
video [batch, 24, T, height / 16, width / 16]
audio [batch, 32, 2, audio T]
```

The `2` is stereo. Audio has its own latent frames at 40 a second.

Here is `first_frame` on its own, then both keyframes together.

{{video:showcase/v_h3_foundry.mp4|Image to video with the studio's h3_i2v graph (workflows/h3_i2v_api.json). The first frame is a gallery still of a gold foundry, held fixed; H3 makes the molten river surge and sparks rise, and the framing barely moves. 124 frames at 960 x 530, stereo at 32000 Hz. Recorded: 66.6 s, peak 46.8 GiB on our test machine. One seed.|showcase/v_h3_foundry.webp}}

{{video:showcase/director_keyframes_bloom.mp4|First and last frame with the h3_fl2v graph (workflows/h3_fl2v_api.json): a seedling in a clay pot as first_frame, red poppies in the same pot as last_frame. H3 grew the plant between them while the window and table stayed put. 124 frames at 960 x 530, with sound. Recorded: 71.2 s, peak 48.0 GiB. One seed.|showcase/director_keyframes_bloom.webp}}

**Turbo switch, nodes 134 to 139.** `LoraLoaderModelOnly` loads a turbo LoRA. The two `ComfySwitchNode`s choose base or LoRA, and 20 or 6 steps, from a single boolean. It starts off.

**Sampling, nodes 123 to 126 and 129.** `BasicGuider` has only one conditioning and no negative, so there's no CFG here. `BasicScheduler` is `simple`, and `KSamplerSelect` is `res_multistep`. `SamplerCustomAdvanced` denoises.

**Decode, nodes 122 and 121.** Both decoders read the same output wire. `VAEDecode` takes the first stream of a nested latent, and `VAEDecodeAudio` takes the last. `CreateVideo` joins them at fps 24, and `SaveVideo` writes the file.

## One clock, two schedules

The audio VAE makes 32000 / 800 = 40 latent frames a second, and the video is 24 frames a second. So one video frame spans 40 / 24 = 5/3 of an audio latent frame. That number is `FRAME_RESCALE`, and positions in the model use it, so tokens from both streams sit on the same time axis.

{{play:avtime}}

The two streams don't follow the same noise level, though. Video uses shift 12 and audio uses shift 3. The sampler only knows one schedule, the video one. `ModelSamplingAV` makes this work by carrying the audio stream scaled by 12 / 3 = 4, and inside the model `time_shift_sigma` converts the video's noise level into the audio's. You can set both with `MiniMaxH3SigmaShift`, which appears as `ModelSamplingMiniMaxH3`. The graph leaves the defaults.

Audio is cheap. At 5 seconds it adds 414 tokens to 37,296 video tokens, about 1.1%.

## Writing prompts

Our `minimax-h3` skill suggests: subject, action, camera path, environment, lighting, and what you should hear. Our `h3-prompts` skill has templates and a linter. Treat those as house advice, tested by us and not stated by MiniMax. Say what you want to hear. The chef's prompt above names the sizzle and the roar.

Our studio's Director goal writes that kind of prompt from a few choices: it adds one sentence each for the shot, the camera move, the lens, the light and the mood after your words.

{{video:showcase/director_wide.mp4|The Director goal on the plain h3_t2v graph. The words: a lone traveller walks across a vast white salt flat toward a distant ring of light. The goal added a wide shot, a crane up, an anamorphic lens, golden hour and an epic mood. The camera rises as the traveller walks into low sun; the ring of light came out as the sun itself. 124 frames at 960 x 530, with sound. Recorded: 127.1 s, peak 45.6 GiB. One seed.|showcase/director_wide.webp}}

## What goes wrong

- **It takes far too long or runs out of memory.** Check the seconds value first. 30 seconds has nearly six times the tokens of 5 seconds, and it sits outside the trained range in the tooltip.
- **`VAEDecodeTiled` doesn't help.** H3's VAE ignores those settings: `decode_tiled` just calls `decode`. It already chunks internally, 17 frames at a time and 256 pixels. Use plain `VAEDecode`.
- **The motion looks too fast or too slow.** `FPS` in the node code is fixed at 24. Set `fps` in `CreateVideo` to 24 as well, or sound and picture drift apart.
- **Silence, or a VAE error at the end.** The two VAEs got crossed. Check that the video VAE goes to `VAEDecode` and the 32000 Hz audio VAE to `VAEDecodeAudio`.
- **Audio volume seems to be capped.** `VAEDecodeAudio` divides by max(1, 5 x the standard deviation). CU-216 shows the rule.
- **A negative prompt has nowhere to go.** Nothing's broken. `BasicGuider` takes one conditioning.
- **A long guide clip is cut.** `MiniMaxH3AddGuide` crops clips to 5, 22, 39 and so on, the same 17k + 5 grid.

## Lab

Sizes at the model's base canvas, 1344 x 768:

```text
length asked -> frames, seconds, video latent [24, T, H, W], audio latent [32, 2, T]   at 1344 x 768
    5 ->    5 frames   0.208 s   video [24,   2, 48, 84]   audio [32, 2,    8]   tokens: video   2,016 + audio    16, audio is 0.8%
  100 ->  107 frames   4.458 s   video [24,  32, 48, 84]   audio [32, 2,  178]   tokens: video  32,256 + audio   356, audio is 1.1%
  124 ->  124 frames   5.167 s   video [24,  37, 48, 84]   audio [32, 2,  207]   tokens: video  37,296 + audio   414, audio is 1.1%
  362 ->  362 frames  15.083 s   video [24, 107, 48, 84]   audio [32, 2,  603]   tokens: video 107,856 + audio 1,206, audio is 1.1%
  736 ->  736 frames  30.667 s   video [24, 217, 48, 84]   audio [32, 2, 1227]   tokens: video 218,736 + audio 2,454, audio is 1.1%
```

The graph's expression, and the audio clock:

```text
the graph's expression at 5 s gives 124, at 15 s 362, at 30 s 736
audio: 32000 / 800 = 40 latent frames a second; per video frame 40 / 24 = 1.6667, which is FRAME_RESCALE = 5/3
```

Where each video latent frame starts on the shared clock:

```text
  video latent frame 0: covers 1 frames, starts at timeline  0.000, which is 0.000 s
  video latent frame 1: covers 4 frames, starts at timeline  1.667, which is 0.042 s
  video latent frame 2: covers 4 frames, starts at timeline  8.333, which is 0.208 s
  video latent frame 3: covers 4 frames, starts at timeline 15.000, which is 0.375 s
  video latent frame 4: covers 4 frames, starts at timeline 21.667, which is 0.542 s
  video latent frame 5: covers 1 frames, starts at timeline 28.333, which is 0.708 s
  video latent frame 6: covers 4 frames, starts at timeline 30.000, which is 0.750 s
```

The latent frames alternate: one frame, then four groups of four. Then the two noise schedules, as `time_shift_sigma` computes them. When the video is at 0.75, the audio is at 0.43. The audio is further along at every moment.

```text
shifts: video 12, audio 3, audio_scale = 12 / 3 = 4.0
video sigma   audio sigma at the same moment
0.99          0.9612
0.9           0.6923
0.75          0.4286
0.5           0.2000
0.25          0.0769
0.1           0.0270
```

And the VAE's chunk numbers. The memory estimate clamps to one chunk, so decoding doesn't grow with length:

```text
video VAE: ratio_t 4, chunk 5 tokens, overlap 2 tokens, chunk_frames 28
```

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_minimax_h3.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_minimax_h3.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax/model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax/model.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax/vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax/vae.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax/audio_vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax/audio_vae.py)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
- [ComfyUI v0.43.0, comfy/supported_models.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/supported_models.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_audio.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_audio.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
