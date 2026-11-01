"""Tests for PSN_Log_Entry_Formatter node."""

import json
import time

from psn_nodes.gen import psn_cv_runtracker as mod
from psn_nodes.gen.psn_cv_runtracker import (
    PSN_Log_Entry_Formatter,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _format_log_entry,
)


def test_node_class_mappings_registered():
    assert list(NODE_CLASS_MAPPINGS) == ["PSN_Log_Entry_Formatter"]
    assert NODE_CLASS_MAPPINGS["PSN_Log_Entry_Formatter"] is PSN_Log_Entry_Formatter
    assert "PSN_CV_RunTracker" not in NODE_CLASS_MAPPINGS
    assert "PSN_Log_Entry_Formatter" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_structure():
    input_types = PSN_Log_Entry_Formatter.INPUT_TYPES()
    assert input_types["required"]["node_id"][0] == "STRING"
    assert input_types["optional"]["input_hash"][0] == "STRING"


def test_run_returns_json_line_with_supplied_values_and_current_time():
    before = time.time()
    (log_entry,) = PSN_Log_Entry_Formatter().run(node_id="test_node", input_hash="abc123")
    after = time.time()
    parsed = json.loads(log_entry)
    assert parsed["node_id"] == "test_node"
    assert parsed["input_hash"] == "abc123"
    assert before <= parsed["timestamp"] <= after
    assert set(parsed) == {"node_id", "input_hash", "timestamp"}


def test_no_duration_and_no_invented_hash():
    (log_entry,) = PSN_Log_Entry_Formatter().run(node_id="n", input_hash="")
    parsed = json.loads(log_entry)
    assert "duration" not in parsed
    # an empty hash stays empty: the sha256 of "" is no longer substituted
    assert parsed["input_hash"] == ""
    assert not hasattr(mod, "_compute_hash")
    assert json.loads(PSN_Log_Entry_Formatter().run(node_id="n", input_hash=None)[0])["input_hash"] == ""


def test_run_with_non_string_node_id():
    parsed = json.loads(PSN_Log_Entry_Formatter().run(node_id=12345, input_hash="somehash")[0])
    assert parsed["node_id"] == "12345"


def test_run_with_empty_node_id():
    parsed = json.loads(PSN_Log_Entry_Formatter().run(node_id="", input_hash="somehash")[0])
    assert parsed["node_id"] == "unnamed_node"


def test_format_log_entry_structure():
    entry = _format_log_entry("my_node", "deadbeef", 1234567890.123)
    assert entry == '{"node_id":"my_node","input_hash":"deadbeef","timestamp":1234567890.123}'


def test_run_with_unicode_node_id():
    parsed = json.loads(PSN_Log_Entry_Formatter().run(node_id="node_日本語", input_hash="unicode_hash")[0])
    assert parsed["node_id"] == "node_日本語"


def test_return_types_and_names_and_description():
    assert PSN_Log_Entry_Formatter.RETURN_TYPES == ("STRING",)
    assert PSN_Log_Entry_Formatter.RETURN_NAMES == ("log_entry",)
    assert PSN_Log_Entry_Formatter.FUNCTION == "run"
    assert PSN_Log_Entry_Formatter.CATEGORY == "ParametricStudio/CV"
    assert "measures no execution time" in PSN_Log_Entry_Formatter.DESCRIPTION
