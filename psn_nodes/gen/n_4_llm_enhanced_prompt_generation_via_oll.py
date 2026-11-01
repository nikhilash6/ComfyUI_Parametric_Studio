"""PSN_Ollama_Prompt_Enhancer

LLM-Enhanced Prompt Generation via Ollama.

This module provides a ComfyUI custom node that enhances short user prompts
into detailed, structured prompts using a local Ollama LLM service.

The node POSTs to ``{ollama_url}/api/generate`` (``stream: false``) with the
standard library and uses the returned text. If the request fails (service
unreachable, HTTP error, bad URL) or Ollama returns no text, it falls back to a
fixed template of style tags and says so in the ``source`` output, so a canned
result is never presented as model output.

  - The request hook ``_ollama_request`` is injectable so tests can supply a
    canned reply without any network.
  - Robust parsing of Ollama-style JSON responses (``{"response": ...}``,
    ``{"message": {"content": ...}}``) and plain-text responses.
  - Template-based enhancement with style presets, and negative prompts per style.
  - Input validation and edge-case handling.
"""

import json
import re
import urllib.request

# ---------------------------------------------------------------------------
# Style presets: each style maps to a set of descriptor fragments and a
# corresponding negative prompt.
# ---------------------------------------------------------------------------

_STYLE_PRESETS = {
    "realistic": {
        "positive": [
            "photorealistic",
            "8k uhd",
            "detailed skin texture",
            "natural lighting",
            "shallow depth of field",
            "professional photography",
            "highly detailed",
            "sharp focus",
        ],
        "negative": (
            "cartoon, anime, illustration, painting, drawing, sketch, "
            "3d render, cgi, plastic, waxy skin, deformed, ugly, blurry, "
            "low quality, watermark, text, signature"
        ),
    },
    "anime": {
        "positive": [
            "anime style",
            "vibrant colors",
            "clean line art",
            "cel shading",
            "detailed background",
            "high quality anime",
            "beautiful lighting",
            "expressive",
        ],
        "negative": (
            "photorealistic, 3d, realistic, ugly, deformed, bad anatomy, "
            "extra limbs, blurry, low quality, watermark, text, signature, "
            "nsfw"
        ),
    },
    "cinematic": {
        "positive": [
            "cinematic",
            "dramatic lighting",
            "film grain",
            "anamorphic lens",
            "color graded",
            "epic composition",
            "shallow depth of field",
            "movie still",
            "highly detailed",
        ],
        "negative": (
            "cartoon, anime, flat lighting, overexposed, underexposed, "
            "blurry, low quality, watermark, text, signature, deformed"
        ),
    },
    "none": {
        "positive": [
            "highly detailed",
            "sharp focus",
            "well composed",
            "beautiful lighting",
            "masterpiece",
        ],
        "negative": (
            "blurry, low quality, watermark, text, signature, deformed, "
            "ugly, bad anatomy"
        ),
    },
}

# ---------------------------------------------------------------------------
# Template-based enhancer (offline fallback)
# ---------------------------------------------------------------------------


def _template_enhance(short_prompt: str, style: str, max_tokens: int) -> tuple:
    """Expand *short_prompt* into a detailed prompt using style presets.

    Returns ``(enhanced_prompt, negative_prompt)``.
    """
    short_prompt = (short_prompt or "").strip()
    if not short_prompt:
        short_prompt = "a beautiful scene"

    style = (style or "none").strip().lower()
    if style not in _STYLE_PRESETS:
        style = "none"

    preset = _STYLE_PRESETS[style]
    descriptors = ", ".join(preset["positive"])

    # Build the enhanced prompt: subject + descriptors + quality tag
    parts = [short_prompt, descriptors, "masterpiece, best quality"]
    enhanced = ", ".join(parts)

    # Rough token budget: truncate if the prompt is too long.
    # We approximate 1 token ≈ 4 characters for English text.
    if max_tokens and max_tokens > 0:
        max_chars = max_tokens * 4
        if len(enhanced) > max_chars:
            enhanced = enhanced[:max_chars].rsplit(",", 1)[0].rstrip(", ")

    return enhanced, preset["negative"]


# ---------------------------------------------------------------------------
# Ollama response parsing
# ---------------------------------------------------------------------------


def _parse_ollama_response(raw: str) -> str:
    """Parse an Ollama API response into plain text.

    Handles:
      - JSON: ``{"message": {"content": "..."}}``
      - JSON: ``{"response": "..."}``
      - Plain text (fallback)
    """
    if not raw or not raw.strip():
        return ""

    raw = raw.strip()

    # Try JSON first
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            # Ollama /api/generate format
            if "message" in data and isinstance(data["message"], dict):
                content = data["message"].get("content", "")
                if content:
                    return content.strip()
            # Ollama /api/chat format
            if "response" in data:
                return str(data["response"]).strip()
            # Fallback: look for any string value
            for v in data.values():
                if isinstance(v, str) and v.strip():
                    return v.strip()
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # Plain text fallback
    return raw


