# CU-407 lab: three traps in a paper's results table, simulated. Every number is made up by this script and stands for no real paper.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
# 1. Best of K runs. Two methods with the SAME true score, some noise per run. The paper reports its method's best run against the baseline's mean.
def trial(K, sd=1.0, n=20000):
    new = 10 + sd * torch.randn(n, K); base = 10 + sd * torch.randn(n, 3); return (new.max(1).values - base.mean(1)).mean().item()
print("runs tried, best one reported   average apparent gain, true gain is 0 (noise sd 1)")
g = {}
for K in (1, 3, 5, 10, 30): g[K] = trial(K); print(f"{K:<31d} {g[K]:.2f}")
assert g[30] > g[10] > g[3] and abs(g[1]) < .05
# 2. Is the difference bigger than the noise? Mean of n runs each, standard error of the difference, and a rough 95% range of plus or minus 2 standard errors.
def read(m1, s1, m2, s2, n):
    se = math.sqrt(s1 ** 2 / n + s2 ** 2 / n); d = m1 - m2; return d, se, d - 2 * se, d + 2 * se
print("\nnew    sd    base   sd    runs  difference  range             verdict")
for r in ((2.30, .05, 2.40, .05, 5), (2.30, .20, 2.40, .20, 5), (2.30, .20, 2.40, .20, 50), (2.30, None, 2.40, None, 1)):
    if r[1] is None: print(f"{r[0]:<6.2f} ?     {r[2]:<6.2f} ?     1     {r[0] - r[2]:<11.2f} can't tell        no spread given, so no judgement"); continue
    d, se, lo, hi = read(*r); v = "clear of 0" if hi < 0 or lo > 0 else "includes 0, no claim"; print(f"{r[0]:<6.2f} {r[1]:<5.2f} {r[2]:<6.2f} {r[3]:<5.2f} {r[4]:<5d} {d:<11.2f} {lo:+.3f} to {hi:+.3f}  {v}")
assert read(2.30, .05, 2.40, .05, 5)[3] < 0 and read(2.30, .20, 2.40, .20, 5)[3] > 0
# 3. Percent gains flatter a small base. Same absolute change.
print("\nbase  new   change  percent")
for b, n in ((10.0, 9.9), (1.0, .9), (.2, .1)): print(f"{b:<5.1f} {n:<5.1f} {n - b:<7.1f} {(n - b) / b:+.0%}")
# 4. Several metrics, one winner. With 8 metrics, each a coin flip, how often is at least one clear of 0 in either direction, and how often is at least one a clear win for the new method?
n = 20000; z = torch.randn(n, 8); print(f"\n8 unrelated metrics, no true difference: at least one looks 'clear of 0' in {(z.abs() > 2).any(1).float().mean().item():.0%} of papers"); print(f"at least one a clear win for the new method, the direction a paper would headline: {(z > 2).any(1).float().mean().item():.0%} of papers"); assert (z.abs() > 2).any(1).float().mean() > .25
