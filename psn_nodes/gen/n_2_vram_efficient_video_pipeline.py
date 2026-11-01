"""Test-latent video chain for ComfyUI (ParametricStudio).

Builds a chain of test latents, each blended with the one before, and stacks
their first three channels as RGB frames.  No model, sampler or VAE is
involved: the "frame" latents are a gradient plus seeded Gaussian noise (the
``steps`` and ``cfg`` inputs only scale the noise amplitude), and the stacking
step does not decode anything.  Use it to wire and test the nodes around a
video graph, not to make video.

Nodes
-----
PSN_Synthetic_Latent_Frame : one test latent, blended with the previous
                             frame's latent when one is given.  Computed on CPU.
PSN_Latent_RGB_Stack       : stacks the first three channels of each latent as
                             RGB frames (no VAE decode), clamped to 0..1, as an
                             IMAGE batch [T*B, H, W, 3].
PSN_Synthetic_Latent_Loop  : runs the test-latent generator for N frames.
"""

import torch

CAT = "ParametricStudio/Video"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _latent_samples(latent):
    """Return the samples tensor from a LATENT dict, validating shape."""
    if not isinstance(latent, dict) or "samples" not in latent:
        raise ValueError("LATENT must be a dict with a 'samples' key")
    x = latent["samples"]
    if not isinstance(x, torch.Tensor):
        raise ValueError("LATENT['samples'] must be a torch.Tensor")
    if x.dim() != 4:
        raise ValueError(
            "LATENT['samples'] must be 4-D [B, C, H, W], got %d-D" % x.dim()
        )
    return x


def _make_latent(samples):
    """Wrap a [B, C, H, W] tensor in a LATENT dict (new dict, no aliasing)."""
    return {"samples": samples}


def _clamp01(t):
    return torch.clamp(t, 0.0, 1.0)


def _deterministic_frame_latent(
    prev_latent, frame_index, total_frames, steps, cfg, seed
):
    """Seeded noise plus gradient, blended with the previous latent.

    Produces a [B, C, H, W] latent that depends on the previous frame's
    latent and the frame index.  No model or sampling is involved.  All
    computation is done on CPU.

    Parameters
    ----------
    prev_latent : torch.Tensor or None
        [B, C, H, W] latent from the previous frame, or None for frame 0.
    frame_index : int
        0-based index of the frame being generated.
    total_frames : int
        Total number of frames in the chain.
    steps : int
        Divides the noise amplitude (no sampling takes place).
    cfg : float
        Classifier-free guidance scale.
    seed : int
        Base random seed.

    Returns
    -------
    torch.Tensor [B, C, H, W] in roughly 0..1.
    """
    if prev_latent is not None:
        x = _latent_samples(prev_latent)
        b, c, h, w = x.shape
        # temporal blend: mix previous latent with a frame-index offset
        t = float(frame_index) / max(1, total_frames - 1)
        offset = torch.full((b, c, h, w), t, dtype=x.dtype, device="cpu")
        # small deterministic noise based on frame index and seed
        g = torch.Generator(device="cpu").manual_seed(seed + frame_index)
        noise = torch.randn((b, c, h, w), generator=g, device="cpu")
        noise_scale = 0.1 / max(1, steps) * cfg
        out = 0.7 * x.cpu() + 0.3 * offset + noise_scale * noise
    else:
        # first frame: no previous latent, use a default shape
        b, c, h, w = 1, 4, 8, 8
        g = torch.Generator(device="cpu").manual_seed(seed + frame_index)
        noise = torch.randn((b, c, h, w), generator=g, device="cpu")
        t = float(frame_index) / max(1, total_frames - 1)
        offset = torch.full((b, c, h, w), t, device="cpu")
        noise_scale = 0.1 / max(1, steps) * cfg
        out = 0.5 + noise_scale * noise + 0.3 * offset

    return _clamp01(out)


