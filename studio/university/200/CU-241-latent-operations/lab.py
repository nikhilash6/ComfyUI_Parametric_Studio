# CU-241 lab: the latent nodes as sums, and why multiplying changes the picture. Follows comfy_extras/nodes_latent.py, comfy/latent_formats.py, latent_preview.py and comfy/model_sampling.py.
import math, torch
import torch.nn.functional as F
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
def multiply(s, k): return s * k                                    # LatentMultiply
def interpolate(s1, s2, ratio):                                     # LatentInterpolate
    m1 = torch.linalg.vector_norm(s1, dim=1); m2 = torch.linalg.vector_norm(s2, dim=1); a = torch.nan_to_num(s1 / m1); b = torch.nan_to_num(s2 / m2)
    t = a * ratio + b * (1 - ratio); mt = torch.linalg.vector_norm(t, dim=1); return torch.nan_to_num(t / mt) * (m1 * ratio + m2 * (1 - ratio))
# 1. An empty latent.
z = torch.zeros(1, 4, 64, 64); print("empty latent times 5, largest value:", multiply(z, 5.).abs().max().item(), " upscaled twice:", F.interpolate(z, scale_factor=2, mode="nearest-exact").shape[-1], "wide, largest value:", F.interpolate(z, scale_factor=2, mode="nearest-exact").abs().max().item())
print("so nothing you do by multiplying an EmptyLatentImage can change a render: samplers skip process_latent_in for all-zero latents too")
# 2. The two scales. The wire holds VAE numbers. Sampling multiplies by scale_factor on the way in and divides on the way out: process_in, process_out.
for n, f in (("SD 1.x", .18215), ("SDXL", .13025)): print(f"{n}: a value of 5.0 on the wire is {5 * f:.3f} inside the sampler, and 1.0 inside is {1 / f:.3f} on the wire")
# 3. The preview map: a straight multiplication, so its effect can be computed. SD15 latent_rgb_factors; preview_to_image does (x + 1) / 2 and clips.
RGB = torch.tensor([[.3512, .2297, .3227], [.3250, .4974, .2350], [-.2829, .1762, .2721], [-.2120, -.2616, -.7177]])
torch.manual_seed(3); lat = torch.randn(1, 4, 32, 32) * .9
def preview(l): return ((l[0].permute(1, 2, 0) @ RGB + 1) / 2)
def clipped(l): p = preview(l); return ((p < 0) | (p > 1)).double().mean().item()
print("\nSD 1.x preview map only, random latent of spread 0.9")
print("multiplier  preview spread around grey  values clipped")
sp = {}
for k in (.5, .8, 1., 1.2, 1.5, 2.):
    p = preview(multiply(lat, k)); sp[k] = p.std().item(); print(f"{k:<11} {sp[k]:<27.3f} {clipped(multiply(lat, k)):.3f}")
assert abs(sp[2.] / sp[1.] - 2) < 1e-4
# 4. Before and during sampling. A toy: data with spread about 1, the exact denoiser, Euler.
W, M, S = torch.tensor([.3, .7], dtype=D), torch.tensor([-1.2, .9], dtype=D), torch.tensor([.3, .4], dtype=D)
def den(x, sigma):
    v = S ** 2 + sigma ** 2; r = torch.softmax(W.log() - .5 * (x[..., None] - M) ** 2 / v - .5 * v.log(), -1); return (r * (S ** 2 * x[..., None] + sigma ** 2 * M) / v).sum(-1)
beta = torch.linspace(.00085 ** .5, .012 ** .5, 1000, dtype=D) ** 2; ab = torch.cumprod(1 - beta, 0); SIG = ((1 - ab) / ab).sqrt(); smin, smax = SIG[0].item(), SIG[-1].item()
def karras(n, rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
def euler(x, s):
    for i in range(len(s) - 1): x = x + (x - den(x, s[i])) / s[i] * (s[i + 1] - s[i])
    return x
g = torch.Generator().manual_seed(1); N = 40000; n = torch.randn(N, dtype=D, generator=g); s = karras(20); ks = torch.multinomial(W, N, True, generator=g); data = M[ks] + S[ks] * torch.randn(N, dtype=D, generator=g)
base = euler(n * (1 + smax ** 2) ** .5, s); w1 = lambda x: (x.sort().values - data.sort().values).abs().mean().item()
print("\nmultiply by 1.5 at different moments, 20 steps. Distance from the data (W1); the plain run scores", f"{w1(base):.3f}")
print("when                           sigma then   W1 to the data   spread of the result")
out = {}
for label, i in (("the starting noise", 0), ("after step 4", 4), ("after step 10", 10), ("after step 16", 16), ("after step 19", 19), ("after the last step", 20)):
    x = euler(n * (1 + smax ** 2) ** .5, s[:i + 1]) if i else n * (1 + smax ** 2) ** .5
    x = x * 1.5; y = euler(x, s[i:]) if i < 20 else x; out[i] = w1(y); print(f"{label:30s} {s[i]:<12.3f} {out[i]:<16.3f} {y.std():.3f}")
assert out[20] > out[4] and out[19] > out[0]
print("spread of the data itself:", f"{data.std():.3f}")
# 5. Mixing two noises. A plain average loses spread, so the model is handed less noise than it was told.
a, b = torch.randn(1, 4, 64, 64, generator=torch.manual_seed(1)), torch.randn(1, 4, 64, 64, generator=torch.manual_seed(2))
print(f"\nmixing two noises half and half: plain average spread {((a + b) / 2).std():.3f}; LatentInterpolate spread {interpolate(a, b, .5).std():.3f}; sqrt(1/2) mix {((a + b) * .5 ** .5).std():.3f}")
assert ((a + b) / 2).std() < .75 and interpolate(a, b, 1.).sub(a).abs().max() < 1e-4
print("LatentInterpolate ratio 1 returns samples1:", bool(interpolate(a, b, 1.).sub(a).abs().max() < 1e-4), " ratio 0 returns samples2:", bool(interpolate(a, b, 0.).sub(b).abs().max() < 1e-4))
# 6. Resizing noise-like numbers.
print("\nresizing a noise latent 2x: spread after each upscale_method")
for m, kw in (("nearest-exact", {}), ("bilinear", {"align_corners": False}), ("bicubic", {"align_corners": False}), ("area", {})): print(f"{m:14s} {F.interpolate(a, scale_factor=2, mode=m, **kw).std():.3f}")
