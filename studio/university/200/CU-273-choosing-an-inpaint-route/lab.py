# CU-273 lab: the three inpaint routes on the same small example, with an identity "VAE" so that every number can be followed.
# Routes follow nodes.py (SetLatentNoiseMask, VAEEncodeForInpaint, InpaintModelConditioning). The sampler blend follows KSamplerX0Inpaint in comfy/samplers.py.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
abar = torch.cumprod(1 - torch.linspace(0.00085 ** 0.5, 0.012 ** 0.5, 1000, dtype=torch.float64) ** 2, 0)
SIG = (((1 - abar) / abar) ** 0.5).float(); LOGS = SIG.log()
def sig(t):
    t = torch.clamp(torch.tensor(float(t)), 0, 999); lo, hi, w = t.floor().long(), t.ceil().long(), t.frac(); return ((1 - w) * LOGS[lo] + w * LOGS[hi]).exp().item()
def normal(n): return [sig(t) for t in torch.linspace(999, 0, n).tolist()] + [0.0]
def sched(steps, d): return normal(steps) if d > 0.9999 else normal(int(steps / d))[-(steps + 1):]

def route_noise_mask(pix, mask): return {"latent": pix.clone(), "mask": mask.clone(), "concat_image": None, "concat_mask": None}
def route_vae_inpaint(pix, mask, grow=6):
    m = mask.round(); k = torch.ones(1, 1, grow, grow); pad = math.ceil((grow - 1) / 2)
    big = torch.clamp(torch.nn.functional.conv2d(m[None, None], k, padding=pad), 0, 1)[0, 0, :mask.shape[0], :mask.shape[1]].round()
    x = (pix - 0.5) * (1 - m) + 0.5
    return {"latent": x, "mask": big, "concat_image": None, "concat_mask": None}
def route_model_cond(pix, mask, noise_mask=True):
    m = mask.round(); blank = (pix - 0.5) * (1 - m) + 0.5
    return {"latent": pix.clone(), "mask": mask.clone() if noise_mask else None, "concat_image": blank, "concat_mask": mask.clone()}

# 1. A soft mask edge through each route.
ramp = torch.tensor([0.0, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.0] * 1).repeat(8, 1)
pix = torch.full((8, 8), 0.9); fmt = lambda t: " ".join(f"{v:.1f}" for v in t[4].tolist())
print("one row of a soft mask, as drawn:              ", fmt(ramp))
print("SetLatentNoiseMask keeps it:                   ", fmt(route_noise_mask(pix, ramp)["mask"]))
print("VAEEncodeForInpaint rounds and grows it (6):   ", fmt(route_vae_inpaint(pix, ramp)["mask"]))
print("InpaintModelConditioning, noise_mask:          ", fmt(route_model_cond(pix, ramp)["mask"]))
print("InpaintModelConditioning, its grey-out, rounded:", fmt(ramp.round()))
assert set(route_vae_inpaint(pix, ramp)["mask"].unique().tolist()) <= {0.0, 1.0}

# 2. What the hole starts from, and where it ends up. The stand-in is the exact denoiser for unit-variance Gaussian content: D(x, s) = x / (1 + s^2).
# It has no idea what the original was, so anything of the original in the result came through the starting latent. A grey hole is 0 here, because the content has mean 0.
g = torch.Generator().manual_seed(0); L = torch.randn(400_000, generator=g); n = torch.randn(400_000, generator=g)
def euler(start, s):
    x = start.clone()
    for i in range(len(s) - 1):
        den = x / (1 + s[i] ** 2); x = x + (x - den) / s[i] * (s[i + 1] - s[i])
    return x
corr = lambda a, b: torch.corrcoef(torch.stack([a, b]))[0, 1].item()
print("\nthe masked part, 20 Euler steps, normal scheduler, stand-in denoiser. Correct content here has spread 1.00")
print("denoise   first sigma   original kept in the latent: correlation, spread     greyed first (VAEEncodeForInpaint): correlation, spread")
rows = {}
for d in (1.0, 0.8, 0.5, 0.3):
    s = sched(20, d); a = euler(L + s[0] * n, s); b = euler(0 * L + s[0] * n, s); rows[d] = (corr(a, L), a.std().item(), corr(b, L), b.std().item())
    print(f"{d:<9} {s[0]:<13.3f} {rows[d][0]:<12.3f} {rows[d][1]:<40.3f} {rows[d][2]:<12.3f} {rows[d][3]:.3f}")
assert abs(rows[1.0][2]) < 0.01 and rows[0.3][0] > 0.7 and rows[0.3][3] < 0.75 and rows[1.0][3] > 0.9

# 3. Kept part. mask 0 = keep. It must come back exactly, whichever route made the latent.
def run(latent, mask, d, steps=12):
    noise = torch.randn(32, generator=torch.Generator().manual_seed(1)); s = sched(steps, d); x = latent + s[0] * noise
    for i in range(steps):
        xin = x * mask + (1 - mask) * (latent + s[i] * noise)          # the kept part is the original plus noise at this level
        den = xin / (1 + s[i] ** 2) * mask + latent * (1 - mask)       # and the output is replaced by the original
        x = xin + (xin - den) / s[i] * (s[i + 1] - s[i])
    return x
L32 = torch.randn(32, generator=torch.Generator().manual_seed(2)); mask = torch.zeros(32); mask[16:] = 1.0; xv = L32.clone(); xv[16:] = 0.0
print("\nsampler blend, 12 Euler steps: largest change outside the mask")
for name, lat, d in (("SetLatentNoiseMask", L32, 1.0), ("SetLatentNoiseMask", L32, 0.5), ("VAEEncodeForInpaint", xv, 1.0), ("VAEEncodeForInpaint", xv, 0.5)):
    o = (run(lat, mask, d)[:16] - lat[:16]).abs().max().item(); assert o < 1e-5
    print(f"{name:<21} denoise {d:<5} {o:.1e}")

# 4. Which channels an inpainting checkpoint gets: BaseModel.concat_cond with concat_keys ("mask", "masked_image") on a 9-channel U-Net.
print("\nan inpainting checkpoint takes 4 + 1 + 4 = 9 channels. Where the last 5 come from")
print("route                     mask channel           masked_image channels")
for a, b, c in (("SetLatentNoiseMask", "noise_mask, rounded", "the latent, not blanked"), ("VAEEncodeForInpaint", "noise_mask, rounded", "the latent, greyed first"), ("InpaintModelConditioning", "concat_mask, rounded", "concat_latent_image, greyed first")):
    print(f"{a:<25} {b:<22} {c}")
