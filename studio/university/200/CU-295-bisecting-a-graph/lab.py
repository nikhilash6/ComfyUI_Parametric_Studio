# CU-295 lab: how many previews it takes to find the first bad node in a chain, walking or halving. Then a trap in text previews: PreviewAny prints a tensor with torch's own summary, so a big tensor hides its middle.
import torch
def walk(bad, n):
    c = 0
    for i in range(1, n):
        c += 1
        if i >= bad: return c
    return c
def halve(bad, n):
    lo, hi = 0, n - 1; c = 0        # node 0 is fine, the last node is bad
    while hi - lo > 1:
        m = (lo + hi) // 2; c += 1
        if m >= bad: hi = m
        else: lo = m
    assert hi == bad; return c
print("chain length   walking: worst, average    halving: worst")
for n in (8, 16, 32, 64):
    W = [walk(b, n) for b in range(1, n)]; H = [halve(b, n) for b in range(1, n)]
    print(f"{n:<14} {max(W):<7} {sum(W) / len(W):<16.1f} {max(H)}")
    if n == 16: assert max(H) == 4 and max(W) == 15
# PreviewAny calls torch.set_printoptions(edgeitems=6), then str(tensor).
def text_of(t):
    torch.set_printoptions(edgeitems=6); s = str(t); torch.set_printoptions(); return s
print()
for shape, label in (((1, 4, 8, 8), "small latent"), ((1, 4, 64, 64), "512 by 512 latent")):
    x = torch.zeros(shape); x[0, 0, shape[2] // 2, shape[3] // 2] = float("nan"); s = text_of(x)
    print(f"{label:20} one NaN in the middle: the word nan appears in the text: {'nan' in s}   ('...' summary: {'...' in s})")
    if shape[2] == 64: assert "nan" not in s
    else: assert "nan" in s
x = torch.zeros(1, 4, 64, 64); x[0, 0, 0, 0] = float("nan"); print("512 by 512 latent    one NaN in a corner: appears:", "nan" in text_of(x)); assert "nan" in text_of(x)
y = torch.full((1, 4, 64, 64), float("nan")); print("512 by 512 latent    all NaN: appears:", "nan" in text_of(y)); assert "nan" in text_of(y)
