"""Tests for n_2_custom_sigma_schedule_baseline.py."""

import json
import math
import sys

import torch

from n_2_custom_sigma_schedule_baseline import (
    PSN_CustomSigmaGenerator,
    PSN_KSampler_Graph_Builder,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _linear_sigmas,
    _karras_sigmas,
    _exponential_sigmas,
    _parse_custom_sigmas,
    _validate_sigmas,
)


def test_module_mappings():
    """Check that NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS exist and are correct."""
    assert "PSN_CustomSigmaGenerator" in NODE_CLASS_MAPPINGS
    assert "PSN_KSampler_Graph_Builder" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_CustomSigmaGenerator"] is PSN_CustomSigmaGenerator
    assert NODE_CLASS_MAPPINGS["PSN_KSampler_Graph_Builder"] is PSN_KSampler_Graph_Builder
    assert "PSN_CustomSigmaGenerator" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_KSampler_Graph_Builder" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_BaselineSampler" not in NODE_CLASS_MAPPINGS
    print("  [1] module mappings ok")


def test_linear_sigmas_count():
    """Linear schedule with steps=10 should produce 11 sigmas (steps+1)."""
    gen = PSN_CustomSigmaGenerator()
    (sigmas,) = gen.run(scheduler_type="Linear", steps=10, start_sigma=1.0, end_sigma=0.0)
    assert sigmas.dim() == 1, "sigmas must be 1D"
    assert sigmas.numel() == 11, "expected 11 sigmas for steps=10, got %d" % sigmas.numel()
    assert abs(sigmas[0].item() - 1.0) < 1e-5, "first sigma should be start_sigma"
    assert abs(sigmas[-1].item() - 0.0) < 1e-5, "last sigma should be end_sigma"
    # Check monotonic decreasing
    for i in range(sigmas.numel() - 1):
        assert sigmas[i].item() >= sigmas[i + 1].item(), "linear sigmas must be non-increasing"
    print("  [2] linear sigmas count ok")


def test_karras_sigmas():
    """Karras schedule should produce steps+1 sigmas, first=start, last=end."""
    gen = PSN_CustomSigmaGenerator()
    (sigmas,) = gen.run(scheduler_type="Karras", steps=20, start_sigma=1.0, end_sigma=0.0)
    assert sigmas.numel() == 21
    assert abs(sigmas[0].item() - 1.0) < 1e-4, "karras first sigma should be ~start_sigma"
    assert abs(sigmas[-1].item() - 0.0) < 1e-6, "karras last sigma should be end_sigma"
    # All values should be non-negative
    assert (sigmas >= 0).all(), "karras sigmas must be non-negative"
    print("  [3] karras sigmas ok")


def test_exponential_sigmas():
    """Exponential schedule should produce steps+1 sigmas."""
    gen = PSN_CustomSigmaGenerator()
    (sigmas,) = gen.run(scheduler_type="Exponential", steps=5, start_sigma=2.0, end_sigma=0.1)
    assert sigmas.numel() == 6
    assert abs(sigmas[0].item() - 2.0) < 1e-5
    assert abs(sigmas[-1].item() - 0.1) < 1e-5
    # Geometric: ratio between consecutive values should be constant
    ratios = [sigmas[i].item() / sigmas[i + 1].item() for i in range(sigmas.numel() - 1)]
    for r in ratios[1:]:
        assert abs(r - ratios[0]) < 1e-3, "exponential sigmas should have constant ratio"
    print("  [4] exponential sigmas ok")


def test_custom_sigmas_string():
    """Custom schedule from a comma-separated string."""
    gen = PSN_CustomSigmaGenerator()
    (sigmas,) = gen.run(
        scheduler_type="Custom",
        steps=10,
        start_sigma=1.0,
        end_sigma=0.0,
        custom_sigma_string="1.0, 0.8, 0.5, 0.2, 0.0",
    )
    assert sigmas.numel() == 5
    expected = [1.0, 0.8, 0.5, 0.2, 0.0]
    for i, v in enumerate(expected):
        assert abs(sigmas[i].item() - v) < 1e-6, "custom sigma[%d] = %f, expected %f" % (i, sigmas[i].item(), v)
    print("  [5] custom sigmas string ok")


