"""Tests for psn_nodes.gen.psn_gemini_prompt_crafter (PSN_Gemini_Response_Parser: parses pasted JSON, no network)."""

import json

from psn_nodes.gen import psn_gemini_prompt_crafter as mod
from psn_nodes.gen.psn_gemini_prompt_crafter import (
    PSN_Gemini_Response_Parser,
    psn_parse_response,
)


def _make_response(text="A vivid photorealistic portrait of a cat.", tokens=42):
    return json.dumps({
        "candidates": [
            {"content": {"parts": [{"text": text}]}}
        ],
        "usage_metadata": {"total_token_count": tokens},
    })


def test_psn_parse_response_success():
    text, tokens, err = psn_parse_response(_make_response("hello world", 17))
    assert err == ""
    assert text == "hello world"
    assert tokens == 17


def test_psn_parse_response_strips_whitespace_and_defaults_tokens_to_zero():
    body = json.dumps({"candidates": [{"content": {"parts": [{"text": "  hi  "}]}}]})
    assert psn_parse_response(body) == ("hi", 0, "")


def test_psn_parse_response_takes_first_candidate_with_text():
    body = json.dumps({"candidates": [{"content": {"parts": []}}, {"content": {"parts": [{"text": "second"}]}}],
                       "usage_metadata": {"total_token_count": 5}})
    assert psn_parse_response(body) == ("second", 5, "")


def test_psn_parse_response_bad_inputs():
    text, tokens, err = psn_parse_response("")
    assert err != "" and text == "" and tokens == 0
    text, tokens, err = psn_parse_response("not json")
    assert "valid JSON" in err
    text, tokens, err = psn_parse_response("[1]")
    assert "object" in err
    text, tokens, err = psn_parse_response(json.dumps({"candidates": []}))
    assert "candidates" in err
    text, tokens, err = psn_parse_response(json.dumps({"candidates": [{"content": {"parts": []}}]}))
    assert "no text" in err


def test_psn_parse_response_truncates_oversize_text_and_ignores_bad_token_count():
    body = json.dumps({"candidates": [{"content": {"parts": [{"text": "x" * 20000}]}}],
                       "usage_metadata": {"total_token_count": True}})
    text, tokens, err = psn_parse_response(body)
    assert len(text) == 16000 and tokens == 0 and err == ""


def test_node_run_happy_path():
    text, tokens = PSN_Gemini_Response_Parser().run(response_text=_make_response("A cinematic anime scene of a dragon.", 55))
    assert text == "A cinematic anime scene of a dragon."
    assert tokens == 55


def test_node_run_error_cases():
    node = PSN_Gemini_Response_Parser()
    text, tokens = node.run(response_text="garbage")
    assert text.startswith("<error:") and "JSON" in text and tokens == 0
    text, tokens = node.run()
    assert text.startswith("<error:") and tokens == 0


def test_no_api_key_style_or_request_builder_remain():
    inputs = PSN_Gemini_Response_Parser.INPUT_TYPES()
    assert list(inputs["required"]) == ["response_text"] and "optional" not in inputs
    assert PSN_Gemini_Response_Parser.RETURN_NAMES == ("parsed_text", "token_count")
    for gone in ("psn_redact_api_key", "psn_build_request_payload", "psn_validate_style", "PSN_Gemini_Prompt_Crafter"):
        assert not hasattr(mod, gone), gone
    assert list(mod.NODE_CLASS_MAPPINGS) == ["PSN_Gemini_Response_Parser"]
    assert "no API call" in PSN_Gemini_Response_Parser.DESCRIPTION
