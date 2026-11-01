import pytest
from psn_nodes.gen.psn_videoqualitymetric import (
    PSN_VideoFrameDiffMetric,
    compute_metric,
    _normalize_frame,
    METRICS,
)

def test_psnr_identical_frames():
    """PSNR should be very high (100) for identical frames."""
    frame = [[0.5, 0.5], [0.5, 0.5]]
    ref = [[0.5, 0.5], [0.5, 0.5]]
    avg, heatmap = compute_metric([frame], [ref], "psnr")
    assert avg == 100.0
    assert len(heatmap) == 1
    assert heatmap[0] == [[0.0, 0.0], [0.0, 0.0]]

def test_psnr_different_frames():
    """PSNR should be lower for different frames."""
    frame = [[1.0, 0.0], [0.0, 1.0]]
    ref = [[0.0, 1.0], [1.0, 0.0]]
    avg, heatmap = compute_metric([frame], [ref], "psnr")
    # MSE = ((1-0)^2 + (0-1)^2 + (0-1)^2 + (1-0)^2) / 4 = 4/4 = 1.0
    # PSNR = 10 * log10(1/1) = 0
    assert abs(avg - 0.0) < 1e-6

def test_luminance_similarity_identical_frames():
    """Luminance similarity should be 1.0 for identical frames."""
    frame = [[0.5, 0.5], [0.5, 0.5]]
    ref = [[0.5, 0.5], [0.5, 0.5]]
    avg, heatmap = compute_metric([frame], [ref], "luminance_similarity")
    assert abs(avg - 1.0) < 1e-6

def test_weighted_l1_identical_frames():
    """Weighted L1 should be 0.0 for identical frames."""
    frame = [[0.5, 0.5], [0.5, 0.5]]
    ref = [[0.5, 0.5], [0.5, 0.5]]
    avg, heatmap = compute_metric([frame], [ref], "weighted_l1")
    assert abs(avg - 0.0) < 1e-6

def test_invalid_metric_raises():
    """Should raise ValueError for unknown metric."""
    frame = [[0.5]]
    ref = [[0.5]]
    with pytest.raises(ValueError, match="Unknown metric"):
        compute_metric([frame], [ref], "unknown_metric")

def test_mismatched_frame_count_raises():
    """Should raise ValueError if frame counts don't match."""
    frames = [[[0.5]], [[0.5]]]
    ref = [[[0.5]]]
    with pytest.raises(ValueError, match="Number of frames"):
        compute_metric(frames, ref, "psnr")

def test_empty_frames():
    """Should handle empty frames gracefully."""
    avg, heatmap = compute_metric([], [], "psnr")
    assert avg == 0.0
    assert heatmap == []

def test_normalization_255_range():
    """Frames with values in [0, 255] should be normalized to [0, 1]."""
    frame = [[255.0, 0.0]]
    ref = [[0.0, 255.0]]
    avg, heatmap = compute_metric([frame], [ref], "psnr")
    # After normalization: frame = [[1.0, 0.0]], ref = [[0.0, 1.0]]
    # Same as test_psnr_different_frames, so PSNR = 0
    assert abs(avg - 0.0) < 1e-6

def test_node_run_interface():
    """Test the node's run method directly."""
    node = PSN_VideoFrameDiffMetric()
    frame = [[0.5, 0.5]]
    ref = [[0.5, 0.5]]
    avg, heatmap = node.run([frame], [ref], "psnr")
    assert avg == 100.0
    assert len(heatmap) == 1

def test_multiple_frames_average():
    """Average should be computed across multiple frames."""
    frame1 = [[1.0]]
    ref1 = [[0.0]]
    frame2 = [[0.0]]
    ref2 = [[1.0]]
    avg, heatmap = compute_metric([frame1, frame2], [ref1, ref2], "psnr")
    # Each frame has MSE = 1.0, PSNR = 0.0
    assert abs(avg - 0.0) < 1e-6
    assert len(heatmap) == 2


def test_luminance_similarity_real_values():
    """(2xy+c1)/(x^2+y^2+c1) per pixel, mean over pixels; heatmap is 1 - similarity."""
    c1 = 0.01 ** 2
    frame, ref = [[1.0, 0.0]], [[0.5, 0.0]]
    avg, heatmap = compute_metric([frame], [ref], "luminance_similarity")
    s0 = (2 * 1.0 * 0.5 + c1) / (1.0 + 0.25 + c1)
    assert avg == pytest.approx((s0 + 1.0) / 2)
    assert heatmap[0][0] == pytest.approx([1 - s0, 0.0])
    # pixels with the same value from a different frame scale give the same score: no local-structure term
    flat, flat_ref = [[0.9, 0.9]], [[0.3, 0.3]]
    assert compute_metric([flat], [flat_ref], "luminance_similarity")[0] == pytest.approx(
        (2 * 0.9 * 0.3 + c1) / (0.81 + 0.09 + c1))

def test_weighted_l1_real_values():
    import math
    frame, ref = [[1.0]], [[0.0]]
    avg, heatmap = compute_metric([frame], [ref], "weighted_l1")
    expected = 1.0 * (1.0 + 0.5 * math.sin(math.pi * 1.0 / 2.0))
    assert avg == pytest.approx(expected) and avg == pytest.approx(1.5)
    assert heatmap[0] == [[pytest.approx(1.5)]]

def test_old_metric_names_are_gone():
    assert METRICS == ["psnr", "luminance_similarity", "weighted_l1"]
    for old in ("ssim", "lpips"):
        with pytest.raises(ValueError, match="Unknown metric"):
            compute_metric([[[0.5]]], [[[0.5]]], old)
    import psn_nodes.gen.psn_videoqualitymetric as m
    assert list(m.NODE_CLASS_MAPPINGS) == ["PSN_VideoFrameDiffMetric"]
    assert "not true SSIM or LPIPS" in m.PSN_VideoFrameDiffMetric.DESCRIPTION
