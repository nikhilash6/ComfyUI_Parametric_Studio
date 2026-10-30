# CU-107 lab: a safetensors file built and read by hand, a pickle that runs code, and how a family is told from a header. Standard library only, under a second.
# Run: python lab.py
# The file layout is the one in the safetensors README: 8 bytes N (unsigned, little-endian), N bytes of JSON, then the byte buffer.
import json, pickle, struct

BYTES = {"F32": 4, "F16": 2, "BF16": 2, "I64": 8}                 # bytes per value for the dtype names used below
CODE = {"F32": "f", "F16": "e", "I64": "q"}                       # struct codes for reading values back (bfloat16 has none)
def prod(shape):
    n = 1
    for d in shape: n *= d
    return n

def build(tensors, metadata=None):
    """tensors: name -> (dtype, shape, raw bytes). Returns the bytes of a safetensors file."""
    header, pos = ({"__metadata__": metadata} if metadata else {}), 0
    for name, (dt, shape, raw) in tensors.items():
        assert len(raw) == prod(shape) * BYTES[dt]
        header[name] = {"dtype": dt, "shape": shape, "data_offsets": [pos, pos + len(raw)]}; pos += len(raw)
    h = json.dumps(header, separators=(",", ":")).encode()
    h += b" " * (-len(h) % 8)                                      # trailing spaces are allowed in the header
    return struct.pack("<Q", len(h)) + h + b"".join(raw for _, _, raw in tensors.values())

def read_header(buf):
    n = struct.unpack("<Q", buf[:8])[0]
    if n > 100_000_000: raise ValueError("header larger than the 100 MB limit")
    if 8 + n > len(buf): raise ValueError("header is longer than the file")
    raw = buf[8:8 + n]
    if raw[:1] != b"{": raise ValueError("header must begin with {")
    def no_duplicates(pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)): raise ValueError("duplicate key in header")
        return dict(pairs)
    return n, json.loads(raw, object_pairs_hook=no_duplicates)

def validate(buf):
    """The checks the README asks for: string-only metadata, sizes that match shape and dtype, and a byte buffer with no holes."""
    n, h = read_header(buf); meta = h.pop("__metadata__", {})
    if not all(isinstance(v, str) for v in meta.values()): raise ValueError("__metadata__ values must be strings")
    pos = 0
    for b, e, name in sorted((t["data_offsets"][0], t["data_offsets"][1], k) for k, t in h.items()):
        if b != pos: raise ValueError(f"hole or overlap before {name}")
        if e - b != prod(h[name]["shape"]) * BYTES[h[name]["dtype"]]: raise ValueError(f"{name}: byte range does not match shape and dtype")
        pos = e
    if pos != len(buf) - 8 - n: raise ValueError("the buffer is not the size the header says")
    return h

def tensor(buf, name):                                             # read one tensor without touching the others
    n, h = read_header(buf); t = h[name]; b, e = t["data_offsets"]
    return struct.unpack("<" + CODE[t["dtype"]] * prod(t["shape"]), buf[8 + n + b: 8 + n + e])

# 1. Build a small file and read it back.
weights = {"layer1.weight": ("F32", [2, 3], struct.pack("<6f", 0.5, 1.5, -2.0, 4.0, 8.0, 0.25)),
           "layer1.bias": ("F16", [4], struct.pack("<4e", 0.25, -1.0, 2.5, 0.125)),
           "ids": ("I64", [5], struct.pack("<5q", 7, 8, 9, 10, 11))}
buf = build(weights, {"format": "pt"})
n, h = read_header(buf)
print(f"file: {len(buf)} bytes = 8 (header length) + {n} (JSON header) + {len(buf) - 8 - n} (tensor bytes);  first 8 bytes: {buf[:8].hex(' ')}")
print("\nname           dtype  shape   offsets    bytes")
for k, t in h.items():
    if k != "__metadata__": print(f"{k:<14} {t['dtype']:<6} {str(t['shape']):<7} {str(t['data_offsets']):<10} {t['data_offsets'][1] - t['data_offsets'][0]}")
