# CU-460 lab: a script's job loop, run against an in-memory stub of the server. No network. The stub follows server.py's post_prompt, validate_job_id and get_history at v0.43.0, cut down.
import copy, json, uuid
def valid_id(pid):                               # validate_job_id: it must survive a round trip through uuid.UUID unchanged
    try: return isinstance(pid, str) and str(uuid.UUID(pid)) == pid
    except ValueError: return False
class Stub:
    def __init__(self): self.history = {}; self.queue = []; self.number = 0; self.files = {}; self.polls = 0; self.delay = 2
    def post_prompt(self, body):
        if "prompt" not in body: return 400, {"error": {"type": "no_prompt"}, "node_errors": {}}
        pid = body.get("prompt_id")
        if pid is not None and not valid_id(pid): return 400, {"error": {"type": "invalid_prompt_id", "message": "prompt_id must be a valid UUID"}, "node_errors": {}}
        for i, n in body["prompt"].items():
            if n["class_type"] == "EmptyImage" and not 1 <= n["inputs"]["width"] <= 16384:
                return 400, {"error": {"type": "prompt_outputs_failed_validation", "message": "Prompt outputs failed validation"}, "node_errors": {i: {"errors": [{"type": "value_bigger_than_max" if n["inputs"]["width"] > 16384 else "value_smaller_than_min", "details": "width"}], "class_type": "EmptyImage"}}}
        if pid is None: pid = f"00000000-0000-4000-8000-{self.number:012d}"
        self.queue.append(pid); n = self.number; self.number += 1; self.prompt = body["prompt"]; self.polls = 0
        return 200, {"prompt_id": pid, "number": n, "node_errors": {}}
    def get_history(self, pid):
        self.polls += 1
        if self.polls < self.delay: return {}
        f = {"filename": "first_00001_.png", "subfolder": "university", "type": "output"}; self.files[(f["filename"], f["subfolder"], f["type"])] = b"\x89PNG"
        self.history[pid] = {"outputs": {"2": {"images": [f]}, "3": {"images": [{"filename": "ComfyUI_temp_abc_00001_.png", "subfolder": "", "type": "temp"}]}}, "status": {"status_str": "success", "completed": True, "messages": []}}
        return {pid: self.history[pid]}
    def view(self, filename, subfolder, type): return self.files[(filename, subfolder, type)]

GRAPH = {"1": {"class_type": "EmptyImage", "inputs": {"width": 256, "height": 256, "batch_size": 1, "color": 16106776}}, "2": {"class_type": "SaveImage", "inputs": {"images": ["1", 0], "filename_prefix": "university/first"}}, "3": {"class_type": "PreviewImage", "inputs": {"images": ["1", 0]}}}
def build(color=None):
    g = copy.deepcopy(GRAPH)                       # never edit the graph you loaded: copy it, then set values
    if color is not None: g["1"]["inputs"]["color"] = color
    return g
def queue(s, g, pid=None):
    st, r = s.post_prompt({"prompt": g, "client_id": "my-script", **({"prompt_id": pid} if pid else {})})
    if st != 200:
        lines = [r["error"]["type"]] + [f"  node {i} {e['class_type']}: {x['type']} ({x['details']})" for i, e in r["node_errors"].items() for x in e["errors"]]
        return None, lines
    return r["prompt_id"], []
def wait(s, pid, tries=10):
    for i in range(tries):
        h = s.get_history(pid)
        if pid in h: return h[pid], i + 1
    raise TimeoutError(pid)

s = Stub()
g = build(color=0xF5C518); assert GRAPH["1"]["inputs"]["color"] == 16106776 and g is not GRAPH
pid, err = queue(s, g); print("queued:", pid, " errors:", err); assert pid
job, polls = wait(s, pid); print("finished after polls:", polls, " status:", job["status"]["status_str"], job["status"]["completed"])
assert s.polls == 2
for nid, out in job["outputs"].items():
    for f in out.get("images", []): print(f"  node {nid}: {f['type']:7} subfolder {f['subfolder']!r:13} filename {f['filename']}")
saved = [f for o in job["outputs"].values() for f in o["images"] if f["type"] == "output"]; assert len(saved) == 1
print("downloaded:", s.view(saved[0]["filename"], saved[0]["subfolder"], saved[0]["type"])); print()
bad = build(); bad["1"]["inputs"]["width"] = 99999; pid2, lines = queue(s, bad); print("too wide:", pid2); print("\n".join(lines)); assert pid2 is None and "value_bigger_than_max" in lines[1]; print()
pid3, lines = queue(s, build(), "MY-JOB-1"); print("my own id MY-JOB-1:", lines); assert lines == ["invalid_prompt_id"]
mine = "12345678-1234-4234-8234-1234567890ab"; pid4, _ = queue(s, build(), mine); print("my own id, a real UUID:", pid4); assert pid4 == mine
