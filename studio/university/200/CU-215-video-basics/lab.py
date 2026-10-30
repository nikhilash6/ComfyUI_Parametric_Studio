# CU-215 lab: frames, latent frames, compression and attention cost for video, from ComfyUI's own constants. Pure arithmetic.
# Run: python lab.py  (CPU only, instant). Prints the same numbers every time.
import math

# 1. A clip's frame count is seconds times frames per second. The fps is only the playback rate you give to CreateVideo.
print("seconds x fps = frames:   5 s at 16 fps = %d,  at 24 fps = %d,  at 30 fps = %d" % (5 * 16, 5 * 24, 5 * 30))

# 2. Causal video VAEs treat the first frame alone and the rest in groups of k (k = 4, 6 or 8). ComfyUI's empty-latent nodes use
#    latent frames = (length - 1) // k + 1, and comfy/sd.py decodes `a` latent frames to k * a - (k - 1) frames.
def latents(f, k): return (f - 1) // k + 1
def frames_back(a, k): return a * k - (k - 1)
print("\nframes asked for -> latent frames -> frames after decoding")
print("asked   k=4 (Wan, Hunyuan)   k=6 (Mochi)    k=8 (LTXV, Cosmos)")
for f in (80, 81, 97, 120, 121, 122, 125):
    cells = [f"{latents(f, k):>2d} -> {frames_back(latents(f, k), k):>3d}" for k in (4, 6, 8)]
    print(f"{f:<7d} {cells[0]:<20s} {cells[1]:<13s} {cells[2]}")
valid = {k: [f for f in range(1, 130) if frames_back(latents(f, k), k) == f] for k in (4, 6, 8)}
assert 121 in valid[4] and 121 in valid[6] and 121 in valid[8] and 120 not in valid[4] and 81 in valid[4] and 97 in valid[8] and 25 in valid[6]
print("lengths that come back unchanged below 130:  k=4 has %d of them, k=6 has %d, k=8 has %d;  121 is in all three" % (len(valid[4]), len(valid[6]), len(valid[8])))

# 3. Compression, from the constants in comfy_extras/nodes_*.py (default size of each node) and comfy/sd.py.
#    RGB values in, divided by latent values out. For long clips the ratio tends to 3 * k * s * s / channels.
models = [("Wan 2.1 (WanImageToVideo)", 4, 8, 16, 832, 480, 81), ("HunyuanVideo (EmptyHunyuanLatentVideo)", 4, 8, 16, 848, 480, 25), ("Mochi (EmptyMochiLatentVideo)", 6, 8, 12, 848, 480, 25),
          ("Cosmos (EmptyCosmosLatentVideo)", 8, 8, 16, 1280, 704, 121), ("LTXV (EmptyLTXVLatentVideo)", 8, 32, 128, 768, 512, 97)]
print("\nmodel                                    k  s   ch   default size      latent shape (ch, T, H, W)   RGB values / latent values   long-clip limit")
for name, k, s, ch, w, h, f in models:
    T = latents(f, k); shape = (ch, T, h // s, w // s); lat = math.prod(shape); rgb = 3 * f * h * w; limit = 3 * k * s * s / ch
    print(f"{name:40s} {k}  {s:<3d} {ch:<4d} {w}x{h}x{f:<4d}  {str(shape):<28s} {rgb / lat:<28.2f} {limit:.0f}")
assert 3 * 4 * 8 * 8 / 16 == 48 and 3 * 8 * 32 * 32 / 128 == 192 and 3 * 6 * 8 * 8 / 12 == 96

# 4. Tokens and attention. The transformer turns each latent frame into (H/p)*(W/p) tokens. Wan uses patch (1, 2, 2); LTXV uses 1.
def tokens(f, k, lh, lw, p): return latents(f, k) * (lh // p) * (lw // p)
n81, n161 = tokens(81, 4, 60, 104, 2), tokens(161, 4, 60, 104, 2)
print(f"\nWan, 832x480: 81 frames -> {latents(81, 4)} latent frames -> {n81:,d} tokens.  161 frames -> {latents(161, 4)} latent frames -> {n161:,d} tokens")
print(f"doubling the frames (81 -> 161) multiplies the tokens by {n161 / n81:.2f} and the number of attention pairs by {(n161 / n81) ** 2:.2f}")
print(f"LTXV, 768x512, 97 frames: {tokens(97, 8, 16, 24, 1):,d} tokens")
# One plain transformer block with n tokens, width d, feed-forward factor 4: attention scores and mixing cost 4 n^2 d operations, the four
# projections and the feed-forward layers 24 n d^2. The attention share is n / (n + 6 d). A textbook estimate, not a measurement.
d = 3072
print(f"\nattention share of a block's operations, width d = {d} (HunyuanVideo, feed-forward factor 4, patch 2x2x1 as listed in the LTX-Video paper), 848x480")
print("frames  latent frames  tokens    attention share n/(n+6d)")
for f in (25, 49, 97, 121):
    n = tokens(f, 4, 60, 106, 2); print(f"{f:<7d} {latents(f, 4):<14d} {n:<9,d} {n / (n + 6 * d):.3f}")
