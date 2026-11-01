# CU-272 lab: the same scene through core's depth renderers.
# v2_style and min_max follow comfy/ldm/depth_anything_3/preprocess.py. The disparity version follows _normalize_disparity in comfy_extras/nodes_moge.py.
import torch
def v2_style(d, sky=None, lo_q=0.01, hi_q=0.99):
    v = d[~sky] if sky is not None else d
    lo, hi = torch.quantile(v, lo_q), torch.quantile(v, hi_q); n = ((d - lo) / (hi - lo).clamp(min=1e-6)).clamp(0, 1); n = 1 - n
    return torch.where(sky, torch.zeros_like(n), n) if sky is not None else n
def min_max(d): return 1 - (d - d.min()) / (d.max() - d.min()).clamp(min=1e-6)
def disparity(d):
    v = torch.isfinite(d) & (d > 0); p = torch.where(v, 1 / d.clamp_min(1e-6), torch.zeros_like(d))
    lo, hi = torch.quantile(p[v], 0.001), torch.quantile(p[v], 0.999); return ((p - lo) / (hi - lo).clamp_min(1e-6)).clamp(0, 1)
scene = torch.linspace(2.0, 10.0, 100001, dtype=torch.float64)   # a floor that runs from 2 m to 10 m
at = lambda g, z: g[(scene - z).abs().argmin()].item()

print("a scene from 2 m to 10 m. Grey value at each distance; 1 is white")
print("distance   DA3 v2_style   DA3 min_max   MoGe disparity")
a, b, c = v2_style(scene), min_max(scene), disparity(scene)
for z in (2, 3, 4, 6, 8, 10):
    print(f"{z} m{'':<6} {at(a, z):<14.3f} {at(b, z):<13.3f} {at(c, z):.3f}")
assert at(a, 2) > 0.99 and at(a, 10) < 0.01 and at(c, 6) < 0.25 and 0.45 < at(a, 6) < 0.55
print("all three put near at white. Depth-linear greys spend even steps per metre, disparity spends most of its range up close")
print("half of the grey range covers: v2_style from 2 m to", round(scene[(a - 0.5).abs().argmin()].item(), 1), "m   disparity from 2 m to", round(scene[(c - 0.5).abs().argmin()].item(), 1), "m")

# Now add a far sky to a share of the pixels. How many of the 256 levels of an 8-bit picture are left for the scene?
def levels(g, mask): return len(torch.unique((g[mask] * 255).round()))
print("\nadd pixels at 500 m (sky). Distinct 8-bit grey levels left for the 2 m to 10 m part")
print("sky share   min_max   v2_style   v2_style with a sky mask   disparity")
out = {}
for share in (0.0, 0.005, 0.02, 0.3):
    n = int(share * 20000 / (1 - share)); d = torch.cat([torch.linspace(2.0, 10.0, 20000, dtype=torch.float64), torch.full((n,), 500.0, dtype=torch.float64)]); sky = d > 100; fg = ~sky
    r = (levels(min_max(d), fg), levels(v2_style(d), fg), levels(v2_style(d, sky), fg), levels(disparity(d), fg)); out[share] = r
    print(f"{share:<11} {r[0]:<9} {r[1]:<10} {r[2]:<26} {r[3]}")
assert out[0.3][0] < 8 and out[0.3][2] > 200 and out[0.005][1] > 200 and out[0.02][1] < 8
# A convention check you can do by eye: is the thing you know is near brighter than the thing you know is far?
near_px, far_px = at(a, 2.5), at(a, 9.5); inv = 1 - a
print(f"\nby-eye check: near object {near_px:.2f}, far wall {far_px:.2f}: near is brighter, this map is near-white")
print(f"after ImageInvert: near object {1 - near_px:.2f}, far wall {1 - far_px:.2f}: the same geometry as a negative. correlation with the original {torch.corrcoef(torch.stack([a, inv]))[0, 1].item():.3f}")
assert torch.corrcoef(torch.stack([a, inv]))[0, 1].item() < -0.999
