# CU-382 lab: the formulas behind one name, side by side. Each was read as source text. Nothing from a pack is imported or run. Formulas are written here in our own words.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1); g = torch.Generator().manual_seed(0)
print("NAG. Core: z+ phi - z- (phi - 1). sd-perturbed-attention: z+ + phi (z+ - z-)")
zp, zn = torch.randn(8, generator=g), torch.randn(8, generator=g)
core = lambda p: zp * p - zn * (p - 1); pack = lambda p: zp + p * (zp - zn)
for p in (1.0, 3.0, 5.0):
    print(f"  phi {p}: same result {torch.allclose(core(p), pack(p))}.  core with phi {p} equals pack with phi {p - 1}: {torch.allclose(core(p), pack(p - 1))}")
assert torch.allclose(core(5.0), pack(4.0)) and not torch.allclose(core(5.0), pack(5.0))
print("\nshift. SD3 style: a t / (1 + (a - 1) t). Flux style: e^mu / (e^mu + (1/t - 1)^s), with s = 1")
sd3 = lambda a, t: t if a == 1 else a * t / (1 + (a - 1) * t); flux = lambda m, s, t: math.exp(m) / (math.exp(m) + (1 / t - 1) ** s)
print("   t     sd3 a=3    flux mu=3   flux mu=ln 3")
for t in (0.1, 0.25, 0.5, 0.75, 0.9): print(f"  {t:4.2f}   {sd3(3, t):7.4f}   {flux(3, 1, t):9.4f}   {flux(math.log(3), 1, t):11.4f}")
assert all(abs(sd3(3, t) - flux(math.log(3), 1, t)) < 1e-12 for t in (0.1, 0.5, 0.9)) and abs(flux(3, 1, 0.5) - sd3(3, 0.5)) > 0.1
print("\nperp-neg. Core's perp: the part of neg at right angles to pos. bvhari's: the part of pos along neg")
pos = torch.tensor([3.0, 1.0]); neg = torch.tensor([2.0, 2.0])
core_perp = neg - (neg @ pos) / (pos @ pos) * pos; pack_perp = (pos @ neg) / (neg @ neg) * neg
print(f"  core {core_perp.tolist()}  dot with pos {(core_perp @ pos).item():+.4f}")
print(f"  pack {pack_perp.tolist()}  dot with pos {(pack_perp @ pos).item():+.4f}")
assert abs((core_perp @ pos).item()) < 1e-5 and abs((pack_perp @ pos).item()) > 1
print('\n"blue" noise. PowerNoiseSuite\'s default divides the FFT by (f^2)^(alpha/4), which with alpha 2 is amplitude 1/f, power 1/f^2.')
def blueish(alpha, n=128):
    x = torch.randn(n, n, generator=g, dtype=torch.float64); fx = torch.fft.fftfreq(n); F = (fx[None] ** 2 + fx[:, None] ** 2); p = F ** (alpha / 2); p[0, 0] = 1
    return torch.fft.ifftn(torch.fft.fftn(x) / torch.sqrt(p)).real
def slope(x):
    n = x.shape[0]; P = torch.fft.fftn(x).abs() ** 2; fx = torch.fft.fftfreq(n); r = (fx[None] ** 2 + fx[:, None] ** 2).sqrt(); lo = P[(r > .05) & (r < .1)].mean(); hi = P[(r > .3) & (r < .4)].mean()
    return (lo / hi).item()
wh = torch.randn(128, 128, generator=g, dtype=torch.float64)
r_w = slope(wh); r_b = slope(blueish(2.0)); print(f"  low frequency power / high frequency power: white {r_w:.2f}, this 'blue' {r_b:.2f}")
print("  above 1 means more power at low frequency. Textbook blue noise has more at high frequency, so below 1.")
assert r_b > 3 * r_w
print("\ndenoise, inside core. BasicScheduler keeps the step count. AlignYourSteps shortens it")
def basic(steps, d): return steps, int(steps / d)
def ays(steps, d): return round(steps * d), steps
for d in (1.0, 0.5, 0.25):
    b = basic(20, d); a = ays(20, d); print(f"  denoise {d}: BasicScheduler runs {b[0]} steps from a {b[1]} step schedule. AYS runs {a[0]} steps.")
assert basic(20, .5)[0] == 20 and ays(20, .5)[0] == 10
print("\nthe sampler called ddim. In core's samplers.py that name runs euler with one inpaint option.")
print("  our one-seed render matched pixel for pixel: see Sampling Lab.")
