"""
Tests for PSN_CFG_Rescale_Calculator node.

These tests verify the arithmetic that reduces a CFG number inside a step
window. No files, network, or GPU access is used.
"""

import pytest
import psn_nodes.gen.n_1_auto_rescaling_cfg_for_video_stability as mod
from psn_nodes.gen.n_1_auto_rescaling_cfg_for_video_stability import (
    PSN_CFG_Rescale_Calculator,
    _compute_reduced_cfg,
)


class TestPSN_CFG_Rescale_Calculator:
    """Test suite for the PSN_CFG_Rescale_Calculator node."""

    def test_honest_names_and_no_model_input(self):
        """Renamed, no MODEL input, no claim of per-step adjustment."""
        assert list(mod.NODE_CLASS_MAPPINGS) == ["PSN_CFG_Rescale_Calculator"]
        assert not hasattr(mod, "PSN_AutoRescaleCFG")
        assert PSN_CFG_Rescale_Calculator.RETURN_NAMES == ("calculated_cfg", "reduction_applied", "reason")
        req = PSN_CFG_Rescale_Calculator.INPUT_TYPES()["required"]
        assert "model" not in req and "MODEL" not in [v[0] for v in req.values()]
        assert "does not patch a model" in PSN_CFG_Rescale_Calculator.DESCRIPTION
        assert mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_CFG_Rescale_Calculator"] == "CFG Rescale Calculator"
        assert _compute_reduced_cfg(7.0, 0.5, 20, 10, 50, 3.0, 1.0, "linear")[0] == 3.5

    def setup_method(self):
        """Set up a fresh node instance for each test."""
        self.node = PSN_CFG_Rescale_Calculator()

    def test_no_rescaling_outside_window(self):
        """Test that no rescaling occurs when step is outside the rescaling window."""
        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=7.0,
            rescale_strength=0.5,
            start_step=10,
            end_step=50,
            step=5,  # Before start_step
            noise_magnitude=2.0,
            threshold=1.0,
            mode="linear",
        )
        assert effective_cfg == 7.0
        assert rescaled is False
        assert "Outside rescaling window" in reason

    def test_no_rescaling_below_threshold(self):
        """Test that no rescaling occurs when noise magnitude is below threshold."""
        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=7.0,
            rescale_strength=0.5,
            start_step=10,
            end_step=50,
            step=20,  # Within window
            noise_magnitude=0.5,  # Below threshold
            threshold=1.0,
            mode="linear",
        )
        assert effective_cfg == 7.0
        assert rescaled is False
        assert "below threshold" in reason

    def test_linear_rescaling_high_noise(self):
        """Test linear rescaling with high noise magnitude."""
        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=7.0,
            rescale_strength=0.5,
            start_step=10,
            end_step=50,
            step=20,  # Within window
            noise_magnitude=3.0,  # Excess ratio = (3-1)/1 = 2.0, clamped to 1.0
            threshold=1.0,
            mode="linear",
        )
        # scale_factor = 1 - 0.5 * min(2.0, 1.0) = 1 - 0.5 = 0.5
        # effective_cfg = 7.0 * 0.5 = 3.5
        assert effective_cfg == pytest.approx(3.5)
        assert rescaled is True
        assert reason.startswith("Reduced from 7.0000 to 3.5000")

    def test_exponential_rescaling(self):
        """Test exponential rescaling mode."""
        import math

        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=7.0,
            rescale_strength=0.5,
            start_step=10,
            end_step=50,
            step=20,
            noise_magnitude=2.0,  # Excess ratio = (2-1)/1 = 1.0
            threshold=1.0,
            mode="exponential",
        )
        # scale_factor = exp(-0.5 * 1.0) = exp(-0.5)
        expected_scale = math.exp(-0.5)
        expected_cfg = 7.0 * expected_scale
        assert effective_cfg == pytest.approx(expected_cfg)
        assert rescaled is True

    def test_clamp_mode_excess_above_one(self):
        """Test clamp mode when excess ratio is >= 1.0."""
        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=10.0,
            rescale_strength=0.3,
            start_step=10,
            end_step=50,
            step=20,
            noise_magnitude=5.0,  # Excess ratio = (5-1)/1 = 4.0 >= 1.0
            threshold=1.0,
            mode="clamp",
        )
        # scale_factor = 1 - 0.3 = 0.7
        # effective_cfg = 10.0 * 0.7 = 7.0
        assert effective_cfg == pytest.approx(7.0)
        assert rescaled is True

    def test_rescale_strength_zero(self):
        """Test that rescale_strength=0.0 means no rescaling."""
        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=7.0,
            rescale_strength=0.0,
            start_step=10,
            end_step=50,
            step=20,
            noise_magnitude=3.0,
            threshold=1.0,
            mode="linear",
        )
        # scale_factor = 1 - 0.0 * min(2.0, 1.0) = 1.0
        # effective_cfg = 7.0 * 1.0 = 7.0
        assert effective_cfg == pytest.approx(7.0)
        assert rescaled is True  # Rescaling was attempted but had no effect

    def test_rescale_strength_one(self):
        """Test that rescale_strength=1.0 with high noise reduces CFG to near zero."""
        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=7.0,
            rescale_strength=1.0,
            start_step=10,
            end_step=50,
            step=20,
            noise_magnitude=3.0,  # Excess ratio clamped to 1.0
            threshold=1.0,
            mode="linear",
        )
        # scale_factor = 1 - 1.0 * 1.0 = 0.0
        # effective_cfg = 7.0 * 0.0 = 0.0
        assert effective_cfg == pytest.approx(0.0)
        assert rescaled is True

    def test_invalid_rescale_strength(self):
        """Test that invalid rescale_strength raises an error."""
        with pytest.raises(ValueError, match="rescale_strength must be between"):
            self.node.run(
                base_cfg=7.0,
                rescale_strength=1.5,  # Invalid: > 1.0
                start_step=10,
                end_step=50,
                step=20,
                noise_magnitude=2.0,
                threshold=1.0,
                mode="linear",
            )

    def test_invalid_end_step(self):
        """Test that end_step < start_step raises an error."""
        with pytest.raises(ValueError, match="end_step must be >= start_step"):
            self.node.run(
                base_cfg=7.0,
                rescale_strength=0.5,
                start_step=50,
                end_step=10,  # Invalid: < start_step
                step=20,
                noise_magnitude=2.0,
                threshold=1.0,
                mode="linear",
            )

    def test_invalid_mode(self):
        """Test that an invalid mode raises an error."""
        with pytest.raises(ValueError, match="mode must be one of"):
            self.node.run(
                base_cfg=7.0,
                rescale_strength=0.5,
                start_step=10,
                end_step=50,
                step=20,
                noise_magnitude=2.0,
                threshold=1.0,
                mode="invalid_mode",
            )

    def test_zero_threshold(self):
        """Test behavior when threshold is zero."""
        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=7.0,
            rescale_strength=0.5,
            start_step=10,
            end_step=50,
            step=20,
            noise_magnitude=1.0,
            threshold=0.0,  # Zero threshold
            mode="linear",
        )
        # When threshold is 0, excess_ratio is set to 1.0
        # scale_factor = 1 - 0.5 * min(1.0, 1.0) = 0.5
        # effective_cfg = 7.0 * 0.5 = 3.5
        assert effective_cfg == pytest.approx(3.5)
        assert rescaled is True

    def test_negative_noise_magnitude(self):
        """Test that negative noise magnitude raises an error."""
        with pytest.raises(ValueError, match="noise_magnitude must be non-negative"):
            self.node.run(
                base_cfg=7.0,
                rescale_strength=0.5,
                start_step=10,
                end_step=50,
                step=20,
                noise_magnitude=-1.0,  # Invalid
                threshold=1.0,
                mode="linear",
            )

    def test_boundary_step_at_start(self):
        """Test rescaling at the exact start_step."""
        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=7.0,
            rescale_strength=0.5,
            start_step=10,
            end_step=50,
            step=10,  # Exactly at start_step
            noise_magnitude=2.0,
            threshold=1.0,
            mode="linear",
        )
        assert rescaled is True
        assert effective_cfg < 7.0

    def test_boundary_step_at_end(self):
        """Test rescaling at the exact end_step."""
        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=7.0,
            rescale_strength=0.5,
            start_step=10,
            end_step=50,
            step=50,  # Exactly at end_step
            noise_magnitude=2.0,
            threshold=1.0,
            mode="linear",
        )
        assert rescaled is True
        assert effective_cfg < 7.0

    def test_step_just_after_end(self):
        """Test no rescaling just after end_step."""
        effective_cfg, rescaled, reason = self.node.run(
            base_cfg=7.0,
            rescale_strength=0.5,
            start_step=10,
            end_step=50,
            step=51,  # Just after end_step
            noise_magnitude=2.0,
            threshold=1.0,
            mode="linear",
        )
        assert effective_cfg == 7.0
        assert rescaled is False
        assert "Outside rescaling window" in reason
