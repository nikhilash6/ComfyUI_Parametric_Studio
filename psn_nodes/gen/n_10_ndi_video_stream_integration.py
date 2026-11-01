"""NDI Video Stream Integration for ComfyUI (ParametricStudio).

Converts IMAGE frames to RGB bytes and hands them to a caller-supplied sender
callable (the NDI_SENDER input). The module itself has no NDI library and
sends nothing over the network: with no sender connected, nothing is handed
off and the node reports False. No node here produces an NDI_SENDER.
"""

import torch

CAT = "ParametricStudio/NDI"


def _s(x):
    """Unwrap a ComfyUI LATENT dict to its samples tensor."""
    if isinstance(x, dict):
        return x["samples"]
    return x


def _out(latent, samples):
    """Re-wrap a samples tensor into a ComfyUI LATENT dict."""
    return {"samples": samples}


def image_to_rgb_bytes(image):
    """Convert a ComfyUI IMAGE tensor [B,H,W,C] in 0..1 to a list of
    per-frame RGB byte arrays (bytes objects).

    Returns a list of length B, each element a bytes object of length
    H*W*3 (row-major, RGB).
    """
    if not torch.is_tensor(image):
        raise TypeError("image must be a torch tensor")
    if image.dim() != 4:
        raise ValueError("image must have shape [B,H,W,C], got %d dims" % image.dim())
    if image.shape[-1] not in (3, 4):
        raise ValueError("image last dim must be 3 (RGB) or 4 (RGBA), got %d" % image.shape[-1])

    # Clamp to 0..1 and convert to uint8
    img = image.clamp(0.0, 1.0)
    # Take first 3 channels if RGBA
    if img.shape[-1] == 4:
        img = img[:, :, :, :3]
    # Convert to uint8
    img_u8 = (img * 255.0 + 0.5).to(torch.uint8)

    frames = []
    for i in range(img_u8.shape[0]):
        frame = img_u8[i].contiguous().view(-1).numpy().tobytes()
        frames.append(frame)
    return frames


class PSN_NDI_Source:
    """Converts IMAGE frames to RGB bytes and hands them to a supplied sender.

    Returns True only when a connected sender callable returned truthy.
    Without a sender nothing is sent and the output is False.
    """

    DESCRIPTION = (
        "Converts frames to RGB bytes and hands them to the connected "
        "NDI_SENDER callable; output is True only if that sender returned "
        "truthy. With no sender connected nothing is sent and the output is "
        "False. This node has no NDI library of its own."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "ndi_name": ("STRING", {"default": "ComfyUI_NDI", "multiline": False}),
                "fps": ("INT", {"default": 30, "min": 1, "max": 240}),
            },
            "optional": {
                "ndi_sender": ("NDI_SENDER",),
            },
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("handed_to_sender",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, ndi_name, fps, ndi_sender=None):
        """Convert image to RGB bytes and hand them to the NDI sender.

        Args:
            image: IMAGE tensor [B,H,W,C] in 0..1.
            ndi_name: Name of the NDI source to register.
            fps: Target frames per second.
            ndi_sender: Optional callable(ndi_name, fps, frames_bytes) -> bool.
                        If None, nothing is sent.

        Returns:
            (bool,): True only if a supplied sender returned truthy.
        """
        # Validate inputs
        if not torch.is_tensor(image):
            raise TypeError("image must be a torch tensor")
        if image.dim() != 4:
            raise ValueError("image must have shape [B,H,W,C]")
        if image.shape[-1] not in (3, 4):
            raise ValueError("image last dim must be 3 or 4")
        if not isinstance(ndi_name, str) or len(ndi_name) == 0:
            raise ValueError("ndi_name must be a non-empty string")
        if not isinstance(fps, int) or fps < 1 or fps > 240:
            raise ValueError("fps must be an integer between 1 and 240")

        # Convert to RGB byte arrays
        frames = image_to_rgb_bytes(image)

        if ndi_sender is None:
            # No sender connected: nothing is handed off.
            return (False,)
        if not callable(ndi_sender):
            raise TypeError("ndi_sender must be callable")
        result = ndi_sender(ndi_name, fps, frames)
        return (bool(result),)


NODE_CLASS_MAPPINGS = {
    "PSN_NDI_Source": PSN_NDI_Source,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_NDI_Source": "NDI Video Stream Source",
}
