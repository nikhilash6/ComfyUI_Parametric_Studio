# CU-307 lab: the same sphere as a voxel grid, an SDF, a mesh and Gaussians. What each costs and what each gets wrong. CPU, instant.
import math, torch
torch.set_num_threads(1)
true = 4 * math.pi; R = 1.0
def grid(res):
    c = (torch.arange(res) + 0.5) / res * 3 - 1.5; z, y, x = torch.meshgrid(c, c, c, indexing="ij"); return (x * x + y * y + z * z).sqrt() - R, 3 / res
def exposed(inside):
    p = torch.nn.functional.pad(inside.float(), (1, 1, 1, 1, 1, 1)); n = 0
    for dim in range(3): n += int((p.diff(dim=dim) != 0).sum())
    return n
print("grid    voxels stored   inside voxels   near-surface voxels   blocky area / true")
out = {}
for res in (32, 64, 128):
    d, h = grid(res); ins = d < 0; band = d.abs() < h; a = exposed(ins) * h * h; out[res] = a / true
    print(f"{res:<7d} {res ** 3:<15,d} {int(ins.sum()):<15,d} {int(band.sum()):<21,d} {a / true:.3f}")
assert all(1.45 < v < 1.55 for v in out.values())
print("the area of the blocks stays near 3/2 of the truth. A finer grid gives smaller stairs, not less stair")
# Why 3/2: the stairs project onto the 3 axes, and each axis sees the sphere's shadow twice. 6 pi r^2 over 4 pi r^2.
print(f"exact limit: 6 pi r^2 / 4 pi r^2 = {6 * math.pi / true:.3f}")
# The draft's lab counted faces of a shell, both walls: that is why it printed about 3, twice 3/2.
d, h = grid(32); shell = d.abs() < h / 2; print(f"counting both walls of a thin shell, as the first version of this lab did: ratio {exposed(shell) * h * h / true:.2f}")
# An SDF stores a distance, so a bit of arithmetic finds the surface between grid points. Linear crossing on a coarse grid.
print("\nsurface radius recovered along a ray by linear interpolation between SDF samples, against the staircase answer")
for res in (8, 16, 32):
    s = torch.linspace(0, 1.5, res + 1); f = s - R; i = (f >= 0).nonzero()[0].item(); t = -f[i - 1] / (f[i] - f[i - 1]); print(f"{res:>3d} samples: SDF crossing {s[i - 1] + t * (s[i] - s[i - 1]):.4f}   occupancy only {s[i]:.4f}")
# Memory: bytes for a stored field, a mesh and splats, at matched detail. Mesh and splat counts follow the surface, a grid follows the volume.
print("\nresolution   full grid, 1 float   thin band, coords + 1 float   triangle mesh, about   Gaussians at band count, 14 floats")
for res in (64, 256, 1024):
    band = int(6 * (res * 2 / 3) ** 2 * math.pi / 3 * 1.0); print(f"{res:<12d} {4 * res ** 3 / 1024 ** 2:<20.1f} {16 * band / 1024 ** 2:<29.1f} {(band * 12 + 2 * band * 12) / 1024 ** 2:<22.1f} {14 * 4 * band / 1024 ** 2:.1f}  MiB")
# Gaussian: one blob's value along a line, opacity weighted. Soft: there is no edge to find.
print("\none Gaussian of scale 0.1, value at a distance:", [round(math.exp(-(x / 0.1) ** 2 / 2), 3) for x in (0, 0.1, 0.2, 0.3)])
