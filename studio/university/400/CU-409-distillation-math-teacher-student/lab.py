# CU-409 lab: distillation on a problem with an exact answer. The data is Gaussian with std s = 1, so the true denoiser is D(x, sigma) = x / (1 + sigma^2),
# and the probability-flow ODE has the exact map x(sigma_a) -> x(sigma_b) = x * sqrt(1 + sigma_b^2) / sqrt(1 + sigma_a^2).
# Each step of a sampler on this problem is multiplying by a number, so a student is a list of numbers fitted by least squares on samples. No network, no training tricks: the shape of the method, not its size.
import math, torch
torch.set_num_threads(1); g = torch.Generator().manual_seed(0)
SMAX, SMIN, RHO = 80.0, 0.002, 7.0                     # the schedule from Karras et al. 2022
def karras(n): return [(SMAX ** (1 / RHO) + i / max(n - 1, 1) * (SMIN ** (1 / RHO) - SMAX ** (1 / RHO))) ** RHO for i in range(n)] + [0.0]
D = lambda x, s: x / (1 + s ** 2)
def euler_step(x, s, t): return x + (x - D(x, s)) / s * (t - s) if s > 0 else x
def run(steps, x):
    sig = karras(steps)
    for i in range(steps): x = euler_step(x, sig[i], sig[i + 1])
    return x
N = 400_000; z = torch.randn(N, generator=g, dtype=torch.float64); noise = z * math.sqrt(1 + SMAX ** 2)    # a true sample at sigma max has std sqrt(1 + 80^2)
truth = noise / math.sqrt(1 + SMAX ** 2)                                                                  # where the exact ODE takes each one
err = lambda x: (x - truth).pow(2).mean().sqrt().item()
print("plain Euler. Model calls, error against the exact path, and the std of the result (should be 1.000)")
print("calls   error    std")
eu = {}
for n in (1, 2, 4, 8, 16, 32, 64, 128):
    x = run(n, noise); eu[n] = err(x); print(f"{n:<7} {eu[n]:<8.4f} {x.std().item():.3f}")
assert eu[128] < eu[8] < eu[1]
# Progressive distillation: the student's one step copies two teacher steps; then it becomes the teacher and the steps halve.
def fit(a, b): return ((a * b).sum() / (a * a).sum()).item()     # least squares for b = c a
def distill(teacher_steps):
    sig = karras(teacher_steps); edges = list(sig); x0 = torch.randn(200_000, generator=g, dtype=torch.float64)
    coef = []
    for i in range(teacher_steps):                                   # the teacher's own numbers, read from samples at each level
        xs = x0 * math.sqrt(1 + sig[i] ** 2); coef.append(fit(xs, euler_step(xs, sig[i], sig[i + 1])))
    rounds = [(teacher_steps, list(coef), list(edges))]
    while len(coef) > 1:
        new = []; ne = edges[::2]
        for j in range(0, len(coef), 2):
            xs = x0 * math.sqrt(1 + edges[j] ** 2); target = xs * coef[j] * coef[j + 1]; new.append(fit(xs, target))
        coef, edges = new, ne; rounds.append((len(coef), list(coef), list(edges)))
    return rounds
def run_student(coef, x):
    for c in coef: x = x * c
    return x
print("\nprogressive distillation from a 64-step teacher. Each round halves the steps")
print("student calls   student error   Euler at the same calls   std of student")
rs = distill(64); pd = {}
for k, coef, _ in rs:
    x = run_student(coef, noise); pd[k] = err(x); print(f"{k:<15} {pd[k]:<15.4f} {eu[k]:<25.4f} {x.std().item():.3f}")
assert pd[1] < eu[1] and pd[4] < eu[4]
print("\nthe student copies the teacher, errors included. One-step student from each teacher, against the teacher's own error")
print("teacher steps   teacher error   one-step student error")
cp = {}
for t in (4, 16, 64):
    x = run(t, noise); c = distill(t)[-1][1]; s = run_student(c, noise); cp[t] = (err(x), err(s)); print(f"{t:<15} {cp[t][0]:<15.4f} {cp[t][1]:.4f}")
    assert abs(cp[t][0] - cp[t][1]) < 0.01
# Consistency: f(x, sigma) maps any point on a path to the path's end. Fit c(sigma) in f = c x so that neighbouring levels on a teacher path agree, with f(x, sigma_min) = x.
def consistency(levels):
    sig = karras(levels); x0 = torch.randn(200_000, generator=g, dtype=torch.float64); f = [None] * levels
    f[levels - 1] = 1.0                                                  # the boundary condition at the smallest level
    for i in range(levels - 2, -1, -1):
        xs = x0 * math.sqrt(1 + sig[i] ** 2); nxt = euler_step(xs, sig[i], sig[i + 1]); f[i] = fit(xs, f[i + 1] * nxt)
    return sig, f
print("\nconsistency: fit c(sigma) so that f(x, sigma) = c x agrees across neighbouring levels of an Euler teacher")
print("levels   c at sigma max   exact c   one-call error   Euler one-call error")
cons = {}
for lv in (8, 32, 128):
    sig, f = consistency(lv); ex = 1 / math.sqrt(1 + SMAX ** 2); x = noise * f[0]; cons[lv] = err(x)
    print(f"{lv:<8} {f[0]:<16.5f} {ex:<9.5f} {cons[lv]:<16.4f} {eu[1]:.4f}")
assert cons[128] < cons[8] and cons[128] < 0.021
sig, f = consistency(128); idx = [0, 32, 64, 96, 127]
print("\nself-consistency on one path, 128 levels: the answer read from different points on it. Exact end value of this path is the first column")
x = torch.tensor([1.0], dtype=torch.float64) * math.sqrt(1 + SMAX ** 2); end = x / math.sqrt(1 + SMAX ** 2); path = {}
print(f"exact end {end.item():.4f}   predictions from levels " + " ".join(f"{sig[i]:.3f}" for i in idx))
xx = x.clone(); out = []
for i in range(127):
    if i in idx: out.append((xx * f[i]).item())
    xx = euler_step(xx, sig[i], sig[i + 1])
out.append((xx * f[127]).item()); print("  " + " ".join(f"{v:.4f}" for v in out))
assert max(out) - min(out) < 1e-6
