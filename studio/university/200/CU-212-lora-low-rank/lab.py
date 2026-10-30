# CU-212 lab: what a LoRA is, how ComfyUI applies it, and what happens when the base weights are stored in a low-precision format.
# Run: python lab.py  (CPU only, about 10 s). Prints the same numbers every time.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
g = torch.Generator().manual_seed(0)

# 1. Parameter counts: a d_out x d_in weight has d_out*d_in numbers, and a rank-r update B A has r*(d_out + d_in).
print("layer (out x in)   rank   full weights   LoRA weights   LoRA / full")
for o, i in ((320, 320), (1024, 1024), (4096, 4096)):
    for r in (4, 16, 128): print(f"{o} x {i:<10d}   {r:<5d}  {o * i:<13,d}  {r * (o + i):<13,d}  {r * (o + i) / (o * i):.4f}")

# 2. The update B A cannot have rank above r, however large the layer.
B = torch.randn(256, 8, generator=g, dtype=torch.float64); A = torch.randn(8, 256, generator=g, dtype=torch.float64)
s = torch.linalg.svdvals(B @ A); rank = int((s > 1e-10 * s[0]).sum())
print(f"\nB (256x8) times A (8x256) is a 256x256 matrix; singular values above 1e-10 of the largest: {rank}")
assert rank == 8

# 3. Merging the update into the weight gives the same output as adding it to the layer's output (the "bypass" form).
def merge(W, up, down, alpha, strength):
    """comfy/weight_adapter/lora.py, LoRAAdapter.calculate_weight: scale = alpha / rank, or 1.0 when the file has no alpha; W += strength * scale * (up @ down)"""
    return W + strength * (alpha / down.shape[0] if alpha is not None else 1.0) * (up @ down)
print("\nmerged W x against W x + strength * scale * up (down x), largest absolute difference over the outputs")
for dt in (torch.float32, torch.float64):
    W = torch.randn(128, 96, generator=g, dtype=dt) * 0.05; up = torch.randn(128, 8, generator=g, dtype=dt) * 0.1; down = torch.randn(8, 96, generator=g, dtype=dt) * 0.1
    x = torch.randn(96, 32, generator=g, dtype=dt); diffs = []
    for strength in (0.5, 1.0, 2.0): diffs.append((merge(W, up, down, 8.0, strength) @ x - (W @ x + strength * (up @ (down @ x)))).abs().max().item())
    d1 = (merge(W, up, down, 8.0, 1.0) - W) @ x; d2 = (merge(W, up, down, 8.0, 2.0) - W) @ x
    up2 = torch.randn(128, 4, generator=g, dtype=dt) * 0.1; down2 = torch.randn(4, 96, generator=g, dtype=dt) * 0.1
    ab = merge(merge(W, up, down, 8.0, 1.0), up2, down2, 4.0, 0.7); ba = merge(merge(W, up2, down2, 4.0, 0.7), up, down, 8.0, 1.0)
    print(f"{str(dt):14s} strength 0.5, 1, 2: {diffs[0]:.1e} {diffs[1]:.1e} {diffs[2]:.1e}   doubling the strength doubles the change: {(d2 - 2 * d1).abs().max():.1e}   two LoRAs in either order: {(ab - ba).abs().max():.1e}")
    assert max(diffs) < (1e-5 if dt == torch.float32 else 1e-12)
print(f"scale alpha/r: alpha 8, r 8 -> {8 / 8}   alpha 1, r 8 -> {1 / 8}   file with no alpha -> {1.0} whatever the rank")

# 4. Initialisation. The product B A must start at zero. One factor is zero, so at step 0 only the other one gets a gradient.
din, dout, r = 64, 96, 8
Wt = torch.randn(dout, din, generator=g) * 0.1; X = torch.randn(din, 256, generator=g)
def loss(up, down): return (((up @ down) - Wt) @ X).pow(2).mean()
def init_paper(): return torch.zeros(dout, r), torch.randn(r, din, generator=g) / math.sqrt(din)            # B = 0, A Gaussian (Hu et al. 2021, section 4.1)
def init_comfy():                                                                                        # comfy/weight_adapter/lora.py, create_train: up Kaiming-uniform, down 0
    up = torch.empty(dout, r); torch.nn.init.kaiming_uniform_(up, a=5 ** 0.5); return up, torch.zeros(r, din)
print("\ninit                    |B A| at start   |grad up|   |grad down|   relative error after 300 Adam steps")
for name, f in (("B = 0, A Gaussian", init_paper), ("up random, down = 0", init_comfy)):
    up, down = [t.requires_grad_() for t in f()]; start = (up @ down).norm().item()
    loss(up, down).backward(); gu, gd = up.grad.norm().item(), down.grad.norm().item(); opt = torch.optim.Adam([up, down], 0.01)
    for _ in range(300): l = loss(up, down); opt.zero_grad(); l.backward(); opt.step()
    print(f"{name:23s} {start:<16.4f} {gu:<10.4f} {gd:<12.4f} {((up @ down - Wt).norm() / Wt.norm()).item():.4f}")
    assert start == 0 and min(gu, gd) == 0 and max(gu, gd) > 0

