"""PSN_VideoFrameDiffMetric: pure-logic difference scores between two lists of grayscale frames.

It does NOT use torch, ComfyUI, or any GPU/IO. It accepts plain Python lists
(frames as nested lists of pixel values) and computes, with the standard library:
  - psnr: true PSNR (peak 1.0) from the mean squared error;
  - luminance_similarity: a per-pixel luminance-similarity term,
    (2xy + c1) / (x^2 + y^2 + c1). This is only the luminance factor of SSIM
    (no local variance or covariance, no windows), NOT true SSIM;
  - weighted_l1: mean absolute difference weighted by 1 + 0.5*sin(pi*(x+y)/2).
    It uses no learned features and is NOT LPIPS.

Inputs:
    frames: A list of frames, where each frame is a list of rows, each row is a
            list of pixel values (floats in [0, 1] or [0, 255]).
    reference: A list of reference frames in the same structure.
    metric: One of "psnr", "luminance_similarity", "weighted_l1".

Outputs:
    average_metric: FLOAT - The average metric value across all frames.
    heatmap: A list of frames (same shape as input) where each pixel is the
             per-pixel contribution (psnr: absolute error; luminance_similarity:
             1 - similarity; weighted_l1: weighted absolute difference).

All pixel values are normalized to [0, 1] internally.
"""

import math

METRICS = ["psnr", "luminance_similarity", "weighted_l1"]

def _normalize_frame(frame):
    """Normalize a frame to [0, 1] range. Detects if values are in [0, 255]."""
    if not frame or not frame[0]:
        return frame
    max_val = 0.0
    for row in frame:
        for v in row:
            if v > max_val:
                max_val = v
    if max_val > 1.0:
        scale = 1.0 / max_val
        return [[v * scale for v in row] for row in frame]
    return frame

def _compute_psnr_frame(frame, ref_frame):
    """Compute PSNR for a single frame pair. Returns (psnr_value, heatmap_frame)."""
    if not frame or not ref_frame:
        return 0.0, frame
    mse = 0.0
    heatmap = []
    total_pixels = 0
    for i, row in enumerate(frame):
        heat_row = []
        for j, v in enumerate(row):
            rv = ref_frame[i][j] if i < len(ref_frame) and j < len(ref_frame[i]) else 0.0
            diff = v - rv
            mse += diff * diff
            heat_row.append(abs(diff))
            total_pixels += 1
        heatmap.append(heat_row)
    if total_pixels == 0:
        return 0.0, heatmap
    mse /= total_pixels
    if mse == 0:
        return 100.0, heatmap
    psnr = 10.0 * math.log10(1.0 / mse)
    return psnr, heatmap

def _compute_luminance_similarity_frame(frame, ref_frame):
    """Per-pixel luminance similarity for a single frame pair. Returns (mean_similarity, heatmap_frame).

    Uses only the luminance term of SSIM, (2xy + c1) / (x^2 + y^2 + c1), on each pixel alone.
    It is not SSIM: there is no local variance, covariance or window.
    """
    if not frame or not ref_frame:
        return 0.0, frame
    c1 = (0.01 * 1.0) ** 2
    total_pixels = 0
    sim_sum = 0.0
    heatmap = []
    for i, row in enumerate(frame):
        heat_row = []
        for j, v in enumerate(row):
            rv = ref_frame[i][j] if i < len(ref_frame) and j < len(ref_frame[i]) else 0.0
            sim = (2 * v * rv + c1) / (v ** 2 + rv ** 2 + c1)
            sim_sum += sim
            heat_row.append(1.0 - sim)  # Difference from perfect similarity
            total_pixels += 1
        heatmap.append(heat_row)
    if total_pixels == 0:
        return 0.0, heatmap
    return sim_sum / total_pixels, heatmap

def _compute_weighted_l1_frame(frame, ref_frame):
    """Weighted mean absolute difference for a single frame pair.
    Weight is 1 + 0.5*sin(pi*(x+y)/2), which emphasises mid-range pixels. Not LPIPS.
    Returns (value, heatmap_frame). Lower is closer."""
    if not frame or not ref_frame:
        return 0.0, frame
    total_pixels = 0
    l1_sum = 0.0
    heatmap = []
    for i, row in enumerate(frame):
        heat_row = []
        for j, v in enumerate(row):
            rv = ref_frame[i][j] if i < len(ref_frame) and j < len(ref_frame[i]) else 0.0
            diff = abs(v - rv)
            weight = 1.0 + 0.5 * math.sin(math.pi * (v + rv) / 2.0)
            l1_sum += diff * weight
            heat_row.append(diff * weight)
            total_pixels += 1
        heatmap.append(heat_row)
    if total_pixels == 0:
        return 0.0, heatmap
    return l1_sum / total_pixels, heatmap

def compute_metric(frames, reference, metric):
    """Compute the specified metric across all frames.
    
    Args:
        frames: List of frames (list of list of floats).
        reference: List of reference frames (list of list of floats).
        metric: One of "psnr", "luminance_similarity", "weighted_l1".
    
    Returns:
        (average_metric, heatmap) where heatmap is a list of frames.
    """
    if metric not in METRICS:
        raise ValueError(f"Unknown metric: {metric}. Must be one of {METRICS}")
    if not frames or not reference:
        return 0.0, frames if frames else []
    if len(frames) != len(reference):
        raise ValueError("Number of frames must match number of reference frames")
    
    frames_norm = [_normalize_frame(f) for f in frames]
    ref_norm = [_normalize_frame(f) for f in reference]
    
    values = []
    heatmaps = []
    for i in range(len(frames_norm)):
        if metric == "psnr":
            val, heat = _compute_psnr_frame(frames_norm[i], ref_norm[i])
        elif metric == "luminance_similarity":
            val, heat = _compute_luminance_similarity_frame(frames_norm[i], ref_norm[i])
        else:  # weighted_l1
            val, heat = _compute_weighted_l1_frame(frames_norm[i], ref_norm[i])
        values.append(val)
        heatmaps.append(heat)
    
    if not values:
        return 0.0, heatmaps
    avg = sum(values) / len(values)
    return avg, heatmaps

class PSN_VideoFrameDiffMetric:
    """Scores the difference between two lists of grayscale frames (pure logic, no GPU).

    Gives PSNR, a per-pixel luminance-similarity score and a weighted L1 difference.
    The last two are not true SSIM or LPIPS.
    """

    DESCRIPTION = (
        "Computes PSNR, a per-pixel luminance-similarity score and a weighted L1 difference between two lists "
        "of grayscale frames; not true SSIM or LPIPS."
    )
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frames": ("LIST", {"default": []}),
                "reference": ("LIST", {"default": []}),
                "metric": (METRICS,),
            },
            "optional": {},
        }
    
    RETURN_TYPES = ("FLOAT", "LIST")
    RETURN_NAMES = ("average_metric", "heatmap")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Video"
    
    def run(self, frames, reference, metric):
        avg, heatmap = compute_metric(frames, reference, metric)
        return (avg, heatmap)

NODE_CLASS_MAPPINGS = {"PSN_VideoFrameDiffMetric": PSN_VideoFrameDiffMetric}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_VideoFrameDiffMetric": "PSN Video Frame Difference Metric (PSNR, luminance, weighted L1)"}
