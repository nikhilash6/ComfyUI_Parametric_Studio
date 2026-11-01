# CU-265 lab: where a reference picture goes, using ports of StyleModelApply.apply_stylemodel and unCLIPConditioning.apply_adm in nodes.py and sdxl_pooled in comfy/model_base.py. Random numbers stand in for embeddings.
import torch
g = torch.Generator().manual_seed(0)
txt = torch.randn(1, 77, 768, generator=g); base = [[txt, {"pooled_output": torch.randn(1, 768, generator=g)}]]
class Out: pass
vision = Out(); vision.last_hidden_state = torch.randn(1, 257, 1024, generator=g); vision.image_embeds = torch.randn(1, 1024, generator=g)
def set_values(c, v, append=False):
    out = []
    for t in c:
        n = [t[0], t[1].copy()]
        for k, val in v.items():
            if append and n[1].get(k) is not None: val = n[1][k] + val
            n[1][k] = val
        out.append(n)
    return out
def unclip(c, output, strength, noise=0.):
    if strength == 0: return c
    return set_values(c, {"unclip_conditioning": [{"clip_vision_output": output, "strength": strength, "noise_augmentation": noise}]}, append=True)
def style(c, get_cond, output, strength=1.):
    cond = get_cond(output).flatten(start_dim=0, end_dim=1).unsqueeze(dim=0) * strength
    return [[torch.cat((t, cond), dim=1), d.copy()] for t, d in c]
adapter = lambda o: torch.randn(1, 8, 768, generator=torch.Generator().manual_seed(1))       # StyleAdapter: num_token=8, context_dim=768 in load_style_model
print("start                ", list(base[0][0].shape), sorted(base[0][1]))
s1 = style(base, adapter, vision); print("StyleModelApply      ", list(s1[0][0].shape), sorted(s1[0][1]))
u1 = unclip(base, vision, 1.); print("unCLIPConditioning   ", list(u1[0][0].shape), sorted(u1[0][1]))
u2 = unclip(u1, vision, .5); print("unCLIP twice: entries in the key:", len(u2[0][1]["unclip_conditioning"]))
print("unCLIP at strength 0 returns the input untouched:", unclip(base, vision, 0) is base)
assert s1[0][0].shape[1] == 85 and u1[0][0] is base[0][0] and len(u2[0][1]["unclip_conditioning"]) == 2
s0 = style(base, adapter, vision, 0.); print("\nstyle strength 0, multiply: tokens are still there,", s0[0][0].shape[1], "of them, all zeros:", s0[0][0][:, 77:].abs().max().item() == 0)
print("text tokens untouched by the style model:", torch.equal(s1[0][0][:, :77], txt))
assert torch.equal(s1[0][0][:, :77], txt)
# Redux: what load_style_model picks when the file has redux_down.weight.
redux_up = torch.nn.Linear(1152, 4096 * 3); redux_down = torch.nn.Linear(4096 * 3, 4096)
print("\nRedux maps each vision token from", redux_up.in_features, "to", redux_down.out_features, "numbers: the same width as T5-XXL's tokens")
vt = torch.randn(1, 4, 1152, generator=g); print("so 4 vision tokens become", list(redux_down(torch.nn.functional.silu(redux_up(vt))).shape))
# On SDXL, sdxl_pooled swaps the pooled text vector for the image one when the key exists.
def sdxl_pooled(args): return "image embedding through unclip_adm, first 1280 numbers" if "unclip_conditioning" in args else "pooled text"
print("\nSDXL global vector without the key:", sdxl_pooled(base[0][1])); print("SDXL global vector with the key:   ", sdxl_pooled(u1[0][1]))
