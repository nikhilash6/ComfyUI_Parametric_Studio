# CU-110 lab: the same seven-node graph in the two JSON dialects, read like a map. Standard library only, well under a second.
# Run: python lab.py
# The save format follows the "Workflow JSON 0.4" schema (links are rows of six items); the API format follows the "Workflow API Format" page.
# Positions and sizes are made up, since they carry no meaning for the graph.
import copy, json

def node(nid, kind, order, ins, outs, widgets):
    """ins: [(name, type, link id or None)], outs: [(name, type, [link ids])]. Returns a node object with the fields the schema requires."""
    return {"id": nid, "type": kind, "pos": [100 * order, 80], "size": [315, 120], "flags": {}, "order": order, "mode": 0,
            "inputs": [{"name": n, "type": t, "link": l} for n, t, l in ins],
            "outputs": [{"name": n, "type": t, "links": ls, "slot_index": i} for i, (n, t, ls) in enumerate(outs)],
            "properties": {"Node name for S&R": kind}, "widgets_values": widgets}
UI = {"last_node_id": 9, "last_link_id": 9, "version": 0.4, "groups": [], "config": {}, "extra": {},
      "nodes": [
          node(4, "CheckpointLoaderSimple", 0, [], [("MODEL", "MODEL", [3]), ("CLIP", "CLIP", [1, 2]), ("VAE", "VAE", [8])], ["model_a.safetensors"]),
          node(5, "EmptyLatentImage", 1, [], [("LATENT", "LATENT", [6])], [512, 512, 1]),
          node(6, "CLIPTextEncode", 2, [("clip", "CLIP", 1)], [("CONDITIONING", "CONDITIONING", [4])], ["a red fox in snow"]),
          node(7, "CLIPTextEncode", 3, [("clip", "CLIP", 2)], [("CONDITIONING", "CONDITIONING", [5])], ["blurry"]),
          node(3, "KSampler", 4, [("model", "MODEL", 3), ("positive", "CONDITIONING", 4), ("negative", "CONDITIONING", 5), ("latent_image", "LATENT", 6)],
               [("LATENT", "LATENT", [7])], [156680208700286, "randomize", 20, 8, "euler", "normal", 1]),
          node(8, "VAEDecode", 5, [("samples", "LATENT", 7), ("vae", "VAE", 8)], [("IMAGE", "IMAGE", [9])], []),
          node(9, "SaveImage", 6, [("images", "IMAGE", 9)], [], ["ComfyUI"])],
      # link rows: [link id, origin node, origin slot, target node, target slot, type]
      "links": [[1, 4, 1, 6, 0, "CLIP"], [2, 4, 1, 7, 0, "CLIP"], [3, 4, 0, 3, 0, "MODEL"], [4, 6, 0, 3, 1, "CONDITIONING"], [5, 7, 0, 3, 2, "CONDITIONING"],
                [6, 5, 0, 3, 3, "LATENT"], [7, 3, 0, 8, 0, "LATENT"], [8, 4, 2, 8, 1, "VAE"], [9, 8, 0, 9, 0, "IMAGE"]]}
UI = json.loads(json.dumps(UI))                                      # it is just JSON text

# 1. Read the save format: one line per node.
print(f"save format, version {UI['version']}: {len(UI['nodes'])} nodes, {len(UI['links'])} links")
print("id  type                    inputs wired (name<-link id)                        widgets_values")
for n in sorted(UI["nodes"], key=lambda n: n["order"]):
    linked = ", ".join(f"{i['name']}<-{i['link']}" for i in n["inputs"] if i["link"] is not None) or "-"
    print(f"{n['id']:<4}{n['type']:<24}{linked:<52}{n['widgets_values']}")

# 2. The wiring is written twice, in `links` and in each node's sockets. A reader should check that the copies agree.
def check(ui):
    """Return a list of disagreements between `links` and the nodes' own sockets."""
    nodes = {n["id"]: n for n in ui["nodes"]}; rows = {r[0]: r for r in ui["links"]}; bad = []
    for lid, o, os_, t, ts, typ in ui["links"]:
        if o not in nodes or t not in nodes: bad.append(f"link {lid} joins node {o} to node {t}, and one of them does not exist"); continue
        out, inp = nodes[o]["outputs"][os_], nodes[t]["inputs"][ts]
        if lid not in out["links"]: bad.append(f"link {lid} is missing from the outputs of node {o}")
        if inp["link"] != lid: bad.append(f"node {t} input '{inp['name']}' says link {inp['link']}, but link {lid} ends there")
        if not (out["type"] == typ == inp["type"]): bad.append(f"link {lid} is typed {typ}, but joins an output of type {out['type']} to an input of type {inp['type']}")
    for n in ui["nodes"]:
        for i in n["inputs"]:
            if i["link"] is not None and i["link"] not in rows: bad.append(f"node {n['id']} input '{i['name']}' says link {i['link']}, which is not in links")
    return bad
