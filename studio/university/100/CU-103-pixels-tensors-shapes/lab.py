# CU-103 lab: the shapes, ranges and 8-bit levels that ComfyUI's IMAGE and LATENT tensors live in. CPU only, about a second.
# Run: python lab.py
# The crop, the rescale and the clamp are written the way comfy/sd.py (VAE.encode, VAE.decode) and nodes.py (SaveImage) do them.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)

# 1. Layout. An IMAGE is [B, H, W, C], floats 0..1, channels last. Convolutions want [B, C, H, W].
B, H, W, C = 2, 6, 8, 3
red = torch.zeros(B, H, W, C); red[..., 0] = 1.0                       # every pixel pure red
moved = red.movedim(-1, 1)                                             # what VAE.encode does with the pixels
wrong = red.reshape(B, C, H, W)                                        # same shape, but the numbers are only relabelled
print(f"IMAGE {list(red.shape)} strides {red.stride()}   after movedim(-1, 1): {list(moved.shape)} strides {moved.stride()}")
print(f"movedim shares memory with the IMAGE: {moved.data_ptr() == red.data_ptr()}   contiguous: {moved.is_contiguous()}")
print(f"share of channel 0 that is red:  movedim {moved[:, 0].mean().item():.3f}   reshape {wrong[:, 0].mean().item():.3f}")
conv = torch.nn.Conv2d(3, 4, 3)
print(f"Conv2d(3, 4, 3) on the [B, C, H, W] tensor gives {list(conv(moved).shape)}")
try: conv(red); print("Conv2d on the [B, H, W, C] tensor: accepted")
except RuntimeError as e: print(f"Conv2d on the [B, H, W, C] tensor: {type(e).__name__}")
print(f"Conv2d on the reshaped tensor: accepted, gives {list(conv(wrong).shape)}, computed from scrambled pixels")
assert moved.data_ptr() == red.data_ptr() and not moved.is_contiguous() and moved[:, 0].min() == 1 and wrong[:, 0].mean() < 0.5

# 2. Size rules of the VAE nodes: crop to a multiple of 8, then the latent has [4, H/8, W/8] values per image.
def crop_to_multiple(px, ratio=8):                                     # vae_encode_crop_pixels in comfy/sd.py
    for d in (1, 2):
        size = px.shape[d]; keep = size // ratio * ratio; offset = (size % ratio) // 2
        if keep != size: px = px.narrow(d, offset, keep)
    return px
print(f"\n{'requested':<12}{'after crop':<12}{'latent shape':<19}numbers in image / latent")
for h, w in ((512, 512), (333, 515), (563, 1000), (1024, 1024)):
    px = crop_to_multiple(torch.zeros(1, h, w, 3)); ch, cw = px.shape[1:3]; n_img, n_lat = ch * cw * 3, 4 * (ch // 8) * (cw // 8)
    print(f"{f'{w}x{h}':<12}{f'{cw}x{ch}':<12}{f'[1, 4, {ch // 8}, {cw // 8}]':<19}{n_img} / {n_lat} = {n_img / n_lat:.0f}x")
assert crop_to_multiple(torch.zeros(1, 333, 515, 3)).shape == (1, 328, 512, 3)

# 3. Range. The VAE input is image * 2 - 1; the output goes through (x + 1) / 2 and a clamp to 0..1.
y = torch.tensor([-1.2, -1.0, 0.0, 0.5, 1.0, 1.3])                     # pretend decoder outputs, two of them outside -1..1
row = lambda t: " ".join(f"{v:5.2f}" for v in t.tolist())
print(f"\ndecoder output  {row(y)}\n(x + 1) / 2      {row((y + 1) / 2)}\nafter clamp      {row(((y + 1) / 2).clamp(0, 1))}")

# 4. Memory. An IMAGE tensor is float32, four bytes per value, even though a PNG holds one byte.
print("\nIMAGE tensor size in float32")
for b, h, w in ((1, 512, 512), (4, 1024, 1024), (100, 1080, 1920)):
    n = b * h * w * 3 * torch.finfo(torch.float32).bits // 8
    print(f"batch {b:<4} {w}x{h:<6} {n:>13,d} bytes = {n / 2 ** 20:9.1f} MiB   (as uint8: {n / 4 / 2 ** 20:8.1f} MiB)")

# 5. Eight-bit levels. SaveImage does np.clip(255. * image, 0, 255).astype(np.uint8): the cast truncates, it does not round.
levels = torch.arange(256, dtype=torch.float32) / 255
ks = torch.arange(256)
def save_rounded(img): return (255. * img).clamp(0, 255).round().to(torch.uint8)
def save_truncated(img): return (255. * img).clamp(0, 255).to(torch.uint8)
print(f"\nan 8-bit image has {sum(1 for k in range(256) if 0.5 <= k / 255 < 1)} levels between 0.5 and 1.0")
print("add 0.1, subtract 0.1, then save (worst error in 8-bit levels; kept = how many of the 256 levels come back unchanged)")
print(f"{'dtype':<10}{'eps':<16}{'values in [0.5, 1)':<21}{'worst error':<14}{'kept by rounding':<19}kept by truncating")
kept = {}
for name, dt in (("float32", torch.float32), ("float16", torch.float16), ("bfloat16", torch.bfloat16)):
    x = levels.to(dt); z = (x + 0.1) - 0.1                              # arithmetic that should cancel
    assert (save_rounded(x) == ks).all() and (save_truncated(x) == ks).all()   # storing and saving alone loses nothing
    worst = ((255. * z).float() - ks).abs().max().item(); r = int((save_rounded(z) == ks).sum()); t = int((save_truncated(z) == ks).sum()); kept[name] = (r, t)
    print(f"{name:<10}{torch.finfo(dt).eps:<16.8g}{round(1 / torch.finfo(dt).eps):<21d}{worst:<14.4f}{r:<19d}{t}")
assert kept["float32"][0] == 256 and kept["float32"][1] < 256 and kept["bfloat16"][0] < 256
