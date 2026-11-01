# CU-230 lab: one small KSampler, field by field, on a toy where the perfect model has a formula. No network, no GPU.
# The sums follow nodes.py (KSampler), comfy/samplers.py (KSampler.set_steps, sampling_function, cfg_function) and comfy/k_diffusion/sampling.py (sample_euler, sample_heun).
import torch
torch.set_num_threads(1)
D = torch.float64
# Two "subjects" in one dimension. The positive prompt asks for the one at +1.5, the negative for one close to it at +1.2.
def den(x, sigma, m):
    v = .3 ** 2 + sigma ** 2; r = torch.softmax(-.5 * (x[..., None] - m) ** 2 / v, -1)
    return (r * (.3 ** 2 * x[..., None] + sigma ** 2 * m) / v).sum(-1)
POS, NEG = torch.tensor([1.5], dtype=D), torch.tensor([1.2], dtype=D)
beta = torch.linspace(.00085 ** .5, .012 ** .5, 1000, dtype=D) ** 2; ab = torch.cumprod(1 - beta, 0); SIG = ((1 - ab) / ab).sqrt()
smin, smax = SIG[0].item(), SIG[-1].item()
def karras(n, rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
def simple(n): return torch.tensor([SIG[-(1 + int(i * 1000 / n))].item() for i in range(n)] + [0.], dtype=D)
SCHED = {"karras": karras, "simple": simple}
def set_steps(sched, steps, denoise):                 # KSampler.set_steps
    if denoise > .9999: return SCHED[sched](steps)
    return SCHED[sched](int(steps / denoise))[-(steps + 1):]
def run(seed=42, steps=20, cfg=7., sampler="euler", scheduler="karras", denoise=1., latent=None):
    passes = [0]
    def model(x, s):                                  # sampling_function: cfg 1 skips the negative pass
        passes[0] += 1; c = den(x, s, POS)
        if abs(cfg - 1) < 1e-9: return c
        passes[0] += 1; return den(x, s, NEG) + (c - den(x, s, NEG)) * cfg
    sig = set_steps(scheduler, steps, denoise); g = torch.manual_seed(seed); n = torch.randn(4000, dtype=D, generator=g)
    lat = torch.zeros(4000, dtype=D) if latent is None else latent
    x = n * (1 + sig[0] ** 2).sqrt() + lat if denoise > .9999 else n * sig[0] + lat     # EPS.noise_scaling
    for i in range(len(sig) - 1):
        d = (x - model(x, sig[i])) / sig[i]; dt = sig[i + 1] - sig[i]
        if sampler == "euler" or sig[i + 1] == 0: x = x + d * dt
        else: x2 = x + d * dt; d2 = (x2 - model(x2, sig[i + 1])) / sig[i + 1]; x = x + (d + d2) / 2 * dt
    return x, passes[0], sig
base, bp, bs = run()
print("field changed            evals  first sigma  last before 0  mean result  change from base")
def row(label, **k):
    x, p, s = run(**k); print(f"{label:24s} {p:<6d} {s[0]:<12.3f} {s[-2]:<14.3f} {x.mean():<+12.3f} {(x - base).pow(2).mean().sqrt():.3f}"); return x, p, s
row("nothing (base)")
a = row("seed 42 -> 43", seed=43)
b = row("steps 20 -> 40", steps=40)
c = row("cfg 7 -> 1", cfg=1.)
d = row("cfg 7 -> 3", cfg=3.)
e = row("sampler euler -> heun", sampler="heun")
f = row("scheduler -> simple", scheduler="simple")
g = row("denoise 1 -> 0.5", denoise=.5)
assert c[1] == 20 and bp == 40 and e[1] == 78 and g[1] == 40 and len(g[2]) == 21 and abs(g[2][0] - 1.1817) < .001
same, _, _ = run(); print("same fields again, identical numbers:", bool(torch.equal(same, base))); assert torch.equal(same, base)
# The CFG sum on one pair of numbers: cfg_function
print("\nuncond 0.2, cond 0.5: " + "   ".join(f"cfg {k}: {.2 + (.5 - .2) * k:.2f}" for k in (0, 1, 3, 7, 14)))
