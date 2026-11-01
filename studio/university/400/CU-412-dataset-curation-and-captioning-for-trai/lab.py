# CU-412 lab: what the core training path does with your pictures and captions, and a toy of why captions decide what a trigger word learns.
# Pair and repeat rules follow LoadImageTextDataSetFromFolderNode in comfy_extras/nodes_dataset.py. Sampling follows TrainSampler._train_step_standard_mode: torch.randperm(dataset)[:batch] at every step.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
# 1. The folder rule.
def load(files):
    pics = []
    for f in files:
        if "/" in f:
            d, name = f.split("/"); rep = int(d.split("_")[0]) if d.split("_")[0].isdigit() else 1; pics += [name] * rep
        else: pics.append(f)
    return pics
print("files                                     pictures in the list")
for fs in (["a.png", "b.png"], ["5_lamp/a.png", "b.png"], ["lamp/a.png", "b.png"]):
    print(f"{str(fs):<41} {load(fs)}")
assert load(["5_lamp/a.png", "b.png"]) == ["a.png"] * 5 + ["b.png"]
# 2. How often each picture is seen.
def counts(n, steps, batch, seed=0):
    g = torch.Generator().manual_seed(seed); c = [0] * n
    for _ in range(steps):
        for i in torch.randperm(n, generator=g)[:batch].tolist(): c[i] += 1
    return c
print("\nsightings per picture, one seeded run. Each step draws afresh, so the counts are uneven")
print("pictures   steps   batch   average   fewest   most")
rows = {}
for n, st, b in ((12, 300, 1), (12, 100, 1), (12, 25, 1), (40, 300, 1), (200, 300, 1), (12, 300, 4)):
    c = counts(n, st, b); rows[(n, st, b)] = c
    print(f"{n:<10} {st:<7} {b:<7} {st * b / n:<9.1f} {min(c):<8} {max(c)}")
assert sum(rows[(12, 300, 1)]) == 300 and min(rows[(200, 300, 1)]) == 0
miss = lambda n, st: sum(1 for x in counts(n, st, 1) if x == 0)
print(f"pictures never seen: 200 pictures at 300 steps {miss(200, 300)}   formula n (1 - 1/n)^steps = {200 * (1 - 1 / 200) ** 300:.1f}")
# 3. A caption of more than the encoder's window is split into groups, not cut. sd1_clip.SDTokenizer: 77 slots, 2 taken by the start and end tokens, 75 for words.
print("\ntokens in the caption   groups sent to the encoder (SD 1.5)   numbers in the conditioning")
for t in (10, 75, 76, 150, 151):
    k = max(1, math.ceil(t / 75)); print(f"{t:<23} {k:<37} {k} x 77 x 768")
# 4. Why captions matter: a toy. A picture is two facts, the new thing (lamp) and the place (a beach in most of them). A linear model learns what each caption word adds.
# Words are inputs; the picture's content is the target. Least squares: the smallest weights that explain the data, which is what gradient descent on a linear model from zero finds.
g = torch.Generator().manual_seed(1)
N = 40; beach = (torch.rand(N, generator=g) < 0.9).float(); forest = 1 - beach          # 90% of the set is on a beach
# Content has three parts: lamp present (always), beach look, forest look.
content = torch.stack([torch.ones(N), beach, forest], 1)
def fit(X):
    return torch.linalg.pinv(X, rcond=1e-6) @ content
def ask(w, words): return (words @ w).tolist()
tr = torch.ones(N)
print("\nthe toy. Prompt: the trigger alone. What the model then produces: lamp, beach, forest (1 = fully present)")
print("captions                                  lamp    beach   forest")
A = fit(torch.stack([tr], 1)); a = ask(A, torch.tensor([1.0]))
B = fit(torch.stack([tr, beach, forest], 1)); b = ask(B, torch.tensor([1.0, 0, 0]))
print(f"{'trigger only':<41} {a[0]:<7.2f} {a[1]:<7.2f} {a[2]:.2f}")
print(f"{'trigger + place words':<41} {b[0]:<7.2f} {b[1]:<7.2f} {b[2]:.2f}")
assert a[1] > 0.8 and b[1] < a[1] - 0.3
c2 = ask(B, torch.tensor([1.0, 0, 1.0])); print(f"{'trigger + place words, asking for forest':<41} {c2[0]:<7.2f} {c2[1]:<7.2f} {c2[2]:.2f}")
assert c2[2] > 0.5
print("\nshare of pictures on the beach, and how much beach the bare trigger brings when place is never captioned")
print("beach share   beach from trigger alone")
for sh in (0.5, 0.75, 0.9, 1.0):
    k = int(N * sh); bb = torch.zeros(N); bb[:k] = 1; w = torch.linalg.pinv(torch.ones(N, 1)) @ bb[:, None]
    print(f"{sh:<13} {w.item():.2f}")
