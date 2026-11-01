# CU-403 lab: the three merges, the size of the result, ComfyUI's ratio, and what quantizing first does. Stand-in weights, not a real model.
# The ratio follows ModelMergeSimple in comfy_extras/nodes_model_merging.py and comfy/lora.py calculate_weight. FP8 with a stored scale follows CU-211: scale = largest value / 448.
import math, torch
torch.set_num_threads(1); g = torch.Generator().manual_seed(0); R = lambda *s: torch.randn(*s, generator=g)
n = 1_000_000; base = 0.02 * R(n)
A = base + 0.002 * R(n); B = base + 0.002 * R(n)         # two fine-tunes of one base: small changes
def lerp(a, b, t): return (1 - t) * a + t * b
def slerp(a, b, t):
    ua, ub = a / a.norm(), b / b.norm(); th = torch.acos((ua * ub).sum().clamp(-1, 1)); return (torch.sin((1 - t) * th) * ua + torch.sin(t * th) * ub) / torch.sin(th)
def task(base, a, b, x, y): return base + x * (a - base) + y * (b - base)
cos = lambda a, b: ((a * b).sum() / (a.norm() * b.norm())).item()
# 1. Size of the merge. Far apart, near parallel.
print("weights of the same size at an angle: size of the halfway blend, against the parents' 1.0000")
print("angle (degrees)   lerp     slerp")
for deg in (1, 10, 45, 90, 135):
    th = math.radians(deg); a = torch.tensor([1.0, 0.0]); b = torch.tensor([math.cos(th), math.sin(th)])
    l, s = lerp(a, b, .5).norm().item(), slerp(a, b, .5).norm().item(); print(f"{deg:<17} {l:<8.4f} {s:.4f}")
    assert abs(l - math.cos(th / 2)) < 1e-5 and abs(s - 1) < 1e-5
print(f"\nour two fine-tunes: angle {math.degrees(math.acos(cos(A, B))):.2f} degrees, size of A {A.norm().item():.4f}, of B {B.norm().item():.4f}")
L, S = lerp(A, B, .5), slerp(A, B, .5) * (A.norm() + B.norm()) / 2
print(f"lerp size {L.norm().item():.4f}   slerp scaled to the mean size {S.norm().item():.4f}   largest difference between them {(L - S).abs().max().item():.2e}, against typical weight 0.02")
T = task(base, A, B, .5, .5); print(f"task arithmetic 0.5 and 0.5 against lerp: largest difference {(T - L).abs().max().item():.1e} (the same sum)")
assert (T - L).abs().max() < 1e-6
T2 = task(base, A, B, 1, 1); da = (A - base); db = (B - base)
print(f"task arithmetic 1 and 1 keeps each change whole: share of A's change present {((T2 - base) * da).sum().item() / (da * da).sum().item():.3f}   lerp 0.5 keeps {((L - base) * da).sum().item() / (da * da).sum().item():.3f}")
# 2. ComfyUI's ratio
w1, w2 = torch.full((2,), 10.0), torch.full((2,), 2.0)
def simple(m1, m2, ratio): return m1 * ratio + (1.0 - ratio) * m2      # add_patches(k, 1 - ratio, ratio): model1 x ratio + model2 x (1 - ratio)
print("\nModelMergeSimple, model1 = 10, model2 = 2")
print("ratio   result")
for r in (1.0, 0.7, 0.3, 0.0):
    print(f"{r:<7} {simple(w1, w2, r)[0].item():.1f}")
assert simple(w1, w2, 1.0)[0] == 10.0 and abs(simple(w1, w2, .3)[0].item() - 4.4) < 1e-5
# 3. Merge first or quantize first. E4M3 FP8 with a scale, rounded to nearest; bf16 and fp16 are plain casts.
def fp8(x):
    s = x.abs().max() / 448.0; return (x / s).clamp(-448, 448).to(torch.float8_e4m3fn).to(torch.float32) * s
def bf(x): return x.to(torch.bfloat16).to(torch.float32)
def hf(x): return x.to(torch.float16).to(torch.float32)
rms = lambda x: x.pow(2).mean().sqrt().item()
truth = lerp(A, B, .5)
print("\nhalfway merge of two fine-tunes. Error against the merge done in full precision, as a share of the weights' size")
print("parents stored as   merged, then stored in the same format   merged from those parents, then stored")
tab = {}
for name, q in (("float32", lambda x: x), ("fp16", hf), ("bf16", bf), ("FP8", fp8)):
    one = rms(q(truth) - truth) / rms(truth); two = rms(q(lerp(q(A), q(B), .5)) - truth) / rms(truth); tab[name] = (one, two)
    print(f"{name:<19} {one:<40.5f} {two:.5f}")
assert tab["FP8"][1] > tab["FP8"][0] * 1.1 and tab["FP8"][0] > 10 * tab["bf16"][0]
print("\nthe task vector B - base, read from stored parents. The change is 10% of the weight's size here. Error as a share of the change")
print("parents stored as   error / change   share of the change kept   correlation with the true change")
want = B - base; add = {}
for name, q in (("float32", lambda x: x), ("fp16", hf), ("bf16", bf), ("FP8", fp8)):
    d = q(B) - q(base); err = rms(d - want) / rms(want); keep = (d * want).sum().item() / (want * want).sum().item(); add[name] = err
    print(f"{name:<19} {err:<16.3f} {keep:<26.3f} {cos(d, want):.3f}")
assert add["FP8"] > 0.3 and add["bf16"] < 0.05
print("\nthe same difference with a smaller change (what happens to fine-tunes that barely moved a weight), FP8 parents")
print("change / weight   error / change   correlation with the true change")
small = {}
for frac in (0.1, 0.03, 0.01):
    b2 = base + frac * 0.02 * R(n); d = fp8(b2) - fp8(base); w = b2 - base; small[frac] = rms(d - w) / rms(w)
    print(f"{frac:<17} {small[frac]:<16.3f} {cos(d, w):.3f}")
assert small[0.01] > small[0.1]
print("\nrounding errors add along a chain of merges. Four parents, FP8. Error as a share of the weights' size")
C = base + 0.002 * R(n); D = base + 0.002 * R(n); truth3 = (A + B + C + D) / 4; y = fp8(lerp(fp8(lerp(fp8(A), fp8(B), .5)), fp8(lerp(fp8(C), fp8(D), .5)), .5))
print(f"four parents, rounded at every merge          {rms(y - truth3) / rms(truth3):.5f}")
print(f"four parents, full precision, rounded once    {rms(fp8(truth3) - truth3) / rms(truth3):.5f}")
assert rms(y - truth3) > rms(fp8(truth3) - truth3)
