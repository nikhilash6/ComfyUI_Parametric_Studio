import base64
import json
import struct
import zlib

import torch

import n_8_3d_model_generation_via_tripo as mod
from n_8_3d_model_generation_via_tripo import (
    PSN_Tripo_Text_Request_Builder,
    PSN_Tripo_Image_Request_Builder,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _validate_image,
    _image_to_base64_png,
)


def decode_png(b64):
    """Minimal decoder for the 8-bit RGB filter-0 PNGs the module writes."""
    data = base64.b64decode(b64)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, ihdr = 8, b"", None
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos:pos + 4])
        tag, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        (crc,) = struct.unpack(">I", data[pos + 8 + n:pos + 12 + n])
        assert crc == zlib.crc32(tag + body) & 0xFFFFFFFF
        if tag == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        pos += 12 + n
    w, h, depth, ctype = ihdr[0], ihdr[1], ihdr[2], ihdr[3]
    assert (depth, ctype) == (8, 2)
    raw = zlib.decompress(idat)
    assert len(raw) == h * (1 + 3 * w)
    out = torch.empty(h, w, 3, dtype=torch.uint8)
    for y in range(h):
        row = raw[y * (1 + 3 * w):(y + 1) * (1 + 3 * w)]
        assert row[0] == 0
        out[y] = torch.frombuffer(bytearray(row[1:]), dtype=torch.uint8).reshape(w, 3)
    return out


# 1. Module-level mappings: only the builders, old fabricating nodes gone
assert set(NODE_CLASS_MAPPINGS) == {"PSN_Tripo_Text_Request_Builder", "PSN_Tripo_Image_Request_Builder"}
assert set(NODE_DISPLAY_NAME_MAPPINGS) == set(NODE_CLASS_MAPPINGS)
assert not hasattr(mod, "PSN_Tripo_Text_To_3D")
assert not hasattr(mod, "PSN_Tripo_Image_To_3D")
assert not hasattr(mod, "_make_job_id")
assert not hasattr(mod, "_make_model_url")

# 2. INPUT_TYPES: no api_key (nothing is sent)
it = PSN_Tripo_Text_Request_Builder.INPUT_TYPES()
assert list(it["required"]) == ["prompt", "texture", "pbr"]
it2 = PSN_Tripo_Image_Request_Builder.INPUT_TYPES()
assert list(it2["required"]) == ["image", "texture"]

# 3. Text request: exact JSON content, no url / job id
node = PSN_Tripo_Text_Request_Builder()
(txt,) = node.run(prompt="  a red cube ", texture=True, pbr=False)
assert json.loads(txt) == {"type": "text_to_model", "prompt": "a red cube",
                           "texture": True, "pbr": False}
assert "tripo3d.ai" not in txt and "job" not in txt

# 4. Text request: different prompt gives different request
(txt2,) = node.run(prompt="a blue sphere", texture=True, pbr=True)
assert json.loads(txt2)["prompt"] == "a blue sphere" and txt2 != txt

# 5. Text: empty prompt raises ValueError, bad types raise TypeError
try:
    node.run(prompt="   ", texture=True, pbr=True)
    assert False, "should have raised"
except ValueError:
    pass
for kw in ({"prompt": 123}, {"prompt": "x", "texture": "y"}, {"prompt": "x", "pbr": 1}):
    try:
        node.run(**kw)
        assert False, "should have raised"
    except TypeError:
        pass

# 6. Image request: the PNG in the payload decodes to the input pixels
img = torch.rand(1, 8, 6, 3)  # [B,H,W,C] in 0..1
node2 = PSN_Tripo_Image_Request_Builder()
(req,) = node2.run(image=img, texture=False)
d = json.loads(req)
assert d["type"] == "image_to_model" and d["texture"] is False
assert set(d) == {"type", "texture", "image_png_base64"}
px = decode_png(d["image_png_base64"])
assert px.shape == (8, 6, 3)
assert torch.equal(px, (img[0] * 255.0).round().to(torch.uint8))

# 7. Different image gives different request; same image the same request
(req_same,) = node2.run(image=img, texture=False)
assert req_same == req
(req_diff,) = node2.run(image=torch.rand(1, 8, 6, 3), texture=False)
assert req_diff != req

# 8. Image validation errors
for bad, exc in ((torch.rand(4, 4, 3), ValueError), (torch.rand(1, 4, 4, 5), ValueError),
                 (torch.rand(1, 4, 4, 3) * 2.0, ValueError), ("not a tensor", TypeError)):
    try:
        _validate_image(bad)
        assert False, "should have raised"
    except exc:
        pass
try:
    node2.run(image=img, texture="yes")
    assert False, "should have raised"
except TypeError:
    pass

# 9. 1-channel and 4-channel images are expanded / stripped to RGB
g = torch.rand(1, 4, 4, 1)
pg = decode_png(_image_to_base64_png(g))
assert torch.equal(pg[..., 0], pg[..., 2]) and torch.equal(pg[..., 0], (g[0, ..., 0] * 255).round().to(torch.uint8))
a = torch.rand(1, 4, 4, 4)
pa = decode_png(_image_to_base64_png(a))
assert torch.equal(pa, (a[0, ..., :3] * 255).round().to(torch.uint8))

# 10. Batch > 1 uses the first frame
batch = torch.rand(3, 4, 4, 3)
(rb,) = node2.run(image=batch, texture=True)
assert torch.equal(decode_png(json.loads(rb)["image_png_base64"]), (batch[0] * 255).round().to(torch.uint8))

# 11. RETURN_TYPES / NAMES / FUNCTION / CATEGORY / DESCRIPTION
for cls in (PSN_Tripo_Text_Request_Builder, PSN_Tripo_Image_Request_Builder):
    assert cls.RETURN_TYPES == ("STRING",)
    assert cls.RETURN_NAMES == ("request_json",)
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY == "ParametricStudio/3D"
    assert "Calls no API" in cls.DESCRIPTION or "calls no API" in cls.DESCRIPTION

print('ok')
