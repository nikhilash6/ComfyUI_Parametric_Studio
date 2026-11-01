# CU-308 lab: counting model calls, what a bigger stride costs on an ODE with a known answer, and what a skipped step really saves.
# The ODE is a toy, not a diffusion model. It shows the shape of the trade, not how any picture changes.
import math
def calls(steps, per_step, cfg):
    """samplers.py sampling_function drops the second conditioning when cfg is 1, unless a node turned that shortcut off."""
    return steps * per_step * (1 if cfg == 1 else 2)
print("model calls = steps x calls per step x (2 if CFG is not 1)")
for name, s, p, c in (("euler, 20 steps, CFG 7", 20, 1, 7), ("euler, 20 steps, CFG 1", 20, 1, 1), ("heun, 20 steps, CFG 7", 20, 2, 7), ("euler, 4 steps, CFG 1 (a distilled model)", 4, 1, 1), ("euler, 50 steps, CFG 7", 50, 1, 7)):
    print(f"  {name:44s} {calls(s, p, c):4d}")
assert calls(50, 1, 7) / calls(4, 1, 1) == 25
def f(x, t): return -x + math.sin(t)
def exact(x0, t): return (x0 + 0.5) * math.exp(-t) + 0.5 * math.sin(t) - 0.5 * math.cos(t)
def euler(x0, n):
    x, t, h = x0, 0.0, 1.0 / n
    for _ in range(n): x += h * f(x, t); t += h
    return x
def heun(x0, n):
    x, t, h = x0, 0.0, 1.0 / n
    for _ in range(n):
        a = f(x, t); b = f(x + h * a, t + h); x += h * (a + b) / 2; t += h
    return x
print("\nthe ODE dx/dt = -x + sin(t) from t = 0 to 1, whose exact answer we know")
print(f"  {'steps':>5s} {'euler calls':>12s} {'euler error':>12s} {'heun calls':>12s} {'heun error':>12s}")
errs = {}
for n in (1, 2, 4, 8, 16):
    ee, he = abs(euler(1.0, n) - exact(1.0, 1)), abs(heun(1.0, n) - exact(1.0, 1)); errs[n] = (ee, he)
    print(f"  {n:5d} {n:12d} {ee:12.5f} {2 * n:12d} {he:12.5f}")
assert errs[2][0] / errs[4][0] > 1.5 and errs[2][1] / errs[4][1] > 3
print(f"  halve the step: euler error x{errs[4][0] / errs[8][0]:.2f} smaller, heun x{errs[4][1] / errs[8][1]:.2f} smaller")
print("\nskipping steps, the idea behind a step cache: reuse the last change when the input barely moved")
def cached(n, thresh):
    x, t, h = 1.0, 0.0, 1.0 / n; last = None; lastx = None; used = 0
    for _ in range(n):
        if last is not None and abs(x - lastx) < thresh: d = last
        else: d = f(x, t); last = d; lastx = x; used += 1
        x += h * d; t += h
    return x, used
for th in (0.0, 0.01, 0.03, 0.1):
    x, u = cached(40, th); print(f"  threshold {th:4.2f}: {u:2d} of 40 calls, error {abs(x - exact(1.0, 1)):.5f}")
assert cached(40, 0.1)[1] < cached(40, 0.0)[1] and abs(cached(40, 0.1)[0] - exact(1.0, 1)) > abs(cached(40, 0.0)[0] - exact(1.0, 1))
