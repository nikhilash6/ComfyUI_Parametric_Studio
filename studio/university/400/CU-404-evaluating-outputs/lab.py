# CU-404 lab: what pixel metrics and a distribution metric measure, on a made-up image and made-up features. CPU, no model.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
N = 64; ys, xs = torch.meshgrid(torch.linspace(0, 1, N), torch.linspace(0, 1, N), indexing="ij")
img = 0.35 + 0.25 * torch.sin(xs * 9) * torch.cos(ys * 7) + 0.25 * ((xs - .5) ** 2 + (ys - .5) ** 2 < .08).float()   # values in 0..1
img = img.clamp(0, 1)
def psnr(a, b): m = ((a - b) ** 2).mean().item(); return float("inf") if m == 0 else 10 * math.log10(1 / m)
def pearson(a, b):
    x, y = a.flatten() - a.mean(), b.flatten() - b.mean(); return (x @ y / (x.norm() * y.norm())).item()
def ssim(a, b, w=8):                                          # Wang et al. 2004, with plain square windows and their constants, in place of a Gaussian window
    c1, c2 = .01 ** 2, .03 ** 2; out = []
    for i in range(0, N - w + 1, w):
        for j in range(0, N - w + 1, w):
            p, q = a[i:i + w, j:j + w], b[i:i + w, j:j + w]; mp, mq = p.mean(), q.mean(); vp, vq = p.var(unbiased=False), q.var(unbiased=False); cv = ((p - mp) * (q - mq)).mean()
            out.append(((2 * mp * mq + c1) * (2 * cv + c2) / ((mp ** 2 + mq ** 2 + c1) * (vp + vq + c2))).item())
    return sum(out) / len(out)
def blur(a):
    k = torch.ones(1, 1, 5, 5) / 25; return torch.nn.functional.conv2d(torch.nn.functional.pad(a[None, None], (2, 2, 2, 2), mode="replicate"), k)[0, 0]
d = {"identical": img.clone(), "brighter by 0.10": (img + .10), "shift 1 pixel": torch.roll(img, 1, 1), "shift 4 pixels": torch.roll(img, 4, 1), "box blur 5x5": blur(img)}
gauss = torch.randn(N, N); gauss = gauss / gauss.pow(2).mean().sqrt(); d["noise, same MSE as +0.10"] = img + gauss * .10
print("change                     PSNR dB   Pearson r   SSIM")
for k, v in d.items(): print(f"{k:<26s} {psnr(img, v):<9.2f} {pearson(img, v):<11.4f} {ssim(img, v):.4f}")
assert abs(psnr(img, d["brighter by 0.10"]) - psnr(img, d["noise, same MSE as +0.10"])) < 1e-3 and pearson(img, d["brighter by 0.10"]) > .9999
assert ssim(img, d["brighter by 0.10"]) > ssim(img, d["noise, same MSE as +0.10"])
# Two seeds of the same prompt share nothing pixel for pixel, so these scores are for pairs that should match, such as a VAE round trip.
other = 0.35 + 0.25 * torch.sin(ys * 8 + 1) * torch.cos(xs * 11) + 0.25 * ((xs - .3) ** 2 + (ys - .7) ** 2 < .08).float(); print(f"\na different picture with the same style of content: PSNR {psnr(img, other.clamp(0, 1)):.2f}, r {pearson(img, other.clamp(0, 1)):.4f}")
# FID: compare two clouds of features by mean and covariance, here 8-dim Gaussians, sampling both from one distribution.
def sqrtm(m):
    e, v = torch.linalg.eigh(m); return (v * e.clamp(min=0).sqrt()) @ v.T
def fid(a, b):
    ma, mb = a.mean(0), b.mean(0); ca, cb = a.T.cov(), b.T.cov(); s = sqrtm(ca); return ((ma - mb) @ (ma - mb) + (ca + cb - 2 * sqrtm(s @ cb @ s)).trace()).item()
L = torch.eye(8) + .3 * torch.randn(8, 8)
print("\nsamples per side  FID, both sides from the same distribution")
last = []
for n in (50, 200, 1000, 5000):
    r = [fid(torch.randn(n, 8, dtype=torch.float64) @ L.double(), torch.randn(n, 8, dtype=torch.float64) @ L.double()) for _ in range(4)]; print(f"{n:<17d} {sum(r) / 4:.4f}"); last.append(sum(r) / 4)
assert last[0] > last[1] > last[2] > last[3]
print("the true distance is 0. a small sample still scores above 0, so only compare FIDs at the same sample size")
