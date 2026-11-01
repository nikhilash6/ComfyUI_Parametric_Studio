# CU-304 lab: how big the score matrix is, and two exact ways not to hold all of it. A third, lossy, for contrast.
# The 8-bit part is a toy of ours, to show that low precision changes the numbers. It is not SageAttention's algorithm.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
MB = 1024 ** 2
print("score matrix for one head and one batch row, fp16 (2 bytes)")
for n in (1024, 4096, 16384, 65536): print(f"  {n:6d} tokens: {n * n * 2 / MB:8.0f} MB")
assert 65536 ** 2 * 2 / MB == 8192
print("  double the tokens: x4")
def standard(Q, K, V, scale):
    return torch.softmax(Q @ K.transpose(-2, -1) * scale, -1) @ V
def sliced(Q, K, V, scale, steps):
    """attention_split's idea: score a slice of the queries, keep its answer, drop its scores."""
    return torch.cat([torch.softmax(q @ K.transpose(-2, -1) * scale, -1) @ V for q in Q.chunk(steps, 1)], 1)
def online(Q, K, V, scale, t):
    """FlashAttention's online softmax: walk K and V in blocks and keep a running max, sum and output per query."""
    b, n, d = Q.shape; m = torch.full((b, n), -math.inf); l = torch.zeros(b, n); o = torch.zeros(b, n, d)
    for s in range(0, K.shape[1], t):
        S = Q @ K[:, s:s + t].transpose(-2, -1) * scale; new = torch.maximum(m, S.max(-1).values)
        c = torch.where(torch.isinf(m), torch.zeros_like(m), torch.exp(m - new)); E = torch.exp(S - new.unsqueeze(-1))
        l = l * c + E.sum(-1); o = o * c.unsqueeze(-1) + E @ V[:, s:s + t]; m = new
    return o / l.unsqueeze(-1)
n, d = 512, 64; g = torch.Generator().manual_seed(0)
Q, K, V = (torch.randn(1, n, d, generator=g, dtype=torch.float64) for _ in range(3)); sc = 1 / math.sqrt(d)
Q, K, V = Q.float(), K.float(), V.float(); ref = standard(Q.double(), K.double(), V.double(), sc).float()
print(f"\n{n} tokens, {d} dimensions: largest difference from the full calculation, in fp32")
print(f"  {'method':28s} {'scores held at once':>20s} {'difference':>12s}")
print(f"  {'full matrix':28s} {n * n:20d} {(standard(Q, K, V, sc) - ref).abs().max():12.2e}")
for st in (4, 16):
    e = (sliced(Q, K, V, sc, st) - ref).abs().max(); print(f"  {f'{st} slices of queries':28s} {n * n // st:20d} {e:12.2e}"); assert e < 1e-4
for t in (128, 32):
    e = (online(Q, K, V, sc, t) - ref).abs().max(); print(f"  {f'online softmax, blocks of {t}':28s} {n * t:20d} {e:12.2e}"); assert e < 1e-4
def to8(x):
    s = x.abs().max() / 127; return torch.round(x / s) * s
e8 = (standard(to8(Q), to8(K), V, sc) - ref).abs().max(); rel = (standard(to8(Q), to8(K), V, sc) - ref).norm() / ref.norm()
print(f"  {'toy: Q and K rounded to int8':28s} {n * n:20d} {e8:12.2e}")
print(f"\nrelative change from int8 Q and K: {rel:.4f}. Exact methods stay at rounding level. Low precision is a real change.")
assert e8 > 1e-3
print("\ntokens from an image: one token per latent cell, 8x VAE")
for px, p in ((512, 1), (1024, 1), (1024, 2), (2048, 2)):
    t = (px // 8 // p) ** 2; print(f"  {px:5d} px, patch {p}: {t:6d} tokens, matrix {t * t * 2 / MB:8.1f} MB per head per row")
