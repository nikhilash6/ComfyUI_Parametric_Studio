"""ParametricStudio - Tripo 3D request builders (offline, no API call).

These nodes only build request JSON text. They call no API, take no API key,
upload nothing, and return no model, URL or job id.

* PSN_Tripo_Text_Request_Builder  - validates a prompt and the texture / pbr
  flags and returns request JSON for a text-to-model task.
* PSN_Tripo_Image_Request_Builder - validates an IMAGE, encodes the first
  frame as a real PNG (base64) and returns request JSON for an image-to-model
  task.

The field names ("type", "prompt", "texture", "pbr", "image_png_base64") are
this module's own request shape and have not been checked against the live
Tripo API. A later step must add the key, send the request and poll the task.
"""

import base64
import json
import struct
import zlib

import torch

CAT = "ParametricStudio/3D"


def _validate_image(image):
    """Validate an IMAGE tensor: [B,H,W,C] float in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError(f"image must be 4-D [B,H,W,C], got {image.dim()}-D")
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError(f"image channels must be 1, 3 or 4, got {image.shape[-1]}")
    if not (image.dtype == torch.float32 or image.dtype == torch.float16 or image.dtype == torch.float64):
        raise TypeError(f"image must be a float tensor, got {image.dtype}")
    if image.numel() > 0:
        if image.min() < -1e-6 or image.max() > 1 + 1e-6:
            raise ValueError("image values must be in [0, 1]")
    return image


def _png_chunk(tag, data):
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def _image_to_base64_png(image):
    """Encode the first image of an IMAGE tensor [B,H,W,C] as a real 8-bit RGB
    PNG, returned as a base64 string. Alpha is dropped, grey is expanded."""
    img = image[0].clamp(0.0, 1.0)
    if img.shape[-1] == 1:
        img = img.expand(-1, -1, 3)
    elif img.shape[-1] == 4:
        img = img[..., :3]
    u8 = (img * 255.0).round().to(torch.uint8).contiguous()
    h, w, _ = u8.shape
    rows = u8.reshape(h, w * 3).numpy()
    raw = b"".join(b"\x00" + rows[y].tobytes() for y in range(h))  # filter 0
    png = (b"\x89PNG\r\n\x1a\n"
           + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + _png_chunk(b"IDAT", zlib.compress(raw))
           + _png_chunk(b"IEND", b""))
    return base64.b64encode(png).decode("ascii")


class PSN_Tripo_Text_Request_Builder:
    """Build request JSON for a Tripo text-to-model task. Calls no API."""

    DESCRIPTION = ("Builds request JSON for a Tripo text-to-model task from the "
                   "prompt. Calls no API, takes no key, and returns no model "
                   "URL or job id.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "a red cube"}),
                "texture": ("BOOLEAN", {"default": True}),
                "pbr": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("request_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt, texture=True, pbr=True):
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if not isinstance(texture, bool):
            raise TypeError("texture must be a boolean")
        if not isinstance(pbr, bool):
            raise TypeError("pbr must be a boolean")

        request = {"type": "text_to_model", "prompt": prompt.strip(),
                   "texture": texture, "pbr": pbr}
        return (json.dumps(request),)


class PSN_Tripo_Image_Request_Builder:
    """Build request JSON for a Tripo image-to-model task. Calls no API."""

    DESCRIPTION = ("Builds request JSON for a Tripo image-to-model task, with "
                   "the first image frame encoded as a base64 PNG. Calls no "
                   "API, uploads nothing, and returns no model URL or job id.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "texture": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("request_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, texture=True):
        if not isinstance(texture, bool):
            raise TypeError("texture must be a boolean")

        img = _validate_image(image)
        request = {"type": "image_to_model", "texture": texture,
                   "image_png_base64": _image_to_base64_png(img)}
        return (json.dumps(request),)


NODE_CLASS_MAPPINGS = {
    "PSN_Tripo_Text_Request_Builder": PSN_Tripo_Text_Request_Builder,
    "PSN_Tripo_Image_Request_Builder": PSN_Tripo_Image_Request_Builder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Tripo_Text_Request_Builder": "Tripo Text-to-3D Request Builder",
    "PSN_Tripo_Image_Request_Builder": "Tripo Image-to-3D Request Builder",
}
