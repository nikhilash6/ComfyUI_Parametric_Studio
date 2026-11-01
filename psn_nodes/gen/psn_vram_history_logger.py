"""PSN_VRAM_Samples_Formatter: formats a list of VRAM samples you supply as JSON.

This module does NOT import torch, start threads, or access the GPU, and it
takes no clock readings. It provides:

- A `VRAMSampleSeries` class that accepts VRAM values (MB) with an offset in ms
  and keeps them, enforcing a minimum spacing between consecutive samples.
- A node `run` function that validates inputs, gives the i-th sample the offset
  i * interval_ms (evenly spaced positions, not times when anything was measured),
  and returns the series.

Whoever supplies the samples measured them; this module only formats them.
"""

import json

CAT = "ParametricStudio/VRAM"


class VRAMSampleSeries:
    """Holds VRAM usage samples with offsets in ms, enforcing a minimum spacing.

    Attributes:
        run_id: Label for this series.
        interval_ms: Minimum spacing in milliseconds between consecutive sample offsets.
        history: List of dicts with 'offset_ms' and 'vram_mb' keys.
    """

    def __init__(self, run_id: str, interval_ms: int):
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        if not isinstance(interval_ms, int) or interval_ms < 1:
            raise ValueError("interval_ms must be a positive integer")
        self.run_id = run_id
        self.interval_ms = interval_ms
        self.history = []
        self._last_offset_ms = None

    def add_sample(self, vram_mb: float, offset_ms: float) -> bool:
        """Add a VRAM sample if the spacing constraint is satisfied.

        Args:
            vram_mb: VRAM usage in megabytes.
            offset_ms: Position of the sample in ms from the start of the series.

        Returns:
            True if the sample was added, False if rejected due to spacing.
        """
        if not isinstance(vram_mb, (int, float)) or vram_mb < 0:
            raise ValueError("vram_mb must be a non-negative number")
        if not isinstance(offset_ms, (int, float)) or offset_ms < 0:
            raise ValueError("offset_ms must be a non-negative number")

        if self._last_offset_ms is not None:
            if (offset_ms - self._last_offset_ms) < self.interval_ms:
                return False

        self.history.append({
            "offset_ms": float(offset_ms),
            "vram_mb": float(vram_mb),
        })
        self._last_offset_ms = float(offset_ms)
        return True

    def get_history(self) -> list:
        """Return the recorded series as a list of dicts."""
        return list(self.history)

    def to_json(self) -> str:
        """Return the series as a JSON string."""
        return json.dumps({
            "run_id": self.run_id,
            "interval_ms": self.interval_ms,
            "samples": self.history,
        }, indent=2)


def _validate_inputs(run_id: str, interval_ms: int, samples: list) -> tuple:
    """Validate all inputs and return (logger, error_message)."""
    if not isinstance(run_id, str) or not run_id.strip():
        return None, "run_id must be a non-empty string"
    if not isinstance(interval_ms, int) or interval_ms < 1:
        return None, "interval_ms must be a positive integer"
    if not isinstance(samples, list):
        return None, "samples must be a list of numbers"
    for i, s in enumerate(samples):
        if not isinstance(s, (int, float)) or s < 0:
            return None, f"samples[{i}] must be a non-negative number"
    try:
        logger = VRAMSampleSeries(run_id, interval_ms)
    except ValueError as e:
        return None, str(e)
    return logger, None


class PSN_VRAM_Samples_Formatter:
    """ComfyUI node that formats a list of VRAM samples (MB) you supply as JSON.

    This node does NOT sample the GPU and reads no clock. Sample i gets the
    offset i * interval_ms: an evenly spaced index position, not a time at
    which anything was measured.
    """

    DESCRIPTION = (
        "Formats a supplied list of VRAM samples (MB) as JSON with evenly spaced index offsets; "
        "does not sample the GPU."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "run_id": ("STRING", {"default": "run_001"}),
                "interval_ms": ("INT", {"default": 100, "min": 1, "max": 100000, "step": 1}),
                "samples": ("LIST", {"default": []}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LIST", "STRING")
    RETURN_NAMES = ("samples_data", "samples_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, run_id: str, interval_ms: int, samples: list) -> tuple:
        logger, err = _validate_inputs(run_id, interval_ms, samples)
        if err:
            return ([], json.dumps({"error": err}))

        # Evenly spaced index offsets: sample i sits at i * interval_ms.
        for i, vram_mb in enumerate(samples):
            logger.add_sample(float(vram_mb), offset_ms=i * interval_ms)

        history = logger.get_history()
        history_json = logger.to_json()
        return (history, history_json)


NODE_CLASS_MAPPINGS = {
    "PSN_VRAM_Samples_Formatter": PSN_VRAM_Samples_Formatter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRAM_Samples_Formatter": "VRAM Samples Formatter (does not sample the GPU)",
}
