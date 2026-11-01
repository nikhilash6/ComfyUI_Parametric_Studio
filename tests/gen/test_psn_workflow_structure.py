"""Tests for PSN_WorkflowBundle node (bundles three inputs; checks only presence)."""

import pytest
from psn_nodes.gen.psn_workflow_structure import PSN_WorkflowBundle


def test_valid_structure_returns_organized_dict():
    """Test that valid inputs produce a correctly organized dictionary."""
    node = PSN_WorkflowBundle()
    loader_out = {"model": "test_model"}
    controller_cfg = {"steps": 20, "cfg": 7.5}
    sampler_in = "prompt_text"

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is True
    assert structured_data["loader"] == loader_out
    assert structured_data["controller"] == controller_cfg
    assert structured_data["sampler"] == sampler_in


def test_invalid_controller_settings_returns_false():
    """Test that non-dict controller_settings results in validation failure."""
    node = PSN_WorkflowBundle()
    loader_out = {"model": "test_model"}
    controller_cfg = "not_a_dict"  # Invalid: should be a dict
    sampler_in = "prompt_text"

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is False
    assert structured_data == {}


def test_none_loader_output_returns_false():
    """Test that None loader_output results in validation failure."""
    node = PSN_WorkflowBundle()
    loader_out = None  # Invalid: should not be None
    controller_cfg = {"steps": 20}
    sampler_in = "prompt_text"

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is False
    assert structured_data == {}


def test_none_sampler_input_returns_false():
    """Test that None sampler_input results in validation failure."""
    node = PSN_WorkflowBundle()
    loader_out = {"model": "test_model"}
    controller_cfg = {"steps": 20}
    sampler_in = None  # Invalid: should not be None

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is False
    assert structured_data == {}


def test_log_structure_includes_summary():
    """Test that log_structure=True includes a structure summary in the output."""
    node = PSN_WorkflowBundle()
    loader_out = {"model": "test_model"}
    controller_cfg = {"steps": 20, "cfg": 7.5}
    sampler_in = "prompt_text"

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in, log_structure=True)

    assert validation_status is True
    assert "structure_summary" in structured_data
    # Verify the summary is valid JSON
    import json
    summary = json.loads(structured_data["structure_summary"])
    assert summary["loader_type"] == "dict"
    assert set(summary["controller_keys"]) == {"steps", "cfg"}
    assert summary["sampler_type"] == "str"


def test_empty_controller_settings_is_valid():
    """Test that an empty dict for controller_settings is still valid."""
    node = PSN_WorkflowBundle()
    loader_out = {"model": "test_model"}
    controller_cfg = {}  # Empty dict is still a valid dict
    sampler_in = "prompt_text"

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is True
    assert structured_data["controller"] == {}


def test_complex_nested_data_preserved():
    """Test that complex nested data structures are preserved correctly."""
    node = PSN_WorkflowBundle()
    loader_out = {"model": "test", "config": {"nested": {"deep": [1, 2, 3]}}}
    controller_cfg = {"steps": 20, "advanced": {"param": True}}
    sampler_in = {"prompt": "test", "negative": "bad"}

    structured_data, validation_status = node.run(loader_out, controller_cfg, sampler_in)

    assert validation_status is True
    assert structured_data["loader"] == loader_out
    assert structured_data["controller"] == controller_cfg
    assert structured_data["sampler"] == sampler_in


def test_any_loader_and_sampler_values_pass_so_no_structure_is_enforced():
    """Only presence is checked: a loader that is a plain string and a sampler that is a number bundle fine."""
    data, ok = PSN_WorkflowBundle().run("not a loader at all", {}, 42)
    assert ok is True
    assert data == {"loader": "not a loader at all", "controller": {}, "sampler": 42}


def test_falsy_but_present_values_count_as_present():
    data, ok = PSN_WorkflowBundle().run(0, {}, "")
    assert ok is True and data["loader"] == 0 and data["sampler"] == ""


def test_renamed_with_honest_output_name_and_description():
    import psn_nodes.gen.psn_workflow_structure as m
    assert list(m.NODE_CLASS_MAPPINGS) == ["PSN_WorkflowBundle"]
    assert PSN_WorkflowBundle.RETURN_NAMES == ("bundled_data", "inputs_present")
    assert "only means" in PSN_WorkflowBundle.DESCRIPTION
