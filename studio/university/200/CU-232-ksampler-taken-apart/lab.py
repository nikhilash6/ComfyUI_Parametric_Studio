# CU-232 lab: the same run through one function and through four parts, then the one place they differ.
# Follows nodes.py common_ksampler, comfy/samplers.py KSampler and CFGGuider, comfy_extras/nodes_custom_sampler.py.
import torch
torch.set_num_threads(1)
D = torch.float64
beta = torch.linspace(.00085 ** .5, .012 ** .5, 1000, dtype=D) ** 2; ab = torch.cumprod(1 - beta, 0); SIG = ((1 - ab) / ab).sqrt()
smin, smax = SIG[0].item(), SIG[-1].item()
def den(x, sigma, m):
    v = .09 + sigma ** 2; r = torch.softmax(-.5 * (x[..., None] - m) ** 2 / v, -1); return (r * (.09 * x[..., None] + sigma ** 2 * m) / v).sum(-1)
POS, NEG = torch.tensor([1.5], dtype=D), torch.tensor([1.2], dtype=D)
def karras(n, rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
# The four parts
def RandomNoise(seed): return lambda lat: torch.randn(lat.shape, dtype=D, generator=torch.manual_seed(seed))
def CFGGuider(cfg): return lambda x, s: den(x, s, NEG) + (den(x, s, POS) - den(x, s, NEG)) * cfg
def KSamplerSelect(name):
    def euler(g, x, s):
        for i in range(len(s) - 1): x = x + (x - g(x, s[i])) / s[i] * (s[i + 1] - s[i])
        return x
    def dpm_2(g, x, s):                               # sample_dpm_2: midpoint in log sigma, Euler for the last step
        for i in range(len(s) - 1):
            d = (x - g(x, s[i])) / s[i]
            if s[i + 1] == 0: x = x + d * (s[i + 1] - s[i])
            else: m = (s[i].log() * .5 + s[i + 1].log() * .5).exp(); x2 = x + d * (m - s[i]); x = x + (x2 - g(x2, m)) / m * (s[i + 1] - s[i])
        return x
    return {"euler": euler, "dpm_2": dpm_2}[name]
def BasicScheduler(steps, denoise=1.):
    if denoise > .9999: return karras(steps)
    return karras(int(steps / denoise))[-(steps + 1):]
def SamplerCustomAdvanced(noise, guider, sampler, sigmas, latent):
    n = noise(latent); x = n * (1 + sigmas[0] ** 2).sqrt() + latent if abs(sigmas[0] - smax) < 1e-5 * smax else n * sigmas[0] + latent
    return sampler(guider, x, sigmas)
# The all in one
DISCARD = {"dpm_2", "dpm_2_ancestral", "uni_pc", "uni_pc_bh2"}          # KSampler.DISCARD_PENULTIMATE_SIGMA_SAMPLERS
def ks_sigmas(sampler, steps):
    if sampler in DISCARD: s = karras(steps + 1); return torch.cat([s[:-2], s[-1:]])
    return karras(steps)
def KSampler(seed, steps, cfg, sampler, latent): return SamplerCustomAdvanced(RandomNoise(seed), CFGGuider(cfg), KSamplerSelect(sampler), ks_sigmas(sampler, steps), latent)
lat = torch.zeros(4000, dtype=D)
a = KSampler(42, 20, 7., "euler", lat); b = SamplerCustomAdvanced(RandomNoise(42), CFGGuider(7.), KSamplerSelect("euler"), BasicScheduler(20), lat)
print("euler, 20 steps: KSampler and the four parts give identical numbers:", bool(torch.equal(a, b))); assert torch.equal(a, b)
print("\nthe last sigmas before 0, karras, 20 steps")
for n in ("euler", "dpm_2"):
    print(f"{n:6s} KSampler      " + " ".join(f"{v:.4f}" for v in ks_sigmas(n, 20)[-4:-1]))
    print(f"{n:6s} BasicScheduler " + " ".join(f"{v:.4f}" for v in BasicScheduler(20)[-4:-1]))
c = KSampler(42, 20, 7., "dpm_2", lat); d = SamplerCustomAdvanced(RandomNoise(42), CFGGuider(7.), KSamplerSelect("dpm_2"), BasicScheduler(20), lat)
print(f"dpm_2, same seed: RMS difference between the two routes {(c - d).pow(2).mean().sqrt():.5f}"); assert not torch.equal(c, d)
print("\nwhat the parts let you do that the widget cannot")
s = BasicScheduler(20); hi, lo = s[:13], s[12:]                       # SplitSigmas at step 12
print(f"split at step 12: first half {len(hi) - 1} steps, sigma {hi[0]:.3f} to {hi[-1]:.3f}; second half {len(lo) - 1} steps, sigma {lo[0]:.3f} to {lo[-1]:.3f}")
e = KSamplerSelect("euler")(CFGGuider(3.), KSamplerSelect("euler")(CFGGuider(7.), RandomNoise(42)(lat) * (1 + s[0] ** 2).sqrt(), hi), lo)
print(f"guider changed from cfg 7 to cfg 3 at that split: mean result {e.mean():+.3f}, against {a.mean():+.3f} for cfg 7 throughout, RMS change {(e - a).pow(2).mean().sqrt():.3f}")
assert hi[-1] == lo[0]
