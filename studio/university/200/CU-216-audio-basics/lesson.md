# CU-216 - Audio and music basics: waveforms to spectrograms

**Objective.** Predict where a tone lands in a spectrum, including when it folds back, explain the trade between frequency detail and time detail, and read how ComfyUI's audio models turn seconds into latents. Taught by DJ Spectrogram.

## The idea

Sound on a computer is a pressure signal measured many times a second. ComfyUI's audio models do not generate those samples one by one. Some compress the waveform with a VAE, at 2048 samples per latent frame in the Stable Audio family. Others first turn it into a log-mel spectrogram, a picture of energy by time and pitch, and encode that picture the way an image model would, as ACE-Step does. Sampling, the Fourier transform, windows and the mel scale decide what survives either route.

## The maths

**Sampling.** Shannon (1949) states it as Theorem 1: a function with no frequencies above W cycles per second is completely determined by its values at points spaced 1/2W seconds apart. So a sample rate sr holds frequencies up to sr / 2, the Nyquist frequency. A tone above that does not vanish. It folds back and appears at |f − sr · round(f / sr)|.

**The DFT.** N samples give N/2 + 1 frequency bins, sr / N Hz apart. A tone that falls between bins leaks into its neighbours, and a window tapers the frame to limit that. The Hann window is w[n] = ½ [1 − cos(2πn / N)] in its periodic form, which is torch's default, and the symmetric form has N − 1 in place of N.

**The STFT.** Cut the signal into frames of n_fft samples, one every `hop` samples, window each and transform it. A frame lasts n_fft / sr seconds and its bins are sr / n_fft Hz apart, so a longer frame gains frequency detail and loses time detail. Both cannot improve together.

**The mel scale.** The mel scale spaces frequencies finely at the bottom and coarsely at the top, which is meant to follow how differences in pitch are heard. ComfyUI's `comfy/audio.py` uses the Slaney form: linear below 1000 Hz, where one mel is 200/3 Hz, and logarithmic above, with 27 mels for each factor of 6.4 in frequency. Slaney's Auditory Toolbox report describes a filterbank whose 27 log-spaced filters are separated by a factor of 1.0711703, which is 6.4 raised to 1/27. The filters are triangles whose weights are divided by their width, which torchaudio's documentation calls area normalization.

## In ComfyUI

**Seconds to latents.** `EmptyLatentAudio` in `comfy_extras/nodes_audio.py` (default 47.6 seconds) makes a latent of shape [batch, 64, length] with length = round((seconds · 44100 / 2048) / 2) · 2, and tags it with a temporal downscale ratio of 2048. `AudioOobleckVAE` in `comfy/ldm/audio/autoencoder.py` takes stereo (2 channels) with strides [2, 4, 4, 8, 8], which multiply to 2048, a latent size of 64, and Snake activations. The Stable Audio Open paper describes an autoencoder with 5 strided convolutional blocks, a latent size of 64 and a latent rate of 21.5 Hz. When the loader in `comfy/sd.py` finds weights for a variant with strides [2, 4, 4, 6, 10], it sets 48000 Hz and a ratio of 1920.

**Resampling.** `VAEEncodeAudio` resamples audio to the VAE's sample rate, 44100 Hz by default, with `resample` in `comfy/audio.py`. Its docstring calls it bandlimited sinc resampling, with a Hann-windowed sinc as the default method.

**Loudness on the way out.** `VAEDecodeAudio` divides the decoded waveform by max(1, 5 × its standard deviation) for each item in the batch.

**Mel route.** `MusicDCAE` in `comfy/ldm/ace/vae/music_dcae_pipeline.py` computes a log-mel spectrogram of the audio with `LogMelSpectrogram`, whose defaults are a Hann window, n_fft 2048, hop 512 and 128 mel bands. It rescales the values from the range −11 to 3 into 0 to 1, and encodes them with an image autoencoder, `AutoencoderDC`. Decoding goes the other way, from latents to a mel spectrogram, and a vocoder turns that into a waveform. A mel spectrogram has lost the phase, so the vocoder has to invent it.

## Lab

First aliasing. One second of a cosine at 10 kHz sampling, so the bins are exactly 1 Hz apart:

```text
sample rate 10000 Hz, Nyquist 5000 Hz.  tone in -> peak found -> predicted |f - sr * round(f / sr)|
  1000 Hz ->   1000 Hz    1000 Hz
  4000 Hz ->   4000 Hz    4000 Hz
  6000 Hz ->   4000 Hz    4000 Hz
  8000 Hz ->   2000 Hz    2000 Hz
  9000 Hz ->   1000 Hz    1000 Hz
 11000 Hz ->   1000 Hz    1000 Hz
```

A 6 kHz tone sampled at 10 kHz is heard as 4 kHz. The formula predicts every row. Next a window. A 440 Hz sine in a 1024-sample frame at 44100 Hz falls between bins 10 and 11, so the peak bin reads 430.66 Hz. A parabola through the log magnitudes of the three bins round the peak refines that:

