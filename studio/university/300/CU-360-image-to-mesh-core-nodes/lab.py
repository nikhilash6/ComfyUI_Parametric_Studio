# CU-360 lab: voxels to triangles. Ports of voxel_to_mesh ("basic") and a Surface Nets vertex rule from comfy_extras/nodes_hunyuan3d.py (ComfyUI v0.43.0), on a known sphere.
import math, torch
torch.set_num_threads(1)
def field(res, radius=0.7):
    """values on a (res + 1) grid over the box, like VanillaVolumeDecoder's grid with bounds 1.01. Positive inside."""
    c = torch.linspace(-1.01, 1.01, res + 1); z, y, x = torch.meshgrid(c, c, c, indexing="ij")
    return radius - (x * x + y * y + z * z).sqrt(), 2.02 / res
def basic_faces(v, thr):
    b = (v > thr).float(); p = torch.nn.functional.pad(b, (1, 1, 1, 1, 1, 1)); n = 0
    for dz, dy, dx in ((0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0)):
        n += int(((p[1:-1, 1:-1, 1:-1] > 0) & (torch.roll(p, (-dz, -dy, -dx), (0, 1, 2))[1:-1, 1:-1, 1:-1] == 0)).sum())
    return n        # exposed square faces; the node makes 2 triangles and 4 new vertices for each
def surfnet(v, thr, h):
    """one vertex per cell the surface crosses, at the mean of the edge crossings; one quad across each crossing grid edge."""
    D = v.shape[0] - 1; ids = {}; verts = []
    inside = v > thr
    corners = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]
    edges = [(0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7)]
    cells = (inside[:-1, :-1, :-1].int() + inside[1:, :-1, :-1].int() + inside[:-1, 1:, :-1].int() + inside[1:, 1:, :-1].int() + inside[:-1, :-1, 1:].int() + inside[1:, :-1, 1:].int() + inside[:-1, 1:, 1:].int() + inside[1:, 1:, 1:].int())
    for z, y, x in ((cells > 0) & (cells < 8)).nonzero().tolist():
        vals = [v[z + a, y + b, x + c].item() for a, b, c in corners]; pts = []
        for e1, e2 in edges:
            if (vals[e1] > thr) != (vals[e2] > thr):
                t = (thr - vals[e1]) / (vals[e2] - vals[e1]); pts.append([corners[e1][i] + t * (corners[e2][i] - corners[e1][i]) for i in range(3)])
        ids[(z, y, x)] = len(verts); verts.append([(z + sum(p[0] for p in pts) / len(pts)), (y + sum(p[1] for p in pts) / len(pts)), (x + sum(p[2] for p in pts) / len(pts))])
    V = torch.tensor(verts, dtype=torch.float64) * h - 1.01; quads = []
    # each grid edge the surface crosses joins the 4 cells around it into one quad
    N = v.shape[0]
    for axis, ((a1, a2)) in enumerate((((0, 1, 0), (0, 0, 1)), ((1, 0, 0), (0, 0, 1)), ((1, 0, 0), (0, 1, 0)))):
        e = [0, 0, 0]; e[axis] = 1
        cross = inside[:N - e[0], :N - e[1], :N - e[2]] != inside[e[0]:, e[1]:, e[2]:]
        for g in cross.nonzero().tolist():
            ring = [tuple(g[i] - f * a1[i] - s * a2[i] for i in range(3)) for f, s in ((1, 1), (0, 1), (0, 0), (1, 0))]
            if all(c in ids for c in ring): quads.append(tuple(ids[c] for c in ring))
    Q = torch.tensor(quads); e1 = V[Q[:, 1]] - V[Q[:, 0]]; e2 = V[Q[:, 2]] - V[Q[:, 0]]; e3 = V[Q[:, 3]] - V[Q[:, 0]]
    area = 0.5 * torch.linalg.cross(e1, e2).norm(dim=1).sum() + 0.5 * torch.linalg.cross(e2, e3).norm(dim=1).sum()
    return V, len(quads) * 2, area.item()
true = 4 * math.pi * 0.7 ** 2
print(f"a sphere of radius 0.7, true area {true:.3f}. Field value = 0.7 - distance, so threshold t makes radius 0.7 - t")
print("grid   basic triangles   basic area / true   surface net triangles   surface net area / true   vertex distance error")
res = {}
for r in (16, 32, 64):
    v, h = field(r); f = basic_faces(v, 0.0); ar = f * h * h
    V, tris, a2 = surfnet(v, 0.0, h); err = (V.norm(dim=1) - 0.7).abs().max().item(); res[r] = (ar / true, a2 / true)
    print(f"{r:<6d} {f * 2:<17,d} {ar / true:<19.3f} {tris:<23,d} {a2 / true:<25.3f} {err:.4f}")
assert 1.4 < res[64][0] < 1.6 and abs(res[64][1] - 1) < 0.1
print("the blocky area stays near 3/2 however fine the grid is; the surface net converges to the truth")
print("\nthreshold moves the surface: on the same 32 grid")
v, h = field(32)
for t in (0.0, 0.1, 0.3, 0.6):
    print(f"threshold {t:<4}: {basic_faces(v, t) * 2:>6,d} triangles, expected radius {0.7 - t:.1f}")
assert basic_faces(v, 0.6) < basic_faces(v, 0.0)
# Cost of VAEDecodeHunyuan3D: octree_resolution + 1 per side, queried num_chunks at a time.
print("\noctree_resolution   grid points     decoder batches at num_chunks 8000")
for o in (64, 128, 256, 512):
    n = (o + 1) ** 3; print(f"{o:<19d} {n:<15,d} {math.ceil(n / 8000):,d}")
assert (256 + 1) ** 3 == 16974593
print("\nEmptyLatentHunyuan3Dv2 at resolution 3072: latent [1, 64, 3072], a list of 3072 tokens with no grid in it")
