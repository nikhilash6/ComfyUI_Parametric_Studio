"""Tests for n_7_visual_model_selection_ui_backend."""

import json
import os
import tempfile

import n_7_visual_model_selection_ui_backend as mod
from n_7_visual_model_selection_ui_backend import (
    PSN_VisualModelSelector,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _build_card,
    _find_cover,
    _clean_metadata,
)


def test_module_mappings():
    assert "PSN_VisualModelSelector" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_VisualModelSelector"] is PSN_VisualModelSelector
    assert "PSN_VisualModelSelector" in NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_VisualModelSelector"], str)


def test_input_types_shape():
    spec = PSN_VisualModelSelector.INPUT_TYPES()
    assert "required" in spec
    assert "model_list" in spec["required"]
    assert "limit" in spec["required"]
    limit_meta = spec["required"]["limit"]
    assert limit_meta[0] == "INT"
    assert limit_meta[1]["min"] == 1
    assert limit_meta[1]["max"] >= 1
    assert PSN_VisualModelSelector.RETURN_TYPES == ("MODEL_CARDS",)
    assert PSN_VisualModelSelector.FUNCTION == "run"
    assert PSN_VisualModelSelector.CATEGORY.startswith("ParametricStudio/")


def _mk(root, name, files):
    d = os.path.join(root, name)
    os.makedirs(d)
    for f in files:
        with open(os.path.join(d, f), "wb") as fh:
            fh.write(b"x")
    return d


def test_run_basic_cards():
    node = PSN_VisualModelSelector()
    with tempfile.TemporaryDirectory() as root:
        alpha = _mk(root, "alpha", ["cover.jpg"])
        beta = _mk(root, "beta", ["preview.png"])
        gamma = _mk(root, "gamma", [])
        model_list = [
            {"name": "alpha", "dir": alpha, "metadata": {"size": 100}},
            {"name": "beta", "dir": beta, "metadata": {"size": 200}},
            {"name": "gamma", "dir": gamma, "metadata": {}},
        ]
        (cards,) = node.run(model_list, limit=10)
        assert len(cards) == 3
        assert cards[0]["name"] == "alpha"
        assert cards[0]["cover_image_path"] == os.path.join(alpha, "cover.jpg")
        assert cards[0]["metadata"] == {"size": 100}
        assert cards[1]["name"] == "beta"
        # no cover.jpg: falls through to the preview.png that does exist
        assert cards[1]["cover_image_path"] == os.path.join(beta, "preview.png")
        assert cards[2]["name"] == "gamma"
        # directory exists but has no cover file: empty, not an invented path
        assert cards[2]["cover_image_path"] == ""


def test_cover_prefers_cover_jpg_over_preview():
    with tempfile.TemporaryDirectory() as root:
        d = _mk(root, "both", ["preview.png", "cover.jpg"])
        assert _find_cover(d) == os.path.join(d, "cover.jpg")


def test_missing_directory_gives_empty_path():
    node = PSN_VisualModelSelector()
    (cards,) = node.run([{"name": "ghost", "dir": "/nonexistent/ghost-dir"}], limit=5)
    assert cards[0]["cover_image_path"] == ""
    # a directory named like a cover file is not a file
    with tempfile.TemporaryDirectory() as root:
        d = os.path.join(root, "m")
        os.makedirs(os.path.join(d, "cover.jpg"))
        assert _find_cover(d) is None


def test_default_cover_constant_removed():
    assert not hasattr(mod, "DEFAULT_PLACEHOLDER")


def test_run_limit_truncates():
    node = PSN_VisualModelSelector()
    model_list = [{"name": "m%d" % i, "dir": "/m%d" % i} for i in range(10)]
    (cards,) = node.run(model_list, limit=3)
    assert len(cards) == 3
    assert [c["name"] for c in cards] == ["m0", "m1", "m2"]


def test_run_empty_and_none():
    node = PSN_VisualModelSelector()
    (cards,) = node.run([], limit=5)
    assert cards == []
    (cards,) = node.run(None, limit=5)
    assert cards == []


def test_run_string_entries_and_missing_dir():
    node = PSN_VisualModelSelector()
    model_list = ["just-a-name", {"name": "no-dir"}, {"name": "  "}]
    (cards,) = node.run(model_list, limit=10)
    assert len(cards) == 3
    assert cards[0]["name"] == "just-a-name"
    assert cards[0]["cover_image_path"] == ""
    assert cards[1]["name"] == "no-dir"
    assert cards[1]["cover_image_path"] == ""
    # blank name falls back to model-<index>
    assert cards[2]["name"] == "model-2"
    assert cards[2]["cover_image_path"] == ""


def test_bad_inputs_raise():
    node = PSN_VisualModelSelector()
    try:
        node.run("not-a-list", limit=5)
        raise AssertionError("expected TypeError for non-list model_list")
    except TypeError:
        pass
    try:
        node.run([], limit=0)
        raise AssertionError("expected ValueError for limit < 1")
    except ValueError:
        pass
    try:
        node.run([], limit="5")
        raise AssertionError("expected TypeError for non-int limit")
    except TypeError:
        pass
    try:
        node.run([], limit=True)
        raise AssertionError("expected TypeError for bool limit")
    except TypeError:
        pass


def test_metadata_sanitisation():
    # non-serialisable values are repr'd
    meta = _clean_metadata({"a": 1, "b": object()})
    assert meta["a"] == 1
    assert isinstance(meta["b"], str)
    # None -> {}
    assert _clean_metadata(None) == {}
    # non-dict -> {"raw": ...}
    out = _clean_metadata("hello")
    assert out == {"raw": "'hello'"}
    # keys are coerced to str
    out2 = _clean_metadata({1: "x"})
    assert "1" in out2


def test_find_cover_edge_cases():
    assert _find_cover(None) is None
    assert _find_cover("") is None
    assert _find_cover("   ") is None
    assert _find_cover(123) is None
    assert _find_cover("/models/foo") is None  # not on disk
    with tempfile.TemporaryDirectory() as root:
        d = _mk(root, "foo", ["cover.jpg"])
        assert _find_cover(d + "/") == os.path.join(d + "/", "cover.jpg")


def test_build_card_non_dict_entry():
    card = _build_card(42, 7)
    assert card["name"] == "model-7"
    assert card["cover_image_path"] == ""
    assert "raw" in card["metadata"]


def test_cards_are_json_serialisable():
    node = PSN_VisualModelSelector()
    model_list = [
        {"name": "a", "dir": "/a", "metadata": {"k": [1, 2, 3]}},
        {"name": "b", "dir": "/b", "metadata": {"nested": {"x": True}}},
    ]
    (cards,) = node.run(model_list, limit=10)
    s = json.dumps(cards)
    assert isinstance(s, str)
    assert len(s) > 0


if __name__ == "__main__":
    test_module_mappings()
    test_input_types_shape()
    test_run_basic_cards()
    test_cover_prefers_cover_jpg_over_preview()
    test_missing_directory_gives_empty_path()
    test_default_cover_constant_removed()
    test_run_limit_truncates()
    test_run_empty_and_none()
    test_run_string_entries_and_missing_dir()
    test_bad_inputs_raise()
    test_metadata_sanitisation()
    test_find_cover_edge_cases()
    test_build_card_non_dict_entry()
    test_cards_are_json_serialisable()
    print("ok")
