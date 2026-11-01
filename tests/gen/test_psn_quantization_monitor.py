"""Tests for PSN_Quantization_Savings_Calc (arithmetic on typed numbers)."""

import math
import pytest

from psn_nodes.gen.psn_quantization_monitor import (
    PSN_Quantization_Savings_Calc,
    compute_vram_savings,
    compute_score_ratio,
    parse_metadata,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_vram_savings_normal_case():
    """Quantized uses 50% less VRAM than reference."""
    savings = compute_vram_savings(500.0, 1000.0)
    assert savings == pytest.approx(50.0, abs=1e-6)


def test_vram_savings_quantized_larger():
    """Quantized model uses more VRAM than reference (negative savings)."""
    savings = compute_vram_savings(1200.0, 1000.0)
    assert savings == pytest.approx(-20.0, abs=1e-6)


def test_vram_savings_zero_reference():
    """Reference VRAM is zero; should return 0.0 to avoid division by zero."""
    savings = compute_vram_savings(500.0, 0.0)
    assert savings == 0.0


def test_vram_savings_negative_reference():
    """Negative reference VRAM is invalid; should return 0.0."""
    savings = compute_vram_savings(500.0, -100.0)
    assert savings == 0.0


def test_vram_savings_clamped_to_minus_100():
    """Savings should not go below -100%."""
    savings = compute_vram_savings(5000.0, 100.0)
    assert savings == pytest.approx(-100.0, abs=1e-6)


def test_quality_metric_identical_scores():
    """Identical quality scores should yield 1.0."""
    q = compute_score_ratio(0.95, 0.95)
    assert q == pytest.approx(1.0, abs=1e-6)


def test_quality_metric_quantized_lower():
    """Quantized score lower than reference; ratio should be < 1.0."""
    q = compute_score_ratio(0.80, 1.00)
    assert q == pytest.approx(0.80, abs=1e-6)


def test_quality_metric_zero_reference():
    """Reference score is zero (none given): no data gives 0.0, never 1.0."""
    assert compute_score_ratio(0.0, 0.0) == 0.0
    assert compute_score_ratio(0.5, 0.0) == pytest.approx(0.0, abs=1e-6)


def test_quality_metric_negative_scores():
    """Negative scores are invalid; should return 0.0."""
    assert compute_score_ratio(-0.5, 1.0) == pytest.approx(0.0, abs=1e-6)
    assert compute_score_ratio(1.0, -0.5) == pytest.approx(0.0, abs=1e-6)


def test_parse_metadata_valid_json():
    """Valid JSON dict should be parsed correctly."""
    meta = parse_metadata('{"model": "llama-7b", "bits": 4}')
    assert meta == {"model": "llama-7b", "bits": 4}


def test_parse_metadata_invalid_json():
    """Invalid JSON should return empty dict."""
    assert parse_metadata("not valid json") == {}
    assert parse_metadata("") == {}
    assert parse_metadata(None) == {}


def test_parse_metadata_non_dict_json():
    """JSON that is not a dict should return empty dict."""
    assert parse_metadata("[1, 2, 3]") == {}
    assert parse_metadata('"string"') == {}


def test_node_run_full_inputs():
    """Full run with all inputs provided."""
    node = PSN_Quantization_Savings_Calc()
    savings, quality, report = node.run(
        quantized_vram_mb=400.0,
        reference_vram_mb=800.0,
        quantized_quality_score=0.92,
        reference_quality_score=1.00,
        metadata_json='{"bits": 8}',
    )
    assert savings == pytest.approx(50.0, abs=1e-6)
    assert quality == pytest.approx(0.92, abs=1e-6)
    assert "vram_saved_percent=50.00%" in report
    assert "score_ratio=0.9200" in report
    assert "bits=8" in report


def test_node_run_no_quality_scores():
    """Run without quality scores; quality_metric should be 0.0."""
    node = PSN_Quantization_Savings_Calc()
    savings, quality, report = node.run(
        quantized_vram_mb=300.0,
        reference_vram_mb=600.0,
    )
    assert savings == pytest.approx(50.0, abs=1e-6)
    assert quality == 0.0
    assert "score_ratio=0.0000 (no scores given)" in report


def test_node_run_bad_vram_values():
    """Bad VRAM values (negative, zero reference) should be handled safely."""
    node = PSN_Quantization_Savings_Calc()
    savings, quality, report = node.run(
        quantized_vram_mb=-100.0,
        reference_vram_mb=0.0,
    )
    assert savings == 0.0
    assert quality == 0.0


def test_node_class_mappings():
    """Verify node is registered correctly."""
    assert "PSN_Quantization_Savings_Calc" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Quantization_Savings_Calc"] is PSN_Quantization_Savings_Calc
    assert "PSN_Quantization_Savings_Calc" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Quantization_Savings_Calc"] == "PSN Quantization Savings Calculator (measures nothing)"


def test_input_types_structure():
    """Verify INPUT_TYPES has required and optional fields with correct types."""
    it = PSN_Quantization_Savings_Calc.INPUT_TYPES()
    assert "required" in it
    assert "optional" in it
    assert "quantized_vram_mb" in it["required"]
    assert "reference_vram_mb" in it["required"]
    assert "quantized_quality_score" in it["optional"]
    assert "reference_quality_score" in it["optional"]
    assert "metadata_json" in it["optional"]
    # Check FLOAT type spec
    assert it["required"]["quantized_vram_mb"][0] == "FLOAT"
    assert it["optional"]["metadata_json"][0] == "STRING"


def test_return_types_and_names():
    """Verify RETURN_TYPES and RETURN_NAMES match."""
    assert PSN_Quantization_Savings_Calc.RETURN_TYPES == ("FLOAT", "FLOAT", "STRING")
    assert PSN_Quantization_Savings_Calc.RETURN_NAMES == ("vram_saved_percent", "score_ratio", "report")
    assert PSN_Quantization_Savings_Calc.FUNCTION == "run"
    assert PSN_Quantization_Savings_Calc.CATEGORY == "ParametricStudio/Quantization"


def test_defaults_with_nothing_typed_do_not_claim_identical_quality():
    """With the node's default inputs (all zeros) the ratio must be 0.0 and the report must say no data."""
    node = PSN_Quantization_Savings_Calc()
    savings, ratio, report = node.run(0.0, 0.0, 0.0, 0.0, "")
    assert savings == 0.0
    assert ratio == 0.0
    assert "no scores given" in report and "no reference VRAM given" in report
    assert "1.0000" not in report


def test_zero_scores_both_given_explicitly_is_still_no_data():
    _, ratio, report = PSN_Quantization_Savings_Calc().run(500.0, 1000.0, 0.0, 0.0)
    assert ratio == 0.0 and "no scores given" in report


def test_description_says_it_measures_nothing():
    assert "measures nothing" in PSN_Quantization_Savings_Calc.DESCRIPTION
