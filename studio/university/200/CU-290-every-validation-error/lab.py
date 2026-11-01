# CU-290 lab: a small validator with the same order of checks as validate_prompt and validate_inputs in execution.py, on a stand-in table of node classes. The third item of each case is the text ComfyUI v0.43.0's own validate_prompt returned for the same graph on a CPU, and the lab asserts it matches.
CLASSES = {
    "EmptyImage": {"req": {"width": ("INT", 1, 16384), "height": ("INT", 1, 16384)}, "out": ("IMAGE",)},
    "SolidMask": {"req": {"value": ("FLOAT", 0.0, 1.0)}, "out": ("MASK",)},
    "ImageInvert": {"req": {"image": ("IMAGE",)}, "out": ("IMAGE",)},
    "ImageScale": {"req": {"image": ("IMAGE",), "upscale_method": (["nearest-exact", "bilinear", "area", "bicubic", "lanczos"],)}, "out": ("IMAGE",)},
    "LoadImage": {"req": {"image": ("STRING",)}, "out": ("IMAGE",), "check": lambda v: f"Invalid image file: {v['image']}"},
    "PreviewImage": {"req": {"images": ("IMAGE",)}, "out": (), "output": True},
}
def bad(t, m, d): return {"type": t, "message": m, "details": d}
def validate_inputs(p, i, seen, stack):
    if i in seen: return seen[i]
    if i in stack:
        path = stack[stack.index(i):] + [i]
        return (False, [bad("dependency_cycle", "Dependency cycle detected", " -> ".join(f"{n} ({p[n]['class_type']})" for n in path))])
    c = CLASSES[p[i]["class_type"]]; ins = p[i]["inputs"]; errs = []; ok = True
    for x, spec in c["req"].items():
        if x not in ins: errs.append(bad("required_input_missing", "Required input is missing", x)); continue
        v = ins[x]; t = spec[0]
        if isinstance(v, list):
            if len(v) != 2: errs.append(bad("bad_linked_input", "Bad linked input, must be a length-2 list of [node_id, slot_index]", x)); continue
            got = CLASSES[p[v[0]]["class_type"]]["out"][v[1]]                  # KeyError or IndexError here is caught one level up
            if got != t: errs.append(bad("return_type_mismatch", "Return type mismatch between linked nodes", f"{x}, received_type({got}) mismatch input_type({t})")); continue
            try:
                r = validate_inputs(p, v[0], seen, stack + [i])
            except Exception as ex:
                seen[v[0]] = (False, [bad("exception_during_inner_validation", "Exception when validating inner node", str(ex))]); ok = False; continue
            if not r[0]:
                ok = False
                if r[1] and r[1][0]["type"] == "dependency_cycle": errs += r[1]
            continue
        try:
            if t == "INT": v = int(v)
            if t == "FLOAT": v = float(v)
        except Exception as ex:
            errs.append(bad("invalid_input_type", f"Failed to convert an input value to a {t} value", f"{x}, {v}, {ex}")); continue
        if len(spec) > 1 and v < spec[1]: errs.append(bad("value_smaller_than_min", f"Value {v} smaller than min of {spec[1]}", x)); continue
        if len(spec) > 1 and v > spec[2]: errs.append(bad("value_bigger_than_max", f"Value {v} bigger than max of {spec[2]}", x)); continue
        if isinstance(t, list) and v not in t: errs.append(bad("value_not_in_list", "Value not in list", f"{x}: {v!r} not in {t}"))
    if "check" in c:
        errs.append(bad("custom_validation_failed", "Custom validation failed for node", "image - " + c["check"](ins)))
    seen[i] = (ok and not errs, errs); return seen[i]
def validate_prompt(p):
    outs = []
    for i, n in p.items():
        if "class_type" not in n: return bad("missing_node_type", f"Node 'ID #{i}' has no class_type. The workflow may be corrupted or a custom node is missing.", f"Node ID '#{i}'")
        if n["class_type"] not in CLASSES: return bad("missing_node_type", f"Node '{n['class_type']}' not found. The custom node may not be installed.", f"Node ID '#{i}'")
        if CLASSES[n["class_type"]].get("output"): outs.append(i)
    if not outs: return bad("prompt_no_outputs", "Prompt has no outputs", "")
    found = []; good = []; seen = {}
    for o in outs:
        try: r = validate_inputs(p, o, seen, [])
        except Exception as ex: r = (False, [bad("exception_during_validation", "Exception when validating node", str(ex))]); seen[o] = r
        if r[0]: good.append(o)
        else: found += [(k, e) for k, v in seen.items() for e in v[1]]
    return {"good": good, "errors": found}
