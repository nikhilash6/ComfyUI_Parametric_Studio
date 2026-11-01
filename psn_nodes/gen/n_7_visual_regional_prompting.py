"""
PSN Visual Regional Prompting (pure-logic, secure-by-design).

This module implements the *logic* of visual regional prompting without any
GPU/torch/PIL/ComfyUI/network/file access. It works on plain values:
bounding boxes (ints), region dictionaries (JSON-able), and prompt strings.

It provides:
  - PSN_RegionalMask: builds a normalized region mask (as a list of row strings)
    from a bounding box and image dimensions, with clamping and validation.
  - PSN_RegionalPrompt_Plan: validates a regions dictionary and emits a JSON
    plan listing each region's box and prompt, with the requested strength
    split evenly across regions. It applies no attention masks and does not
    touch a model or conditioning.

All functions take plain values (numbers, strings, dicts) and return plain
values (numbers, strings, lists, dicts). No sockets, no file I/O, no eval.
"""

import json
import math

CAT = "ParametricStudio/Regional"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value, lo, hi):
    """Clamp value into [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _validate_bbox(bbox, width, height):
    """
    Validate and clamp a bounding box (x, y, w, h) to image bounds.
    Returns (x, y, w, h) as ints, or raises ValueError.
    """
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise ValueError("bbox must be a list/tuple of 4 ints: [x, y, w, h]")
    x, y, w, h = bbox
    for v in (x, y, w, h):
        if not isinstance(v, (int, float)):
            raise ValueError("bbox components must be numeric")
    x, y, w, h = int(x), int(y), int(w), int(h)
    if w <= 0 or h <= 0:
        raise ValueError("bbox width and height must be positive")
    # Clamp to image bounds
    x = _clamp(x, 0, width - 1)
    y = _clamp(y, 0, height - 1)
    w = _clamp(w, 1, width - x)
    h = _clamp(h, 1, height - y)
    return (x, y, w, h)


def _build_mask_rows(bbox, width, height):
    """
    Build a mask as a list of strings, one per row of the image.
    Each string is '0'/'1' per pixel column: '1' inside the bbox, '0' outside.
    This is a pure-logic representation of a binary mask.
    """
    x, y, w, h = bbox
    rows = []
    for row in range(height):
        chars = []
        for col in range(width):
            if y <= row < y + h and x <= col < x + w:
                chars.append('1')
            else:
                chars.append('0')
        rows.append(''.join(chars))
    return rows


def _validate_regions(regions, width, height):
    """
    Validate a regions dict. Expected format:
    {
        "region_name": {"bbox": [x, y, w, h], "prompt": "some prompt"},
        ...
    }
    Returns a list of validated region entries.
    """
    if not isinstance(regions, dict):
        raise ValueError("regions must be a dict")
    entries = []
    for name, spec in regions.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("region names must be non-empty strings")
        if not isinstance(spec, dict):
            raise ValueError("each region spec must be a dict")
        if "bbox" not in spec:
            raise ValueError(f"region '{name}' missing 'bbox'")
        if "prompt" not in spec:
            raise ValueError(f"region '{name}' missing 'prompt'")
        prompt = spec["prompt"]
        if not isinstance(prompt, str):
            raise ValueError(f"region '{name}' prompt must be a string")
        bbox = _validate_bbox(spec["bbox"], width, height)
        entries.append({
            "name": name,
            "bbox": bbox,
            "prompt": prompt,
        })
    return entries


def _split_strength(entries, attention_strength):
    """
    Split the requested strength evenly: each region gets
    attention_strength / num_regions. A number in the plan only.
    """
    n = len(entries)
    if n == 0:
        return []
    weight = attention_strength / n
    return [weight] * n


# ---------------------------------------------------------------------------
# Node: PSN_RegionalMask
# ---------------------------------------------------------------------------

class PSN_RegionalMask:
    """
    Creates a binary mask for a specific region of the image.

    Inputs:
      - image (IMAGE): Base image (represented as width/height ints in this
        pure-logic implementation; in ComfyUI this would be a tensor).
      - bbox (INT list): Bounding box [x, y, w, h].

    Outputs:
      - mask (MASK): A list of strings representing the binary mask
        (one string per row, '1' inside region, '0' outside).
      - mask_info (STRING): JSON summary of the mask region.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_width": ("INT", {"default": 512, "min": 1, "max": 8192, "step": 1}),
                "image_height": ("INT", {"default": 512, "min": 1, "max": 8192, "step": 1}),
                "bbox": ("STRING", {"default": "[0, 0, 256, 256]", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("mask", "mask_info")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image_width, image_height, bbox):
        # Parse bbox from JSON string
        try:
            bbox_list = json.loads(bbox)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("bbox must be valid JSON list of 4 ints")
        bbox_tuple = _validate_bbox(bbox_list, image_width, image_height)
        mask_rows = _build_mask_rows(bbox_tuple, image_width, image_height)
        mask_info = json.dumps({
            "bbox": list(bbox_tuple),
            "width": image_width,
            "height": image_height,
            "mask_rows": len(mask_rows),
        })
        return (json.dumps(mask_rows), mask_info)


# ---------------------------------------------------------------------------
# Node: PSN_RegionalPrompt
# ---------------------------------------------------------------------------

class PSN_RegionalPrompt_Plan:
    """
    Validates regions (box + prompt per region) and emits a JSON plan.
    Applies no attention masks and changes no conditioning; the plan is text
    for other tooling to use.

    Inputs:
      - image_width (INT): Width of the base image.
      - image_height (INT): Height of the base image.
      - regions (STRING): JSON dict of regions with bboxes and prompts.
      - attention_strength (FLOAT): Strength, split evenly across regions.

    Outputs:
      - regional_plan (STRING): JSON plan (boxes clamped to the image, prompts,
        and each region's even share of the strength).
      - total_regions (INT): Number of regions.
      - status (STRING): "regions valid" or an error message.
    """

    DESCRIPTION = ("Validates regions (box + prompt) and emits a JSON plan with "
                   "the strength split evenly across regions. Applies no "
                   "attention masks and changes no conditioning.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_width": ("INT", {"default": 512, "min": 1, "max": 8192, "step": 1}),
                "image_height": ("INT", {"default": 512, "min": 1, "max": 8192, "step": 1}),
                "regions": ("STRING", {"default": "{}", "multiline": True}),
                "attention_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("regional_plan", "total_regions", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image_width, image_height, regions, attention_strength):
        try:
            regions_dict = json.loads(regions)
        except (json.JSONDecodeError, TypeError):
            return ("", 0, "error: regions must be valid JSON")

        try:
            entries = _validate_regions(regions_dict, image_width, image_height)
        except ValueError as e:
            return ("", 0, f"error: {e}")

        weights = _split_strength(entries, attention_strength)

        plan = {
            "image_width": image_width,
            "image_height": image_height,
            "attention_strength": attention_strength,
            "regions": [],
        }
        for entry, weight in zip(entries, weights):
            plan["regions"].append({
                "name": entry["name"],
                "bbox": list(entry["bbox"]),
                "prompt": entry["prompt"],
                "strength_share": round(weight, 6),
            })

        plan_json = json.dumps(plan, indent=2)
        return (plan_json, len(entries), "regions valid")


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_RegionalMask": PSN_RegionalMask,
    "PSN_RegionalPrompt_Plan": PSN_RegionalPrompt_Plan,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_RegionalMask": "PSN Regional Mask",
    "PSN_RegionalPrompt_Plan": "PSN Regional Prompt Plan (JSON)",
}
