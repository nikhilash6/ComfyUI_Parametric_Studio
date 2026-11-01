"""PSN_VisualModelSelector: backend for a visual model selection UI.

Given a model list (as produced by a registry loader), this node assembles
"model cards" containing a display name, a cover image path and a metadata
dict. The cover path is the first of cover.jpg / preview.png that exists as a
file inside the model's directory (checked with os.path.isfile); when the
directory is missing or has neither file, the path is the empty string.

The node is pure Python + stdlib and does not touch the network. `model_list`
is a plain list of dicts (or names).
"""

import json
import os

CAT = "ParametricStudio/ModelSelection"

# Candidate cover file names, in priority order.
COVER_CANDIDATES = ("cover.jpg", "preview.png")


def _is_dict(value):
    return isinstance(value, dict)


def _clean_name(value, fallback="unnamed-model"):
    """Return a safe, non-empty display name."""
    if isinstance(value, str):
        value = value.strip()
        if value:
            return value
    return fallback


def _clean_metadata(value):
    """Coerce arbitrary metadata into a JSON-serialisable dict."""
    if _is_dict(value):
        out = {}
        for k, v in value.items():
            key = str(k)
            try:
                json.dumps(v)
            except (TypeError, ValueError):
                v = repr(v)
            out[key] = v
        return out
    if value is None:
        return {}
    return {"raw": repr(value)}


def _find_cover(model_dir):
    """Return the path of the first cover candidate that exists as a file
    inside `model_dir`, else None (also None for a blank or non-string dir)."""
    if not isinstance(model_dir, str) or not model_dir.strip():
        return None
    for cand in COVER_CANDIDATES:
        path = os.path.join(model_dir, cand)
        if os.path.isfile(path):
            return path
    return None


def _build_card(entry, index):
    """Build a single model card dict from a registry entry.

    `entry` may be a dict with keys like name / dir / metadata, or a plain
    string (treated as the model name with no directory).
    """
    if isinstance(entry, str):
        name = _clean_name(entry, "model-%d" % index)
        model_dir = None
        metadata = {}
    elif _is_dict(entry):
        name = _clean_name(entry.get("name"), "model-%d" % index)
        model_dir = entry.get("dir") or entry.get("directory") or entry.get("path")
        metadata = _clean_metadata(entry.get("metadata"))
    else:
        name = "model-%d" % index
        model_dir = None
        metadata = {"raw": repr(entry)}

    cover = _find_cover(model_dir) or ""

    return {
        "name": name,
        "cover_image_path": cover,
        "metadata": metadata,
    }


class PSN_VisualModelSelector:
    """Assemble model cards (name, cover image path, metadata) for a UI."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # In a full ComfyUI install this would be ("MODEL_LIST",) from
                # PSN_ModelRegistryLoader.  We accept a generic CUSTOM type so
                # the node can be wired up once the loader exists.
                "model_list": ("MODEL_LIST",),
                "limit": ("INT", {"default": 10, "min": 1, "max": 1024}),
            }
        }

    RETURN_TYPES = ("MODEL_CARDS",)
    RETURN_NAMES = ("model_cards",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_list, limit):
        if model_list is None:
            model_list = []
        if not isinstance(model_list, (list, tuple)):
            raise TypeError("model_list must be a list or tuple of entries")
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise TypeError("limit must be an int")
        if limit < 1:
            raise ValueError("limit must be >= 1")

        cards = []
        for i, entry in enumerate(model_list):
            if i >= limit:
                break
            cards.append(_build_card(entry, i))
        return (cards,)


NODE_CLASS_MAPPINGS = {
    "PSN_VisualModelSelector": PSN_VisualModelSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VisualModelSelector": "Visual Model Selector (UI Backend)",
}
