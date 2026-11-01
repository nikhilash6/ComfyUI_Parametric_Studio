# CU-511 lab: how three families of audio model spend their model calls. Numbers are from the papers and from ComfyUI v0.43.0 source named beside each. CPU, seeded.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
# 1. Autoregression: one call per step, in order. A dilated causal stack sees further at the same depth. Measured by autograd.
def wavenet_rf(dilations):
    x = torch.zeros(1, 1, 2049, requires_grad=True); y = x
    for d in dilations: y = torch.nn.functional.conv1d(y, torch.ones(1, 1, 2), dilation=d) + 1
    y[0, 0, -1].backward(); return int((x.grad != 0).sum().item())
dil = [2 ** i for i in range(10)]; print("dilations 1, 2, 4 ... 512, kernel 2:", wavenet_rf(dil), "samples seen, against", wavenet_rf([1] * 10), "with no dilation at the same 10 layers")
assert wavenet_rf(dil) == 1024 and wavenet_rf([1] * 10) == 11
# 2. Model calls for 30 seconds of sound.
def table(seconds):
    rows = []
    rows.append(("WaveNet, one call per sample at 16 kHz", 16000 * seconds, "sequential"))
    rows.append(("MusicGen, delay pattern, 50 steps/s", 50 * seconds, "sequential"))
    rows.append(("Music 3 AR stage, main model, 25 frames/s", 25 * seconds, "sequential"))
    rows.append(("Music 3 DiT, 30 steps, CFG on", 30 * 2, "each call covers the song, in windows"))
    rows.append(("Stable Audio style diffusion, 30 steps, CFG on", 30 * 2, "each call covers the clip"))
    return rows
print("\nmodel                                            calls for 30 s   how")
for n, c, h in table(30): print(f"{n:48s} {c:<16,d} {h}")
for n, c, h in table(120)[:3]: pass
print("\nat 120 s the sequential counts multiply by 4; the diffusion step count does not change, each call just gets longer")
assert table(120)[2][1] == 4 * table(30)[2][1] and table(120)[4][1] == table(30)[4][1]
# MiniMaxMusic3DiT's window loop in comfy/ldm/minimax_music/dit.py: audio frames at 25 a second, windows of 200 frames, hop of 100.
def latent_length(frames): return max(1, int(frames * 44100 / 24000 * 960 / 512))
def passes(seconds):
    n = latent_length(25 * seconds); window = latent_length(200); hop = latent_length(100); start = 0; count = 0
    if n <= window: return 1
    while True:
        count += 1
        if min(start + window, n) == n: return count
        start += hop
print(f"\nMusic 3 DiT passes per model call, window 8 s, hop 4 s: 30 s -> {passes(30)}, 120 s -> {passes(120)}")
# 3. Sequential generation means a sample can't be made before the one it depends on. Noise-to-data flow updates every position together.
x = torch.tensor([1.0, -2.0, 3.0, 0.5]); e = torch.randn(4)
print("\nflow matching on 4 latent values, x_sigma = (1 - sigma) x + sigma noise:")
for s in (1.0, 0.5, 0.0):
    print(f"sigma {s:<4}: " + " ".join(f"{v:+.3f}" for v in ((1 - s) * x + s * e).tolist()))
assert torch.equal((1 - 0.0) * x + 0.0 * e, x)
# 4. Euler with the perfect model reaches x in one step for this straight path. Real models don't, so they take many.
s = torch.linspace(1, 0, 11); z = e.clone(); v = e - x
for a, b in zip(s, s[1:]): z = z + (b - a) * v
print("Euler on the straight path with a perfect velocity, 10 steps, error", f"{(z - x).abs().max().item():.1e}")
assert (z - x).abs().max() < 1e-5
# 5. Finite scalar quantization, as in ACE-Step's tokenizer idea: round each number to a few levels. No codebook lookup.
def fsq(z, levels): half = (levels - 1) / 2; return torch.round(torch.tanh(z) * half) / half
print("\nFSQ with 5 levels:", [round(v, 2) for v in fsq(torch.tensor([-2.0, -0.3, 0.1, 0.9]), 5).tolist()], "a token, but ACE-Step still generates by a diffusion transformer, not by predicting tokens one by one")
