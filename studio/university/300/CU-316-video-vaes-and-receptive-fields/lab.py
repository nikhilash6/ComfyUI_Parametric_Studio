# CU-316 lab: receptive fields measured by experiment, the causal first-frame rule, and tile overlap. Real torch convolutions, CPU, seeded.
import math, torch
import torch.nn.functional as F
torch.manual_seed(0); torch.set_num_threads(1)
# 1. The formula: r = 1 + sum over layers of (k - 1) * (product of the strides before that layer).
def rf(layers):
    r, j = 1, 1
    for k, s in layers: r += (k - 1) * j; j *= s
    return r, j
def measured(layers, n=301):
    """push a weight of 1 through each conv: which inputs reach the middle output? Measured with autograd, not with the formula."""
    x = torch.zeros(1, 1, n, requires_grad=True); y = x + 1
    for k, s in layers: y = F.conv1d(y, torch.ones(1, 1, k), stride=s)
    y[0, 0, y.shape[2] // 2].backward(); return int((x.grad != 0).sum().item())
print("layers (kernel, stride)                        formula r  measured  output spacing j")
for L in ([(3, 1)], [(3, 2)], [(3, 2), (3, 2)], [(3, 1), (3, 1), (3, 1), (3, 1)], [(3, 2), (3, 2), (3, 2), (3, 2)], [(3, 1), (3, 2), (3, 1), (3, 2), (3, 1), (3, 2)]):
    r, j = rf(L); m = measured(L); print(f"{str(L):46s} {r:<10d} {m:<9d} {j}"); assert r == m
# 2. The draft of this lesson's lab claimed two stride-2 layers on 7 pixels give 3 pixels. One layer does. Two give 1.
c = lambda n: (n - 3) // 2 + 1; print(f"\nspatial size with kernel 3, stride 2, no padding: 7 -> {c(7)} after one layer, {c(c(7))} after two")
assert c(c(7)) == 1
# 3. Causal padding and the first frame. Pad 2 frames before, none after, stride 2, twice: a stride-4 stack. The output count follows (n - 1) // 4 + 1.
def causal_t(n):
    x = torch.zeros(1, 1, n, 1, 1); k = torch.ones(1, 1, 3, 1, 1)
    for _ in range(2): x = F.conv3d(F.pad(x, (0, 0, 0, 0, 2, 0), mode="replicate"), k, stride=(2, 1, 1))
    return x.shape[2]
print("\nframes in -> latent frames from two causal stride-2 layers, against (n - 1) // 4 + 1:")
for n in (1, 5, 9, 17, 21, 81, 120, 121):
    o = causal_t(n); print(f"{n:>4d} -> {o:>3d}   {(n - 1) // 4 + 1}"); assert o == (n - 1) // 4 + 1
# 4. No future leak: change a late frame and check an earlier output.
x = torch.rand(1, 1, 21, 1, 1); y = x.clone(); y[0, 0, 20] += 5.0; k = torch.rand(1, 1, 3, 1, 1)
def stack(v):
    for _ in range(2): v = F.conv3d(F.pad(v, (0, 0, 0, 0, 2, 0), mode="replicate"), k, stride=(2, 1, 1))
    return v
a, b = stack(x), stack(y); ch = (a != b).flatten().nonzero().flatten().tolist(); print(f"\nchange frame 20 of 21: the {a.shape[2]} latent frames that move are {ch}")
assert ch == [5]
# 5. Why tiles need overlap: decode a 1D latent with a stack of receptive radius 3, in two tiles, and compare. Error stops when the overlap covers the radius.
torch.manual_seed(1); w = [torch.randn(1, 1, 3) * 0.6 for _ in range(3)]; z = torch.randn(1, 1, 64)
def dec(v):
    for k in w: v = torch.tanh(F.conv1d(v, k, padding=1))
    return v
t = dec(z); print("\ntwo tiles of a 64-long latent, zero padding at each tile edge, hard join in the middle of the overlap")
print("overlap   largest error at the join"); errs = []
for ov in (0, 2, 4, 6, 8, 12):
    m = 32; a = dec(z[..., :m + ov // 2 + ov % 2 + ov // 2]) if False else dec(z[..., :m + ov]); b = dec(z[..., m - ov:]); o = torch.cat([a[..., :m], b[..., ov:]], -1); e = (o - t).abs().max().item(); errs.append(e); print(f"{ov:<9d} {e:.6f}")
assert errs[0] > 1e-3 and errs[-1] < 1e-9
