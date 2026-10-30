# CU-211 lab: what a scale, a block size and a bit width cost, measured on a weight matrix.
# Run: python lab.py  (CPU only, a few seconds). Prints the same numbers every time.
# The weights are synthetic: Gaussian, std 0.02. In the "outliers" case we plant large values ourselves.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
g = torch.Generator().manual_seed(0)
N, K = 512, 1024
W = torch.randn(N, K, generator=g) * 0.02
Wo = W.clone(); n_out = N * K // 1000
Wo.view(-1)[torch.randperm(N * K, generator=g)[:n_out]] *= 30        # 0.1% of the entries made 30 times larger
X = torch.randn(K, 64, generator=g)

def rel(a, b): return ((a - b).norm() / a.norm()).item()
def absmax_round(w, qmax, dims):
    """symmetric absmax quantization: scale = max|w| / qmax, q = round(w / scale), result = q * scale"""
    scale = w.abs().amax(dim=dims, keepdim=True) / qmax
    return torch.round(w / scale).clamp(-qmax, qmax) * scale
def blocks(w, b): return w.reshape(w.shape[0], w.shape[1] // b, b)
def int_block(w, qmax, b): return absmax_round(blocks(w, b), qmax, (2,)).reshape(w.shape)
def fp16(x): return x.to(torch.float16).to(torch.float32)
def q8_0(w):
    """ggml quantize_row_q8_0_ref / dequantize_row_q8_0: blocks of 32, d = amax/127 stored as fp16, q = round(x / d)"""
    wb = blocks(w, 32); d = wb.abs().amax(dim=2, keepdim=True) / 127.0
    return (torch.round(wb * (1.0 / d)) * fp16(d)).reshape(w.shape)
def q4_0(w):
    """ggml quantize_row_q4_0_ref / dequantize_row_q4_0: blocks of 32, d = (signed value of largest magnitude) / -8, q = min(15, trunc(x / d + 8.5)), result (q - 8) * d"""
    wb = blocks(w, 32); mx = torch.gather(wb, 2, wb.abs().argmax(dim=2, keepdim=True)); d = mx / -8.0
    return ((torch.clamp(torch.trunc(wb * (1.0 / d) + 8.5), max=15) - 8) * fp16(d)).reshape(w.shape)
def fp8(w, dt, fmax, scaled=True):
    """per-tensor FP8 as in comfy_kitchen's eager quantize_per_tensor_fp8: clamp(x / scale) cast to FP8, scale = amax / format max"""
    scale = w.abs().max() / fmax if scaled else torch.tensor(1.0)
    return (w * (1.0 / scale)).clamp(-fmax, fmax).to(dt).to(torch.float32) * scale

# 1. The rounding error of a uniform grid with step s has RMS s / sqrt(12). Check it on int8, one scale for the whole matrix.
step = (W.abs().max() / 127).item(); err = (absmax_round(W, 127, (0, 1)) - W).pow(2).mean().sqrt().item()
print(f"int8, one scale: step {step:.3e}   predicted RMS error step/sqrt(12) {step / math.sqrt(12):.3e}   measured {err:.3e}")
assert abs(err / (step / math.sqrt(12)) - 1) < 0.05

# 2. Granularity and bit width. Relative error is |W - W_hat| / |W| (Frobenius). Output error is the same measure on W X.
fmts = [("int8, one scale", lambda w: absmax_round(w, 127, (0, 1)), 8 + 32 / (N * K)),
        ("int8, scale per row", lambda w: absmax_round(w, 127, (1,)), 8 + 32 / K),
        ("int8, scale per 32", lambda w: int_block(w, 127, 32), 8 + 16 / 32),
        ("GGUF Q8_0", q8_0, 8 + 16 / 32),
        ("int4, one scale", lambda w: absmax_round(w, 7, (0, 1)), 4 + 32 / (N * K)),
        ("int4, scale per row", lambda w: absmax_round(w, 7, (1,)), 4 + 32 / K),
        ("int4, scale per 32", lambda w: int_block(w, 7, 32), 4 + 16 / 32),
        ("GGUF Q4_0", q4_0, 4 + 16 / 32),
        ("FP8 E4M3, one scale", lambda w: fp8(w, torch.float8_e4m3fn, 448.0), 8 + 32 / (N * K)),
        ("FP8 E5M2, one scale", lambda w: fp8(w, torch.float8_e5m2, 57344.0), 8 + 32 / (N * K))]
print(f"\nweights: Gaussian std 0.02, {N}x{K}.  outliers: {n_out} entries (0.1%) multiplied by 30, largest |w| {W.abs().max():.3f} -> {Wo.abs().max():.3f}")
print("format                bits/weight   weight error: clean   with outliers   output error with outliers")
res = {}
for name, f, bpw in fmts:
    res[name] = (rel(W, f(W)), rel(Wo, f(Wo)), rel(Wo @ X, f(Wo) @ X))
    print(f"{name:21s} {bpw:<13.2f} {res[name][0]:<22.4f} {res[name][1]:<15.4f} {res[name][2]:.4f}")
assert res["int8, scale per 32"][1] < res["int8, scale per row"][1] < res["int8, one scale"][1]
assert res["FP8 E4M3, one scale"][1] < res["int8, one scale"][1] and res["int8, one scale"][0] < res["FP8 E4M3, one scale"][0]
r = res["int4, scale per 32"][0] / res["int8, scale per 32"][0]
print(f"\nclean data, scale per 32: int4 error / int8 error = {r:.1f}   the step ratio 127/7 = {127 / 7:.1f}")
assert 15 < r < 21

# 3. In the exact ggml Q4_0 code the largest value of a block is stored in code 0, so it comes back exactly (up to the fp16 scale).
wb = blocks(W, 32); mx = torch.gather(wb, 2, wb.abs().argmax(dim=2, keepdim=True)); back = torch.gather(blocks(q4_0(W), 32), 2, wb.abs().argmax(dim=2, keepdim=True))
print(f"Q4_0: largest-magnitude weight of each block, worst relative error after the round trip {((back - mx).abs() / mx.abs()).max():.2e}")

# 4. Why FP8 also needs a scale: E4M3 has a smallest value (2^-9 = 0.00195), so small weights lose their precision unless scaled up.
print("\nFP8 E4M3 error by weight size    std:   0.1000   0.0200   0.0040   0.0008")
rows = {"scale 1 (plain cast)": False, "scale = amax/448": True}
for name, sc in list(rows.items()):
    out = []
    for s in (0.1, 0.02, 0.004, 0.0008):
        w = torch.randn(N, K, generator=g) * s; out.append(rel(w, fp8(w, torch.float8_e4m3fn, 448.0, sc)))
    print(f"  {name:29s}       " + "   ".join(f"{e:.4f}" for e in out))
    rows[name] = out
assert rows["scale 1 (plain cast)"][3] > 0.5 and rows["scale = amax/448"][3] < 0.05

# 5. A scale per output row or per tensor factors out of the dot product, so an integer matmul can be rescaled afterwards.
sx = X.abs().max() / 127; Xq = torch.round(X / sx); sw = W.abs().amax(dim=1, keepdim=True) / 127; Wq = torch.round(W / sw)
y_int = (Wq.to(torch.int64) @ Xq.to(torch.int64)).to(torch.float32) * sw * sx; y_deq = (Wq * sw) @ (Xq * sx)
print(f"\nint8 matmul with int64 accumulation, then rescaled, against dequantize-then-multiply: largest difference {(y_int - y_deq).abs().max():.1e} on outputs of size {y_deq.abs().mean():.3f}")
assert (y_int - y_deq).abs().max() < 1e-3

# 6. Bits per weight from the published layouts, and what 1 billion weights occupy.
print("\nlayout                                       bits/weight   GiB per billion weights")
lay = [("fp16 or bf16", 16.0), ("ComfyUI float8_e4m3fn, scalar scale", 8.0), ("ComfyUI mxfp8, 8-bit scale per 32", 8 + 8 / 32),
       ("ComfyUI nvfp4, 8-bit scale per 16", 4 + 8 / 16), ("GGUF Q8_0, fp16 scale per 32", (2 + 32) * 8 / 32), ("GGUF Q4_0, fp16 scale per 32", (2 + 16) * 8 / 32),
       ("GGUF Q4_K, 144 bytes per 256", 144 * 8 / 256)]
for n, b in lay: print(f"{n:44s} {b:<13.2f} {1e9 * b / 8 / 2 ** 30:.2f}")
