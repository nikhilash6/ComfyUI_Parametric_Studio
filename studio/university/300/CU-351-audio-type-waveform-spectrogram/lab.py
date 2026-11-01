# CU-351 lab: ComfyUI's AUDIO value, with the same steps as comfy_extras/nodes_audio.py (ComfyUI v0.43.0), then a spectrogram. CPU, seeded.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
# EmptyAudio: {"waveform": zeros(1, channels, round(duration * sample_rate)), "sample_rate": sr}
def empty_audio(duration, sr, ch): return {"waveform": torch.zeros((1, ch, int(round(duration * sr))), dtype=torch.float32), "sample_rate": sr}
a = empty_audio(1.0, 44100, 2); print("EmptyAudio(1.0 s, 44100, 2):", list(a["waveform"].shape), "[batch, channels, samples], sample_rate", a["sample_rate"])
assert a["waveform"].shape == (1, 2, 44100)
# AudioAdjustVolume: gain = 10 ** (dB / 20)
print("\nvolume dB   gain      peak of a 0.5 peak sine")
t = torch.arange(44100, dtype=torch.float64) / 44100
for db in (-6, 0, 6, 12):
    g = 10 ** (db / 20); print(f"{db:<11d} {g:<9.4f} {0.5 * g:.4f}")
print("a peak above 1.0 is not clipped by this node; nothing here limits it")
# What duration a tensor means depends on the rate stored beside it.
n = 88200
for sr in (32000, 44100, 48000): print(f"{n} samples read at {sr} Hz last {n / sr:.3f} s")
# TrimAudioDuration: start and end indices from seconds.
def trim(w, sr, start, dur):
    s = int(round(start * sr)); return w[..., s:s + int(round(dur * sr))]
print("\ntrim 0.25 s from 0.5 s at 44100 Hz:", trim(a["waveform"], 44100, 0.5, 0.25).shape[-1], "samples")
# match_audio_sample_rates: AudioConcat and AudioMerge resample the lower rate up to the higher one. Mono is doubled by AudioConcat.
def concat_rate(a_sr, b_sr): return max(a_sr, b_sr)
print("AudioConcat of 32000 Hz (H3) and 44100 Hz (Music 3): both become", concat_rate(32000, 44100), "Hz")
# A spectrogram, by hand with torch.stft: 440 Hz + 880 Hz, then silence, then a click.
sr = 16000; T = torch.arange(sr, dtype=torch.float32) / sr
x = torch.sin(2 * math.pi * 440 * T) + 0.5 * torch.sin(2 * math.pi * 880 * T); x[sr // 2:] = 0; x[3 * sr // 4] = 1.0
print("\nn_fft   hop    frames  bins   Hz per bin  ms per window  strongest bin in the first half")
for nfft in (128, 512, 2048):
    hop = nfft // 4; S = torch.stft(x, nfft, hop, window=torch.hann_window(nfft), return_complex=True).abs()
    frames = S.shape[1]; peak = S[:, : frames // 3].mean(1).argmax().item()
    print(f"{nfft:<7d} {hop:<6d} {frames:<7d} {S.shape[0]:<6d} {sr / nfft:<11.2f} {nfft / sr * 1000:<14.1f} {peak} = {peak * sr / nfft:.1f} Hz")
S = torch.stft(x, 2048, 512, window=torch.hann_window(2048), return_complex=True).abs(); pk = S[:, :10].mean(1).argmax().item() * sr / 2048
assert abs(pk - 440) < 8
# A click in short and long windows: how many frames light up? The energy spreads in time with the window.
def click_frames(nfft):
    hop = nfft // 4; S = torch.stft(x, nfft, hop, window=torch.hann_window(nfft), return_complex=True).abs()[:, :]
    e = S.pow(2).sum(0); start = int(0.6 * sr / hop); return int((e[start:] > 1e-6).sum().item()), (e[start:] > 1e-6).sum().item() * hop / sr * 1000
for nfft in (128, 2048):
    f, ms = click_frames(nfft); print(f"the single-sample click with n_fft {nfft}: visible in {f} frames, {ms:.0f} ms of the picture")
# Bytes. A float32 waveform in RAM, stereo.
for s in (30, 300): print(f"{s} s of stereo at 44100 Hz in RAM as float32: {s * 44100 * 2 * 4 / 1024 ** 2:.1f} MiB")
