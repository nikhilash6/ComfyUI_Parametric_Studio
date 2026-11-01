# CU-374 lab: what a quantized file holds, what a loader has to do with it, and why merging goes first. Synthetic weights, real torch fp8.
import json, torch
torch.manual_seed(0); torch.set_num_threads(1); GB = 1024 ** 3
g = torch.Generator().manual_seed(0)
print("bytes per weight, and one billion weights")
for n, b in (("fp32", 4), ("fp16 or bf16", 2), ("fp8 e4m3 or e5m2", 1), ("GGUF Q8_0", 34 / 32), ("GGUF Q4_0", 18 / 32), ("nvfp4", 9 / 16)):
    print(f"  {n:18s} {b:.4f}  {1e9 * b / GB:5.2f} GB")
print("\nthe comfy_quant entry from QUANTIZATION.md: one small uint8 tensor holding JSON")
conf = {"format": "float8_e4m3fn"}; t = torch.tensor(list(json.dumps(conf).encode("utf-8")), dtype=torch.uint8)
back = json.loads(bytes(t.tolist()).decode("utf-8")); print(f"  stored as {t.dtype}, shape {tuple(t.shape)}, reads back as {back}")
assert back == conf
E4 = torch.float8_e4m3fn
def to_fp8(w):
    s = w.abs().max() / 448.0; return (w / s).clamp(-448, 448).to(E4), s
def from_fp8(q, s): return q.to(torch.float32) * s
def rel(a, b): return ((a - b).norm() / b.norm()).item()
A = torch.randn(512, 512, generator=g) * 0.02; B = torch.randn(512, 512, generator=g) * 0.02; Base = A * 0.8 + torch.randn(512, 512, generator=g) * 0.004; Lo = torch.randn(512, 512, generator=g) * 0.0005
print("\nwhat the loader does, step by step, with one fp8 layer")
q, s = to_fp8(A); print(f"  on disk or in memory: {q.dtype}, {q.numel() * q.element_size()} bytes, scale {s.item():.6f}")
out = from_fp8(q, s); print(f"  for a plain matmul: cast to fp32, multiply by the scale. weight error {rel(out, A):.4f}")
print("\nmerge first, quantize after, against the other way round")
print("  case                               weight error against the true unquantized merge")
true = 0.5 * A + 0.5 * B
qa, sa = to_fp8(A); qb, sb = to_fp8(B); merged_bad = 0.5 * from_fp8(qa, sa) + 0.5 * from_fp8(qb, sb); m, sm = to_fp8(merged_bad); bad = rel(from_fp8(m, sm), true)
m2, s2 = to_fp8(true); good = rel(from_fp8(m2, s2), true)
print(f"  50/50 merge, then quantize once     {good:.4f}")
print(f"  quantize both, merge, quantize      {bad:.4f}")
diff_true = A - Base; dq = from_fp8(*to_fp8(A)) - from_fp8(*to_fp8(Base))
print(f"  add-difference term (A - base), from unquantized:   0.0000")
print(f"  add-difference term (A - base), from fp8 inputs:    {rel(dq, diff_true):.4f}")
assert bad > good and rel(dq, diff_true) > 0.05
print("\na small LoRA-sized change on a weight: added before or after rounding")
tr = A + Lo; x, sx = to_fp8(tr); before = rel(from_fp8(x, sx), tr)
y, sy = to_fp8(A); after = rel(from_fp8(y, sy) + Lo, tr)
y2, sy2 = to_fp8(from_fp8(y, sy) + Lo); requant = rel(from_fp8(y2, sy2), tr)
print(f"  add, then quantize once             {before:.4f}")
print(f"  quantized weight, add at run time   {after:.4f}")
print(f"  quantized weight, add, requantize   {requant:.4f}")
assert requant > before
print("\ndoes the change survive? the size of the change against the size of the rounding")
change = (tr - A).norm().item(); rounding = (from_fp8(y, sy) - A).norm().item()
print(f"  change {change:.3f}   rounding error already in the file {rounding:.3f}")
print("\nunet_dtype's choice for a file whose weights are fp8, ported: fp8 stays if the card computes in fp8, or if double the size would not fit")
def keep_fp8(fp8_compute, params, room): return fp8_compute or params * 2 > room
for c, p, r in ((True, 6e9, 20e9), (False, 6e9, 20e9), (False, 6e9, 8e9)):
    print(f"  fp8 compute {str(c):5s} params {p:.0e} room {r:.0e}: {'stays fp8' if keep_fp8(c, p, r) else 'falls through to the other types'}")
assert keep_fp8(True, 6e9, 20e9) and not keep_fp8(False, 6e9, 20e9) and keep_fp8(False, 6e9, 8e9)
