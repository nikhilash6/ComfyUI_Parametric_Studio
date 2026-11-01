# CU-431 lab: what validate_inputs in execution.py does to a constant. This ports just the conversion and range branch, with the same order of checks. It is not ComfyUI, but every row below also ran through the real validate_prompt (see the lesson).
def check(kind, val, opts):
    try:
        if kind == "INT": val = int(val)
        if kind == "FLOAT": val = float(val)
        if kind == "STRING": val = str(val)
        if kind == "BOOLEAN": val = bool(val)
    except Exception as ex:
        return f"invalid_input_type: Failed to convert an input value to a {kind} value"
    if "min" in opts and val < opts["min"]: return f"value_smaller_than_min: Value {val} smaller than min of {opts['min']}"
    if "max" in opts and val > opts["max"]: return f"value_bigger_than_max: Value {val} bigger than max of {opts['max']}"
    return val
I = {"min": 0, "max": 10, "step": 2}; F = {"min": 0.0, "max": 1.0}
rows = [("INT", 3.7, I), ("INT", "3.7", I), ("INT", 3, I), ("INT", 11, I), ("FLOAT", "0.5", F), ("FLOAT", "nan", F), ("FLOAT", 2.0, F),
        ("BOOLEAN", "false", {}), ("BOOLEAN", 0, {}), ("STRING", 5, {}), ("STRING", None, {})]
print(f"{'type':8}{'you sent':10}the node receives")
out = {}
for k, v, o in rows:
    r = check(k, v, o); out[(k, repr(v))] = r
    print(f"{k:8}{v!r:10}{r!r}")
assert out[("INT", repr("3.7"))].startswith("invalid_input_type") and out[("INT", repr(3.7))] == 3
assert out[("BOOLEAN", repr("false"))] is True and out[("STRING", "None")] == "None"
nan = out[("FLOAT", repr("nan"))]; assert nan != nan
assert out[("INT", "3")] == 3     # step=2 is not checked: 3 passes

# Optional inputs: the server passes only what the prompt holds, so a default in the schema does not reach Python.
def call(fn, schema_required, prompt_inputs):
    missing = [k for k in schema_required if k not in prompt_inputs]
    if missing: return f"required_input_missing: {missing[0]}"
    return fn(**prompt_inputs)
def node(s, o=None): return {"s": s, "o": o}
print("\noptional o, schema default 3, left out of the prompt:", call(node, ["s"], {"s": "hi"}))
print("required s, left out of the prompt:                ", call(node, ["s"], {"o": 3}))
assert call(node, ["s"], {"s": "hi"})["o"] is None

# A wire is a list of two items. A widget value that is a list must be wrapped, or it is read as a wire.
def is_wire(v): return isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and isinstance(v[1], (int, float))
for v in (["1", 0], ["a"], {"__value__": ["a"]}, 5):
    print(f"{v!r:24} wire? {is_wire(v)}")
assert is_wire(["1", 0]) and not is_wire(["a"])
