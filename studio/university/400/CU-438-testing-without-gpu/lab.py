# CU-438 lab: plain tests for a node, run against a good node and six broken ones. The node class is real Python with a tiny stand-in for the base class. Real engine tests, which need ComfyUI on the import path, are in the lesson with their output.
import torch
class Out:
    def __init__(self, *a): self.args = a
def schema_ok(s):
    ids = [i[0] for i in s]
    if len(set(ids)) != len(ids): raise ValueError(f"Input ids must be unique, but {[x for x in ids if ids.count(x) > 1][:1]} are not.")
    for _, o in s:
        if "min" in o and "max" in o and o["min"] > o["max"]: raise ValueError("min above max")
        if "default" in o and "min" in o and not o["min"] <= o["default"] <= o["max"]: raise ValueError("default out of range")
GOOD = [("image", {}), ("amount", {"default": 1.0, "min": 0.0, "max": 4.0})]
class Good:
    schema = GOOD
    @classmethod
    def execute(cls, image, amount): return Out(torch.clamp(image * amount, 0, 1))
class InPlace(Good):
    @classmethod
    def execute(cls, image, amount): image *= amount; image.clamp_(0, 1); return Out(image)
class NoClamp(Good):
    @classmethod
    def execute(cls, image, amount): return Out(image * amount)
class Swapped(Good):
    schema = [("image", {}), ("amount", {"default": 1.0, "min": 4.0, "max": 0.0})]
class DupId(Good):
    schema = [("image", {}), ("image", {})]
class Stateful(Good):
    calls = {"n": 0}
    @classmethod
    def execute(cls, image, amount): cls.calls["n"] += 1; return Out(torch.clamp(image * amount + 0.001 * cls.calls["n"], 0, 1))
class Squeezed(Good):
    @classmethod
    def execute(cls, image, amount): return Out(torch.clamp(image * amount, 0, 1)[0])
def t_schema(N): schema_ok(N.schema)
def t_input_untouched(N):
    x = torch.full((1, 2, 2, 3), 0.25); y = x.clone(); N.execute(x, 2.0); assert torch.equal(x, y), "input changed"
def t_range(N):
    r = N.execute(torch.full((1, 2, 2, 3), 0.75), 4.0).args[0]; assert 0 <= r.min() and r.max() <= 1, "out of 0 to 1"
def t_shape(N):
    x = torch.zeros(2, 4, 6, 3); assert N.execute(x, 1.0).args[0].shape == x.shape, "shape changed"
def t_same_twice(N):
    x = torch.full((1, 2, 2, 3), 0.25); assert torch.equal(N.execute(x.clone(), 2.0).args[0], N.execute(x.clone(), 2.0).args[0]), "different answers"
TESTS = [t_schema, t_input_untouched, t_range, t_shape, t_same_twice]
print(f"{'node':10}" + "".join(f"{t.__name__[2:]:17}" for t in TESTS))
res = {}
for N in (Good, InPlace, NoClamp, Swapped, DupId, Stateful, Squeezed):
    row = []
    for t in TESTS:
        try: t(N); row.append("pass")
        except Exception as e: row.append("FAIL")
    res[N.__name__] = row; print(f"{N.__name__:10}" + "".join(f"{x:17}" for x in row))
assert res["Good"] == ["pass"] * 5 and res["InPlace"][1] == "FAIL" and res["NoClamp"][2] == "FAIL" and res["Swapped"][0] == "FAIL" and res["DupId"][0] == "FAIL" and res["Stateful"][4] == "FAIL" and res["Squeezed"][3] == "FAIL"
assert all("FAIL" in res[k] for k in res if k != "Good")
