# CU-333 lab: Wan 2.2 5B against the 14B pair, from comfy_extras/nodes_wan.py and comfy/sd.py (ComfyUI v0.43.0) and Wan's own configs (wan_ti2v_5B.py, wan_t2v_A14B.py).
import math
def shape(w, h, n, s, c): return (c, (n - 1) // 4 + 1, h // s, w // s)
def tokens(sh): return sh[1] * (sh[2] // 2) * (sh[3] // 2)    # patch (1, 2, 2) in both configs
print("model             VAE            latent at 832x480x81       values       tokens")
A = shape(832, 480, 81, 16, 48); B = shape(832, 480, 81, 8, 16)
for name, vae, sh in (("TI2V 5B", "4x16x16, 48ch", A), ("T2V A14B", "4x8x8, 16ch", B)):
    print(f"{name:17s} {vae:14s} {str(sh):26s} {math.prod(sh):<12,d} {tokens(sh):,d}")
print(f"the 14B route has {tokens(B) / tokens(A):.2f} times the tokens and {tokens(B) ** 2 / tokens(A) ** 2:.0f} times the attention pairs at the same picture size")
print(f"values per pixel of the picture: 5B {3 * 16 * 16 * 4 / 48:.0f}:1, 14B {3 * 8 * 8 * 4 / 16:.0f}:1 for long clips")
assert tokens(B) == 4 * tokens(A)
print("\ntransformer in Wan's configs:  TI2V 5B dim 3072, 30 layers, 24 heads   T2V A14B dim 5120, 40 layers, 40 heads, two of them")
# Both Wans share ModelSamplingSD3's shift: sigma = shift * t / (1 + (shift - 1) * t).
def shifted(t, s): return s * t / (1 + (s - 1) * t)
def grid(steps, s): return [shifted(1 - i / steps, s) for i in range(steps)]
print("\nshift changes where a plain even grid of 20 steps spends its time (a plain even grid: real samplers may space it differently)")
for s in (5.0, 8.0, 12.0):
    g = grid(20, s); print(f"shift {s:>4}: first sigmas {g[0]:.3f} {g[1]:.3f} {g[2]:.3f}, steps above 0.875: {sum(x >= 0.875 for x in g):>2d} of 20, steps below 0.5: {sum(x < 0.5 for x in g):>2d}")
assert sum(x >= 0.875 for x in grid(20, 12.0)) > sum(x >= 0.875 for x in grid(20, 5.0))
# The 14B split: Wan's config has boundary 0.875, sample_shift 12, 40 steps. On this plain grid, how many steps go to each model?
g = grid(40, 12.0); high = sum(x >= 0.875 for x in g); print(f"\n14B with its own numbers on the plain grid: boundary 0.875, {high} steps on the high-noise model, {40 - high} on the low-noise model")
# Wan22ImageToVideoLatent: the first dimension is fixed at 1 and batch_size is used only on the branch with a start image.
def node_shape(w, h, n, batch, start): return (batch if start else 1, 48, (n - 1) // 4 + 1, h // 16, w // 16)
print("\nWan22ImageToVideoLatent batch_size 4: no start image ->", node_shape(832, 480, 81, 4, False), " with a start image ->", node_shape(832, 480, 81, 4, True))
assert node_shape(832, 480, 81, 4, False)[0] == 1
# The VAE's decode estimate in comfy/sd.py has no frame count in it: 8000 * H * W * 16 * 16 * bytes.
for w, h in ((832, 480), (1280, 704)):
    print(f"decode estimate at {w}x{h}: {8000 * (h // 16) * (w // 16) * 256 * 2 / 1024 ** 3:.1f} GiB in bfloat16, any length")
