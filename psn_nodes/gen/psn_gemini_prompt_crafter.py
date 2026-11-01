"""PSN_Gemini_Response_Parser: parses a Gemini-style JSON response that you paste in.

It makes no API call and takes no API key. It reads the text of a response that has a
top-level "candidates" list (first candidate part with a "text" field) and an optional
"usage_metadata.total_token_count", and returns that text and the token count. Nothing
is generated, refined or sent anywhere; no network I/O.
"""

import json

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum length of the refined prompt we will accept from the response.
_MAX_REFINED_CHARS = 16000

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def psn_parse_response(response_text):
    """Parse a Gemini-style JSON response into (text, token_count, error).

    Accepts the JSON text of a response that contains a top-level
    "candidates" list with at least one candidate whose "content.parts"
    list contains a "text" field, and a top-level "usage_metadata" object
    with "total_token_count".

    On success error is "".
    """
    if not isinstance(response_text, str) or not response_text.strip():
        return "", 0, "response_text must be a non-empty string"
    try:
        data = json.loads(response_text)
    except (ValueError, TypeError):
        return "", 0, "response_text is not valid JSON"
    if not isinstance(data, dict):
        return "", 0, "response JSON must be an object"

    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return "", 0, "response missing non-empty 'candidates' list"

    refined = ""
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        content = cand.get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                refined = part["text"].strip()
                break
        if refined:
            break

    if not refined:
        return "", 0, "no text found in response candidates"

    if len(refined) > _MAX_REFINED_CHARS:
        refined = refined[:_MAX_REFINED_CHARS]

    usage = data.get("usage_metadata")
    token_usage = 0
    if isinstance(usage, dict):
        ttc = usage.get("total_token_count")
        if isinstance(ttc, int) and not isinstance(ttc, bool) and ttc >= 0:
            token_usage = ttc

    return refined, token_usage, ""


# ---------------------------------------------------------------------------
# ComfyUI node
# ---------------------------------------------------------------------------

class PSN_Gemini_Response_Parser:
    """Extracts the text and token count from a pasted Gemini-style JSON response. Makes no API call."""

    DESCRIPTION = ("Parses a pasted Gemini JSON response into its text and total token count. "
                   "It makes no API call, takes no API key and generates or refines nothing.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "response_text": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("parsed_text", "token_count")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Gemini"

    def run(self, response_text=""):
        text, token_count, err = psn_parse_response(response_text)
        if err:
            return ("<error: " + err + ">", 0)
        return (text, token_count)


NODE_CLASS_MAPPINGS = {
    "PSN_Gemini_Response_Parser": PSN_Gemini_Response_Parser,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Gemini_Response_Parser": "Gemini Response Parser (pasted JSON, no API call)",
}