print(f"__metadata__: {h['__metadata__']}")
assert validate(buf) and tensor(buf, "layer1.weight") == (0.5, 1.5, -2.0, 4.0, 8.0, 0.25) and tensor(buf, "ids") == (7, 8, 9, 10, 11) and tensor(buf, "layer1.bias")[3] == 0.125
big = build({"w": ("F16", [1000, 1000], bytes(2_000_000))})
bn = struct.unpack("<Q", big[:8])[0]
print(f"\none 1000 x 1000 float16 tensor: file {len(big):,d} bytes, and 8 + {bn} = {8 + bn} bytes are enough to learn its name, dtype and shape")

# 2. What a loader must refuse.
good = bytearray(buf)
def with_header(change):
    hh = json.loads(buf[8:8 + n]); change(hh); raw = json.dumps(hh, separators=(",", ":")).encode()
    return struct.pack("<Q", len(raw)) + raw + buf[8 + n:]
cases = {"offsets shifted by 4": with_header(lambda hh: hh["layer1.bias"].update(data_offsets=[28, 36])),
         "shape no longer fits the bytes": with_header(lambda hh: hh["layer1.weight"].update(shape=[2, 4])),
         "file cut short by 10 bytes": bytes(good[:-10]),
         "header length claims 10^12 bytes": struct.pack("<Q", 10 ** 12) + bytes(good[8:]),
         "metadata value is a number": with_header(lambda hh: hh["__metadata__"].update(step=5))}
print("\nchecks on damaged copies")
for label, bad in cases.items():
    try: validate(bad); verdict = "accepted"
    except ValueError as e: verdict = f"refused: {e}"
    print(f"{label:<34} {verdict}")
    assert verdict.startswith("refused")

# 3. A pickle is a program. Loading it calls whatever the file says to call.
ran = []
def record(message): ran.append(message)                           # stands in for any function at all
class Payload:
    def __reduce__(self): return (record, ("a function the loader never meant to call",))
pickle.loads(pickle.dumps(Payload()))
print(f"\nafter pickle.loads on a harmless payload: ran = {ran}")
assert ran

# 4. Family from a header alone. The key names are the ones ComfyUI's detector reads and the shapes are those of Stable Diffusion 1.5 and SDXL base files.
P = "model.diffusion_model."
MOCK = {"SD 1.5 style file": {P + "input_blocks.0.0.weight": [320, 4, 3, 3], P + "input_blocks.1.1.transformer_blocks.0.attn2.to_k.weight": [320, 768]},
        "SDXL style file": {P + "input_blocks.0.0.weight": [320, 4, 3, 3], P + "input_blocks.4.1.transformer_blocks.0.attn2.to_k.weight": [640, 2048], P + "label_emb.0.0.weight": [1280, 2816]},
        "VAE-only file": {"encoder.conv_in.weight": [128, 3, 3, 3], "decoder.conv_in.weight": [512, 4, 3, 3]}}
FAMILIES = {"SD 1.x": {"model_channels": 320, "context_dim": 768, "adm_in_channels": None},
            "SDXL": {"model_channels": 320, "context_dim": 2048, "adm_in_channels": 2816}}
def read_config(shapes):                                           # what detect_unet_config reads: three shapes
    if P + "input_blocks.0.0.weight" not in shapes: return None
    ctx = [s[1] for k, s in shapes.items() if k.startswith(P + "input_blocks.") and k.endswith("attn2.to_k.weight")]
    y = shapes.get(P + "label_emb.0.0.weight")
    return {"model_channels": shapes[P + "input_blocks.0.0.weight"][0], "context_dim": ctx[0] if ctx else None, "adm_in_channels": y[1] if y else None}
print(f"\n{'file':<19}{'read from the shapes':<76}family")
for label, shapes in MOCK.items():
    cfg = read_config(shapes); fam = [f for f, req in FAMILIES.items() if cfg and all(cfg[k] == v for k, v in req.items())]
    print(f"{label:<19}{str(cfg):<76}{fam[0] if fam else 'no match'}")
assert [f for f, req in FAMILIES.items() if all(read_config(MOCK['SDXL style file'])[k] == v for k, v in req.items())] == ["SDXL"] and read_config(MOCK["VAE-only file"]) is None

# 5. Size is values times bytes per value.
print("\n1,000,000,000 values stored as   bytes            GiB")
for dt in ("F32", "F16", "BF16"): print(f"{dt:<30}{10 ** 9 * BYTES[dt]:>16,d} {10 ** 9 * BYTES[dt] / 2 ** 30:>8.2f}")
