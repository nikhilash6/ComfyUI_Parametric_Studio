# CU-511 - History 11: Audio models: WaveNet to autoregressive music to diffusion music

**Objective.** Say how autoregressive and diffusion audio models spend their model calls, and place the models in ComfyUI in that history. Taught by DJ Spectrogram.

## The idea

Audio has one brutal number: tens of thousands of samples for every second. The history of audio models is largely a series of answers to that number.

## Era one: one sample at a time

**WaveNet (2016)** works directly on raw waveforms, at 16,000 samples a second or more. It's autoregressive: each sample is predicted from the ones before it. Training is fast, because all the past samples are known. Generating is sequential: a sample has to be produced and fed back before the next one can start. That's 480,000 steps for 30 seconds.

Its other big idea reaches far back without many layers. A dilated convolution skips inputs: 1, then 2, 4, up to 512. Ten layers see 1024 samples, where ten plain layers of kernel 2 see 11. The lab measures this.

## Era two: tokens

Compress first, and predict far fewer things. **MusicGen (2023)** turns 32 kHz audio into tokens with EnCodec, using a stride of 640. That's 50 frames a second, with 4 codebooks at each frame. One transformer predicts them in sequence. For 30 seconds, that's 6,000 predictions. It's still sequential, but it's within reach.

## Era three: everything at once

Diffusion and flow matching don't go in order. They start from noise for the whole clip, and each model call updates all of it. So the count of calls doesn't depend on length: 30 steps with CFG are 60 calls for any clip. Each call gets more expensive as the clip grows. In ComfyUI this family works on a compressed latent. CU-216 shows the Stable Audio VAE, at 2048 samples per latent frame.

Don't read this as "diffusion is always faster". Fewer calls aren't less time: one diffusion call covers the whole clip, while an autoregressive call covers one small step. And diffusion has its own costs.

## In ComfyUI: now it's both

Here's the twist. The newest music model in core combines the eras.

**MiniMax Music 3** runs an autoregressive language model first, at 25 frames a second with 8 codes per frame. Then it runs a flow-matching DiT, guided by that model's hidden states. So you pay for both, and you get structure from one and detail from the other. CU-350 walks through it.

{{graph:wf_music3}}

{{audio:families/mini-max-music3_1.mp3|Music 3. Prompt: epic cinematic trailer score, deep brass, driving taiko drums, soaring strings, instrumental. One seed, shortened web copy.}}

**ACE-Step 1.5** has a diffusion transformer, `AceStepDiTModel`, with lyric and timbre encoders. It also has `AceStepAudioTokenizer`, which uses finite scalar quantization, FSQ. FSQ rounds each number to a few levels and needs no learned codebook. The word "tokenizer" doesn't make the model autoregressive. Its class layout says the generator is the DiT, though we have not traced each path through the tokenizer.

{{audio:families/ace-step-1-5_0.mp3|ACE-Step 1.5, a gallery render with the same kind of prompt: a slow cinematic ambient score, instrumental. One seed, shortened web copy.}}

**LTX** does sound as part of video, using `CausalAudioAutoencoder` and a `Vocoder`, in `LTXAVModel`. **MiniMax H3** does the same with its own VAE. CU-331 and CU-332 cover them.

Compare the call counts yourself:

{{play:audiocalls}}

## What goes wrong

- **Expecting every model to get steps from one setting.** On Music 3, the long wait is in the text encoder. KSampler's steps don't touch that part.
- **Assuming a longer song costs the same on a diffusion model.** The step count stays fixed, and each call grows.
- **Calling a model autoregressive because it has tokens.** ACE-Step has a tokenizer and a DiT. Check where the generation loop is.
- **Reducing steps on an AR stage.** AR has no steps setting of that kind. Its length is the number of frames.
- **Comparing call counts as if they were seconds.** One sample-level call is very small. One DiT call is very large.
- **Trusting a figure from a blog for a model's rate.** Read the paper or the source. An earlier draft of this lesson did not, and got details wrong.

## Lab

The dilated stack, measured by tracing which inputs reach one output:

```text
dilations 1, 2, 4 ... 512, kernel 2: 1024 samples seen, against 11 with no dilation at the same 10 layers
```

Calls for 30 seconds, and what changes at 120:

```text
model                                            calls for 30 s   how
WaveNet, one call per sample at 16 kHz           480,000          sequential
MusicGen, 50 frames/s x 4 codebooks              6,000            sequential
Music 3 AR stage, main model, 25 frames/s        750              sequential
Music 3 DiT, 30 steps, CFG on                    60               each call covers the song, in windows
Stable Audio style diffusion, 30 steps, CFG on   60               each call covers the clip

at 120 s the sequential counts multiply by 4; the diffusion step count does not change, each call just gets longer
```

Flow matching's sum runs over every value at once, not in order. At sigma 1 it's all noise, and at sigma 0 it's the data:

```text
flow matching on 4 latent values, x_sigma = (1 - sigma) x + sigma noise:
sigma 1.0 : +1.541 -0.293 -2.179 +0.568
sigma 0.5 : +1.270 -1.147 +0.411 +0.534
sigma 0.0 : +1.000 -2.000 +3.000 +0.500
```

With a perfect velocity, the path is straight, and Euler lands exactly. Real models aren't perfect, so they take many steps:

```text
Euler on the straight path with a perfect velocity, 10 steps, error 4.8e-07
```

And FSQ in one line:

```text
FSQ with 5 levels: [-1.0, -0.5, 0.0, 0.5] a token, but ACE-Step still generates by a diffusion transformer, not by predicting tokens one by one
```

## Sources

- [WaveNet: A Generative Model for Raw Audio](https://arxiv.org/abs/1609.03499)
- [Simple and Controllable Music Generation](https://arxiv.org/abs/2306.05284)
- [Stable Audio Open](https://arxiv.org/abs/2407.14358)
- [ComfyUI v0.43.0, comfy/ldm/minimax_music/ar.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax_music/ar.py)
- [ComfyUI v0.43.0, comfy/ldm/ace/ace_step15.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/ace/ace_step15.py)
- [ComfyUI v0.43.0, comfy/ldm/lightricks/av_model.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lightricks/av_model.py)
- [ComfyUI v0.43.0, comfy/ldm/lightricks/vae/causal_audio_autoencoder.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lightricks/vae/causal_audio_autoencoder.py)
- [ComfyUI v0.43.0, comfy/ldm/lightricks/vocoders/vocoder.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/lightricks/vocoders/vocoder.py)
