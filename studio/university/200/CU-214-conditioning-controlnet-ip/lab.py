# CU-214 lab: where each kind of conditioning enters the model, in numbers.
# Run: python lab.py  (CPU only, a few seconds). Prints the same numbers every time.
import copy, math, torch
torch.manual_seed(0); torch.set_num_threads(1)
g = torch.Generator().manual_seed(0)

# SD 1.x noise levels, as comfy/model_sampling.py builds them: scaled-linear betas, sigma = sqrt((1 - abar) / abar), 1000 steps.
abar = torch.cumprod(1 - torch.linspace(0.00085 ** 0.5, 0.012 ** 0.5, 1000, dtype=torch.float64) ** 2, 0)
SIG = (((1 - abar) / abar) ** 0.5).float(); LOGS = SIG.log()
def sigma_at(t):                        # ModelSamplingDiscrete.sigma: interpolate log sigma between neighbouring timesteps
    t = torch.clamp(torch.tensor(float(t)), 0, 999); lo, hi, w = t.floor().long(), t.ceil().long(), t.frac()
    return ((1 - w) * LOGS[lo] + w * LOGS[hi]).exp().item()
def percent_to_sigma(p):                # ModelSamplingDiscrete.percent_to_sigma
    return 999999999.9 if p <= 0 else 0.0 if p >= 1 else sigma_at((1.0 - p) * 999.0)
def normal_sigmas(steps):               # comfy/samplers.py normal_scheduler for SD 1.x: timesteps 999 .. 0 evenly, then a final 0
    return torch.FloatTensor([sigma_at(t) for t in torch.linspace(999, 0, steps).tolist()] + [0.0])
def karras_sigmas(steps, rho=7.0):      # comfy/k_diffusion/sampling.py get_sigmas_karras
    ramp = torch.linspace(0, 1, steps); lo, hi = SIG[0].item() ** (1 / rho), SIG[-1].item() ** (1 / rho)
    return torch.cat([(hi + ramp * (lo - hi)) ** rho, torch.zeros(1)])
def with_denoise(fn, steps, denoise):   # comfy/samplers.py KSampler.set_steps: build a longer schedule, keep its last steps + 1 values
    return fn(steps) if denoise > 0.9999 else fn(int(steps / denoise))[-(steps + 1):]

# 1. img2img. "denoise" picks where on a longer schedule the sampler starts. Start from x = L + sigma_0 n, with L and n unit-variance.
L = torch.randn(1_000_000, generator=g); n = torch.randn(1_000_000, generator=g)
print("img2img, 20 steps, normal scheduler, SD 1.x noise levels")
print("denoise  steps run   first sigma   signal share 1/sqrt(1+sigma^2)   measured correlation with the clean latent")
for d in (0.2, 0.5, 0.8):
    s = with_denoise(normal_sigmas, 20, d); s0 = s[0].item(); x = L + s0 * n
    corr = ((x * L).mean() / (x.std() * L.std())).item()
    print(f"{d:<8} {len(s) - 1:<10d} {s0:<13.3f} {1 / math.sqrt(1 + s0 ** 2):<32.3f} {corr:.3f}")
    assert abs(corr - 1 / math.sqrt(1 + s0 ** 2)) < 0.01
print(f"denoise 1.0 starts from sigma_max = {SIG[-1]:.3f}")

# 2. A ControlNet window. start_percent and end_percent are fractions of the timestep range, turned into sigma levels, not fractions of the steps.
print("\nControlNet start_percent 0: steps (of 20) that run with the ControlNet on")
print("end_percent   sigma where it stops   normal scheduler   karras scheduler")
for e in (0.25, 0.5, 0.75):
    thr = percent_to_sigma(e); cnt = [int((fn(20)[:-1] >= thr).sum()) for fn in (normal_sigmas, karras_sigmas)]
    print(f"{e:<13} {thr:<22.3f} {cnt[0]:<18d} {cnt[1]}")

