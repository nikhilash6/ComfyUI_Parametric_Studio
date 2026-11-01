# CU-262 lab: three ways to use two prompts. Ports of ConditioningCombine, ConditioningConcat, ConditioningAverage (nodes.py) and of the averaging in _calc_cond_batch (comfy/samplers.py).
# The model is a tiny cross-attention, so a nonlinear answer shows why blending answers differs from blending inputs.
import torch
torch.manual_seed(0); torch.set_num_threads(1)
DIM = 16; Q = torch.randn(6, DIM); calls = {"n": 0}
def model(ctx):
    calls["n"] += 1; w = torch.softmax(Q @ ctx.transpose(0, 1) * 1.5, -1); return w @ ctx
A = torch.randn(1, 77, DIM); B = torch.randn(1, 77, DIM)
PA, PB = torch.randn(1, 8), torch.randn(1, 8)
ca = [[A, {"pooled_output": PA}]]; cb = [[B, {"pooled_output": PB}]]
def combine(a, b): return a + b
def concat(to, frm):
    return [[torch.cat((t, frm[0][0]), 1), d.copy()] for t, d in to]
def average(to, frm, s):
    f = frm[0][0]; pf = frm[0][1].get("pooled_output"); out = []
    for t1, d in to:
        t0 = f[:, :t1.shape[1]]
        if t0.shape[1] < t1.shape[1]: t0 = torch.cat([t0, torch.zeros(1, t1.shape[1] - t0.shape[1], t1.shape[2])], 1)
        n = d.copy(); n["pooled_output"] = d["pooled_output"] * s + pf * (1 - s); out.append([t1 * s + t0 * (1 - s), n])
    return out
def predict(cond):
    """_calc_cond_batch: run each entry, add answer times weight, divide by the total weight."""
    out = torch.zeros(6, DIM); cnt = torch.ones(6, DIM) * 1e-37
    for t, d in cond: out += model(t[0]) * 1.0; cnt += 1.0
    return out / cnt
print("node       entries  tensor           predictions for the positive, per step")
res = {}
for name, c in (("Combine", combine(ca, cb)), ("Concat", concat(ca, cb)), ("Average", average(ca, cb, .5))):
    calls["n"] = 0; res[name] = predict(c); print(f"{name:<10} {len(c):<8} {str(list(c[0][0].shape)):<16} {calls['n']}"); res[name + "_c"] = c
assert len(res["Combine_c"]) == 2 and res["Concat_c"][0][0].shape[1] == 154 and res["Average_c"][0][0].shape[1] == 77
pa = model(A[0]); pb = model(B[0])
print("\nhow far apart the three answers are (one number each, on the same query)")
print(f"Combine against (answer A + answer B) / 2: {(res['Combine'] - (pa + pb) / 2).norm().item():.4f}")
print(f"Average against Combine:                   {(res['Average'] - res['Combine']).norm().item():.3f}")
print(f"Concat against Combine:                    {(res['Concat'] - res['Combine']).norm().item():.3f}")
print(f"Concat against Average:                    {(res['Concat'] - res['Average']).norm().item():.3f}")
assert (res["Combine"] - (pa + pb) / 2).norm() < 1e-5 and (res["Average"] - res["Combine"]).norm() > .1 and (res["Concat"] - res["Combine"]).norm() > .1
print("\nsmall print from the source")
long = [[torch.randn(1, 154, DIM), {"pooled_output": PB}]]
print("Average, 'from' longer than 'to':  result has", average(ca, long, .5)[0][0].shape[1], "tokens, the extra ones are cut")
short = [[torch.randn(1, 40, DIM), {"pooled_output": PB}]]
print("Average, 'from' shorter than 'to': result has", average(ca, short, .5)[0][0].shape[1], "tokens, the gap is filled with zeros")
print("Concat keeps the pooled vector of 'to' only:", torch.equal(concat(ca, cb)[0][1]["pooled_output"], PA))
print("Average at strength 1 is 'to' unchanged:", torch.equal(average(ca, cb, 1.0)[0][0], A))
assert torch.equal(concat(ca, cb)[0][1]["pooled_output"], PA)
