# CU-102 lab: a miniature of how ComfyUI decides what to run and what to reuse. Standard library only, well under a second.
# Run: python lab.py
# The node table, the error names and the cache-key recipe follow ComfyUI v0.43.0 (execution.py, comfy_execution/graph.py, comfy_execution/caching.py).
# Nothing here runs a model: every "result" is just a label, so that the counts of what ran can be checked by hand.
import copy, json

# Output types, input types and output-node flag of the six node classes used below (names as in nodes.py).
NODES = {
    "CheckpointLoaderSimple": {"out": ["MODEL", "CLIP", "VAE"], "in": {}, "output": False},
    "CLIPTextEncode": {"out": ["CONDITIONING"], "in": {"clip": "CLIP"}, "output": False},
    "EmptyLatentImage": {"out": ["LATENT"], "in": {}, "output": False},
    "KSampler": {"out": ["LATENT"], "in": {"model": "MODEL", "positive": "CONDITIONING", "negative": "CONDITIONING", "latent_image": "LATENT"}, "output": False},
    "VAEDecode": {"out": ["IMAGE"], "in": {"samples": "LATENT", "vae": "VAE"}, "output": False},
    "SaveImage": {"out": ["IMAGE"], "in": {"images": "IMAGE"}, "output": True},
}

def is_link(v): return isinstance(v, list)          # a wire is [source node id, output slot]; anything else is a constant

# The prompt is what the server receives: {node id: {"class_type": ..., "inputs": {name: constant or [source id, slot]}}}.
PROMPT = {
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model_a.safetensors"}},
    "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red fox in snow", "clip": ["1", 1]}},
    "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry", "clip": ["1", 1]}},
    "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
    "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0], "seed": 42, "steps": 20, "cfg": 8.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
    "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
    "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "ComfyUI"}},
    "8": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},   # wired to nothing
}

def validate(prompt):
    """Return (error type, "message: details") in the form validate_prompt logs it, or None when the prompt is acceptable."""
    outputs = [n for n, node in prompt.items() if NODES[node["class_type"]]["output"]]
    if not outputs: return ("prompt_no_outputs", "Prompt has no outputs")
    def name(n): return f"{n} ({prompt[n]['class_type']})"
    def visit(n, path):                                    # only nodes upstream of an output are ever checked
        if n in path: return ("dependency_cycle", "Dependency cycle detected: " + " -> ".join(name(x) for x in path[path.index(n):] + [n]))
        for key, want in NODES[prompt[n]["class_type"]]["in"].items():
            if key not in prompt[n]["inputs"]: return ("required_input_missing", f"Required input is missing: {key}")
            v = prompt[n]["inputs"][key]
            if is_link(v):
                got = NODES[prompt[v[0]]["class_type"]]["out"][v[1]]
                if not set(got.split(",")) & set(want.split(",")): return ("return_type_mismatch", f"Return type mismatch between linked nodes: {key}, received_type({got}) mismatch input_type({want})")
                err = visit(v[0], path + [n])
                if err: return err
        return None
    for o in outputs:
        err = visit(o, [])
        if err: return err
    return None

def signature(prompt, nid):
    """The cache key: this node's class and inputs, then the same for every ancestor, wires replaced by the ancestor's place in the list."""
    order, index = [], {}
    def walk(n):
        for k in sorted(prompt[n]["inputs"]):
            v = prompt[n]["inputs"][k]
            if is_link(v) and v[0] not in index:
                index[v[0]] = len(order); order.append(v[0]); walk(v[0])
    walk(nid)
    def own(n):
        parts = [prompt[n]["class_type"]]
        for k in sorted(prompt[n]["inputs"]):
            v = prompt[n]["inputs"][k]
            parts.append([k, ["ANCESTOR", index[v[0]], v[1]] if is_link(v) else v])
        return parts
    return json.dumps([own(nid)] + [own(a) for a in order])