# ---------------------------------------------------------------------------
# Ollama request hook (injectable for testing)
# ---------------------------------------------------------------------------


def _default_ollama_request(ollama_url: str, model_name: str, prompt: str, max_tokens: int) -> str:
    """POST to ``{ollama_url}/api/generate`` (stream false) and return the body.

    Raises ValueError for a non-http(s) URL and OSError (URLError/HTTPError/
    timeout) when the service cannot be reached.
    """
    base = (ollama_url or "").strip().rstrip("/")
    if not base.lower().startswith(("http://", "https://")):
        raise ValueError("ollama_url must start with http:// or https://")
    body = json.dumps({
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": int(max_tokens)},
    }).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/generate", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# ComfyUI Node
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/LLM"


class PSN_Ollama_Prompt_Enhancer:
    """Enhance a short prompt into a detailed prompt using a local Ollama LLM.

    When the request fails or returns no text, a fixed template of style tags is
    used instead and the ``source`` output says so.

    Inputs:
        short_prompt  – the user's initial short prompt.
        ollama_url    – URL of the Ollama service (default http://localhost:11434).
        model_name    – Ollama model name (e.g. "llama3").
        style         – desired style: realistic / anime / cinematic / none.
        max_tokens    – maximum tokens for the generated prompt.

    Outputs:
        enhanced_prompt  – the detailed prompt string.
        negative_prompt  – a suggested negative prompt string.
        source           – "ollama", or "template (fallback: <reason>)".
    """

    DESCRIPTION = ("Expands a short prompt with a local Ollama model via "
                   "POST /api/generate. If Ollama cannot be reached or returns "
                   "nothing, it uses fixed style tags and reports that in the "
                   "source output.")

    # Replaceable by tests (canned reply, no network).
    _ollama_request = staticmethod(_default_ollama_request)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "short_prompt": ("STRING", {"default": "a cat", "multiline": True}),
                "style": (
                    ["realistic", "anime", "cinematic", "none"],
                    {"default": "realistic"},
                ),
                "max_tokens": ("INT", {"default": 128, "min": 16, "max": 2048}),
            },
            "optional": {
                "ollama_url": ("STRING", {"default": "http://localhost:11434"}),
                "model_name": ("STRING", {"default": "llama3"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("enhanced_prompt", "negative_prompt", "source")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        short_prompt: str,
        style: str = "realistic",
        max_tokens: int = 128,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "llama3",
    ):
        """Enhance *short_prompt* via Ollama (or template fallback).

        Returns ``(enhanced_prompt, negative_prompt, source)``.
        """
        # --- Validate inputs ------------------------------------------------
        if not isinstance(short_prompt, str):
            raise TypeError("short_prompt must be a string")
        if not isinstance(style, str):
            raise TypeError("style must be a string")
        if not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer")

        short_prompt = short_prompt.strip()
        style = style.strip().lower()
        if style not in _STYLE_PRESETS:
            style = "none"

        # --- Build the instruction for the LLM ------------------------------
        instruction = (
            f"Enhance the following short prompt into a detailed, structured "
            f"image-generation prompt. Style: {style}. "
            f"Return ONLY the enhanced prompt text, no explanations.\n\n"
            f"Short prompt: {short_prompt}"
        )

        # --- Try Ollama first, fall back to template ------------------------
        enhanced = None
        negative = None
        source = "ollama"
        fallback_reason = ""

        try:
            raw_response = self._ollama_request(
                ollama_url, model_name, instruction, max_tokens
            )
            enhanced = _parse_ollama_response(raw_response)
            if enhanced:
                # Extract negative prompt if the LLM included one
                # (convention: a line starting with "Negative:")
                neg_match = re.search(r"Negative:\s*(.+)", enhanced, re.IGNORECASE)
                if neg_match:
                    negative = neg_match.group(1).strip()
                    enhanced = enhanced[: neg_match.start()].strip().rstrip(",")
        except (OSError, ValueError) as exc:
            enhanced = None
            negative = None
            fallback_reason = "%s: %s" % (type(exc).__name__, exc)

        if not enhanced:
            if not fallback_reason:
                fallback_reason = "Ollama returned no text"
            source = "template (fallback: %s)" % fallback_reason
            enhanced, negative = _template_enhance(short_prompt, style, max_tokens)

        # Ensure we always have a negative prompt
        if not negative:
            negative = _STYLE_PRESETS[style]["negative"]

        return (enhanced, negative, source)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Ollama_Prompt_Enhancer": PSN_Ollama_Prompt_Enhancer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Ollama_Prompt_Enhancer": "Ollama Prompt Enhancer",
}
