# CU-296 lab: what the seed does and does not fix. prepare_noise is ported from comfy/sample.py. No model runs. A small PNG with a graph inside is written and read back, using the same text chunks SaveImage writes.
import torch, struct, zlib, json, hashlib
torch.set_num_threads(1)
def prepare_noise(shape, seed, noise_inds=None):
    g = torch.manual_seed(seed)
    if noise_inds is None: return torch.randn(shape, generator=g, device="cpu")
    uniq = sorted(set(noise_inds)); noises = []
    for i in range(uniq[-1] + 1):
        n = torch.randn([1] + list(shape)[1:], generator=g, device="cpu")
        if i in uniq: noises.append(n)
    return torch.cat([noises[uniq.index(i)] for i in noise_inds])
s = (1, 4, 8, 8)
a = prepare_noise(s, 42); b = prepare_noise(s, 42); c = prepare_noise(s, 43); print("same seed twice, same noise:", torch.equal(a, b), "  seed + 1, same noise:", torch.equal(a, c))
assert torch.equal(a, b) and not torch.equal(a, c)
batch = prepare_noise((4, 4, 8, 8), 42)
print("first of a batch of 4 equals a single:", torch.equal(batch[0:1], a))
print("third of a batch of 4 equals a single with that seed:", torch.equal(batch[2:3], a))
print("third of a batch of 4 equals seed + 2:", torch.equal(batch[2:3], prepare_noise(s, 44)))
idx = prepare_noise((1, 4, 8, 8), 42, noise_inds=[2]); print("third, rebuilt with batch_index [2] (LatentFromBatch):", torch.equal(batch[2:3], idx))
assert torch.equal(batch[0:1], a) and not torch.equal(batch[2:3], a) and torch.equal(batch[2:3], idx)
# Read a graph back from a PNG. SaveImage calls metadata.add_text("prompt", json) with Pillow, which writes tEXt chunks.
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
def tiny_png(texts):
    raw = zlib.compress(b"\x00\x10\x20\x30")
    p = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    for k, v in texts.items(): p += chunk(b"tEXt", k.encode() + b"\0" + v.encode())
    return p + chunk(b"IDAT", raw) + chunk(b"IEND", b"")
def read_text(p):
    i = 8; out = {}
    while i < len(p):
        n = struct.unpack(">I", p[i:i + 4])[0]; t = p[i + 4:i + 8]; d = p[i + 8:i + 8 + n]; i += 12 + n
        if t == b"tEXt": k, v = d.split(b"\0", 1); out[k.decode()] = v.decode()
    return out
g = {"5": {"class_type": "KSampler", "inputs": {"seed": 424242, "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "karras"}}, "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}}}
got = read_text(tiny_png({"prompt": json.dumps(g)})); back = json.loads(got["prompt"])
print("\nread from the PNG:", {k: back["5"]["inputs"][k] for k in ("seed", "steps", "cfg", "sampler_name", "scheduler")}, back["1"]["inputs"])
assert back == g
print("a screenshot, or a re-saved JPEG, has no such chunk:", read_text(tiny_png({})))
# Diff two graphs: the checklist in code.
theirs = back; mine = json.loads(json.dumps(g)); mine["5"]["inputs"]["scheduler"] = "normal"; mine["5"]["inputs"]["cfg"] = 8.0
diff = [(n, k, theirs[n]["inputs"][k], mine[n]["inputs"].get(k)) for n in theirs for k in theirs[n]["inputs"] if theirs[n]["inputs"][k] != mine[n]["inputs"].get(k)]
for d in diff: print("differs:", d)
assert len(diff) == 2
