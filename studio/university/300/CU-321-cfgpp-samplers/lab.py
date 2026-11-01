# CU-321 lab: plain Euler against euler_cfg_pp with exact predictions. Port of sample_euler_cfg_pp, compared with the real sampler on a CPU using a stand-in model.
import torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
def den(x, s):
    v = .25 + s ** 2; c = (.25 * x + s ** 2 * 1.5) / v
    r = torch.softmax(torch.stack([-.5 * (x + 1) ** 2 / v, -.5 * (x - 1.5) ** 2 / v], -1), -1); u = r[..., 0] * (.25 * x - s ** 2) / v + r[..., 1] * (.25 * x + s ** 2 * 1.5) / v
    return c, u
def karras(n=20, lo=.03, hi=14.6, rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(hi ** (1 / rho) + r * (lo ** (1 / rho) - hi ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
SIG = karras()
def euler(x, s):
    for i in range(20):
        c, u = den(x, SIG[i]); d = u + (c - u) * s; x = x + (x - d) / SIG[i] * (SIG[i + 1] - SIG[i])
    return x
def pp(x, s):
    for i in range(20):
        c, u = den(x, SIG[i]); d = u + (c - u) * s; x = d if SIG[i + 1] == 0 else d + SIG[i + 1] * (x - u) / SIG[i]     # noise taken from the unconditional prediction
    return x
start = 14.6 * torch.randn(40000, dtype=D)
print("the prompt asks for the blob at 1.5, with width .5")
print("cfg     euler mean   euler width   euler_cfg_pp mean   euler_cfg_pp width")
R = {}
for s in (.2, .4, .6, .8, 1., 1.5, 2., 5., 7., 12.5):
    a = euler(start, s); b = pp(start, s); R[s] = (a.mean().item(), b.mean().item()); print(f"{s:<7} {a.mean():<12.2f} {a.std():<13.2f} {b.mean():<19.2f} {b.std():.2f}")
assert abs(R[1.][0] - 1.5) < .1 and R[1.][1] > 1.8 and R[7.][1] > R[7.][0]
print("\nsame cfg number, different strength: which plain cfg lands closest to each CFG++ setting on this toy")
for s in (.2, .4, .6, .8, 1.):
    best = min((1., 1.5, 2., 3., 4., 5., 6., 7., 8., 10., 12.5, 15.), key=lambda w: abs(euler(start[:4000], w).mean().item() - R[s][1])); print(f"cfg_pp {s:<5} is nearest plain cfg {best}")
print("\npredictions per step: euler at cfg 1 = 1, euler_cfg_pp at cfg 1 = 2 (the sampler sets disable_cfg1_optimization)")
c, u = den(torch.tensor(.7, dtype=D), SIG[10]); s = SIG[10]; sn = SIG[11]; x0 = torch.tensor(.7, dtype=D); d = u + (c - u) * 1.
plain = d + sn * (x0 - d) / s; ppx = d + sn * (x0 - u) / s
print(f"one step at cfg 1: same clean estimate, plain re-noises to {plain.item():.4f}, CFG++ to {ppx.item():.4f}")
assert abs((plain - (x0 + (x0 - d) / s * (sn - s))).item()) < 1e-9 and abs(plain.item() - ppx.item()) > 1e-4