class Engine:
    def __init__(self): self.cache = {}                    # key -> result label

    def run(self, prompt):
        err = validate(prompt)
        if err: return err
        keys = {n: signature(prompt, n) for n in prompt}
        cached_at_start = sorted(n for n in prompt if keys[n] in self.cache)
        outputs = [n for n in prompt if NODES[prompt[n]["class_type"]]["output"]]
        # Find what is needed: walk upstream from the output nodes and stop at anything already cached.
        pending, stack = [], list(outputs)
        while stack:
            n = stack.pop()
            if n in pending: continue
            pending.append(n)
            for v in prompt[n]["inputs"].values():
                if is_link(v) and keys[v[0]] not in self.cache: stack.append(v[0])
        waiting = {n: {v[0] for v in prompt[n]["inputs"].values() if is_link(v) and v[0] in pending} for n in pending}
        ran = []
        while waiting:
            ready = [n for n in pending if n in waiting and not waiting[n]]
            assert ready, "every waiting node waits on another: a cycle"
            def feeds_output(n): return any(NODES[prompt[m]["class_type"]]["output"] for m in waiting if n in waiting[m])
            pick = next((n for n in ready if NODES[prompt[n]["class_type"]]["output"]), None) or next((n for n in ready if feeds_output(n)), None) or ready[0]
            if keys[pick] not in self.cache:               # same key already stored means nothing to compute
                self.cache[keys[pick]] = f"result of {prompt[pick]['class_type']}"; ran.append(pick)
            del waiting[pick]
            for w in waiting.values(): w.discard(pick)
        return ran, cached_at_start, sorted(n for n in prompt if n not in pending and n not in cached_at_start)

def orders(prompt):
    """Count the valid execution orders of the nodes that feed the output (every order that respects the wires)."""
    need, stack = set(), [n for n in prompt if NODES[prompt[n]["class_type"]]["output"]]
    while stack:
        n = stack.pop()
        if n in need: continue
        need.add(n); stack += [v[0] for v in prompt[n]["inputs"].values() if is_link(v)]
    deps = {n: {v[0] for v in prompt[n]["inputs"].values() if is_link(v)} for n in need}
    ways = {frozenset(): 1}
    for size in range(len(need)):
        for done in [s for s in ways if len(s) == size]:
            for n in need - done:
                if deps[n] <= done: ways[done | {n}] = ways.get(done | {n}, 0) + ways[done]
    return len(need), ways[frozenset(need)]

def with_(prompt, nid, **changes):
    p = copy.deepcopy(prompt); p[nid]["inputs"].update(changes); return p

e = Engine()
n_need, n_orders = orders(PROMPT)
print(f"nodes that feed the output: {n_need} of {len(PROMPT)}   valid execution orders: {n_orders}")
print("\nwhat                                  ran              found in cache                    not needed")
def show(label, prompt):
    ran, cached, skipped = e.run(prompt)
    j = lambda xs: " ".join(xs) or "-"
    print(f"{label:<37} {j(ran):<16} {j(cached):<33} {j(skipped)}")
    return ran, cached, skipped
# Each row changes one more thing than the row above it, and the cache keeps what the earlier rows stored.
cur = PROMPT
a = show("first run", cur)
b = show("same prompt again", cur)
cur = with_(cur, "5", seed=43); c = show("seed 42 -> 43", cur)
cur = with_(cur, "2", text="a grey wolf in snow"); d = show("positive text changed", cur)
cur = with_(cur, "1", ckpt_name="model_b.safetensors"); f = show("checkpoint file name changed", cur)
cur = with_(cur, "4", width=768); g = show("latent 512 -> 768 wide", cur)
cur = copy.deepcopy(cur); cur["9"] = {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "second"}}; h = show("second SaveImage added", cur)
ren = {k: str(int(k) + 100) for k in cur}
cur = {ren[k]: {"class_type": v["class_type"], "inputs": {n: ([ren[x[0]], x[1]] if is_link(x) else x) for n, x in v["inputs"].items()}} for k, v in cur.items()}
i = show("every node id renumbered (+100)", cur)
assert a[0] and len(a[0]) == 7 and a[2] == ["8"] and b[0] == [] and c[0] == ["5", "6", "7"] and d[0] == ["2", "5", "6", "7"]
assert sorted(f[0]) == ["1", "2", "3", "5", "6", "7"] and f[1] == ["4"] and sorted(g[0]) == ["4", "5", "6", "7"] and h[0] == ["9"] and i[0] == []

print("\nvalidation, before anything runs")
bad_type = with_(PROMPT, "5", model=["1", 1])                    # CLIP wire into a MODEL socket
cycle = copy.deepcopy(PROMPT); cycle["10"] = copy.deepcopy(cycle["5"]); cycle["10"]["inputs"]["latent_image"] = ["5", 0]; cycle["5"]["inputs"]["latent_image"] = ["10", 0]
missing = copy.deepcopy(PROMPT); del missing["5"]["inputs"]["latent_image"]
no_out = {k: v for k, v in PROMPT.items() if k != "7"}
for label, p in (("CLIP wire into the MODEL socket", bad_type), ("two samplers feeding each other", cycle), ("KSampler without latent_image", missing), ("no output node", no_out)):
    err = validate(p); print(f"{label:<34} {err[0]}  |  {err[1]}")
    assert err
