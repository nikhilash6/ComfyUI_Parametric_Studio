# CU-229 lab: the sRGB curve, what blending and shrinking do on stored values, and the 8-bit step at the end of a ComfyUI graph.
# Run: python lab.py  (CPU only, a second or two). Prints the same numbers every time.
import math, torch
import torch.nn.functional as F
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
def to_linear(c):
    """sRGB decode, as in the W3C CSS Color 4 sample code and comfy_extras/nodes_images.py srgb_to_linear: linear toe up to 0.04045, then a 2.4 power."""
    c = torch.as_tensor(c, dtype=D); return torch.where(c <= 0.04045, c / 12.92, ((c.clamp(min=0) + 0.055) / 1.055) ** 2.4)
def to_srgb(v):
    """sRGB encode: 12.92 * v up to 0.0031308, then 1.055 * v ** (1 / 2.4) - 0.055"""
    v = torch.as_tensor(v, dtype=D); return torch.where(v <= 0.0031308, v * 12.92, 1.055 * v.clamp(min=0) ** (1 / 2.4) - 0.055)

# 1. The curve. Two pieces that meet, a round trip, and how far it is from a plain power law.
print(f"decode at 0.04045: linear piece {0.04045 / 12.92:.7f}, power piece {((0.04045 + 0.055) / 1.055) ** 2.4:.7f};  encode at 0.0031308: linear piece {0.0031308 * 12.92:.6f}, power piece {1.055 * 0.0031308 ** (1 / 2.4) - 0.055:.6f}")
codes = torch.arange(256, dtype=D) / 255
print(f"round trip decode then encode over the 256 codes: largest error {(to_srgb(to_linear(codes)) - codes).abs().max():.1e}")
print("code   sRGB linear   plain power 2.2   ratio")
for k in (1, 5, 20, 50, 128, 255):
    a = to_linear(k / 255).item(); b = (k / 255) ** 2.2; print(f"{k:<6d} {a:<13.6f} {b:<17.6f} {a / b:.2f}")

# 2. Blending on stored values and on light. Luminance weights are the middle row of the sRGB to XYZ matrix in the CSS Color 4 text.
W = torch.tensor([87098 / 409605, 175762 / 245763, 12673 / 175545], dtype=D)
print(f"\nluminance weights R, G, B: {W[0]:.4f} {W[1]:.4f} {W[2]:.4f}")
bw = to_srgb((to_linear(0.0) + to_linear(1.0)) / 2)
print(f"black and white, half and half: on stored values {0.5:.4f}, in linear light then encoded {bw:.4f}   (8-bit code {0.5 * 255:.1f} against {bw * 255:.1f})")
red, green = torch.tensor([1., 0., 0.], dtype=D), torch.tensor([0., 1., 0.], dtype=D)
stored = (red + green) / 2; light = to_srgb((to_linear(red) + to_linear(green)) / 2)
y_stored = (to_linear(stored) * W).sum().item(); y_light = (to_linear(light) * W).sum().item(); y_true = ((to_linear(red) + to_linear(green)) / 2 * W).sum().item()
print(f"red and green, half and half: stored-value blend {stored.tolist()}, light blend {[round(v, 4) for v in light.tolist()]}")
print(f"  luminance of the light that reaches the eye: stored-value blend {y_stored:.4f}, light blend {y_light:.4f}, the average of the two lights {y_true:.4f}")
checker = (torch.arange(8)[:, None] + torch.arange(8)[None]) % 2; ck = checker.float()[None, None]
area = F.interpolate(ck, size=(4, 4), mode="area")[0, 0, 0, 0].item(); lin = to_srgb(to_linear(ck).mean()).item()
print(f"2x area downscale of a black and white checkerboard (the ImageScale 'area' method): pixel {area:.4f}; averaging the same four pixels in linear light: {lin:.4f}")
assert abs(area - 0.5) < 1e-6 and abs(bw - 0.7354) < 1e-3 and abs(y_stored / y_true - 0.4287) < 1e-3

# 3. How 8-bit codes cover light.
lin_codes = to_linear(torch.arange(256, dtype=D) / 255)
print(f"\ncodes whose light is below 1% of white: sRGB {int((lin_codes < 0.01).sum())}, if the codes were linear in light {int((torch.arange(256) / 255 < 0.01).sum())}")
print(f"codes whose light is at least half of white: sRGB {int((lin_codes >= 0.5).sum())}, if the codes were linear in light {int((torch.arange(256) / 255 >= 0.5).sum())}")

# 4. The 8-bit step. LoadImage divides codes by 255 in float32. SaveImage computes np.clip(255. * image, 0, 255).astype(np.uint8), which truncates.
k = torch.arange(256); v = k.to(torch.float32) / 255.0; saved = (255.0 * v).clamp(0, 255).to(torch.uint8)
print(f"\nload then save, all 256 codes: codes that come back changed: {int((saved.long() != k).sum())}")
x = torch.rand(1_000_000, generator=torch.Generator().manual_seed(1)) ; trunc = (255.0 * x).clamp(0, 255).to(torch.uint8).float() - 255.0 * x; rnd = (255.0 * x).round() - 255.0 * x
print(f"random values in [0, 1], error of the saved code in codes: truncation mean {trunc.mean():+.3f}, largest {trunc.abs().max():.3f};  rounding mean {rnd.mean():+.3f}, largest {rnd.abs().max():.3f}")
print(f"a value of 0.999 is saved as code {int((255.0 * torch.tensor(0.999)).clamp(0, 255).to(torch.uint8))} by truncation and {int((255.0 * torch.tensor(0.999)).round())} by rounding")
assert int((saved.long() != k).sum()) == 0 and abs(trunc.mean() + 0.5) < 0.01 and abs(rnd.mean()) < 0.01
