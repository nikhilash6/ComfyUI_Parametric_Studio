"""PSN prompt extraction helpers for text taken from tutorial screenshots.

This module does NOT perform OCR. It has two pure-string nodes:

  * PSN_TextLinesToRegions splits text you supply (for example text copied out
    of an external OCR tool) into one record per non-empty line.
  * PSN_Prompt_Cleaner strips common UI noise, splits prompt / negative-prompt /
    settings sections, and emits a JSON document for a prompt library.

It reads no image, loads no model, and has no box coordinates or confidence
scores. No network, file, OS, subprocess, eval/exec, or torch/comfy imports are
used. All functions take plain values (strings, booleans, JSON text).
"""

import json
import re

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/OCR"

# --- configuration ---------------------------------------------------------

# Common UI / chrome text that should be dropped from a tutorial screenshot.
# Matched case-insensitively as whole tokens.
_UI_TOKENS = (
    "submit", "cancel", "ok", "okay", "close", "back", "next", "previous",
    "save", "save as", "open", "file", "edit", "view", "help",
    "apply", "reset", "done", "confirm", "yes", "no", "browse", "upload",
    "download", "search", "menu", "home", "login", "sign in", "sign out",
    "logout", "preferences", "options", "more", "less",
    "minimize", "maximize", "restore", "close window", "x", "x close",
)

# Section markers used to split a tutorial's text into structured parts.
# Each marker is a regex pattern (case-insensitive).
_NEGATIVE_MARKERS = (
    r"negative\s*prompt\s*:",
    r"negative\s*:",
    r"neg\s*prompt\s*:",
    r"neg\s*:",
)
_SETTINGS_MARKERS = (
    r"settings\s*:",
    r"parameters\s*:",
    r"cfg\s*:",
    r"steps\s*:",
    r"sampler\s*:",
    r"seed\s*:",
    r"resolution\s*:",
    r"aspect\s*ratio\s*:",
    r"model\s*:",
    r"lora\s*:",
)


def _build_line_records(text):
    """Return a JSON string with one record per non-empty line of text."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    lines_out = [{"id": idx, "text": line} for idx, line in enumerate(lines)]
    return json.dumps({"lines": lines_out})


def _strip_ui(text):
    """Remove common UI tokens from text, line by line."""
    if not isinstance(text, str):
        return ""
    out_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered in _UI_TOKENS:
            continue
        # Drop leading/trailing UI tokens embedded in a line.
        tokens = line.split()
        kept = [t for t in tokens if t.lower().strip(".,;:!?") not in _UI_TOKENS]
        if kept:
            out_lines.append(" ".join(kept))
    return "\n".join(out_lines)


def _match_marker(line, markers):
    """Try to match any marker regex against the line.

    Returns (matched, remainder) where remainder is the text after the marker.
    """
    for pattern in markers:
        m = re.search(pattern, line, re.IGNORECASE)
        if m:
            remainder = line[m.end():].strip(" :")
            return True, remainder
    return False, ""


def _split_sections(text):
    """Split cleaned text into (prompt, negative_prompt, settings)."""
    if not isinstance(text, str):
        return "", "", ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    prompt_parts = []
    negative_parts = []
    settings_parts = []
    current = "prompt"

    for line in lines:
        matched, remainder = _match_marker(line, _NEGATIVE_MARKERS)
        if matched:
            current = "negative"
            if remainder:
                negative_parts.append(remainder)
            continue

        matched, remainder = _match_marker(line, _SETTINGS_MARKERS)
        if matched:
            current = "settings"
            if remainder:
                settings_parts.append(remainder)
            continue

        if current == "prompt":
            prompt_parts.append(line)
        elif current == "negative":
            negative_parts.append(line)
        else:
            settings_parts.append(line)

    return (
        " ".join(prompt_parts).strip(),
        " ".join(negative_parts).strip(),
        " ".join(settings_parts).strip(),
    )


def _build_structured(prompt, negative, settings):
    """Build the structured JSON document for the prompt library."""
    doc = {
        "prompt": prompt,
        "negative_prompt": negative,
        "settings": settings,
    }
    return json.dumps(doc, ensure_ascii=False)


# --- nodes -----------------------------------------------------------------

class PSN_TextLinesToRegions:
    """Split supplied text into per-line records. Performs no OCR."""

    DESCRIPTION = ("Splits text you supply into one record per non-empty line. "
                   "It reads no image and performs no OCR; it gives no boxes "
                   "or confidence scores.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "", "multiline": True,
                                    "tooltip": "Text to split into lines (for example copied from an OCR tool)."}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("raw_text", "line_records")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, text):
        text = text if isinstance(text, str) else ""
        return (text, _build_line_records(text))


class PSN_Prompt_Cleaner:
    """Clean OCR text: strip UI noise, split sections, emit library JSON."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_text": ("STRING", {"default": "", "multiline": True}),
                "remove_ui_elements": ("BOOLEAN", {"default": True}),
                "format_for_library": ("BOOLEAN", {"default": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("cleaned_prompt", "structured_data")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, raw_text, remove_ui_elements, format_for_library):
        text = raw_text if isinstance(raw_text, str) else ""
        if remove_ui_elements:
            text = _strip_ui(text)
        prompt, negative, settings = _split_sections(text)
        cleaned = prompt
        if format_for_library:
            structured = _build_structured(prompt, negative, settings)
        else:
            structured = json.dumps({"prompt": prompt,
                                     "negative_prompt": negative,
                                     "settings": settings},
                                    ensure_ascii=False)
        return (cleaned, structured)


NODE_CLASS_MAPPINGS = {
    "PSN_TextLinesToRegions": PSN_TextLinesToRegions,
    "PSN_Prompt_Cleaner": PSN_Prompt_Cleaner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_TextLinesToRegions": "PSN Split Text Into Line Records",
    "PSN_Prompt_Cleaner": "PSN Prompt Cleaner",
}
