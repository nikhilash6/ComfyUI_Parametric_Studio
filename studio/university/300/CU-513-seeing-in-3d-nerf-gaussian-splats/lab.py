# CU-513 lab: volume rendering as NeRF writes it, the same ray as stacked Gaussians, and the cost of each. The standard emission-absorption sum. CPU, seeded.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
# NeRF's quadrature: C = sum T_i (1 - exp(-sigma_i delta_i)) c_i, T_i = exp(-sum_{j<i} sigma_j delta_j)
def render(sigma, delta, color):
    alpha = 1 - torch.exp(-sigma * delta); T = torch.cat([torch.ones(1), torch.cumprod(1 - alpha, 0)[:-1]]); w = T * alpha
    return (w[:, None] * color).sum(0), T, w
# The first draft's lab: three slices, alpha 0.5 each, red, green, blue.
sig = torch.full((3,), math.log(2.0)); dl = torch.ones(3); col = torch.eye(3)
C, T, w = render(sig, dl, col); print("three slices, alpha 0.5: colour", [round(x, 4) for x in C.tolist()], " transmittance", [round(x, 4) for x in T.tolist()], f" background keeps {1 - w.sum():.3f}")
assert abs(C[0] - 0.5) < 1e-6 and abs(C[2] - 0.125) < 1e-6
# A ball of fog of density 1, radius 1. One ray through the centre has an exact answer for its opacity. Fewer samples get it wrong when delta is wrong.
def fog(n):
    t = torch.linspace(0.0, 4.0, n + 1); mid = (t[:-1] + t[1:]) / 2; d = t[1:] - t[:-1]
    s = 1.0 * ((mid - 2).abs() < 1).float(); alpha = 1 - torch.exp(-s * d); return 1 - torch.prod(1 - alpha).item()
exact = 1 - math.exp(-2); print(f"\nray through fog, exact opacity {exact:.6f}")
print("samples per ray   opacity")
for n in (5, 7, 16, 64, 192): print(f"{n:<17d} {fog(n):.6f}")
# Thin opaque shell: the case where NeRF needs a lot of samples, which is why it uses a coarse and a fine pass.
def shell(n):
    t = torch.linspace(0.0, 4.0, n + 1); mid = (t[:-1] + t[1:]) / 2; d = t[1:] - t[:-1]; s = 200.0 * ((mid - 1).abs() < 0.02).float(); return 1 - torch.exp(-(s * d).sum()).item()
print("\na thin wall, 0.04 thick, density 200, seen through evenly spaced samples:")
for n in (16, 64, 128, 256, 512): print(f"{n:>4d} samples: opacity {shell(n):.4f}")
assert shell(16) < 0.5 and shell(512) > 0.99
# Cost in network calls for one 800 x 800 image at 192 samples per ray, chosen as an example.
print(f"\nNeRF at 800 x 800, 192 samples a ray: {800 * 800 * 192:,d} network queries per image. Splats: no network at render time, one projection per Gaussian")
# The same ray as Gaussians. A Gaussian's opacity along the ray peaks at its centre. Composite front to back, as RenderSplat's comment describes.
op = torch.tensor([0.5, 0.5, 0.5]); order = torch.tensor([2.0, 1.0, 3.0]).argsort(); C2 = torch.zeros(3); left = 1.0
for i in order.tolist(): C2 += left * op[i] * col[i]; left *= 1 - op[i]
print("three Gaussians at depths 2, 1, 3, sorted before blending:", [round(x, 3) for x in C2.tolist()], "(the nearest colour wins most)")
assert C2[1] == 0.5
# Sort order matters for blending: drawing back to front with the wrong rule gives a different picture.
wrong = torch.zeros(3); left = 1.0
for i in range(3): wrong += left * op[i] * col[i]; left *= 1 - op[i]
print("unsorted, in stored order:", [round(x, 3) for x in wrong.tolist()])
