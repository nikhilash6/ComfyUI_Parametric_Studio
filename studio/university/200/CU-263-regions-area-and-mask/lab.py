# CU-263 lab: ports of get_area_and_mult and the blending in _calc_cond_batch (comfy/samplers.py), compared with the real function on a CPU.
# A "prediction" here is a constant, so every printed number is that entry's share of a cell. Picture 768 by 512 is 96 by 64 cells.
import torch
H, W = 64, 96
def area_mult(area, strength=1.0, fuzz=8):
    ah, aw, y, x = area; ah = min(H - y, ah); aw = min(W - x, aw); m = torch.ones(ah, aw) * strength
    for dim, (size, off, total) in enumerate(((ah, y, H), (aw, x, W))):
        rr = min(fuzz, size // 4)
        if off != 0:
            for t in range(rr): m.narrow(dim, t, 1).mul_((t + 1) / rr)
        if size + off < total:
            for t in range(rr): m.narrow(dim, size - 1 - t, 1).mul_((t + 1) / rr)
    return m, (ah, aw, y, x)
def blend(entries):
    """entries: (value, area or None, strength, mask or None) -> the blended prediction."""
    out = torch.zeros(H, W); cnt = torch.ones(H, W) * 1e-37; calls = 0; crops = []
    for v, area, st, mask in entries:
        calls += 1
        if mask is not None: m = mask * st; out += v * m; cnt += m; crops.append((H, W))
        elif area is None: out += v * st; cnt += st; crops.append((H, W))
        else:
            m, (ah, aw, y, x) = area_mult(area, st); out[y:y + ah, x:x + aw] += v * m; cnt[y:y + ah, x:x + aw] += m; crops.append((ah, aw))
    return out / cnt, calls, crops
AREA = (256 // 8, 256 // 8, 200 // 8, 256 // 8)                   # ConditioningSetArea: width 256, height 256, x 256, y 200
print("the area tuple for w 256, h 256, x 256, y 200:", AREA)
m, _ = area_mult(AREA); print("first 10 cells across the box:", " ".join(f"{v:.3f}" for v in m[16, :10].tolist()))
assert abs(m[16, 0].item() - 1 / 8) < 1e-6 and m[16, 16].item() == 1
print("\nboxed prompt = 1, whole-picture prompt = 0. The number is the boxed prompt's share.")
print("strength   box centre   box edge   outside")
for st in (.5, 1., 3., 10.):
    p, _, _ = blend([(0., None, 1., None), (1., AREA, st, None)]); print(f"{st:<10} {p[41, 48].item():<12.3f} {p[41, 32].item():<10.3f} {p[5, 5].item():.3f}")
p, calls, crops = blend([(0., None, 1., None), (1., AREA, 1., None)]); print("entries run:", calls, "  model input sizes in cells:", crops)
assert crops[1] == (32, 32) and abs(p[41, 48].item() - .5) < 1e-6 and p[5, 5].item() == 0
s1, _, _ = blend([(1., AREA, 1., None)]); s2, _, _ = blend([(1., AREA, 5., None)])
print("\nonly the box, nothing whole-picture: centre", s1[41, 48].item(), "  with strength 5:", s2[41, 48].item(), "  outside the box:", s1[5, 5].item())
assert s1[41, 48].item() == s2[41, 48].item() == 1 and s1[5, 5].item() == 0
mask = torch.zeros(H, W); mask[25:57, 32:64] = 1
pm, _, cropsm = blend([(0., None, 1., None), (1., None, 1., mask)])
print("\na mask over the same square: centre", pm[41, 48].item(), " edge", pm[41, 32].item(), " outside", pm[5, 5].item(), "  model input sizes:", cropsm)
assert cropsm[1] == (H, W) and pm[41, 32].item() == .5
print("\nthe same pixel numbers on a family whose latent is 16 times smaller than the picture, not 8")
print("ConditioningSetArea still divides by 8: a 256 pixel box becomes", 256 // 8, "cells, which is", 256 // 8 * 16, "pixels there")
print("ConditioningSetAreaPercentage uses the real latent size: 0.33 of a 64-cell side is", max(1, round(.33 * 64)), "cells")
