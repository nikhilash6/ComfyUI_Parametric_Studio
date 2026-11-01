# CU-282 lab: why you compare at the same seed, and how a sweep reads. A tiny network with a LoRA on one layer stands in for a model: the point is the arithmetic of comparing, not pictures.
import torch
torch.manual_seed(0); torch.set_num_threads(1)
D = 64; g = torch.Generator().manual_seed(0)
W1 = torch.randn(D, D, generator=g) / D ** 0.5; W2 = torch.randn(D, D, generator=g) / D ** 0.5; W3 = torch.randn(D, D, generator=g) / D ** 0.5
up = torch.randn(D, 4, generator=g) / D ** 0.5; down = torch.randn(4, D, generator=g) / D ** 0.5
def net(z, s):                                    # s is the LoRA strength on the middle layer
    return torch.tanh(W3 @ torch.tanh((W2 + s * up @ down) @ torch.tanh(W1 @ z)))
seeds = [torch.randn(D, generator=torch.Generator().manual_seed(100 + i)) for i in range(200)]
diff = lambda a, b: (a - b).abs().mean().item()
same = [diff(net(z, 0.0), net(z, 1.0)) for z in seeds]
other = [diff(net(seeds[i], 0.0), net(seeds[(i + 1) % 200], 1.0)) for i in range(200)]
base = [diff(net(seeds[i], 0.0), net(seeds[(i + 1) % 200], 0.0)) for i in range(200)]
mean = lambda x: sum(x) / len(x)
print("mean absolute difference between two outputs, 200 tries")
print("pair                                difference")
print(f"same seed, LoRA off against on      {mean(same):.4f}")
print(f"new seed, LoRA off against on       {mean(other):.4f}")
print(f"new seed, LoRA off against off      {mean(base):.4f}")
print(f"at a new seed the LoRA's part is hidden: {mean(other):.4f} against {mean(base):.4f} with no LoRA at all, while the same-seed pair shows {mean(same):.4f}")
assert mean(same) < mean(other) * 0.5 and abs(mean(other) - mean(base)) < 0.1 * mean(base)
print(f"same seed, LoRA off twice: {diff(net(seeds[0], 0.0), net(seeds[0], 0.0)):.4f}  strength 0 is the base exactly, so anything else that moved is your test's fault")
assert diff(net(seeds[0], 0.0), net(seeds[0], 0.0)) == 0
print("\none seed can mislead: effect of the LoRA at strength 1, per seed")
s = sorted(same); print(f"smallest {s[0]:.4f}   median {s[100]:.4f}   largest {s[-1]:.4f}   largest / smallest {s[-1] / s[0]:.1f}")
print("\nstrength sweep, same seeds. The weight moves in a straight line. The output need not")
print("strength   weight change   output change   change per unit of strength")
rows = {}; dW = (up @ down).norm().item()
for st in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0, -1.0):
    c = mean([diff(net(z, 0.0), net(z, st)) for z in seeds[:50]]); rows[st] = c
    print(f"{st:<10} {abs(st) * dW:<15.4f} {c:<15.4f} {(c / abs(st) if st else 0):.4f}")
assert rows[0.0] == 0 and rows[0.5] < rows[1.0] < rows[2.0]
assert rows[4.0] / 4 < rows[0.25] / 0.25
print("\nfour pictures to make, one seed, and what each answers")
print("LoRA   trigger   tells you")
for a, b, c in (("off", "no", "the base with this prompt"), ("off", "yes", "what the word alone does on the base"), ("on", "no", "what the LoRA does without its word"), ("on", "yes", "the full effect")): print(f"{a:<6} {b:<9} {c}")