# 5. What a rank-r update can represent. Fit B A to a target update T by gradient descent on |B A - T|, and compare with the best
#    rank-r matrix that exists (the truncated SVD, Eckart-Young). One target is rank 4 plus a little noise; the other is a full-rank random matrix.
def fit(T, r, steps=3000):
    gg = torch.Generator().manual_seed(r)
    up = (torch.randn(T.shape[0], r, generator=gg) * 0.1).requires_grad_(); down = (torch.randn(r, T.shape[1], generator=gg) * 0.1).requires_grad_(); opt = torch.optim.Adam([up, down], 0.01)
    for _ in range(steps): l = (up @ down - T).pow(2).sum(); opt.zero_grad(); l.backward(); opt.step()
    return ((up @ down - T).norm() / T.norm()).item()
T4 = torch.randn(96, 4, generator=g) @ torch.randn(4, 64, generator=g) / 4; T4 = T4 + 0.02 * T4.std() * torch.randn(96, 64, generator=g)
TF = torch.randn(96, 64, generator=g)
print("\nrelative error |B A - T| / |T| for a 96 x 64 update T")
print("rank   T = rank 4 + noise: trained   best possible     T = full rank: trained   best possible")
rows = {}
for r in (1, 2, 4, 8, 16, 32):
    cells = []
    for T in (T4, TF):
        sv = torch.linalg.svdvals(T.double()); best = (sv[r:].pow(2).sum().sqrt() / sv.pow(2).sum().sqrt()).item(); got = fit(T, r); cells += [got, best]
        assert got > best - 1e-4
    rows[r] = cells; print(f"{r:<6d} {cells[0]:<28.4f}{cells[1]:<17.4f} {cells[2]:<24.4f}{cells[3]:.4f}")
assert rows[4][0] < 0.05 and rows[2][0] > 0.5 and rows[32][2] > 0.3

# 6. Merging into base weights that are stored in a low-precision format, then storing again (what ComfyUI does when the model is
#    loaded with the LoRA merged). Weights N(0, 0.02^2); the update B A is scaled to the given standard deviation.
#    bf16 and fp16 round to nearest. For FP8 we store a per-tensor scale (amax / 448), recalculate it after the merge, and compare rounding to
#    nearest with stochastic rounding, which comfy/float.py uses for FP8 (our version rounds up with probability equal to the distance past the lower neighbour).
def e4m3_nearest(x): return x.clamp(-448.0, 448.0).to(torch.float8_e4m3fn).to(torch.float32)
def e4m3_stochastic(x, gen):
    a = x.abs(); e = torch.floor(torch.log2(a.clamp(min=2.0 ** -6))).clamp(min=-6.0); sp = 2.0 ** (e - 3)       # spacing of the E4M3 grid
    lo = torch.floor(a / sp) * sp; up = (torch.rand(a.shape, generator=gen) < (a - lo) / sp).float()
    return torch.sign(x) * (lo + up * sp).clamp(max=448.0)
N, K = 512, 1024; W0 = torch.randn(N, K, generator=g) * 0.02; s0 = W0.abs().max() / 448
bases = {"fp16": W0.to(torch.float16).float(), "bf16": W0.to(torch.bfloat16).float(), "FP8": e4m3_nearest(W0 / s0) * s0}
gen = torch.Generator().manual_seed(123); Xo = torch.randn(K, 64, generator=g)
print("\nupdate std   stored as   rounding     share of the update kept   RMS error / update RMS   output correlation")
kept = {}; same = {}
for dstd in (1e-5, 1e-4, 1e-3):
    delta = torch.randn(N, 8, generator=g) @ torch.randn(8, K, generator=g); delta = delta * (dstd / delta.std())
    for name, base in bases.items():
        merged = base + delta
        if name == "FP8":
            s1 = merged.abs().max() / 448; outs = {"nearest": e4m3_nearest(merged / s1) * s1, "stochastic": e4m3_stochastic(merged / s1, gen) * s1}
            same[dstd] = (e4m3_nearest(merged / s1) == e4m3_nearest(base / s0)).float().mean().item()
        else: outs = {"nearest": merged.to(torch.float16 if name == "fp16" else torch.bfloat16).float()}
        for rnd, o in outs.items():
            got = o - base; share = ((got * delta).sum() / (delta * delta).sum()).item(); yd, yg = delta @ Xo, got @ Xo; kept[(dstd, name, rnd)] = share
            print(f"{dstd:<12g} {name:11s} {rnd:12s} {share:<26.3f} {((got - delta).pow(2).mean().sqrt() / delta.pow(2).mean().sqrt()).item():<24.2f} {((yd * yg).sum() / (yd.norm() * yg.norm())).item():.3f}")
assert kept[(1e-4, "FP8", "nearest")] < 0.5 and abs(kept[(1e-4, "FP8", "stochastic")] - 1) < 0.05 and kept[(1e-3, "bf16", "nearest")] > 0.99
print(f"\nFP8, rounding to nearest: share of weights whose 8-bit code is unchanged by the merge, for update std 1e-05, 0.0001, 0.001: {same[1e-5]:.3f} {same[1e-4]:.3f} {same[1e-3]:.3f}")
assert same[1e-4] > 0.7
