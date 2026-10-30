# CU-506 lab: three checks on the DDPM paper (Ho, Jain, Abbeel 2020), each against an answer we can compute exactly.
# 1. the posterior of the forward process, 2. the weights that the simplified loss throws away, 3. the two reverse-variance choices.
# Run: python lab.py  (CPU only, about 3 s). Prints the same numbers every time.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64; T = 1000
betas = torch.linspace(1e-4, 0.02, T, dtype=D); alphas = 1 - betas; abar = torch.cumprod(alphas, 0)           # the paper's schedule: beta from 1e-4 to 0.02 in 1000 steps
abar_prev = torch.cat([torch.ones(1, dtype=D), abar[:-1]]); btilde = (1 - abar_prev) / (1 - abar) * betas      # beta-tilde_t, the posterior variance (eq. 7)

# 1. q(x_{t-1} | x_t, x_0) by Bayes' rule on a fine grid, against the closed form (eqs. 6 and 7) and the epsilon form of its mean (eq. 10). Here x_0 = 0.8, eps = 0.7.
print("t      mean by Bayes   closed-form mean   mean from eps (eq. 10)   variance by Bayes   beta-tilde_t")
x0, grid = 0.8, torch.linspace(-8, 8, 400001, dtype=D)
for t in (2, 50, 500, 1000):
    i = t - 1; eps = 0.7; xt = abar[i].sqrt() * x0 + (1 - abar[i]).sqrt() * eps
    prior = torch.exp(-0.5 * (grid - abar_prev[i].sqrt() * x0) ** 2 / (1 - abar_prev[i]))                      # q(x_{t-1} | x_0)
    like = torch.exp(-0.5 * (xt - alphas[i].sqrt() * grid) ** 2 / betas[i]); post = prior * like; post = post / post.sum()   # times q(x_t | x_{t-1})
    mean = (post * grid).sum(); var = (post * (grid - mean) ** 2).sum()
    closed = abar_prev[i].sqrt() * betas[i] / (1 - abar[i]) * x0 + alphas[i].sqrt() * (1 - abar_prev[i]) / (1 - abar[i]) * xt
    from_eps = (xt - betas[i] / (1 - abar[i]).sqrt() * eps) / alphas[i].sqrt()
    print(f"{t:<6d} {mean:.6f}        {closed:.6f}           {from_eps:.6f}                 {var:.4e}          {btilde[i]:.4e}")
    assert abs(mean - closed) < 1e-9 and abs(closed - from_eps) < 1e-12 and abs(var / btilde[i] - 1) < 1e-6

# 2. The weights. Take the bound's term at step t, (1 / 2 sigma_t^2) |mu-tilde - mu_theta|^2, with the network's mean written through epsilon (eq. 11).
#    The paper shows it equals beta_t^2 / (2 sigma_t^2 alpha_t (1 - abar_t)) times |eps - eps_theta|^2 (eq. 12). L_simple (eq. 14) weighs every step by 1.
n = 10000; ti = torch.randint(1, T, (n,)); x0r, er, et = torch.randn(n, dtype=D), torch.randn(n, dtype=D), torch.randn(n, dtype=D)       # random data, noise and a random 'network output'
xt = abar[ti].sqrt() * x0r + (1 - abar[ti]).sqrt() * er; sig2 = betas[ti]                                                              # sigma_t^2 = beta_t
mu_tilde = abar_prev[ti].sqrt() * betas[ti] / (1 - abar[ti]) * x0r + alphas[ti].sqrt() * (1 - abar_prev[ti]) / (1 - abar[ti]) * xt
mu_theta = (xt - betas[ti] / (1 - abar[ti]).sqrt() * et) / alphas[ti].sqrt()
lhs = (mu_tilde - mu_theta) ** 2 / (2 * sig2); rhs = betas[ti] ** 2 / (2 * sig2 * alphas[ti] * (1 - abar[ti])) * (er - et) ** 2
print(f"\nlargest difference between the two sides of eq. 12 over {n} random cases: {(lhs - rhs).abs().max():.1e}, while the terms reach {lhs.max():.1f}"); assert (lhs - rhs).abs().max() < 1e-9 * lhs.max()
w = betas / (2 * alphas * (1 - abar))
print("\nt       weight in the bound   weight in L_simple   L_simple / bound")
for t in (1, 10, 100, 500, 1000): print(f"{t:<7d} {w[t - 1]:<21.5f} {1:<20d} {1 / w[t - 1]:.1f}")
assert w[0] > 40 * w[99] and w[999] < w[0] / 40

# 3. The two reverse variances. For Gaussian data N(0, s^2) the exact reverse variance is a beta / (beta + alpha a), with a = abar_{t-1} s^2 + 1 - abar_{t-1}.
print("\nt       beta_tilde / beta   exact reverse variance / beta_t if the data have std 0 (a point), 0.5, 1")
for t in (2, 5, 10, 50, 500, 1000):
    i = t - 1; row = []
    for s in (0., 0.5, 1.):
        a = abar_prev[i] * s * s + 1 - abar_prev[i]; row.append((a * betas[i] / (betas[i] + alphas[i] * a) / betas[i]).item())
    print(f"{t:<7d} {btilde[i] / betas[i]:<19.4f} {row[0]:.4f}  {row[1]:.4f}  {row[2]:.4f}")
    assert abs(row[0] - btilde[i] / betas[i]) < 1e-12 and abs(row[2] - 1) < 1e-12
