# CU-505 lab: a miniature CLIP. Two linear encoders, the symmetric contrastive loss of the CLIP paper (its Figure 3), and zero-shot use.
# World: 12 shapes x 10 colours = 120 concepts. An "image" is a 64-number vector, shape part + colour part + noise. A "caption" names the shape and the colour.
# 20 of the 120 combinations are never shown in training, so classifying them is zero-shot. Chance is 1 in 120.
# Run: python lab.py  (CPU only, about 15 s). Prints the same numbers every time.
import math, torch
torch.set_num_threads(1)
F = torch.nn.functional
S, C, DI, DE, NOISE = 12, 10, 64, 16, 2.0
g = torch.Generator().manual_seed(0)
SHAPE, COLOUR = torch.randn(S, DI, generator=g), torch.randn(C, DI, generator=g)
combos = [(s, k) for s in range(S) for k in range(C)]; perm = torch.randperm(len(combos), generator=g).tolist()
held, seen = [combos[i] for i in perm[:20]], [combos[i] for i in perm[20:]]
def images(cs, gen): return SHAPE[[a for a, b in cs]] + COLOUR[[b for a, b in cs]] + NOISE * torch.randn(len(cs), DI, generator=gen)
def captions(cs): v = torch.zeros(len(cs), S + C); v[torch.arange(len(cs)), torch.tensor([a for a, b in cs])] = 1; v[torch.arange(len(cs)), S + torch.tensor([b for a, b in cs])] = 1; return v
ALL = captions(combos)                                                          # the 120 candidate captions

def clip_loss(Ie, Te, scale):                                                   # Figure 3 of the paper: normalise, scaled cosine similarities, cross entropy both ways, average
    logits = Ie @ Te.T * scale; n = len(Ie); y = torch.arange(n)
    return (F.cross_entropy(logits, y) + F.cross_entropy(logits.T, y)) / 2
def train(seed, tau=None, N=32, steps=600):                                     # tau None: learn the temperature, start at 0.07, clip the logit scale at 100 (CLIP section 2.5)
    torch.manual_seed(seed); gen = torch.Generator().manual_seed(100 + seed); Wi, Wt = torch.nn.Linear(DI, DE, bias=False), torch.nn.Linear(S + C, DE, bias=False)
    t = torch.nn.Parameter(torch.tensor(math.log(1 / (0.07 if tau is None else tau))), requires_grad=tau is None)
    opt = torch.optim.Adam(list(Wi.parameters()) + list(Wt.parameters()) + ([t] if tau is None else []), 3e-3); losses = []
    for _ in range(steps):
        cs = [seen[j] for j in torch.randperm(len(seen), generator=gen)[:N].tolist()]                       # N different concepts, so the diagonal is the only right answer
        loss = clip_loss(F.normalize(Wi(images(cs, gen)), dim=1), F.normalize(Wt(captions(cs)), dim=1), t.exp()); opt.zero_grad(); loss.backward(); opt.step(); losses.append(loss.item())
        if tau is None: t.data.clamp_(max=math.log(100))
    with torch.no_grad():
        Tall = F.normalize(Wt(ALL), dim=1); acc = []
        for group in (seen, held):                                                                          # classify fresh images among all 120 captions
            cs = group * 20; pred = (F.normalize(Wi(images(cs, torch.Generator().manual_seed(7))), dim=1) @ Tall.T).argmax(1)
            acc.append((pred == torch.tensor([combos.index(c) for c in cs])).float().mean().item())
    return sum(losses[-100:]) / 100, math.exp(-t.item()), acc

# 1. What the loss can reach. A model that gives every caption the same score has loss ln N. With cosine similarities and temperature tau, the best
#    arrangement puts each image on its caption (cosine 1) and the N captions as far apart as N unit vectors can be (every pair at cosine -1/(N-1)).
def best_case(N, tau): return math.log(1 + (N - 1) * math.exp((-1 / (N - 1) - 1) / tau))
print("batch size N   loss of a model with no idea, ln N"); [print(f"{n:<14d} {math.log(n):.4f}") for n in (8, 32, 100)]

# 2. One run with the temperature learned, like CLIP, then the zero-shot test.
loss, tau, (a_seen, a_held) = train(0)
print(f"\nlearned temperature: tau started at 0.0700 and ended at {tau:.4f}; loss over the last 100 steps {loss:.4f}")
print(f"zero-shot, 1 correct caption among 120: images of the 100 combinations used in training {a_seen:.3f}, of the 20 never used {a_held:.3f}, chance {1 / 120:.3f}")
assert a_held > 0.5 and a_seen > 0.5

# 3. The temperature, fixed at four values. Mean of 3 seeds. Batch of 32.
print("\ntau     best case at N = 32   loss after 600 steps   zero-shot on the 20 unused combinations")
for tau_ in (1.0, 0.3, 0.07, 0.01):
    runs = [train(s, tau=tau_) for s in range(3)]; l = sum(r[0] for r in runs) / 3; a = sum(r[2][1] for r in runs) / 3
    print(f"{tau_:<7.2f} {best_case(32, tau_):<21.4f} {l:<22.4f} {a:.3f}"); assert l >= best_case(32, tau_)

# 4. The batch size, temperature learned. Mean of 3 seeds. More captions in the batch means more wrong answers to rule out.
print("\nbatch N   chance loss ln N   loss after 600 steps   zero-shot on the 20 unused combinations")
for n in (8, 32, 100):
    runs = [train(s, N=n) for s in range(3)]; print(f"{n:<9d} {math.log(n):<18.4f} {sum(r[0] for r in runs) / 3:<22.4f} {sum(r[2][1] for r in runs) / 3:.3f}")
