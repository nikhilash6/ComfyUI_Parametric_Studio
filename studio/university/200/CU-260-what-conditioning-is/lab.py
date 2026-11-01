# CU-260 lab: CONDITIONING is a plain Python list. Each function below is a port of the node named beside it, compared with the real node on a CPU.
import torch
def show(name, c): print(f"{name:<34} {len(c)} entr{'y' if len(c) == 1 else 'ies'}   " + "   ".join(f"{list(t.shape)} {sorted(d)}" for t, d in c))
def set_values(c, values):                                             # node_helpers.conditioning_set_values
    out = []
    for t in c: n = [t[0], t[1].copy()]; n[1].update(values); out.append(n)
    return out
def encode(seed):                                                     # the shape CLIPTextEncode returns on SD 1.5
    g = torch.Generator().manual_seed(seed); return [[torch.randn(1, 77, 768, generator=g), {"pooled_output": torch.randn(1, 768, generator=g)}]]
def combine(a, b): return a + b                                       # ConditioningCombine.combine
def set_area(c, w, h, x, y, s=1.0): return set_values(c, {"area": (h // 8, w // 8, y // 8, x // 8), "strength": s, "set_area_to_bounds": False})    # ConditioningSetArea.append
def set_range(c, a, b): return set_values(c, {"start_percent": a, "end_percent": b})                                                                # ConditioningSetTimestepRange.set_range
def zero_out(c): return [[torch.zeros_like(t), {**d, "pooled_output": torch.zeros_like(d["pooled_output"])}] for t, d in c]                         # ConditioningZeroOut.zero_out
A = encode(1); B = encode(2)
show("CLIPTextEncode", A)
area = set_area(A, 256, 256, 256, 200); show("ConditioningSetArea", area)
ranged = set_range(area, 0, .5); show("then SetTimestepRange", ranged)
both = combine(ranged, B); show("then Combine with a second prompt", both)
assert isinstance(A, list) and isinstance(A[0][0], torch.Tensor) and isinstance(A[0][1], dict)
print("\nthe tensor is shared, the dict is copied")
print("SetArea made a new tensor:", area[0][0] is not A[0][0], "   and changed the original dict:", "area" in A[0][1])
assert area[0][0] is A[0][0] and "area" not in A[0][1]
again = set_range(ranged, .3, .9); print("a second SetTimestepRange keeps", (again[0][1]["start_percent"], again[0][1]["end_percent"]), "and forgets", (0, .5))
assert again[0][1]["end_percent"] == .9
z = zero_out(A); print("\nZeroOut: largest value", z[0][0].abs().max().item(), "  shape unchanged:", z[0][0].shape == A[0][0].shape)
assert z[0][0].abs().max() == 0
# convert_cond in comfy/sampler_helpers.py, the first thing the sampler does with the list.
def convert(c): return [{**d, "cross_attn": t, "model_conds": d.get("model_conds", {})} for t, d in c]
conv = convert(both); print("\nwhat the sampler turns the list into: a list of plain dicts")
for d in conv: print(sorted(d))
assert all("cross_attn" in d for d in conv)
