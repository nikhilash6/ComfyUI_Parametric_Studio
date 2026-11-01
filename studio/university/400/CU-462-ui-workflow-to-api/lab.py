# CU-462 lab: from the save format to the API format, then set values by node id. The widget orders are copied from a saved /object_info of ComfyUI v0.43.0. No server.
import copy, json
WIDGETS = {"CheckpointLoaderSimple": ["ckpt_name"], "CLIPTextEncode": ["text"], "EmptyLatentImage": ["width", "height", "batch_size"], "KSampler": ["seed", None, "steps", "cfg", "sampler_name", "scheduler", "denoise"], "VAEDecode": [], "SaveImage": ["filename_prefix"], "Note": []}
LIMITS = {"KSampler": {"seed": (int, 0, 18446744073709551615), "steps": (int, 1, 10000), "cfg": (float, 0.0, 100.0), "denoise": (float, 0.0, 1.0)}, "EmptyLatentImage": {"width": (int, 16, 16384), "height": (int, 16, 16384), "batch_size": (int, 1, 4096)}}
UI = {"nodes": [
 {"id": 1, "type": "CheckpointLoaderSimple", "mode": 0, "inputs": [], "widgets_values": ["v1-5-pruned-emaonly.safetensors"]},
 {"id": 2, "type": "CLIPTextEncode", "title": "Positive", "mode": 0, "inputs": [{"name": "clip", "link": 1}], "widgets_values": ["a brass astrolabe"]},
 {"id": 3, "type": "CLIPTextEncode", "title": "Negative", "mode": 0, "inputs": [{"name": "clip", "link": 2}], "widgets_values": ["blurry"]},
 {"id": 4, "type": "EmptyLatentImage", "mode": 0, "inputs": [], "widgets_values": [512, 512, 1]},
 {"id": 5, "type": "KSampler", "mode": 0, "inputs": [{"name": "model", "link": 3}, {"name": "positive", "link": 4}, {"name": "negative", "link": 5}, {"name": "latent_image", "link": 6}], "widgets_values": [424242, "randomize", 20, 7.0, "euler", "karras", 1.0]},
 {"id": 6, "type": "VAEDecode", "mode": 0, "inputs": [{"name": "samples", "link": 7}, {"name": "vae", "link": 8}], "widgets_values": []},
 {"id": 7, "type": "SaveImage", "mode": 0, "inputs": [{"name": "images", "link": 9}], "widgets_values": ["university"]},
 {"id": 8, "type": "SaveImage", "mode": 2, "inputs": [{"name": "images", "link": 10}], "widgets_values": ["muted"]},
 {"id": 9, "type": "Note", "mode": 0, "inputs": [], "widgets_values": ["remember to change the seed"]}],
 "links": [[1, 1, 1, 2, 0, "CLIP"], [2, 1, 1, 3, 0, "CLIP"], [3, 1, 0, 5, 0, "MODEL"], [4, 2, 0, 5, 1, "CONDITIONING"], [5, 3, 0, 5, 2, "CONDITIONING"], [6, 4, 0, 5, 3, "LATENT"], [7, 5, 0, 6, 0, "LATENT"], [8, 1, 2, 6, 1, "VAE"], [9, 6, 0, 7, 0, "IMAGE"], [10, 6, 0, 8, 0, "IMAGE"]]}
VIRTUAL = {"Note"}; MUTED = 2; BYPASSED = 4
def convert(ui, widgets=WIDGETS):
    links = {l[0]: l for l in ui["links"]}; out = {}
    for n in ui["nodes"]:
        if n["type"] in VIRTUAL or n["mode"] in (MUTED, BYPASSED): continue
        inputs = {name: v for name, v in zip(widgets[n["type"]], n["widgets_values"]) if name}
        for s in n["inputs"]:
            if s.get("link") is not None: l = links[s["link"]]; inputs[s["name"]] = [str(l[1]), l[2]]
        out[str(n["id"])] = {"class_type": n["type"], "inputs": inputs, "_meta": {"title": n.get("title", n["type"])}}
    return out
api = convert(UI); print("nodes in the file:", len(UI["nodes"]), "  nodes in the API graph:", len(api), "  left out:", sorted(set(str(n["id"]) for n in UI["nodes"]) - set(api)))
assert sorted(api) == ["1", "2", "3", "4", "5", "6", "7"]
print("node 5:", json.dumps(api["5"]["inputs"])); assert api["5"]["inputs"]["steps"] == 20 and "randomize" not in json.dumps(api["5"]["inputs"])
print()
naive = dict(WIDGETS); naive["KSampler"] = ["seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"]
print("forget the editor-only value:", {k: v for k, v in convert(UI, naive)["5"]["inputs"].items() if not isinstance(v, list)}); assert convert(UI, naive)["5"]["inputs"]["steps"] == "randomize"
def check(g):
    """Same idea as validate_inputs: a type conversion, then the limits. Wording cut down."""
    bad = []
    for i, n in g.items():
        for k, (t, lo, hi) in LIMITS.get(n["class_type"], {}).items():
            v = n["inputs"].get(k)
            if isinstance(v, list): continue
            try: v = t(v)
            except (TypeError, ValueError): bad.append((i, k, "invalid_input_type")); continue
            if v < lo: bad.append((i, k, "value_smaller_than_min"))
            elif v > hi: bad.append((i, k, "value_bigger_than_max"))
    return bad
print("the check says:", check(convert(UI, naive))); assert check(api) == []
print()
def find(g, class_type, title=None):
    hits = [i for i, n in g.items() if n["class_type"] == class_type and (title is None or n["_meta"]["title"] == title)]
    if len(hits) != 1: raise LookupError(f"{class_type} {title}: {len(hits)} matches")
    return hits[0]
def set_value(g, node, name, value):
    if isinstance(g[node]["inputs"].get(name), list): raise ValueError(f"{name} on node {node} is a wire")
    if name not in g[node]["inputs"]: raise KeyError(f"node {node} has no input {name}")
    g[node]["inputs"][name] = value
job = copy.deepcopy(api); set_value(job, find(job, "KSampler"), "seed", 7); set_value(job, find(job, "CLIPTextEncode", "Positive"), "text", "a red kite")
print("changed:", [(i, k) for i in job for k in job[i]["inputs"] if job[i]["inputs"][k] != api[i]["inputs"][k]])
for label, fn in [("find by class alone", lambda: find(job, "CLIPTextEncode")), ("set a wire", lambda: set_value(job, "5", "model", "x")), ("mistyped name", lambda: set_value(job, "5", "sed", 1))]:
    try: fn(); print(label, "worked"); assert False
    except (LookupError, ValueError) as e: print(f"{label}: {e}")
assert job["5"]["inputs"]["model"] == ["1", 0]
print()
# An array value would look like a wire, so the front end wraps it. execution.py takes it back out.
def is_link(v): return isinstance(v, list)
def unwrap(v): return v["__value__"] if isinstance(v, dict) and "__value__" in v else v
print("[1, 2] looks like a wire:", is_link([1, 2]), "  wrapped:", is_link({"__value__": [1, 2]}), "  unwrapped later:", unwrap({"__value__": [1, 2]}))
