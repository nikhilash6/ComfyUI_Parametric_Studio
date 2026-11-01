# CU-334 lab: what long video costs, and which fix touches which cost. Formulas from comfy/model_base.py and comfy/sd.py (ComfyUI v0.43.0), then plain arithmetic.
import math
# 1. Length: sampler tokens grow with frames, attention pairs with their square. Same shape in 3 families at 960 x 544.
def t_ltx(n, w=960, h=544): return ((n - 1) // 8 + 1) * (h // 32) * (w // 32)
def t_wan(n, w=960, h=544): return ((n - 1) // 4 + 1) * (h // 16 // 2) * (w // 16 // 2)
def t_h3(n, w=960, h=544):
    while n % 17 != 5: n += 1
    return ((n - 5) // 17 * 5 + 2) * (h // 16 // 2) * (w // 16 // 2)
print("seconds at 24 fps   LTX tokens   Wan 5B tokens   H3 video tokens   attention pairs against 5 s")
base = t_ltx(121)
for s in (5, 10, 20, 40):
    n = s * 24 + 1; print(f"{s:<19d} {t_ltx(n):<12,d} {t_wan(n):<15,d} {t_h3(n):<17,d} {t_ltx(n) ** 2 / base ** 2:.1f}x")
assert t_ltx(241) ** 2 > 3.5 * t_ltx(121) ** 2
# 2. Decode estimates in comfy/sd.py (bfloat16 or fp16, 2 bytes). H3 clamps to one chunk, Wan 2.2 leaves frames out, LTX counts them.
def d_ltx(n, w, h, t_tile=None, s_tile=None):
    T, H, W = (n - 1) // 8 + 1, h // 32, w // 32
    if t_tile: T = min(T, t_tile)
    if s_tile: H, W = min(H, s_tile), min(W, s_tile)
    return 1200 * T * H * W * 512 * 2 / 1024 ** 3
def d_wan(w, h): return 8000 * (h // 16) * (w // 16) * 256 * 2 / 1024 ** 3
def d_h3(n, w, h): f = min(n, 28 + 2); return (9.5 * f * h * w + 270_000_000) * 2 * 1.03 / 1024 ** 3
print("\ndecode memory estimate, GiB, 1920 x 1088:")
print("frames   LTX whole   LTX temporal tile 8   LTX + spatial tile 16   Wan 5B   H3")
for n in (121, 241, 481):
    print(f"{n:<8d} {d_ltx(n, 1920, 1088):<11.1f} {d_ltx(n, 1920, 1088, 8):<21.1f} {d_ltx(n, 1920, 1088, 8, 16):<23.1f} {d_wan(1920, 1088):<8.1f} {d_h3(n, 1920, 1088):.1f}")
assert d_h3(121, 1920, 1088) == d_h3(481, 1920, 1088) and d_ltx(481, 1920, 1088, 8) == d_ltx(121, 1920, 1088, 8)
# 3. Frames in RAM: an IMAGE is float32, 4 bytes a value, 3 values a pixel.
print("\nthe finished frames in system RAM as a float32 IMAGE:")
for w, h, s in ((960, 544, 5), (1344, 768, 15), (1920, 1088, 60)):
    print(f"{w}x{h}, {s} s at 24 fps: {w * h * 3 * 4 * s * 24 / 1024 ** 3:.1f} GiB")
# 4. A chain: each new clip starts from the old clip's last frames, and the first frames of each new clip are dropped at the join.
def chain(total, clip, overlap):
    n = 1; have = clip
    while have < total: have += clip - overlap; n += 1
    return n, have
print("\na chain to reach 60 s at 24 fps (1440 frames) with H3-sized clips of 124 frames")
for ov in (1, 5, 22):
    n, have = chain(1440, 124, ov); print(f"overlap {ov:>2d} frames: {n} clips, {n * 124} frames rendered for {have} kept, {n * 124 / have:.3f} times the work, {n - 1} seams")
assert chain(1440, 124, 1)[0] == 12
# 5. Temporal tiles in tiled_scale_multidim: the same position rule as spatial tiles, on latent frames.
def starts(D, S, O): return list(range(0, D - O, S - O)) if D > S else [0]
for T in (16, 31, 61):
    st = starts(T, 8, 1); print(f"{T} latent frames, temporal tile 8, overlap 1: {len(st)} decodes, starts {st}")