def damaged(change):
    d = copy.deepcopy(UI); change(d); return d
print(f"\nwiring written twice agrees: {check(UI) == []}")
faults = {"link 4 deleted from links": damaged(lambda d: d["links"].pop(3)),
          "link 6 re-pointed to slot 2": damaged(lambda d: d["links"][5].__setitem__(4, 2)),
          "link 9 typed MODEL": damaged(lambda d: d["links"][8].__setitem__(5, "MODEL")),
          "link 1 joins node 42": damaged(lambda d: d["links"][0].__setitem__(1, 42))}
for label, d in faults.items():
    found = check(d); print(f"{label:<30}{len(found)} found: {found[0]}")
    assert found

# 3. Translate to the API format. Sockets that carry a link become [source id, slot]; widget values get names. The names come from each node's definition.
WIDGETS = {"CheckpointLoaderSimple": ["ckpt_name"], "EmptyLatentImage": ["width", "height", "batch_size"], "CLIPTextEncode": ["text"], "VAEDecode": [],
           "KSampler": ["seed", None, "steps", "cfg", "sampler_name", "scheduler", "denoise"], "SaveImage": ["filename_prefix"]}   # None: "control after generate", which the server never sees
def to_api(ui):
    rows = {r[0]: r for r in ui["links"]}; api = {}
    for n in ui["nodes"]:
        inputs = {i["name"]: [str(rows[i["link"]][1]), rows[i["link"]][2]] for i in n["inputs"] if i["link"] is not None}
        inputs.update({k: v for k, v in zip(WIDGETS[n["type"]], n["widgets_values"]) if k is not None})
        api[str(n["id"])] = {"inputs": inputs, "class_type": n["type"]}
    return api
API = to_api(UI)
ks = next(n for n in UI["nodes"] if n["type"] == "KSampler")
print(f"\nsave format -> API format: {len(API)} entries, keys {sorted(API)}")
print(f"KSampler has {len(ks['widgets_values'])} widget values but {len(API['3']['inputs']) - 4} widget inputs in the API format")
print("API entry 3:", json.dumps(API["3"], separators=(",", ":")))
assert API["3"]["inputs"]["model"] == ["4", 0] and API["9"]["inputs"]["images"] == ["8", 0] and "randomize" not in json.dumps(API)

# 4. Read both dialects the same way: follow a wire from the KSampler's positive input to its text, find the seed, list what the SaveImage depends on.
def text_ui(ui):
    rows = {r[0]: r for r in ui["links"]}; nodes = {n["id"]: n for n in ui["nodes"]}
    k = next(n for n in ui["nodes"] if n["type"] == "KSampler"); lid = next(i["link"] for i in k["inputs"] if i["name"] == "positive")
    return nodes[rows[lid][1]]["widgets_values"][0], k["widgets_values"][0]
def text_api(api):
    k = next(v for v in api.values() if v["class_type"] == "KSampler")
    return api[k["inputs"]["positive"][0]]["inputs"]["text"], k["inputs"]["seed"]
def upstream(api, nid):
    seen, todo = [], [nid]
    while todo:
        n = todo.pop()
        for v in api[n]["inputs"].values():
            if isinstance(v, list) and v[0] not in seen: seen.append(v[0]); todo.append(v[0])
    return sorted(seen)
print(f"\npositive text and seed from the save format: {text_ui(UI)}")
print(f"positive text and seed from the API format:  {text_api(API)}")
print(f"nodes the SaveImage depends on: {upstream(API, '9')}")
print(f"model files named in the graph: {sorted(v['inputs']['ckpt_name'] for v in API.values() if v['class_type'] == 'CheckpointLoaderSimple')}")
assert text_ui(UI) == text_api(API) and upstream(API, "9") == ["3", "4", "5", "6", "7", "8"]

# 5. A trap when writing API JSON by hand: object keys are strings, so a source id written as a number finds nothing.
hand = copy.deepcopy(API); hand["8"]["inputs"]["samples"] = [3, 0]
try: hand[hand["8"]["inputs"]["samples"][0]]; verdict = "found"
except KeyError as e: verdict = f"KeyError {e}"
print(f"\nsource id written as 3 instead of '3': looking up the node gives {verdict}")
assert verdict.startswith("KeyError")
