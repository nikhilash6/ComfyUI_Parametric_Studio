"""PSN_Quantization_Savings_Calc: percent VRAM saved and a score ratio from numbers you type.

This module does arithmetic on plain numbers (VRAM usage in MB, quality scores)
that you or an upstream node supply. It measures nothing: no model is loaded,
no VRAM is read and no quality is evaluated. It computes:

- vram_saved_percent: percentage of VRAM saved by the quantized figure relative
  to the reference (full precision) figure.
- score_ratio: quantized score divided by reference score, clamped to 0.0..1.0.
  It is 0.0 when no scores were given (reference score 0 or missing); that means
  "no data", not "poor quality".

All inputs are plain numbers (FLOAT) or strings (JSON text for optional
metadata). No file, network, subprocess, or torch access is performed.
"""

import json
import math

CAT = "ParametricStudio/Quantization"


def _safe_float(value, default=0.0):
    """Convert value to float safely; return default on failure."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return default
        return float(value)
    if isinstance(value, str):
        try:
            f = float(value)
            if math.isnan(f) or math.isinf(f):
                return default
            return f
        except (ValueError, TypeError):
            return default
    return default


def _clamp(value, lo, hi):
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))


def compute_vram_savings(quantized_vram_mb, reference_vram_mb):
    """Compute percentage VRAM savings.

    Returns a float in [-100.0, 100.0]. Positive means savings (quantized
    uses less VRAM). Negative means the quantized model uses more VRAM.
    If reference_vram_mb is 0 or negative, returns 0.0.
    """
    q = _safe_float(quantized_vram_mb, 0.0)
    r = _safe_float(reference_vram_mb, 0.0)
    if r <= 0.0:
        return 0.0
    savings = ((r - q) / r) * 100.0
    return _clamp(savings, -100.0, 100.0)


def compute_score_ratio(quantized_score, reference_score):
    """Return quantized/reference clamped to [0.0, 1.0].

    Returns 0.0 when there is no usable data: a reference score of 0 (the
    default, meaning none was given) or any negative score.
    """
    qs = _safe_float(quantized_score, 0.0)
    rs = _safe_float(reference_score, 0.0)
    if rs <= 0.0 or qs < 0.0:
        return 0.0
    return _clamp(qs / rs, 0.0, 1.0)


def parse_metadata(json_text):
    """Parse optional JSON metadata string; return dict or empty dict."""
    if not json_text or not isinstance(json_text, str):
        return {}
    try:
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}


class PSN_Quantization_Savings_Calc:
    """Compute percent VRAM saved and a score ratio from numbers you type.

    Measures nothing: no model objects, torch tensors, or GPU access are used.
    """

    DESCRIPTION = (
        "Computes % VRAM saved and a score ratio from numbers you type; measures nothing. "
        "score_ratio is 0 when no scores are given."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "quantized_vram_mb": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.1}),
                "reference_vram_mb": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.1}),
            },
            "optional": {
                "quantized_quality_score": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.001}),
                "reference_quality_score": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.001}),
                "metadata_json": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "STRING")
    RETURN_NAMES = ("vram_saved_percent", "score_ratio", "report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, quantized_vram_mb, reference_vram_mb,
            quantized_quality_score=None, reference_quality_score=None,
            metadata_json=None):
        savings = compute_vram_savings(quantized_vram_mb, reference_vram_mb)

        if quantized_quality_score is not None and reference_quality_score is not None:
            quality = compute_score_ratio(quantized_quality_score, reference_quality_score)
        else:
            quality = 0.0
        have_scores = _safe_float(reference_quality_score, 0.0) > 0.0

        meta = parse_metadata(metadata_json)
        report_parts = [
            "vram_saved_percent={:.2f}%".format(savings)
            if _safe_float(reference_vram_mb, 0.0) > 0.0
            else "vram_saved_percent=0.00% (no reference VRAM given)",
            "score_ratio={:.4f}".format(quality)
            if have_scores
            else "score_ratio=0.0000 (no scores given)",
        ]
        if meta:
            for key in sorted(meta.keys()):
                report_parts.append("{}={}".format(key, meta[key]))
        report = "; ".join(report_parts)

        return (savings, quality, report)


NODE_CLASS_MAPPINGS = {
    "PSN_Quantization_Savings_Calc": PSN_Quantization_Savings_Calc,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Quantization_Savings_Calc": "PSN Quantization Savings Calculator (measures nothing)",
}
