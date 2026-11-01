# CU-302 lab: heads, grouped keys and rotary positions, with the same shapes and formulas as ComfyUI's code. CPU, no model.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
# 1. Heads: split the width, attend separately, join. The split itself loses nothing.
B, N, D, H = 1, 6, 64, 8; x = torch.randn(B, N, D); hd = D // H
split = x.view(B, N, H, hd).transpose(1, 2); back = split.transpose(1, 2).reshape(B, N, D)
print(f"width {D}, {H} heads -> {split.shape[1]} heads of width {split.shape[3]}, split then join is identical: {torch.equal(x, back)}"); assert torch.equal(x, back)
# 2. The attention sum, with fewer key/value heads repeated to match, as comfy/ldm/lumina/model.py does with n_rep.
def attend(xq, xk, xv):                                   # all (B, heads, N, head_dim)
    s = (xq @ xk.transpose(-1, -2)) / math.sqrt(xk.shape[-1]); return s.softmax(-1) @ xv
def proj_size(dim, heads, kv): return dim * (heads + kv + kv) * (dim // heads)    # one Linear(dim, (heads + 2 kv) head_dim) with no bias
def gqa(x, heads, kv, W):
    b, n, d = x.shape; hd = d // heads; xq, xk, xv = (x @ W).split([heads * hd, kv * hd, kv * hd], -1)
    q = xq.view(b, n, heads, hd).transpose(1, 2); k = xk.view(b, n, kv, hd).transpose(1, 2).repeat_interleave(heads // kv, 1); v = xv.view(b, n, kv, hd).transpose(1, 2).repeat_interleave(heads // kv, 1)
    return attend(q, k, v), k
W = torch.randn(D, (H + 2 * 4) * hd); out, k = gqa(x, H, 4, W)
print(f"8 query heads, 4 key/value heads: output {tuple(out.shape)}, heads 0 and 1 share keys: {torch.equal(k[:, 0], k[:, 1])}, heads 1 and 2 share keys: {torch.equal(k[:, 1], k[:, 2])}")
assert torch.equal(k[:, 0], k[:, 1]) and not torch.equal(k[:, 1], k[:, 2])
print("\nprojection weights for one block, Lumina 2 sizes (dim 2304, head width 96, from model_detection.py)")
print("key/value heads   weights        relative")
base = proj_size(2304, 24, 24)
for kv in (24, 12, 8, 4):
    n = proj_size(2304, 24, kv); print(f"{kv:<17d} {n:<14,d} {n / base:.3f}")
assert proj_size(2304, 24, 8) == 2304 * 40 * 96
print("the attention matrix is still one per query head: 24 of them, whatever kv is")
# 3. RoPE: the same formula as rope() in comfy/ldm/flux/math.py, on one axis.
def angles(pos, dim, theta=10000.0): return pos * (1.0 / theta ** torch.linspace(0, (dim - 2) / dim, dim // 2, dtype=torch.float64))
def rotate(x, pos, theta=10000.0):
    a = angles(torch.tensor(float(pos), dtype=torch.float64), x.shape[-1], theta); c, s = a.cos(), a.sin(); p, r = x[..., 0::2], x[..., 1::2]
    out = torch.empty_like(x); out[..., 0::2] = c * p - s * r; out[..., 1::2] = s * p + c * r; return out
dim = 96; q = torch.randn(dim, dtype=torch.float64); k = torch.randn(dim, dtype=torch.float64)
print(f"\nlength before {q.norm():.6f}, after rotating to position 500 {rotate(q, 500).norm():.6f}"); assert abs(q.norm() - rotate(q, 500).norm()) < 1e-9
print("query at  key at  gap  score with RoPE  score with added position")
pe = lambda p: torch.cat([angles(torch.tensor(float(p), dtype=torch.float64), dim).sin(), angles(torch.tensor(float(p), dtype=torch.float64), dim).cos()])
scores = {}
for a, b in ((0, 3), (10, 13), (500, 503), (0, 40)):
    s = (rotate(q, a) @ rotate(k, b)).item(); s2 = ((q + pe(a)) @ (k + pe(b))).item(); scores[(a, b)] = (s, s2); print(f"{a:<9d} {b:<7d} {b - a:<4d} {s:<16.6f} {s2:.6f}")
assert abs(scores[(0, 3)][0] - scores[(500, 503)][0]) < 1e-9 and abs(scores[(0, 3)][0] - scores[(0, 40)][0]) > 1e-3
print("same gap, same RoPE score:", abs(scores[(0, 3)][0] - scores[(500, 503)][0]) < 1e-9, " same gap, same added-position score:", abs(scores[(0, 3)][1] - scores[(500, 503)][1]) < 1e-9)
# 4. Several axes: split the head width and give each axis its own part. Image ids here are (time, row, column), FLUX.2 uses four axes of 32.
axes = [32, 32, 32]; assert sum(axes) == dim
def rotate_nd(x, ids):
    parts = x.split(axes, -1); return torch.cat([rotate(p, i) for p, i in zip(parts, ids)], -1)
a = rotate_nd(q, (0, 5, 9)) @ rotate_nd(k, (0, 7, 2)); b = rotate_nd(q, (3, 25, 49)) @ rotate_nd(k, (3, 27, 42))
print(f"\n3 axes: score for offset (0, +2, -7) at two places in the grid: {a.item():.6f} {b.item():.6f}"); assert abs(a - b) < 1e-9
