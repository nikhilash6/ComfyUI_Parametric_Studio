# CU-501 lab: the GAN game of Goodfellow et al. (2014), checked three ways.
# 1. The value of the game, computed exactly on six points. 2. Why the generator loss needs the "non-saturating" form. 3. A small GAN trained on a CPU.
# Run: python lab.py  (CPU only, about 15 s). Prints the same numbers every time.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D64 = torch.float64
xlogy = torch.special.xlogy

# 1. The game on six points, where every quantity can be computed exactly.
p = torch.tensor([.05, .15, .30, .30, .15, .05], dtype=D64)                       # the data distribution
def value(q, d): return (xlogy(p, d) + xlogy(q, 1 - d)).sum()                       # V(D, G), eq. 1: E_data[log D] + E_G[log(1 - D)]
def kl(a, b): return xlogy(a, a / b).sum()
def jsd(a, b): m = (a + b) / 2; return (kl(a, m) + kl(b, m)) / 2
gens = {"uniform": torch.full((6,), 1 / 6, dtype=D64), "shifted by one": torch.tensor([.15, .30, .30, .15, .05, .05], dtype=D64),
        "two middle points": torch.tensor([0, 0, .5, .5, 0, 0], dtype=D64), "the data itself": p}
print("generator           JSD      V(D*, G)   -log4 + 2 JSD   V(D=1/2, G)")
g = torch.Generator().manual_seed(0)
for name, q in gens.items():
    d_star = p / (p + q)                                                             # eq. 2, the best discriminator for this generator
    v, bound = value(q, d_star), -math.log(4) + 2 * jsd(p, q)
    print(f"{name:19s} {jsd(p, q):.4f}   {v:+.6f}  {bound:+.6f}        {value(q, torch.full((6,), .5, dtype=D64)):+.6f}")
    assert abs(v - bound) < 1e-12
    worse = sum(bool(value(q, (d_star + .2 * (torch.rand(6, generator=g, dtype=D64) - .5)).clamp(1e-3, 1 - 1e-3)) < v) for _ in range(2000))
    assert worse == 2000                                                             # no discriminator we try beats D*
print("D* for the data itself:", " ".join(f"{x:.2f}" for x in (p / (p + p)).tolist()), "  -log 4 =", f"{-math.log(4):+.6f}")

# 2. Saturation. Early on D rejects fakes with confidence, so D(G(z)) is near 0. Compare the two generator losses.
print("\nlogit a   D = sigmoid(a)   |d log(1-D) / da|   |d (-log D) / da|")
for a0 in (-8., -4., -2., 0.):
    a = torch.tensor(a0, dtype=D64, requires_grad=True); d = torch.sigmoid(a)
    g_min, = torch.autograd.grad(torch.log(1 - d), a); a2 = torch.tensor(a0, dtype=D64, requires_grad=True); g_ns, = torch.autograd.grad(-torch.log(torch.sigmoid(a2)), a2)
    print(f"{a0:+5.1f}     {d.item():.5f}          {abs(g_min.item()):.5f}              {abs(g_ns.item()):.5f}")
    assert abs(abs(g_min.item()) - d.item()) < 1e-12 and abs(abs(g_ns.item()) - (1 - d.item())) < 1e-12

# 3. A small GAN on the same two-hump data as CU-101: weights .3 / .7, means -2 / 1.5, stds .3 / .5.
W, M, S = torch.tensor([.3, .7]), torch.tensor([-2., 1.5]), torch.tensor([.3, .5])
def data(n, gen=None): k = torch.multinomial(W, n, True, generator=gen); return M[k] + S[k] * torch.randn(n, generator=gen)
def mlp(i, o, w=64): return torch.nn.Sequential(torch.nn.Linear(i, w), torch.nn.LeakyReLU(.2), torch.nn.Linear(w, w), torch.nn.LeakyReLU(.2), torch.nn.Linear(w, o))
bce = torch.nn.functional.binary_cross_entropy_with_logits
def w1(x, gen): return (x.sort().values - data(len(x), gen).sort().values).abs().mean().item()
def gap(x): return ((x > -1) & (x < .5)).float().mean().item()                     # the empty space between the humps

