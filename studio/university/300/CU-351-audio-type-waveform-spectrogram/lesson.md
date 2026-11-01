# CU-351 - Waveform, sample rate and spectrograms: ComfyUI's AUDIO type

**Objective.** Say what an AUDIO value holds, predict what each core audio node does to it, and read a spectrogram. Taught by DJ Spectrogram.

## The idea

An image in ComfyUI is one tensor. Audio is two things: a tensor of samples and the rate they were recorded at. Neither means anything alone. 88,200 samples is 2 seconds at 44100 Hz and 2.76 seconds at 32000 Hz.

```
{"waveform": tensor [batch, channels, samples], "sample_rate": 44100}
```

Values are floats, usually between -1 and 1. Stereo has 2 channels, mono has 1. Note the channel comes first here, unlike images, where it comes last.

## Your graph, with no model

Run this now. It needs no GPU.

{{graph:nm_audio}}

Silence you can't hear, but the file is real: open it and check the length. Here is the same thing, taken apart:

{{graph:e_audio_channels}}

## What the nodes do

- **`EmptyAudio`:** zeros, with `round(duration x sample_rate)` samples.
- **`AudioAdjustVolume`:** multiplies by 10 to the power dB / 20. So -6 dB is about 0.5 and +6 dB is about 2. There's no limiter, so values can pass 1.
- **`TrimAudioDuration`:** cuts by seconds, using the stored rate.
- **`SplitAudioChannels` and `JoinAudioChannels`:** stereo to two single channels and back.
- **`AudioConcat`:** end to end, in either order. It doubles mono to stereo, and if the rates differ, it resamples the lower one up.
- **`AudioMerge`:** mixes two together, with the same rate matching.
- **`AudioEqualizer3Band`:** low, mid and high gain.
- **`VAEDecodeAudio`:** returns this same type, with the VAE's own rate. It also rescales: see CU-216.

Different models give you different rates. Check before you mix them.

| source | sample rate | channels |
|---|---|---|
| MiniMax H3 audio VAE | 32000 | 2 |
| MiniMax Music 3 DAV | 44100 | 2 |
| Stable Audio family, by default | 44100 | 2 |
| LTX-2.5, gallery file | 48000 | 2 |

{{audio:showcase/a_score.m4a|A Music 3 score from our gallery, 44100 Hz stereo. Prompt: epic cinematic trailer score, deep brass, driving taiko drums, soaring strings, instrumental. One seed.}}

## Seeing a sound

A waveform shows loudness over time. It hides pitch. A spectrogram cuts the sound into short overlapping windows, runs a Fourier transform on each, and stacks the results: time across, frequency up, brightness for strength.

The window length is the one big choice. A long window tells nearby notes apart and smears a drum hit across time. A short one does the opposite. You can't have both at once.

{{play:spectro}}

Core has no general node that draws a spectrogram. We found them only inside model code, like `LogMelSpectrogram` for ACE-Step and `_compute_mel_spectrogram` for Wan Dancer. So this view is something you get from the browser lab above, from a pack, or from your own script.

## What goes wrong

- **A clip plays at the wrong pitch and speed.** Samples were written with the wrong rate. Nothing checks this for you if a custom node forgets it. Keep the rate with the tensor.
- **A 32000 Hz track feels dull next to a 48000 Hz one.** A 32000 Hz file can't hold anything above 16000 Hz. Resampling up to mix doesn't bring it back.
- **Harsh distortion after raising volume.** Gain has no limiter. A 0.5 peak with +12 dB reaches 1.99. Lower it, or master afterwards.
- **A shape error from your own node.** The order is batch, channels, samples. A tensor of `[samples, channels]` from a library like soundfile needs rearranging first.
- **Merging gives an unexpected length.** Merging and joining have to reconcile different lengths. `JoinAudioChannels` trims to the shorter one. Read the log line, or check the length.
- **A long song uses more RAM than you'd expect?** It uses less than you think: 300 s of stereo is only 100.9 MiB, tiny next to video. If memory fails, look at the model, not the waveform.

## Lab

The lab builds these values the way the nodes do. The shape first:

```text
EmptyAudio(1.0 s, 44100, 2): [1, 2, 44100] [batch, channels, samples], sample_rate 44100
```

Volume, and what the rate means:

```text
volume dB   gain      peak of a 0.5 peak sine
-6          0.5012    0.2506
0           1.0000    0.5000
6           1.9953    0.9976
12          3.9811    1.9905
a peak above 1.0 is not clipped by this node; nothing here limits it
88200 samples read at 32000 Hz last 2.756 s
88200 samples read at 44100 Hz last 2.000 s
88200 samples read at 48000 Hz last 1.837 s
```

Trim and the rate rule for joining:

```text
trim 0.25 s from 0.5 s at 44100 Hz: 11025 samples
AudioConcat of 32000 Hz (H3) and 44100 Hz (Music 3): both become 44100 Hz
```

A spectrogram with `torch.stft` on 440 Hz plus 880 Hz. With a 128-sample window, a bin is 125 Hz wide, and the peak reads 500 Hz. At 512 and 2048 it reads 437.5 Hz, the bin nearest 440:

```text
n_fft   hop    frames  bins   Hz per bin  ms per window  strongest bin in the first half
128     32     501     65     125.00      8.0            4 = 500.0 Hz
512     128    126     257    31.25       32.0           14 = 437.5 Hz
2048    512    32      1025   7.81        128.0          56 = 437.5 Hz
```

A single-sample click, in the two windows. It's one sample long, but in the picture it covers about as long as the window:

```text
the single-sample click with n_fft 128: visible in 3 frames, 6 ms of the picture
the single-sample click with n_fft 2048: visible in 4 frames, 128 ms of the picture
```

And memory:

```text
30 s of stereo at 44100 Hz in RAM as float32: 10.1 MiB
300 s of stereo at 44100 Hz in RAM as float32: 100.9 MiB
```

## Sources

- [ComfyUI v0.43.0, comfy_extras/nodes_audio.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_audio.py)
- [ComfyUI v0.43.0, comfy/audio.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/audio.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/ldm/minimax/audio_vae.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/minimax/audio_vae.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_wandancer.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_wandancer.py)
