# CU-116 lab: what LoadImage hands on. A plain stand-in for the arithmetic in LoadImage.load_image (nodes.py, ComfyUI v0.43.0), on made-up pixels, with the VAE's crop rule from comfy/sd.py.
# A run of the real node on two small files gave the same shapes and mask values as parts 1 and 2.
import torch
torch.manual_seed(0)
def load(pixels):
    """pixels: uint8 tensor [H, W, 3] or [H, W, 4]. Returns IMAGE [1, H, W, 3] and MASK."""
    image = pixels[..., :3].float() / 255.0
    if pixels.shape[-1] == 4:
        mask = 1.0 - pixels[..., 3].float() / 255.0
    else:
        mask = torch.zeros(64, 64)
    return image.unsqueeze(0), mask.unsqueeze(0)
rgba = torch.zeros(48, 64, 4, dtype=torch.uint8); rgba[..., :3] = torch.tensor([200, 160, 40], dtype=torch.uint8); rgba[..., 3] = 255; rgba[:24, :, 3] = 0
rgb = rgba[..., :3].clone()
print(f"{'file':<22}{'IMAGE':<20}{'MASK':<16}mask mean  mask at top, at bottom")
for name, p in (("with alpha, top clear", rgba), ("no alpha", rgb)):
    i, m = load(p)
    top = m[0, 0, 0].item(); bot = m[0, -1, -1].item()
    print(f"{name:<22}{str(list(i.shape)):<20}{str(list(m.shape)):<16}{m.mean().item():<11.3f}{top:.1f} {bot:.1f}")
i, m = load(rgba); assert i.shape == (1, 48, 64, 3) and m.shape == (1, 48, 64) and m[0, 0, 0] == 1 and m[0, -1, -1] == 0
i2, m2 = load(rgb); assert m2.shape == (1, 64, 64) and m2.sum() == 0
print("the mask of a file with no alpha is 64 x 64 whatever the picture's size:", list(m2.shape[1:]) != list(i2.shape[1:3]))
print("\nsize of a picture on its way into a latent")
def crop(h, w, r=8): return h // r * r, w // r * r
print(f"{'file':<14}{'after crop':<14}{'latent [B, 4, h, w]':<24}pixels lost")
for w, h in ((1024, 1024), (3024, 4032), (1000, 563), (515, 333)):
    ch, cw = crop(h, w); print(f"{f'{w}x{h}':<14}{f'{cw}x{ch}':<14}{f'[1, 4, {ch // 8}, {cw // 8}]':<24}{w * h - cw * ch:,}")
assert crop(333, 515) == (328, 512)
print("\nphone photo 3024x4032 in memory as an IMAGE:", f"{3024 * 4032 * 3 * 4 / 2 ** 20:.1f} MiB,", f"against the {512 * 512 * 3 * 4 / 2 ** 20:.1f} MiB of a 512x512 one, {3024 * 4032 / (512 * 512):.1f} times the pixels")
