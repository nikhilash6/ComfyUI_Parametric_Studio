# CU-323 lab: perp_neg from comfy_extras/nodes_perpneg.py, ported and compared with the real function on a CPU. The arrows stand in for predictions.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
def perp_neg(pos_p, neg_p, empty, neg_scale, s):
    pos = pos_p - empty; neg = neg_p - empty
    perp = neg - ((neg * pos).sum() / (pos.norm() ** 2)) * pos
    return empty + s * (pos - perp * neg_scale)
def plain(pos_p, neg_p, s): return neg_p + (pos_p - neg_p) * s
E = torch.zeros(2, dtype=torch.float64); P = torch.tensor([1., 0.], dtype=torch.float64)
print("negative's angle to the positive   plain along   plain sideways   perp-neg along   perp-neg sideways")
R = {}
for ang in (0, 15, 45, 90, 135, 180):
    N = torch.tensor([math.cos(math.radians(ang)), math.sin(math.radians(ang))], dtype=torch.float64); a = plain(P, N, 7.); b = perp_neg(P, N, E, 1., 7.); R[ang] = (a, b)
    print(f"{ang:<34} {a[0].item():<13.2f} {a[1].item():<16.2f} {b[0].item():<16.2f} {b[1].item():.2f}")
assert abs(R[0][0][0].item() - 1) < 1e-9 and abs(R[0][1][0].item() - 7) < 1e-9
assert all(abs(R[a][1][0].item() - 7) < 1e-9 for a in R)    # perp-neg's reach along the positive never depends on the negative
print("\nat 0 degrees the two prompts are the same: plain cfg has nothing left to amplify, Perp-Neg still goes the full 7.")
print("at 180 degrees plain cfg goes to", round(R[180][0][0].item(), 1), "and Perp-Neg stays at", round(R[180][1][0].item(), 1), ": a negative pointing straight away from the positive adds nothing.")
# A batch: the dot product in the source sums over the whole tensor, not image by image.
g = torch.Generator().manual_seed(0); a = torch.randn(2, 16, dtype=torch.float64, generator=g); b = torch.randn(2, 16, dtype=torch.float64, generator=g); e = torch.zeros(2, 16, dtype=torch.float64)
pp = a - e; nn = b - e; perp_all = nn - ((nn * pp).sum() / pp.norm() ** 2) * pp
print(f"\nbatch of 2: the part left over is at right angles to the whole batch: {(perp_all * pp).sum().item():+.1e}. Image 1 alone: {(perp_all[0] * pp[0]).sum().item():+.2f}, image 2 alone: {(perp_all[1] * pp[1]).sum().item():+.2f}")
assert abs((perp_all * pp).sum().item()) < 1e-9 and abs((perp_all[0] * pp[0]).sum().item()) > 1e-3
print("\ncost: positive, negative and empty are all predicted each step: 3, not 2. Setting neg_scale to 0 drops the negative; adding cfg 1 also drops the empty.")
c = perp_neg(P, torch.tensor([.3, .9], dtype=torch.float64), E, 0., 7.); print("neg_scale 0 is plain cfg against the empty prompt:", torch.allclose(c, E + (P - E) * 7.))
assert torch.allclose(c, E + (P - E) * 7.)
