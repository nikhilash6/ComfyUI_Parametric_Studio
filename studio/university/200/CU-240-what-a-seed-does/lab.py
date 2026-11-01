# CU-240 lab: what a seed makes. Follows prepare_noise in comfy/sample.py and default_noise_sampler in comfy/k_diffusion/sampling.py.
import math, torch
torch.set_num_threads(1)
def prepare_noise(shape, seed, inds=None):
    g = torch.manual_seed(seed)
    if inds is None: return torch.randn(shape, dtype=torch.float32, generator=g, device="cpu")
    uniq = sorted(set(inds)); ns = {}
    for i in range(uniq[-1] + 1):
        n = torch.randn((1,) + tuple(shape[1:]), dtype=torch.float32, generator=g, device="cpu")
        if i in uniq: ns[i] = n
    return torch.cat([ns[i] for i in inds], 0)
SD = (1, 4, 64, 64)
a = prepare_noise(SD, 42); b = prepare_noise(SD, 42); c = prepare_noise(SD, 43)
print("512x512 SD latent: values", a.numel(), " mean", f"{a.mean():+.4f}", " std", f"{a.std():.4f}")
print("seed 42 twice, identical:", bool(torch.equal(a, b)), "  seeds 42 and 43, correlation:", f"{torch.corrcoef(torch.stack([a.flatten(), c.flatten()]))[0, 1]:+.4f}")
assert torch.equal(a, b)
print("first three values, seed 0:", [round(v, 4) for v in prepare_noise((1, 4, 8, 8), 0).flatten()[:3].tolist()], " seed 1:", [round(v, 4) for v in prepare_noise((1, 4, 8, 8), 1).flatten()[:3].tolist()])
# A bigger latent starts with the same numbers, so changing the height keeps part of the noise.
t = prepare_noise((1, 4, 96, 64), 42).flatten(); print("same seed, 512x768 against 512x512, shared opening values:", int((t[:a.numel()] == a.flatten()).long().cumprod(0).sum()), "of", a.numel())
print("\nbatches: one block of noise, cut into images")
B = prepare_noise((4, 4, 64, 64), 42)
print("batch item 0 equals the single image with that seed:", bool(torch.equal(B[0], a[0]))); assert torch.equal(B[0], a[0])
print("batch item 1 equals seed 43:", bool(torch.equal(B[1], c[0])))
print("\nLatentFromBatch keeps batch_index, and the generator skips ahead to it")
print("shape                  values per item  multiple of 16  picked item equals the batch item")
res = {}
for sh in ((4, 4, 64, 64), (4, 16, 128, 128), (4, 4, 65, 65), (4, 4, 66, 65), (4, 16, 65, 65)):
    n = sh[1] * sh[2] * sh[3]; B = prepare_noise(sh, 7); p = prepare_noise(sh, 7, inds=[2]); res[sh] = bool(torch.equal(p[0], B[2])); print(f"{str(sh):22s} {n:<16d} {str(n % 16 == 0):<15s} {res[sh]}")
assert res[(4, 4, 64, 64)] and not res[(4, 4, 65, 65)]
f = prepare_noise((4, 4, 64, 64), 42, inds=[0, 0, 0, 0]); print("seed_behavior fixed, batch_index [0,0,0,0], all four the same:", bool(torch.equal(f[0], f[3])))
# Spectra
def radial(x, bands=8):
    p = torch.fft.fft2(x).abs() ** 2; h, w = x.shape; fy = torch.fft.fftfreq(h)[:, None]; fx = torch.fft.fftfreq(w)[None]; r = (fx ** 2 + fy ** 2).sqrt(); out = []
    for i in range(bands):
        m = (r > i * .5 / bands) & (r <= (i + 1) * .5 / bands); out.append(p[m].mean().item())
    mean = sum(out) / bands; return [v / mean for v in out]
def filt(x, power):                                    # multiply the spectrum by |f|^power; power falls as |f|^(2 power)
    h, w = x.shape; r = (torch.fft.fftfreq(w)[None] ** 2 + torch.fft.fftfreq(h)[:, None] ** 2).sqrt(); r[0, 0] = 1.; y = torch.fft.ifft2(torch.fft.fft2(x) * r ** power).real; return (y - y.mean()) / y.std()
w = torch.randn(512, 512, generator=torch.manual_seed(1))
print("\npower in eight bands, low frequency first, 1.00 is a fair share")
show = lambda n, b: print(f"{n:30s} " + " ".join(f"{v:5.2f}" for v in b))
rw = radial(w); show("white, torch.randn", rw); pk = radial(filt(w, -.5)); show("pink, power 1/f", pk); br = radial(filt(w, -1.)); show("named blue by one pack, 1/f^2", br); bl = radial(filt(w, .5)); show("real blue, power rises with f", bl)
assert max(rw) < 1.1 and min(rw) > .9 and br[0] > br[-1] * 50 and bl[-1] > bl[0] * 5
# From measures.json: the same question asked of core's two noise sources, on a real tensor.
M = {"default_noise_sampler (torch.randn)": [0.941, 1.006, 1.016, 1.005, 1.017, 1.003, 1.009, 1.005, 0.983, 0.988, 1.012, 0.991, 1.009, 0.996, 1.007, 1.011], "BrownianTreeNoiseSampler increment": [0.962, 1.015, 1.018, 0.963, 1.001, 1.011, 1.008, 0.982, 1.013, 1.01, 0.993, 1.004, 0.996, 1.01, 1.006, 1.008]}
print("\nour measures.json, 16 bands")
for k, v in M.items(): print(f"{k:38s} lowest {min(v):.3f}  highest {max(v):.3f}")
# Per-step noise: seed + 1 on the CPU, seed on a GPU, in a generator of its own.
print("\ndefault_noise_sampler seeds: on the CPU seed + 1 =", 42 + 1, ", on any other device seed =", 42)
