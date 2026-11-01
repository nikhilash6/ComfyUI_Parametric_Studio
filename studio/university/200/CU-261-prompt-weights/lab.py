# CU-261 lab: ports of parse_parentheses, token_weights and the weighting line of encode_token_weights in comfy/sd1_clip.py, compared with the real functions on a CPU.
import torch
def parse(s):
    r = []; cur = ""; n = 0
    for ch in s:
        if ch == "(":
            if n == 0:
                if cur: r.append(cur)
                cur = "("
            else: cur += ch
            n += 1
        elif ch == ")":
            n -= 1
            if n == 0: r.append(cur + ")"); cur = ""
            else: cur += ch
        else: cur += ch
    if cur: r.append(cur)
    return r
def tw(s, w=1.0):
    out = []
    for x in parse(s):
        wt = w
        if len(x) >= 2 and x[-1] == ")" and x[0] == "(":
            x = x[1:-1]; i = x.rfind(":"); wt *= 1.1
            if i > 0:
                try: wt = float(x[i + 1:]); x = x[:i]
                except: pass
            out += tw(x, wt)
        else: out += [(x, w)]
    return out
print("what you type                     what the parser hands on")
for p in ("a (brass) b", "a ((brass)) b", "a (brass:1.3) b", "a ((brass:1.3)) b", "((a (b:1.5) c))", "(brass:high)", "(a) (b:0)"):
    print(f"{p:<33} " + "  ".join(f"{t!r} {round(v, 4)}" for t, v in tw(p)))
assert tw("a ((brass)) b")[1] == ("brass", 1.1 * 1.1) and tw("a ((brass:1.3)) b")[1] == ("brass", 1.3) and tw("(brass:high)")[0] == ("brass:high", 1.1)
# encode_token_weights: z[j] = (z[j] - z_empty[j]) * weight + z_empty[j]. Weighting pivots on the empty prompt's row, not on zero.
torch.manual_seed(0)
z = torch.randn(4, 8); empty = torch.randn(4, 8) * .6
def weighted(j, w): return (z[j] - empty[j]) * w + empty[j]
print("\nweight   distance from this token's row   distance from the empty prompt's row   length")
for w in (0., .5, 1., 1.21, 1.5, 3.):
    v = weighted(2, w); print(f"{w:<8} {(v - z[2]).norm().item():<32.3f} {(v - empty[2]).norm().item():<38.3f} {v.norm().item():.3f}")
assert torch.allclose(weighted(2, 0.), empty[2]) and torch.allclose(weighted(2, 1.), z[2])
assert (weighted(2, 1.5) - 1.5 * z[2]).norm() > .1                                  # it is not a plain multiply
print("\nweight 0 gives the empty prompt's row at that position. The token is not removed: the tensor keeps its length.")
print("pooled_output comes from the unweighted pass: the line above only touches the token rows.")
