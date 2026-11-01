# CU-420 lab: the sums in comfy/weight_adapter, on small matrices. Each calculation follows calculate_weight in lora.py, loha.py, lokr.py and oft.py, and weight_decompose in base.py.
import torch
torch.set_num_threads(1); g = torch.Generator().manual_seed(0); R = lambda *s: torch.randn(*s, generator=g)
def factorization(dim, factor=-1):                # comfy/weight_adapter/base.py
    if factor > 0 and dim % factor == 0 and dim >= factor ** 2:
        m, n = factor, dim // factor
        return (n, m) if m > n else (m, n)
    if factor < 0: factor = dim
    m, n = 1, dim; length = m + n
    while m < n:
        nm = m + 1
        while dim % nm != 0: nm += 1
        nn = dim // nm
        if nm + nn > length or nm > factor: break
        m, n = nm, nn
    return (n, m) if m > n else (m, n)
for d, f, want in ((1024, -1, (32, 32)), (1024, 8, (8, 128)), (360, 8, (8, 45)), (127, 8, (1, 127))): assert factorization(d, f) == want
def lora(w, up, down, alpha, s):
    a = alpha / down.shape[0] if alpha is not None else 1.0; return w + s * a * (up @ down)
def loha(w, a1, b1, a2, b2, alpha, s):
    a = alpha / b1.shape[0] if alpha is not None else 1.0; return w + s * a * ((a1 @ b1) * (a2 @ b2))
def lokr(w, w1, w2, alpha, s, dim=None):
    a = alpha / dim if alpha is not None and dim is not None else 1.0; return w + s * a * torch.kron(w1, w2)
def dora(w, up, down, alpha, scale, s):            # dora_scale on the input axis: one value per column
    calc = w + (alpha / down.shape[0]) * (up @ down); calc = calc * (scale / (calc.norm(dim=0, keepdim=True) + torch.finfo(w.dtype).eps))
    return w + s * (calc - w)
D = 1280
print(f"how much each format stores for one {D} x {D} layer. Full weight: {D * D:,} numbers")
print("format                   numbers stored   share of full   largest rank it can reach")
rows = [("LoRA rank 8", 8 * (D + D), 8), ("LoRA rank 32", 32 * (D + D), 32), ("LoHa rank 8", 2 * 8 * (D + D), 64)]
for f in (4, 8, 16, 32):
    m, n = factorization(D, f); rows.append((f"LoKr factor {f} ({m} x {n})", m * m + n * n, D))
for name, p, rk in rows: print(f"{name:<24} {p:<16,} {p / D ** 2:<15.4f} {rk}")
print("\nmeasured rank of the change on a 96 x 96 layer, random factors (singular values above 1e-5 of the largest)")
rk = lambda M: int((torch.linalg.svdvals(M.double()) > 1e-5 * torch.linalg.svdvals(M.double())[0]).sum())
w0 = torch.zeros(96, 96)
a, b = R(96, 4), R(4, 96); r1 = rk(lora(w0, a, b, 4.0, 1.0))
a1, b1, a2, b2 = R(96, 4), R(4, 96), R(96, 4), R(4, 96); r2 = rk(loha(w0, a1, b1, a2, b2, 4.0, 1.0))
m, n = factorization(96, 8); r3 = rk(lokr(w0, R(m, m), R(n, n), None, 1.0))
print(f"LoRA rank 4: {r1}   LoHa rank 4: {r2} (up to 4 x 4)   LoKr {m} x {n}, full factors: {r3}, from {m * m + n * n} numbers against LoRA's {4 * 192}")
assert r1 == 4 and r2 == 16 and r3 == 96
print("\nthe price of that rank: a Kronecker product is one shape repeated. Relative error of the best possible fit to two 96 x 96 targets, about the same budget of numbers")
T_smooth = torch.kron(R(8, 8), R(12, 12)) + 0.05 * R(96, 96); T_low = R(96, 4) @ R(4, 96) + 0.05 * R(96, 96)
def best_kron(T, m, n):                            # Van Loan and Pitsianis: rearrange, then the top singular pair
    M = T.reshape(m, n, m, n).permute(0, 2, 1, 3).reshape(m * m, n * n); U, S, V = torch.linalg.svd(M, full_matrices=False)
    return torch.kron((U[:, 0] * S[0] ** 0.5).reshape(m, m), (V[0] * S[0] ** 0.5).reshape(n, n))
