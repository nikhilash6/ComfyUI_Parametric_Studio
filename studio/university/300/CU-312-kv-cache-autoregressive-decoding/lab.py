# CU-312 lab: generate one token at a time, with and without a KV cache, and count the work. CPU, no model.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = 16; E = torch.randn(50, D); Wq, Wk, Wv = [torch.randn(D, D) for _ in range(3)]; head = torch.randn(D, 50)
def attend(q, k, v, mask=None):
    s = q @ k.transpose(-1, -2) / math.sqrt(D)
    if mask is not None: s = s.masked_fill(~mask, float("-inf"))
    return s.softmax(-1) @ v
# Without a cache: every step projects every token again and attends again. Each new token only looks backwards.
def step_full(ids):
    x = E[ids]; n = len(ids); out = attend(x @ Wq, x @ Wk, x @ Wv, torch.tril(torch.ones(n, n, dtype=torch.bool))); return out[-1], {"proj": n, "pairs": n * (n + 1) // 2}
# With a cache: project only the new token, store its k and v, attend one row against everything stored.
class Cache:
    def __init__(self, cap): self.k = torch.zeros(cap, D); self.v = torch.zeros(cap, D); self.n = 0
    def append(self, k, v): self.k[self.n] = k; self.v[self.n] = v; self.n += 1
def step_cached(tok, c):
    x = E[tok]; c.append(x @ Wk, x @ Wv); return attend((x @ Wq).unsqueeze(0), c.k[:c.n], c.v[:c.n])[0], {"proj": 1, "pairs": c.n}
ids = [1]; c = Cache(64); a = step_cached(1, c)[0]; f = step_full(ids)[0]; print(f"first token, cached against recomputed: max difference {(a - f).abs().max():.1e}")
work = {"full": [0, 0], "cached": [0, 0]}; maxgap = 0.0; seq = [1]; c = Cache(64); w = step_cached(1, c)
for side, r in (("cached", w[1]),): work[side][0] += r["proj"]; work[side][1] += r["pairs"]
o, r = step_full(seq); work["full"][0] += r["proj"]; work["full"][1] += r["pairs"]; last = w[0]
for _ in range(39):
    tok = int((last @ head).argmax()); seq.append(tok)
    o1, r1 = step_full(seq); o2, r2 = step_cached(tok, c); maxgap = max(maxgap, (o1 - o2).abs().max().item()); last = o2
    work["full"][0] += r1["proj"]; work["full"][1] += r1["pairs"]; work["cached"][0] += r2["proj"]; work["cached"][1] += r2["pairs"]
print(f"40 tokens generated, largest difference between the two outputs at any step: {maxgap:.1e}"); assert maxgap < 1e-4
print("              token projections   attention pairs")
print(f"no cache      {work['full'][0]:<19,d} {work['full'][1]:,d}"); print(f"KV cache      {work['cached'][0]:<19,d} {work['cached'][1]:,d}")
assert work["cached"][0] == 40 and work["full"][0] == 820
# The price: memory for each layer, kept for the whole run.
print("\ntokens stored   one layer, 8 kv heads, head width 128, bf16   24 layers")
for n in (256, 1024, 4096, 16384):
    b = 2 * n * 8 * 128 * 2; print(f"{n:<15,d} {b / 2 ** 20:<45.1f} {24 * b / 2 ** 30:.2f} GiB")
# The cache is only right if nothing earlier changes. Change one early token and the stored keys are stale.
s2 = list(seq); s2[3] = (s2[3] + 1) % 50; o3, _ = step_full(s2); cq = (E[s2[-1]] @ Wq).unsqueeze(0); stale = attend(cq, c.k[:c.n], c.v[:c.n])[0]
print(f"\nedit token 3 and reuse the old cache: the output is off by {(o3 - stale).abs().max():.3f}, so a cache must be thrown away or rolled back"); assert (o3 - stale).abs().max() > 1e-3
# A cross-attention to a fixed context, such as a prompt, needs its keys computed once only (crossattn_cache in comfy/ldm/wan/ar_model.py).
print("cross-attention to a fixed text of 77 tokens over 40 steps: 77 key projections with a cache,", 77 * 40, "without")
