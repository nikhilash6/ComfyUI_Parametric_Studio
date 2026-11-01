# CU-361 lab: the same sphere as a point cloud, a splat and a mesh. Ports the idea of _splat_density and _otsu_level from comfy_extras/nodes_gaussian_splat.py (ComfyUI v0.43.0). CPU, seeded.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1); g = torch.Generator().manual_seed(0)
# 1. What each kind stores, per element. SPLAT from comfy_api/latest/_util/geometry_types.py. K = (sh_degree + 1) ** 2.
def splat_floats(deg): return 3 + 3 + 4 + 1 + 3 * (deg + 1) ** 2
print("per element, in 32-bit floats:")
print(f"  point with colour: {3 + 3}")
for d in (0, 1, 3): print(f"  Gaussian, SH degree {d}: {splat_floats(d)} (centre 3, scale 3, rotation 4, opacity 1, colour {3 * (d + 1) ** 2})")
print(f"  mesh vertex with colour: 6, plus 3 integers per triangle, about 2 triangles per vertex on a closed mesh")
assert splat_floats(0) == 14 and splat_floats(3) == 59
# The standard .ply adds three unused normals, written by _gaussian_ply_bytes.
for n, d in ((100_000, 0), (1_000_000, 3)):
    print(f"{n:>9,d} Gaussians, degree {d}, in a .ply: {(splat_floats(d) + 3) * 4 * n / 1024 ** 2:.1f} MiB")
# 2. N points on a sphere of radius 1: a point has no size, so density decides whether a surface is there.
N = 4000; P = torch.randn(N, 3, generator=g); P = P / P.norm(dim=1, keepdim=True)
# 3. Density grid: each Gaussian adds opacity * exp(-d^2 / (2 s^2)) in a window of 3 sigma, as _splat_density does for an isotropic Gaussian.
def density(P, s, res=48):
    lo = P.min(0).values - 4 * s; hi = P.max(0).values + 4 * s; vox = ((hi - lo).max() / res).item()
    dims = (((hi - lo) / vox).ceil().long() + 1).tolist(); vol = torch.zeros(dims); k = max(1, math.ceil(3 * s / vox))
    idx = ((P - lo) / vox).round().long(); off = torch.arange(-k, k + 1)
    oz, oy, ox = torch.meshgrid(off, off, off, indexing="ij"); O = torch.stack([oz, oy, ox], -1).reshape(-1, 3)
    for i in range(0, P.shape[0], 512):
        c = idx[i:i + 512][:, None, :] + O[None]; pos = lo + c.float() * vox; d2 = (pos - P[i:i + 512][:, None, :]).pow(2).sum(-1); w = torch.exp(-d2 / (2 * s * s))
        ok = ((c >= 0) & (c < torch.tensor(dims))).all(-1)
        fl = c[ok][:, 0] * dims[1] * dims[2] + c[ok][:, 1] * dims[2] + c[ok][:, 2]; vol.view(-1).index_add_(0, fl, w[ok])
    return vol, lo, vox
def otsu(v, bins=256):
    h = torch.histc(v, bins, v.min().item(), v.max().item()).double(); w = h / h.sum(); c = torch.linspace(v.min().item(), v.max().item(), bins).double()
    W = w.cumsum(0); M = (w * c).cumsum(0); bv = (M[-1] * W - M) ** 2 / (W * (1 - W)).clamp_min(1e-12); return c[bv.argmax()].item()
print("\nblob size   occupied voxels   Otsu level   surface voxels   holes on a line test (rays that miss the surface, of 200)")
holes = {}
for s in (0.01, 0.03, 0.08):
    vol, lo, vox = density(P, s); occ = vol[vol > vol.max() * 1e-3]; lv = otsu(occ); solid = vol > lv
    rays = torch.randn(200, 3, generator=g); rays = rays / rays.norm(dim=1, keepdim=True); miss = 0
    for r in rays:
        pts = ((torch.linspace(0.8, 1.2, 40)[:, None] * r[None]) - lo) / vox; pi = pts.round().long().clamp_min(0)
        pi = torch.min(pi, torch.tensor(vol.shape) - 1); miss += not bool(solid[pi[:, 0], pi[:, 1], pi[:, 2]].any())
    holes[s] = miss; print(f"{s:<11} {occ.numel():<17,d} {lv:<12.3f} {int(solid.sum()):<16,d} {miss}")
assert holes[0.08] <= holes[0.01]
print("small blobs on sparse points leave holes; bigger blobs close them and thicken the wall")
# 4. Compositing a line of sight, the idea behind front-to-back depth slabs: colour and transparency, no surface needed.
a = torch.tensor([0.5, 0.5, 0.5]); T = torch.cat([torch.ones(1), (1 - a).cumprod(0)[:-1]]); print("\nthree blobs on one ray, opacity 0.5 each: weights", [round(x, 3) for x in (a * T).tolist()], "background gets", round((1 - a).prod().item(), 3))
# 5. Splat rotation: a flat disc seen edge on and face on. Projected area of a Gaussian with scales (1, 1, 0.05).
s = torch.tensor([1, 1, 0.05])
for deg in (0, 45, 90):
    th = math.radians(deg); R = torch.tensor([[1.0, 0, 0], [0, math.cos(th), -math.sin(th)], [0, math.sin(th), math.cos(th)]]); C = R @ torch.diag(s ** 2) @ R.T
    print(f"a flat disc tilted {deg:>2d} degrees: footprint on screen {math.sqrt(torch.det(C[:2, :2]).item()):.3f}")
