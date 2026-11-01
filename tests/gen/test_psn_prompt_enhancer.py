"""Tests for the PSN_Prompt_Reply_Parser pure-logic core."""

import pytest

import psn_nodes.gen.psn_prompt_enhancer as mod
from psn_nodes.gen.psn_prompt_enhancer import (
    PSN_Prompt_Reply_Parser,
    parse_llm_response,
)


def test_parse_splits_positive_and_negative():
    resp = "Positive: a cat on a windowsill, soft light\nNegative: blurry, low quality"
    pos, neg, status = parse_llm_response(resp, "cat")
    assert pos == "a cat on a windowsill, soft light"
    assert neg == "blurry, low quality"
    assert status.startswith("parsed")


def test_parse_tolerates_case_and_whitespace():
    resp = "  positive:   a dog running  \n   NEGATIVE:   extra limbs  "
    pos, neg, _ = parse_llm_response(resp, "dog")
    assert pos == "a dog running"
    assert neg == "extra limbs"


def test_parse_empty_reply_returns_raw_prompt_and_says_so_with_empty_negative():
    pos, neg, status = parse_llm_response("", "a red car")
    assert pos == "a red car"
    assert neg == ""           # no invented negative prompt
    assert "no reply given" in status and "unchanged" in status


def test_parse_missing_negative_is_empty_not_invented():
    pos, neg, status = parse_llm_response("Positive: a mountain at dawn", "mountain")
    assert pos == "a mountain at dawn"
    assert neg == ""
    assert "no Negative: line" in status


def test_parse_missing_positive_falls_back_to_raw_prompt_and_says_so():
    pos, neg, status = parse_llm_response("Negative: blurry, distorted", "a bird")
    assert pos == "a bird"
    assert neg == "blurry, distorted"
    assert "no Positive: line" in status and "unchanged" in status


def test_run_returns_parsed_outputs():
    pos, neg, status = PSN_Prompt_Reply_Parser().run("cat", "Positive: a cat, detailed\nNegative: blurry")
    assert (pos, neg) == ("a cat, detailed", "blurry")
    assert status.startswith("parsed")


def test_run_with_empty_reply_does_not_pretend_to_enhance():
    pos, neg, status = PSN_Prompt_Reply_Parser().run("a fox", "")
    assert pos == "a fox" and neg == ""
    assert "no reply given" in status


def test_renamed_and_unused_inputs_and_constant_negative_removed():
    assert list(mod.NODE_CLASS_MAPPINGS) == ["PSN_Prompt_Reply_Parser"]
    assert set(PSN_Prompt_Reply_Parser.INPUT_TYPES()["required"]) == {"raw_prompt", "llm_response"}
    assert PSN_Prompt_Reply_Parser.RETURN_NAMES == ("positive_prompt", "negative_prompt", "parse_status")
    assert "enhances nothing" in PSN_Prompt_Reply_Parser.DESCRIPTION
    for gone in ("build_system_prompt", "_FALLBACK_NEGATIVE", "_MODEL_GUIDANCE", "PSN_PromptEnhancer"):
        assert not hasattr(mod, gone)
