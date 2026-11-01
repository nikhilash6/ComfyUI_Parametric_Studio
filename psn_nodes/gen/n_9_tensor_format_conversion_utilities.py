"""ParametricStudio tensor format conversion utilities.

Converts between ComfyUI IMAGE, LATENT and MASK formats.

Real ComfyUI types used here:
    IMAGE  : float torch tensor [B, H, W, C] in 0..1
    MASK   : float torch tensor [B, H, W] in 0..1
    LATENT : dict {"samples": float torch tensor [B, C, H, W]}

The VAE-dependent nodes (PSN_Image_To_Latent, PSN_Latent_To_Image,
PSN_Mask_To_Latent) take a ComfyUI VAE and call its ``encode`` (IMAGE
[B,H,W,C] -> latent tensor) and ``decode`` (latent tensor -> IMAGE) methods.
An object without the needed method raises TypeError; there is no fallback
conversion.
"""

import torch

CAT = "ParametricStudio/TensorFormat"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _s(x):
    """Return the raw tensor from a LATENT dict or a plain tensor."""
    if isinstance(x, dict):
        return x["samples"]
    return x


def _out(latent, samples):
    """Wrap a samples tensor in a LATENT dict, preserving other keys."""
    if isinstance(latent, dict):
        d = dict(latent)
        d["samples"] = samples
        return d
    return {"samples": samples}


def _as_image(image):
    """Validate / normalise an IMAGE tensor to [B,H,W,C] float in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    x = image.detach().clone().float()
    if x.dim() == 3:
        # [H, W, C] -> [1, H, W, C]
        x = x.unsqueeze(0)
    if x.dim() != 4:
        raise ValueError("image must have shape [B,H,W,C] (or [H,W,C])")
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError("image channel count must be 1, 3 or 4")
    return x


def _as_mask(mask):
    """Validate / normalise a MASK tensor to [B,H,W] float in 0..1."""
    if not isinstance(mask, torch.Tensor):
        raise TypeError("mask must be a torch.Tensor")
    x = mask.detach().clone().float()
    if x.dim() == 2:
        x = x.unsqueeze(0)
    if x.dim() != 3:
        raise ValueError("mask must have shape [B,H,W] (or [H,W])")
    return x


def _as_latent(latent):
    """Validate a LATENT dict and return its samples tensor."""
    if not isinstance(latent, dict) or "samples" not in latent:
        raise TypeError("latent must be a dict with a 'samples' key")
    x = latent["samples"]
    if not isinstance(x, torch.Tensor):
        raise TypeError("latent['samples'] must be a torch.Tensor")
    x = x.detach().clone().float()
    if x.dim() != 4:
        raise ValueError("latent samples must have shape [B,C,H,W]")
    return x


def _clamp01(x):
    return x.clamp_(0.0, 1.0)


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------


def _require(vae, method):
    """Raise unless *vae* has the given method (no substitute is used)."""
    if vae is None or not callable(getattr(vae, method, None)):
        raise TypeError("vae must be a VAE exposing .%s()" % method)
    return getattr(vae, method)


class PSN_Image_To_Latent:
    """Encode an IMAGE into LATENT space using a VAE."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "vae": ("VAE",),
            }
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, vae):
        img = _as_image(image)
        samples = _require(vae, "encode")(img)
        return ({"samples": samples},)


class PSN_Latent_To_Image:
    """Decode a LATENT into an IMAGE using a VAE."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
                "vae": ("VAE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, vae):
        lat = _as_latent(latent)
        img = _require(vae, "decode")(lat)
        return (img.clamp(0.0, 1.0),)


class PSN_Mask_To_Latent:
    """Convert a MASK into a LATENT representation for inpainting.

    The mask is first expanded to a 3-channel IMAGE, then encoded
    with the VAE.  The resulting latent can be fed into an inpainting
    sampler.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK",),
                "vae": ("VAE",),
            }
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, mask, vae):
        m = _as_mask(mask)
        # expand [B,H,W] -> [B,H,W,3] image (a real VAE encodes RGB)
        img = m.unsqueeze(-1).repeat(1, 1, 1, 3)
        samples = _require(vae, "encode")(img)
        return ({"samples": samples},)


class PSN_Latent_To_Mask:
    """Convert a LATENT back to a MASK (spatial shape of the latent).

    The latent samples are reduced to a single-channel mask by taking
    the mean over the channel dimension and clamping to 0..1.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent):
        x = _as_latent(latent)  # [B, C, H, W]
        m = x.mean(dim=1)  # [B, H, W]
        return (_clamp01(m),)


class PSN_Image_To_Mask:
    """Convert an IMAGE to a MASK by averaging the colour channels."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image):
        x = _as_image(image)  # [B, H, W, C]
        m = x.mean(dim=-1)  # [B, H, W]
        return (_clamp01(m),)


class PSN_Mask_To_Image:
    """Convert a MASK to a single-channel IMAGE."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, mask):
        m = _as_mask(mask)  # [B, H, W]
        img = m.unsqueeze(-1)  # [B, H, W, 1]
        return (_clamp01(img),)


# ---------------------------------------------------------------------------
# mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Image_To_Latent": PSN_Image_To_Latent,
    "PSN_Latent_To_Image": PSN_Latent_To_Image,
    "PSN_Mask_To_Latent": PSN_Mask_To_Latent,
    "PSN_Latent_To_Mask": PSN_Latent_To_Mask,
    "PSN_Image_To_Mask": PSN_Image_To_Mask,
    "PSN_Mask_To_Image": PSN_Mask_To_Image,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Image_To_Latent": "PSN Image To Latent",
    "PSN_Latent_To_Image": "PSN Latent To Image",
    "PSN_Mask_To_Latent": "PSN Mask To Latent",
    "PSN_Latent_To_Mask": "PSN Latent To Mask",
    "PSN_Image_To_Mask": "PSN Image To Mask",
    "PSN_Mask_To_Image": "PSN Mask To Image",
}
