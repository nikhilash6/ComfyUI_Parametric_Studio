"""Tests for PSN_VRAM_Bytes_Check (arithmetic on typed bytes)."""

import pytest

from psn_nodes.gen.psn_vramguard import (
    PSN_VRAM_Bytes_Check,
    _check_vram,
    _validate_inputs,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_psn_vram_bytes_check_safe_small_request():
    """Small request on a 24GB GPU with low allocation should be safe."""
    node = PSN_VRAM_Bytes_Check()
    safe, msg = node.run(
        required_gb=1.0,
        current_batch_size=1,
        allocated_bytes=2e9,
        reserved_bytes=3e9,
        total_bytes=24e9,
    )
    assert safe is True
    assert msg.startswith("Fits")


def test_psn_vram_bytes_check_unsafe_large_request():
    """Absurdly large request should be flagged as OOM risk."""
    node = PSN_VRAM_Bytes_Check()
    safe, msg = node.run(
        required_gb=200.0,
        current_batch_size=1,
        allocated_bytes=2e9,
        reserved_bytes=3e9,
        total_bytes=24e9,
    )
    assert safe is False
    assert "Over budget" in msg


def test_psn_vram_bytes_check_boundary_at_90_percent():
    """Request that lands exactly at 90% of total should be safe (not >)."""
    total = 24e9
    limit = total * 0.9
    allocated = 1e9
    required_gb = (limit - allocated) / 1e9
    node = PSN_VRAM_Bytes_Check()
    safe, msg = node.run(
        required_gb=required_gb,
        current_batch_size=1,
        allocated_bytes=allocated,
        reserved_bytes=0.0,
        total_bytes=total,
    )
    assert safe is True


def test_psn_vram_bytes_check_just_over_90_percent():
    """Request slightly over 90% should be unsafe."""
    total = 24e9
    limit = total * 0.9
    allocated = 1e9
    required_gb = (limit - allocated) / 1e9 + 0.001
    node = PSN_VRAM_Bytes_Check()
    safe, msg = node.run(
        required_gb=required_gb,
        current_batch_size=1,
        allocated_bytes=allocated,
        reserved_bytes=0.0,
        total_bytes=total,
    )
    assert safe is False
    assert "Over budget" in msg


def test_psn_vram_bytes_check_invalid_negative_required_gb():
    """Negative required_gb should be rejected."""
    safe, msg = _check_vram(
        required_gb=-1.0,
        current_batch_size=1,
        allocated_bytes=0.0,
        reserved_bytes=0.0,
        total_bytes=24e9,
    )
    assert safe is False
    assert "Invalid input" in msg


def test_psn_vram_bytes_check_invalid_zero_batch_size():
    """Batch size of 0 should be rejected."""
    safe, msg = _check_vram(
        required_gb=1.0,
        current_batch_size=0,
        allocated_bytes=0.0,
        reserved_bytes=0.0,
        total_bytes=24e9,
    )
    assert safe is False
    assert "Invalid input" in msg


def test_psn_vram_bytes_check_invalid_zero_total_bytes():
    """Total bytes of 0 should be rejected."""
    safe, msg = _check_vram(
        required_gb=1.0,
        current_batch_size=1,
        allocated_bytes=0.0,
        reserved_bytes=0.0,
        total_bytes=0.0,
    )
    assert safe is False
    assert "Invalid input" in msg


def test_psn_vram_bytes_check_allocated_exceeds_total():
    """Allocated bytes greater than total should be rejected."""
    safe, msg = _check_vram(
        required_gb=1.0,
        current_batch_size=1,
        allocated_bytes=30e9,
        reserved_bytes=0.0,
        total_bytes=24e9,
    )
    assert safe is False
    assert "Invalid input" in msg


def test_psn_vram_bytes_check_non_numeric_input():
    """Non-numeric required_gb should be rejected."""
    safe, msg = _check_vram(
        required_gb="1.0",
        current_batch_size=1,
        allocated_bytes=0.0,
        reserved_bytes=0.0,
        total_bytes=24e9,
    )
    assert safe is False
    assert "Invalid input" in msg


def test_psn_vram_bytes_check_node_mappings():
    """Node class and display name mappings should be present."""
    assert "PSN_VRAM_Bytes_Check" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_VRAM_Bytes_Check"] is PSN_VRAM_Bytes_Check
    assert "PSN_VRAM_Bytes_Check" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_VRAM_Bytes_Check"] == "VRAM Bytes Check (typed numbers, reads no GPU)"


def test_psn_vram_bytes_check_input_types_structure():
    """INPUT_TYPES should have the expected required fields."""
    it = PSN_VRAM_Bytes_Check.INPUT_TYPES()
    assert "required" in it
    req = it["required"]
    assert "required_gb" in req
    assert "current_batch_size" in req
    assert "allocated_bytes" in req
    assert "reserved_bytes" in req
    assert "total_bytes" in req
    assert PSN_VRAM_Bytes_Check.RETURN_TYPES == ("BOOLEAN", "STRING")
    assert PSN_VRAM_Bytes_Check.RETURN_NAMES == ("fits_budget", "message")
    assert PSN_VRAM_Bytes_Check.FUNCTION == "run"


def test_defaults_with_nothing_typed_do_not_report_fits():
    """allocated=0 and reserved=0 (the defaults) means no measurement: must not say it fits."""
    node = PSN_VRAM_Bytes_Check()
    fits, msg = node.run(required_gb=1.0, current_batch_size=1, allocated_bytes=0.0,
                         reserved_bytes=0.0, total_bytes=24e9)
    assert fits is False
    assert msg.startswith("No measurement given")
    assert "Safe" not in msg and "Fits" not in msg


def test_reserved_only_counts_as_a_measurement():
    fits, msg = PSN_VRAM_Bytes_Check().run(1.0, 1, 0.0, 3e9, 24e9)
    assert fits is True and msg.startswith("Fits")


def test_old_names_are_gone():
    assert list(NODE_CLASS_MAPPINGS) == ["PSN_VRAM_Bytes_Check"]
    assert "reads no GPU" in PSN_VRAM_Bytes_Check.DESCRIPTION
