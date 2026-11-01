# CU-313 lab: a mixture of experts layer with the same gate, top-k and sum as comfy/ldm/hidream/model.py. CPU, random weights: this shows mechanics, not a trained router.
import torch
torch.manual_seed(0); torch.set_num_threads(1)
D, H, E, K = 32, 64, 4, 2
class FF(torch.nn.Module):
    def __init__(s, d, h): super().__init__(); s.a = torch.nn.Linear(d, h); s.b = torch.nn.Linear(h, d)
    def forward(s, x): return s.b(torch.nn.functional.silu(s.a(x)))
class MoE(torch.nn.Module):
    def __init__(s): super().__init__(); s.w = torch.nn.Parameter(torch.randn(E, D)); s.ex = torch.nn.ModuleList(FF(D, H) for _ in range(E)); s.shared = FF(D, H // 2); s.calls = [0] * E
    def gate(s, x): return torch.topk((x @ s.w.T).softmax(-1), K, -1, sorted=False)
    def forward(s, x):
        w, idx = s.gate(x); xr = x.repeat_interleave(K, 0); y = torch.empty_like(xr); flat = idx.view(-1)
        for i, e in enumerate(s.ex):
            m = flat == i; s.calls[i] = int(m.sum()); y[m] = e(xr[m])
        return (y.view(*w.shape, -1) * w.unsqueeze(-1)).sum(1) + s.shared(x)
m = MoE(); x = torch.randn(1000, D); y = m(x); w, idx = m.gate(x)
print(f"tokens {x.shape[0]}, experts {E}, each token uses {K}: output {tuple(y.shape)}"); assert y.shape == x.shape
print("first 4 tokens, expert ids and weights:")
for i in range(4): print(f"  {idx[i].tolist()}  {[round(v, 3) for v in w[i].tolist()]}  weights sum to {w[i].sum().item():.3f}")
assert (w.sum(1) <= 1.0001).all(); print("load on each expert:", m.calls, " total", sum(m.calls), "=", x.shape[0], "x", K); assert sum(m.calls) == x.shape[0] * K
# A check by brute force: compute every expert for every token, then pick. Same answer, much more work.
with torch.no_grad():
    allout = torch.stack([e(x) for e in m.ex], 1); pick = allout.gather(1, idx.unsqueeze(-1).expand(-1, -1, D)); y2 = (pick * w.unsqueeze(-1)).sum(1) + m.shared(x)
print(f"routed against compute-all-then-pick: max difference {(y - y2).abs().max().item():.1e}"); assert (y - y2).abs().max() < 1e-4
# What it buys: parameters grow with E, work per token with K.
ps = lambda mod: sum(p.numel() for p in mod.parameters())
print("\nexperts  top-k  expert parameters stored   expert calls per token")
for e_, k_ in ((1, 1), (4, 2), (6, 2), (16, 2)): print(f"{e_:<8d} {k_:<6d} {e_ * ps(m.ex[0]):<26,d} {k_}")
# A gate that always prefers one expert: this is what the auxiliary loss exists to fight in training.
b = torch.randn(1000, D) + 0.5; g = (b @ torch.cat([torch.ones(1, D), torch.randn(E - 1, D) * .1]).T).softmax(-1).topk(1, -1)[1].view(-1).bincount(minlength=E).tolist()
print("\ntop-1 load when one expert's gate weights line up with the data:", g); assert max(g) > 600
# The topk choice has no gradient. Only the weights do.
xx = torch.randn(1, D, requires_grad=True); ww = m.w; w1, i1 = torch.topk((xx @ ww.T).softmax(-1), K, -1); print("gradient flows through the weights:", w1.requires_grad, " through the chosen ids:", i1.requires_grad); assert w1.requires_grad and not i1.requires_grad
