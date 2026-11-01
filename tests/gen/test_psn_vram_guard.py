"""Tests for PSN_VRAM_Budget_Compare (compares typed numbers, no I/O)."""

import math

import pytest

from psn_nodes.gen.psn_vram_guard import (
    PSN_VRAM_Budget_Compare,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _guard():
    return PSN_VRAM_Budget_Compare()


def test_psn_vram_budget_compare_safe_when_usage_below_threshold():
    node = _guard()
    is_safe, warning = node.run(budget_gb=8.0, usage_gb=4.0)
    assert is_safe is True
    assert warning == ""


def test_psn_vram_budget_compare_safe_when_usage_equals_threshold():
    node = _guard()
    is_safe, warning = node.run(budget_gb=8.0, usage_gb=8.0)
    assert is_safe is True
    assert warning == ""


def test_psn_vram_budget_compare_unsafe_when_usage_exceeds_threshold():
    node = _guard()
    is_safe, warning = node.run(budget_gb=8.0, usage_gb=9.5)
    assert is_safe is False
    assert "exceeds budget" in warning
    assert "9.500" in warning
    assert "8.000" in warning


def test_psn_vram_budget_compare_rejects_nan_usage():
    node = _guard()
    is_safe, warning = node.run(budget_gb=8.0, usage_gb=float("nan"))
    assert is_safe is False
    assert "finite" in warning


def test_psn_vram_budget_compare_rejects_infinite_threshold():
    node = _guard()
    is_safe, warning = node.run(budget_gb=float("inf"), usage_gb=1.0)
    assert is_safe is False
    assert "finite" in warning


def test_psn_vram_budget_compare_rejects_negative_usage():
    node = _guard()
    is_safe, warning = node.run(budget_gb=8.0, usage_gb=-1.0)
    assert is_safe is False
    assert "must be >= 0" in warning


def test_psn_vram_budget_compare_rejects_negative_threshold():
    node = _guard()
    is_safe, warning = node.run(budget_gb=-2.0, usage_gb=1.0)
    assert is_safe is False
    assert "budget_gb must be >= 0" in warning


def test_psn_vram_budget_compare_rejects_bool_input():
    node = _guard()
    is_safe, warning = node.run(budget_gb=True, usage_gb=1.0)
    assert is_safe is False
    assert "must be a number" in warning


def test_psn_vram_budget_compare_rejects_non_numeric_string():
    node = _guard()
    is_safe, warning = node.run(budget_gb=8.0, usage_gb="not-a-number")
    assert is_safe is False
    assert "could not be parsed" in warning


def test_psn_vram_budget_compare_accepts_numeric_string():
    node = _guard()
    is_safe, warning = node.run(budget_gb="8.0", usage_gb="7.5")
    assert is_safe is True
    assert warning == ""


def test_psn_vram_budget_compare_zero_threshold_with_zero_usage_is_safe():
    node = _guard()
    is_safe, warning = node.run(budget_gb=0.0, usage_gb=0.0)
    assert is_safe is True
    assert warning == ""


def test_psn_vram_budget_compare_zero_threshold_with_positive_usage_is_unsafe():
    node = _guard()
    is_safe, warning = node.run(budget_gb=0.0, usage_gb=0.1)
    assert is_safe is False
    assert "exceeds budget" in warning


def test_psn_vram_budget_compare_node_mappings_present():
    assert "PSN_VRAM_Budget_Compare" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_VRAM_Budget_Compare"] is PSN_VRAM_Budget_Compare
    assert "PSN_VRAM_Budget_Compare" in NODE_DISPLAY_NAME_MAPPINGS


def test_psn_vram_budget_compare_input_types_shape():
    spec = PSN_VRAM_Budget_Compare.INPUT_TYPES()
    assert "required" in spec
    assert "budget_gb" in spec["required"]
    assert "usage_gb" in spec["required"]
    assert PSN_VRAM_Budget_Compare.RETURN_TYPES == ("BOOLEAN", "STRING")
    assert PSN_VRAM_Budget_Compare.RETURN_NAMES == ("within_budget", "message")
    assert PSN_VRAM_Budget_Compare.FUNCTION == "run"


def test_nothing_is_measured_gpu_is_never_read(monkeypatch):
    """Result depends only on the two numbers given; no torch/nvml/subprocess call is made."""
    import sys, subprocess
    def boom(*a, **k):
        raise AssertionError("GPU or process access attempted")
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setitem(sys.modules, "pynvml", None)
    assert _guard().run(budget_gb=8.0, usage_gb=0.0) == (True, "")
    assert _guard().run(budget_gb=8.0, usage_gb=12.0)[0] is False
    assert "reads no GPU" in PSN_VRAM_Budget_Compare.DESCRIPTION
    assert "PSN_VRAM_Guard" not in NODE_CLASS_MAPPINGS
