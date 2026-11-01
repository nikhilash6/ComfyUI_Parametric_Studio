# CU-264 lab: start and end percent become sigmas, and each step compares its own sigma. Ports of percent_to_sigma in comfy/model_sampling.py and the first lines of get_area_and_mult, compared with the real ones on a CPU.
import torch
betas = torch.linspace(.00085 ** .5, .012 ** .5, 1000, dtype=torch.float64) ** 2; ac = torch.cumprod(1 - betas, 0); SIGMAS = ((1 - ac) / ac) ** .5; LS = SIGMAS.log()
def percent_to_sigma(p):
    """ModelSamplingDiscrete: SD 1.5's table, read at 999 times (1 - percent)."""
    if p <= 0: return 999999999.9
    if p >= 1: return 0.
    t = (1 - p) * 999; lo = int(t); hi = min(lo + 1, 999); f = t - lo; return float(((1 - f) * LS[lo] + f * LS[hi]).exp())
def flow_percent_to_sigma(p, shift=3.):
    """ModelSamplingDiscreteFlow."""
    if p <= 0: return 1.
    if p >= 1: return 0.
    t = 1 - p; return shift * t / (1 + (shift - 1) * t)
def karras(n, lo, hi, rho=7.): return [(hi ** (1 / rho) + i / (n - 1) * (lo ** (1 / rho) - hi ** (1 / rho))) ** rho for i in range(n)]
def active(sig, start, end):
    """get_area_and_mult: skip when the step's sigma is above timestep_start or below timestep_end."""
    return sig <= start and sig >= end
SMAX, SMIN = SIGMAS[-1].item(), SIGMAS[0].item()
print(f"SD 1.5 sigmas run from {SMAX:.3f} down to {SMIN:.4f}")
print("percent   sigma     flow model with shift 3")
for p in (.1, .25, .5, .75, .9): print(f"{p:<9} {percent_to_sigma(p):<9.3f} {flow_percent_to_sigma(p):.3f}")
assert abs(percent_to_sigma(.5) - 1.61558) < 1e-3 and abs(flow_percent_to_sigma(.5) - .75) < 1e-9
S20 = karras(20, SMIN, SMAX)
def count(a, b, sigs): return sum(active(s, percent_to_sigma(a), percent_to_sigma(b)) for s in sigs)
print("\nend_percent 0.5 on 20 Karras steps: first prompt runs", count(0, .5, S20), "steps, the second", count(.5, 1, S20))
import math
U20 = [math.exp(math.log(SMAX) + i / 19 * (math.log(SMIN) - math.log(SMAX))) for i in range(20)]
L20 = [SMAX + i / 19 * (SMIN - SMAX) for i in range(20)]
print("the same split on an even log spacing:", count(0, .5, U20), "and", count(.5, 1, U20), "   on an even linear spacing:", count(0, .5, L20), "and", count(.5, 1, L20))
assert count(0, .5, S20) != 10 or count(0, .5, L20) != 10
print("\nsteps with no prompt at all: ranges 0 to 0.4 and 0.6 to 1")
gap = [i for i, s in enumerate(S20) if not active(s, percent_to_sigma(0), percent_to_sigma(.4)) and not active(s, percent_to_sigma(.6), percent_to_sigma(1))]
print("uncovered steps:", gap)
out = torch.zeros(4) / (torch.ones(4) * 1e-37); print("what an uncovered step's positive prediction becomes:", out.tolist())
assert len(gap) > 0 and out.abs().max() == 0
