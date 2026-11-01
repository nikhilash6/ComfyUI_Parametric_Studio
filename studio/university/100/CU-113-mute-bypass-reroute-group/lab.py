# CU-113 lab: what the editor sends for each state of a small graph. A short port of graphToPrompt and ExecutableNodeDTO from the ComfyUI front end, without subgraphs.
# Read from the front end's main branch on 2026-11-01. Not run in the real editor. The "server says" column follows validate_prompt in ComfyUI v0.43.0.
import json, copy
ALWAYS, NEVER, BYPASS = 0, 2, 4   # LGraphEventMode

def node(cls, inputs=(), outputs=(), widgets=None, virtual=False, output=False):
    return {"cls": cls, "inputs": [dict(zip(("name", "type", "from"), i)) for i in inputs], "outputs": list(outputs), "widgets": widgets or {}, "mode": ALWAYS, "virtual": virtual, "output": output}
CHAIN = {"1": node("EmptyImage", outputs=["IMAGE"], widgets={"width": 512}),
         "2": node("ImageBlur", [("image", "IMAGE", ("1", 0))], ["IMAGE"], {"blur_radius": 4}),
         "3": node("Reroute", [("", "*", ("2", 0))], ["*"], virtual=True),
         "4": node("ImageInvert", [("image", "IMAGE", ("3", 0))], ["IMAGE"]),
         "5": node("PreviewImage", [("images", "IMAGE", ("4", 0))], output=True),
         "6": node("Note", widgets={"text": "try the blur"}, virtual=True)}
DECODE = {"1": node("CheckpointLoaderSimple", outputs=["MODEL", "CLIP", "VAE"], widgets={"ckpt_name": "model.safetensors"}),
          "2": node("EmptyLatentImage", outputs=["LATENT"], widgets={"width": 512}),
          "3": node("VAEDecode", [("samples", "LATENT", ("2", 0)), ("vae", "VAE", ("1", 2))], ["IMAGE"]),
          "4": node("PreviewImage", [("images", "IMAGE", ("3", 0))], output=True)}
def fits(a, b): return a == "*" or b == "*" or a == b
def bypass_slot(n, slot, want):
    """_getBypassSlotIndex: the same slot number if it fits, else the first input of the wanted type, else the first that fits."""
    ins = n["inputs"]; out = n["outputs"][slot]
    if want in ("*", ""): return slot if len(ins) > slot else 0
    if slot < len(ins) and fits(ins[slot]["type"], out) and fits(ins[slot]["type"], want): return slot
    for k, i in enumerate(ins):
        if i["type"] == want: return k
    for k, i in enumerate(ins):
        if fits(i["type"], out) and fits(i["type"], want): return k
    return -1
def resolve_output(g, nid, slot, want):
    n = g[nid]
    if n["mode"] == NEVER: return None
    if n["mode"] == BYPASS:
        k = bypass_slot(n, slot, want)
        return None if k == -1 else resolve_input(g, nid, k)
    if n["virtual"]: return resolve_input(g, nid, slot, want) if slot < len(n["inputs"]) else None
    return [nid, slot]
def resolve_input(g, nid, k, want=None):
    i = g[nid]["inputs"][k]
    return resolve_output(g, i["from"][0], i["from"][1], want or i["type"]) if i["from"] else None
def graph_to_prompt(g):
    out = {}
    for nid, n in g.items():
        if n["virtual"] or n["mode"] in (NEVER, BYPASS): continue
        inputs = dict(n["widgets"])
        for k, i in enumerate(n["inputs"]):
            r = resolve_input(g, nid, k)
            if r: inputs[i["name"]] = r
        out[nid] = {"inputs": inputs, "class_type": n["cls"]}
    return out
def server_says(api, g):
    outs = [k for k in api if g[k]["output"]]
    if not outs: return "prompt_no_outputs"
    for k, v in api.items():
        for i in g[k]["inputs"]:
            if i["name"] not in v["inputs"]: return f"required_input_missing: {i['name']} of {g[k]['cls']}"
    return "valid"
def state(base, **modes):
    g = copy.deepcopy(base)
    for k, m in modes.items(): g[k[1:]]["mode"] = m
    return g
def wires(api): return " ".join(f"{k}<-{v[0]}" for n in api.values() for k, v in n["inputs"].items() if isinstance(v, list)) or "-"
rows = [("as drawn", state(CHAIN)), ("bypass 2 ImageBlur", state(CHAIN, n2=BYPASS)), ("mute 2 ImageBlur", state(CHAIN, n2=NEVER)), ("bypass 2 and 4", state(CHAIN, n2=BYPASS, n4=BYPASS)), ("mute 2 and 4", state(CHAIN, n2=NEVER, n4=NEVER)), ("mute 5 PreviewImage", state(CHAIN, n5=NEVER)), ("bypass 1 EmptyImage", state(CHAIN, n1=BYPASS))]
print(f"{'blur then invert':<22}{'nodes sent':<14}{'wires':<28}server says")
res = {}
for name, g in rows:
    api = graph_to_prompt(g); res[name] = (api, server_says(api, g))
    print(f"{name:<22}{' '.join(api):<14}{wires(api):<28}{res[name][1]}")
assert "3" not in res["as drawn"][0] and "6" not in res["as drawn"][0]                    # the reroute and the note never travel
assert res["as drawn"][0]["4"]["inputs"]["image"] == ["2", 0]                             # the wire goes straight through the reroute
assert res["bypass 2 ImageBlur"][0]["4"]["inputs"]["image"] == ["1", 0] and res["bypass 2 ImageBlur"][1] == "valid"
assert res["mute 2 ImageBlur"][1].startswith("required_input_missing") and res["mute 5 PreviewImage"][1] == "prompt_no_outputs"
print(f"\n{'latent to picture':<22}{'nodes sent':<14}{'wires':<28}server says")
for name, g in (("as drawn", state(DECODE)), ("bypass 3 VAEDecode", state(DECODE, n3=BYPASS)), ("mute 3 VAEDecode", state(DECODE, n3=NEVER))):
    api = graph_to_prompt(g); s = server_says(api, g)
    print(f"{name:<22}{' '.join(api):<14}{wires(api):<28}{s}")
    if name.startswith("bypass"): assert s.startswith("required_input_missing")
print("\nthe JSON for 'bypass 2 ImageBlur':")
print(json.dumps(res["bypass 2 ImageBlur"][0]))
assert "mode" not in json.dumps(res["bypass 2 ImageBlur"][0])
print("the word mode appears in it:", "mode" in json.dumps(res["bypass 2 ImageBlur"][0]))
