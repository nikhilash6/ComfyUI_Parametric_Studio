# CU-271 lab: what the Canny thresholds are measured in, and how a bad map looks in numbers.
# The pipeline follows kornia.filters.canny 0.9.0 as the Canny node calls it: grey, 5x5 Gaussian sigma 1, unscaled Sobel, thinning along the gradient, two thresholds, hysteresis.
import math, torch
import torch.nn.functional as F
torch.manual_seed(0); torch.set_num_threads(1)
g1 = torch.exp(-(torch.arange(5.) - 2) ** 2 / 2); g1 = g1 / g1.sum(); G = (g1[:, None] @ g1[None, :])[None, None]
KX = torch.tensor([[-1., 0, 1], [-2, 0, 2], [-1, 0, 1]])[None, None]; KY = KX.transpose(2, 3)
OFF = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]      # direction k = gradient angle / 45 degrees
def canny(img, low, high):
    assert low <= high, "Invalid input thresholds. low_threshold should be smaller than or equal to the high_threshold."
    x = F.conv2d(F.pad(img[None, None], (2, 2, 2, 2), mode="reflect"), G)
    p = F.pad(x, (1, 1, 1, 1), mode="replicate"); gx, gy = F.conv2d(p, KX)[0, 0], F.conv2d(p, KY)[0, 0]
    mag = torch.sqrt(gx ** 2 + gy ** 2 + 1e-6); H, W = mag.shape
    pad = F.pad(mag, (1, 1, 1, 1)); k = ((torch.atan2(gy, gx) * 4 / math.pi).round() % 8).long(); keep = torch.zeros_like(mag, dtype=torch.bool)
    for d, (dy, dx) in enumerate(OFF):
        m = k == d; a = pad[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]; dy2, dx2 = OFF[(d + 4) % 8]; b = pad[1 + dy2:1 + dy2 + H, 1 + dx2:1 + dx2 + W]
        if d == 0 or d == 2: ok = (mag >= a) & (mag > b)        # of two equal pixels across a straight step, keep the left or upper one
        elif d == 4 or d == 6: ok = (mag > a) & (mag >= b)
        else: ok = (mag > a) & (mag > b)
        keep = keep | (m & ok)
    thin = mag * keep; hi = thin > high; lo = thin > low; e = hi.clone()
    nb = torch.ones(1, 1, 3, 3); 
    while True:
        n = (F.conv2d(e.float()[None, None], nb, padding=1)[0, 0] > 0) & lo
        if bool((n == e).all()): return mag, e.float()
        e = n
def step(h, base=0.2):
    x = torch.full((64, 64), base); x[:, 32:] = base + h; return x

print("a straight edge of contrast h, on a scale where black is 0 and white is 1")
print("h      largest magnitude (raw, 2.59 x h)   found at 0.4/0.8   found at 0.1/0.2   found at 0.99/0.99")
found = {}
for h in (0.1, 0.3, 0.31, 0.38, 0.39, 0.5):
    m, _ = canny(step(h), 0.4, 0.8); r = [canny(step(h), a, b)[1].sum().item() > 0 for a, b in ((0.4, 0.8), (0.1, 0.2), (0.99, 0.99))]; found[h] = r
    print(f"{h:<6} {m.max().item():<35.3f} {str(r[0]):<18} {str(r[1]):<18} {r[2]}")
assert found[0.3][0] is False and found[0.31][0] is True and found[0.38][2] is False and found[0.39][2] is True
print("smallest contrast that can start an edge = high_threshold / 2.59:  0.8 -> {:.3f}   0.2 -> {:.3f}   0.99 (the slider's top) -> {:.3f}".format(0.8 / 2.588, 0.2 / 2.588, 0.99 / 2.588))

# A small scene: a strong disc, a faint square, and noise. The question for each setting is what the map keeps.
yy, xx = torch.meshgrid(torch.arange(128.), torch.arange(128.), indexing="ij")
disc = ((xx - 44) ** 2 + (yy - 64) ** 2).sqrt() < 28; square = (abs(xx - 100) < 16) & (abs(yy - 64) < 16)
clean = torch.full((128, 128), 0.25); clean[disc] = 0.85; clean[square] = 0.40
gen = torch.Generator().manual_seed(1); noisy = clean + 0.05 * torch.randn(128, 128, generator=gen)
def near(mask, r):
    k = 2 * r + 1; dil = F.max_pool2d(mask.float()[None, None], k, 1, r)[0, 0] > 0; ero = F.max_pool2d((~mask).float()[None, None], k, 1, r)[0, 0] > 0
    return dil & ero
bd = near(disc, 2); bs = near(square, 2); far = ~(near(disc, 4) | near(square, 4))
print("\nnoise 0.05, 128 x 128: what each threshold pair keeps")
print("low   high   pixels marked   disc outline   faint square   stray pixels")
res = {}
for low, high in ((0.05, 0.1), (0.1, 0.2), (0.2, 0.4), (0.4, 0.8), (0.8, 0.9), (0.95, 0.99)):
    e = canny(noisy, low, high)[1] > 0; ring = (F.max_pool2d(e.float()[None, None], 5, 1, 2)[0, 0] > 0)
    dcov = (ring & bd).sum().item() / bd.sum().item(); scov = (ring & bs).sum().item() / bs.sum().item(); stray = (e & far).sum().item() / far.sum().item()
    res[(low, high)] = (dcov, scov, stray)
    print(f"{low:<5} {high:<6} {e.float().mean().item() * 100:<15.1f} {dcov:<14.2f} {scov:<14.2f} {stray:.4f}")
assert res[(0.05, 0.1)][2] > 0.05 and res[(0.4, 0.8)][1] < 0.5 and res[(0.4, 0.8)][0] > 0.9

# The hint is fitted to the latent's shape by common_upscale with crop "center": the part outside the new shape is thrown away.
def kept(w, h, W, H):
    old, new = w / h, W / H; x = y = 0
    if old > new: x = round((w - w * (new / old)) / 2)
    elif old < new: y = round((h - h * (old / new)) / 2)
    return w - 2 * x, h - 2 * y
print("\nhint size against the latent's shape (common_upscale, crop center)")
print("hint          render        part of the hint used   share kept")
for w, h, W, H in ((1024, 1024, 512, 512), (1024, 768, 512, 512), (768, 1024, 512, 768), (1920, 1080, 512, 512)):
    a, b = kept(w, h, W, H); print(f"{w} x {h:<6} {W} x {H:<6} {a} x {b:<16} {a * b / (w * h):.2f}")
assert kept(1024, 768, 512, 512) == (768, 768)
