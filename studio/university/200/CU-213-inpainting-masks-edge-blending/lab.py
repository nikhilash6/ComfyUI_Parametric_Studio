# CU-213 lab: how ComfyUI blends with a mask, and what resolution and shape that blend really has.
# The functions below follow ComfyUI v0.43.0 (file and function named in each docstring) on small tensors. Run: python lab.py  (CPU only, a second or two).
import math, torch
import torch.nn.functional as F
torch.manual_seed(0); torch.set_num_threads(1)
g = torch.Generator().manual_seed(0)

def feather_mask(mask, left, top, right, bottom):
    """comfy_extras/nodes_mask.py, FeatherMask.execute, for one mask [H, W]: multiplies the columns and rows next to the four borders by a linear ramp."""
    out = mask.clone(); H, W = out.shape; left, right, top, bottom = min(left, W), min(right, W), min(top, H), min(bottom, H)
    for x in range(left): out[:, x] *= (x + 1.0) / left
    for x in range(right): out[:, -(x + 1)] *= (x + 1) / right
    for y in range(top): out[y, :] *= (y + 1.0) / top
    for y in range(bottom): out[-(y + 1), :] *= (y + 1) / bottom
    return out
def outpaint_feather(d2, d3, top, left, bottom, right, feathering):
    """nodes.py, ImagePadForOutpaint.expand_image: mask inside the original image, (feathering - d)^2 / feathering^2 at distance d from a padded edge."""
    t = torch.zeros(d2, d3)
    if feathering > 0 and feathering * 2 < d2 and feathering * 2 < d3:
        for i in range(d2):
            for j in range(d3):
                d = min(i if top != 0 else d2, d2 - i if bottom != 0 else d2, j if left != 0 else d3, d3 - j if right != 0 else d3)
                if d < feathering: t[i, j] = ((feathering - d) / feathering) ** 2
    return t
def gaussian_kernel(ks, sigma):
    """comfy_extras/nodes_post_processing.py, gaussian_kernel: the grid runs from -1 to 1, so sigma is measured in half-widths of the kernel."""
    x, y = torch.meshgrid(torch.linspace(-1, 1, ks), torch.linspace(-1, 1, ks), indexing="ij"); d = torch.sqrt(x * x + y * y); k = torch.exp(-(d * d) / (2.0 * sigma * sigma)); return k / k.sum()
