"""PSN_Memory_Store: in-process memory store for agent preferences.

Keeps an in-memory dictionary keyed by (agent_id, key). It does no file I/O,
OS access or network calls, so the store lives only as long as the ComfyUI
process. The output is a MEMORY_HANDLE: a JSON list of {"key", "text"} entries
for the given agent_id, which PSN_Memory_Recall reads and filters directly.

Supported modes:
  - "SET":    Replace the value for the given (agent_id, key).
  - "APPEND": Append the value to the existing value (newline-separated if
              the existing value is non-empty).
"""

import json

CAT = "ParametricStudio/Memory"

_MODES = ("SET", "APPEND")


def _validate_agent_id(agent_id: str) -> str:
    if not isinstance(agent_id, str):
        raise ValueError("agent_id must be a string")
    stripped = agent_id.strip()
    if not stripped:
        raise ValueError("agent_id must not be empty")
    if len(stripped) > 256:
        raise ValueError("agent_id must be at most 256 characters")
    return stripped


def _validate_key(key: str) -> str:
    if not isinstance(key, str):
        raise ValueError("key must be a string")
    stripped = key.strip()
    if not stripped:
        raise ValueError("key must not be empty")
    if len(stripped) > 512:
        raise ValueError("key must be at most 512 characters")
    return stripped


def _validate_value(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    if len(value) > 1_000_000:
        raise ValueError("value must be at most 1,000,000 characters")
    return value


def _validate_mode(mode: str) -> str:
    if not isinstance(mode, str):
        raise ValueError("mode must be a string")
    if mode not in _MODES:
        raise ValueError(f"mode must be one of {_MODES}, got {mode!r}")
    return mode


# In-process store: {(agent_id, key): value}
_STORE: dict = {}


class PSN_Memory_Store:
    """Stores a key-value pair in an in-process memory store and returns all of the agent's entries."""

    DESCRIPTION = (
        "Stores a key-value pair in this process's memory (lost when ComfyUI restarts) and "
        "outputs the agent's entries as a JSON list for Memory Recall. Writes no file."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "agent_id": ("STRING", {"default": "default_agent"}),
                "key": ("STRING", {"default": "preferred_style"}),
                "value": ("STRING", {"default": ""}),
                "mode": (list(_MODES),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("MEMORY_HANDLE",)
    RETURN_NAMES = ("store_handle",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, agent_id: str, key: str, value: str, mode: str) -> tuple:
        agent_id = _validate_agent_id(agent_id)
        key = _validate_key(key)
        value = _validate_value(value)
        mode = _validate_mode(mode)

        store_key = (agent_id, key)

        if mode == "SET":
            _STORE[store_key] = value
        elif mode == "APPEND":
            existing = _STORE.get(store_key, "")
            if existing:
                _STORE[store_key] = existing + "\n" + value
            else:
                _STORE[store_key] = value

        entries = [
            {"key": k, "text": v}
            for (a_id, k), v in _STORE.items()
            if a_id == agent_id
        ]
        return (json.dumps(entries, ensure_ascii=False),)


NODE_CLASS_MAPPINGS = {
    "PSN_Memory_Store": PSN_Memory_Store,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Memory_Store": "PSN Memory Store",
}
