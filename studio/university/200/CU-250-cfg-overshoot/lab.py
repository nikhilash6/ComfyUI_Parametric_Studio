# CU-250 lab: what raising cfg does on a problem where the right answer is known. CPU, fixed seed.
# Sixteen cells stand in for a latent. Each cell is its own small problem: all pictures put it at one of two values, and the prompt's pictures always pick the same one of the two.
# Every prediction is exact, so all the overshoot here comes from the cfg sum.
import torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64; DIM = 16
gen = torch.Generator().manual_seed(1)
T = torch.randn(DIM, dtype=D, generator=gen); T = T / T.std()         # the row the prompt asks for: spread 1 across its cells
OTHER = T - 2.5 * T.sign(); W2 = .25
def den_c(x, sg): v = W2 + sg ** 2; return (W2 * x + sg ** 2 * T) / v                # exact denoiser of one bell at the target
def den_u(x, sg):                                                                    # exact denoiser of the two-bell mix, cell by cell
    v = W2 + sg ** 2; r = torch.softmax(torch.stack([-.5 * (x - T) ** 2 / v, -.5 * (x - OTHER) ** 2 / v], -1), -1)
    return r[..., 0] * (W2 * x + sg ** 2 * T) / v + r[..., 1] * (W2 * x + sg ** 2 * OTHER) / v
def karras(n, lo=.03, hi=14.6, rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(hi ** (1 / rho) + r * (lo ** (1 / rho) - hi ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
SIG = karras(20)
def euler(start, cfg):
    x = start.clone(); peak = 0.; calls = 0
    for i in range(20):
        c = den_c(x, SIG[i]); u = den_u(x, SIG[i]); calls += 1 if cfg == 1 else 2
        d = u + (c - u) * cfg                                         # cfg_function, in denoised space
        peak = max(peak, d.abs().max().item())
        x = x + (x - d) / SIG[i] * (SIG[i + 1] - SIG[i])
    return x, peak, calls
start = 14.6 * torch.randn(200, DIM, dtype=D, generator=gen)
print(f"the target row has spread {T.std().item():.2f} and largest value {T.abs().max().item():.2f}")
print("cfg    spread   largest cell   distance from target   moved from cfg 7   largest prediction   calls")
ref, _, _ = euler(start, 7.); rows = {}
for cfg in (1., 2., 3., 5., 7., 10., 14., 20.):
    x, peak, calls = euler(start, cfg); sp = x.std(dim=-1).mean().item(); big = x.abs().max(dim=-1).values.mean().item(); dist = (x - T).pow(2).mean(-1).sqrt().mean().item(); moved = (x - ref).pow(2).mean(-1).sqrt().mean().item(); rows[cfg] = (sp, big, dist, moved)
    print(f"{cfg:<6.0f} {sp:<8.2f} {big:<14.2f} {dist:<22.2f} {moved:<18.2f} {peak:<20.1f} {calls}")
assert rows[14.][0] > rows[7.][0] > rows[3.][0]                       # spread keeps growing
assert rows[14.][2] > rows[7.][2] > rows[3.][2]                       # and the samples move further from what was asked for
assert rows[7.][3] == 0 and rows[14.][3] > .1
print(f"\nspread at cfg 14 is {rows[14.][0] / rows[7.][0]:.2f} times the spread at cfg 7. Steps and calls did not change, so cost does not warn you.")
