"""ParametricStudio - Luminance / Saturation Mask for Inpainting.

This module provides a ComfyUI custom node that makes a binary mask by
thresholding a simple per-pixel colour score. It is NOT semantic segmentation:
it recognises no objects and loads no model. ``rule_id`` picks one of four
formulas:

  0 = deviation of luminance from the image median (scaled by its 95th percentile)
  1 = luminance (bright pixels)
  2 = inverted luminance (dark pixels)
  3 = max-min channel spread (saturated / colourful pixels)

The score is thresholded to a binary mask, with optional erosion then dilation
(max/min pooling) to remove specks. Everything runs on CPU with torch.
"""

import torch

CAT = "ParametricStudio/SemanticMasking"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _as_image(image):
    """Validate and return a float tensor [B,H,W,C] in 0..1 (cloned)."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError(f"image must be 4-D [B,H,W,C], got {image.dim()}-D")
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError(f"image channels must be 1, 3 or 4, got {image.shape[-1]}")
    x = image.float().clone()
    # Clamp to 0..1 (ComfyUI images are already in this range, but be safe).
    x = x.clamp(0.0, 1.0)
    return x


def _as_mask(mask):
    """Validate and return a float tensor [B,H,W] in 0..1 (cloned)."""
    if not isinstance(mask, torch.Tensor):
        raise TypeError("mask must be a torch.Tensor")
    if mask.dim() != 3:
        raise ValueError(f"mask must be 3-D [B,H,W], got {mask.dim()}-D")
    x = mask.float().clone().clamp(0.0, 1.0)
    return x


def _to_image(mask):
    """Convert a [B,H,W] mask to a [B,H,W,1] IMAGE tensor."""
    return mask.unsqueeze(-1)


# ---------------------------------------------------------------------------
# Core segmentation heuristic
# ---------------------------------------------------------------------------

def _foreground_score(image, class_id):
    """Compute a per-pixel luminance/saturation score in 0..1 (no object recognition).

    Parameters
    ----------
    image : Tensor [B,H,W,C]  (C in {1,3,4}), values 0..1
    class_id : int
        0 – generic foreground (luminance deviation from median)
        1 – bright objects   (high luminance)
        2 – dark objects     (low luminance)
        3 – saturated / colourful objects (high colour saturation)

    Returns
    -------
    Tensor [B,H,W] in 0..1
    """
    x = image
    # Work with RGB (drop alpha if present).
    if x.shape[-1] == 4:
        x = x[..., :3]
    if x.shape[-1] == 1:
        x = x.expand(-1, -1, -1, 3)

    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b  # [B,H,W]

    if class_id == 1:
        # Bright objects: score = luminance itself.
        score = lum
    elif class_id == 2:
        # Dark objects: score = 1 - luminance.
        score = 1.0 - lum
    elif class_id == 3:
        # Saturated / colourful: use max-min channel spread as a saturation
        # proxy, normalised.
        cmax = x.max(dim=-1).values
        cmin = x.min(dim=-1).values
        score = (cmax - cmin)  # 0..1 already
    else:
        # class_id == 0 (default): deviation from the per-image median
        # luminance, normalised to 0..1.
        med = lum.median(dim=1, keepdim=True).values.median(dim=2, keepdim=True).values
        # med is [B,1,1]
        dev = (lum - med).abs()  # [B,H,W]
        # Normalise by the 95th percentile of the deviation (robust).
        p95 = torch.quantile(dev.reshape(dev.shape[0], -1), 0.95, dim=1, keepdim=True).unsqueeze(-1)
        p95 = p95.clamp_min(1e-6)
        score = (dev / p95).clamp(0.0, 1.0)

    return score.clamp(0.0, 1.0)


def _morphology(mask, op, radius):
    """Simple binary morphology via max/min pooling.

    Parameters
    ----------
    mask : Tensor [B,H,W]  (0/1 or 0..1)
    op : str  'erode' or 'dilate'
    radius : int  (kernel half-size; kernel = (2*radius+1)^2)

    Returns
    -------
    Tensor [B,H,W]
    """
    if radius <= 0:
        return mask
    k = 2 * radius + 1
    if op == "erode":
        # Erosion = min-pooling.
        out = torch.nn.functional.max_pool2d(
            1.0 - mask.unsqueeze(1), kernel_size=k, stride=1, padding=radius
        ).squeeze(1)
        return (1.0 - out).clamp(0.0, 1.0)
    else:  # dilate
        out = torch.nn.functional.max_pool2d(
            mask.unsqueeze(1), kernel_size=k, stride=1, padding=radius
        ).squeeze(1)
        return out.clamp(0.0, 1.0)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_LuminanceSaturationMask:
    """Threshold a luminance or saturation score into a binary mask.

    No semantic segmentation: it does not know what any object is. ``rule_id``
    only selects the colour formula.

    Inputs
    ------
    image : IMAGE  [B,H,W,C] float 0..1
    rule_id : INT  0=luminance deviation from median, 1=bright, 2=dark, 3=saturated
    score_threshold : FLOAT  0..1  (pixels scoring below this are background)
    morphology_radius : INT  0..16  (0 = no cleanup; >0 = erode+dilate)

    Outputs
    -------
    mask : MASK  [B,H,W]  binary 0/1
    score_map : IMAGE  [B,H,W,1]  float 0..1 (the pre-threshold score)
    """

    DESCRIPTION = ("Thresholds image luminance or saturation into a binary "
                   "mask, with optional erode/dilate cleanup. It does no "
                   "semantic segmentation and recognises no objects.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "rule_id": ("INT", {"default": 0, "min": 0, "max": 3}),
                "score_threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "morphology_radius": ("INT", {"default": 0, "min": 0, "max": 16}),
            }
        }

    RETURN_TYPES = ("MASK", "IMAGE")
    RETURN_NAMES = ("mask", "score_map")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, rule_id, score_threshold, morphology_radius):
        img = _as_image(image)
        if not (0.0 <= score_threshold <= 1.0):
            raise ValueError("score_threshold must be in [0, 1]")
        if rule_id not in (0, 1, 2, 3):
            raise ValueError(f"rule_id must be 0..3, got {rule_id}")

        # 1. Per-pixel score.
        score = _foreground_score(img, rule_id)  # [B,H,W] 0..1

        # 2. Threshold -> binary mask.
        mask = (score >= score_threshold).float()  # [B,H,W] 0/1

        # 3. Optional morphological cleanup (erode then dilate = opening).
        if morphology_radius > 0:
            mask = _morphology(mask, "erode", morphology_radius)
            mask = _morphology(mask, "dilate", morphology_radius)

        # 4. Score map as a single-channel IMAGE.
        score_map = _to_image(score)  # [B,H,W,1]

        return (mask, score_map)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_LuminanceSaturationMask": PSN_LuminanceSaturationMask,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LuminanceSaturationMask": "PSN Luminance / Saturation Mask (Inpainting)",
}
