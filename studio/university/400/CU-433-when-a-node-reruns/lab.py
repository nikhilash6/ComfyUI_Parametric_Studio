# CU-433 lab: why each fingerprint value does or does not re-run. Python's own == on the key is what decides, as in the real cache. The engine parts are a stand-in, and each count below matches a real run of three queues in the lesson.
import math, hashlib
class Node: pass
def key(fp): return ("MyNode", (fp,), ("x", 1))       # class, fingerprint, inputs: the shape of CacheKeySetInputSignature's signature
def queue(fn, n=3):
    cache = []; runs = 0
    for _ in range(n):
        k = key(fn())
        if not any(k == c for c in cache): runs += 1; cache.append(k)
    return runs
SHARED = float("nan"); counter = [0]
def tick(): counter[0] += 1; return counter[0]
cases = [("no hook (False is what the engine uses)", lambda: False), ("return None", lambda: None), ("return a fixed string", lambda: "same"),
         ('return float("NaN"), a new object each time', lambda: float("NaN")), ("return math.nan, one shared object", lambda: math.nan),
         ("a module-level NaN, one shared object", lambda: SHARED), ("a counter that goes up", tick)]
print("what the hook returns                            runs in 3 queues")
res = {}
for name, fn in cases:
    r = queue(fn); res[name] = r; print(f"{name:48} {r}")
assert res['return float("NaN"), a new object each time'] == 3 and res["return math.nan, one shared object"] == 1 and res["no hook (False is what the engine uses)"] == 1
n = float("nan"); print(f"\nnan == nan: {n == n}   (n,) == (n,): {(n,) == (n,)}   (float('nan'),) == (float('nan'),): {(float('nan'),) == (float('nan'),)}")
assert (n,) == (n,) and (float("nan"),) != (float("nan"),)

# Hash a file: the honest fingerprint.
FILES = {"a.png": b"first version"}
def fp_file(): return hashlib.sha256(FILES["a.png"]).hexdigest()
cache = set(); log = []
for edit in (None, None, b"second version", None):
    if edit: FILES["a.png"] = edit
    k = key(fp_file()); log.append(k not in cache); cache.add(k)
print("file hash, queue 4 times, file edited before the 3rd:", log)
assert log == [True, False, True, False]

# validate_inputs: naming an input in your function switches off the built-in range check for it. A port of that branch of execution.py.
SPEC = {"p": {"min": 0, "max": 10}, "q": {"min": 0, "max": 10}}
def custom(p): return True if p % 2 == 0 else f"p must be even, got {p}"
def validate(values, fn, named):
    errs = []
    for k, v in values.items():
        if k in named: continue                       # "if x not in validate_function_inputs and not validate_has_kwargs"
        if v > SPEC[k]["max"]: errs.append(("value_bigger_than_max", k))
    r = fn(values["p"])
    if r is not True: errs.append(("custom_validation_failed", f"p - {r}"))
    return errs
print("\nvalidate_inputs(p) on an input with max 10")
for pq in ((3, 1), (100, 1), (2, 100), (2, 1)):
    e = validate({"p": pq[0], "q": pq[1]}, custom, {"p"}); print(f"p={pq[0]:<4} q={pq[1]:<4} {e or 'passes'}")
assert validate({"p": 100, "q": 1}, custom, {"p"}) == [] and validate({"p": 2, "q": 100}, custom, {"p"})[0][0] == "value_bigger_than_max"
