# CU-517 lab: a two-graph pipeline with a job ledger, against a stub server. No network, no model. What's shown is the bookkeeping, not any real studio.
import hashlib, json
def key(g): return hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest()[:10]
class Stub:
    def __init__(self, fail_on=None): self.calls = []; self.fail = fail_on; self.files = {}
    def run(self, g):
        name = g["name"]; self.calls.append(name)
        if name == self.fail: self.fail = None; return {"status": "error", "files": []}
        f = f"{name}_{len(self.calls):05}_.png"; self.files[f] = "made by " + name + " from " + str(g.get("input")); return {"status": "success", "files": [f]}
def pipeline(server, ledger, prompt):
    a = {"name": "draft", "text": prompt}; b = {"name": "refine", "input": None}; c = {"name": "upscale", "input": None}; prev = None
    for g in (a, b, c):
        if "input" in g: g["input"] = prev
        k = key(g)
        if k in ledger: prev = ledger[k]; continue                  # this step's work is already on disk
        r = server.run(g)
        if r["status"] != "success": return "stopped at " + g["name"]
        ledger[k] = r["files"][0]; prev = r["files"][0]
    return prev
s = Stub("refine"); led = {}; print("first try:", pipeline(s, led, "a brass astrolabe"), " calls:", s.calls); assert s.calls == ["draft", "refine"]
print("second try:", pipeline(s, led, "a brass astrolabe"), " calls:", s.calls); assert s.calls == ["draft", "refine", "refine", "upscale"]
print("again, nothing changed:", pipeline(s, led, "a brass astrolabe"), " calls so far:", len(s.calls)); assert len(s.calls) == 4
print("new prompt:", pipeline(s, led, "a copper sextant"), " calls so far:", len(s.calls)); assert len(s.calls) == 7
# One graph or several? Count what must run again after changing the last step's setting.
print("\nsplit                  change the last step    why")
print("one graph              it and what follows it  the engine's cache keeps earlier results, while they stay in memory")
print("three graphs + ledger  1 graph runs            your ledger keeps file names, for as long as the files stay")
# Polling, as API nodes do: ask, wait, ask again, and give up at a limit. No fixed delay of ours is the real one.
def poll(states, limit):
    for i, st in enumerate(states[:limit]):
        if st in ("done", "failed"): return st, i + 1
    return "gave up", limit
print("\npoll:", poll(["queued", "running", "done"], 10), poll(["queued", "failed"], 10), poll(["queued"] * 20, 10)); assert poll(["queued"] * 20, 10)[0] == "gave up"
