# CU-450 lab: what a dry run is for. A tiny version checker that says which packages a pack would move, and whether a constraints file catches it. All package names and versions are examples.
import re
def ver(s): return tuple(int(x) for x in re.findall(r"\d+", s))
def ok(v, spec):
    for part in filter(None, spec.split(",")):
        m = re.match(r"(==|>=|<=|<|>)(.+)", part.strip()); op, want = m.group(1), ver(m.group(2))
        if op == "==" and ver(v) != want: return False
        if op == ">=" and ver(v) < want: return False
        if op == "<=" and ver(v) > want: return False
        if op == "<" and ver(v) >= want: return False
        if op == ">" and ver(v) <= want: return False
    return True
assert ok("5.0.1", "<5") is False and ok("4.9", ">=4,<5") and ok("2.1", "==2.1")
INSTALLED = {"torch": "2.8.0", "numpy": "2.1.0", "opencv-python": "5.0.0", "safetensors": "0.5.3", "pillow": "11.0.0"}
PROTECT = {"torch", "numpy", "safetensors"}
CONSTRAINTS = {"torch": "==2.8.0", "numpy": "==2.1.0", "safetensors": "==0.5.3"}
AVAILABLE = {"numpy": ["1.26.4", "2.1.0", "2.3.0"], "opencv-python": ["4.11.0", "5.0.0"], "torch": ["2.5.0", "2.8.0"], "newlib": ["1.2.0"], "safetensors": ["0.5.3"]}
def resolve(req, constraints=None):
    """Pick the newest version that fits the pack's need and, if given, the constraints. A real resolver does far more."""
    moves = []; fails = []
    for name, spec in req.items():
        c = (constraints or {}).get(name, ""); fit = [v for v in AVAILABLE.get(name, []) if ok(v, spec) and ok(v, c)]
        if not fit: fails.append(f"{name}: nothing fits {spec} with {c or 'no constraint'}"); continue
        have = INSTALLED.get(name)
        if have and ok(have, spec) and ok(have, c): continue
        moves.append((name, have, sorted(fit, key=ver)[-1]))
    return moves, fails
PACKS = {"pack A, modest": {"newlib": ">=1.0", "numpy": ">=1.26"}, "pack B, wants old opencv": {"opencv-python": "<5"}, "pack C, wants old numpy": {"numpy": "<2"}, "pack D, pins torch": {"torch": "==2.5.0"}}
for label, cons in (("dry run with no constraints", None), ("dry run with the constraints file", CONSTRAINTS)):
    print(label)
    for name, req in PACKS.items():
        mv, fl = resolve(req, cons); tags = [f"{n} {a} -> {b}" + (" PROTECTED" if n in PROTECT else "") for n, a, b in mv]
        print(f"  {name:26s} {'; '.join(tags) or 'no moves'}{'  FAILS: ' + fl[0] if fl else ''}")
    print()
assert resolve(PACKS["pack C, wants old numpy"])[0][0][2] == "1.26.4"
assert resolve(PACKS["pack C, wants old numpy"], CONSTRAINTS)[1]
assert not resolve(PACKS["pack A, modest"], CONSTRAINTS)[1]
print("a failure in the second list is good news: it happened on paper, not in your environment")
print("\nwhat each layer of the method protects against")
for layer, stops in (("read the text first", "a surprise at import"), ("dry run with constraints", "a version moving under other packs"), ("a second venv", "breaking the one you use"), ("a container, no outside network, read-only models", "a pack reaching out, or changing weights"), ("a no-model graph, then a real graph", "a pack that imports but does not work"), ("--disable-all-custom-nodes", "not knowing whether a pack is to blame")):
    print(f"  {layer:50s} {stops}")
