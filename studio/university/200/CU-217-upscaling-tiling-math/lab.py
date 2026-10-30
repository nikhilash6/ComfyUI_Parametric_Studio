# CU-217 lab: tile positions, overlap, feathering and what tiling costs, following comfy/utils.py (tiled_scale_multidim) and comfy/sd.py (decode_tiled_).
# Run: python lab.py  (CPU only, a few seconds). Prints the same numbers every time.
import itertools, math, torch
import torch.nn.functional as F
torch.manual_seed(0); torch.set_num_threads(1)
g = torch.Generator().manual_seed(0)

def plan(D, S, O):
    """tile starts and lengths along one side: starts = range(0, D - O, S - O) when D > S, each tile cut off at the border (comfy/utils.py)"""
    starts = list(range(0, D - O, S - O)) if D > S else [0]
    return starts, [min(S, D - p) for p in starts]
def count(D, S, O):
    """get_tiled_scale_steps for one side: 1 if D <= S, else ceil((D - O) / (S - O))"""
    return 1 if D <= S else math.ceil((D - O) / (S - O))
def work(D, S, O): return sum(plan(D, S, O)[1]) / D                       # pixels fed to the model along one side, relative to D

# 1. Positions and counts.
for D, S, O in ((1024, 512, 64), (1536, 512, 64), (960, 512, 64)):
    st, ln = plan(D, S, O); print(f"side {D}, tile {S}, overlap {O}: starts {st}, lengths {ln}, {len(st)} tiles")
assert all(count(D, S, O) == len(plan(D, S, O)[0]) for D in range(100, 700, 7) for S in (64, 128, 256) for O in (0, 8, 32) if S > O)
print("ceil((D - O) / (S - O)) agrees with the number of tile starts for every D from 100 to 700, tiles of 64, 128 and 256, overlaps 0, 8 and 32")

# 2. ImageUpscaleWithModel uses tiles of 512 with an overlap of 32. Tiles per side and the extra work, by input side.
print("\ninput side   tiles per side   tiles   pixels fed to the model / pixels in the image")
for D in (512, 768, 1024, 2048):
    n = count(D, 512, 32); print(f"{D:<12d} {n:<16d} {n * n:<7d} {work(D, 512, 32) ** 2:.3f}")

# 3. VAEDecodeTiled at its defaults (tile 512, overlap 64) on a 1024 x 1024 image with an 8x VAE: a 128 x 128 latent, tile 64, overlap 8.
#    decode_tiled_ runs three tilings, (tile/2, 2 tile), (2 tile, tile/2) and (tile, tile), and averages the three results.
L, T, O = 128, 64, 8; tilings = ((T // 2, T * 2), (T * 2, T // 2), (T, T)); calls, area = [], 0
for tx, ty in tilings:
    calls.append(count(L, tx, O) * count(L, ty, O)); area += work(L, tx, O) * work(L, ty, O) * L * L
print(f"\nVAEDecodeTiled on a 1024 x 1024 image: latent {L}x{L}, tiles {tilings}, decoder calls {calls}, {sum(calls)} in all, against {calls[2]} for the (64, 64) tiling alone")
print(f"latent positions decoded: {area:,.0f} for {L * L:,d} in the latent, {area / (L * L):.2f} times the work of one untiled pass")

# 4. Why overlap and feathering matter. A small decoder: three 3x3 convolutions and a 1x1, then 2x nearest upsampling. Its receptive field reaches 3 latent
#    pixels, and zero padding at a tile edge hides the neighbours, so output near a tile edge is wrong. Compare tiled output with the untiled output.
C = 8
w1 = torch.randn(C, 4, 3, 3, generator=g) * 0.12; w2 = torch.randn(C, C, 3, 3, generator=g) * 0.10; w3 = torch.randn(C, C, 3, 3, generator=g) * 0.10; w4 = torch.randn(3, C, 1, 1, generator=g) * 0.5
def dec(x):
    h = torch.tanh(F.conv2d(x, w1, padding=1)); h = torch.tanh(F.conv2d(h, w2, padding=1)); h = torch.tanh(F.conv2d(h, w3, padding=1))
    return F.interpolate(F.conv2d(h, w4), scale_factor=2, mode="nearest")
def tiled_scale(x, fn, tile, overlap, up, out_ch, feather=True):
    """comfy/utils.py tiled_scale_multidim for 2D: tiles at `plan` positions, a linear ramp of length overlap * up at both ends of every tile, weighted sum divided by summed weights"""
    H, W = x.shape[2:]; dims = (H, W)
    if H <= tile[0] and W <= tile[1]: return fn(x)
    out = torch.zeros(1, out_ch, H * up, W * up); div = torch.zeros(1, 1, H * up, W * up)
    for it in itertools.product(*[plan(S, t, overlap)[0] for S, t in zip(dims, tile)]):
        s_in = x; ups = []
        for d in range(2):
            pos = it[d]; l = min(tile[d], dims[d] - pos); s_in = s_in.narrow(d + 2, pos, l); ups.append(pos * up)
        ps = fn(s_in); mask = torch.ones(1, 1, *ps.shape[2:])
        if feather:
            for d in range(2, 4):
                fe = round(overlap * up)
                if fe >= mask.shape[d]: continue
                for t in range(fe): a = (t + 1) / fe; mask.narrow(d, t, 1).mul_(a); mask.narrow(d, mask.shape[d] - 1 - t, 1).mul_(a)
        o, od, pv, mv = out, div, ps, mask
        for d in range(2):
            l = min(pv.shape[d + 2], o.shape[d + 2] - ups[d]); o = o.narrow(d + 2, ups[d], l); od = od.narrow(d + 2, ups[d], l)
            if l < pv.shape[d + 2]: pv = pv.narrow(d + 2, 0, l); mv = mv.narrow(d + 2, 0, l)
        o.add_(pv * mv); od.add_(mv)
    return out / div
x = F.avg_pool2d(torch.randn(1, 4, 68, 68, generator=g), 5, stride=1); x = x / x.std(); truth = dec(x); sd = truth.std().item()
print(f"\nlatent 64x64, tile 32, receptive field 3 latent pixels. Largest error of the tiled output against the untiled output, as a multiple of the output's standard deviation ({sd:.3f})")
print("overlap   tiles   pixels fed in / pixels   plain average   feathered (ComfyUI's mask)   three tilings averaged")
res = {}
for O in (0, 2, 4, 8):
    plain = tiled_scale(x, dec, (32, 32), O, 2, 3, feather=False); feath = tiled_scale(x, dec, (32, 32), O, 2, 3)
    three = (tiled_scale(x, dec, (16, 64), O, 2, 3) + tiled_scale(x, dec, (64, 16), O, 2, 3) + feath) / 3
    e = [((y - truth).abs().max().item() / sd) for y in (plain, feath, three)]; res[O] = e
    print(f"{O:<9d} {count(64, 32, O) ** 2:<7d} {work(64, 32, O) ** 2:<22.3f} {e[0]:<15.2f} {e[1]:<28.2f} {e[2]:.2f}")
assert res[8][1] < res[8][0] / 3 and res[8][2] < res[8][1] and res[8][1] < res[2][1] and res[0][0] == res[0][1]
