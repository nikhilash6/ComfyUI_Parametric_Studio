# CU-435 lab: node expansion on a small stand-in engine. GraphBuilder's id rule is ported from comfy_execution/graph_utils.py. The engine is much simplified. The ids and the result match a real run in the lesson.
class Node:
    def __init__(self, id, cls, inputs): self.id, self.cls, self.inputs = id, cls, inputs
    def out(self, i): return [self.id, i]
class GraphBuilder:
    root, call, graph = "", 0, 0
    @classmethod
    def set_default_prefix(cls, root, call, graph=0): cls.root, cls.call, cls.graph = root, call, graph
    def __init__(self):
        self.prefix = f"{GraphBuilder.root}.{GraphBuilder.call}.{GraphBuilder.graph}."; GraphBuilder.graph += 1; self.nodes = {}; self.n = 1
    def node(self, cls, **inputs):
        i = self.prefix + str(self.n); self.n += 1; self.nodes[i] = Node(i, cls, inputs); return self.nodes[i]
    def finalize(self): return {k: {"class_type": v.cls, "inputs": v.inputs} for k, v in self.nodes.items()}
RAN = []
def invert(image): RAN.append("ImageInvert"); return round(1 - image, 4)
def expand_node(image, times):
    g = GraphBuilder(); last = None
    for _ in range(times): last = g.node("ImageInvert", image=last.out(0) if last else image)
    return {"result": (last.out(0),), "expand": g.finalize()}
def bad_class(image):
    g = GraphBuilder(); n = g.node("NoSuchNode", image=image); return {"result": (n.out(0),), "expand": g.finalize()}
CLASSES = {"ImageInvert": invert}
def resolve(v, graph, done):
    if isinstance(v, list): return ev(v[0], graph, done)
    return v
def ev(i, graph, done):
    if i in done: return done[i]
    n = graph[i]
    if n["class_type"] not in CLASSES: raise KeyError(n["class_type"])                 # execute() reads NODE_CLASS_MAPPINGS[class_type]
    done[i] = CLASSES[n["class_type"]](**{k: resolve(v, graph, done) for k, v in n["inputs"].items()})
    return done[i]
def run_expanding(uid, fn, call_index=0, **inputs):
    GraphBuilder.set_default_prefix(uid, call_index, 0)                                  # pre_execute_cb in execution.py
    r = fn(**inputs); graph = r["expand"]; print(f"  node {uid} added:", list(graph))
    return ev(r["result"][0][0], graph, {})
print("times=3, picture mean 0.1255"); v = run_expanding("2", expand_node, image=0.1255, times=3); print("  result", v, " inverts that ran:", len(RAN))
assert v == 0.8745 and len(RAN) == 3
RAN.clear(); print("times=6"); v = run_expanding("2", expand_node, image=0.1255, times=6); print("  result", v, " inverts that ran:", len(RAN)); assert v == 0.1255
print("second call in a list, call index 1"); RAN.clear(); run_expanding("2", expand_node, call_index=1, image=0.1255, times=2)
print("a second builder in one call gets its own prefix"); GraphBuilder.set_default_prefix("2", 0, 0); a = GraphBuilder(); b = GraphBuilder(); print("  ", a.prefix, b.prefix); assert a.prefix != b.prefix
try: run_expanding("2", bad_class, image=0.1)
except KeyError as e: print("a class that does not exist:", "KeyError:", e); assert str(e) == "'NoSuchNode'"
