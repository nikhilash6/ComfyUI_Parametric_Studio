"""PSN_Log_Entry_Formatter: formats one compact JSON log line from a node id, a supplied input hash and the current time.

It measures nothing: no execution time, no output hash, and it does not compute any hash. The
input_hash is whatever string the caller passes in (empty if none). It does no file I/O, network
access or OS operations; the caller must persist the returned line if it wants a log.

Dependencies: time, json (standard library only).
"""

import json
import time

CAT = "ParametricStudio/CV"


def _format_log_entry(node_id: str, input_hash: str, timestamp: float) -> str:
    """Format a single JSONL log entry as a compact JSON string."""
    entry = {
        "node_id": node_id,
        "input_hash": input_hash,
        "timestamp": timestamp,
    }
    return json.dumps(entry, separators=(",", ":"))


class PSN_Log_Entry_Formatter:
    """Formats a JSON log line {node_id, input_hash, timestamp}. Measures no execution and writes no file."""

    DESCRIPTION = ("Formats a JSON log line from node_id, the input_hash you pass in (not computed here) and the "
                   "current time. It measures no execution time, computes no hash and writes nothing.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "node_id": ("STRING", {"default": "unnamed_node"}),
            },
            "optional": {
                "input_hash": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("log_entry",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, node_id: str, input_hash: str = "") -> tuple:
        """Return a JSON log line with the node id, the supplied input_hash ("" if none) and the current time.

        Args:
            node_id: Identifier for the node the line is about.
            input_hash: A hash string supplied by the caller; passed through as given.

        Returns:
            A tuple containing a single compact JSON string.
        """
        if not isinstance(node_id, str):
            node_id = str(node_id)
        if not node_id:
            node_id = "unnamed_node"

        if not isinstance(input_hash, str):
            input_hash = str(input_hash) if input_hash is not None else ""

        return (_format_log_entry(node_id, input_hash, time.time()),)


NODE_CLASS_MAPPINGS = {
    "PSN_Log_Entry_Formatter": PSN_Log_Entry_Formatter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Log_Entry_Formatter": "Log Line Formatter (measures nothing)",
}