def best_rank(T, r):
    U, S, V = torch.linalg.svd(T, full_matrices=False); return (U[:, :r] * S[:r]) @ V[:r]
err = lambda T, A: ((T - A).norm() / T.norm()).item()
print("target                  LoKr 8 x 12 (208 numbers)   LoRA rank 1 (192 numbers)")
e = {}
for name, T in (("made of a Kronecker", T_smooth), ("made of rank 4", T_low)):
    e[name] = (err(T, best_kron(T, 8, 12)), err(T, best_rank(T, 1))); print(f"{name:<23} {e[name][0]:<27.3f} {e[name][1]:.3f}")
assert e["made of a Kronecker"][0] < e["made of a Kronecker"][1] and e["made of rank 4"][0] > 0.3
print("\nalpha: the same factors, scale alpha / rank")
print("format and file            alpha   scale")
print(f"{'LoRA rank 8':<26} 8       1.0\n{'LoRA rank 8':<26} 1       0.125\n{'LoRA rank 8, no alpha':<26} none    1.0\n{'LoKr, full w1 and w2':<26} 1       1.0  (no rank to divide by: alpha is ignored)\n{'OFT':<26} 1       norm limit, not a scale")
w = R(32, 32); w1, w2 = R(4, 4), R(8, 8)
assert torch.equal(lokr(w, w1, w2, 1.0, 1.0), lokr(w, w1, w2, 4.0, 1.0))
print("\nDoRA: the file also stores a size for each column. Column sizes of a 64 x 64 weight after the patch")
W = R(64, 64) * 0.1; up, down = R(64, 4) * 0.05, R(4, 64) * 0.05; scale = W.norm(dim=0, keepdim=True) * 1.5
print("strength   mean column size   wanted size   mean size of the LoRA version")
ds = {}
for s in (0.0, 0.5, 1.0):
    a = dora(W, up, down, 4.0, scale, s); b = lora(W, up, down, 4.0, s); ds[s] = a.norm(dim=0).mean().item()
    print(f"{s:<10} {a.norm(dim=0).mean().item():<18.4f} {scale.mean().item():<13.4f} {b.norm(dim=0).mean().item():.4f}")
assert abs(ds[1.0] - scale.mean().item()) < 1e-3
print("\nOFT: the change is a rotation of the weight, built from a skew-symmetric block. It keeps the size of each row group")
q = R(8, 8) * 0.1; q = q - q.T; I = torch.eye(8); r = (I + q) @ torch.linalg.inv(I - q); W8 = R(8, 32)
print(f"rotation check |R Rt - I|: {(r @ r.T - I).abs().max().item():.1e}   weight size before {W8.norm().item():.4f}, after {(r @ W8).norm().item():.4f}")
assert (r @ r.T - I).abs().max() < 1e-4 and abs((r @ W8).norm() - W8.norm()) < 1e-3
print("\nwhat TrainLoraNode's rank widget means, per algorithm, for a 1280 x 1280 layer at rank 8")
print("algorithm   rank widget used as   result")
print(f"LoRA        rank                  up 1280 x 8, down 8 x 1280: {2 * 8 * 1280:,} numbers")
print(f"LoHa        rank                  two such pairs: {2 * 2 * 8 * 1280:,} numbers")
m, n = factorization(1280, 8); print(f"LoKr        factor                w1 {m} x {m}, w2 {n} x {n}: {m * m + n * n:,} numbers")
bs, bn = factorization(1280, 8); print(f"OFT         factor                {bn} blocks of {bs} x {bs}: {bn * bs * bs:,} numbers")