E = {"class_type": "EmptyImage", "inputs": {"width": 8, "height": 8}}
def P(src): return {"class_type": "PreviewImage", "inputs": {"images": src}}
CASES = [
 ("no output node", {"1": E}, "prompt_no_outputs: Prompt has no outputs"),
 ("class not installed", {"1": {"class_type": "SuperKSampler", "inputs": {}}, "2": P(["1", 0])}, "missing_node_type: Node 'SuperKSampler' not found. The custom node may not be installed."),
 ("no class_type at all", {"1": {"inputs": {}}, "2": P(["1", 0])}, "missing_node_type: Node 'ID #1' has no class_type. The workflow may be corrupted or a custom node is missing."),
 ("input left out", {"1": {"class_type": "ImageInvert", "inputs": {}}, "2": P(["1", 0])}, "required_input_missing: Required input is missing: image"),
 ("wire with 3 items", {"1": E, "2": P(["1", 0, 7])}, "bad_linked_input: Bad linked input, must be a length-2 list of [node_id, slot_index]: images"),
 ("MASK into IMAGE", {"1": {"class_type": "SolidMask", "inputs": {"value": 1.0}}, "2": P(["1", 0])}, "return_type_mismatch: Return type mismatch between linked nodes: images, received_type(MASK) mismatch input_type(IMAGE)"),
 ("text in a number", {"1": {"class_type": "EmptyImage", "inputs": {"width": "wide", "height": 8}}, "2": P(["1", 0])}, "invalid_input_type: Failed to convert an input value to a INT value: width, wide, invalid literal for int() with base 10: 'wide'"),
 ("width 0", {"1": {"class_type": "EmptyImage", "inputs": {"width": 0, "height": 8}}, "2": P(["1", 0])}, "value_smaller_than_min: Value 0 smaller than min of 1: width"),
 ("width 999999", {"1": {"class_type": "EmptyImage", "inputs": {"width": 999999, "height": 8}}, "2": P(["1", 0])}, "value_bigger_than_max: Value 999999 bigger than max of 16384: width"),
 ("menu value not offered", {"1": E, "3": {"class_type": "ImageScale", "inputs": {"image": ["1", 0], "upscale_method": "magic"}}, "2": P(["3", 0])}, "value_not_in_list: Value not in list: upscale_method: 'magic' not in ['nearest-exact', 'bilinear', 'area', 'bicubic', 'lanczos']"),
 ("file not there", {"1": {"class_type": "LoadImage", "inputs": {"image": "nothing_here.png"}}, "2": P(["1", 0])}, "custom_validation_failed: Custom validation failed for node: image - Invalid image file: nothing_here.png"),
 ("two nodes in a loop", {"1": {"class_type": "ImageInvert", "inputs": {"image": ["3", 0]}}, "3": {"class_type": "ImageInvert", "inputs": {"image": ["1", 0]}}, "2": P(["1", 0])}, "dependency_cycle: Dependency cycle detected: 1 (ImageInvert) -> 3 (ImageInvert) -> 1 (ImageInvert)"),
 ("wire to a missing node, mid graph", {"1": {"class_type": "ImageInvert", "inputs": {"image": ["99", 0]}}, "2": P(["1", 0])}, "exception_during_inner_validation: Exception when validating inner node: '99'"),
 ("wire to a missing node, on the output", {"2": P(["99", 0])}, "exception_during_validation: Exception when validating node: '99'"),
 ("wire to a missing slot", {"1": E, "2": P(["1", 5])}, "exception_during_validation: Exception when validating node: tuple index out of range"),
]
for name, g, real in CASES:
    r = validate_prompt(g)
    e = r if "type" in r else r["errors"][0][1]
    text = f"{e['type']}: {e['message']}" + (f": {e['details']}" if e["details"] and "type" not in r else "")
    print(f"{name:38}{text}")
    assert text == real, (text, real)
# One bad output does not sink a good one.
r = validate_prompt({"1": E, "2": P(["1", 0]), "3": {"class_type": "ImageInvert", "inputs": {}}, "4": P(["3", 0])})
print("\ntwo outputs, one broken: runs", r["good"], " reported:", r["errors"][0][1]["type"]); assert r["good"] == ["2"]
