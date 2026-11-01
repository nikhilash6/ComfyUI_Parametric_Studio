# CU-514 lab: the speed era with an exact teacher. Data is a mixture of two Gaussians, so the true denoiser has a formula and the probability-flow ODE can be solved to any accuracy.
# A small student learns the ODE's end point directly, then runs in a loop written like sample_lcm. Then two tables read from ComfyUI's source. CPU, no model.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1); F = torch.float64
W, M, S = torch.tensor([.3, .7], dtype=F), torch.tensor([-2., 1.5], dtype=F), torch.tensor([.3, .5], dtype=F)
def data(n, gen=None): k = torch.multinomial(W, n, True, generator=gen); return M[k] + S[k] * torch.randn(n, generator=gen, dtype=F)
def denoise(x, sig):
    """E[x0 | x0 + sig n = x], the perfect model."""
    x = x[:, None]; sig = sig[:, None] if torch.is_tensor(sig) and sig.dim() else torch.as_tensor(sig, dtype=F); V = S ** 2 + sig ** 2
    r = (W.log() - .5 * V.log() - .5 * (x - M) ** 2 / V).softmax(1); return (r * (M + S ** 2 / V * (x - M))).sum(1)
def karras(n, smin=.002, smax=20., rho=7.):
    r = [(smax ** (1 / rho) + i / max(n - 1, 1) * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho for i in range(n)] if n > 1 else [smax]; return r + [0.]
def euler(x, sigs):
    for a, b in zip(sigs[:-1], sigs[1:]): x = x + (b - a) * (x - denoise(x, a)) / a
    return x
def heun_end(x, sig, n=30):
    """The teacher: follow the ODE from sig down to about zero. sig may differ per sample."""
    s = sig.clone()
    for i in range(n):
        nxt = s * (1 - (i + 1) / n) ** 3 / (1 - i / n) ** 3 if i < n - 1 else s * 0
        d = (x - denoise(x, s)) / s; xn = x + (nxt - s) * d
        if i < n - 1: xn = x + (nxt - s) * (d + (xn - denoise(xn, nxt)) / nxt) / 2
        x, s = xn, nxt
    return x
def w1(x, ref): return (x.sort().values - ref.sort().values).abs().mean().item()
N = 20000; truth = data(N, torch.Generator().manual_seed(2)); floor = w1(data(N, torch.Generator().manual_seed(3)), truth); SMAX = 20.
start = torch.randn(N, generator=torch.Generator().manual_seed(1), dtype=F) * math.sqrt(SMAX ** 2 + 1.5)
# Is the teacher good? Its end points against the real data.
print(f"teacher, 30 Heun steps (59 calls): W1 {w1(heun_end(start, torch.full((N,), SMAX, dtype=F)), truth):.4f}; two real samples differ by {floor:.4f}")
# Student: learns (x, sigma) -> where the ODE from there ends. This is the ideal a consistency model aims at. Boundary form as in the LCM class of comfy_extras/nodes_model_advanced.py: at sigma near 0 the output is the input.
g = torch.Generator().manual_seed(4); M0 = 20000; s0 = (torch.rand(M0, generator=g, dtype=F) * (math.log(SMAX) - math.log(.002)) + math.log(.002)).exp(); x_in = data(M0, g) + s0 * torch.randn(M0, generator=g, dtype=F); end = heun_end(x_in, s0)
net = torch.nn.Sequential(torch.nn.Linear(2, 64), torch.nn.SiLU(), torch.nn.Linear(64, 64), torch.nn.SiLU(), torch.nn.Linear(64, 1))
SD = .5
def student(x, sig):
    x = x.float(); sig = sig.float(); c_skip = SD ** 2 / (sig ** 2 + SD ** 2); c_out = sig * SD / (sig ** 2 + SD ** 2).sqrt(); c_in = 1 / (sig ** 2 + SD ** 2).sqrt()
    return c_skip * x + c_out * net(torch.stack((c_in * x, sig.log() / 4), 1))[:, 0]
opt = torch.optim.Adam(net.parameters(), 2e-3); STEPS = 2000; sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, STEPS); torch.manual_seed(0)
for _ in range(STEPS):
    i = torch.randint(0, M0, (256,)); loss = ((student(x_in[i], s0[i]) - end[i].float()) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step(); sch.step()
def lcm_loop(x, sigs, seed=7):
    """The shape of sample_lcm: take the model's clean guess, then add fresh noise for the next level."""
    g = torch.Generator().manual_seed(seed)
    for a, b in zip(sigs[:-1], sigs[1:]):
        x = student(x, torch.full((len(x),), a, dtype=F)).detach().double()
        if b > 0: x = x + b * torch.randn(len(x), generator=g, dtype=F)
    return x
LOOP = {1: [SMAX, 0.], 2: [SMAX, 1., 0.], 4: [SMAX, 4., 1., .3, 0.], 8: [SMAX, 8., 4., 2., 1., .6, .3, .1, 0.]}
print("\nmodel calls   plain Euler, perfect model   student in an LCM loop")
rows = {}
for n in (1, 2, 4, 8, 32):
    e = w1(euler(start, karras(n)), truth); s = w1(lcm_loop(start, LOOP[n]), truth) if n in LOOP else None; rows[n] = (e, s)
    print(f"{n:<13d} {e:<28.4f} " + (f"{s:.4f}" if s is not None else "-"))
assert rows[1][1] < rows[1][0] / 5 and rows[4][1] < rows[4][0]
# The student is only as good as what it was trained for. Ask it about data it was not distilled from: same student, the data moved.
W2, M2 = torch.tensor([.7, .3], dtype=F), torch.tensor([-2., 1.5], dtype=F)
k = torch.multinomial(W2, N, True, generator=torch.Generator().manual_seed(9)); other = M2[k] + S[k] * torch.randn(N, generator=torch.Generator().manual_seed(10), dtype=F)
print(f"\nstudent against its own teacher's data {rows[1][1]:.4f}; against data with the hump weights swapped {w1(lcm_loop(start, LOOP[1]), other):.4f}. A student copies one teacher.")
assert w1(lcm_loop(start, LOOP[1]), other) > 5 * rows[1][1]
# Read from source. Calls per run: cfg 1 skips the second branch (sampling_function in comfy/samplers.py).
print("\nsteps   cfg   model calls   share of 20 steps at cfg 7")
for st, cfg in ((20, 7.), (8, 7.), (4, 1.), (1, 1.)):
    c = st * (1 if math.isclose(cfg, 1.) else 2); g = math.gcd(c, 40); print(f"{st:<7d} {cfg:<5.1f} {c:<13d} {c // g}/{40 // g}"); assert c <= 40
# c_skip and c_out from the LCM class. Timestep scaled by 10, sigma_data 0.5.
print("\ntimestep   c_skip    c_out   share of the answer taken straight from the input")
for t in (999, 499, 99, 19, 0):
    st = t * 10.; cs = .25 / (st ** 2 + .25); co = st / (st ** 2 + .25) ** .5; print(f"{t:<10d} {cs:<9.6f} {co:<7.4f} {cs:.6f}"); assert abs(cs + co ** 2 - 1) < 1e-9
assert (.25 / (0 + .25)) == 1.
# SDTurboScheduler (comfy_extras/nodes_custom_sampler.py) picks real timesteps from this list.
ts = torch.flip(torch.arange(1, 11) * 100 - 1, (0,))
for st in (1, 2, 4): print(f"SDTurboScheduler, steps {st}, denoise 1.0: timesteps {ts[:st].tolist()} then sigma 0")
assert ts[:4].tolist() == [999, 899, 799, 699]
