# CU-331 lab: the numbers behind the LTX-2.5 graph, ported from comfy_extras/nodes_lt.py, nodes_lt_audio.py, nodes.py and comfy/sd.py (ComfyUI v0.43.0).
import math, torch
torch.set_num_threads(1)
# 1. EmptyLTXVLatentVideo
def ltx_shape(w, h, n): return (128, (n - 1) // 8 + 1, h // 32, w // 32)
for w, h, n in ((832, 480, 81), (960, 544, 145), (1920, 1088, 121)):
    s = ltx_shape(w, h, n); print(f"{w}x{h}, {n} frames -> latent {s}, one token per position: {s[1] * s[2] * s[3]:,d} tokens")
assert ltx_shape(832, 480, 81) == (128, 11, 15, 26)
# 2. The sigma list in the graph, from ManualSigmas. The same list is DISTILLED_SIGMA_VALUES in Lightricks' own code.
S = [1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0]
print(f"\ndistilled list: {len(S) - 1} steps, so {len(S) - 1} model calls at CFG 1")
print("step sizes:", " ".join(f"{a - b:.4f}" for a, b in zip(S, S[1:])))
print(f"share of the noise range removed by the first 4 steps: {(S[0] - S[4]) / S[0]:.3f}, by the last 2: {(S[-3] - S[-1]) / S[0]:.3f}")
assert abs(S[0] - S[4] - 0.025) < 1e-9
# 3. What LTXVScheduler would do instead, from its code. The shift rises with the number of latent positions.
def ltxv_scheduler(steps, tokens=4096, max_shift=2.05, base_shift=0.95, stretch=True, terminal=0.1):
    sig = torch.linspace(1.0, 0.0, steps + 1)
    mm = (max_shift - base_shift) / (4096 - 1024); b = base_shift - mm * 1024; shift = tokens * mm + b
    sig = torch.where(sig != 0, math.exp(shift) / (math.exp(shift) + (1 / sig - 1)), torch.zeros(1))
    if stretch:
        nz = sig != 0; one = 1.0 - sig[nz]; scale = one[-1] / (1.0 - terminal); sig[nz] = 1.0 - one / scale
    return shift, sig
for tok in (1024, 4096, 4290):
    sh, s = ltxv_scheduler(8, tok); print(f"LTXVScheduler 8 steps, {tok:>5d} positions: shift {sh:.3f}, sigmas " + " ".join(f"{x:.3f}" for x in s.tolist()))
assert abs(ltxv_scheduler(8, 4096)[1][-2].item() - 0.1) < 1e-5
# 4. VAEDecodeTiled turns pixel and frame sizes into latent sizes. Graph values: tile 512, overlap 64, temporal 64, temporal overlap 8.
def tiled(tile, ov, t, tov, sc=32, tc=8):
    if tile < ov * 4: ov = tile // 4
    if t < tov * 2: tov = tov // 2
    t = max(2, t // tc); tov = max(1, min(t // 2, tov // tc))
    return tile // sc, ov // sc, t, tov
print("\nVAEDecodeTiled(512, 64, 64, 8) on an 8 x 32 x 32 VAE: spatial tile %d, overlap %d latent units, temporal tile %d, overlap %d latent frames" % tiled(512, 64, 64, 8))
assert tiled(512, 64, 64, 8) == (16, 2, 8, 1)
# 5. The VAE's own memory estimate, from comfy/sd.py, for bfloat16 (2 bytes). tile clamps the shape, as _tile_bounded_shape does.
def decode_gb(T, H, W, tile=None):
    if tile: T, H, W = min(T, tile[0]), min(H, tile[1]), min(W, tile[1])
    return 1200 * T * H * W * (8 * 8 * 8) * 2 / 1024 ** 3
for w, h, n in ((832, 480, 81), (1920, 1088, 121)):
    _, T, H, W = ltx_shape(w, h, n); print(f"decode estimate {w}x{h} {n} frames: whole {decode_gb(T, H, W):.1f} GiB, with the graph's tiles {decode_gb(T, H, W, (8, 16)):.1f} GiB")
# 6. Audio latents. Default config in causal_audio_autoencoder.py: 16000 Hz, hop 160, 64 mel bins, 8 channels, downsample 4. A real checkpoint can override these.
per_sec = 16000 / 160 / 4; n = round(81 / 24 * per_sec)
print(f"\nLTXVEmptyLatentAudio with those defaults: {per_sec:.0f} latent frames a second, 81 frames at 24 fps -> [1, 8, {n}, {64 // 4}]")
assert n == 84
# 7. CFG 1: sampling_function skips the unconditional pass, so the negative prompt is never run.
print("CFGGuider cfg 1.0: math.isclose(cond_scale, 1.0) is", math.isclose(1.0, 1.0), "so the negative prompt in this graph does nothing")
