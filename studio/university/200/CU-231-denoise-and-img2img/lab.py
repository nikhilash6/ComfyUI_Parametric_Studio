# CU-231 lab: what denoise does, from KSampler.set_steps, then image to image on a toy with an exact denoiser.
import torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
beta = torch.linspace(.00085 ** .5, .012 ** .5, 1000, dtype=D) ** 2; ab = torch.cumprod(1 - beta, 0); SIG = ((1 - ab) / ab).sqrt(); LS = SIG.log()
smin, smax = SIG[0].item(), SIG[-1].item()
def karras(n, rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
def simple(n): return torch.tensor([SIG[-(1 + int(i * 1000 / n))].item() for i in range(n)] + [0.], dtype=D)
def set_steps(sch, steps, denoise):
    if denoise > .9999: return sch(steps)
    if denoise <= 0: return torch.zeros(0, dtype=D)
    return sch(int(steps / denoise))[-(steps + 1):]
print("KSampler at 20 steps, karras")
print("denoise  schedule built  steps run  starts at sigma  sigma / sqrt(1 + sigma^2)")
for d in (1., .75, .5, .25, .1):
    s = set_steps(karras, 20, d); sg = s[0].item(); print(f"{d:<8} {int(20 / d):<15d} {len(s) - 1:<10d} {sg:<16.4f} {sg / (1 + sg ** 2) ** .5:.3f}")
assert all(len(set_steps(karras, 20, d)) == 21 for d in (1., .75, .5, .25, .1))
print(f"same denoise 0.5, other schedulers start at: karras {set_steps(karras, 10, .5)[0]:.3f}   simple {set_steps(simple, 10, .5)[0]:.3f}")
print("denoise 0 gives", len(set_steps(karras, 20, 0.)), "sigmas, and the sampler hands back the latent untouched")
# BasicScheduler matches set_steps. Align Your Steps and friends cut to round(steps * denoise) steps instead.
print("Align Your Steps style at 20 steps, denoise 0.5: runs", round(20 * .5), "steps; BasicScheduler runs", len(set_steps(karras, 20, .5)) - 1)
# Rounding: int(steps / denoise) truncates, so nearby values can give one schedule.
print("schedule length for denoise 0.50, 0.49, 0.48 at 20 steps:", [int(20 / d) for d in (.5, .49, .48)])

# Image to image. Two subjects, one on each side. Start from a picture of the left one and see when it changes subject.
W, M, S = torch.tensor([.5, .5], dtype=D), torch.tensor([-1.2, 1.2], dtype=D), torch.tensor([.3, .3], dtype=D)
def den(x, sigma):
    v = S ** 2 + sigma ** 2; r = torch.softmax(W.log() - .5 * (x[..., None] - M) ** 2 / v, -1); return (r * (S ** 2 * x[..., None] + sigma ** 2 * M) / v).sum(-1)
def euler(x, s):
    for i in range(len(s) - 1): x = x + (x - den(x, s[i])) / s[i] * (s[i + 1] - s[i])
    return x
n = 20000; pic = M[0] + S[0] * torch.randn(n, dtype=D); noise = torch.randn(n, dtype=D)
print("\nstart from the left subject, 20 steps, exact denoiser")
print("denoise  start sigma  still the left subject  mean distance moved")
keep = {}
for d in (.1, .25, .4, .5, .6, .75, .9, 1.):
    s = set_steps(karras, 20, d); x0 = noise * (1 + s[0] ** 2).sqrt() + pic if d > .9999 else noise * s[0] + pic   # EPS.noise_scaling
    out = euler(x0, s); keep[d] = (out < 0).double().mean().item(); print(f"{d:<8} {s[0]:<12.3f} {keep[d]:<23.3f} {(out - pic).abs().mean():.3f}")
assert keep[.1] > .99 and keep[1.] < keep[.1]
print("the latent is still in the sum at denoise 1: left share", f"{keep[1.]:.3f}", "against", f"{(euler(noise * (1 + smax ** 2) ** .5, karras(20)) < 0).double().mean():.3f}", "from an empty latent")
# A wrong-first-noise check: the formula below denoise 1 uses sigma, at denoise 1 uses sqrt(1 + sigma^2).
print(f"noise multiplier at full denoise: {(1 + smax ** 2) ** .5:.4f}   sigma itself: {smax:.4f}")
