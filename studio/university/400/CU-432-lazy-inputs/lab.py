# CU-432 lab: the lazy loop of execute() in execution.py, on a small stand-in for the engine with made-up node classes. Not ComfyUI itself. The event order matches a real run in the lesson.
LOG = []
class Tick:                                      # an expensive branch
    OPTS = {}
    def run(self, tag): LOG.append(f"branch {tag} runs"); return f"result {tag}"
class Switch:
    LAZY = {"a", "b"}
    def check_lazy_status(self, use_a, a=None, b=None):
        LOG.append(f"check_lazy_status a={'value' if a else None} b={'value' if b else None}")
        return ["a"] if use_a else ["b"]
    def run(self, use_a, a=None, b=None): LOG.append("execute"); return a if use_a else b
class Eager:
    LAZY = set()
    def run(self, use_a, a=None, b=None): LOG.append("execute"); return a if use_a else b
class TwoWay(Switch):                            # a bad check: it asks for an input that is a constant
    def check_lazy_status(self, use_a, a=None, b=None): return ["a"]
CL = {"Tick": Tick, "Switch": Switch, "Eager": Eager, "TwoWay": TwoWay}
def is_link(v): return isinstance(v, list) and len(v) == 2
def run(prompt, out):
    done = {}
    def ev(i):
        if i in done: return done[i]
        n = prompt[i]; c = CL[n["class_type"]](); lazy = getattr(c, "LAZY", set()); ins = n["inputs"]
        for k, v in ins.items():
            if is_link(v) and k not in lazy: ev(v[0])
        while True:
            args = {k: (done.get(v[0]) if is_link(v) else v) for k, v in ins.items()}
            if not hasattr(c, "check_lazy_status"): break
            want = [k for k in c.check_lazy_status(**args) if args.get(k) is None]   # names with a value already are dropped, as in execute()
            if not want: break
            for k in want:                             # make_input_strong_link in comfy_execution/graph.py
                if k not in ins: raise RuntimeError(f"Node {i} says it needs input {k}, but there is no input to that node at all")
                ev(ins[k][0])
        done[i] = c.run(**args); return done[i]
    return ev(out)
g = lambda cls, ua: {"A": {"class_type": "Tick", "inputs": {"tag": "A"}}, "B": {"class_type": "Tick", "inputs": {"tag": "B"}},
                     "S": {"class_type": cls, "inputs": {"use_a": ua, "a": ["A", 0], "b": ["B", 0]}}}
for cls, ua in (("Switch", True), ("Switch", False), ("Eager", True)):
    LOG.clear(); r = run(g(cls, ua), "S"); print(f"{cls}, use_a={ua}: {r}"); [print("   ", l) for l in LOG]
    if cls == "Switch": assert LOG.count("execute") == 1 and sum("branch" in l for l in LOG) == 1 and sum("check" in l for l in LOG) == 2
    else: assert sum("branch" in l for l in LOG) == 2
print()
try: run({"S": {"class_type": "TwoWay", "inputs": {"use_a": True}}}, "S")
except RuntimeError as e: print(f"asks for an input with no wire: {e}"); last = str(e)
assert "no input to that node" in last
# Wrong and right ways to write the check.
def always(use_a, a=None, b=None): return ["a", "b"]
print("\nasking for every input, every time, undoes the saving:", always(True))
assert always(True) == ["a", "b"]
