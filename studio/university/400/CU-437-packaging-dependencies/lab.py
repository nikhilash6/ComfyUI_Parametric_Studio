# CU-437 lab: three things a pack author can get wrong, each small enough to show here. The loader rules are a port of load_custom_node and init_external_custom_nodes in nodes.py. The version check is a teaching model of one idea, not pip's resolver.
import re
def parse(v): return tuple(int(x) for x in v.split("."))
def ok(version, spec):
    m = re.fullmatch(r"(==|>=|<=|<|>|~=)(.+)", spec)
    if not m: return True
    a, b = parse(version), parse(m[2]); op = m[1]
    return {"==": a == b, ">=": a >= b, "<=": a <= b, "<": a < b, ">": a > b, "~=": a >= b and a[:len(b) - 1] == b[:-1]}[op]
HOST = {"torch": "2.6.0", "numpy": "1.26.4", "pillow": "10.4.0", "transformers": "4.50.3"}
def would_move(reqs):
    return [f"{n} {HOST[n]} (asked {s})" for n, s in reqs if n in HOST and not ok(HOST[n], s)]
for label, reqs in (("pins everything", [("torch", "==2.1.0"), ("numpy", "==1.24.0"), ("pillow", "==9.5.0")]), ("floors only", [("numpy", ">=1.25"), ("pillow", ">=10.0")]), ("only what is new", [("opencv-python", ">=4.8")])):
    m = would_move(reqs); print(f"{label:18} would move: {m or 'nothing'}")
assert len(would_move([("torch", "==2.1.0"), ("numpy", "==1.24.0"), ("pillow", "==9.5.0")])) == 3 and would_move([("numpy", ">=1.25")]) == []
# Load order. ignore= holds core names, so core always wins. Between two packs, the last loaded wins, and the order is os.listdir's.
core = {"KSampler": "core"}; base = set(core); table = dict(core); log = []
def load(pack, mapping):
    for name, cls in mapping.items():
        if name not in base: table[name] = cls
        else: log.append(f"{pack} tried to replace core {name}: ignored")
load("pack_a", {"KSampler": "pack_a", "Blur": "pack_a"}); load("pack_b", {"Blur": "pack_b"})
print("\ntable:", table); print(log[0]); assert table == {"KSampler": "core", "Blur": "pack_b"}
print("so prefix your ids: MyPack_Blur clashes only if another pack picks the same prefix")
# An import error costs the whole pack, and nothing else.
def try_import(name, fn, result):
    try: fn(); result.append((name, "loaded"))
    except Exception as e: result.append((name, f"IMPORT FAILED: {type(e).__name__}: {e}"))
def bad(): raise ModuleNotFoundError("No module named 'cv2'")
res = []; try_import("pack_a", lambda: None, res); try_import("pack_b", bad, res); try_import("pack_c", lambda: None, res)
print(); [print(a, b) for a, b in res]; assert res[1][1].startswith("IMPORT FAILED") and res[2][1] == "loaded"
# Registering. NODE_CLASS_MAPPINGS is read first, and if it is there comfy_entrypoint is never called.
def how(module): return "V1 table" if module.get("NODE_CLASS_MAPPINGS") is not None else "comfy_entrypoint" if "comfy_entrypoint" in module else "skipped: need one of them"
print(); [print(k, "->", how(m)) for k, m in (("both", {"NODE_CLASS_MAPPINGS": {}, "comfy_entrypoint": 1}), ("v3", {"comfy_entrypoint": 1}), ("neither", {}))]
assert how({"NODE_CLASS_MAPPINGS": {}, "comfy_entrypoint": 1}) == "V1 table"
