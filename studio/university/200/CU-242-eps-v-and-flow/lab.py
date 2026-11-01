# CU-242 lab: EPS, V_PREDICTION and CONST from comfy/model_sampling.py. Give each its perfect output and the clean latent must come back. Then read one kind as another.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
class EPS:
    name = "eps"
    def mix(s, x0, n, sigma): return x0 + sigma * n                                     # noise_scaling
    def calculate_input(s, sigma, x): return x / (sigma ** 2 + 1) ** .5
    def calculate_denoised(s, sigma, out, x): return x - out * sigma
    def perfect(s, x0, n, sigma): return n
class V(EPS):
    name = "v"
    def calculate_denoised(s, sigma, out, x): return x * 1 / (sigma ** 2 + 1) - out * sigma / (sigma ** 2 + 1) ** .5
    def perfect(s, x0, n, sigma): a, b = 1 / (1 + sigma ** 2) ** .5, sigma / (1 + sigma ** 2) ** .5; return a * n - b * x0     # alpha eps - sqrt(1 - alpha^2) x0
class FLOW:
    name = "flow"
    def mix(s, x0, n, sigma): return (1 - sigma) * x0 + sigma * n
    def calculate_input(s, sigma, x): return x
    def calculate_denoised(s, sigma, out, x): return x - out * sigma
    def perfect(s, x0, n, sigma): return n - x0
x0 = torch.randn(10000, dtype=D); n = torch.randn(10000, dtype=D)
print("kind   sigma    largest error of the recovered clean latent   spread of what the model sees   spread of its perfect output")
for k, sigmas in ((EPS(), (.03, 1., 14.6)), (V(), (.03, 1., 14.6)), (FLOW(), (.05, .5, .95))):
    for sg in sigmas:
        x = k.mix(x0, n, sg); out = k.perfect(x0, n, sg); back = k.calculate_denoised(sg, out, x); e = (back - x0).abs().max().item(); print(f"{k.name:6s} {sg:<8} {e:<45.1e} {k.calculate_input(sg, x).std():<31.3f} {out.std():.3f}"); assert e < 1e-9
# Read v output as if it were eps, and the other way.
print("\nload a model as the wrong kind: RMS error of the clean-latent estimate, with otherwise perfect outputs")
print("sigma   right kind  v model read as eps  eps model read as v")
E_, V_ = EPS(), V(); res = {}
for sg in (.03, .3, 1., 3., 14.6):
    x = E_.mix(x0, n, sg); ve = (E_.calculate_denoised(sg, V_.perfect(x0, n, sg), x) - x0).pow(2).mean().sqrt().item(); ev = (V_.calculate_denoised(sg, E_.perfect(x0, n, sg), x) - x0).pow(2).mean().sqrt().item(); res[sg] = (ve, ev); print(f"{sg:<7} {0.0:<11.3f} {ve:<20.3f} {ev:.3f}")
assert res[14.6][0] > 5
print("\nthe table of sigmas for an SD-style model")
beta = torch.linspace(.00085 ** .5, .012 ** .5, 1000, dtype=D) ** 2; ab = torch.cumprod(1 - beta, 0); SIG = ((1 - ab) / ab).sqrt()
print(f"sigma_min {SIG[0]:.5f}   sigma_max {SIG[-1]:.5f}   signal left at the top: sqrt(alphabar) {ab[-1].sqrt():.5f}")
def zsnr(sig):                                        # rescale_zero_terminal_snr_sigmas
    a = (1 / (sig * sig + 1)).sqrt(); a0, aT = a[0].clone(), a[-1].clone(); a = (a - aT) * (a0 / (a0 - aT)); b = a ** 2; b[-1] = 4.8973451890853435e-08; return ((1 - b) / b).sqrt()
Z = zsnr(SIG); print(f"with zsnr: sigma_min {Z[0]:.5f}   sigma_max {Z[-1]:.2f}   signal left at the top: {1 / (1 + Z[-1] ** 2) ** .5:.6f}")
assert abs(Z[-1] - 4518.76) < .5
print("\nshift: time_snr_shift(a, t) = a t / (1 + (a - 1) t)")
sh = lambda a, t: a * t / (1 + (a - 1) * t)
print("shift   t=0.9   t=0.75  t=0.5   t=0.25  t=0.1")
for a in (1., 1.15, 1.73, 3., 3.158, 6.): print(f"{a:<7} " + " ".join(f"{sh(a, t):<7.3f}" for t in (.9, .75, .5, .25, .1)))
fl = lambda mu, t: math.exp(mu) / (math.exp(mu) + (1 / t - 1))                         # flux_time_shift with sigma 1
print(f"the number 1.15 at t=0.5: as ModelSamplingSD3 shift {sh(1.15, .5):.3f}; as ModelSamplingFlux max_shift at 1024x1024 {fl(1.15, .5):.3f}"); assert abs(fl(1.15, .5) - sh(math.exp(1.15), .5)) < 1e-12
w = h = 1024; mm = (1.15 - .5) / (4096 - 256); print(f"ModelSamplingFlux at {w}x{h}: tokens {w * h / 256:.0f}, mu {w * h / 256 * mm + (.5 - mm * 256):.3f}, the same bend as SD3 shift {math.exp(w * h / 256 * mm + (.5 - mm * 256)):.3f}")
print("\nhow a step finds its timestep: discrete models take the nearest table index, flow models multiply")
print(f"sigma 1.0, discrete: index {int((SIG.log() - 0.).abs().argmin())}; flow sigma 0.5 with multiplier 1000: {.5 * 1000:.0f}")
LS = SIG.log(); print(f"percent_to_sigma(0.5): SD table {(.5 * LS[499] + .5 * LS[500]).exp():.4f}; flow shift 3 {sh(3., .5):.4f}")