```text
n_fft 1024, sample rate 44100: bin width 43.07 Hz, a 440 Hz sine, estimates from a parabola through the three bins around the peak
  rectangular window  peak bin 10 = 430.66 Hz, estimate 434.00 Hz, level 20 bins from the peak -37.4 dB
  Hann window         peak bin 10 = 430.66 Hz, estimate 440.63 Hz, level 20 bins from the peak -91.2 dB
```

Twenty bins from the peak, the Hann window leaks at -91.2 dB against -37.4 dB for the rectangular window, and its refined estimate, 440.63 Hz, is within 1 Hz of the truth. Now the trade. Two equal tones 20 Hz apart, at 440 and 460 Hz, and a "dip", how far the spectrum falls midway between them below its highest value:

```text
n_fft   bin width    window length   dip between tones at 440 and 460 Hz
1024    43.07  Hz   23.2     ms     -0.9 dB
2048    21.53  Hz   46.4     ms     -1.7 dB
4096    10.77  Hz   92.9     ms     -4.5 dB
8192    5.38   Hz   185.8    ms     -28.1 dB
16384   2.69   Hz   371.5    ms     -44.1 dB
```

With a 23 ms frame the two tones are one hump. They separate clearly at 8192 samples, 186 ms, where a bin is 5.38 Hz wide against the 20 Hz gap. A frame that long cannot place a drum hit more precisely than its own length. The mel scale, built the way ComfyUI builds it:

```text
Hz        100     500    1000    2000    4000    8000   16000
mel      1.50    7.50   15.00   25.08   35.16   45.25   55.33
linear part: one mel is 66.67 Hz.  log part: one mel multiplies the frequency by 6.4 ** (1 / 27) = 1.0711703
128 mel bands up to 22050 Hz, n_fft 2048 (21.53 Hz per bin): spacing of band centres 31.0 Hz at the bottom, 672.0 Hz at the top, which is 1.4 and 31.2 bins
```

The factor 1.0711703 matches the one in Slaney's report. Band centres are 1.4 bins apart at the bottom and 31.2 bins apart at the top, so the spectrogram keeps fine detail at low frequencies and pools the high ones. Now ComfyUI's latent length for audio, and what the compression is:

```text
seconds   latent length   duration of that length
1.0       22              1.022 s
10.0      216             10.031 s
30.0      646             30.000 s
47.6      1024            47.554 s
latent frames per second 21.53; stereo samples per second 88200, latent values per second 1378.1: 64 to 1
```

The length is rounded to an even number, so the duration the latent covers is close to the request and not exact. The default of 47.6 seconds gives 1024 latent frames. Then the decode-side rescaling, on sines of different amplitudes:

```text
sine amplitude   std before   std after
0.05             0.0354       0.0354
0.2              0.1414       0.1414
0.3              0.2121       0.2000
0.9              0.6364       0.2000
```

Quiet audio is left alone. Anything with a standard deviation above 0.2 comes out at 0.2, so the loudness of decoded audio is set by this rule and not by the model. Last, why resampling needs a filter. A 6 kHz tone at 16 kHz is halved to 8 kHz, where the Nyquist frequency is 4 kHz:

```text
6 kHz tone, 16 kHz -> 8 kHz: amplitude of what remains, taking every second sample 1.0000 (at 2000 Hz), with a low-pass first 0.0000
```

Taking every second sample moves the tone to 2 kHz at full strength. A low-pass filter first, which is what the sinc in `resample` does, removes it.

## What is contested

The mel scale is an approximation of hearing, and there is more than one version of it: torchaudio's `melscale_fbanks` defaults to the HTK scale and offers Slaney as an option, and ComfyUI uses Slaney. The dips in the lab are for equal tones. Unequal tones and other windows resolve differently, and the Hann window shown is the periodic form. We did not run an audio VAE or a vocoder, so nothing here measures audio quality, and the claim that a mel spectrogram loses phase is a property of taking magnitudes, not something the lab tests.

## Sources

- [Shannon 1949. Communication in the Presence of Noise. Proc. IRE 37(1), 10-21](https://doi.org/10.1109/JRPROC.1949.232969)
- [Slaney 1998. Auditory Toolbox, Version 2 (Interval Research Technical Report 1998-010)](https://engineering.purdue.edu/~malcolm/interval/1998-010/AuditoryToolboxTechReport.pdf)
- [Evans et al. 2024. Stable Audio Open](https://arxiv.org/abs/2407.14358)
- [torchaudio.functional.melscale_fbanks documentation](https://docs.pytorch.org/audio/stable/generated/torchaudio.functional.melscale_fbanks.html)
- [torch.hann_window documentation (PyTorch 2.15)](https://docs.pytorch.org/docs/2.15/generated/torch.hann_window.html)
- [ComfyUI v0.43.0, comfy_extras/nodes_audio.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_audio.py)
- [ComfyUI v0.43.0, comfy/audio.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/audio.py)
- [ComfyUI v0.43.0, comfy/ldm/audio/autoencoder.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/audio/autoencoder.py)
- [ComfyUI v0.43.0, comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/sd.py)
- [ComfyUI v0.43.0, comfy/ldm/ace/vae/music_log_mel.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/ace/vae/music_log_mel.py)
- [ComfyUI v0.43.0, comfy/ldm/ace/vae/music_dcae_pipeline.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/ace/vae/music_dcae_pipeline.py)
