# CU-416 lab: a CPU model of the two questions a GPU profile answers: what was alive at the peak, and where did the time go.
# Sizes and times here are examples we chose. The tool's arithmetic is real. A real profile needs real numbers.
import torch
torch.manual_seed(0); torch.set_num_threads(1)
MB = 1024 ** 2
x = torch.randn(2, 3, 8, 8); assert x.numel() * x.element_size() == 1536
print(f"a tensor's bytes = elements x bytes each: {tuple(x.shape)} fp32 = {x.numel() * x.element_size()} bytes")
for name, shape, b in (("SD latent, 64x64", (1, 4, 64, 64), 4), ("IMAGE 1024x1024", (1, 1024, 1024, 3), 4), ("16 channel latent, 128x128", (1, 16, 128, 128), 2)):
    n = 1
    for s in shape: n *= s
    print(f"  {name:28s} {n * b / MB:8.2f} MB")
def peak(order, frees):
    """Walk the operations in order. A tensor lives from its own step until the last step that reads it."""
    live = {}; hi = 0; who = []
    for i, (name, size) in enumerate(order):
        live[name] = size
        t = sum(live.values())
        if t > hi: hi = t; who = sorted(live)
        for f in frees.get(name, ()): live.pop(f)
    return hi, who
order = [("a", 300), ("b", 500), ("c", 200), ("d", 100)]
print("\nthe peak is not the sum, and not the biggest tensor. Four tensors, in MB:", dict(order))
h, w = peak(order, {"b": ["a"], "c": ["b"], "d": ["c"]}); print(f"  each freed after the next one is made: peak {h} MB, alive {w}")
h2, w2 = peak(order, {}); print(f"  nothing freed: peak {h2} MB, alive {w2}")
assert h == 800 and h2 == 1100
print("  sum of all = 1100, biggest alone = 500")
print("\nallocated, reserved and what nvidia-smi shows: a toy caching allocator")
class Alloc:
    def __init__(self): self.allocated = 0; self.reserved = 0; self.hi = 0
    def get(self, n):
        self.allocated += n; self.reserved = max(self.reserved, self.allocated); self.hi = max(self.hi, self.allocated)
    def put(self, n): self.allocated -= n
    def empty_cache(self): self.reserved = self.allocated
A = Alloc(); A.get(6000); A.put(5000); print(f"  after freeing: allocated {A.allocated}  reserved {A.reserved}  peak allocated {A.hi}")
A.empty_cache(); print(f"  after empty_cache: allocated {A.allocated}  reserved {A.reserved}  peak allocated {A.hi}")
assert A.reserved == 1000 and A.hi == 6000
print("\nwork in a matmul. y = x W for M rows, K inputs and N outputs is 2 M N K operations, and doubling the side changes M")
for name, M, N, K in (("512 px, 4096 tokens", 4096, 320, 320), ("1024 px, 16384 tokens", 16384, 320, 320)):
    print(f"  {name:24s} {2 * M * N * K:>16,d}")
print("\nwhere the time went, example numbers")
stages = {"load models": 40.0, "text encode": 2.0, "sampling": 60.0, "VAE decode": 8.0}; tot = sum(stages.values())
for k, v in stages.items(): print(f"  {k:12s} {v:5.1f} s  {100 * v / tot:5.1f}%")
def after(stage, x): return tot - stages[stage] + stages[stage] / x
print(f"  text encode 10 times faster: {after('text encode', 10):.1f} s.  sampling 2 times faster: {after('sampling', 2):.1f} s")
assert after("sampling", 2) < after("text encode", 10)
print("\nwhy one timing lies: the first run includes loading. Same example, median of five runs")
runs = [66.0, 1.5, 1.5, 1.5, 1.5]; s = sorted(runs); print(f"  runs {runs}  mean {sum(runs) / 5:.1f} s  median {s[2]:.1f} s")
assert s[2] == 1.5
