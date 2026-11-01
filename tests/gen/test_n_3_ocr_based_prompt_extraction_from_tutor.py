"""Tests for PSN OCR-based prompt extraction (pure-logic core)."""

import json

from psn_nodes.gen import n_3_ocr_based_prompt_extraction_from_tutor as mod
from psn_nodes.gen.n_3_ocr_based_prompt_extraction_from_tutor import (
    PSN_TextLinesToRegions,
    PSN_Prompt_Cleaner,
    _strip_ui,
    _split_sections,
    _build_structured,
)


def test_lines_to_regions_splits_lines():
    node = PSN_TextLinesToRegions()
    raw, recs = node.run("a cat on a mat\n\n  negative: blur  ")
    assert raw == "a cat on a mat\n\n  negative: blur  "
    parsed = json.loads(recs)
    assert parsed["lines"] == [
        {"id": 0, "text": "a cat on a mat"},
        {"id": 1, "text": "negative: blur"},
    ]


def test_lines_to_regions_has_no_fabricated_fields():
    node = PSN_TextLinesToRegions()
    _, recs = node.run("hello\nworld")
    for rec in json.loads(recs)["lines"]:
        assert set(rec) == {"id", "text"}
    assert "confidence" not in recs and "box" not in recs
    assert "ocr_engine" not in PSN_TextLinesToRegions.INPUT_TYPES()["required"]
    assert not hasattr(mod, "OCR_ENGINES")
    assert "PSN_Tutorial_OCR_Extractor" not in mod.NODE_CLASS_MAPPINGS
    assert "PSN_TextLinesToRegions" in mod.NODE_CLASS_MAPPINGS
    assert "no OCR" in PSN_TextLinesToRegions.DESCRIPTION


def test_lines_to_regions_handles_non_string():
    node = PSN_TextLinesToRegions()
    raw, recs = node.run(12345)
    assert raw == ""
    assert json.loads(recs)["lines"] == []


def test_cleaner_removes_ui_elements():
    node = PSN_Prompt_Cleaner()
    raw = "Submit\na beautiful sunset\nCancel\nnegative: blur\nOK"
    cleaned, structured = node.run(raw, True, True)
    assert "Submit" not in cleaned
    assert "Cancel" not in cleaned
    assert "OK" not in cleaned
    assert "a beautiful sunset" in cleaned
    doc = json.loads(structured)
    assert doc["prompt"] == "a beautiful sunset"
    assert doc["negative_prompt"] == "blur"


def test_cleaner_keeps_ui_when_disabled():
    node = PSN_Prompt_Cleaner()
    raw = "Submit\na beautiful sunset"
    cleaned, _ = node.run(raw, False, True)
    assert "Submit" in cleaned


def test_cleaner_splits_sections_correctly():
    node = PSN_Prompt_Cleaner()
    raw = ("a red car\n"
           "negative prompt: blur, low quality\n"
           "settings: steps 30, cfg 7")
    cleaned, structured = node.run(raw, True, True)
    doc = json.loads(structured)
    assert doc["prompt"] == "a red car"
    assert "blur" in doc["negative_prompt"]
    assert "steps 30" in doc["settings"]


def test_cleaner_no_format_still_valid_json():
    node = PSN_Prompt_Cleaner()
    raw = "a dog"
    cleaned, structured = node.run(raw, True, False)
    doc = json.loads(structured)
    assert doc["prompt"] == "a dog"


def test_cleaner_handles_empty_and_bad_input():
    node = PSN_Prompt_Cleaner()
    cleaned, structured = node.run("", True, True)
    assert cleaned == ""
    doc = json.loads(structured)
    assert doc["prompt"] == ""
    cleaned2, structured2 = node.run(None, True, True)
    assert cleaned2 == ""
    json.loads(structured2)


def test_strip_ui_removes_embedded_tokens():
    assert _strip_ui("Submit a form") == "a form"
    assert _strip_ui("Cancel") == ""


def test_build_structured_roundtrip():
    doc = json.loads(_build_structured("p", "n", "s"))
    assert doc == {"prompt": "p", "negative_prompt": "n", "settings": "s"}
