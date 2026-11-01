"""ParametricStudio - prompt style template (offline, torch/stdlib only).

Rewrites a user prompt with fixed rules: it strips a list of filler words and
appends a style profile's fixed quality tokens and default negative prompt
(optionally weighted).  No LLM or other model is involved, nothing is
generated or rephrased, and there is no network access.
"""

import re
import torch

CAT = "ParametricStudio/LLM"

# ---------------------------------------------------------------------------
# Style profiles: what each target model likes in a prompt.
# ---------------------------------------------------------------------------
STYLE_PROFILES = {
    "generic": {
        "prefix": "",
        "suffix": "",
        "quality": ["high quality", "detailed"],
        "negative": "blurry, low quality, distorted, watermark",
        "weight": 1.0,
    },
    "sd15": {
        "prefix": "masterpiece, best quality,",
        "suffix": "",
        "quality": ["highres", "sharp focus"],
        "negative": "lowres, bad anatomy, bad hands, blurry, watermark, text",
        "weight": 1.0,
    },
    "sdxl": {
        "prefix": "",
        "suffix": "",
        "quality": ["cinematic lighting", "8k uhd", "sharp focus"],
        "negative": "lowres, cropped, worst quality, jpeg artifacts, watermark",
        "weight": 1.0,
    },
    "anime": {
        "prefix": "",
        "suffix": "",
        "quality": ["vibrant colors", "clean lineart", "detailed eyes"],
        "negative": "photorealistic, 3d render, blurry, extra limbs",
        "weight": 1.0,
    },
    "photo": {
        "prefix": "",
        "suffix": "",
        "quality": ["photorealistic", "85mm lens", "natural lighting", "high dynamic range"],
        "negative": "cartoon, anime, painting, oversaturated, plastic skin",
        "weight": 1.0,
    },
}

# Words that should be dropped from the user prompt (filler / meta words).
_DROP_WORDS = {
    "please", "can", "you", "could", "would", "like", "to", "the",
    "make", "create", "generate", "draw", "render", "image", "picture",
    "of", "in", "with", "and", "for", "me", "i", "want",
}


def _clean(text):
    """Normalize whitespace and strip meta/filler words from a prompt."""
    if not isinstance(text, str):
        raise TypeError("prompt must be a string")
    text = re.sub(r"\s+", " ", text).strip()
    tokens = text.split(" ")
    kept = []
    for tok in tokens:
        low = tok.lower().strip(",.!?;:")
        if low in _DROP_WORDS:
            continue
        kept.append(tok)
    out = " ".join(kept).strip()
    # collapse doubled punctuation left behind by dropped words
    out = re.sub(r"\s+([,\.!?;:])", r"\1", out)
    out = re.sub(r"^\s*[,\.!?;:]+", "", out)
    out = re.sub(r"[,\.!?;:]\s*$", "", out)
    return out.strip()


def _weight_tokens(quality, weight):
    """Wrap quality tokens in (token:weight) syntax when weight != 1.0."""
    if abs(weight - 1.0) < 1e-9:
        return list(quality)
    return ["(%s:%.2f)" % (q, weight) for q in quality]


def apply_style_template(prompt, style="generic", weight=1.0, add_negative=True):
    """Strip filler words and append a style profile's fixed tokens (no model involved).

    Returns dict with keys: prompt, negative, style, changed.
    """
    if style not in STYLE_PROFILES:
        raise ValueError("unknown style: %r" % (style,))
    try:
        weight = float(weight)
    except (TypeError, ValueError):
        raise TypeError("weight must be a number")
    if not (0.0 <= weight <= 3.0):
        raise ValueError("weight out of range [0, 3]")

    prof = STYLE_PROFILES[style]
    core = _clean(prompt)
    if not core:
        core = "abstract composition"

    parts = []
    if prof["prefix"]:
        parts.append(prof["prefix"])
    parts.append(core)
    parts.extend(_weight_tokens(prof["quality"], weight))
    if prof["suffix"]:
        parts.append(prof["suffix"])

    final = ", ".join(p for p in parts if p)
    final = re.sub(r"\s*,\s*", ", ", final).strip(", ")

    negative = prof["negative"] if add_negative else ""
    return {
        "prompt": final,
        "negative": negative,
        "style": style,
        "changed": final != prompt,
    }


def _s(x):
    """Validate a tensor and return it (never mutate)."""
    if not torch.is_tensor(x):
        raise TypeError("expected a torch tensor")
    return x


class PSN_PromptStyleTemplate:
    """Strip filler words and append a style profile's fixed tokens and default negative.

    Applies a style profile (quality tokens, weighting, negative prompt) to the
    raw user prompt.  No LLM is involved.
    """

    DESCRIPTION = (
        "Strips filler words and appends a style profile's fixed quality tokens and default "
        "negative prompt. No LLM involved: nothing is rewritten beyond that."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "a cat", "multiline": True}),
                "style": (sorted(STYLE_PROFILES.keys()), {"default": "generic"}),
                "weight": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.05}),
                "add_negative": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("prompt", "negative", "changed")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt, style, weight, add_negative):
        res = apply_style_template(prompt, style=style, weight=weight, add_negative=add_negative)
        return (res["prompt"], res["negative"], 1 if res["changed"] else 0)


NODE_CLASS_MAPPINGS = {
    "PSN_PromptStyleTemplate": PSN_PromptStyleTemplate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PromptStyleTemplate": "Prompt Style Template (filler words stripped, fixed tokens added, no LLM)",
}
