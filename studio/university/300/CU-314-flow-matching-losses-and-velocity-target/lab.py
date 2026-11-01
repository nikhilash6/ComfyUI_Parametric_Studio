# CU-314 lab: the flow matching training target, what its loss can and cannot reach, how the same error looks in other units, and how often each noise level gets trained.
# The formulas follow comfy/model_sampling.py (CONST, time_snr_shift) and comfy_extras/nodes_train.py (TrainSampler.fwd_bwd, _generate_batch_sigmas). Timestep sampling follows Esser et al. 2024.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
W, M, S = torch.tensor([.3, .7], dtype=D), torch.tensor([-2., 1.5], dtype=D), torch.tensor([.3, .5], dtype=D)
def data(n): k = torch.multinomial(W, n, True); return M[k] + S[k] * torch.randn(n, dtype=D)
def den(y, s):
    v = S ** 2 + s ** 2; r = torch.softmax(W.log() - .5 * (y[..., None] - M) ** 2 / v - .5 * v.log(), -1); return (r * (S ** 2 * y[..., None] + s ** 2 * M) / v).sum(-1)
def best_v(x, t): return (x - den(x / (1 - t), t / (1 - t))) / t          # E[eps - x0 | x_t = x]: what least squares must learn
# 1. One training pair.
x0, e = torch.tensor(1.5, dtype=D), torch.tensor(-.7, dtype=D)
print("one pair: x0 1.5, noise -0.7")
print("t     x_t      target v  x_t - t v  (the CONST.calculate_denoised formula)")
for t in (.1, .5, .9):
    x = (1 - t) * x0 + t * e; v = e - x0; print(f"{t:<5} {x:<+8.3f} {v:<+9.3f} {x - t * v:+.3f}"); assert abs(x - t * v - x0) < 1e-12
# 2. The loss has a floor. Even the perfect model cannot know which pair it is looking at.
n = 400000; x0 = data(n); e = torch.randn(n, dtype=D)
print("\nthe best possible velocity loss at each t, and what a model that ignores x would score")
print("t     floor (perfect model)  constant guess")
fl = {}
for t in (.05, .2, .5, .8, .95):
    x = (1 - t) * x0 + t * e; tgt = e - x0; fl[t] = (tgt - best_v(x, t)).pow(2).mean().item(); print(f"{t:<5} {fl[t]:<22.4f} {tgt.var():.4f}")
print(f"spread of x0 alone, where the floor heads as t nears 1: {x0.var():.2f}")
assert min(fl.values()) > .01
# Same error, other units: x0_hat = x_t - t v_hat and eps_hat = x_t + (1 - t) v_hat.
print("\nthe same velocity error of 0.1 read in other units")
print("t     clean-latent error (t x 0.1)   noise error ((1 - t) x 0.1)")
for t in (.05, .5, .95):
    x = (1 - t) * x0[:1000] + t * e[:1000]; v = e[:1000] - x0[:1000]; vh = v + .1
    assert abs(((x - t * vh) - x0[:1000]).abs().max() - t * .1) < 1e-9 and abs(((x + (1 - t) * vh) - e[:1000]).abs().max() - (1 - t) * .1) < 1e-9
    print(f"{t:<5} {t * .1:<30.3f} {(1 - t) * .1:.3f}")
# Core's trainer compares clean-latent estimates, so on a CONST model each noise level's velocity error counts with weight sigma^2.
print("\nComfyUI's TrainSampler loss on a flow model, against plain velocity loss, with the same perfect model")
print("sigma  velocity loss  clean-latent loss  ratio  sigma^2")
for t in (.2, .5, .8):
    x = (1 - t) * x0 + t * e; vh = best_v(x, t); lv = (vh - (e - x0)).pow(2).mean().item(); l0 = ((x - t * vh) - x0).pow(2).mean().item(); print(f"{t:<6} {lv:<14.4f} {l0:<18.4f} {l0 / lv:<6.3f} {t * t:.3f}"); assert abs(l0 / lv - t * t) < 1e-9
# How often each noise level is trained.
torch.manual_seed(1); u = torch.rand(1000000, dtype=D); shift = lambda a, t: a * t / (1 + (a - 1) * t)
logit = torch.sigmoid(torch.randn(1000000, dtype=D)); core3 = shift(3., 1 - u)
print("\nshare of training samples by noise level")
print("sampling                                  t<0.25   0.25-0.75  t>0.75")
for k, a in (("uniform", u), ("logit-normal m 0, s 1 (Esser et al.)", logit), ("uniform through shift 3 (core's trainer)", core3)):
    print(f"{k:41s} {(a < .25).double().mean():<8.3f} {((a >= .25) & (a <= .75)).double().mean():<10.3f} {(a > .75).double().mean():.3f}")
assert ((logit >= .25) & (logit <= .75)).double().mean() > .6
# 3. Train on the per-pair target. The loss settles at the floor, not at zero, and the model still works.
net = torch.nn.Sequential(torch.nn.Linear(2, 128), torch.nn.SiLU(), torch.nn.Linear(128, 128), torch.nn.SiLU(), torch.nn.Linear(128, 128), torch.nn.SiLU(), torch.nn.Linear(128, 1)); opt = torch.optim.Adam(net.parameters(), 2e-3)
torch.manual_seed(2)
ts = torch.rand(200000, dtype=D).clamp(.001, .999); xa, ea = data(200000), torch.randn(200000, dtype=D); xta = (1 - ts) * xa + ts * ea
fl_all = 0.
for i in range(0, 200000, 5000):
    t = ts[i:i + 5000]; xt = xta[i:i + 5000]; yy = xt / (1 - t); ss = t / (1 - t); v = S ** 2 + ss[:, None] ** 2; r = torch.softmax(W.log() - .5 * (yy[:, None] - M) ** 2 / v - .5 * v.log(), -1); d = (r * (S ** 2 * yy[:, None] + ss[:, None] ** 2 * M) / v).sum(-1); fl_all += ((ea[i:i + 5000] - xa[i:i + 5000]) - (xt - d) / t).pow(2).mean().item() / 40
print(f"\nfloor of the loss averaged over uniform t: {fl_all:.3f}")
print("step   running velocity loss")
run = 0.
for i in range(2500):
    x0b = data(1024).float(); eb = torch.randn(1024); t = torch.rand(1024); xt = (1 - t) * x0b + t * eb
    loss = ((net(torch.stack([xt, t], 1))[:, 0] - (eb - x0b)) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step(); run += loss.item()
    if (i + 1) % 500 == 0: print(f"{i + 1:<6d} {run / 500:.3f}"); last = run / 500; run = 0.
assert last > fl_all * .9
with torch.no_grad():
    x = torch.randn(40000); grid = torch.linspace(1, 0, 33)
    for i in range(32): x = x + net(torch.stack([x, torch.full_like(x, grid[i].item())], 1))[:, 0] * (grid[i + 1] - grid[i])
w = (x.double().sort().values - data(40000).sort().values).abs().mean().item(); fl2 = (data(40000).sort().values - data(40000).sort().values).abs().mean().item()
print(f"32 Euler steps from that model: W1 to the data {w:.3f}, two real samples of this size differ by {fl2:.3f}"); assert w < .2
