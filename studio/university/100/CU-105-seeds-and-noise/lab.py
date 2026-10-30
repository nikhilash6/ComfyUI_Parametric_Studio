# CU-105 lab: what a seed fixes and what it leaves open. CPU only, a few seconds.
# Run: python lab.py
# Part 1 and 2 use PyTorch's CPU generator the way comfy/sample.py prepare_noise does (seed, then float32 normal numbers on the CPU).
# Part 3 and 4 run a toy: data that is two blobs, whose exact denoiser has a closed form, sampled with ComfyUI's Euler and ancestral-Euler update rules.
import math, torch
torch.set_num_threads(1)

def prepare_noise(shape, seed):                                      # the same recipe as comfy.sample.prepare_noise
    g = torch.manual_seed(seed)
    return torch.randn(shape, dtype=torch.float32, generator=g, device="cpu")
def corr(x, y):
    x, y = x.flatten().double(), y.flatten().double(); x, y = x - x.mean(), y - y.mean()
    return (x @ y / (x.norm() * y.norm())).item()

# 1. The seed is the starting noise.
shape = (1, 4, 64, 64)                                               # the latent of a 512 x 512 image, 16384 numbers
a, b, c = prepare_noise(shape, 42), prepare_noise(shape, 42), prepare_noise(shape, 43)
print(f"same seed twice: identical {torch.equal(a, b)}")
print(f"seed 42 against seed 43: correlation {corr(a, c):.4f} over {a.numel()} values")
print(f"noise from seed 42: mean {a.mean().item():.4f}, std {a.std().item():.4f}")
batch = prepare_noise((4,) + shape[1:], 42)
print(f"batch of 4 from seed 42: image 0 equals the single-image noise {torch.equal(batch[:1], a)}, correlation of images 0 and 1: {corr(batch[0], batch[1]):.4f}")
assert torch.equal(a, b) and abs(corr(a, c)) < 0.05 and torch.equal(batch[:1], a)

# 2. Where the extra noise of an ancestral sampler comes from, and why the sum of the same numbers can differ.
extra_same = torch.randn(shape, generator=torch.Generator().manual_seed(42))
extra_plus1 = torch.randn(shape, generator=torch.Generator().manual_seed(43))
print(f"\na CPU generator seeded 42 repeats the starting noise: {torch.equal(extra_same, a)}; seeded 43, which ComfyUI does on the CPU: correlation {corr(extra_plus1, a):.4f}")
flat = a.flatten(); fwd = torch.tensor(0.0); rev = torch.tensor(0.0)
for v in flat: fwd = fwd + v
for v in flat.flip(0): rev = rev + v
print(f"sum of the 16384 numbers in float32: forward {fwd.item():.6f}, reverse {rev.item():.6f}, torch.sum {flat.sum().item():.6f}; exact {flat.double().sum().item():.6f}")
assert torch.equal(extra_same, a) and not torch.equal(fwd, rev)

# 3. A toy to watch the sampler. Data: two blobs at plus and minus 2 along axis 0 (std 0.5 in 16 dimensions).
# For this data the exact denoiser is D(x, sigma) = c x + (1 - c) m tanh(m.x / (s^2 + sigma^2)), with c = s^2 / (s^2 + sigma^2).
DIM, N, S, M = 16, 4000, 0.5, 2.0
mvec = torch.zeros(DIM, dtype=torch.float64); mvec[0] = M
def denoise(x, sigma):
    v = S * S + sigma * sigma; c = S * S / v
    return c * x + (1 - c) * torch.tanh((x @ mvec) / v)[:, None] * mvec[None, :]
def schedule(n, lo=0.0292, hi=14.6146):                              # exponential spacing, then a final 0 (the SD 1.x sigma range)
    return torch.cat([torch.exp(torch.linspace(math.log(hi), math.log(lo), n, dtype=torch.float64)), torch.zeros(1, dtype=torch.float64)])
def euler(x, sg):                                                    # sample_euler: x += (x - denoised) / sigma * (sigma_next - sigma)
    for i in range(len(sg) - 1):
        x = x + (x - denoise(x, sg[i])) / sg[i] * (sg[i + 1] - sg[i])
    return x
def ancestral(x, sg, seed):                                          # sample_euler_ancestral with eta = 1, noise from a generator seeded with the seed
    g = torch.Generator().manual_seed(seed)
    for i in range(len(sg) - 1):
        s_from, s_to = float(sg[i]), float(sg[i + 1])
        up = min(s_to, (s_to ** 2 * (s_from ** 2 - s_to ** 2) / s_from ** 2) ** 0.5); down = (s_to ** 2 - up ** 2) ** 0.5
        den = denoise(x, sg[i])
        x = den if down == 0 else x + (x - den) / s_from * (down - s_from) + torch.randn(x.shape, generator=g, dtype=torch.float64) * up
    return x
noise = torch.randn(N, DIM, generator=torch.Generator().manual_seed(1234), dtype=torch.float64)
def run(kind, steps):
    sg = schedule(steps); x = noise * math.sqrt(1 + float(sg[0]) ** 2)    # a fully noised start, like noise_scaling with max_denoise
    return euler(x, sg) if kind == "euler" else ancestral(x, sg, 77)
ref = {k: run(k, 80) for k in ("euler", "ancestral")}
print("\nthe same 4000 starting noises, finished with different step counts, compared with an 80-step run")
print(f"{'steps':<16}{'Euler: same blob':<19}{'mean distance':<16}{'ancestral: same blob':<22}mean distance")
for steps in (5, 10, 20, 40):
    row = []
    for k in ("euler", "ancestral"):
        out = run(k, steps); row += [((out[:, 0] > 0) == (ref[k][:, 0] > 0)).double().mean().item(), (out - ref[k]).norm(dim=1).mean().item()]
    print(f"{steps:<16}{row[0]:<19.3f}{row[1]:<16.3f}{row[2]:<22.3f}{row[3]:.3f}")
shuffle = torch.randperm(N, generator=torch.Generator().manual_seed(5))
row = []
for k in ("euler", "ancestral"):
    out = run(k, 40)[shuffle]; row += [((out[:, 0] > 0) == (ref[k][:, 0] > 0)).double().mean().item(), (out - ref[k]).norm(dim=1).mean().item()]
print(f"{'unrelated noise':<16}{row[0]:<19.3f}{row[1]:<16.3f}{row[2]:<22.3f}{row[3]:.3f}")
e10, e40 = run("euler", 10), run("euler", 40)
a10, a40 = run("ancestral", 10), run("ancestral", 40)
assert ((e10[:, 0] > 0) == (ref["euler"][:, 0] > 0)).all() and ((a10[:, 0] > 0) == (ref["ancestral"][:, 0] > 0)).double().mean() < 0.8
assert torch.equal(run("euler", 20), run("euler", 20)) and torch.equal(run("ancestral", 20), run("ancestral", 20))
print("same seed, same steps, run twice: identical for Euler and for ancestral")

# 4. A tiny nudge to the starting noise: one part in a million.
sg = schedule(20); start = noise * math.sqrt(1 + float(sg[0]) ** 2)
base, nudged = euler(start.clone(), sg), euler(start * (1 + 1e-6), sg)
print(f"starting noise scaled by 1 + 1e-6 (Euler, 20 steps): samples that change blob {int(((base[:, 0] > 0) != (nudged[:, 0] > 0)).sum())} of {N}, largest change of any number {(base - nudged).abs().max().item():.6f}")
assert ((base[:, 0] > 0) != (nudged[:, 0] > 0)).sum() == 0
