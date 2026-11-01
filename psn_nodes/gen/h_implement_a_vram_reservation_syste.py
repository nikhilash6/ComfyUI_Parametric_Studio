"""ParametricStudio VRAM planning ledger.

An in-process planning ledger for GPU memory (VRAM) figures.  It reserves
nothing on the GPU: it does arithmetic on numbers the caller types in and
remembers per-task entries in a module-level dict.  It keeps track of:

* the total VRAM figure typed in (default 24 GB, an assumption, not read from a device),
* a fixed system/OS figure typed in,
* per-task entries (keyed by a task id),
* and a "live used" figure typed in or wired from elsewhere (default 0).

The nodes expose two operations:

* ``PSN_VramLedgerReserve`` - add ``need_gb`` GB for a task to the ledger.  If
  the ledger's free figure (typed total minus system, live-used and other
  entries) is too small the node reports ``ledger_granted=False`` and the task
  id is NOT added.  The IMAGE input passes through unchanged so the node can
  sit in a workflow as a gate on the ledger result.

* ``PSN_VramLedgerRelease`` - remove a task id from the ledger.  No GPU memory
  is freed.

The ledger is a module-level singleton that the nodes mutate.  All tensor
inputs are passed through untouched (never modified in place).
"""

import torch

CAT = "ParametricStudio/VRAM"


class _Ledger:
    """In-process VRAM planning ledger (singleton per process); touches no GPU."""

    def __init__(self):
        self.total_gb = 24.0
        self.system_gb = 1.0
        self.live_used_gb = 0.0
        self._reservations = {}

    def configure(self, total_gb, system_gb):
        if total_gb <= 0:
            raise ValueError("total_gb must be > 0")
        if system_gb < 0:
            raise ValueError("system_gb must be >= 0")
        if system_gb >= total_gb:
            raise ValueError("system_gb must be < total_gb")
        self.total_gb = float(total_gb)
        self.system_gb = float(system_gb)

    def set_live_used(self, used_gb):
        if used_gb < 0:
            raise ValueError("live_used_gb must be >= 0")
        self.live_used_gb = float(used_gb)

    def free_gb(self):
        reserved = sum(self._reservations.values())
        return max(0.0, self.total_gb - self.system_gb - self.live_used_gb - reserved)

    def reserve(self, task_id, need_gb):
        """Return (granted, free_after).  Never mutates on failure."""
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("task_id must be a non-empty string")
        if need_gb < 0:
            raise ValueError("need_gb must be >= 0")
        if task_id in self._reservations:
            raise ValueError("task_id already reserved: %r" % task_id)
        free = self.free_gb()
        if need_gb > free:
            return False, free
        self._reservations[task_id] = float(need_gb)
        return True, self.free_gb()

    def release(self, task_id):
        if task_id not in self._reservations:
            raise KeyError("no reservation for task_id: %r" % task_id)
        del self._reservations[task_id]

    def snapshot(self):
        return {
            "total_gb": self.total_gb,
            "system_gb": self.system_gb,
            "live_used_gb": self.live_used_gb,
            "reserved_gb": sum(self._reservations.values()),
            "free_gb": self.free_gb(),
            "reservations": dict(self._reservations),
        }


LEDGER = _Ledger()


def _passthrough_image(img):
    """Return a fresh tensor equal to ``img`` (never the same object)."""
    if not isinstance(img, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if img.dim() != 4:
        raise TypeError("image must be [B,H,W,C], got %d dims" % img.dim())
    return img.clone()


def _passthrough_latent(latent):
    if not isinstance(latent, dict) or "samples" not in latent:
        raise TypeError("latent must be a dict with a 'samples' tensor")
    s = latent["samples"]
    if not isinstance(s, torch.Tensor):
        raise TypeError("latent['samples'] must be a torch.Tensor")
    if s.dim() != 4:
        raise TypeError("latent samples must be [B,C,H,W], got %d dims" % s.dim())
    out = dict(latent)
    out["samples"] = s.clone()
    return out


class PSN_VramLedgerReserve:
    """Add a task's typed GB figure to the planning ledger; pass IMAGE through.

    Reserves no GPU memory.  If the ledger has too little free (by the typed
    figures) and fail_on_denied is set, the node raises a RuntimeError.
    """

    DESCRIPTION = (
        "Keeps an in-process planning ledger of typed GB figures (total, system, live used, need). "
        "Reserves no GPU memory and reads no device."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "task_id": ("STRING", {"default": "render"}),
                "need_gb": ("FLOAT", {"default": 2.0, "min": 0.0, "max": 512.0, "step": 0.1}),
                "total_gb": ("FLOAT", {"default": 24.0, "min": 0.1, "max": 2048.0, "step": 0.5}),
                "system_gb": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2048.0, "step": 0.1}),
                "live_used_gb": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 2048.0, "step": 0.1}),
                "fail_on_denied": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "BOOLEAN", "FLOAT")
    RETURN_NAMES = ("image", "ledger_granted", "ledger_free_gb")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, task_id, need_gb, total_gb, system_gb, live_used_gb, fail_on_denied):
        LEDGER.configure(total_gb, system_gb)
        LEDGER.set_live_used(live_used_gb)
        granted, free_after = LEDGER.reserve(task_id, need_gb)
        if not granted and fail_on_denied:
            raise RuntimeError(
                "VRAM ledger entry denied for %r: need %.2f GB, ledger free %.2f GB"
                % (task_id, need_gb, free_after)
            )
        return (_passthrough_image(image), granted, free_after)


class PSN_VramLedgerRelease:
    """Remove a task id from the planning ledger.  Frees no GPU memory."""

    DESCRIPTION = (
        "Removes a task id from the in-process planning ledger. Frees no GPU memory."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "task_id": ("STRING", {"default": "render"}),
                "fail_on_missing": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "BOOLEAN")
    RETURN_NAMES = ("image", "ledger_entry_removed")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, task_id, fail_on_missing):
        try:
            LEDGER.release(task_id)
            released = True
        except KeyError:
            if fail_on_missing:
                raise
            released = False
        return (_passthrough_image(image), released)


class PSN_VramReport:
    """Emit the current ledger snapshot as a FLOAT (free GB) for UI wiring."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("image", "free_gb", "reserved_gb", "live_used_gb")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image):
        snap = LEDGER.snapshot()
        return (
            _passthrough_image(image),
            snap["free_gb"],
            snap["reserved_gb"],
            snap["live_used_gb"],
        )


NODE_CLASS_MAPPINGS = {
    "PSN_VramLedgerReserve": PSN_VramLedgerReserve,
    "PSN_VramLedgerRelease": PSN_VramLedgerRelease,
    "PSN_VramReport": PSN_VramReport,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VramLedgerReserve": "VRAM Ledger Reserve (planning only, reserves no GPU memory)",
    "PSN_VramLedgerRelease": "VRAM Ledger Release (planning only, frees no GPU memory)",
    "PSN_VramReport": "VRAM Report",
}
