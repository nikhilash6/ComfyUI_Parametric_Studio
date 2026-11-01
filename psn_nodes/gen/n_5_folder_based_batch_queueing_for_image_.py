"""PSN_Folder_Batch_Queue: queue image files from a manifest for batch processing.

The node does not scan a folder. It operates on an in-memory manifest: a list
of dicts describing files ({"name": str, "mtime": float, "data": bytes}) where
"data" holds the encoded image file bytes (PNG, JPEG, ...). It filters by name
pattern, sorts, limits the count and decodes each file's bytes into an IMAGE
tensor with PIL. Bytes that are not a decodable image raise ValueError.
"""

import io
import random

import numpy as np
import torch
from PIL import Image

CAT = "ParametricStudio/Batch"

_IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")


def _matches_pattern(name: str, pattern: str) -> bool:
    """Minimal glob match supporting '*' and '?' (no os.path needed)."""
    import re

    pat = "^"
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            pat += ".*"
        elif c == "?":
            pat += "."
        else:
            pat += re.escape(c)
        i += 1
    pat += "$"
    return re.match(pat, name) is not None


def _bytes_to_image(data: bytes, name: str) -> torch.Tensor:
    """Decode encoded image bytes into a [1,H,W,3] float32 tensor in 0..1.

    Raises ValueError if the bytes are not a decodable image.
    """
    try:
        with Image.open(io.BytesIO(data)) as im:
            rgb = im.convert("RGB")
            arr = np.asarray(rgb, dtype=np.float32) / 255.0
    except (OSError, ValueError, SyntaxError) as exc:
        raise ValueError(f"cannot decode image bytes for {name!r}: {exc}")
    return torch.from_numpy(arr).unsqueeze(0).contiguous()


def _sort_manifest(manifest: list, sort_order: str) -> list:
    """Return a NEW sorted list (never mutate the input)."""
    if sort_order == "name":
        return sorted(manifest, key=lambda m: m.get("name", ""))
    if sort_order == "date":
        return sorted(manifest, key=lambda m: m.get("mtime", 0.0))
    if sort_order == "random":
        out = list(manifest)
        random.Random(12345).shuffle(out)  # deterministic for tests
        return out
    raise ValueError(f"unknown sort_order: {sort_order!r}")


class PSN_Folder_Batch_Queue:
    """Queue image files (manifest) for batch processing: filter, sort, limit, decode."""

    DESCRIPTION = ("Filters, sorts and limits a manifest of image files and "
                   "decodes each file's bytes into an IMAGE. It does not scan "
                   "a folder; the manifest is supplied by the caller.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "manifest": ("LIST[FILE_INFO]",),
                "sort_order": (["name", "date", "random"], {"default": "name"}),
            },
            "optional": {
                "file_pattern": ("STRING", {"default": "*"}),
                "max_files": ("INT", {"default": 0, "min": 0, "max": 100000}),
            },
        }

    RETURN_TYPES = ("LIST[IMAGE]", "LIST[STRING]", "INT")
    RETURN_NAMES = ("images", "file_paths", "count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, manifest, sort_order, file_pattern="*", max_files=0):
        if not isinstance(manifest, (list, tuple)):
            raise TypeError("manifest must be a list of file-info dicts")
        if sort_order not in ("name", "date", "random"):
            raise ValueError(f"sort_order must be name/date/random, got {sort_order!r}")

        # filter by pattern (match on basename)
        filtered = []
        for m in manifest:
            if not isinstance(m, dict):
                raise TypeError("each manifest entry must be a dict")
            name = m.get("name", "")
            if not isinstance(name, str) or not name:
                raise ValueError("manifest entry missing valid 'name'")
            if file_pattern and file_pattern != "*" and not _matches_pattern(name, file_pattern):
                continue
            filtered.append(m)

        ordered = _sort_manifest(filtered, sort_order)

        if max_files and max_files > 0:
            ordered = ordered[:max_files]

        images = []
        paths = []
        for m in ordered:
            data = m.get("data", b"")
            if not isinstance(data, (bytes, bytearray)):
                raise TypeError("manifest entry 'data' must be bytes")
            img = _bytes_to_image(bytes(data), m["name"])
            images.append(img)
            paths.append(m["name"])

        return (images, paths, len(images))


NODE_CLASS_MAPPINGS = {
    "PSN_Folder_Batch_Queue": PSN_Folder_Batch_Queue,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Folder_Batch_Queue": "Folder Batch Queue (Images)",
}
