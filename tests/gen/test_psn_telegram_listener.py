"""Tests for psn_nodes.gen.psn_telegram_listener."""

import json
import pytest

from psn_nodes.gen.psn_telegram_listener import (
    PSN_Telegram_Update_Parser,
    psn_parse_allow_list,
    psn_is_allowed,
    psn_is_command,
    psn_parse_updates_payload,
)


def test_psn_parse_allow_list_valid():
    ids = psn_parse_allow_list("123, 456,789")
    assert ids == [123, 456, 789]


def test_psn_parse_allow_list_invalid():
    with pytest.raises(ValueError):
        psn_parse_allow_list("123, abc, 456")


def test_psn_is_command_variants():
    assert psn_is_command("/start") is True
    assert psn_is_command("!help") is True
    assert psn_is_command("hello") is False
    assert psn_is_command("") is False
    assert psn_is_command(None) is False


def test_psn_parse_updates_payload_with_message():
    payload = json.dumps({
        "ok": True,
        "result": [
            {
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "/start",
                },
            }
        ],
    })
    parsed = psn_parse_updates_payload(payload)
    assert parsed["chat_id"] == 12345
    assert parsed["text_prompt"] == "/start"
    assert parsed["is_command"] is True
    assert parsed["has_image"] is False


def test_psn_parse_updates_payload_with_image():
    payload = json.dumps({
        "ok": True,
        "result": [
            {
                "update_id": 2,
                "message": {
                    "message_id": 2,
                    "chat": {"id": 67890, "type": "private"},
                    "photo": [{"file_id": "abc"}],
                    "caption": "a photo",
                },
            }
        ],
    })
    parsed = psn_parse_updates_payload(payload)
    assert parsed["chat_id"] == 67890
    assert parsed["has_image"] is True
    assert parsed["text_prompt"] == ""


def test_psn_parse_updates_payload_empty():
    parsed = psn_parse_updates_payload(json.dumps({"ok": True, "result": []}))
    assert parsed["chat_id"] == -1
    assert parsed["text_prompt"] == ""
    assert parsed["is_command"] is False


def test_psn_parse_updates_payload_invalid_json():
    with pytest.raises(ValueError):
        psn_parse_updates_payload("not json")


def _payload(chat_id, text="hello"):
    return json.dumps({"ok": True, "result": [{"update_id": 1, "message": {"chat": {"id": chat_id}, "text": text}}]})


def test_psn_node_run_allowed_chat():
    node = PSN_Telegram_Update_Parser()
    chat_id, text, is_cmd, is_allowed = node.run(allowed_chat_ids="100,200", updates_payload=_payload(100))
    assert chat_id == 100
    assert text == "hello"
    assert is_cmd is False
    assert is_allowed is True


def test_psn_node_run_disallowed_chat():
    node = PSN_Telegram_Update_Parser()
    chat_id, text, is_cmd, is_allowed = node.run(allowed_chat_ids="100,200", updates_payload=_payload(999))
    assert chat_id == 999
    assert is_allowed is False


def test_psn_node_run_command_text():
    _, text, is_cmd, _ = PSN_Telegram_Update_Parser().run("1", _payload(1, "/start now"))
    assert text == "/start now" and is_cmd is True


def test_psn_node_run_no_message_is_never_allowed():
    out = PSN_Telegram_Update_Parser().run("1,-1", json.dumps({"ok": True, "result": []}))
    assert out == (-1, "", False, False)


def test_psn_node_run_bad_allow_list():
    node = PSN_Telegram_Update_Parser()
    with pytest.raises(ValueError):
        node.run(allowed_chat_ids="1,abc", updates_payload=json.dumps({"ok": True, "result": []}))


def test_node_is_renamed_and_has_no_connection_inputs_or_token_output():
    import psn_nodes.gen.psn_telegram_listener as m
    assert list(m.NODE_CLASS_MAPPINGS) == ["PSN_Telegram_Update_Parser"]
    cls = m.PSN_Telegram_Update_Parser
    assert set(cls.INPUT_TYPES()["required"]) == {"allowed_chat_ids", "updates_payload"}
    assert cls.RETURN_NAMES == ("chat_id", "text_prompt", "is_command", "is_allowed")
    assert "does not connect" in cls.DESCRIPTION
    assert not hasattr(m, "psn_redact_token") and not hasattr(m, "PSN_Telegram_Listener")
