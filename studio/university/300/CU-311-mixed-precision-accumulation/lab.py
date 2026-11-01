# CU-311 lab: where a sum loses numbers. A running sum in several formats, the dot product inside a matmul, and a toy gradient sum.
import torch
torch.manual_seed(0); torch.set_num_threads(1)
print("format   mantissa bits   spacing just above 1 (eps)   smallest normal   largest")
for n, d, m in (("fp16", torch.float16, 10), ("bf16", torch.bfloat16, 7), ("fp32", torch.float32, 23)):
    i = torch.finfo(d); print(f"{n:8s} {m:<15d} {i.eps:<28.3e} {i.tiny:<17.3e} {i.max:.3e}")
assert torch.finfo(torch.float16).eps == 2 ** -10
one, small = torch.tensor(1.0, dtype=torch.float16), torch.tensor(1e-4, dtype=torch.float16)
print(f"\n1.0 + 0.0001 in fp16 = {(one + small).item():.6f}    in fp32 = {(one.float() + small.float()).item():.6f}")
assert (one + small).item() == 1.0
def running(dt, x, n):
    s = torch.tensor(0.0, dtype=dt); a = torch.tensor(x, dtype=dt); stall = None
    for i in range(n):
        t = s + a
        if t == s and stall is None: stall = i
        s = t
    return s.item(), stall
print("\nadd 0.0001 again and again, rounding after each add. The true total is count x 0.0001")
print("format   count     result     stopped moving at")
for n, d in (("fp16", torch.float16), ("bf16", torch.bfloat16), ("fp32", torch.float32)):
    for c in (1000, 20000):
        r, st = running(d, 1e-4, c); print(f"{n:8s} {c:<9d} {r:<10.4f} {'never' if st is None else f'add number {st}'}")
r16, st16 = running(torch.float16, 1e-4, 20000); assert r16 < 1 and st16 is not None
assert running(torch.float32, 1e-4, 20000)[1] is None
print("\nthe same loss inside one matmul: a dot product of 4096 terms, summed in the format named")
g = torch.Generator().manual_seed(0); w = torch.randn(4096, generator=g) * 0.02; x = torch.randn(4096, generator=g) * 1.0
truth = (w.double() * x.double()).sum().item(); prods = (w.to(torch.float16) * x.to(torch.float16))
s16 = torch.tensor(0.0, dtype=torch.float16)
for v in prods: s16 = s16 + v
s32 = torch.tensor(0.0, dtype=torch.float32)
for v in prods: s32 = s32 + v.float()
print(f"true {truth:.5f}   fp16 terms summed in fp32 {s32.item():.5f}   fp16 terms summed in fp16 {s16.item():.5f}")
print(f"error: fp32 sum {abs(s32.item() - truth):.5f}   fp16 sum {abs(s16.item() - truth):.5f}")
assert abs(s16.item() - truth) > abs(s32.item() - truth)
print("\na toy gradient sum: 64 small batches on one weight tensor")
W = torch.randn(32, 32, generator=g); acc16 = torch.zeros_like(W, dtype=torch.float16); acc32 = torch.zeros_like(W); truth = torch.zeros_like(W, dtype=torch.float64)
for i in range(64):
    gr = torch.randn(32, 32, generator=g) * 1e-3 + (0.3 if i == 0 else 0.0)
    acc16 += gr.to(torch.float16); acc32 += gr; truth += gr.double()
e16 = ((acc16.double() - truth).norm() / truth.norm()).item(); e32 = ((acc32.double() - truth).norm() / truth.norm()).item()
print(f"relative error of the summed gradient: fp16 {e16:.2e}   fp32 {e32:.2e}")
assert e16 > 100 * e32
print("\ngradients small enough to vanish: the reason GradScaler exists")
for v in (1e-5, 1e-7, 1e-8):
    print(f"  {v:.0e} stored as fp16: {torch.tensor(v, dtype=torch.float16).item():.3e}   scaled by 65536 first, then back: {(torch.tensor(v * 65536, dtype=torch.float16).float() / 65536).item():.3e}")
assert torch.tensor(1e-8, dtype=torch.float16).item() == 0.0
