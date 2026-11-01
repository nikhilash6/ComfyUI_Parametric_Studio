# CU-223 lab: what an app has to do. Pick inputs and outputs of a workflow, build a form, fill it, and patch only those values before queueing.
# Run: python lab.py  (standard library only, under a second).
import copy, json
prompt = {"3": {"class_type": "KSampler", "inputs": {"seed": 1, "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
          "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
          "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
          "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a fox", "clip": ["4", 1]}},
          "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
          "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
          "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "app"}}}
app = {"inputs": [["6", "text", "Describe the image"], ["3", "seed", "Seed"], ["5", "width", "Width"]], "outputs": ["9"]}
def is_link(v): return isinstance(v, list) and len(v) == 2
widgets = sum(1 for n in prompt.values() for v in n["inputs"].values() if not is_link(v)); print(f"the graph has {len(prompt)} nodes and {widgets} widget values; the app shows {len(app['inputs'])} of them")
form = [{"label": l, "node": n, "input": k, "value": prompt[n]["inputs"][k]} for n, k, l in app["inputs"]]
for f in form: print(f"  field {f['label']!r:22} -> node {f['node']} input {f['input']!r}, default {f['value']!r}")
for n, k, _ in app["inputs"]: assert not is_link(prompt[n]["inputs"][k]), "a form field must be a value, not a wire"
def fill(values):
    p = copy.deepcopy(prompt)
    for (n, k, _), v in zip(app["inputs"], values): p[n]["inputs"][k] = v
    return p
a = fill(["a red kite", 42, 768]); changed = sorted((n, k) for n in prompt for k in prompt[n]["inputs"] if a[n]["inputs"][k] != prompt[n]["inputs"][k]); print("values changed by the form:", changed)
assert changed == [("3", "seed"), ("5", "width"), ("6", "text")]
assert {n: {k for k, v in x["inputs"].items() if is_link(v)} for n, x in prompt.items()} == {n: {k for k, v in x["inputs"].items() if is_link(v)} for n, x in a.items()}
print("wires changed by the form: 0")
print("body queued:", json.dumps({"prompt": {"6": a["6"]}})[:60], "... the same POST /prompt as any other client")
assert prompt["6"]["inputs"]["text"] == "a fox"
# A form cannot hide a type error: an out-of-range or wrong-type value still fails on the server, as for any client.
def check(node, key, value): return {"width": lambda v: isinstance(v, int) and 16 <= v <= 16384}.get(key, lambda v: True)(value)
print("width=768 valid:", check("5", "width", 768), "  width=4 valid:", check("5", "width", 4)); assert not check("5", "width", 4)
# What a field costs: walk the wires down from the node it sits on. Everything already cached, one value changed.
down = {n: [m for m, x in prompt.items() if any(is_link(v) and v[0] == n for v in x["inputs"].values())] for n in prompt}
def reruns(n):
    seen, todo = set(), [n]
    while todo:
        k = todo.pop()
        if k not in seen: seen.add(k); todo += down[k]
    return seen
print("\nchange this field     nodes that run again")
for n, k, label in [["6", "text", "Describe the image"], ["3", "seed", "Seed"], ["5", "width", "Width"], ["9", "filename_prefix", "File prefix"], ["4", "ckpt_name", "Checkpoint"]]:
    print(f"{label:20}  {len(reruns(n))} of {len(prompt)}")
assert len(reruns("3")) == 3 and len(reruns("9")) == 1 and len(reruns("4")) == 6
# The shape the front end saves in the workflow's extra field. The first item is a widget id or a node id.
saved = {"linearMode": True, "linearData": {"inputs": [[n, k] for n, k, _ in app["inputs"]], "outputs": app["outputs"]}}
print("\nsaved with the workflow:", json.dumps(saved)); assert saved["linearData"]["outputs"] == ["9"]
print("the prompt graph holds it:", "linearData" in json.dumps(prompt)); assert "linearData" not in json.dumps(prompt)
