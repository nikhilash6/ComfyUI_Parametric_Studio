"""Test helpers: a minimal glTF binary and a synthetic 23-bone humanoid (z up, metres, facing -Y)."""
import json
import struct


def make_glb(doc: dict) -> bytes:
    data = json.dumps(doc).encode()
    data += b" " * ((4 - len(data) % 4) % 4)
    total = 12 + 8 + len(data)
    return b"glTF" + struct.pack("<II", 2, total) + struct.pack("<II", len(data), 0x4E4F534A) + data


#: (name, parent, head, tail). The character faces -Y, so its left is +X. Bone lengths follow a 1.70 m adult.
HUMANOID = [
    ("hips", "", (0, 0, 0.95), (0, 0, 1.05)),
    ("spine1", "hips", (0, 0, 1.05), (0, 0, 1.18)),
    ("spine2", "spine1", (0, 0, 1.18), (0, 0, 1.30)),
    ("chest", "spine2", (0, 0, 1.30), (0, 0, 1.42)),
    ("neck", "chest", (0, 0, 1.42), (0, 0, 1.52)),
    ("head", "neck", (0, 0, 1.52), (0, 0, 1.69)),
    ("head_end", "head", (0, 0, 1.69), (0, 0, 1.70)),
    ("l_shoulder", "chest", (0.03, 0, 1.40), (0.17, 0, 1.40)),
    ("l_arm", "l_shoulder", (0.17, 0, 1.40), (0.45, 0, 1.40)),
    ("l_forearm", "l_arm", (0.45, 0, 1.40), (0.70, 0, 1.40)),
    ("l_hand", "l_forearm", (0.70, 0, 1.40), (0.80, 0, 1.40)),
    ("r_shoulder", "chest", (-0.03, 0, 1.40), (-0.17, 0, 1.40)),
    ("r_arm", "r_shoulder", (-0.17, 0, 1.40), (-0.45, 0, 1.40)),
    ("r_forearm", "r_arm", (-0.45, 0, 1.40), (-0.70, 0, 1.40)),
    ("r_hand", "r_forearm", (-0.70, 0, 1.40), (-0.80, 0, 1.40)),
    ("l_upleg", "hips", (0.10, 0, 0.95), (0.10, 0, 0.52)),
    ("l_leg", "l_upleg", (0.10, 0, 0.52), (0.10, 0, 0.09)),
    ("l_foot", "l_leg", (0.10, 0, 0.09), (0.10, -0.12, 0.02)),
    ("l_toe", "l_foot", (0.10, -0.12, 0.02), (0.10, -0.18, 0.0)),
    ("r_upleg", "hips", (-0.10, 0, 0.95), (-0.10, 0, 0.52)),
    ("r_leg", "r_upleg", (-0.10, 0, 0.52), (-0.10, 0, 0.09)),
    ("r_foot", "r_leg", (-0.10, 0, 0.09), (-0.10, -0.12, 0.02)),
    ("r_toe", "r_foot", (-0.10, -0.12, 0.02), (-0.10, -0.18, 0.0)),
]


def bones(rename=None) -> list[dict]:
    r = rename or {}
    return [{"name": r.get(n, n), "parent": r.get(p, p) if p else "", "head": list(h), "tail": list(t)}
            for n, p, h, t in HUMANOID]


def ctx_for(lib, meta, tmp_path, outputs=None, **seams):
    """What a local step gets at build time, with a work folder under tmp_path."""
    return {"library": lib, "asset": meta, "work": tmp_path / "work", "outputs": outputs or {}, **seams}


def glb_file(path, doc=None) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(make_glb(doc or {"asset": {"version": "2.0"}, "nodes": [{"name": "body"}], "meshes": [{}]}))
    return str(path)
