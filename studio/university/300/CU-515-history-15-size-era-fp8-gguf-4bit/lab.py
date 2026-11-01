# CU-515 lab: what each arrival of the size era buys. Real torch dtypes on one synthetic weight matrix, with an outlier test, and the arithmetic of file sizes. CPU, no model.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
W = torch.randn(512, 1024) * .02; Wo = W.clone(); idx = torch.rand(W.shape) < .001; Wo[idx] *= 30     # weights we made, not a real model's. Wo has 0.1% of its entries 30 times larger.
def err(a, b): return ((a - b).norm() / a.norm()).item()
def cast(w, dt): return w.to(dt).float()
def fp8(w, dt, scaled=True):
    s = w.abs().max() / torch.finfo(dt).max if scaled else torch.tensor(1.)        # the recalculate branch in comfy/quant_ops.py: largest value over the format's maximum
    return (w / s).to(dt).float() * s
def grid(w, qmax): s = w.abs().max() / qmax; return (w / s).round().clamp(-qmax, qmax) * s
def blocks(w, qmax, size):
    """One integer scale per run of `size` weights. A simple stand-in for a block format, not any format's exact code."""
    v = w.reshape(-1); n = v.numel() // size * size; b = v[:n].reshape(-1, size); s = b.abs().amax(1, keepdim=True).clamp_min(1e-12) / qmax; return ((b / s).round().clamp(-qmax, qmax) * s).reshape(w.shape)
rows = [("fp16", 16, cast(W, torch.float16), cast(Wo, torch.float16)), ("bf16", 16, cast(W, torch.bfloat16), cast(Wo, torch.bfloat16)),
        ("fp8 e4m3, scaled", 8, fp8(W, torch.float8_e4m3fn), fp8(Wo, torch.float8_e4m3fn)), ("fp8 e5m2, scaled", 8, fp8(W, torch.float8_e5m2), fp8(Wo, torch.float8_e5m2)),
        ("int8, one scale", 8, grid(W, 127), grid(Wo, 127)), ("int4, one scale", 4, grid(W, 7), grid(Wo, 7)), ("int4, a scale per 16", 4 + 16 / 16, blocks(W, 7, 16), blocks(Wo, 7, 16)), ("int4, a scale per 32", 4 + 16 / 32, blocks(W, 7, 32), blocks(Wo, 7, 32))]
print("format                 bits per weight   error, clean weights   error, with outliers")
res = {}
for name, bits, a, b in rows: res[name] = (err(W, a), err(Wo, b)); print(f"{name:<22s} {bits:<17.2f} {res[name][0]:<22.2e} {res[name][1]:.2e}")
assert res["int4, one scale"][0] > 5 * res["int8, one scale"][0] and res["int4, a scale per 16"][1] < res["int4, one scale"][1] / 2
print(f"\none outlier in a thousand: int4 with one scale goes from {res['int4, one scale'][0]:.3f} to {res['int4, one scale'][1]:.3f}, int4 with a scale per 16 from {res['int4, a scale per 16'][0]:.3f} to {res['int4, a scale per 16'][1]:.3f}")
# fp8 without its scale. E4M3 runs out of precision below its smallest values, so small weights die.
tiny = W * .04; print(f"fp8 e4m3 on weights of std {tiny.std().item():.4f}: plain cast error {err(tiny, fp8(tiny, torch.float8_e4m3fn, False)):.3f}, with a scale {err(tiny, fp8(tiny, torch.float8_e4m3fn)):.3f}")
assert err(tiny, fp8(tiny, torch.float8_e4m3fn, False)) > 5 * err(tiny, fp8(tiny, torch.float8_e4m3fn))
print(f"largest value: fp8 e4m3 {torch.finfo(torch.float8_e4m3fn).max:g}, fp8 e5m2 {torch.finfo(torch.float8_e5m2).max:g}, fp16 {torch.finfo(torch.float16).max:g}")
# File sizes. Only the weights, counted in GiB.
print("\nparameters   fp32 GiB   fp16 or bf16   fp8 or int8   4.5 bits")
for p in (1.3e9, 5e9, 14e9):
    g = [p * b / 8 / 2 ** 30 for b in (32, 16, 8, 4.5)]; print(f"{p / 1e9:<12.1f} {g[0]:<10.1f} {g[1]:<14.1f} {g[2]:<13.1f} {g[3]:.1f}")
assert abs(14e9 * 16 / 8 / 2 ** 30 - 26.08) < .01
