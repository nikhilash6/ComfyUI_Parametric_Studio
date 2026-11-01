# CU-372 lab: read parameter counts from a safetensors header without loading any weights, then do the sum. The file is built in memory. Sizes are generic, not any real model's.
import json, struct, io, torch
GB = 1024 ** 3; MB = 1024 ** 2
SIZE = {"F32": 4, "F16": 2, "BF16": 2, "F8_E4M3": 1, "I8": 1, "U8": 1}
def make_file(tensors):
    """safetensors layout: 8 bytes little endian header length, then JSON, then raw data."""
    head = {}; pos = 0
    for k, (dt, shape) in tensors.items():
        n = SIZE[dt]
        for s in shape: n *= s
        head[k] = {"dtype": dt, "shape": shape, "data_offsets": [pos, pos + n]}; pos += n
    raw = json.dumps(head).encode(); return struct.pack("<Q", len(raw)) + raw, pos
def read_header(blob):
    n = struct.unpack("<Q", blob[:8])[0]; return json.loads(blob[8:8 + n])
blob, data = make_file({"blocks.0.weight": ("F16", [1024, 1024]), "blocks.1.weight": ("F16", [1024, 1024]), "out.weight": ("F32", [1024, 16]), "out.bias": ("F32", [16])})
h = read_header(blob); params = 0; by = {}
for k, v in h.items():
    n = 1
    for s in v["shape"]: n *= s
    params += n; by[v["dtype"]] = by.get(v["dtype"], 0) + n
print(f"header {len(blob)} bytes read, data {data} bytes not touched")
print(f"tensors {len(h)}, parameters {params:,}, by type {by}")
assert params == 2 * 1024 * 1024 + 16384 + 16 and sum(by[d] * SIZE[d] for d in by) == data
print("\nbudget sheet. Every size here is an example. Replace them with your own files' sizes")
def sheet(card, parts, work, keep_te):
    print(f"  card {card} GB, reserved 0.39 GB")
    used = 0.39
    for n, g, on in parts:
        if on or keep_te: used += g; print(f"    {n:32s} {g:6.2f} GB")
    print(f"    {'working memory (your estimate)':32s} {work:6.2f} GB"); used += work
    print(f"    total {used:.2f} GB, left over {card - used:.2f} GB"); return card - used
P = [("diffusion model file", 11.6, True), ("text encoder file", 8.0, False), ("VAE file", 0.34, True)]
a = sheet(24, P, 2.0, True); b = sheet(12, P, 2.0, True); c = sheet(12, P, 2.0, False)
P8 = [("the same model, fp8", 5.8, True), ("VAE file", 0.34, True)]
d = sheet(12, P8, 2.0, False)
assert a > 0 and b < 0 and c < 0 and d > 0
print("\nthe same model in other forms, weights only. File size is about parameters x bytes")
for name, per in (("fp16", 2), ("fp8", 1), ("4-bit, with scales", 4.5 / 8)):
    print(f"  6 billion parameters, {name:20s} {6e9 * per / GB:6.2f} GB")
assert abs(6e9 * 2 / GB - 11.18) < 0.01
print("\nthe sizes that move with your settings: working memory estimate for a model with factor 1, fp16, CFG on")
for side, b in ((1024, 1), (1024, 2), (1536, 1), (2048, 1)):
    area = b * 2 * (side // 8) ** 2; print(f"  {side} px, batch {b}: {area * 2 * 0.01:8.1f} MB")
