# CU-384 lab: a pickle runs code when it is loaded. What the code does here is print a line. Run on PyTorch 2.x with torch.load's limit on and off.
import io, json, pickle, struct, torch
class Payload:
    def __reduce__(self): return (print, ("  >>> this line was printed by loading a file. It could have been anything.",))
blob = pickle.dumps({"weight": 1.0, "extra": Payload()})
print(f"a pickle, {len(blob)} bytes. Loading it with pickle.loads:")
pickle.loads(blob)
print("\nthe same trick in a file torch.save wrote")
buf = io.BytesIO(); torch.save({"weight": torch.zeros(2), "extra": Payload()}, buf); data = buf.getvalue()
print("torch.load(weights_only=True), which is what comfy/utils.py load_torch_file passes:")
refused = False
try:
    torch.load(io.BytesIO(data), weights_only=True); print("  loaded")
except pickle.UnpicklingError as e:
    refused = True; print("  refused: UnpicklingError")
assert refused
print("torch.load(weights_only=False):")
out = torch.load(io.BytesIO(data), weights_only=False); print(f"  loaded, keys {sorted(out)}")
assert out["extra"] is None
print("\nplain weights pass the limit")
buf = io.BytesIO(); torch.save({"state_dict": {"a": torch.ones(2)}}, buf); d = torch.load(io.BytesIO(buf.getvalue()), weights_only=True); print(f"  keys {list(d)}, tensor {d['state_dict']['a'].tolist()}")
print("\nsafetensors has no code path to attack this way: an 8 byte length, JSON, then raw numbers")
head = {"a": {"dtype": "F32", "shape": [2], "data_offsets": [0, 8]}, "__metadata__": {"note": "strings only"}}; raw = json.dumps(head).encode(); f = struct.pack("<Q", len(raw)) + raw + struct.pack("<2f", 1.0, 2.0)
n = struct.unpack("<Q", f[:8])[0]; h = json.loads(f[8:8 + n]); vals = struct.unpack("<2f", f[8 + n:])
print(f"  header {h['a']}  numbers {vals}")
assert vals == (1.0, 2.0) and h["__metadata__"]["note"] == "strings only"
print("\nthe word in a filename does not decide anything. Read what the bytes start with")
def kind(b):
    if b[:4] == b"PK\x03\x04": return "zip, the torch.save format, holds a pickle"
    if b[:1] == b"\x80": return "raw pickle"
    if b[8:9] == b"{": return "looks like safetensors"
    return "unknown"
buf = io.BytesIO(); torch.save({}, buf)
for name, b in (("a.ckpt from torch.save", buf.getvalue()), ("b.pt that is a raw pickle", blob), ("c.bin that is safetensors", f)): print(f"  {name:28s} {kind(b)}")
assert kind(f).startswith("looks") and kind(blob) == "raw pickle"
print("\nwhat to search a pack for, as text")
for s in ("pickle.load", "torch.load(", "weights_only=False", "trust_remote_code=True", "numpy.load(", "allow_pickle=True"): print(f"  {s}")
