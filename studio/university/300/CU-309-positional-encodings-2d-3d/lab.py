# CU-309 lab: three ways to tell a token where it is, using the formulas in ComfyUI's code. CPU, no model.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
# 1. Why anything is needed: attention alone does not see order.
def attend(x, W): return ((x @ W[0]) @ (x @ W[1]).transpose(-1, -2) / math.sqrt(x.shape[-1])).softmax(-1) @ (x @ W[2])
x = torch.randn(1, 16, 32); W = [torch.randn(32, 32) for _ in range(3)]; perm = torch.randperm(16)
gap = (attend(x, W)[:, perm] - attend(x[:, perm], W)).abs().max().item(); print(f"shuffle tokens then attend, against attend then shuffle: max difference {gap:.1e}"); assert gap < 1e-4
# 2. Sine and cosine, added to the tokens. Same as get_1d_sincos_pos_embed_from_grid in mmdit.py.
def sincos1d(dim, pos):
    om = 1.0 / 10000 ** (torch.arange(dim // 2, dtype=torch.float64) / (dim / 2)); a = torch.outer(pos.double().reshape(-1), om); return torch.cat([a.sin(), a.cos()], 1)
# get_2d_sincos_pos_embed_from_grid: half the width for each axis, then join.
def sincos2d(dim, h, w):
    ys, xs = torch.meshgrid(torch.arange(h), torch.arange(w), indexing="ij"); return torch.cat([sincos1d(dim // 2, ys), sincos1d(dim // 2, xs)], 1)
e = sincos2d(16, 8, 8); print(f"\n2D table for an 8x8 grid, width 16: {tuple(e.shape)}, values in [{e.min():.3f}, {e.max():.3f}]")
print("first 4 values for row 0, column 0:", [round(v, 3) for v in e[0][:4].tolist()], " every position different:", len({tuple(r) for r in e.round(decimals=6).tolist()}) == 64); assert len({tuple(r) for r in e.round(decimals=6).tolist()}) == 64
# Each frequency has its own wavelength. Short ones tell near positions apart, long ones far positions.
print("frequency  wavelength in positions")
for i, o in enumerate((1.0 / 10000 ** (torch.arange(4, dtype=torch.float64) / 4)).tolist()): print(f"{i:<10d} {2 * math.pi / o:.1f}")
# 3. Neighbours look alike: the dot product falls off with distance, near positions first.
e = sincos2d(64, 32, 32); c = e[0]; row = [(c @ e[k]).item() / (c @ c).item() for k in (0, 1, 2, 4, 8, 16, 31)]
print("\nsimilarity of column 0 to column k, same row:", [(k, round(v, 3)) for k, v in zip((0, 1, 2, 4, 8, 16, 31), row)]); assert row[0] > row[1] > row[2] > row[3]
# 4. A table has a fixed size. A model trained at one size must reshape or rescale for another. PixArt's scales the grid (pe_interpolation, base_size).
g16 = sincos1d(32, torch.arange(16).float()); g32 = sincos1d(32, torch.arange(32).float() / 2)
print(f"\nposition grid scaled by 1/2 for a double-size image: token 2 of 32 equals token 1 of 16: {torch.allclose(g32[2], g16[1])}"); assert torch.allclose(g32[2], g16[1])
# 5. Ids instead of a table: RoPE takes (t, y, x) for each token and has no size limit, as EmbedND does in comfy/ldm/flux/layers.py.
def rot(x, pos):
    a = pos * (1.0 / 10000.0 ** torch.linspace(0, (x.shape[-1] - 2) / x.shape[-1], x.shape[-1] // 2, dtype=torch.float64)); p, r = x[..., ::2], x[..., 1::2]; o = torch.empty_like(x); o[..., ::2] = a.cos() * p - a.sin() * r; o[..., 1::2] = a.sin() * p + a.cos() * r; return o
def rot3(x, ids, axes):
    return torch.cat([rot(p, float(i)) for p, i in zip(x.split(axes, -1), ids)], -1)
axes = [16, 56, 56]; q, k = torch.randn(128, dtype=torch.float64), torch.randn(128, dtype=torch.float64)
a = rot3(q, (0, 10, 10), axes) @ rot3(k, (0, 12, 13), axes); b = rot3(q, (7, 500, 900), axes) @ rot3(k, (7, 502, 903), axes)
print(f"\nRoPE on 3 axes, widths {axes}: offset (0, 2, 3) near the corner {a.item():.6f}, far beyond any training grid {b.item():.6f}"); assert abs(a - b) < 1e-9
# Wan splits the head width by the same idea, from the head width alone. WanModel: axes_dim = [d - 4 (d // 6), 2 (d // 6), 2 (d // 6)].
for d in (128, 96): print(f"head width {d}: axes for time, height, width = {[d - 4 * (d // 6), 2 * (d // 6), 2 * (d // 6)]}, sum {d}"); assert d - 4 * (d // 6) + 4 * (d // 6) == d
# A token count for video: (frames, height, width) divided by the patch.
f, h, w, pt, ps = 21, 90, 160, 1, 2; n = (f // pt) * (h // ps) * (w // ps); print(f"latent {f}x{h}x{w}, patch {pt}x{ps}x{ps}: {n:,d} tokens")
