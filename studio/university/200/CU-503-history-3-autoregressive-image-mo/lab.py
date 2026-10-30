# CU-503 lab: the chain rule for images, a causal mask, and the price of sampling one pixel at a time.
# Data: 8x8 binary images of a vertical bar two pixels wide at one of 7 positions, each pixel then flipped with probability 0.05.
# Because the generator is known, the exact conditionals p(x_i | x_<i) can be computed and the learned model graded against them.
# Run: python lab.py  (CPU only, about 8 s). Prints the same numbers every time.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D64 = torch.float64
S = 8; N = S * S; EPS = 0.05; K = 7
BARS = torch.stack([torch.zeros(S, S).index_fill_(1, torch.tensor([c, c + 1]), 1.).flatten() for c in range(K)]).to(D64)
Q = BARS * (1 - 2 * EPS) + EPS                                                  # P(pixel = 1 | bar at c)
g = torch.Generator().manual_seed(1)
def data(n, gen): c = torch.randint(0, K, (n,), generator=gen); return (BARS[c] + (torch.rand(n, N, generator=gen, dtype=D64) < EPS).to(D64)) % 2
train, test = data(20000, g), data(20000, g)

# 1. The chain rule, checked. The exact conditional of pixel i given the pixels before it is a Bayes average over the bar position.
def pixel_ll(x): return x[:, None, :] * Q.log() + (1 - x[:, None, :]) * (1 - Q).log()          # n x K x N, log p(x_i | bar c)
def exact_cond(x):
    ll = pixel_ll(x); before = ll.cumsum(2) - ll                                                # evidence from the pixels before i
    return (torch.logsumexp(before + ll, 1) - torch.logsumexp(before, 1)) / math.log(2)        # log2 p(x_i | x_<i), n x N
cond = exact_cond(test); joint = (torch.logsumexp(pixel_ll(test).sum(2), 1) - math.log(K)) / math.log(2)   # log2 p(x) from the generator directly
err = (cond.sum(1) - joint).abs().max().item(); print(f"largest gap between sum_i log2 p(x_i | x_<i) and log2 p(x), over 20000 images: {err:.1e}"); assert err < 1e-9

# 2. A causal mask makes every conditional computable in one pass. Masks as in MADE: hidden unit k has a degree m(k); it reads inputs d <= m(k), and output d reads units with m(k) < d.
class Net(torch.nn.Module):
    def __init__(s, masked, hidden=256):
        super().__init__(); s.a, s.b = torch.nn.Linear(N, hidden), torch.nn.Linear(hidden, N); m = torch.arange(hidden) % (N - 1) + 1; d = torch.arange(1, N + 1)
        s.register_buffer("Ma", (m[:, None] >= d[None, :]).float() if masked else torch.ones(hidden, N)); s.register_buffer("Mb", (d[:, None] > m[None, :]).float() if masked else torch.ones(N, hidden))
    def forward(s, x): return torch.nn.functional.linear(torch.relu(torch.nn.functional.linear(x, s.a.weight * s.Ma, s.a.bias)), s.b.weight * s.Mb, s.b.bias)   # logit of P(x_i = 1 | x_<i)
x0 = test[0].float(); upper = torch.triu(torch.ones(N, N), 0).bool()                           # entries (i, j) with j >= i
print("\nlargest |d logit_i / d x_j|    j >= i (future and self)   j < i (past)")
for masked in (True, False):
    torch.manual_seed(0); net = Net(masked); J = torch.autograd.functional.jacobian(lambda v: net(v[None])[0], x0)
    print(f"{'masked network' if masked else 'unmasked network':30s} {J[upper].abs().max():.2e}                   {J[~upper].abs().max():.3f}")
    if masked: assert J[upper].abs().max() == 0 and J[~upper].abs().max() > 0
    else: assert J[upper].abs().max() > 0

# 3. Train the masked network by maximum likelihood. One forward pass scores all 64 conditionals, so there is no loop over pixels.
torch.manual_seed(0); net = Net(True); opt = torch.optim.Adam(net.parameters(), 3e-3); xs = train.float(); bce = torch.nn.functional.binary_cross_entropy_with_logits
for _ in range(1500):
    b = xs[torch.randint(0, len(xs), (256,))]; loss = bce(net(b), b); opt.zero_grad(); loss.backward(); opt.step()
with torch.no_grad(): lp = -bce(net(test.float()), test.float(), reduction="none") / math.log(2)  # log2 p(x_i | x_<i) under the learned model
p = train.mean(0).clamp(1e-3, 1 - 1e-3); ind = (test * p.log2() + (1 - test) * (1 - p).log2())
print("\nmodel                        bits per pixel on 20000 fresh images")
for name, v in (("uniform: every image equally likely", torch.full((1,), -1.)), ("independent pixels", ind.double()), ("learned autoregressive", lp.double()), ("exact autoregressive (the truth)", cond)):
    print(f"{name:36s} {-v.mean() if v.numel() > 1 else 1.0:.4f}")
assert -lp.mean() < -cond.mean() + 0.03 and -ind.mean() > 2 * -cond.mean()
print("\nbits per pixel by image row   " + " ".join(f"{r + 1:5d}" for r in range(S)))
for name, v in (("learned", lp.double()), ("exact", cond)): print(f"{name:30s}" + " ".join(f"{-v.view(-1, S, S)[:, r].mean():5.2f}" for r in range(S)))
print(f"the flip noise alone costs {-(EPS * math.log2(EPS) + (1 - EPS) * math.log2(1 - EPS)):.2f} bits per pixel")

# 4. Sampling is the sequential part: pixel i can only be drawn after pixels 1..i-1 exist. One network pass per pixel.
def valid(x):                                                                                  # a bar: two adjacent columns almost full, the rest almost empty
    cs = x.view(-1, S, S).sum(1); top = cs.topk(2, dim=1); ok = ((top.indices[:, 0] - top.indices[:, 1]).abs() == 1) & (top.values.min(1).values >= 6)
    rest = cs.clone(); rest.scatter_(1, top.indices, 0.); return ok & (rest.max(1).values <= 3)
gen = torch.Generator().manual_seed(2); n = 4000; x = torch.zeros(n, N); passes = 0
with torch.no_grad():
    for i in range(N): x[:, i] = (torch.rand(n, generator=gen) < torch.sigmoid(net(x)[:, i])).float(); passes += 1
xi = (torch.rand(n, N, generator=gen) < p.float()).float(); xt = data(n, torch.Generator().manual_seed(3)).float()
print(f"\nnetwork passes to draw {n} images: {passes} (one per pixel), against 1 pass to score them")
print(f"share that look like a bar:  real data {valid(xt).float().mean():.3f}   autoregressive samples {valid(x).float().mean():.3f}   independent-pixel samples {valid(xi).float().mean():.3f}")
for r in range(S): print("   ".join("".join("#" if v else "." for v in x[k].view(S, S)[r].tolist()) for k in range(4)))
assert valid(x).float().mean() > .8 and valid(xt).float().mean() > .95 and valid(xi).float().mean() < .2 and passes == N
print(f"\nvalues in a 256x256 RGB image: {256 * 256 * 3:,}; image tokens in DALL-E's 32x32 grid: {32 * 32:,}; ratio {256 * 256 * 3 / (32 * 32):.0f}")
