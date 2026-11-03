# CU-350 - MiniMax Music 3, node by node

**Objective.** Read the Music 3 graph, say what happens at the text encoder and at the sampler, and set caption, lyrics and seconds so the song comes out whole. Taught by DJ Spectrogram.

## The idea

Here's the part that surprises everybody: the "text encoder" in this graph writes the song.

In an image graph, a text encoder turns words into a vector in a moment. Here, `MiniMaxMusic3TextEncode` loads a large language model and generates audio codes one frame at a time, in a loop, 25 frames per second of music. That loop is what its progress bar is showing. It decides the structure, the words, and when to stop. Its hidden states become the conditioning. Then a flow-matching transformer, the DiT, turns noise into a detailed latent with that as its guide, and a decoder makes the waveform.

So the song has two stages. Music 3's README calls them a Global LLM and a Local LLM, then hidden-state synthesis with Flow Matching and a Flow-VAE. In the code those are the main model and `audio_decoder` in `ar.py`, the DiT in `dit.py`, and the DAV decoder in `dav.py`.

{{audio:families/mini-max-music3_0.mp3|Prompt: slow cinematic ambient score, warm cello and soft piano, deep pads, golden hour mood, hopeful and calm, instrumental. One seed, a shortened web copy.}}

Because the song comes first, it can set the clock for a whole video:

