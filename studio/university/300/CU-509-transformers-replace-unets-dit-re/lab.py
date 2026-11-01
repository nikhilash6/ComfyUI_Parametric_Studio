# CU-509 lab: rectified flow with an exact answer. Data is a mixture of two Gaussians, so the true velocity field has a formula.
# Checks: the path, what one Euler step really does, where the steps go, how straight the real paths are, and what reflow buys. CPU, no model.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1); F = torch.float64
W, M, S = torch.tensor([.3, .7], dtype=F), torch.tensor([-2., 1.5], dtype=F), torch.tensor([.3, .5], dtype=F)
MEAN = (W * M).sum().item()
def data(n, gen=None): k = torch.multinomial(W, n, True, generator=gen); return M[k] + S[k] * torch.randn(n, generator=gen, dtype=F)
def velocity(x, t):
    """E[x1 - x0 | x_t = x] for x_t = (1 - t) x0 + t x1, x0 ~ N(0, 1). t = 0 is noise, t = 1 is data."""
    x = x[:, None]; D = (1 - t) ** 2 + (t * S) ** 2; d = x - t * M
    r = (W.log() - .5 * D.log() - .5 * d ** 2 / D).softmax(1)
    return (r * (M + t * S ** 2 / D * d - (1 - t) / D * d)).sum(1)
def euler(x, grid, f=velocity):
    for a, b in zip(grid[:-1], grid[1:]): x = x + (b - a) * f(x, a)
    return x
def uniform(n): return [i / n for i in range(n + 1)]
def shifted(n, s): return [1 - s * u / (1 + (s - 1) * u) for u in [1 - i / n for i in range(n + 1)]]   # time_snr_shift in comfy/model_sampling.py, sigma = 1 - t
def w1(x, ref): return (x.sort().values - ref.sort().values).abs().mean().item()
N = 20000; x0 = torch.randn(N, generator=torch.Generator().manual_seed(1), dtype=F); truth = data(N, torch.Generator().manual_seed(2)); floor = w1(data(N, torch.Generator().manual_seed(3)), truth)

# 1. The straight line is one pair's path. Its velocity does not change along the line. This is the target, not what the model ends up following.
a, b = torch.tensor(-.7, dtype=F), torch.tensor(1.3, dtype=F); pts = [(1 - t) * a + t * b for t in (0, .25, .5, .75, 1)]
gaps = {round((pts[i + 1] - pts[i]).item() / .25, 6) for i in range(4)}; print(f"one pair x0 = -0.7, x1 = 1.3: speed on each quarter of the line {sorted(gaps)}, x1 - x0 = {(b - a).item():.1f}"); assert len(gaps) == 1

# 2. One Euler step from pure noise. At t = 0 the noise says nothing about which x1 it will meet, so v(x, 0) = E[x1] - x and every start lands on the mean.
one = euler(x0, [0., 1.]); print(f"one Euler step from t = 0: every one of {N:,d} samples lands in [{one.min().item():.4f}, {one.max().item():.4f}]; the mean of the data is {MEAN:.4f}"); assert (one - MEAN).abs().max() < 1e-9

# 3. Steps. W1 is the average gap between sorted samples and the real data, lower is better.
print(f"\nerror (W1) against the real data, by number of Euler steps. Two real samples differ by {floor:.4f}")
print("steps   even in t   shift 3 (SD3 default)")
rows = {}
for n in (1, 2, 4, 8, 16, 32, 64):
    rows[n] = (w1(euler(x0, uniform(n)), truth), w1(euler(x0, shifted(n, 3.)), truth)); print(f"{n:<7d} {rows[n][0]:<11.4f} {rows[n][1]:.4f}")
assert rows[1][0] > 1.0 and rows[64][0] < .06

# 4. How straight are the real paths? For each start, compare the velocity along the path with the straight line from its own start to its own end.
def straightness(f, x, n=100):
    grid = uniform(n); end = euler(x, grid, f); line = end - x; total = 0.; cur = x
    for a, b in zip(grid[:-1], grid[1:]): v = f(cur, a); total += ((v - line) ** 2).mean().item() * (b - a); cur = cur + (b - a) * v
    return total, end
s1, ends = straightness(velocity, x0[:4000]); print(f"\nexact field: mean squared departure from a straight line {s1:.4f} (0 would be perfectly straight)"); assert s1 > .05

# 5. Reflow (Liu et al.). Take the pairs the first flow produced, (start, its end), which no longer cross, and train a new model on those. The same training code on independent pairs is the first flow.
def mlp(): return torch.nn.Sequential(torch.nn.Linear(2, 64), torch.nn.SiLU(), torch.nn.Linear(64, 64), torch.nn.SiLU(), torch.nn.Linear(64, 64), torch.nn.SiLU(), torch.nn.Linear(64, 1))
def train(sample, steps=1500, bs=256):
    torch.manual_seed(0); net = mlp().float(); opt = torch.optim.Adam(net.parameters(), 2e-3); sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, steps)
    for _ in range(steps):
        p, q = sample(bs); t = torch.rand(bs); xt = (1 - t) * p + t * q; loss = ((net(torch.stack((xt, t), 1))[:, 0] - (q - p)) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step(); sched.step()
    return lambda x, t: net(torch.stack((x.float(), torch.full_like(x.float(), t)), 1))[:, 0].detach().double()
g = torch.Generator().manual_seed(4); P0 = torch.randn(20000, generator=g, dtype=F); P1 = euler(P0, uniform(100))
def indep(bs): return torch.randn(bs), data(bs).float()
def coupled(bs): i = torch.randint(0, len(P0), (bs,)); return P0[i].float(), P1[i].float()
first, second = train(indep), train(coupled); sf, _ = straightness(first, x0[:4000]); ss, _ = straightness(second, x0[:4000])
print("\ntrained model                 departure from straight   W1 at 1 step   2 steps   4 steps   64 steps")
for name, f, s in (("first flow, independent pairs", first, sf), ("reflow, the first flow's pairs", second, ss)):
    print(f"{name:<29s} {s:<25.4f} " + "   ".join(f"{w1(euler(x0, uniform(n), f), truth):.4f}" for n in (1, 2, 4)) + f"     {w1(euler(x0, uniform(64), f), truth):.4f}")
r1, r2 = w1(euler(x0, [0., 1.], first), truth), w1(euler(x0, [0., 1.], second), truth); print(f"one step: reflow's error is {r1 / r2:.1f} times smaller"); assert ss < sf / 3 and r2 < r1 / 3

# 6. ComfyUI's CONST class writes the same line backwards: sigma = 1 - t, x = sigma * noise + (1 - sigma) * x0, and the model output is noise minus data.
clean, noise, sig = torch.tensor(.8, dtype=F), torch.tensor(-1.1, dtype=F), torch.tensor(.35, dtype=F); xs = sig * noise + (1 - sig) * clean; out = noise - clean; back = xs - out * sig
print(f"\nCONST: sigma {sig.item():.2f}, input {xs.item():.4f}, output noise - data {out.item():.4f}, calculate_denoised gives {back.item():.4f}, the clean value is {clean.item():.4f}"); assert abs(back - clean) < 1e-12
