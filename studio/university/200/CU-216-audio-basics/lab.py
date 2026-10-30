# CU-216 lab: sampling, the DFT and its window, the mel scale, and how ComfyUI turns seconds into audio latents.
# Run: python lab.py  (CPU only, a second or two). Prints the same numbers every time.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
def peak_hz(x, sr): return torch.argmax(torch.fft.rfft(x).abs()).item() * sr / len(x)

# 1. Aliasing. One second of a cosine at f, sampled at 10 kHz. The DFT bins are exactly 1 Hz apart. Above 5 kHz the tone folds back.
sr = 10000; t = torch.arange(sr, dtype=D) / sr
print("sample rate 10000 Hz, Nyquist 5000 Hz.  tone in -> peak found -> predicted |f - sr * round(f / sr)|")
for f in (1000, 4000, 6000, 8000, 9000, 11000):
    found = peak_hz(torch.cos(2 * math.pi * f * t), sr); pred = abs(f - sr * round(f / sr)); print(f"{f:>6d} Hz -> {found:>6.0f} Hz   {pred:>5d} Hz"); assert found == pred

# 2. Bins and windows. 1024 samples at 44100 Hz: a bin is 43.07 Hz wide, so a 440 Hz sine falls between bins 10 and 11.
sr = 44100; n = 1024; x = torch.sin(2 * math.pi * 440 * torch.arange(n, dtype=D) / sr)
print(f"\nn_fft {n}, sample rate {sr}: bin width {sr / n:.2f} Hz, a 440 Hz sine, estimates from a parabola through the three bins around the peak")
res = {}
for name, w in (("rectangular window", torch.ones(n, dtype=D)), ("Hann window", torch.hann_window(n, dtype=D))):
    m = torch.fft.rfft(x * w).abs(); k = torch.argmax(m).item(); a, b, c = m[k - 1].log(), m[k].log(), m[k + 1].log(); est = (k + 0.5 * (a - c) / (a - 2 * b + c)).item() * sr / n
    res[name] = (k, est, 20 * math.log10(m[k + 20].item() / m[k].item()))
    print(f"  {name:19s} peak bin {k} = {k * sr / n:.2f} Hz, estimate {est:.2f} Hz, level 20 bins from the peak {res[name][2]:.1f} dB")
assert abs(res["Hann window"][1] - 440) < 1 and res["Hann window"][2] < res["rectangular window"][2] - 40

# 3. The trade between frequency and time. Two equal tones, 440 and 460 Hz, a Hann window. A longer window has narrower bins and spans more time.
#    "Dip" is how far the spectrum falls at 450 Hz, midway between the tones, below its highest value between 430 and 470 Hz (average over 8 relative phases).
print("\nn_fft   bin width    window length   dip between tones at 440 and 460 Hz")
dips = {}
for n in (1024, 2048, 4096, 8192, 16384):
    t = torch.arange(n, dtype=D) / sr; vals = []
    for j in range(8):
        x = (torch.sin(2 * math.pi * 440 * t) + torch.sin(2 * math.pi * 460 * t + math.pi * j / 4)) * torch.hann_window(n, dtype=D)
        m = torch.fft.rfft(x, n=8 * n).abs(); f = torch.arange(len(m), dtype=D) * sr / (8 * n); mid = m[(f - 450).abs().argmin()]; top = m[(f > 430) & (f < 470)].max(); vals.append(20 * math.log10(mid / top))
    dips[n] = sum(vals) / len(vals); print(f"{n:<7d} {sr / n:<6.2f} Hz   {n / sr * 1000:<8.1f} ms     {dips[n]:.1f} dB")
assert dips[1024] > -1 and dips[16384] < -20

