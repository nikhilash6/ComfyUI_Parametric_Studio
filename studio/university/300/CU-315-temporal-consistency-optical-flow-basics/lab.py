# CU-315 lab: what optical flow measures, why a plain frame difference is not flow, and how to tell motion from flicker. CPU, seeded, under a second.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1); g = torch.Generator().manual_seed(0)
import torch.nn.functional as F
S = 64
yy, xx = torch.meshgrid(torch.arange(S, dtype=torch.float64), torch.arange(S, dtype=torch.float64), indexing="ij")
base = F.avg_pool2d(torch.randn(1, 1, S + 8, S + 8, generator=g).double(), 9, stride=1)[0, 0]; base = (base - base.min()) / (base.max() - base.min())
def shift(img, dx, dy):
    """move the picture by a whole or a fractional number of pixels, with grid_sample (bilinear, wrapping at the border by reflection)"""
    gx = (xx - dx) / (S - 1) * 2 - 1; gy = (yy - dy) / (S - 1) * 2 - 1; grid = torch.stack([gx, gy], -1)[None]
    return F.grid_sample(img[None, None], grid, mode="bilinear", padding_mode="reflection", align_corners=True)[0, 0]
a = base; b = shift(a, 3.0, -1.5)
# 1. The draft of this lesson called b - a "flow". It is not: it has one number per pixel, a flow has two, and it says nothing about where things went.
d = b - a; print(f"frame difference: 1 number per pixel, mean {d.mean():+.4f}, largest {d.abs().max():.3f}. True motion (+3.0, -1.5) cannot be read from it")
# 2. Brightness constancy: I(x + u, y + v, t + 1) = I(x, y, t). Search for the (u, v) that makes the warped frame match.
best = min(((shift(a, u / 2, v / 2) - b).pow(2).mean().item(), u / 2, v / 2) for u in range(-12, 13) for v in range(-12, 13))
print(f"search over whole and half pixels: best motion ({best[1]:+.1f}, {best[2]:+.1f}), mean squared error left {best[0]:.6f}")
assert best[1] == 3.0 and best[2] == -1.5
# 3. Lucas-Kanade: linearise brightness constancy, Ix u + Iy v + It = 0, and solve least squares over a window. It works for small motion only.
def lk(a, b):
    Ix = (a[1:-1, 2:] - a[1:-1, :-2]) / 2; Iy = (a[2:, 1:-1] - a[:-2, 1:-1]) / 2; It = (b - a)[1:-1, 1:-1]
    A = torch.stack([Ix.flatten(), Iy.flatten()], 1); return torch.linalg.lstsq(A, -It.flatten()[:, None]).solution.flatten().tolist()
print("\ntrue motion   Lucas-Kanade over the whole frame")
for dx, dy in ((0.3, -0.2), (1.0, 0.5), (3.0, -1.5), (8.0, 4.0)):
    u, v = lk(a, shift(a, dx, dy)); print(f"({dx:+.1f}, {dy:+.1f})  ->  ({u:+.2f}, {v:+.2f})")
u, v = lk(a, shift(a, 0.3, -0.2)); assert abs(u - 0.3) < 0.05 and abs(v + 0.2) < 0.05
# 4. Motion against flicker. Residual = what is left after undoing the best motion. Motion leaves little. Flicker leaves a lot.
def best_residual(a, b, r=8):
    return min((shift(a, u, v) - b).abs().mean().item() for u in range(-r, r + 1) for v in range(-r, r + 1))
cases = {"camera pans 3 pixels": shift(a, 3, 0), "brightness jumps 10%": a * 1.1, "fine noise re-rolled": a + 0.05 * torch.randn(S, S, generator=g).double(), "still frame": a.clone()}
print("\nchange between two frames   mean |difference|   left after the best whole-pixel shift")
res = {}
for k, b2 in cases.items():
    res[k] = best_residual(a, b2); print(f"{k:27s} {(b2 - a).abs().mean().item():<19.4f} {res[k]:.4f}")
assert res["camera pans 3 pixels"] < res["brightness jumps 10%"] and res["camera pans 3 pixels"] < res["fine noise re-rolled"]
# 5. Why causal: VideoConv3d in ComfyUI pads kernel_size - 1 frames before the clip and none after, so no output depends on a later frame.
x = torch.zeros(1, 1, 9, 1, 1); x[0, 0, 4] = 1.0; k = torch.ones(1, 1, 3, 1, 1) / 3
causal = F.conv3d(F.pad(x, (0, 0, 0, 0, 2, 0)), k)[0, 0, :, 0, 0]; centred = F.conv3d(F.pad(x, (0, 0, 0, 0, 1, 1)), k)[0, 0, :, 0, 0]
print("\nan impulse at frame 4 through a 3-frame kernel:")
print("causal  output non-zero at frames", causal.nonzero().flatten().tolist()); print("centred output non-zero at frames", centred.nonzero().flatten().tolist())
assert causal.nonzero().min().item() == 4 and centred.nonzero().min().item() == 3
