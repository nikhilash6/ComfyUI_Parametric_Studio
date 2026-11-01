# CU-251 lab: cfg is a sum outside the model, embedded guidance is an input to it. Ports of cfg_function, sampling_function's skip and Flux's timestep_embedding.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
calls = {"n": 0}
class MockModel:
    """Stands in for the transformer. Its answer depends on the prompt and, if it has guidance_in, on the guidance number."""
    def __init__(self, guidance_embed): self.guidance_embed = guidance_embed
    def __call__(self, x, prompt, guidance):
        calls["n"] += 1
        vec = embed(torch.tensor([1.0]))                        # the timestep's vector; the same for every call here
        if self.guidance_embed and guidance is not None: vec = vec + embed(torch.tensor([guidance]))  # forward_orig: vec = vec + guidance_in(...)
        return x * .9 + prompt * (1 + vec.mean().item() * .5)
def embed(t, dim=256, max_period=10000, time_factor=1000.0):
    """timestep_embedding in comfy/ldm/flux/layers.py."""
    t = time_factor * t; half = dim // 2; freqs = torch.exp(-math.log(max_period) * torch.arange(half, dtype=torch.float32) / half); a = t[:, None].float() * freqs[None]
    return torch.cat([torch.cos(a), torch.sin(a)], dim=-1)
def step(model, x, pos, neg, cfg, guidance):
    """sampling_function then cfg_function: at cfg 1 the second conditioning is never run."""
    c = model(x, pos, guidance)
    if math.isclose(cfg, 1.0): return c
    u = model(x, neg, guidance); return u + (c - u) * cfg
x = torch.randn(8); POS = torch.randn(8); NEG = torch.randn(8); OTHER = torch.randn(8)
print("20 steps                                    predictions   negative matters   guidance number matters")
def row(name, emb, cfg):
    m = MockModel(emb); calls["n"] = 0
    for _ in range(20): a = step(m, x, POS, NEG, cfg, 3.5)
    n = calls["n"]; b = step(m, x, POS, OTHER, cfg, 3.5); g = step(m, x, POS, NEG, cfg, 1.0)
    negm = not torch.equal(a, b); gm = not torch.equal(a, g)
    print(f"{name:<43} {n:<13} {str(negm):<18} {gm}"); return n, negm, gm
A = row("no guidance_in, cfg 7 (SD 1.5, SDXL, SD 3.5)", False, 7.)
B = row("no guidance_in, cfg 1 (a distilled file)", False, 1.)
C = row("has guidance_in, cfg 1 (FLUX.1 dev)", True, 1.)
D_ = row("has guidance_in, cfg 3.5 (both at once)", True, 3.5)
assert A == (40, True, False) and B == (20, False, False) and C == (20, False, True) and D_ == (40, True, True)
print("\nwhat the model is handed as the guidance number: a 256-long vector, like the one for the timestep")
for g in (1.0, 3.5, 3.6, 10.0):
    e = embed(torch.tensor([g])); print(f"guidance {g:<5} first values {e[0, 0].item():+.3f} {e[0, 1].item():+.3f} {e[0, 2].item():+.3f}   size {e.norm().item():.2f}   difference from 3.5: {(e - embed(torch.tensor([3.5]))).norm().item():.2f}")
