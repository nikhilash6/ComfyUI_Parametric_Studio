# CU-410 lab: quantize every layer of a small stack and watch the error move through it. Synthetic weights.
# Rounding here is absmax int8 or int4 per tensor, as in CU-211. This measures numbers, not pictures.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = 256
def q(w, qmax):
    s = w.abs().max() / qmax; return torch.round(w / s) * s
def make(depth, gain, g):
    """Each layer is a random matrix scaled so that its largest singular value is near gain."""
    out = []
    for _ in range(depth):
        w = torch.randn(D, D, generator=g, dtype=torch.float64) / math.sqrt(D); out.append(w * gain / 2.0)
    return out
def run(layers, x, res=False):
    for w in layers:
        y = torch.tanh(x @ w.T) ; x = x + y if res else y
    return x
def rel(a, b): return ((a - b).norm() / b.norm()).item()
g = torch.Generator().manual_seed(1); X = torch.randn(512, D, generator=g, dtype=torch.float64)
print("one layer: y = W x. The error of the output is exactly dW x, which is linear in the weight error")
W = make(1, 1.0, g)[0]; dW = q(W, 127) - W; y = X @ W.T; yq = X @ q(W, 127).T
print(f"  weight error {dW.norm() / W.norm():.5f}   output error {rel(yq, y):.5f}   |dW x| matches: {((yq - y) - X @ dW.T).abs().max():.1e}")
assert ((yq - y) - X @ dW.T).abs().max() < 1e-10
print("\nerror at the output of a stack, every layer int8, by depth and by how much each layer stretches its input")
print("depth   gain 0.5   gain 1.0   gain 2.0   gain 4.0")
tab = {}
for d in (1, 2, 4, 8, 16):
    row = []
    for gain in (0.5, 1.0, 2.0, 4.0):
        L = make(d, gain, torch.Generator().manual_seed(10 + d)); e = rel(run([q(w, 127) for w in L], X), run(L, X)); row.append(e); tab[(d, gain)] = e
    print(f"{d:5d}   " + "   ".join(f"{e:8.5f}" for e in row))
print(f"gain 1: depth 16 / depth 1 = {tab[(16, 1.0)] / tab[(1, 1.0)]:.2f}.  errors that add like independent noise would give sqrt(16) = 4")
assert 3 < tab[(16, 1.0)] / tab[(1, 1.0)] < 5 and tab[(16, 4.0)] > 3 * tab[(16, 1.0)]
print("\nonly one layer quantized, 8 layers, gain 2: does an early error matter more than a late one?")
L = make(8, 2.0, torch.Generator().manual_seed(5)); clean = run(L, X); es = []
for i in (0, 3, 7):
    M = list(L); M[i] = q(M[i], 127); e = rel(run(M, X), clean); es.append(e); print(f"  layer {i}: output error {e:.5f}")
print("\nbits: same stack, 8 layers, gain 2, every layer")
b8 = rel(run([q(w, 127) for w in L], X), clean); b4 = rel(run([q(w, 7) for w in L], X), clean)
print(f"  int8 {b8:.5f}   int4 {b4:.5f}   ratio {b4 / b8:.1f}   the step ratio 127/7 = {127 / 7:.1f}")
assert b4 > 5 * b8
print("\nskip connections: x + f(x), as in residual blocks, 16 layers, gain 1, int8")
L = make(16, 1.0, torch.Generator().manual_seed(6)); a = rel(run([q(w, 127) for w in L], X), run(L, X)); b = rel(run([q(w, 127) for w in L], X, True), run(L, X, True))
print(f"  plain {a:.5f}   with skips {b:.5f}")
print("\nweight rounding needs no calibration data. The scale comes from the weights themselves:")
print(f"  scale for layer 0 = {L[0].abs().max() / 127:.6f}, no input was looked at")
