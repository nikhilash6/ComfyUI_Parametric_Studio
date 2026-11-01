# CU-294 lab: tell a good model file from a broken one by reading its first bytes, using the published safetensors layout: 8 bytes giving the header length, then a JSON header, then data. Files here are made in memory. The error names in the lesson come from running ComfyUI's loader on the same three kinds of bad file.
import json, struct, hashlib
def make(tensors):
    h = {}; pos = 0; body = b""
    for name, (shape, data) in tensors.items():
        h[name] = {"dtype": "F32", "shape": shape, "data_offsets": [pos, pos + len(data)]}; pos += len(data); body += data
    head = json.dumps(h).encode(); return struct.pack("<Q", len(head)) + head + body
def inspect(b):
    if len(b) < 8: return "too short to hold a header"
    n = struct.unpack("<Q", b[:8])[0]
    if n > len(b): return f"not safetensors: first 8 bytes say a {n:,} byte header, the file has {len(b)} bytes"
    try: h = json.loads(b[8:8 + n])
    except Exception: return "header is not JSON"
    end = max((v["data_offsets"][1] for k, v in h.items() if k != "__metadata__"), default=0)
    if 8 + n + end != len(b): return f"cut short or padded: header expects {8 + n + end} bytes, file has {len(b)}"
    return f"looks whole: {len(h)} tensors, first key {next(iter(h))}"
good = make({"first_stage_model.decoder.conv_in.weight": ([2], b"\0" * 8), "model.diffusion_model.input.weight": ([2], b"\0" * 8)})
FILES = {"a good file": good, "cut short by a failed download": good[:-4], "a web page saved under a model's name": b"<html>not a model</html>" * 5, "an empty file": b""}
res = {}
for k, b in FILES.items(): res[k] = inspect(b); print(f"{k:40}{res[k]}")
assert res["a good file"].startswith("looks whole") and res["cut short by a failed download"].startswith("cut short") and res["a web page saved under a model's name"].startswith("not safetensors")
# Hash: the same name is not the same file.
a = hashlib.sha256(good).hexdigest(); c = hashlib.sha256(good[:-4]).hexdigest(); print(f"\nsha256 of the good file  {a[:16]}\nsha256 of the short file {c[:16]}"); assert a != c
# The check on a file menu. A port of the value_not_in_list branch of validate_inputs: long menus are not printed.
def menu(name, val, options):
    if val in options: return None
    info = f"(list of length {len(options)})" if len(options) > 20 else str(options)
    return f"Value not in list: {name}: {val!r} not in {info}"
print(); print(menu("ckpt_name", "model_a.safetensors", [])); print(menu("ckpt_name", "model_a.safetensors", ["b.safetensors"])); print(menu("ckpt_name", "model_a.safetensors", [f"m{i}" for i in range(30)]))
assert "list of length 30" in menu("x", "y", [f"m{i}" for i in range(30)]) and menu("x", "y", ["y"]) is None
# Subfolders count: the name in the menu includes the folder.
print("\nsame file, but the graph was saved on a machine with a folder:", menu("ckpt_name", "sd/model.safetensors", ["model.safetensors"]))