def image_blur(img, radius, sigma):
    """comfy_extras/nodes_post_processing.py, Blur (node ImageBlur) for one channel [H, W]: reflect padding, then a (2 radius + 1) square kernel."""
    ks = radius * 2 + 1; H, W = img.shape; p = F.pad(img.reshape(1, 1, H, W), (radius,) * 4, "reflect")
    return F.conv2d(p, gaussian_kernel(ks, sigma).reshape(1, 1, ks, ks), padding=ks // 2)[:, :, radius:-radius, radius:-radius][0, 0]
def composite_row(dest, src, mask):
    """comfy_extras/nodes_mask.py, composite, with source, mask and destination the same size: mask * source + (1 - mask) * destination."""
    return mask * src + (1 - mask) * dest
def to_latent(mask_px, factor=8):
    """comfy/utils.py, reshape_mask (called by comfy/sampler_helpers.py, prepare_mask): bilinear interpolation to the latent size, no antialiasing."""
    H, W = mask_px.shape; return F.interpolate(mask_px.reshape(1, 1, H, W), size=(H // factor, W // factor), mode="bilinear")[0, 0]
def grow_box(mask, k):
    """nodes.py, VAEEncodeForInpaint.encode: grow_mask_by, a k x k box of ones, padding ceil((k - 1) / 2), clamped to 0..1."""
    return torch.clamp(F.conv2d(mask.reshape(1, 1, *mask.shape).round(), torch.ones(1, 1, k, k), padding=math.ceil((k - 1) / 2)), 0, 1)[0, 0][:mask.shape[0], :mask.shape[1]]
def grow_cross(mask, expand, tapered=True):
    """comfy_extras/nodes_mask.py, GrowMask: expand rounds of a 3x3 maximum filter (scipy grey_dilation), without the corners when tapered_corners is on."""
    out = mask.clone()
    for _ in range(expand):
        p = F.pad(out, (1, 1, 1, 1)); H, W = out.shape; stack = [p[1 + dy:1 + dy + H, 1 + dx:1 + dx + W] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if tapered is False or dy == 0 or dx == 0]
        out = torch.stack(stack).amax(0)
    return out

# 1. Two ramps that ComfyUI builds. FeatherMask ramps linearly next to the border of the mask image, starting at 1/n, not at 0.
print("FeatherMask, left=8, all-ones mask, first 10 columns:  " + " ".join(f"{v:.3f}" for v in feather_mask(torch.ones(4, 16), 8, 0, 0, 0)[0, :10].tolist()))
print("ImagePadForOutpaint, feathering=8, rows from the padded edge:  " + " ".join(f"{v:.3f}" for v in outpaint_feather(32, 32, 8, 0, 0, 0, 8)[:10, 16].tolist()))

# 2. The seam. A flat 0.8 image is composited onto a flat 0.2 image, 64 pixels wide, through a mask that is 1 in columns 16..47. The output step is 0.6 times the mask step.
H, W = 32, 64; dest = torch.full((W,), 0.2); src = torch.full((W,), 0.8)
def seam_mask(kind):
    full = torch.zeros(H, W); full[:, 16:48] = 1.0
    if kind == "hard": return full[16]
    if kind == "FeatherMask 8": full[16, 16:48] = feather_mask(torch.ones(1, 32), 8, 0, 8, 0)[0]; return full[16]
    return image_blur(full, kind[0], kind[1])[16]
print("\nmask                                          largest step in the output   pixels with mask strictly between 0.1 and 0.9 (both seams)")
for kind, label in (("hard", "hard edge"), ("FeatherMask 8", "patch feathered with left=8 right=8"), ((8, 1.0), "ImageBlur radius 8 sigma 1.0"), ((8, 0.3), "ImageBlur radius 8 sigma 0.3"), ((16, 0.3), "ImageBlur radius 16 sigma 0.3")):
    m = seam_mask(kind); row = composite_row(dest, src, m); mixed = int(((m > 0.1) & (m < 0.9)).sum())
    print(f"{label:45s} {(row[1:] - row[:-1]).abs().max().item():<28.3f} {mixed}")

# 3. Growing a mask. One masked pixel at 20. The box in VAEEncodeForInpaint is asymmetric when its width is even.
one = torch.zeros(64, 64); one[20, 20] = 1.0
def extent(m): idx = (m[20] > 0).nonzero().flatten(); return f"{idx.min().item()}..{idx.max().item()}"
print("\ngrowing one masked pixel at column 20:  " + "   ".join(f"grow_mask_by {k}: {extent(grow_box(one, k))}" for k in (4, 5, 6, 7)))
c, sq = grow_cross(one, 3), grow_cross(one, 3, tapered=False)
print(f"GrowMask expand 3 on the same pixel: columns {extent(c)}, pixels set {int(c.sum())} with tapered corners, {int(sq.sum())} without")

# 4. What the sampler sees. The mask is interpolated down to the latent grid (factor 8): each latent cell reads two pixels per axis, pixels 3 and 4 of its 8.
print("\nlatent mask (8 cells of 8 pixels) for a hard pixel mask that is 1 from column e on")
for e in (24, 21, 20, 28):
    m = torch.zeros(8, 64); m[:, e:] = 1.0; print(f"  e = {e:<3d}" + " ".join(f"{v:.2f}" for v in to_latent(m)[0].tolist()))
print("a stripe 3 pixels wide, starting at offset s inside one latent cell: largest latent mask value")
vals, vals_grown = [], []
for s in range(8):
    m = torch.zeros(64, 64); m[:, 24 + s:27 + s] = 1.0; vals.append(to_latent(m).max().item()); vals_grown.append(to_latent(grow_box(m, 6)).max().item())
print("  s =              " + "    ".join(str(s) for s in range(8))); print("  stripe as drawn  " + " ".join(f"{v:.2f}" for v in vals)); print("  after grow_mask_by 6 " + " ".join(f"{v:.2f}" for v in vals_grown))
assert min(vals) == 0.0 and min(vals_grown) >= 0.5

# 5. The blend inside the sampler (comfy/samplers.py, KSamplerX0Inpaint.__call__), with a stand-in model: a fixed random network.
#    mask 1 = generate, 0 = keep, between = a mix. The known part is the original latent re-noised to the current sigma with the same noise every step.
n = 32; L = torch.sin(torch.linspace(0, 6, n)); noise = torch.randn(n, generator=g)
mask = torch.zeros(n); mask[8:24] = 0.5; mask[12:20] = 1.0
W1 = torch.randn(n, 64, generator=g) * 0.3; W2 = torch.randn(64, n, generator=g) * 0.3
def model(x, sigma): return x - sigma * (torch.tanh((x / math.sqrt(sigma ** 2 + 1)) @ W1) @ W2)
def x0_inpaint(x, sigma):
    keep = 1.0 - mask; x = x * mask + (L + noise * sigma) * keep                  # scale_latent_inpaint: noise_scaling(sigma, noise, latent_image)
    raw = model(x, sigma); return raw * mask + L * keep, raw
sigmas = torch.cat([torch.logspace(math.log10(14.6), math.log10(0.03), 12), torch.zeros(1)]); x = noise * sigmas[0] + L
for i in range(12):
    den, raw = x0_inpaint(x, sigmas[i]); x = x + (x - den) / sigmas[i] * (sigmas[i + 1] - sigmas[i])        # Euler step; the last step lands on the denoised value
print("\nsampler bookkeeping, 12 Euler steps, stand-in model, mask 0 / 0.5 / 1")
d0 = (x - L)[mask == 0].abs().max().item(); d1 = (x - raw)[mask == 1].abs().max().item(); dh = (x - (0.5 * raw + 0.5 * L))[mask == 0.5].abs().max().item()
print(f"  mask 0:   largest |final - original latent|                          {d0:.1e}")
print(f"  mask 1:   largest |final - last model output|                        {d1:.1e}")
print(f"  mask 0.5: largest |final - (0.5 last model output + 0.5 original)|   {dh:.1e}")
assert d0 < 1e-5 and d1 < 1e-5 and dh < 1e-5
