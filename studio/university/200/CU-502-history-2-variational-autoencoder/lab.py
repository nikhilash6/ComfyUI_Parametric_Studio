# CU-502 lab: the three ideas of "Auto-Encoding Variational Bayes", each checked on a model where the exact answer is known.
# Model: z ~ N(0, 1), x | z ~ N(w z + c, s^2). Then p(x) and the posterior p(z | x) are Gaussians we can write down.
# Run: python lab.py  (CPU only, about 5 s). Prints the same numbers every time.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
w, c, s = 2.0, 1.0, 0.5
def log_normal(x, m, v): return -0.5 * (math.log(2 * math.pi * v) + (x - m) ** 2 / v)          # log N(x; m, v), v is a variance
def log_px(x): return log_normal(x, c, w * w + s * s)                                             # exact marginal: N(c, w^2 + s^2)
def post(x): return w * (x - c) / (w * w + s * s), torch.tensor(s * s / (w * w + s * s), dtype=D)  # exact posterior mean and variance
def kl(m1, v1, m2, v2): return 0.5 * ((m1 - m2) ** 2 / v2 + v1 / v2 - 1 - torch.log(v1 / v2))     # KL( N(m1,v1) || N(m2,v2) )
def elbo(x, m, v):                                                                                 # E_q[log p(x|z)] - KL(q || prior), q = N(m, v), in closed form
    rec = -0.5 * math.log(2 * math.pi * s * s) - ((x - c - w * m) ** 2 + w * w * v) / (2 * s * s)
    return rec - kl(m, v, torch.zeros_like(m), torch.ones_like(v))

# 1. The bound and its gap, for one datapoint and four choices of q(z|x).
x0 = torch.tensor(2.5, dtype=D); pm, pv = post(x0); lp = log_px(x0)
qs = {"true posterior": (pm, pv), "shifted by 0.3": (pm + .3, pv), "too wide": (pm, torch.tensor(1., dtype=D)), "the prior": (torch.tensor(0., dtype=D), torch.tensor(1., dtype=D))}
print(f"log p(x) = {lp:.4f} for x = 2.5")
print("q(z|x)            bound    Monte Carlo  gap      KL(q || p(z|x))")
for name, (m, v) in qs.items():
    z = m + v.sqrt() * torch.randn(1_000_000, dtype=D)                                              # reparameterised draws
    draws = log_normal(x0, w * z + c, s * s) + log_normal(z, 0., 1.) - log_normal(z, m, v)           # log p(x,z) - log q(z) for each draw
    mc, se = draws.mean(), draws.std() / 1000                                                          # estimate and its standard error
    b = elbo(x0, m, v); g = lp - b; k = kl(m, v, pm, pv)
    print(f"{name:16s} {b:8.4f} {mc:8.4f}     {g:7.4f}  {k:7.4f}")
    assert abs(g - k) < 1e-9 and abs(b - mc) < max(4 * se, 1e-9) and b <= lp + 1e-12

# 2. Two unbiased estimators of d(bound)/d(mean of q), with the mean of q 0.3 away from the posterior mean.
#    Reparameterised: differentiate through z = m + sigma e.  Score function (the "naive" estimator of the paper): f(z) d log q(z) / dm.
N = 200_000; m0 = pm + .3
print("\nstd of q   exact gradient   reparameterised: mean    std     score function: mean    std     variance ratio")
for sd0 in (0.5, pv.sqrt().item(), 0.1):
    mt = m0.clone().requires_grad_(True); exact, = torch.autograd.grad(elbo(x0, mt, torch.tensor(sd0 ** 2, dtype=D)), mt)
    e = torch.randn(N, dtype=D); mv = m0.expand(N).clone().requires_grad_(True)
    z = mv + sd0 * e; f = log_normal(x0, w * z + c, s * s) + log_normal(z, 0., 1.) - (-0.5 * math.log(2 * math.pi * sd0 ** 2) - 0.5 * e ** 2)   # log p(x,z) - log q(z), with log q written through e
    g_rep, = torch.autograd.grad(f.sum(), mv)
    zd = (m0 + sd0 * e).detach(); mv2 = m0.expand(N).clone().requires_grad_(True); fd = (log_normal(x0, w * zd + c, s * s) + log_normal(zd, 0., 1.) - log_normal(zd, m0, sd0 ** 2)).detach()
    g_sf, = torch.autograd.grad((fd * log_normal(zd, mv2, sd0 ** 2)).sum(), mv2)
    print(f"{sd0:.4f}     {exact.item():+.4f}          {g_rep.mean():+.4f}               {g_rep.std():6.3f}  {g_sf.mean():+.4f}               {g_sf.std():6.3f}  {g_sf.var() / g_rep.var():8.1f}")
    assert abs(g_rep.mean() - exact) < 0.1 and abs(g_sf.mean() - exact) < 0.3 and g_sf.var() > 3 * g_rep.var()
