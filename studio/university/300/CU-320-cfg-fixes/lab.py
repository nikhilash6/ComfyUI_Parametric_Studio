# CU-320 lab: RescaleCFG, CFGNorm, APG and CFG-Zero-Star as sums, ported from v0.43.0 and compared with the real nodes on a CPU.
# The inputs are made-up latents, not model output: this shows what each sum does, not how a picture will look.
import torch
torch.manual_seed(0); torch.set_num_threads(1)
x = torch.randn(1, 4, 16, 16) * 3.2; c = torch.randn(1, 4, 16, 16); u = .8 * c + .25 * torch.randn(1, 4, 16, 16); SIGMA = 3.; S = 14.
def cfg(c, u, s): return u + (c - u) * s
def rescale(x, c, u, s, sigma, mult=.7):
    xs = x / (sigma * sigma + 1); vc = ((xs - c) * (sigma ** 2 + 1) ** .5) / sigma; vu = ((xs - u) * (sigma ** 2 + 1) ** .5) / sigma
    vcfg = vu + s * (vc - vu); vr = vcfg * (vc.std(dim=(1, 2, 3), keepdim=True) / vcfg.std(dim=(1, 2, 3), keepdim=True)); vf = mult * vr + (1 - mult) * vcfg
    return xs - vf * sigma / (sigma * sigma + 1) ** .5
def cfgnorm(c, u, s, strength=1.):
    p = cfg(c, u, s); return p * (torch.norm(c, dim=1, keepdim=True) / (torch.norm(p, dim=1, keepdim=True) + 1e-8)).clamp(0, 1) * strength
def apg(c, u, s, eta=1., thr=5.):
    g = c - u
    if thr > 0: n = g.norm(p=2, dim=[-1, -2, -3], keepdim=True); g = g * torch.minimum(torch.ones_like(n), thr / n)
    v = torch.nn.functional.normalize(c, dim=[-1, -2, -3]); par = (g * v).sum(dim=[-1, -2, -3], keepdim=True) * v; orth = g - par
    mc = (u + orth + eta * par) + (c - u) / s; return u + (mc - u) * s      # pre_cfg_function, then the normal cfg sum
def alpha(x, c, u): p = (x - c).flatten(1); n = (x - u).flatten(1); return ((p * n).sum(1, keepdim=True) / ((n ** 2).sum(1, keepdim=True) + 1e-8)).view(-1, 1, 1, 1)
def zero(x, c, u, s): a = alpha(x, c, u); o = cfg(c, u, s); return o + u * (a - 1) + s * u * (1 - a)
def stats(d): return f"{d.std().item():<10.2f} {d.abs().max().item():<10.2f} {torch.norm(d, dim=1).mean().item():.2f}"
print("method                          spread     largest    mean size of a cell")
rows = {"the positive prediction": c, "plain cfg 7": cfg(c, u, 7.), "plain cfg 14": cfg(c, u, S), "RescaleCFG 0.7": rescale(x, c, u, S, SIGMA), "CFGNorm strength 1": cfgnorm(c, u, S), "APG eta 1, threshold 5": apg(c, u, S), "APG eta 0, threshold 5": apg(c, u, S, 0.), "CFG-Zero-Star": zero(x, c, u, S)}
for k, v in rows.items(): print(f"{k:<31} {stats(v)}")
assert rows["RescaleCFG 0.7"].std() < rows["plain cfg 14"].std() and torch.norm(rows["CFGNorm strength 1"], dim=1).max() <= torch.norm(c, dim=1).max() + 1e-4
print("\nCFGNorm: can a cell ever come out larger than the positive's cell?", bool((torch.norm(rows["CFGNorm strength 1"], dim=1) > torch.norm(c, dim=1) + 1e-4).any()))
print("CFGNorm strength 0.5 against strength 1: everything is multiplied by", round((cfgnorm(c, u, S, .5).norm() / cfgnorm(c, u, S, 1.).norm()).item(), 3))
print("\nAPG with its limits off: eta 1, threshold 0, node cfg s")
for s in (3., 7., 14.):
    d = (apg(c, u, s, 1., 0.) - cfg(c, u, s + 1)).abs().max().item(); e = (apg(c, u, s, 1., 0.) - cfg(c, u, s)).abs().max().item(); print(f"s = {s:<5} largest difference from plain cfg s: {e:<8.3f} from plain cfg s + 1: {d:.6f}")
    assert d < 1e-4 and e > .1
gn = (c - u).norm().item(); print(f"\nthis guidance vector has length {gn:.2f}. A threshold above that never acts:", (apg(c, u, S, 1., gn + 1.) - apg(c, u, S, 1., 0.)).abs().max().item() < 1e-5)
print("APG at eta 1 with the node's other defaults: the part along the positive is kept whole, so only the threshold can act.")
a = alpha(x, c, u).item(); print(f"\nCFG-Zero-Star: alpha here is {a:.4f}. Near 1 it barely differs from plain cfg: largest change {(rows['CFG-Zero-Star'] - rows['plain cfg 14']).abs().max().item():.3f}")
# The velocity form in the paper is (1 - w) * a * v_u + w * v_c. Convert the node's result to the same form and compare.
paper = x - ((1 - S) * a * (x - u) + S * (x - c))
node = zero(x, c, u, S); gapv = (paper - node); expected = x * (1 - S) * (1 - a)
print(f"node against the paper's formula applied to x - D: largest difference {gapv.abs().max().item():.3f}, which is x * (1 - w) * (1 - alpha): {(gapv - expected).abs().max().item() < 1e-4}")
assert (gapv - expected).abs().max() < 1e-4
