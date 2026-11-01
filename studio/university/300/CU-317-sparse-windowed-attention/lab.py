# CU-317 lab: full attention against windows, with the partition rule of comfy/ldm/sam3/sam.py. Counts and a small run. CPU, no model.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
def window_partition(x, ws):   # x: (B, H, W, C), must already be a multiple of ws here
    B, H, W, C = x.shape; return x.view(B, H // ws, ws, W // ws, ws, C).permute(0, 1, 3, 2, 4, 5).reshape(-1, ws, ws, C)
def window_unpartition(w, ws, H, W):
    B = w.shape[0] // (H * W // ws // ws); return w.view(B, H // ws, W // ws, ws, ws, -1).permute(0, 1, 3, 2, 4, 5).reshape(B, H, W, -1)
x = torch.randn(1, 16, 16, 8); w = window_partition(x, 4); print(f"grid {tuple(x.shape)} -> {w.shape[0]} windows of {w.shape[1]}x{w.shape[2]}, back again identical: {torch.equal(window_unpartition(w, 4, 16, 16), x)}"); assert torch.equal(window_unpartition(w, 4, 16, 16), x)
print("\ngrid side  tokens    full pairs        window 8 pairs   share of full")
for s in (32, 64, 128, 256):
    n = s * s; full = n * n; win = (s // 8) ** 2 * 64 ** 2; print(f"{s:<10d} {n:<9,d} {full:<17,d} {win:<16,d} {win / full:.4f}"); assert win == n * 64
print("window pairs grow with the tokens (n x 64). full pairs grow with the square of the tokens.")
# Reach: what can token (0, 0) be influenced by after L layers, with a fixed grid against shifted windows?
def reach(side, ws, layers, shift):
    seen = torch.zeros(side, side, dtype=torch.bool); seen[0, 0] = True
    for L in range(layers):
        off = (ws // 2) if (shift and L % 2) else 0; new = seen.clone(); key = lambda i: (i + off) // ws
        for key_y in range(0, side // ws + 2):
            for key_x in range(0, side // ws + 2):
                ys = [i for i in range(side) if key(i) == key_y]; xs = [i for i in range(side) if key(i) == key_x]
                if ys and xs and seen[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1].any(): new[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1] = True
        seen = new
    return int(seen.sum())
print("\nlayers  tokens reachable, fixed windows  tokens reachable, shifted every second layer   (grid 32x32, window 8, 1024 tokens)")
R = {}
for L in (1, 2, 4, 8, 12): R[L] = (reach(32, 8, L, False), reach(32, 8, L, True)); print(f"{L:<7d} {R[L][0]:<32d} {R[L][1]}")
assert R[12][0] == 64 and R[12][1] > 64
# Masking is not windowing: a mask gives the same answer but still spends a full matrix.
n = 16; q, k, v = [torch.randn(1, n, 8) for _ in range(3)]
def attend(q, k, v, m=None):
    s = q @ k.transpose(-1, -2) / math.sqrt(8)
    if m is not None: s = s.masked_fill(~m, float("-inf"))
    return s.softmax(-1) @ v
gr = torch.arange(n) // 4; mask = gr[:, None] == gr[None]; masked = attend(q, k, v, mask); parts = torch.cat([attend(q[:, i:i + 4], k[:, i:i + 4], v[:, i:i + 4]) for i in range(0, n, 4)], 1)
print(f"\nmasked full attention against four separate windows: max difference {(masked - parts).abs().max():.1e}. pairs computed: {n * n} against {4 * 16}"); assert (masked - parts).abs().max() < 1e-5
# Sparse: only occupied cells are tokens, as Trellis 2 voxels. Attention is over the occupied list, whatever the grid.
for side, frac in ((64, 0.02), (128, 0.01)):
    occ = int(side ** 3 * frac); print(f"3D grid {side}^3 = {side ** 3:,d} cells, {frac:.0%} occupied: {occ:,d} tokens, {occ * occ:,d} pairs against {side ** 6:,d} if every cell were a token")