def test_bad_custom_string():
    """Custom string with invalid values should raise ValueError."""
    gen = PSN_CustomSigmaGenerator()
    # Non-numeric value
    try:
        gen.run(scheduler_type="Custom", steps=10, start_sigma=1.0, end_sigma=0.0,
                custom_sigma_string="1.0, abc, 0.0")
        assert False, "should have raised ValueError for non-numeric value"
    except ValueError:
        pass
    # Negative value
    try:
        gen.run(scheduler_type="Custom", steps=10, start_sigma=1.0, end_sigma=0.0,
                custom_sigma_string="1.0, -0.5, 0.0")
        assert False, "should have raised ValueError for negative value"
    except ValueError:
        pass
    # Empty string
    try:
        gen.run(scheduler_type="Custom", steps=10, start_sigma=1.0, end_sigma=0.0,
                custom_sigma_string="")
        assert False, "should have raised ValueError for empty string"
    except ValueError:
        pass
    print("  [6] bad custom string ok")


def test_bad_scheduler_type():
    """Unknown scheduler type should raise ValueError."""
    gen = PSN_CustomSigmaGenerator()
    try:
        gen.run(scheduler_type="Bogus", steps=10, start_sigma=1.0, end_sigma=0.0)
        assert False, "should have raised ValueError for unknown scheduler type"
    except ValueError:
        pass
    print("  [7] bad scheduler type ok")


def test_graph_builder_basic():
    """Builder returns only a JSON node entry carrying the sigmas; no latent, no sampling."""
    gen = PSN_CustomSigmaGenerator()
    (sigmas,) = gen.run(scheduler_type="Linear", steps=5, start_sigma=1.0, end_sigma=0.0)
    builder = PSN_KSampler_Graph_Builder()
    out = builder.run(sigmas=sigmas, sampler="euler", seed=42)
    assert len(out) == 1 and PSN_KSampler_Graph_Builder.RETURN_TYPES == ("STRING",)
    assert PSN_KSampler_Graph_Builder.RETURN_NAMES == ("node_entry_json",)
    graph = json.loads(out[0])
    assert list(graph) == ["3"], "no invented extra nodes"
    inputs = graph["3"]["inputs"]
    assert graph["3"]["class_type"] == "KSampler"
    assert inputs["custom_sigmas"] == sigmas.tolist()
    assert inputs["steps"] == 5 and inputs["seed"] == 42 and inputs["sampler_name"] == "euler"
    # fabricated pieces are gone: no dangling links, no invented node entries
    assert not any(isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) for v in inputs.values())
    assert "PLACEHOLDER" not in out[0]
    assert "no sampling" in PSN_KSampler_Graph_Builder.DESCRIPTION
    assert "LATENT" not in str(PSN_KSampler_Graph_Builder.INPUT_TYPES())
    print("  [8] graph builder basic ok")


def test_graph_builder_bad_inputs():
    builder = PSN_KSampler_Graph_Builder()
    for bad in (torch.randn(2, 3), torch.tensor([1.0, float("nan"), 0.0]), torch.tensor([1.0, -0.5, 0.0])):
        try:
            builder.run(sigmas=bad, sampler="euler")
            assert False, "should have raised ValueError for bad sigmas"
        except ValueError:
            pass
    try:
        builder.run(sigmas=torch.tensor([1.0, 0.0]), sampler="nope")
        assert False, "should have raised ValueError for unknown sampler"
    except ValueError:
        pass
    print("  [9] graph builder bad inputs ok")


def test_edge_case_single_step():
    """steps=1 should produce 2 sigmas."""
    gen = PSN_CustomSigmaGenerator()
    (sigmas,) = gen.run(scheduler_type="Linear", steps=1, start_sigma=1.0, end_sigma=0.0)
    assert sigmas.numel() == 2
    assert abs(sigmas[0].item() - 1.0) < 1e-5
    assert abs(sigmas[1].item() - 0.0) < 1e-5
    print("  [11] edge case single step ok")


def test_edge_case_zero_start():
    """start_sigma=0 should produce all-zero sigmas (no noise)."""
    gen = PSN_CustomSigmaGenerator()
    (sigmas,) = gen.run(scheduler_type="Linear", steps=5, start_sigma=0.0, end_sigma=0.0)
    assert (sigmas == 0).all(), "all sigmas should be 0 when start=0, end=0"
    print("  [12] edge case zero start ok")


def main():
    print("Running tests for n_2_custom_sigma_schedule_baseline...")
    test_module_mappings()
    test_linear_sigmas_count()
    test_karras_sigmas()
    test_exponential_sigmas()
    test_custom_sigmas_string()
    test_bad_custom_string()
    test_bad_scheduler_type()
    test_graph_builder_basic()
    test_graph_builder_bad_inputs()
    test_edge_case_single_step()
    test_edge_case_zero_start()
    print("ok")


if __name__ == "__main__":
    main()
