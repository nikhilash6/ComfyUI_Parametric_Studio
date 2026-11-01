# CU-233 lab: two KSamplerAdvanced nodes sharing a schedule, and what each wrong setting does. Exact denoiser, no network.
# The slicing follows KSampler.sample in comfy/samplers.py. The noise rule follows common_ksampler in nodes.py and EPS.noise_scaling in comfy/model_sampling.py.
import torch
torch.set_num_threads(1)
D = torch.float64
beta = torch.linspace(.00085 ** .5, .012 ** .5, 1000, dtype=D) ** 2; ab = torch.cumprod(1 - beta, 0); SIG = ((1 - ab) / ab).sqrt()
smin, smax = SIG[0].item(), SIG[-1].item()
W, M, S = torch.tensor([.3, .7], dtype=D), torch.tensor([-1.2, .9], dtype=D), torch.tensor([.3, .4], dtype=D)
def den(x, sigma):
    v = S ** 2 + sigma ** 2; r = torch.softmax(W.log() - .5 * (x[..., None] - M) ** 2 / v - .5 * v.log(), -1); return (r * (S ** 2 * x[..., None] + sigma ** 2 * M) / v).sum(-1)
def karras(n, rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
def euler(x, s):
    for i in range(len(s) - 1): x = x + (x - den(x, s[i])) / s[i] * (s[i + 1] - s[i])
    return x
def dpmpp_2m(x, s):
    old = None
    for i in range(len(s) - 1):
        d = den(x, s[i])
        if s[i + 1] == 0: x = d; break
        t, tn = -s[i].log(), -s[i + 1].log(); h = tn - t
        if old is None: x = s[i + 1] / s[i] * x - (-h).expm1() * d
        else: r = (t + s[i - 1].log()) / h; x = s[i + 1] / s[i] * x - (-h).expm1() * ((1 + 1 / (2 * r)) * d - 1 / (2 * r) * old)
        old = d
    return x
SOLVER = {"euler": euler, "dpmpp_2m": dpmpp_2m}
def advanced(lat, solver, steps, start, end, add_noise, leftover, noise):
    s = karras(steps)
    if end < len(s) - 1:                              # last_step
        s = s[:end + 1].clone()
        if not leftover: s[-1] = 0                     # force_full_denoise
    if start >= len(s) - 1: return lat                 # start_step past the end: latent handed back
    s = s[start:]
    n = noise if add_noise else torch.zeros_like(lat)
    x = n * (1 + s[0] ** 2).sqrt() + lat if abs(s[0] - smax) < 1e-5 * smax else n * s[0] + lat
    return SOLVER[solver](x, s)
N = 40000; n1, n2 = torch.randn(N, dtype=D, generator=torch.manual_seed(1)), torch.randn(N, dtype=D, generator=torch.manual_seed(2)); zero = torch.zeros(N, dtype=D)
def w1(x, y): return (x.sort().values - y.sort().values).abs().mean().item()
ref = euler(n1 * (1 + smax ** 2) ** .5, karras(4000)); one = advanced(zero, "euler", 20, 0, 10000, True, False, n1)
print("the first sampler stops at step 12 of 20; the second starts there")
s = karras(20); print(f"sigma at step 12: {s[12]:.4f}")
print("\nsetup                                             RMS from one run   W1 to the true result")
def case(label, solver2="euler", steps2=20, add2=False, left=True, s1="euler", base=None):
    a = advanced(zero, s1, 20, 0, 12, True, left, n1); b = advanced(a, solver2, steps2, 12, 10000, add2, False, n2)
    print(f"{label:49s} {(b - (base if base is not None else one)).pow(2).mean().sqrt():<18.4f} {w1(b, ref):.4f}"); return b
good = case("leftover on, new noise off, same steps")
assert (good - one).abs().max() < 1e-12
b1 = case("leftover OFF (first finishes, jumps to sigma 0)", left=False)
b2 = case("new noise ON at the second", add2=True)
b3 = case("second has steps 30, not 20", steps2=30)
b4 = case("leftover OFF and new noise ON (a restart)", left=False, add2=True)
print(f"one run, 20 steps, for reference                  {0.0:<18.4f} {w1(one, ref):.4f}")
assert w1(b1, ref) > w1(good, ref)
print("\nwhat the first sampler hands over, as a spread (the data alone has spread", f"{(W * (M ** 2 + S ** 2)).sum().sub((W * M).sum() ** 2).sqrt():.3f})")
a = advanced(zero, "euler", 20, 0, 12, True, True, n1); print(f"leftover on: {a.std():.3f}   expected from data and sigma: {((W * (M ** 2 + S ** 2)).sum() - (W * M).sum() ** 2 + s[12] ** 2).sqrt():.3f}")
a0 = advanced(zero, "euler", 20, 0, 12, True, False, n1); print(f"leftover off: {a0.std():.3f}")
# Multistep history starts again at the join, even with the same solver.
whole = dpmpp_2m(n1 * (1 + smax ** 2) ** .5, karras(20)); ha = advanced(zero, "dpmpp_2m", 20, 0, 12, True, True, n1); hb = advanced(ha, "dpmpp_2m", 20, 12, 10000, False, False, n2)
print(f"\ndpmpp_2m split at step 12 against dpmpp_2m in one run: RMS {(hb - whole).pow(2).mean().sqrt():.5f}. Euler has no history: RMS {(good - one).pow(2).mean().sqrt():.1e}"); assert (hb - whole).abs().max() > 1e-4
mix = advanced(advanced(zero, "euler", 20, 0, 12, True, True, n1), "dpmpp_2m", 20, 12, 10000, False, False, n2); print(f"euler then dpmpp_2m, W1 to the true result: {w1(mix, ref):.4f}; euler all the way {w1(one, ref):.4f}; dpmpp_2m all the way {w1(whole, ref):.4f}")
print("start_at_step past the end hands the latent straight back:", bool(torch.equal(advanced(n1, "euler", 20, 25, 10000, False, False, n2), n1)))