{{video:pipelines/song_to_video/cut.mp4|Our Song to Video pipeline: Music 3 sang the lyrics first, FLUX.2 Klein drew one keeper and four keyframes with her as the reference, H3 moved each keyframe, and the last step cut on the song's downbeats. 392 frames at 1216 x 672, with the song. Our review lists flaws: in shot 3 the coat turns khaki on top and she carries two lanterns. Whole pipeline: 436.5 s, peak 41.1 GiB.|pipelines/song_to_video/cut.webp}}

## Walk the graph

{{graph:wf_music3}}

**Loaders.** `UNETLoader` loads the DiT. `CLIPLoader` with type `minimax` loads the language model. `VAELoader` loads the DAV.

**`MiniMaxMusic3TextEncode`.** Inputs:

- `caption`: what the music is.
- `lyrics`: the words and the structure.
- `seed`: fed through `derive_seed`, so it picks the composition.
- `max_duration`: a ceiling in seconds, not a target. The model can end the song earlier.
- `cfg_scale` and `top_k`: used inside the code-generating loop. The graph has `cfg_scale` 1.7 and `top_k` 50. The source's defaults are 1.5 and 50.

It has two outputs: conditioning, and `seconds`, which is how long the model actually made it.

**`ConditioningZeroOut`** gives the sampler a negative that's all zeros.

**`EmptyMiniMaxMusic3LatentAudio`** takes `seconds`, wired from the text encoder. That wire matters, as you'll see. It makes `[batch, 128, L]`, where L is `int(frames x 44100 / 24000 x 960 / 512)`, about 86 latent frames a second.

**`KSampler`** at 30 steps, cfg 1.7, euler, simple, on the DiT. Note there are two separate things called CFG in this graph: `cfg_scale` in the loop and `cfg` here.

**Decode.** `VAEDecodeAudio`, or `VAEDecodeAudioTiled` when `ComfySwitchNode` is set to true. `SaveAudioAdvanced` writes FLAC.

## The 128 channels

They aren't 128 features of one signal. `MiniMaxMusic3DAV.decode` reshapes `[B, 128, L]` to `[2B, 64, L]`, decodes, and joins the results: 64 channels for the left ear and 64 for the right. Each latent frame becomes 512 samples at 44100 Hz. That rate is what ComfyUI's code uses, in `latent_length` and in the VAE, and it's what our web copy reports. MiniMax's README says 32 kHz, and we didn't settle why they differ. It's decode only: asking this VAE to encode raises an error, so you can't feed a song back in this way.

## What the model reads

`build_prompt` wraps your text in special tokens. The two cleaners change it first, which explains some odd results:

- Caption: Markdown headers, bullets and bold are removed. A `<|BPM 72|>` tag becomes `BPM is 72`.
- Lyrics: everything in brackets goes on its own line and is lowercased. ` ^ ` becomes a line break. It all starts with `[start]`.

Caption and lyrics together are limited to 5000 tokens.

Our notes recommend a three-block caption with Global Metadata, Vocal Details and Arrangement. In one same-seed test it sang 13 of 16 lyric lines clearly, against 5 of 16 for a one-line prompt. The studio's `music3_styles.json` holds 675 styles in 19 families, mostly from MiniMax's official caption templates, with 41 marked as authored by the studio. Those are starting points to read.

{{play:audiocalls}}

## What goes wrong

- **The song is cut off at the end.** The ceiling stopped it. If the track is exactly `max_duration` long and still loud at the end, raise it and keep the seed. Our notes size it at about 6 seconds per sung line.
- **Seconds typed by hand.** If the latent is longer than the conditioning, the DiT pads the condition with zeros, and the end of your song is generated with no guidance. Wire `seconds` from the text encoder, as the graph does.
- **A long wait with no steps moving.** That's the code-generating loop, inside the encoder node. Our notes say this stage takes most of the time. It isn't stuck.
- **Same seed, different take.** Seed picks the composition in the loop. KSampler's seed picks the DiT noise, and that noise changes when the length changes. Our notes describe a re-render as a fresh render of the same composition.
- **An instrumental hums.** Our notes say a lone `[instrumental]` still hums. Use only non-vocal tags on their own lines, and say "No vocals. Purely instrumental." in the caption. Hand-tested on an older stack. The graph's own `lyrics` is a lone `[instrumental]`, so change that first if you want no voice at all.
- **Words after a tag aren't sung, or they read oddly.** Put each tag on its own line. Our notes rewrite `[Verse 1]` as `[Verse]`, without saying how much it matters.
- **Loudness is the same whatever you do.** `VAEDecodeAudio` rescales: see CU-216. Master afterwards.
- **BPM and key drift.** They're suggestions to the model. Measure them.
- **Licence.** The weights use the MiniMax-Music3 Community License, not an open one. Commercial use needs "MiniMax-Music3" shown prominently in your product's interface, and separate written permission above 20 million US dollars of yearly revenue. A hosted service has further duties. Read `LICENSE` in MiniMax's Hugging Face repository before you ship.

## Lab

From seconds to everything else:

```text
longest allowed: 9000 / 25 = 360 s
seconds   AR frames   8-code groups   latent [B, 128, L]   samples per channel   duration at 44100 Hz
30        750         6,000           [1, 128, 2583  ]      1,322,496             29.989 s
60        1500        12,000          [1, 128, 5167  ]      2,645,504             59.989 s
120       3000        24,000          [1, 128, 10335 ]      5,291,520             119.989 s
360       9000        72,000          [1, 128, 31007 ]      15,875,584            359.991 s
500       9000        72,000          [1, 128, 31007 ]      15,875,584            359.991 s
latent frames a second: 86.132, against 44100 / 512 = 86.133
```

The ceiling shows at 500 seconds: the row is the same as 360. That's the code's limit. The README describes songs up to five minutes, so past 300 seconds you are beyond what MiniMax describes. The DiT doesn't take a whole long song at once. It uses windows of 200 frames, hopping 100, and averages:

```text
DiT window 689 latent frames (8.0 s), hop 344
   5 s: 1 DiT passes per sampling step, with CFG on twice that
  30 s: 7 DiT passes per sampling step, with CFG on twice that
  60 s: 15 DiT passes per sampling step, with CFG on twice that
 120 s: 30 DiT passes per sampling step, with CFG on twice that
```

And the 128 channels:

```text
DAV decode: [1, 128, L] -> [2, 64, L], one 64-channel stream per stereo channel. Values per second 11025 for 88200 samples: 8 to 1
```

Your text before and after the cleaners, from a port of `prompt.py` checked against the real functions:

```text
caption in : '## Global Metadata\n\n- **Genre**: lo-fi\n- <|BPM 72|>'
caption out: 'Global Metadata\nGenre: lo-fi\nBPM is 72'
lyrics in  : '[Verse] Rain on the glass ^ I stay [CHORUS]\nHold on'
lyrics out : '[start]\n[verse]\nRain on the glass\nI stay\n[chorus]\nHold on'
```

Finally the hand-typed seconds mistake:

```text
The AR stage stops at 21 s and you typed 30 s by hand: 775 latent frames, 9.0 s, are decoded with a zero condition
```

## Sources

- [MiniMax Music 3 README](https://github.com/MiniMax-AI/MiniMax-Music3)
- [ComfyUI v0.43.0, comfy_extras/nodes_minimax_music.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_minimax_music.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax_music/ar.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax_music/ar.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax_music/dit.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax_music/dit.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax_music/dav.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax_music/dav.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax_music/prompt.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax_music/prompt.py)
- [ComfyUI v0.43.0, comfy/text_encoders/minimax_music.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/text_encoders/minimax_music.py)
