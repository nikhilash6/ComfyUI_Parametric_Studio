# CU-330 lab: the frame grid and latent shape of each video family, ported from ComfyUI v0.43.0. Pure arithmetic.
import math
# EmptyLTXVLatentVideo, Wan22ImageToVideoLatent, WanImageToVideo: latent frames = (n - 1) // k + 1. These floor.
def floor_grid(n, k): T = (n - 1) // k + 1; return T, (T - 1) * k + 1
# nodes_minimax_h3.py: align_frame_count walks up to the next 17k + 5, video_latent_t counts 5 latent frames per 17.
def align_frame_count(n):
    while n % 17 != 5: n += 1
    return n
def video_latent_t(f): return 2 if f <= 5 else ((f - 5) // 17) * 5 + 2
FAM = [("LTX-2.5", 8, 32, 128, 1), ("Wan 2.2 5B", 4, 16, 48, 2), ("Wan 2.1 and 14B", 4, 8, 16, 2), ("MiniMax H3", None, 16, 24, 2)]
def plan(name, k, s, c, p, n, w, h):
    if k is None: f = align_frame_count(max(5, n)); T = video_latent_t(f)
    else: T, f = floor_grid(n, k)
    H, W = h // s, w // s
    tokens = T * (H // p + (H % p > 0)) * (W // p + (W % p > 0))
    return f, T, H, W, c * T * H * W, tokens
print("You ask for 5 seconds at 24 fps, 120 frames, at 832 x 480.")
print("model             frames you get   seconds   latent (C, T, H, W)      latent values   video tokens")
for name, k, s, c, p in FAM:
    f, T, H, W, v, t = plan(name, k, s, c, p, 120, 832, 480)
    print(f"{name:17s} {f:<16d} {f / 24:<9.3f} {str((c, T, H, W)):<24s} {v:<15,d} {t:,d}")
assert plan(*FAM[0], 120, 832, 480)[0] == 113 and plan(*FAM[1], 120, 832, 480)[0] == 117 and plan(*FAM[3], 120, 832, 480)[0] == 124
print("\nFrame counts on each grid, up to 130:")
for name, k, _, _, _ in FAM[:2] + FAM[3:]:
    good = [f for f in range(1, 131) if (f % 17 == 5 if k is None else (f - 1) % k == 0)]
    print(f"{name:12s} {len(good):>3d} counts, the last few {good[-4:]}")
# H3's 17k + 5: tokens cover 1, 4, 4, 4, 4 frames in turn (FRAME_PER_TOKEN in comfy/ldm/minimax/model.py).
FRAME_PER_TOKEN = (1, 4, 4, 4, 4)
print("\nH3 frames per latent frame, summed:")
for f in (5, 22, 39, 124):
    T = video_latent_t(f); total = sum(FRAME_PER_TOKEN[i % 5] for i in range(T))
    print(f"{f:>4d} frames -> {T:>3d} latent frames -> {total:>3d} frames back")
    assert total == f
# Real files from our gallery, frame counts read with ffprobe. Each one sits on its model's grid.
print("\nFrame counts of real clips in our gallery, against the grid:")
for label, frames, ok in (("LTX-2.5, 6 s asked", 145, lambda f: (f - 1) % 8 == 0), ("LTX-2.5, virtual set", 121, lambda f: (f - 1) % 8 == 0), ("Wan 2.2, 5 s asked", 121, lambda f: (f - 1) % 4 == 0), ("MiniMax H3, 5 s asked", 124, lambda f: f % 17 == 5)):
    print(f"{label:24s} {frames:>4d} frames  on the grid: {ok(frames)}"); assert ok(frames)
print("\nWidth 850 asked of a node that floors: LTX keeps", 850 // 32 * 32, " Wan 2.2 5B keeps", 850 // 16 * 16)
