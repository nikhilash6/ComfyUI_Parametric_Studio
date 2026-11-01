"""PSN intermediate latent debugging nodes.

Provides PSN_Peek_Visualizer, which lays a batch of images [N,H,W,C] out in a
single row. It runs no sampler and decodes no latents; the peek images must
come from elsewhere (for example a KSampler with a latent preview).
"""

import torch

CAT = "ParametricStudio/Debug"


class PSN_Peek_Visualizer:
    """Arrange peeked images [N,H,W,C] into a single grid image."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "peeks": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("grid",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, peeks):
        if not torch.is_tensor(peeks):
            raise ValueError("peeks must be a torch tensor")
        if peeks.dim() != 4:
            raise ValueError("peeks must be 4D [N,H,W,C], got %dD" % peeks.dim())
        n, h, w, c = peeks.shape
        if n == 0:
            raise ValueError("peeks is empty; nothing to visualize")
        if c < 1:
            raise ValueError("peeks must have at least 1 channel")
        # Lay out in a single row: grid is [1, h, n*w, c].
        grid = peeks.reshape(1, h, n * w, c)
        return (grid,)


NODE_CLASS_MAPPINGS = {
    "PSN_Peek_Visualizer": PSN_Peek_Visualizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Peek_Visualizer": "PSN Peek Visualizer",
}
