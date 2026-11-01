"""ParametricStudio - Band colour threshold masks (torch-only).

PSN_BandColorThresholdMask: a heuristic MASK made of a brightness / saturation
/ redness threshold applied inside a fixed horizontal band of the image
(rows counted from the top). It is not a feature detector: it does not find
hair, eyes, mouths or bodies, only pixels of a given colour inside a fixed
band, whatever the picture shows. No model, no learned weights.
"""

import torch

CAT = "ParametricStudio/AnimePose"


def _as_image(image):
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    x = image.detach().clone().float()
    if x.dim() != 4:
        raise ValueError("image must be [B,H,W,C], got %s" % (tuple(x.shape),))
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError("image channels must be 1, 3 or 4, got %d" % x.shape[-1])
    return x.clamp_(0.0, 1.0)


# rule name -> what it does (rows are counted from the top of the image)
_SEG_CLASSES = [
    "dark_unsaturated_top60",   # lum < 0.35 and saturation < 0.35, rows 0-60%
    "bright_top40",             # lum > 0.7, rows 0-40%
    "reddish_band_30_55",       # r - mean(g, b) > 0.05, rows 30-55%
    "midtone_below_30",         # 0.15 < lum < 0.85, rows 30-100%
]


def _mask_dark_unsaturated_top60(img):
    b, h, w, _ = img.shape
    rgb = img[..., :3]
    r, g, bch = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = (r + g + bch) / 3.0
    mx = torch.max(torch.max(r, g), bch)
    mn = torch.min(torch.min(r, g), bch)
    sat = torch.where(mx > 0, (mx - mn) / mx.clamp_min(1e-6), torch.zeros_like(mx))
    dark = (lum < 0.35).float()
    low_sat = (sat < 0.35).float()
    hair = dark * low_sat
    mask_top = torch.zeros_like(hair)
    cut = max(1, int(h * 0.6))
    mask_top[:, :cut, :] = 1.0
    return (hair * mask_top).clamp(0.0, 1.0)


def _mask_bright_top40(img):
    b, h, w, _ = img.shape
    rgb = img[..., :3]
    r, g, bch = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = (r + g + bch) / 3.0
    bright = (lum > 0.7).float()
    mask_top = torch.zeros_like(bright)
    cut = max(1, int(h * 0.4))
    mask_top[:, :cut, :] = 1.0
    return (bright * mask_top).clamp(0.0, 1.0)


def _mask_reddish_band_30_55(img):
    b, h, w, _ = img.shape
    rgb = img[..., :3]
    r, g, bch = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    redness = (r - (g + bch) / 2.0)
    mouth = (redness > 0.05).float()
    mask_band = torch.zeros_like(mouth)
    y0 = max(0, int(h * 0.3))
    y1 = min(h, int(h * 0.55))
    mask_band[:, y0:y1, :] = 1.0
    return (mouth * mask_band).clamp(0.0, 1.0)


def _mask_midtone_below_30(img):
    b, h, w, _ = img.shape
    rgb = img[..., :3]
    lum = rgb.mean(dim=-1)
    body = ((lum > 0.15) & (lum < 0.85)).float()
    mask_bot = torch.zeros_like(body)
    y0 = max(0, int(h * 0.3))
    mask_bot[:, y0:, :] = 1.0
    return (body * mask_bot).clamp(0.0, 1.0)


_SEG_FUNCS = {
    "dark_unsaturated_top60": _mask_dark_unsaturated_top60,
    "bright_top40": _mask_bright_top40,
    "reddish_band_30_55": _mask_reddish_band_30_55,
    "midtone_below_30": _mask_midtone_below_30,
}


class PSN_BandColorThresholdMask:
    """Mask of pixels passing a colour threshold inside a fixed row band.

    Pick one rule (see _SEG_CLASSES). Each rule is a brightness, saturation or
    redness threshold limited to a fixed vertical band of the image. It does
    not detect any feature; it only selects pixels by colour and row.
    """

    DESCRIPTION = ("Heuristic brightness/saturation/redness threshold inside "
                   "a fixed vertical band of the image. Not a feature "
                   "detector: it does not find hair, eyes, mouths or bodies.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "rule": (list(_SEG_CLASSES),),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, rule):
        img = _as_image(image)
        if rule not in _SEG_FUNCS:
            raise ValueError("unknown rule %r" % (rule,))
        return (_SEG_FUNCS[rule](img),)


NODE_CLASS_MAPPINGS = {
    "PSN_BandColorThresholdMask": PSN_BandColorThresholdMask,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_BandColorThresholdMask": "Band Colour Threshold Mask",
}
