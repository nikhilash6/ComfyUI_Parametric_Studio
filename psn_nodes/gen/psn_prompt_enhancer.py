"""PSN_Prompt_Reply_Parser (pure-logic core).

This module parses an LLM reply that you paste in, of the form

    Positive: <prompt>
    Negative: <prompt>

into a positive and a negative prompt. It calls no LLM and enhances nothing: the
text comes out as the reply wrote it. It uses only the Python standard library
and performs no network, file, or subprocess I/O.

If the reply has no ``Positive:`` line, the positive prompt is the raw prompt
unchanged and the status says so. If it has no ``Negative:`` line, the negative
prompt is empty.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Text"


def parse_llm_response(llm_response, raw_prompt):
    """Parse a pasted reply into ``(positive, negative, status)``.

    The expected format is two lines, the first beginning with ``Positive:``
    and the second with ``Negative:``. Parsing is tolerant of surrounding
    whitespace and of the labels being in any case. If there is no positive
    line, ``raw_prompt`` is returned unchanged as the positive prompt. If there
    is no negative line, the negative prompt is "". ``status`` says which.
    """
    raw = str(raw_prompt).strip()
    if not llm_response or not str(llm_response).strip():
        return (raw, "", "no reply given: positive_prompt is the raw prompt unchanged, negative_prompt is empty")

    positive = None
    negative = None

    for line in str(llm_response).splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if lower.startswith("positive:"):
            positive = stripped[len("positive:"):].strip()
        elif lower.startswith("negative:"):
            negative = stripped[len("negative:"):].strip()

    notes = []
    if not positive:
        positive = raw
        notes.append("no Positive: line found, positive_prompt is the raw prompt unchanged")
    if not negative:
        negative = ""
        notes.append("no Negative: line found, negative_prompt is empty")
    status = "; ".join(notes) if notes else "parsed Positive: and Negative: lines from the reply"
    return (positive, negative, status)


class PSN_Prompt_Reply_Parser:
    """Parse a pasted ``Positive:`` / ``Negative:`` LLM reply into two prompts.

    Calls no LLM and enhances nothing. See the module docstring for the fallbacks.
    """

    DESCRIPTION = (
        "Parses a pasted Positive:/Negative: LLM reply into two prompts; calls no LLM and enhances nothing."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_prompt": ("STRING", {"default": "", "multiline": True}),
                # The reply text, pasted in or produced by another node.
                "llm_response": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "parse_status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, raw_prompt, llm_response):
        return parse_llm_response(llm_response, raw_prompt)


NODE_CLASS_MAPPINGS = {"PSN_Prompt_Reply_Parser": PSN_Prompt_Reply_Parser}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Prompt_Reply_Parser": "PSN Prompt Reply Parser (enhances nothing)"}
