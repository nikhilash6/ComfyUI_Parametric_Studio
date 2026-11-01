"""ParametricStudio multi-GPU video upscaling nodes.

Core idea: split a video frame batch across several GPUs, upscale each
sub-batch, and merge the results back into a single batch.

What is implemented here (CPU-safe, torch only):
  * PSN_SplitBatchForGPU   - split an IMAGE batch into N sub-batches.
  * PSN_NearestUpscaleBatch - integer nearest-neighbour upscale of an IMAGE
    batch on CPU. It uses no upscaler model and no GPU.
  * PSN_MergeUpscaledBatches - concatenate sub-batches back into one batch.

NOT implemented (needs real multi-GPU hardware / ComfyUI model plumbing):
  * actual CUDA device placement (torch.cuda),
  * model-based upscaling,
  * true parallel execution across GPUs (this is a node library, not a
    scheduler; ComfyUI runs nodes sequentially).
"""

import torch

CAT = "ParametricStudio/VideoUpscale"


def _as_image(x):
    """Validate/convert an IMAGE input to a float tensor [B,H,W,C] in 0..1."""
    if not isinstance(x, torch.Tensor):
        raise TypeError("image_batch must be a torch.Tensor")
    if x.dim() != 4:
        raise ValueError("image_batch must have shape [B,H,W,C], got %s" % (tuple(x.shape),))
    if x.dtype != torch.float32:
        x = x.float()
    return x


def _split_evenly(batch, num_gpus):
    """Split batch dim into num_gpus contiguous sub-batches (sizes differ by <=1)."""
    b = batch.shape[0]
    if num_gpus <= 0:
        raise ValueError("num_gpus must be >= 1")
    if num_gpus > b:
        raise ValueError("num_gpus (%d) cannot exceed batch size (%d)" % (num_gpus, b))
    base, extra = divmod(b, num_gpus)
    sizes = [base + (1 if i < extra else 0) for i in range(num_gpus)]
    out = []
    start = 0
    for s in sizes:
        out.append(batch[start:start + s].contiguous())
        start += s
    return out


def _nearest_upscale(img, factor):
    """Deterministic nearest-neighbour spatial upscale of [B,H,W,C] by `factor`."""
    if factor <= 1:
        return img.contiguous()
    # repeat_interleave is the cleanest nearest-neighbour upsample in torch.
    up = torch.repeat_interleave(img, factor, dim=1)
    up = torch.repeat_interleave(up, factor, dim=2)
    return up.contiguous()


class PSN_SplitBatchForGPU:
    """Split an IMAGE batch into num_gpus contiguous sub-batches (one per GPU)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_batch": ("IMAGE",),
                "num_gpus": ("INT", {"default": 2, "min": 1, "max": 64}),
            }
        }

    RETURN_TYPES = ("IMAGE",) * 64  # up to 64 outputs; ComfyUI wires the ones used
    RETURN_NAMES = tuple("gpu_%d" % i for i in range(64))
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image_batch, num_gpus):
        img = _as_image(image_batch)
        parts = _split_evenly(img, num_gpus)
        # Pad with empty tensors so the declared output count is always met.
        while len(parts) < 64:
            parts.append(img.new_empty((0, *img.shape[1:])))
        return tuple(parts)


class PSN_NearestUpscaleBatch:
    """Integer nearest-neighbour upscale of an IMAGE batch on CPU.

    Repeats each pixel `scale` times along height and width. Runs no upscaler
    model and uses no GPU. The input tensor is never modified in place.
    """

    DESCRIPTION = ("Integer nearest-neighbour upscale of an IMAGE batch on "
                   "CPU. Uses no upscaler model and no GPU.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_batch": ("IMAGE",),
                "scale": ("INT", {"default": 2, "min": 1, "max": 8}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("upscaled_batch",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image_batch, scale):
        img = _as_image(image_batch)
        if scale < 1:
            raise ValueError("scale must be >= 1")
        return (_nearest_upscale(img, scale),)


class PSN_MergeUpscaledBatches:
    """Merge a list of IMAGE sub-batches back into one batch (batch dim concat)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "batch_list": ("IMAGE",),  # ComfyUI has no LIST type; accept a single IMAGE
            },
            "optional": {
                "extra_1": ("IMAGE",),
                "extra_2": ("IMAGE",),
                "extra_3": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("merged_batch",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, batch_list, extra_1=None, extra_2=None, extra_3=None):
        parts = [batch_list]
        for e in (extra_1, extra_2, extra_3):
            if e is not None:
                parts.append(e)
        tensors = []
        for p in parts:
            t = _as_image(p)
            if t.shape[0] == 0:
                continue
            tensors.append(t)
        if not tensors:
            raise ValueError("no non-empty sub-batches to merge")
        # All sub-batches must share H,W,C.
        ref = tensors[0].shape[1:]
        for t in tensors[1:]:
            if t.shape[1:] != ref:
                raise ValueError("sub-batches have mismatched spatial shapes: %s vs %s" % (ref, t.shape[1:]))
        merged = torch.cat(tensors, dim=0).contiguous()
        return (merged,)


NODE_CLASS_MAPPINGS = {
    "PSN_SplitBatchForGPU": PSN_SplitBatchForGPU,
    "PSN_NearestUpscaleBatch": PSN_NearestUpscaleBatch,
    "PSN_MergeUpscaledBatches": PSN_MergeUpscaledBatches,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SplitBatchForGPU": "PSN Split Batch For GPU",
    "PSN_NearestUpscaleBatch": "PSN Nearest-Neighbour Upscale (CPU)",
    "PSN_MergeUpscaledBatches": "PSN Merge Upscaled Batches",
}