def _latent_rgb_frames(latent):
    """Take a [B, C, H, W] latent's first 3 channels as a [B, H, W, 3] tensor in 0..1.

    Channels are used as RGB as they are (repeated if the latent has fewer
    than 3).  No VAE decode happens.
    """
    x = _latent_samples(latent)
    b, c, h, w = x.shape
    # take first 3 channels (or repeat if fewer)
    if c >= 3:
        rgb = x[:, :3, :, :]
    elif c == 1:
        rgb = x.expand(b, 3, h, w)
    else:
        rgb = x.repeat(1, (3 + c - 1) // c, 1, 1)[:, :3, :, :]
    # [B, 3, H, W] -> [B, H, W, 3]
    img = rgb.permute(0, 2, 3, 1).contiguous()
    return _clamp01(img)


# ---------------------------------------------------------------------------
# Node 1: PSN_Synthetic_Latent_Frame
# ---------------------------------------------------------------------------


class PSN_Synthetic_Latent_Frame:
    """Make one test latent: gradient plus seeded noise, blended with the previous latent.

    Runs no model or sampler.  The first frame is 1x4x8x8; later frames take
    the previous latent's shape.  Computed on CPU.
    """

    DESCRIPTION = ("Makes a deterministic test latent from a gradient and seeded noise, blended "
                   "with the previous latent when given. It runs no model or sampling; steps "
                   "and cfg only scale the noise.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frame_index": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "total_frames": ("INT", {"default": 4, "min": 1, "max": 10000}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 30.0}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2**32 - 1}),
            },
            "optional": {
                "prev_latent": ("LATENT",),
            },
        }

    RETURN_TYPES = ("LATENT", "LATENT")
    RETURN_NAMES = ("current_latent", "next_prev_latent")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        frame_index,
        total_frames,
        steps,
        cfg,
        seed,
        prev_latent=None,
    ):
        if frame_index < 0:
            raise ValueError("frame_index must be >= 0")
        if total_frames < 1:
            raise ValueError("total_frames must be >= 1")
        if frame_index >= total_frames:
            raise ValueError(
                "frame_index (%d) must be < total_frames (%d)"
                % (frame_index, total_frames)
            )
        if steps < 1:
            raise ValueError("steps must be >= 1")

        # validate prev_latent if provided
        if prev_latent is not None:
            _latent_samples(prev_latent)

        current = _deterministic_frame_latent(
            prev_latent, frame_index, total_frames, steps, cfg, seed
        )

        # next_prev_latent is the current frame's latent (to feed the next
        # iteration); return a copy so the caller cannot mutate our state.
        next_prev = current.clone()

        return (_make_latent(current), _make_latent(next_prev))


# The loop below uses the frame node under this alias.
_FrameNode = PSN_Synthetic_Latent_Frame


# ---------------------------------------------------------------------------
# Node 2: PSN_Latent_RGB_Stack
# ---------------------------------------------------------------------------


class PSN_Latent_RGB_Stack:
    """Stack the first three channels of each latent as RGB frames, clamped to 0..1.

    No VAE decode.  The output is an IMAGE batch [T*B, H, W, 3], frames in
    list order.
    """

    DESCRIPTION = ("Stacks the first three latent channels of each latent as RGB frames, "
                   "clamped to 0..1, as an IMAGE batch. It does no VAE decode, so the "
                   "pictures are raw latent values.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latents": ("LATENT",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("rgb_frames",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latents):
        # latents can be a single LATENT dict or a list of LATENT dicts
        if isinstance(latents, dict):
            latent_list = [latents]
        elif isinstance(latents, (list, tuple)):
            latent_list = list(latents)
        else:
            raise ValueError(
                "latents must be a LATENT dict or a list of LATENT dicts"
            )

        if len(latent_list) == 0:
            raise ValueError("latents list must not be empty")

        frames = []
        for i, lat in enumerate(latent_list):
            if not isinstance(lat, dict):
                raise ValueError("latents[%d] is not a LATENT dict" % i)
            img = _latent_rgb_frames(lat)
            frames.append(img)

        # all frames must have the same spatial size and batch
        ref = frames[0]
        for i, f in enumerate(frames[1:], 1):
            if f.shape != ref.shape:
                raise ValueError(
                    "frame %d shape %s != frame 0 shape %s"
                    % (i, tuple(f.shape), tuple(ref.shape))
                )

        # [B, H, W, 3] each -> [T*B, H, W, 3]
        return (torch.cat(frames, dim=0).contiguous(),)


# ---------------------------------------------------------------------------
# Node 3: PSN_Synthetic_Latent_Loop  (convenience: run the generator N times)
# ---------------------------------------------------------------------------


class PSN_Synthetic_Latent_Loop:
    """Run the test-latent generator sequentially for *total_frames* frames.

    Runs no model or sampling.  Returns the list of latents (as a list of
    LATENT dicts) ready for PSN_Latent_RGB_Stack.
    """

    DESCRIPTION = ("Runs the test-latent generator (gradient plus seeded noise, chained from the "
                   "previous frame) for N frames. It runs no model or sampling.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "total_frames": ("INT", {"default": 4, "min": 1, "max": 10000}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 30.0}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2**32 - 1}),
            },
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latents",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, total_frames, steps, cfg, seed):
        if total_frames < 1:
            raise ValueError("total_frames must be >= 1")

        gen = _FrameNode()
        latents = []
        prev = None
        for i in range(total_frames):
            cur, nxt = gen.run(
                frame_index=i,
                total_frames=total_frames,
                steps=steps,
                cfg=cfg,
                seed=seed,
                prev_latent=prev,
            )
            latents.append(cur)
            prev = nxt
        return (latents,)


# ---------------------------------------------------------------------------
# mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Synthetic_Latent_Frame": PSN_Synthetic_Latent_Frame,
    "PSN_Latent_RGB_Stack": PSN_Latent_RGB_Stack,
    "PSN_Synthetic_Latent_Loop": PSN_Synthetic_Latent_Loop,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Synthetic_Latent_Frame": "Test Latent Frame (gradient and noise, no model)",
    "PSN_Latent_RGB_Stack": "Latent RGB Stack (no VAE decode)",
    "PSN_Synthetic_Latent_Loop": "Test Latent Loop (gradient and noise, no model)",
}