# 4. The mel scale as comfy/audio.py builds it (Slaney): linear below 1000 Hz, logarithmic above, 27 mels per factor of 6.4 in frequency.
def hz_to_mel(f): return 15.0 + math.log(f / 1000.0) / (math.log(6.4) / 27.0) if f >= 1000.0 else f / (200.0 / 3)
print("\nHz     " + "  ".join(f"{f:>6d}" for f in (100, 500, 1000, 2000, 4000, 8000, 16000)))
print("mel    " + "  ".join(f"{hz_to_mel(f):>6.2f}" for f in (100, 500, 1000, 2000, 4000, 8000, 16000)))
print(f"linear part: one mel is {200 / 3:.2f} Hz.  log part: one mel multiplies the frequency by 6.4 ** (1 / 27) = {6.4 ** (1 / 27):.7f}")
n_mels, fmax = 128, 22050; mels = torch.linspace(hz_to_mel(0.0), hz_to_mel(fmax), n_mels + 2, dtype=D); hz = (200.0 / 3) * mels; hi = mels >= 15.0
hz[hi] = 1000.0 * torch.exp((math.log(6.4) / 27.0) * (mels[hi] - 15.0)); centers = hz[1:-1]; bin_hz = 44100 / 2048
print(f"128 mel bands up to {fmax} Hz, n_fft 2048 ({bin_hz:.2f} Hz per bin): spacing of band centres {centers[1] - centers[0]:.1f} Hz at the bottom, {centers[-1] - centers[-2]:.1f} Hz at the top, which is {(centers[1] - centers[0]) / bin_hz:.1f} and {(centers[-1] - centers[-2]) / bin_hz:.1f} bins")
assert abs(hz_to_mel(1000.0) - 15.0) < 1e-9

# 5. Seconds to audio latents as in comfy_extras/nodes_audio.py (EmptyLatentAudio): length = round((seconds * 44100 / 2048) / 2) * 2, 64 channels.
print("\nseconds   latent length   duration of that length")
for s in (1.0, 10.0, 30.0, 47.6):
    L = round((s * 44100 / 2048) / 2) * 2; print(f"{s:<9} {L:<15d} {L * 2048 / 44100:.3f} s")
print(f"latent frames per second {44100 / 2048:.2f}; stereo samples per second {2 * 44100}, latent values per second {64 * 44100 / 2048:.1f}: {2 * 44100 / (64 * 44100 / 2048):.0f} to 1")

# 6. VAEDecodeAudio rescales its output: audio / max(1, 5 * std). Quiet audio is left alone, louder audio is brought to std 0.2.
tt = torch.arange(44100, dtype=D) / 44100
print("\nsine amplitude   std before   std after")
for a in (0.05, 0.2, 0.3, 0.9):
    y = a * torch.sin(2 * math.pi * 440 * tt); sd = y.std().item() * 5.0; sd = max(sd, 1.0); z = y / sd; print(f"{a:<16} {y.std().item():<12.4f} {z.std().item():.4f}")

# 7. Dropping samples without a low-pass filter. 16 kHz audio with a 6 kHz tone, halved to 8 kHz (new Nyquist 4 kHz). The tone should vanish.
sr = 16000; x = torch.sin(2 * math.pi * 6000 * torch.arange(sr, dtype=D) / sr)
half = 64; k = torch.arange(-half, half + 1, dtype=D); h = 2 * 0.22 * torch.sinc(2 * 0.22 * k) * torch.hann_window(2 * half + 1, dtype=D); h = h / h.sum()
naive = x[::2]; filtered = torch.nn.functional.conv1d(x.reshape(1, 1, -1), h.reshape(1, 1, -1), padding=half)[0, 0][::2]
amp = lambda y: torch.fft.rfft(y).abs().max().item() * 2 / len(y)
print(f"\n6 kHz tone, 16 kHz -> 8 kHz: amplitude of what remains, taking every second sample {amp(naive):.4f} (at {peak_hz(naive, 8000):.0f} Hz), with a low-pass first {amp(filtered):.4f}")
assert amp(naive) > 0.9 and amp(filtered) < 0.01
