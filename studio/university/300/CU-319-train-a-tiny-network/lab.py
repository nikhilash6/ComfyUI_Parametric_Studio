# CU-319 lab: a tiny network, forward, backward and training, measured.
# Run: python lab.py  (CPU only, a few seconds).
import math, torch
torch.manual_seed(0); torch.set_num_threads(1); torch.set_default_dtype(torch.float64)

def spiral(n=240, noise=0.1, seed=7):
    """Two interleaved arms in [-1, 1]², as in the browser lab: every other point is the other class."""
    g = torch.Generator().manual_seed(seed); i = torch.arange(n); c = i % 2
    t = (i // 2) / (n // 2) * 1.75 * math.pi + 0.3; r = t / (1.75 * math.pi + 0.3); ang = t + c * math.pi
    X = torch.stack([r * torch.cos(ang), r * torch.sin(ang)], 1) + torch.randn(n, 2, generator=g) * noise * 0.5
    return X, c.double()

def net(sizes, act, seed=1):
    g = torch.Generator().manual_seed(seed)
    return [(torch.randn(o, i, generator=g) * math.sqrt((2 if act is torch.relu else 1) / i), torch.zeros(o)) for i, o in zip(sizes, sizes[1:])]

def forward(params, X, act):
    a = X
    for l, (W, b) in enumerate(params):
        z = a @ W.T + b; a = act(z) if l < len(params) - 1 else z
    return a[:, 0]                                                     # the logit; sigmoid of it is the probability of class 1

def loss(params, X, y, act): return torch.nn.functional.binary_cross_entropy_with_logits(forward(params, X, act), y)

X, y = spiral(); tr, te = torch.arange(240) % 4 != 3, torch.arange(240) % 4 == 3
print(f"spiral: {len(y)} points, {int(y.sum())} of class 1, {int(tr.sum())} to train on, {int(te.sum())} held out")

# 1. The backward pass, by hand, for one hidden layer, against autograd.
p = net([2, 4, 1], torch.tanh); (W1, b1), (W2, b2) = p
z1 = X[tr] @ W1.T + b1; a1 = torch.tanh(z1); z2 = a1 @ W2.T + b2; pr = torch.sigmoid(z2[:, 0])
d2 = ((pr - y[tr]) / len(pr))[:, None]                                  # sigmoid with cross-entropy: dL/dz = p - y, over the batch
gW2 = d2.T @ a1; d1 = (d2 @ W2) * (1 - a1 ** 2); gW1 = d1.T @ X[tr]
q = [(W.clone().requires_grad_(), b.clone().requires_grad_()) for W, b in p]; loss(q, X[tr], y[tr], torch.tanh).backward()
gap = max((gW1 - q[0][0].grad).abs().max().item(), (gW2 - q[1][0].grad).abs().max().item())
print(f"\nhand-written backward against autograd, largest difference: {gap:.1e}"); assert gap < 1e-12

# 2. A gradient check: central differences against the backward pass, every weight, float64.
def check(act):
    p = net([2, 5, 5, 1], act, seed=3); flat = torch.cat([t.flatten() for W, b in p for t in (W, b)])
    def f(v):
        out, k = [], 0
        for W, b in p: out.append((v[k:k + W.numel()].view_as(W), v[k + W.numel():k + W.numel() + b.numel()])); k += W.numel() + b.numel()
        return loss(out, X[:30], y[:30], act)
    v = flat.clone().requires_grad_(); f(v).backward(); worst = 0.0; eps = 1e-5
    for i in range(len(flat)):
        e = torch.zeros_like(flat); e[i] = eps; num = ((f(flat + e) - f(flat - e)) / (2 * eps)).item(); an = v.grad[i].item()
        if abs(an) + abs(num) > 1e-9: worst = max(worst, abs(an - num) / (abs(an) + abs(num)))
    return len(flat), worst
print("\nactivation  parameters  worst relative error")
for name, act in (("tanh", torch.tanh), ("sigmoid", torch.sigmoid)):
    n, w = check(act); print(f"{name:<11} {n:<11} {w:.1e}"); assert w < 1e-6

# 3. Training: full-batch gradient descent, as the browser lab does it.
def train(sizes, act, lr, steps):
    p = [(W.requires_grad_(), b.requires_grad_()) for W, b in net(sizes, act)]; first = loss(p, X[tr], y[tr], act).item()
    for _ in range(steps):
        L = loss(p, X[tr], y[tr], act); g = torch.autograd.grad(L, [t for pair in p for t in pair])
        with torch.no_grad():
            for t, d in zip([t for pair in p for t in pair], g): t -= lr * d
    with torch.no_grad():
        acc = lambda m: ((forward(p, X[m], act) > 0).double() == y[m]).double().mean().item()
        return first, loss(p, X[tr], y[tr], act).item(), acc(tr), acc(te)
ident = lambda z: z
print("\nnetwork        activation  rate  steps  loss before  loss after  train right  held out right")
rows = [([2, 8, 8, 1], torch.tanh, "tanh", 0.3, 2500), ([2, 8, 8, 1], ident, "linear", 0.3, 2500), ([2, 8, 8, 1], torch.tanh, "tanh", 0.003, 2500)]
res = {}
for sizes, act, name, lr, steps in rows:
    a, b, c, d = train(sizes, act, lr, steps); res[(name, lr)] = (c, d)
    print(f"{'-'.join(map(str, sizes)):<14} {name:<11} {lr:<5} {steps:<6} {a:<12.4f} {b:<11.4f} {c * 100:<12.1f} {d * 100:.1f}")
assert res[("tanh", 0.3)][0] >= 0.95 and res[("tanh", 0.3)][1] >= 0.9 and res[("linear", 0.3)][0] < 0.85 and res[("tanh", 0.003)][0] < res[("tanh", 0.3)][0]

# 4. Why the linear network can't: two linear layers are one linear layer.
(W1, b1), (W2, b2) = net([2, 8, 1], ident); x = torch.randn(5, 2)
two = (x @ W1.T + b1) @ W2.T + b2; one = x @ (W2 @ W1).T + (W2 @ b1 + b2); gap = (two - one).abs().max().item()
print(f"\ntwo linear layers against the single layer W2·W1: largest difference {gap:.1e}"); assert gap < 1e-12

# 5. The same block inside SD 1.5: every transformer block has a FeedForward, Linear then GEGLU then Linear, 4 times wider in the middle.
dim = 320; inner = dim * 4; ff = (dim * inner * 2 + inner * 2) + (inner * dim + dim)
print(f"\nSD 1.5 FeedForward at width {dim}: {dim} -> {inner} (gated, so {inner * 2} outputs) -> {dim}, {ff:,} weights and biases")
print(f"the browser lab's 2-8-8-1 network: {2 * 8 + 8 + 8 * 8 + 8 + 8 + 1} weights and biases")
