# CU-507 lab: what moving diffusion into a latent grid does to the cost of one layer.
# The costs are counted by PyTorch's own FLOP counter on shape-only ("meta") tensors, so no 512x512 attention is ever computed. A multiply-add counts as 2 FLOPs.
# Run: python lab.py  (CPU only, about 2 s). Prints the same numbers every time.
import math, torch
from torch.utils.flop_counter import FlopCounterMode

def conv_flops(h, w, cin, cout, k=3):                                      # one 3x3 convolution over an h x w grid
    conv = torch.nn.Conv2d(cin, cout, k, padding=k // 2, device="meta"); x = torch.empty(1, cin, h, w, device="meta")
    with FlopCounterMode(display=False) as fc: conv(x)
    return fc.get_total_flops()
def attn_flops(n, dim, heads=8):                                           # softmax(Q K^T) V over n positions, the two big matrix products
    q = torch.empty(1, heads, n, dim // heads, device="meta")
    with FlopCounterMode(display=False) as fc: torch.nn.functional.scaled_dot_product_attention(q, q, q)
    return fc.get_total_flops()

# 1. The same two layers on the pixel grid and on the latent grid of a 512x512 image. Convolution: 64 -> 64 channels. Attention: 320 dimensions, 8 heads.
rows = [("pixels 512x512x3", 512, 3), ("latent 64x64x4 (f = 8)", 64, 4)]; res = []
print("grid                     values    positions   conv GFLOPs   attention GFLOPs   attention matrix entries")
for name, side, ch in rows:
    n = side * side; c, a = conv_flops(side, side, 64, 64), attn_flops(n, 320); res.append((n, c, a))
    assert c == 2 * 9 * 64 * 64 * n and a == 4 * n * n * 320               # the counter agrees with the textbook formulas
    print(f"{name:24s} {n * ch:<9,d} {n:<11,d} {c / 1e9:<13.2f} {a / 1e9:<18.1f} {n * n:,d}")
print(f"{'ratio':24s} {res[0][0] * 3 / (res[1][0] * 4):<9.0f} {res[0][0] // res[1][0]:<11d} {res[0][1] / res[1][1]:<13.0f} {res[0][2] / res[1][2]:<18.0f} {res[0][0] ** 2 // res[1][0] ** 2}")

# 2. The same latent attention layer for other image sizes. ComfyUI's EmptyLatentImage makes a [batch, 4, height // 8, width // 8] tensor.
print("\nimage size    latent shape        positions   attention GFLOPs   relative to 512x512   conv GFLOPs")
base = None
for s in (512, 768, 1024, 2048):
    lat = torch.zeros([1, 4, s // 8, s // 8], device="meta"); n = lat.shape[2] * lat.shape[3]; a = attn_flops(n, 320); c = conv_flops(lat.shape[2], lat.shape[3], 64, 64); base = base or (a, c)
    print(f"{f'{s}x{s}':<13s} {str(list(lat.shape)):<19s} {n:<11,d} {a / 1e9:<18.1f} {a / base[0]:<21.2f} {c / 1e9:.2f}  ({c / base[1]:.2f}x)")
assert attn_flops(128 * 128, 320) == 16 * attn_flops(64 * 64, 320)
