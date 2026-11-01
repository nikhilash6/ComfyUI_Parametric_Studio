# CU-415 lab: hash a graph, write and read PNG metadata, and test what a seed fixes. CPU, no model.
import hashlib, json, struct, zlib, torch
def canon(g): return json.dumps(g, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def gh(g): return hashlib.sha256(canon(g).encode()).hexdigest()[:12]
G = {"3": {"class_type": "KSampler", "inputs": {"seed": 42, "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "karras", "denoise": 1.0, "model": ["4", 0]}}, "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}}}
base = gh(G); print("graph hash:", base)
def edit(f): g = json.loads(json.dumps(G)); f(g); return g
reord = json.loads(json.dumps(dict(reversed(list(G.items())))))
tests = {"same graph, keys in another order": reord, "seed 42 -> 43": edit(lambda g: g["3"]["inputs"].update(seed=43)), "node id 4 -> 40 (and the wire)": {"3": {**G["3"], "inputs": {**G["3"]["inputs"], "model": ["40", 0]}}, "40": G["4"]}, "cfg 7 -> 7.0": edit(lambda g: g["3"]["inputs"].update(cfg=7))}
print("\nchange                               hash changes?")
for k, g in tests.items(): print(f"{k:<36s} {gh(g) != base}")
print(f"{'new weights under the same file name':<36s} False, the graph only holds the name")
assert gh(reord) == base and gh(tests["seed 42 -> 43"]) != base and gh(tests["node id 4 -> 40 (and the wire)"]) != base and gh(tests["cfg 7 -> 7.0"]) != base
# PNG metadata, as SaveImage writes it: a text chunk named prompt, and one per key of extra_pnginfo such as workflow. A minimal PNG is built here and read back.
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
def png(meta):
    raw = b"\x00" + bytes([200, 100, 50]); out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    for k, v in meta.items(): out += chunk(b"tEXt", k.encode() + b"\x00" + v.encode())
    return out + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
def read(b):
    p = 8; meta = {}
    while p < len(b):
        n = struct.unpack(">I", b[p:p + 4])[0]; t = b[p + 4:p + 8]; d = b[p + 8:p + 8 + n]; p += 12 + n
        if t == b"tEXt": k, v = d.split(b"\x00", 1); meta[k.decode()] = v.decode()
    return meta
f = png({"prompt": json.dumps(G)}); m = read(f); print("\nPNG with metadata:", len(f), "bytes, keys", list(m), " hash of what's stored:", gh(json.loads(m["prompt"]))); assert gh(json.loads(m["prompt"])) == base
g = png({}); print("with --disable-metadata:", len(g), "bytes, keys", list(read(g))); assert read(g) == {}
print("hash of the file differs between the two:", hashlib.sha256(f).hexdigest() != hashlib.sha256(g).hexdigest())
# What a seed fixes, with the call comfy/sample.py makes: torch.randn(shape, generator=torch.manual_seed(seed), on the CPU).
def noise(shape, seed): return torch.randn(shape, generator=torch.manual_seed(seed))
a = noise((1, 4, 8, 8), 42); print("\nsame seed, same shape, equal noise:", torch.equal(a, noise((1, 4, 8, 8), 42)))
print("first image of a batch of 2 equals a batch of 1:", torch.equal(noise((2, 4, 8, 8), 42)[:1], a))
w = noise((1, 4, 8, 16), 42); print("same seed, wider image, same noise in the same place:", torch.equal(w[..., :8], a)); assert not torch.equal(w[..., :8], a)
# A record: enough to find out later why two runs differ. Only the first part can be computed from the graph.
rec = {"graph_sha256": base, "comfyui": "v0.43.0", "torch": "from /system_stats", "weights_sha256": "hash each file yourself", "packs": "git commit of each", "seed": 42, "hardware": "GPU name and driver"}
print("\nrecord fields:", list(rec))