# 3. Zero convolution (Zhang and Agrawala 2023, eq. 2): y_c = F(x) + Z2(F_c(x + Z1(c))), with F locked, F_c a trainable copy, Z1 and Z2 zero-initialised.
d = 16; F = torch.nn.Sequential(torch.nn.Linear(d, d), torch.nn.ReLU(), torch.nn.Linear(d, d)).requires_grad_(False)
Fc = copy.deepcopy(F).requires_grad_(True); Z1, Z2 = torch.nn.Linear(d, d), torch.nn.Linear(d, d)
for z in (Z1, Z2): torch.nn.init.zeros_(z.weight); torch.nn.init.zeros_(z.bias)
x, c, target = torch.randn(64, d, generator=g), torch.randn(64, d, generator=g), torch.randn(64, d, generator=g)
def grads():
    yc = F(x) + Z2(Fc(x + Z1(c))); loss = (yc - target).pow(2).mean()
    for p in list(Fc.parameters()) + list(Z1.parameters()) + list(Z2.parameters()): p.grad = None
    loss.backward(); gn = lambda ps: sum(p.grad.norm() ** 2 for p in ps).sqrt().item()
    return (yc - F(x)).abs().max().item(), gn(Z2.parameters()), gn(Fc.parameters()), gn(Z1.parameters())
print("\nzero convolution            max |y_c - y|   grad of Z2   grad of trainable copy   grad of Z1")
r = grads(); print(f"step 0                      {r[0]:<15.1e} {r[1]:<12.4f} {r[2]:<23.4f} {r[3]:.4f}")
assert r[0] == 0 and r[1] > 0 and r[2] == 0 and r[3] == 0
with torch.no_grad():
    for p in Z2.parameters(): p -= 0.1 * p.grad
r = grads(); print(f"after one step on Z2        {r[0]:<15.1e} {r[1]:<12.4f} {r[2]:<23.4f} {r[3]:.4f}")
assert r[0] > 0 and r[2] > 0 and r[3] > 0

# 4. IP-Adapter's decoupled cross-attention (Ye et al. 2023, eq. 8) against appending image tokens to the text tokens, as the core StyleModelApply node does.
#    StyleModelApply has two strength types: "multiply" scales the image tokens, "attn_bias" adds log(strength) to their attention logits.
dm, nq, nt, ni = 32, 16, 8, 4
Wq, Wk, Wv, Wk2, Wv2 = [torch.randn(dm, dm, generator=g) / math.sqrt(dm) for _ in range(5)]
Z = torch.randn(nq, dm, generator=g); ci = torch.randn(ni, dm, generator=g); ct = torch.randn(nt, dm, generator=g); Q = Z @ Wq
def attn(K, V, extra=None):
    logits = Q @ K.T / math.sqrt(dm)
    if extra is not None: logits = logits + extra
    return torch.softmax(logits, -1) @ V
def decoupled(lam): return attn(ct @ Wk, ct @ Wv) + lam * attn(ci @ Wk2, ci @ Wv2)
def multiply(s): t = torch.cat([ct, s * ci]); return attn(t @ Wk, t @ Wv)
def attn_bias(s):
    t = torch.cat([ct, ci]); bias = torch.zeros(nt + ni); bias[nt:] = math.log(s) if s > 0 else -math.inf; return attn(t @ Wk, t @ Wv, bias)
text_only = attn(ct @ Wk, ct @ Wv)
print("\nimage strength 0 against a layer with no image at all, largest difference, and a linearity test of the image's effect")
print("design                                      strength 0 vs no image   relative error of (f(2) - f(0)) against 2 (f(1) - f(0))")
rows = {}
for name, f in (("decoupled cross-attention", decoupled), ("appended tokens, multiply", multiply), ("appended tokens, attn_bias", attn_bias)):
    d0 = (f(0.0) - text_only).abs().max().item(); a, b = f(2.0) - f(0.0), f(1.0) - f(0.0); lin = ((a - 2 * b).norm() / b.norm()).item(); rows[name] = (d0, lin)
    print(f"{name:43s} {d0:<24.1e} {lin:.3f}")
assert rows["decoupled cross-attention"][0] == 0 and rows["decoupled cross-attention"][1] < 1e-4 and rows["appended tokens, multiply"][0] > 0.1 and rows["appended tokens, attn_bias"][0] < 1e-6 and rows["appended tokens, attn_bias"][1] > 0.1
