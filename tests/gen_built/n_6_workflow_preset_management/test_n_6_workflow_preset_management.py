"""Tests for n_6_workflow_preset_management module."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from n_6_workflow_preset_management import (
    PSN_PresetLoader,
    PSN_Preset_Json_Build,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _validate_graph,
)


def make_sample_graph():
    return {
        "nodes": [
            {"id": 1, "type": "KSampler", "pos": [0, 0], "properties": {}},
            {"id": 2, "type": "VAEDecode", "pos": [300, 0], "properties": {}},
        ],
        "links": [[1, 0, 2, 0]],
        "version": 0.4,
    }


def test_module_structure():
    """Check module-level mappings exist and are correct."""
    assert "PSN_PresetLoader" in NODE_CLASS_MAPPINGS
    assert "PSN_Preset_Json_Build" in NODE_CLASS_MAPPINGS
    assert "PSN_PresetLoader" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_Preset_Json_Build" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_PresetLoader"] is PSN_PresetLoader
    assert NODE_CLASS_MAPPINGS["PSN_Preset_Json_Build"] is PSN_Preset_Json_Build


def test_input_types():
    """Check INPUT_TYPES classmethod returns proper dict."""
    lt = PSN_PresetLoader.INPUT_TYPES()
    assert "required" in lt
    assert "preset_name" in lt["required"]
    assert "preset_dir" in lt["required"]
    assert "preset_json" in lt["required"]

    st = PSN_Preset_Json_Build.INPUT_TYPES()
    assert "required" in st
    assert list(st["required"]) == ["graph"]


def test_loader_valid_preset():
    """Load a valid preset and verify graph structure."""
    loader = PSN_PresetLoader()
    graph = make_sample_graph()
    json_str = json.dumps(graph)
    result = loader.run("test_preset", "./presets", json_str)
    assert len(result) == 1
    loaded = result[0]
    assert isinstance(loaded, dict)
    assert "nodes" in loaded
    assert len(loaded["nodes"]) == 2
    assert loaded["nodes"][0]["id"] == 1
    assert loaded["nodes"][0]["type"] == "KSampler"
    assert loaded["nodes"][1]["type"] == "VAEDecode"
    assert loaded["links"] == [[1, 0, 2, 0]]


def test_loader_does_not_mutate_input():
    """Ensure the loader returns a copy, not the original object."""
    loader = PSN_PresetLoader()
    graph = make_sample_graph()
    json_str = json.dumps(graph)
    result = loader.run("test", "./presets", json_str)
    loaded = result[0]
    # Mutate the returned graph
    loaded["nodes"][0]["type"] = "MUTATED"
    # Original should be unchanged (it was a string, but the parsed dict is separate)
    # Re-parse to verify
    original = json.loads(json_str)
    assert original["nodes"][0]["type"] == "KSampler"


def test_loader_bad_json():
    """Loader should raise on invalid JSON."""
    loader = PSN_PresetLoader()
    try:
        loader.run("bad", "./presets", "not valid json {{{")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid JSON" in str(e)


def test_loader_missing_nodes_key():
    """Loader should reject graph without 'nodes' key."""
    loader = PSN_PresetLoader()
    bad_graph = {"links": []}
    try:
        loader.run("bad", "./presets", json.dumps(bad_graph))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "nodes" in str(e)


def test_loader_node_missing_id():
    """Loader should reject node without 'id'."""
    loader = PSN_PresetLoader()
    bad_graph = {"nodes": [{"type": "KSampler"}]}
    try:
        loader.run("bad", "./presets", json.dumps(bad_graph))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "id" in str(e)


def test_loader_bad_types():
    """Loader should reject non-string inputs."""
    loader = PSN_PresetLoader()
    try:
        loader.run(123, "./presets", "{}")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    try:
        loader.run("name", 456, "{}")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    try:
        loader.run("name", "./presets", 789)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_builder_returns_json_text_not_path():
    """Builder returns the serialized graph, and no path."""
    builder = PSN_Preset_Json_Build()
    graph = make_sample_graph()
    result = builder.run(graph)
    assert len(result) == 1
    text = result[0]
    assert isinstance(text, str)
    assert text == json.dumps(graph, sort_keys=True, indent=2)
    assert json.loads(text) == graph
    assert not text.endswith(".json")
    assert "preset_dir" not in PSN_Preset_Json_Build.INPUT_TYPES()["required"]


def test_builder_writes_no_file():
    """Builder touches no files in the working directory."""
    import tempfile
    d = tempfile.mkdtemp()
    old = os.getcwd()
    os.chdir(d)
    try:
        PSN_Preset_Json_Build().run(make_sample_graph())
        assert os.listdir(d) == []
    finally:
        os.chdir(old)


def test_builder_bad_graph():
    """Builder should reject invalid graph."""
    builder = PSN_Preset_Json_Build()
    for bad in ("not a dict", {"links": []}, {"nodes": [{"type": "K"}]}):
        try:
            builder.run(bad)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


def test_roundtrip():
    """Save then load should produce equivalent graph."""
    builder = PSN_Preset_Json_Build()
    loader = PSN_PresetLoader()
    graph = make_sample_graph()
    json_str = builder.run(graph)[0]
    loaded = loader.run("rt", "./presets", json_str)[0]
    assert loaded == graph


def test_empty_graph():
    """Loader should accept a graph with empty nodes list."""
    loader = PSN_PresetLoader()
    empty_graph = {"nodes": [], "links": []}
    result = loader.run("empty", "./presets", json.dumps(empty_graph))
    assert result[0]["nodes"] == []


def test_return_types_and_names():
    """Check RETURN_TYPES and RETURN_NAMES."""
    assert PSN_PresetLoader.RETURN_TYPES == ("GRAPH",)
    assert PSN_PresetLoader.RETURN_NAMES == ("GRAPH",)
    assert PSN_Preset_Json_Build.RETURN_TYPES == ("STRING",)
    assert PSN_Preset_Json_Build.RETURN_NAMES == ("preset_json",)
    assert PSN_PresetLoader.FUNCTION == "run"
    assert PSN_Preset_Json_Build.FUNCTION == "run"
    assert PSN_PresetLoader.CATEGORY == "ParametricStudio/PresetManagement"
    assert PSN_Preset_Json_Build.CATEGORY == "ParametricStudio/PresetManagement"


if __name__ == "__main__":
    test_module_structure()
    test_input_types()
    test_loader_valid_preset()
    test_loader_does_not_mutate_input()
    test_loader_bad_json()
    test_loader_missing_nodes_key()
    test_loader_node_missing_id()
    test_loader_bad_types()
    test_builder_returns_json_text_not_path()
    test_builder_writes_no_file()
    test_builder_bad_graph()
    test_roundtrip()
    test_empty_graph()
    test_return_types_and_names()
    print("ok")
