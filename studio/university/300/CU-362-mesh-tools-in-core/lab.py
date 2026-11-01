# CU-362 lab: why you remesh, then decimate, then unwrap. A small QEM on an icosphere, in the spirit of comfy_extras/mesh3d/postprocess/qem_decimate.py (midpoint placement). CPU.
import math, torch, heapq
torch.set_num_threads(1)
def icosphere(level):
    t = (1 + 5 ** 0.5) / 2
    V = [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]]
    F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    V = [[c / math.sqrt(sum(x * x for x in v)) for c in v] for v in V]
    for _ in range(level):
        mid = {}; nf = []
        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                p = [(x + y) / 2 for x, y in zip(V[a], V[b])]; l = math.sqrt(sum(x * x for x in p)); V.append([x / l for x in p]); mid[k] = len(V) - 1
            return mid[k]
        for a, b, c in F:
            ab, bc, ca = m(a, b), m(b, c), m(c, a); nf += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        F = nf
    return torch.tensor(V, dtype=torch.float64), torch.tensor(F)
def quadrics(V, F):
    Q = torch.zeros(V.shape[0], 4, 4, dtype=torch.float64); a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = torch.linalg.cross(b - a, c - a); n = n / n.norm(dim=1, keepdim=True); d = -(n * a).sum(1, keepdim=True); p = torch.cat([n, d], 1); K = p[:, :, None] * p[:, None, :]
    for i in range(3): Q.index_add_(0, F[:, i], K)
    return Q
def simplify(V, F, target):
    """greedy edge collapse to the midpoint, cheapest first. The core node runs parallel rounds with extra checks: this is the idea, not the code."""
    V = V.clone(); Q = quadrics(V, F); F = [tuple(f) for f in F.tolist()]; alive = set(range(len(F))); v2f = {}
    for i, f in enumerate(F):
        for x in f: v2f.setdefault(x, set()).add(i)
    def cost(a, b):
        m = (V[a] + V[b]) / 2; h = torch.cat([m, torch.ones(1, dtype=torch.float64)]); return (h @ (Q[a] + Q[b]) @ h).item()
    heap = []
    for f in F:
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            if a < b: heapq.heappush(heap, (cost(a, b), a, b))
    while len(alive) > target and heap:
        c, a, b = heapq.heappop(heap)
        if a not in v2f or b not in v2f or abs(c - cost(a, b)) > 1e-12: continue
        shared = v2f[a] & v2f[b]
        V[a] = (V[a] + V[b]) / 2; Q[a] = Q[a] + Q[b]
        for i in shared: alive.discard(i); [v2f[x].discard(i) for x in F[i]]
        for i in v2f[b] - shared: F[i] = tuple(a if x == b else x for x in F[i]); v2f[a].add(i)
        del v2f[b]
        for x in {y for i in v2f[a] for y in F[i]} - {a}: heapq.heappush(heap, (cost(min(a, x), max(a, x)), min(a, x), max(a, x)))
    used = sorted(v2f); return V[used], len(alive)
V, F = icosphere(3)
print(f"icosphere: {V.shape[0]} vertices, {F.shape[0]} faces. True sphere radius 1.")
print("target faces   faces left   vertices   mean distance from the sphere   worst")
rows = {}
for tgt in (640, 320, 160, 80):
    v, n = simplify(V, F, tgt); e = (v.norm(dim=1) - 1).abs(); rows[tgt] = e.mean().item(); print(f"{tgt:<14d} {n:<12d} {v.shape[0]:<10d} {e.mean().item():<31.5f} {e.max().item():.5f}")
assert rows[80] > rows[640]
# Remesh cost: the node asks for resolution ** 3 * 64 bytes before it starts. Faces per its tooltip: 256 about 100k, 512 about 1M.
print("\nRemeshMesh memory_required floor")
for r in (128, 256, 512, 1024): print(f"resolution {r:>4d}: {r ** 3 * 64 / 1024 ** 3:>6.2f} GiB")
assert 512 ** 3 * 64 == 8589934592
# Seams. UnwrapMesh duplicates a vertex for every chart it touches. A cube cut into 6 separate faces, and cut into one cross.
print("\nA cube has 8 corners. Cut into 6 separate squares its vertex list becomes", 6 * 4, "; laid out as one cross,", 14, "; the geometry is the same")
# Texel use: charts plus padding. Each chart of side c texels with padding p takes (c + 2 p) ** 2.
for charts in (6, 96, 1536):
    side = int(math.sqrt(1024 * 1024 / charts)); inner = side - 2; print(f"{charts:>5d} charts in a 1024 atlas with padding 1: at most {charts * inner * inner / 1024 ** 2:.1%} of the texels hold colour")
assert 6 * (int(math.sqrt(1024 ** 2 / 6)) - 2) ** 2 < 1024 ** 2
