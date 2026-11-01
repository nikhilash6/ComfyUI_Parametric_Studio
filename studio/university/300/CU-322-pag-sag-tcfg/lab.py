# CU-322 lab: PAG, SAG and TCFG with a stand-in model that counts its own predictions. Ports of the post_cfg functions and score_tangential_damping, compared with the real nodes where they take plain tensors.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
calls = {"n": 0}
def predict(x, kind, perturbed=False): calls["n"] += 1; base = {"cond": 1.2, "uncond": .9}[kind]; return x * base * (.8 if perturbed else 1.)
def sampling_step(x, cfg, pag=None, sag=None, disable_opt=False):
    """sampling_function with the two post-cfg nodes: returns the guided result and the number of predictions."""
    calls["n"] = 0; disable = disable_opt or sag is not None; skip = math.isclose(cfg, 1.) and not disable
    c = predict(x, "cond"); u = torch.zeros_like(x) if skip else predict(x, "uncond"); d = u + (c - u) * cfg
    if pag not in (None, 0): d = d + (c - predict(x, "cond", True)) * pag                    # PerturbedAttentionGuidance
    if sag is not None: deg = u * .95; d = d + (deg - predict(deg + x - u, "uncond")) * sag   # SelfAttentionGuidance, with a stand-in for the blur
    return d, calls["n"]
x = torch.randn(8)
print("setup                          predictions per step   over 20 steps")
for name, cfg, kw, want in (("cfg 1", 1., {}, 1), ("cfg 7", 7., {}, 2), ("cfg 7 + TCFG", 7., {}, 2), ("cfg 1 + PAG 3", 1., {"pag": 3.}, 2), ("cfg 7 + PAG 3", 7., {"pag": 3.}, 3), ("cfg 7 + PAG scale 0", 7., {"pag": 0.}, 2), ("cfg 1 + SAG .5", 1., {"sag": .5}, 3), ("cfg 7 + SAG .5", 7., {"sag": .5}, 3), ("cfg 7 + PAG + SAG", 7., {"pag": 3., "sag": .5}, 4)):
    _, n = sampling_step(x, cfg, **kw); print(f"{name:<30} {n:<22} {n * 20}"); assert n == want
# What PAG breaks: the attention map becomes the identity, so each token gets back only its own value.
q = torch.randn(1, 6, 8); k = torch.randn(1, 6, 8); v = torch.randn(1, 6, 8)
normal = torch.softmax(q @ k.transpose(1, 2) / 8 ** .5, -1) @ v; perturbed = v   # perturbed_attention in nodes_pag.py: return v
print(f"\nPAG: normal attention moves each token by {(normal - v).norm(dim=-1).mean().item():.2f} on average. The perturbed version moves it by {(perturbed - v).norm().item():.1f}.")
assert (perturbed - v).norm() == 0 and (normal - v).norm() > .1
# TCFG: keep only the unconditional's part along the top shared direction.
def tangential(cs, us):
    b = cs.shape[0]; c = cs.reshape(b, 1, -1); u = us.reshape(b, 1, -1); _, _, Vh = torch.linalg.svd(torch.cat((u, c), 1), full_matrices=False); v1 = Vh[:, :1, :]; return ((u @ v1.transpose(-2, -1)) * v1).reshape_as(us)
cs = torch.randn(1, 4, 8, 8); us = .9 * cs + .3 * torch.randn(1, 4, 8, 8); td = tangential(cs, us)
print(f"TCFG: unconditional score length {us.norm().item():.3f}, after damping {td.norm().item():.3f}, what was removed {(us - td).norm().item():.3f}")
sim = lambda a, b: torch.nn.functional.cosine_similarity(a.flatten(1), b.flatten(1)).item()
print(f"      angle to the conditional: cosine {sim(us, cs):.3f} before, {sim(td, cs):.3f} after")
assert td.norm() < us.norm() and sim(td, cs) > sim(us, cs)
print("      model calls added by that: 0. The cost is one SVD per step.")
# SAG's map: where is mean attention above 1?
attn = torch.softmax(torch.randn(1, 16, 16) * 2, -1); summed = attn.sum(1)
print(f"SAG: tokens whose total incoming attention is above 1.0 are blurred. Here {int((summed > 1).sum())} of 16. The threshold is fixed at 1.0 in the source.")
assert 0 < int((summed > 1).sum()) < 16
