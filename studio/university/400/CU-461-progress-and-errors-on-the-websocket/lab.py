# CU-461 lab: replays message lists captured from a real PromptExecutor run (ComfyUI v0.43.0, CPU, with a recording fake server) through a small watcher. The last message of each list comes from prompt_worker in main.py, read, not captured. No network.
import json, struct
TRACES = {
 "first run": [("execution_start", {}), ("execution_cached", {"nodes": []}), ("executing", {"node": "1"}), ("executing", {"node": "2"}), ("progress", {"value": 1, "max": 2}), ("progress", {"value": 2, "max": 2}), ("executing", {"node": "3"}), ("executed", {"node": "3", "output": {"images": [{"filename": "t_00001_.png", "subfolder": "", "type": "output"}]}}), ("execution_success", {})],
 "same again": [("execution_start", {}), ("execution_cached", {"nodes": ["1", "2", "3"]}), ("executed", {"node": "3", "output": {"images": [{"filename": "t_00001_.png", "subfolder": "", "type": "output"}]}}), ("execution_success", {})],
 "a node raises": [("execution_start", {}), ("execution_cached", {"nodes": ["1"]}), ("executing", {"node": "2"}), ("execution_error", {"node_id": "2", "node_type": "Boom", "exception_type": "ValueError", "exception_message": "boom on purpose\n"})],
 "interrupted": [("execution_start", {}), ("execution_cached", {"nodes": ["1"]}), ("executing", {"node": "2"}), ("execution_interrupted", {"node_id": "2", "node_type": "Stop"})],
}
END = ("executing", {"node": None})            # prompt_worker sends this after task_done, for every job
def watch(trace, pid="J"):
    st = {"nodes_run": 0, "progress": 0, "cached": 0, "files": 0, "result": "unknown", "why": ""}
    for t, d in trace + [END]:
        d = {**d, "prompt_id": pid}
        if d["prompt_id"] != pid: continue     # other people's jobs can share your socket
        if t == "execution_cached": st["cached"] = len(d["nodes"])
        elif t == "executing" and d["node"] is not None: st["nodes_run"] += 1
        elif t == "progress": st["progress"] += 1
        elif t == "executed": st["files"] += len(d["output"].get("images", []))
        elif t == "execution_success": st["result"] = "success"
        elif t == "execution_error": st["result"] = "error"; st["why"] = f"{d['node_type']} {d['exception_type']}: {d['exception_message'].strip()}"
        elif t == "execution_interrupted": st["result"] = "interrupted"; st["why"] = f"stopped in {d['node_type']}"
        if t == "executing" and d["node"] is None: return st
    raise AssertionError("no end message")
print("job             nodes run  cached  progress  files  result       why")
R = {}
for k, tr in TRACES.items():
    r = R[k] = watch(tr); print(f"{k:15} {r['nodes_run']:9}  {r['cached']:6}  {r['progress']:8}  {r['files']:5}  {r['result']:11}  {r['why']}")
assert R["same again"]["nodes_run"] == 0 and R["same again"]["files"] == 1 and R["a node raises"]["result"] == "error" and R["interrupted"]["result"] == "interrupted"
print()
# Routing, as in PromptServer.send_json: sid None goes to everyone, a known sid to one socket, an unknown sid to nobody.
def deliver(sockets, event, sid):
    if sid is None: return sorted(sockets)
    return [sid] if sid in sockets else []
sk = {"me", "other"}
print("sent to me:          ", deliver(sk, "executing", "me"))
print("sent to everyone:    ", deliver(sk, "status", None))
print("sent while I am away:", deliver({"other"}, "execution_success", "me")); assert deliver({"other"}, "x", "me") == []
print()
# With no client_id the executor has server.client_id = None. add_message only sends when broadcast=True; progress uses send_sync with sid None.
def no_client_id(kinds):
    return [k for k, broadcast in kinds if broadcast]
kinds = [("execution_start", False), ("execution_cached", False), ("progress", True), ("progress_state", True), ("execution_success", False), ("execution_interrupted", True)]
print("a job queued with no client_id can still send:", no_client_id(kinds)); assert "execution_success" not in no_client_id(kinds)
print()
# Binary frames: encode_bytes puts a 4-byte big-endian event type first.
def preview_frame(type_num, image): return struct.pack(">I", 1) + struct.pack(">I", type_num) + image
def meta_frame(meta, image):
    j = json.dumps(meta).encode(); return struct.pack(">I", 4) + struct.pack(">I", len(j)) + j + image
def text_frame(node, text):
    n = node.encode(); return struct.pack(">I", 3) + struct.pack(">I", len(n)) + n + text.encode()
def read_frame(b):
    ev = struct.unpack(">I", b[:4])[0]
    if ev == 1: return "preview", {1: "JPEG", 2: "PNG"}[struct.unpack(">I", b[4:8])[0]], b[8:]
    if ev == 4: n = struct.unpack(">I", b[4:8])[0]; return "preview+meta", json.loads(b[8:8 + n]), b[8 + n:]
    if ev == 3: n = struct.unpack(">I", b[4:8])[0]; return "text", b[8:8 + n].decode(), b[8 + n:].decode()
for f in (preview_frame(1, b"\xff\xd8.."), meta_frame({"node_id": "5", "image_type": "image/jpeg"}, b"\xff\xd8.."), text_frame("5", "loading")): print(read_frame(f))
assert read_frame(preview_frame(2, b"x")) == ("preview", "PNG", b"x")
