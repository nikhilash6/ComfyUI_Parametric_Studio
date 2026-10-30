# CU-219 lab: the Sobel operator by hand, why Canny blurs first, and how a depth map is turned into a grey image.
# Run: python lab.py  (CPU only, a second or two). Prints the same numbers every time.
import math, torch
import torch.nn.functional as F
torch.manual_seed(0); torch.set_num_threads(1)
g = torch.Generator().manual_seed(0)
KX = torch.tensor([[-1., 0., 1.], [-2., 0., 2.], [-1., 0., 1.]]); KY = KX.T          # the 3x3 Sobel stencils (kornia get_sobel_kernel_3x3, and its transpose for y)
def corr(img, k, pad=1): return F.conv2d(img[None, None], k[None, None], padding=pad)[0, 0]      # F.conv2d is a cross-correlation: the kernel is not flipped
def gauss5(sigma=1.0):
    x = torch.arange(-2., 3.); k = torch.exp(-x ** 2 / (2 * sigma ** 2)); k = k / k.sum(); return torch.outer(k, k)

# 1. The stencil, and what it answers. Per unit slope it answers 8; a unit step gives 4; the sign follows correlation, not convolution.
print("Sobel x stencil = outer([1, 2, 1], [-1, 0, 1]):", torch.equal(KX, torch.outer(torch.tensor([1., 2., 1.]), torch.tensor([-1., 0., 1.]))))
ramp = (0.1 * torch.arange(16.)).repeat(16, 1); step = torch.zeros(16, 16); step[:, 8:] = 1.0
print(f"ramp of slope 0.1 per pixel: Gx = {corr(ramp, KX)[8, 8]:.3f} (8 x slope = {8 * 0.1:.3f});  unit step: Gx = {corr(step, KX)[8, 7]:.1f} and {corr(step, KX)[8, 8]:.1f} at the two pixels beside the edge")
print(f"rising edge with the stencil as it is: {corr(step, KX)[8, 7]:+.1f}, with the stencil flipped (a true convolution): {corr(step, KX.flip(0).flip(1))[8, 7]:+.1f}")
blur_step = corr(step, gauss5(), pad=2); mag = torch.sqrt(corr(blur_step, KX) ** 2 + corr(blur_step, KY) ** 2)
print(f"unit step after the 5x5 Gaussian blur with sigma 1 (the Canny node's default): Sobel magnitude {mag[8, 7:9].max():.2f}, against 4.00 without the blur")
assert abs(mag[8, 7:9].max() - 2.59) < 0.01

# 2. Noise. White noise of standard deviation 1: the stencil's noise has std sqrt(12); the plain difference [-1, 0, 1] has sqrt(2). Signal: 4h against h for a step of height h.
n = torch.randn(512, 512, generator=g); sob = corr(n, KX)[2:-2, 2:-2].std().item(); dif = (n[:, 2:] - n[:, :-2]).std().item()
print(f"\nnoise std through Sobel {sob:.3f} (sqrt(12) = {math.sqrt(12):.3f}), through the plain difference {dif:.3f} (sqrt(2) = {math.sqrt(2):.3f})")
print(f"signal to noise for a step of height h: Sobel {4 / sob:.3f} h, plain difference {1 / dif:.3f} h, ratio {(4 / sob) / (1 / dif):.2f}")

# 3. Edges of a disc with noise. Image 64x64, disc of radius 20, value 1.0 inside and 0.2 outside. Pixels with Sobel magnitude above 0.8 (the Canny node's
#    high threshold) are called edge; true edge pixels are within 1.5 pixels of the circle, false ones are more than 3 pixels from it. No non-maximum suppression or hysteresis.
yy, xx = torch.meshgrid(torch.arange(64.), torch.arange(64.), indexing="ij"); r = torch.sqrt((yy - 31.5) ** 2 + (xx - 31.5) ** 2)
clean = torch.where(r < 20, torch.tensor(1.0), torch.tensor(0.2)); ring = (r - 20).abs() < 1.5; far = (r - 20).abs() > 3
print("\nnoise std   blur first   true edge pixels found   false edge pixels (of the pixels far from the circle)")
rows = {}
for sd in (0.0, 0.05, 0.1, 0.2):
    img = clean + sd * torch.randn(64, 64, generator=g)
    for blur in (False, True):
        src = corr(img, gauss5(), pad=2) if blur else img
        m = torch.sqrt(corr(src, KX) ** 2 + corr(src, KY) ** 2); m[:4] = 0; m[-4:] = 0; m[:, :4] = 0; m[:, -4:] = 0; hit = m > 0.8
        found = (hit & ring).sum().item() / ring.sum().item(); fp = (hit & far).sum().item() / (far & (m >= 0)).sum().item(); rows[(sd, blur)] = (found, fp)
        print(f"{sd:<11} {'yes' if blur else 'no':<12} {found:<24.3f} {fp:.4f}")
assert rows[(0.2, False)][1] > 0.3 and rows[(0.2, True)][1] < 0.01 and rows[(0.2, True)][0] > 0.9

# 4. Depth to a grey image, as comfy/ldm/depth_anything_3/preprocess.py does it (near = white). min_max uses the extremes, v2_style the 1st and 99th percentiles.
def min_max(d): lo, hi = d.min(), d.max(); return 1 - ((d - lo) / (hi - lo).clamp(min=1e-6)).clamp(0, 1)
def v2_style(d): lo, hi = torch.quantile(d.flatten(), 0.01), torch.quantile(d.flatten(), 0.99); return 1 - ((d - lo) / (hi - lo).clamp(min=1e-6)).clamp(0, 1)
print("\nscene depth ramps from 2 m to 10 m; a share of the pixels is far away (500 m, like sky). Grey value, 1 = near, at 2 m, 6 m and 10 m")
print("far pixels   min_max               v2_style")
for share in (0.0, 0.005, 0.02):
    d = 2.0 + 8.0 * torch.linspace(0, 1, 100)[:, None].repeat(1, 100); far_px = torch.rand(100, 100, generator=g) < share; far_px[:, 0] = False; d = torch.where(far_px, torch.tensor(500.0), d)
    pick = lambda f: " ".join(f"{f(d)[i, 0].item():.3f}" for i in (0, 50, 99))
    print(f"{share:<12.3f} {pick(min_max):<21s} {pick(v2_style)}")
