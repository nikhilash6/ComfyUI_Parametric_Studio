# CU-109 lab: width, height and the pixel budget. Standard library only, about a second.
# Run: python lab.py
# Part 1 follows EmptyLatentImage's integer division. Part 2 is the arithmetic of the "Scale Image to Total Pixels" node (ComfyUI v0.43.0).
# Part 3 checks the 40 training sizes listed in Appendix I of the SDXL paper. Part 4 counts how cost grows with the side of a square image.
import math

P = 1024 * 1024                                                    # a budget of one "megapixel" as ComfyUI counts it: 1024 x 1024

# 1. What you type is not always what you get. EmptyLatentImage makes a latent of [4, height // 8, width // 8] and the VAE decodes back to 8 x that.
print("requested   latent [1, 4, h, w]   decoded size   pixels lost")
for w, h in ((1024, 1024), (1333, 750), (1920, 1080)):
    lh, lw = h // 8, w // 8
    print(f"{f'{w}x{h}':<12}{f'[1, 4, {lh}, {lw}]':<22}{f'{lw * 8}x{lh * 8}':<15}{w * h - lw * 8 * lh * 8:,d}")

# 2. Scale Image to Total Pixels: scale both sides by sqrt(budget / pixels), then round each to a multiple of resolution_steps.
def scale_to_total_pixels(w, h, megapixels=1.0, steps=1):
    scale = math.sqrt(megapixels * 1024 * 1024 / (w * h))
    return round(w * scale / steps) * steps, round(h * scale / steps) * steps
print("\ninput        steps   result       pixels / budget   ratio error")
for w, h in ((1920, 1080), (3000, 2000), (1000, 1000), (1080, 1920)):
    for steps in (1, 8, 64):
        rw, rh = scale_to_total_pixels(w, h, 1.0, steps)
        print(f"{f'{w}x{h}':<13}{steps:<8}{f'{rw}x{rh}':<13}{rw * rh / P:<18.4f}{(rw / rh) / (w / h) - 1:+.4f}")
assert scale_to_total_pixels(1920, 1080, 1.0, 64) == (1344, 768) and scale_to_total_pixels(1920, 1080, 1.0, 1) == (1365, 768)

# 3. SDXL's multi-aspect training sizes, (height, width), Appendix I of the paper.
SDXL = [(512, 2048), (512, 1984), (512, 1920), (512, 1856), (576, 1792), (576, 1728), (576, 1664), (640, 1600), (640, 1536), (704, 1472),
        (704, 1408), (704, 1344), (768, 1344), (768, 1280), (832, 1216), (832, 1152), (896, 1152), (896, 1088), (960, 1088), (960, 1024),
        (1024, 1024), (1024, 960), (1088, 960), (1088, 896), (1152, 896), (1152, 832), (1216, 832), (1280, 768), (1344, 768), (1408, 704),
        (1472, 704), (1536, 640), (1600, 640), (1664, 576), (1728, 576), (1792, 576), (1856, 512), (1920, 512), (1984, 512), (2048, 512)]
areas = [h * w for h, w in SDXL]
print(f"\nSDXL sizes: {len(SDXL)}, all sides multiples of 64: {all(h % 64 == 0 and w % 64 == 0 for h, w in SDXL)}, "
      f"pixels between {min(areas) / P:.4f} and {max(areas) / P:.4f} of 1024 x 1024")
def fit(ratio, budget=P, m=64, floor=0.9):
    """Among pairs of multiples of m with floor * budget <= pixels <= budget, the one whose width / height is closest to ratio; the larger one wins a tie."""
    best = None
    for h in range(m, 4097, m):
        for w in range(m, 4097, m):
            if floor * budget <= w * h <= budget:
                key = (round(abs(math.log(w / h) - math.log(ratio)), 12), -w * h)
                if best is None or key < best[0]: best = (key, (w, h))
    return best[1]
hits = sum(fit(1 / round(h / w, 2)) == (w, h) for h, w in SDXL)       # the paper's table gives height / width to two decimals
print(f"a rule 'multiples of 64, between 90% and 100% of the budget, closest ratio' finds {hits} of the 40 sizes from their rounded ratios")
print("(the 90% floor was read off this same table, so this checks the rule's consistency, not the paper's method)")
assert hits == 40 and all(64 * 64 <= h * w for h, w in SDXL)
print("\nwanted ratio    multiples of 64     multiples of 8      the 64 result is in the SDXL list")
for name, r in (("1:1", 1.0), ("4:3", 4 / 3), ("3:2", 1.5), ("16:9", 16 / 9), ("9:16", 9 / 16)):
    a, b = fit(r, m=64), fit(r, m=8)
    print(f"{name:<16}{f'{a[0]}x{a[1]}':<20}{f'{b[0]}x{b[1]}':<20}{'yes' if (a[1], a[0]) in SDXL else 'no'}")

# 4. Cost of a square image of side s. Tokens N = (s / 8)^2 if a layer attends over every latent position; an N x N attention matrix has N^2 entries.
# The last column uses the memory estimate that comfy/sd.py attaches to the VAE decoder: 2178 * latent_h * latent_w * 64 * bytes per value (times 2.73 on AMD, not shown).
print("\nside   pixels / 512x512   tokens N   N^2 entries        full matrix in fp16   VAE decode estimate (fp32)")
for s in (512, 768, 1024, 1536, 2048):
    n = (s // 8) ** 2; est = 2178 * (s // 8) * (s // 8) * 64 * 4
    print(f"{s:<7}{s * s / 512 ** 2:<19.2f}{n:<11,d}{n * n:<19,d}{n * n * 2 / 2 ** 30:>9.2f} GiB{'':<9}{est / 2 ** 30:>6.2f} GiB")
assert (1024 // 8) ** 4 == 16 * (512 // 8) ** 4
