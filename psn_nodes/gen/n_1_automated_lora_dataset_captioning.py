"""ParametricStudio: Image-statistics captions and caption auditing.

* PSN_Image_Stats_Caption: computes mean brightness, contrast and the
  dominant RGB tone of the IMAGE tensor and fills a fixed caption template
  with them.  No vision-language model runs: the caption only says how bright,
  how contrasty and which tone the image is, never what is in it.

* PSN_Caption_Auditor: validates a caption against banned/allowed term lists
  using plain string matching.
"""

import torch

CAT = "ParametricStudio/LLM Captioning"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_image_tensor(image):
    """Validate and return a float torch tensor of shape [B,H,W,C] in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError("image must have shape [B, H, W, C], got %s" % (tuple(image.shape),))
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError("image channel count must be 1, 3 or 4, got %d" % image.shape[-1])
    if not torch.is_floating_point(image):
        raise TypeError("image must be a floating point tensor")
    if image.numel() == 0:
        raise ValueError("image tensor is empty")
    return image


def _image_stats(image):
    """Compute deterministic, cheap image statistics on CPU."""
    img = image.detach().to(torch.float32).cpu()
    rgb = img[..., :3]
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    mean_brightness = float(lum.mean().item())
    contrast = float(lum.std().item()) if lum.numel() > 1 else 0.0

    r = float(rgb[..., 0].mean().item())
    g = float(rgb[..., 1].mean().item())
    b = float(rgb[..., 2].mean().item())
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx - mn < 0.05:
        dominant_hue = "neutral"
    elif mx == r:
        dominant_hue = "red"
    elif mx == g:
        dominant_hue = "green"
    else:
        dominant_hue = "blue"

    return {
        "mean_brightness": mean_brightness,
        "contrast": contrast,
        "dominant_hue": dominant_hue,
        "width": int(image.shape[2]),
        "height": int(image.shape[1]),
        "batch": int(image.shape[0]),
    }


def _brightness_word(v):
    if v < 0.25:
        return "dark"
    if v < 0.5:
        return "dim"
    if v < 0.75:
        return "bright"
    return "very bright"


def _contrast_word(v):
    if v < 0.08:
        return "low contrast"
    if v < 0.2:
        return "medium contrast"
    return "high contrast"


def _template_caption(stats, caption_style):
    """Caption template filled from image statistics."""
    bright = _brightness_word(stats["mean_brightness"])
    contrast = _contrast_word(stats["contrast"])
    hue = stats["dominant_hue"]
    size = "%dx%d" % (stats["width"], stats["height"])

    if caption_style == "booru_tags":
        tags = ["image", size, bright.replace(" ", "_"), contrast.replace(" ", "_")]
        if hue != "neutral":
            tags.append(hue + "_tone")
        return ", ".join(tags)

    if caption_style == "concise":
        return "A %s image with %s, %s tones." % (bright, contrast, hue)

    if caption_style == "natural_language":
        return (
            "This is a %s image (%s) with %s and %s color tones." % (
                bright, size, contrast, hue
            )
        )

    return (
        "A %s image of size %s. The overall lighting is %s with %s. "
        "The dominant color tone is %s." % (
            bright, size, bright, contrast, hue
        )
    )


# ---------------------------------------------------------------------------
# Node 1: PSN_Image_Stats_Caption
# ---------------------------------------------------------------------------


class PSN_Image_Stats_Caption:
    """Write a template caption from mean brightness, contrast and dominant
    RGB tone.

    No VLM or other model is run, so the caption never describes the image
    content.  Statistics are taken over the whole batch.
    """

    DESCRIPTION = (
        "Writes a template caption from the image's mean brightness, contrast "
        "and dominant RGB tone. No vision-language model runs, so it does not "
        "describe what is in the image."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "caption_style": (
                    ["detailed", "concise", "booru_tags", "natural_language"],
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("caption",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, caption_style):
        img = _as_image_tensor(image)
        stats = _image_stats(img)
        return (_template_caption(stats, caption_style),)


# ---------------------------------------------------------------------------
# Node 2: PSN_Caption_Auditor
# ---------------------------------------------------------------------------


def _split_terms(s):
    if not s:
        return []
    return [t.strip().lower() for t in str(s).split(",") if t.strip()]


class PSN_Caption_Auditor:
    """Validate a caption against banned and allowed term lists.

    * ``banned_terms``: comma-separated list; if any appear (case-insensitive
      substring match) the caption is invalid.
    * ``allowed_terms``: comma-separated list; if non-empty, at least one of
      these terms must appear in the caption for it to be valid.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "caption": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "allowed_terms": ("STRING", {"default": "", "multiline": True}),
                "banned_terms": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("is_valid", "correction_suggestion")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, caption, allowed_terms="", banned_terms=""):
        if caption is None:
            caption = ""
        text = str(caption)
        low = text.lower()

        banned = _split_terms(banned_terms)
        allowed = _split_terms(allowed_terms)

        problems = []

        found_banned = []
        for term in banned:
            if term and term in low:
                found_banned.append(term)
        if found_banned:
            problems.append("banned terms present: %s" % ", ".join(found_banned))

        if allowed:
            present = [t for t in allowed if t in low]
            if not present:
                problems.append(
                    "none of the allowed terms present: %s" % ", ".join(allowed)
                )

        if not text.strip():
            problems.append("caption is empty")

        is_valid = len(problems) == 0

        if is_valid:
            suggestion = ""
        else:
            parts = []
            for term in found_banned:
                parts.append("remove '%s'" % term)
            if allowed and not any(t in low for t in allowed):
                parts.append("include at least one of: %s" % ", ".join(allowed))
            if not text.strip():
                parts.append("provide a non-empty caption")
            suggestion = "; ".join(parts) if parts else "; ".join(problems)

        return (is_valid, suggestion)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Image_Stats_Caption": PSN_Image_Stats_Caption,
    "PSN_Caption_Auditor": PSN_Caption_Auditor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Image_Stats_Caption": "Image Stats Caption (no VLM)",
    "PSN_Caption_Auditor": "Caption Auditor",
}
