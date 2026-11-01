# CU-405 lab: the checks an agent should pass before and after it queues, against a stub. No model and no server. The node table is a small copy of what /object_info reports.
import json
SPEC = {"EmptyImage": {"required": {"width": "INT", "height": "INT", "batch_size": "INT", "color": "INT"}, "out": ["IMAGE"]}, "ImageInvert": {"required": {"image": "IMAGE"}, "out": ["IMAGE"]}, "PreviewImage": {"required": {"images": "IMAGE"}, "out": [], "output": True}, "EmptyLatentImage": {"required": {"width": "INT", "height": "INT", "batch_size": "INT"}, "out": ["LATENT"]}, "Made_Up_Node": None}
def verify(g):
    """The same questions validate_prompt asks, in plain code. Problem names are the server's."""
    bad = []
    for i, n in g.items():
        s = SPEC.get(n["class_type"])
        if s is None: bad.append((i, "missing_node_type")); continue
        for k, t in s["required"].items():
            if k not in n["inputs"]: bad.append((i, "required_input_missing:" + k)); continue
            v = n["inputs"][k]
            if isinstance(v, list):
                if v[0] not in g: bad.append((i, "exception_during_inner_validation:" + k)); continue   # the real code's lookup fails and is caught
                src = SPEC.get(g[v[0]]["class_type"]) or {"out": []}
                if v[1] >= len(src["out"]): bad.append((i, "exception_during_inner_validation:" + k))
                elif src["out"][v[1]] != t: bad.append((i, "return_type_mismatch:" + k))
    if not any((SPEC.get(n["class_type"]) or {}).get("output") for n in g.values()): bad.append(("-", "prompt_no_outputs"))
    return bad
good = {"1": {"class_type": "EmptyImage", "inputs": {"width": 64, "height": 64, "batch_size": 1, "color": 0}}, "2": {"class_type": "ImageInvert", "inputs": {"image": ["1", 0]}}, "3": {"class_type": "PreviewImage", "inputs": {"images": ["2", 0]}}}
def mutate(f):
    g = json.loads(json.dumps(good)); f(g); return g
cases = {"good": good, "invented node": mutate(lambda g: g["2"].update(class_type="Made_Up_Node")), "forgot an input": mutate(lambda g: g["1"]["inputs"].pop("height")), "wire to nothing": mutate(lambda g: g["2"]["inputs"].update(image=["9", 0])), "output slot too big": mutate(lambda g: g["2"]["inputs"].update(image=["1", 1])), "wrong type on a wire": mutate(lambda g: (g.update({"4": {"class_type": "EmptyLatentImage", "inputs": {"width": 64, "height": 64, "batch_size": 1}}}), g["2"]["inputs"].update(image=["4", 0]))), "no output node": mutate(lambda g: g.pop("3"))}
print("graph                  problems")
for k, g in cases.items(): print(f"{k:<22s} {verify(g)}")
assert verify(good) == [] and all(verify(g) for k, g in cases.items() if k != "good")
# Check: a graph can pass and still be wrong. Validation only sees types.
swap = mutate(lambda g: g["1"]["inputs"].update(width=8192)); print("\n8192 wide passes these checks:", verify(swap) == [], " so a size limit is your job, or the agent queues a huge job")
# The gate: what a tool may do without asking. Routes and classes as in server.py. Your policy decides the rest.
GATE = {"GET /object_info": "free", "GET /history": "free", "GET /view": "free", "GET /system_stats": "free", "POST /prompt": "budget", "POST /upload/image": "ask", "POST /queue clear": "ask", "POST /interrupt": "ask", "POST /free": "ask", "API node in graph": "ask"}
def gate(action, spent=0, limit=3): 
    k = GATE.get(action, "deny"); return "yes" if k == "free" or (k == "budget" and spent < limit) else "no" if k == "deny" else "ask a person"
print("\naction                 allowed?")
for a in ["GET /object_info", "POST /prompt", "POST /queue clear", "POST /free", "API node in graph", "shell command"]: print(f"{a:<22s} {gate(a)}")
print("fourth POST /prompt with a limit of 3:", gate("POST /prompt", 3)); assert gate("POST /prompt", 3) == "ask a person" and gate("shell command") == "no"
# After the run: three facts to read, not assume.
hist = {"ok": {"status": {"status_str": "success", "completed": True}, "outputs": {"3": {"images": [{"filename": "x_00001_.png", "type": "temp"}]}}}, "failed": {"status": {"status_str": "error", "completed": False}, "outputs": {}}, "ran, no images": {"status": {"status_str": "success", "completed": True}, "outputs": {}}}
def check(h):
    if h["status"]["status_str"] != "success": return "failed: read status messages"
    files = [f for o in h["outputs"].values() for f in o.get("images", [])]
    return "no files: don't report success" if not files else f"{len(files)} file: fetch it and look before reporting"
print("\nrun              what the agent should do")
for k, h in hist.items(): print(f"{k:<16s} {check(h)}")
assert check(hist["ran, no images"]).startswith("no files")