assert g_sf.var() > 100 * g_rep.var()

# 3. Amortised inference. One small encoder q(z|x) = N(a x + b, sigma^2) for ALL x, trained only by the reparameterised bound (the paper's AEVB, M = 100, L = 1).
def train(use_x, steps=3000):
    a, b, ls = (torch.tensor(0., dtype=D, requires_grad=True) for _ in range(3))
    opt = torch.optim.Adam([b, ls] + ([a] if use_x else []), 0.02); sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda t: 1 - t / steps)    # learning rate decays to 0
    for _ in range(steps):
        x = c + math.sqrt(w * w + s * s) * torch.randn(100, dtype=D); m = (a if use_x else 0.) * x + b; sd = ls.exp()
        zz = m + sd * torch.randn(100, dtype=D)                                                      # one reparameterised draw per datapoint
        loss = -(log_normal(x, w * zz + c, s * s) - kl(m, sd ** 2, torch.zeros_like(m), torch.ones_like(m))).mean()
        opt.zero_grad(); loss.backward(); opt.step(); sched.step()
    return (a.item() if use_x else 0.), b.item(), ls.exp().item()
xt = c + math.sqrt(w * w + s * s) * torch.randn(200_000, dtype=D)
def mean_gap(a, b, sd): m = a * xt + b; return (log_px(xt) - elbo(xt, m, torch.full_like(m, sd ** 2))).mean().item()
true_a, true_b, true_sd = w / (w * w + s * s), -w * c / (w * w + s * s), math.sqrt(s * s / (w * w + s * s))
print("\nencoder q(z|x) = N(a x + b, sigma^2)    a        b        sigma    mean gap log p(x) - bound")
rows = [("exact posterior", true_a, true_b, true_sd), ("learned, may use x", *train(True)), ("learned, ignores x", *train(False))]
for name, a, b, sd in rows: print(f"{name:22s}          {a:+.4f}  {b:+.4f}  {sd:.4f}   {abs(mean_gap(a, b, sd)):.4f}")
assert abs(rows[1][1] - true_a) < 0.02 and mean_gap(*rows[1][1:]) < 0.01 and mean_gap(*rows[2][1:]) > 1

# 4. Why a decoder trained on squared error blurs. Edge at pixel 3 or at pixel 6, equally likely, and a code z that cannot tell which.
A = torch.tensor([0, 0, 0, 1, 1, 1, 1, 1, 1.], dtype=D); B = torch.tensor([0, 0, 0, 0, 0, 0, 1, 1, 1.], dtype=D)
imgs = torch.stack([A, B])[torch.randint(0, 2, (2000,))]; out = torch.zeros(9, dtype=D, requires_grad=True); opt = torch.optim.Adam([out], 0.05)
for _ in range(600): loss = ((out - imgs) ** 2).sum(1).mean(); opt.zero_grad(); loss.backward(); opt.step()
o = out.detach(); sse_mean = 0.5 * (((o - A) ** 2).sum() + ((o - B) ** 2).sum()); sse_pick = 0.5 * ((A - B) ** 2).sum()    # picking A or B at random: wrong half the time
print("\nimage A      ", " ".join(f"{v:.2f}" for v in A.tolist())); print("image B      ", " ".join(f"{v:.2f}" for v in B.tolist()))
print("best output  ", " ".join(f"{v:.2f}" for v in o.tolist()))
print(f"largest jump between neighbouring pixels: best output {(o[1:] - o[:-1]).abs().max():.2f}, either real image 1.00")
print(f"expected squared error: best output {sse_mean:.2f}, a sharp image picked at random {sse_pick:.2f}")
assert (o[1:] - o[:-1]).abs().max() < 0.6 and sse_mean < sse_pick