# 3a. A generator gradient under a confident discriminator: train D for 300 steps against an untrained G, then compare the two losses.
torch.manual_seed(0); G0, D0 = mlp(2, 1), mlp(1, 1); opt = torch.optim.Adam(D0.parameters(), 1e-3)
for _ in range(300):
    f = G0(torch.randn(256, 2)).detach(); l = bce(D0(data(256)[:, None]), torch.ones(256, 1)) + bce(D0(f), torch.zeros(256, 1)); opt.zero_grad(); l.backward(); opt.step()
z = torch.randn(4096, 2); norms = []
print(f"\nafter 300 discriminator steps against an untrained generator, mean D(G(z)) = {torch.sigmoid(D0(G0(z))).mean():.4f}")
for name, loss in (("log(1 - D)", lambda a: torch.nn.functional.logsigmoid(-a).mean()), ("-log D", lambda a: -torch.nn.functional.logsigmoid(a).mean())):
    G0.zero_grad(); loss(D0(G0(z))).backward(); norms.append(math.sqrt(sum((q.grad ** 2).sum().item() for q in G0.parameters())))
    print(f"generator gradient norm with loss {name:10s}: {norms[-1]:.4f}")
print(f"ratio {norms[1] / norms[0]:.1f}"); assert norms[1] > 10 * norms[0]

# 3b. Train G and D in turn, one step each (k = 1), with the non-saturating generator loss. Four seeds; seed 0 is logged.
def play(seed, steps=2000, zdim=2, bs=256, log=False):
    torch.manual_seed(seed); gen = torch.Generator().manual_seed(1000 + seed); G, Dn = mlp(zdim, 1), mlp(1, 1)
    oG, oD = (torch.optim.Adam(m.parameters(), 1e-3, betas=(.5, .999)) for m in (G, Dn))
    for i in range(steps):
        f = G(torch.randn(bs, zdim)).detach(); lD = bce(Dn(data(bs)[:, None]), torch.ones(bs, 1)) + bce(Dn(f), torch.zeros(bs, 1)); oD.zero_grad(); lD.backward(); oD.step()
        lG = bce(Dn(G(torch.randn(bs, zdim))), torch.ones(bs, 1)); oG.zero_grad(); lG.backward(); oG.step()
        if log and (i + 1) % 500 == 0:
            with torch.no_grad(): xr = data(20000)[:, None]; xf = G(torch.randn(20000, zdim)); print(f"{i + 1:<6d} {torch.sigmoid(Dn(xr)).mean():.3f}    {torch.sigmoid(Dn(xf)).mean():.3f}    {w1(xf[:, 0], gen):.3f}  {(xf > 0).float().mean():.3f}")
    with torch.no_grad():
        xr = data(20000)[:, None]; xf = G(torch.randn(20000, zdim)); acc = ((Dn(xr) > 0).float().mean() + (Dn(xf) <= 0).float().mean()).item() / 2
        return w1(xf[:, 0], gen), (xf > 0).float().mean().item(), gap(xf[:, 0]), acc
print("\nseed 0 while it trains (the real data has 0.700 of its mass in the right hump)\nstep   D(real)  D(fake)  W1     right hump")
runs = [play(0, log=True)] + [play(s) for s in (1, 2, 3)]
floor = w1(data(20000), torch.Generator().manual_seed(5)); truth_gap = gap(data(200000, torch.Generator().manual_seed(6)))
print("\nafter 2000 steps, four seeds\nseed  W1      right hump  share in the gap  discriminator accuracy")
for s, (a, b, c, d) in enumerate(runs): print(f"{s}     {a:.3f}   {b:.3f}       {c:.3f}             {d:.3f}")
print(f"two real samples of this size differ by W1 {floor:.3f}; the gap holds {truth_gap:.3f} of the real data; 0.500 is a discriminator that cannot tell")
assert all(abs(r[1] - .7) < .05 and r[3] < .56 for r in runs) and all(r[0] < .4 for r in runs)
