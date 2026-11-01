# CU-270 lab: when a ControlNet is on, how the percents become noise levels, and what strength multiplies.
# Noise levels and schedules follow comfy/model_sampling.py, comfy/samplers.py and comfy/k_diffusion/sampling.py. The on/off test follows ControlBase.get_control in comfy/controlnet.py.
import math, torch
abar = torch.cumprod(1 - torch.linspace(0.00085 ** 0.5, 0.012 ** 0.5, 1000, dtype=torch.float64) ** 2, 0)
SIG = (((1 - abar) / abar) ** 0.5).float(); LOGS = SIG.log()
def sigma_at(t):
    t = torch.clamp(torch.tensor(float(t)), 0, 999); lo, hi, w = t.floor().long(), t.ceil().long(), t.frac()
    return ((1 - w) * LOGS[lo] + w * LOGS[hi]).exp().item()
def percent_to_sigma(p): return 999999999.9 if p <= 0 else 0.0 if p >= 1 else sigma_at((1.0 - p) * 999.0)
def flow_percent(p, shift=3.0):                  # ModelSamplingDiscreteFlow.percent_to_sigma with time_snr_shift
    if p <= 0: return 1.0
    if p >= 1: return 0.0
    t = 1 - p; return shift * t / (1 + (shift - 1) * t)
def normal(n): return [sigma_at(t) for t in torch.linspace(999, 0, n).tolist()] + [0.0]
def karras(n, rho=7.0):
    lo, hi = SIG[0].item() ** (1 / rho), SIG[-1].item() ** (1 / rho)
    return [(hi + i / (n - 1) * (lo - hi)) ** rho for i in range(n)] + [0.0]
def exponential(n):
    a, b = math.log(SIG[-1].item()), math.log(SIG[0].item())
    return [math.exp(a + i / (n - 1) * (b - a)) for i in range(n)] + [0.0]
def simple(n):
    ss = 1000 / n; return [SIG[-(1 + int(x * ss))].item() for x in range(n)] + [0.0]
def on_steps(sig, start, end):                   # a step runs the ControlNet unless sigma > start level or sigma < end level
    hi, lo = percent_to_sigma(start), percent_to_sigma(end)
    return sum(1 for s in sig[:-1] if not (s > hi or s < lo))
SCHED = {"normal": normal, "karras": karras, "exponential": exponential, "simple": simple}

print("percent to noise level, SD 1.x")
print("percent  timestep  sigma")
for p in (0.0, 0.25, 0.5, 0.75, 0.8, 1.0):
    s = percent_to_sigma(p); print(f"{p:<8} {(1 - p) * 999:<9.1f} {'above every step' if p == 0 else f'{s:.3f}'}")
print("\n20 steps, start_percent 0: steps with the ControlNet on")
print("end_percent   normal   karras   exponential   simple")
want = {"normal": [5, 10, 15, 16, 20], "karras": [6, 9, 12, 12, 20], "exponential": [4, 7, 10, 10, 20], "simple": [5, 10, 15, 16, 20]}
got = {k: [] for k in SCHED}
for e in (0.25, 0.5, 0.75, 0.8, 1.0):
    row = [on_steps(SCHED[k](20), 0.0, e) for k in SCHED]
    for k, v in zip(SCHED, row): got[k].append(v)
    print(f"{e:<13} {row[0]:<8} {row[1]:<8} {row[2]:<13} {row[3]}")
assert got == want   # the same counts come out of ComfyUI's own calculate_sigmas and percent_to_sigma
print("\nsame window, start 0 end 0.8, different step counts, karras")
print("steps   on   share")
for n in (8, 20, 40):
    k = on_steps(karras(n), 0.0, 0.8); print(f"{n:<7} {k:<4} {k / n:.2f}")
print("\nother windows, 20 steps, normal")
print("start   end   steps on")
for a, b in ((0.0, 0.5), (0.2, 0.8), (0.5, 1.0), (0.8, 0.2)):
    print(f"{a:<7} {b:<5} {on_steps(normal(20), a, b)}")
assert on_steps(normal(20), 0.8, 0.2) == 0     # start after end: the test is never passed, and nothing warns you
print("\nthe window is on the model's scale, so denoise moves your steps under it. 20 steps, normal, start 0")
print("denoise  first sigma   end 0.25   end 0.5   end 0.8")
rows = {}
for d in (1.0, 0.8, 0.5, 0.3):
    s = normal(20) if d > 0.9999 else normal(int(20 / d))[-21:]
    r = [on_steps(s, 0.0, e) for e in (0.25, 0.5, 0.8)]; rows[d] = r
    print(f"{d:<8} {s[0]:<13.3f} {r[0]:<10} {r[1]:<9} {r[2]}")
assert rows[0.5][0] == 0 and rows[0.5][1] == 0
print("\nsame percent on a flow model, shift 3")
print("percent  sigma on SD 1.x   sigma on flow")
for p in (0.25, 0.5, 0.75):
    print(f"{p:<8} {percent_to_sigma(p):<17.3f} {flow_percent(p):.3f}")
# Strength: control_merge multiplies each residual, and a chained ControlNet adds its residuals to the earlier one's.
g = torch.Generator().manual_seed(0); r1, r2 = torch.randn(4, generator=g), torch.randn(4, generator=g)
def merge(res, strength, prev=None):
    out = res * strength
    return out if prev is None else prev + out
a = merge(r1, 1.0); b = merge(r1, 0.5); c = merge(r2, 0.5, merge(r1, 0.5))
print("\nstrength multiplies the residuals: |0.5 x| / |x| =", round((b.norm() / a.norm()).item(), 3), "  chained: difference from 0.5 r1 + 0.5 r2 =", round((c - 0.5 * r1 - 0.5 * r2).abs().max().item(), 6))
assert abs((b.norm() / a.norm()).item() - 0.5) < 1e-6 and (c - 0.5 * r1 - 0.5 * r2).abs().max() < 1e-6
