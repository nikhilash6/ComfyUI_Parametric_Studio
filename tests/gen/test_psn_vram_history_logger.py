"""Tests for PSN_VRAM_Samples_Formatter."""

import json
import pytest
from psn_nodes.gen.psn_vram_history_logger import (
    PSN_VRAM_Samples_Formatter,
    VRAMSampleSeries,
    _validate_inputs,
)


def test_valid_inputs_produce_history():
    node = PSN_VRAM_Samples_Formatter()
    samples = [100.0, 200.0, 300.0]
    history, history_json = node.run("test_run", 100, samples)
    assert len(history) == 3
    assert history[0]["vram_mb"] == 100.0
    assert history[1]["vram_mb"] == 200.0
    assert history[2]["vram_mb"] == 300.0
    # evenly spaced index offsets, not clock times
    assert [h["offset_ms"] for h in history] == [0.0, 100.0, 200.0]
    parsed = json.loads(history_json)
    assert parsed["run_id"] == "test_run"
    assert parsed["interval_ms"] == 100
    assert len(parsed["samples"]) == 3


def test_empty_samples_returns_empty_history():
    node = PSN_VRAM_Samples_Formatter()
    history, history_json = node.run("test_run", 100, [])
    assert history == []
    parsed = json.loads(history_json)
    assert parsed["samples"] == []


def test_invalid_run_id_empty_string():
    node = PSN_VRAM_Samples_Formatter()
    history, history_json = node.run("", 100, [100.0])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_run_id_non_string():
    node = PSN_VRAM_Samples_Formatter()
    history, history_json = node.run(123, 100, [100.0])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_interval_ms_zero():
    node = PSN_VRAM_Samples_Formatter()
    history, history_json = node.run("test_run", 0, [100.0])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_interval_ms_negative():
    node = PSN_VRAM_Samples_Formatter()
    history, history_json = node.run("test_run", -5, [100.0])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_samples_non_list():
    node = PSN_VRAM_Samples_Formatter()
    history, history_json = node.run("test_run", 100, "not_a_list")
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_samples_negative_value():
    node = PSN_VRAM_Samples_Formatter()
    history, history_json = node.run("test_run", 100, [100.0, -5.0])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_invalid_samples_non_numeric():
    node = PSN_VRAM_Samples_Formatter()
    history, history_json = node.run("test_run", 100, [100.0, "bad"])
    assert history == []
    parsed = json.loads(history_json)
    assert "error" in parsed


def test_logger_rejects_samples_within_interval():
    logger = VRAMSampleSeries("test", 100)
    assert logger.add_sample(100.0, offset_ms=0.0) is True
    assert logger.add_sample(200.0, offset_ms=50.0) is False  # within 100ms
    assert logger.add_sample(300.0, offset_ms=100.0) is True  # exactly at interval
    assert len(logger.get_history()) == 2


def test_logger_rejects_negative_vram():
    logger = VRAMSampleSeries("test", 100)
    with pytest.raises(ValueError):
        logger.add_sample(-1.0, offset_ms=0.0)


def test_logger_rejects_negative_offset():
    logger = VRAMSampleSeries("test", 100)
    with pytest.raises(ValueError):
        logger.add_sample(100.0, offset_ms=-1.0)


def test_history_json_structure():
    node = PSN_VRAM_Samples_Formatter()
    samples = [50.0, 150.0]
    history, history_json = node.run("json_test", 200, samples)
    parsed = json.loads(history_json)
    assert "run_id" in parsed
    assert "interval_ms" in parsed
    assert "samples" in parsed
    assert parsed["run_id"] == "json_test"
    assert parsed["interval_ms"] == 200
    assert len(parsed["samples"]) == 2
    for s in parsed["samples"]:
        assert "offset_ms" in s
        assert "vram_mb" in s


def test_no_clock_timestamps_are_produced(monkeypatch):
    """Output carries index offsets only: no wall-clock reading is made and no 'timestamp_ms' key exists."""
    import time
    import psn_nodes.gen.psn_vram_history_logger as m
    def boom(*a, **k):
        raise AssertionError("clock read")
    monkeypatch.setattr(time, "time", boom)
    history, history_json = PSN_VRAM_Samples_Formatter().run("r", 250, [10.0, 20.0])
    assert [h["offset_ms"] for h in history] == [0.0, 250.0]
    assert "timestamp_ms" not in history_json
    assert PSN_VRAM_Samples_Formatter.RETURN_NAMES == ("samples_data", "samples_json")
    assert list(m.NODE_CLASS_MAPPINGS) == ["PSN_VRAM_Samples_Formatter"]
    assert "does not sample the GPU" in PSN_VRAM_Samples_Formatter.DESCRIPTION
