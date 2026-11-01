"""PSN_Telegram_Update_Parser: parses a pasted Telegram `getUpdates` JSON string.

This module never connects to Telegram. It opens no sockets, makes no network
calls, does not poll, takes no bot token, and does not touch the file system.
It provides:
  - allow-list parsing and membership checks for chat IDs,
  - command-prefix detection,
  - parsing of a JSON `getUpdates` payload (text you paste in) into a
    normalized message dict.

Fetching updates from Telegram is left to whatever produces the JSON text.
"""

import json
from typing import Any, Dict, List, Tuple

CAT = "ParametricStudio/Telegram"

# Allowed command prefixes that mark a message as a command.
COMMAND_PREFIXES = ("/", "!")


def psn_parse_allow_list(allowed_chat_ids: str) -> List[int]:
    """Parse a comma-separated string of chat IDs into a list of ints.

    Raises ValueError if any entry is not a valid integer.
    """
    if not isinstance(allowed_chat_ids, str):
        raise ValueError("allowed_chat_ids must be a string")
    ids: List[int] = []
    for part in allowed_chat_ids.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            raise ValueError(f"Invalid chat ID in allow-list: {part!r}")
    return ids


def psn_is_allowed(chat_id: int, allow_list: List[int]) -> bool:
    """Check whether chat_id is in the allow-list."""
    return chat_id in allow_list


def psn_is_command(text: str) -> bool:
    """Return True if the text starts with a defined command prefix."""
    if not isinstance(text, str) or not text:
        return False
    return any(text.startswith(p) for p in COMMAND_PREFIXES)


def psn_parse_updates_payload(payload: str) -> Dict[str, Any]:
    """Parse a JSON `getUpdates` response into a normalized message dict.

    Returns a dict with keys:
      chat_id (int), text_prompt (str), has_image (bool), is_command (bool)
    If no message is found, returns a dict with chat_id=-1 and empty fields.
    """
    if not isinstance(payload, str):
        raise ValueError("payload must be a JSON string")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Payload must be a JSON object")

    updates = data.get("result", [])
    if not isinstance(updates, list) or not updates:
        return {
            "chat_id": -1,
            "text_prompt": "",
            "has_image": False,
            "is_command": False,
        }

    # Take the first update that contains a message.
    for update in updates:
        if not isinstance(update, dict):
            continue
        msg = update.get("message")
        if not isinstance(msg, dict):
            continue
        chat = msg.get("chat", {})
        chat_id = chat.get("id", -1)
        text = msg.get("text", "")
        has_image = "photo" in msg
        return {
            "chat_id": int(chat_id),
            "text_prompt": text if isinstance(text, str) else "",
            "has_image": bool(has_image),
            "is_command": psn_is_command(text if isinstance(text, str) else ""),
        }

    return {
        "chat_id": -1,
        "text_prompt": "",
        "has_image": False,
        "is_command": False,
    }


class PSN_Telegram_Update_Parser:
    """Parse a pasted Telegram `getUpdates` JSON string.

    Takes the JSON text of a `getUpdates` response and an allow-list of chat
    IDs. Parses the first message in it and checks its chat id against the
    allow-list. It does not connect to Telegram or poll for updates.
    """

    DESCRIPTION = (
        "Parses a pasted Telegram getUpdates JSON string and checks the chat id against an allow-list; "
        "does not connect to Telegram."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "allowed_chat_ids": ("STRING", {"default": "", "multiline": False}),
                "updates_payload": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("INT", "STRING", "BOOLEAN", "BOOLEAN")
    RETURN_NAMES = ("chat_id", "text_prompt", "is_command", "is_allowed")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        allowed_chat_ids: str,
        updates_payload: str,
    ) -> Tuple[int, str, bool, bool]:
        # Parse allow-list
        allow_list = psn_parse_allow_list(allowed_chat_ids)

        # Parse the updates payload
        parsed = psn_parse_updates_payload(updates_payload)
        chat_id = parsed["chat_id"]
        text_prompt = parsed["text_prompt"]
        is_command = parsed["is_command"]

        # Check allow-list
        is_allowed = psn_is_allowed(chat_id, allow_list) if chat_id != -1 else False

        return (chat_id, text_prompt, is_command, is_allowed)


NODE_CLASS_MAPPINGS = {"PSN_Telegram_Update_Parser": PSN_Telegram_Update_Parser}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Telegram_Update_Parser": "PSN Telegram Update Parser (does not connect)"}
