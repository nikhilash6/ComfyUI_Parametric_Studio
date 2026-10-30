# CU-508 lab: the arithmetic of LoRA and the start-at-zero trick shared by LoRA and ControlNet, each checked against an exact answer.
# 1. parameter counts, 2. how well rank r can follow a change, against the best possible rank-r matrix, 3. why both methods start as the base model and how they begin to learn,
# 4. merging a LoRA into the weights against adding it as a side path.
# Run: python lab.py  (CPU only, about 10 s). Prints the same numbers every time.
import math, torch
torch.set_num_threads(1); torch.manual_seed(0)
D = torch.float64

# 1. A LoRA replaces the update of a d x k matrix, d*k numbers, by B (d x r) and A (r x k), r*(d+k) numbers.
d = 1280
print("layer 1280 x 1280: full update has", f"{d * d:,}", "numbers")
print("rank r   LoRA numbers   share of the full update   reduction")
for r in (1, 4, 16, 64): print(f"{r:<8d} {r * 2 * d:<14,d} {r * 2 * d / d / d:<26.4f} {d * d / (r * 2 * d):.0f}x")

# 2. Training a LoRA to follow a change DW* in a 64 x 64 layer. For inputs x ~ N(0, I), the expected squared error is |BA - DW*|^2 / 64, so this is a rank-r approximation of DW*.
#    The best possible rank-r matrix is the truncated SVD (Eckart-Young), whose error is the part of the singular-value spectrum beyond r.
n = 64
def target(s):
    U, _ = torch.linalg.qr(torch.randn(n, n, dtype=D)); V, _ = torch.linalg.qr(torch.randn(n, n, dtype=D)); S = torch.zeros(n, dtype=D); S[:len(s)] = torch.tensor(s, dtype=D)
    return U @ torch.diag(S) @ V.T, S
print("\nrelative error |BA - DW*| / |DW*| of a trained LoRA, against the best rank-r matrix")
print(f"{'change DW*':27s} " + "  ".join(f"{'r=' + str(r):<15s}" for r in (1, 2, 4, 8, 16)))
for name, s in (("rank 4 (4, 3, 2, 1)", [4., 3., 2., 1.]), ("decaying (2 x 0.75^i)", [2. * 0.75 ** i for i in range(n)])):
    T, S = target(s); cells = []
    for r in (1, 2, 4, 8, 16):
        torch.manual_seed(r); A = (torch.randn(r, n, dtype=D) / math.sqrt(n)).requires_grad_(True); B = torch.zeros(n, r, dtype=D, requires_grad=True)   # A random, B zero, as in the paper
        opt = torch.optim.Adam([A, B], 0.02); sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: 1 - i / 4000)
        for _ in range(4000): loss = ((B @ A - T) ** 2).sum(); opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        rel = ((B @ A - T).norm() / T.norm()).item(); floor = (S[r:].pow(2).sum().sqrt() / S.pow(2).sum().sqrt()).item(); cells.append(f"{rel:.4f} / {floor:.4f}")
        assert rel < floor + 0.01
    print(f"{name:27s} " + "  ".join(f"{c:<15s}" for c in cells))
print("(each cell: trained / best possible)")

# 3. Starting at zero. LoRA: h = W0 x + B A x, with B = 0. ControlNet: y_c = F(x) + Z2( F_c( x + Z1(c) ) ), with the 1x1 convolutions Z1 and Z2 zero (weights and biases).
W0 = torch.randn(n, n, dtype=D) / math.sqrt(n); A = (torch.randn(8, n, dtype=D) / math.sqrt(n)).requires_grad_(True); B = torch.zeros(n, 8, dtype=D, requires_grad=True)
x = torch.randn(32, n, dtype=D); y_star = x @ (W0 + target([4., 3., 2., 1.])[0]).T
out = x @ W0.T + x @ A.T @ B.T; print("\nLoRA at step 0: largest difference from the base layer", f"{(out - x @ W0.T).abs().max():.1f}")
rows = []
for step in range(3):
    loss = ((x @ W0.T + x @ A.T @ B.T - y_star) ** 2).mean(); gA, gB = torch.autograd.grad(loss, [A, B]); rows.append((step, gA.norm().item(), gB.norm().item()))
    with torch.no_grad(): A -= 0.05 * gA; B -= 0.05 * gB
print("step   |grad A|   |grad B|"); [print(f"{s:<6d} {a:<9.4f} {b:.4f}") for s, a, b in rows]
assert rows[0][1] == 0 and rows[0][2] > 0 and rows[1][1] > 0

F = torch.nn.Conv2d(8, 8, 3, padding=1).double(); Fc = torch.nn.Conv2d(8, 8, 3, padding=1).double(); Fc.load_state_dict(F.state_dict())          # locked block and its trainable copy
Z1, Z2 = torch.nn.Conv2d(8, 8, 1).double(), torch.nn.Conv2d(8, 8, 1).double()
for z in (Z1, Z2): torch.nn.init.zeros_(z.weight); torch.nn.init.zeros_(z.bias)
for p in F.parameters(): p.requires_grad_(False)
xi, c = torch.randn(4, 8, 16, 16, dtype=D), 10 * torch.randn(4, 8, 16, 16, dtype=D)                                                          # a large random condition
y_target = F(xi) + 0.5 * torch.nn.functional.avg_pool2d(c, 3, 1, 1)                                                                          # an output that depends on the condition
y_c = F(xi) + Z2(Fc(xi + Z1(c))); print(f"ControlNet at step 0: largest difference from the locked block {(y_c - F(xi)).abs().max():.1f}, with a condition of standard deviation 10")
print("step   |grad Z2|   |grad copy|   |grad Z1|"); params = list(Z1.parameters()) + list(Z2.parameters()) + list(Fc.parameters())
for step in range(3):
    loss = ((F(xi) + Z2(Fc(xi + Z1(c))) - y_target) ** 2).mean(); grads = torch.autograd.grad(loss, params)
    n1, n2, n3 = (torch.cat([g.flatten() for g in grads[a:b]]).norm().item() for a, b in ((0, 2), (2, 4), (4, 6)))   # Z1, Z2, copy
    print(f"{step:<6d} {n2:<11.4f} {n3:<12.4f} {n1:.4f}")
    with torch.no_grad():
        for p, g in zip(params, grads): p -= 0.05 * g
    if step == 0: assert n2 > 0 and n3 == 0 and n1 == 0
    if step == 1: assert n3 > 0 and n1 > 0

# 4. Two ways to apply a trained LoRA: merge W' = W + s BA into the weights, or keep W and add s B(Ax) beside it. Same function, different cost.
alpha, r = 8, 16; s = alpha / r; Bm, Am, Wm = torch.randn(d, r), torch.randn(r, d) / math.sqrt(d), torch.randn(d, d) / math.sqrt(d); xt = torch.randn(8, d)
merged = xt @ (Wm + s * Bm @ Am).T; bypass = xt @ Wm.T + s * (xt @ Am.T) @ Bm.T
print(f"\nmerged against side path, float32: largest difference {(merged - bypass).abs().max():.1e} on outputs of size {merged.abs().max():.0f}")
print(f"extra multiply-adds per token for the side path, rank {r}: {r * 2 * d:,} on top of {d * d:,}, which is {r * 2 * d / d / d:.1%}")
assert (merged - bypass).abs().max() < 1e-3
