"""
PSN_ELLA_Request_Formatter: validates ELLA parameters and formats a redacted JSON
request payload.

This module does NOT run ELLA and does NOT change any conditioning. It only:
- Formats the ELLA connector request (model, sigma, strength, conditioning
  JSON) as a JSON string
- Validates config (sigma range, strength range, model allow-list)
- Rate limits invocations
- Redacts sensitive fields in the payload
- Offers a helper that parses a connector response (not used by the node)

It does NOT open sockets, access files, use torch, import comfy, or perform
network I/O. All functions and the node take plain values (numbers, strings,
JSON text) and return plain values. Invalid input raises ValueError.
"""

import json
import time

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/ELLA"

# Allow-list of valid ELLA model identifiers
ALLOWED_ELLA_MODELS = (
    "ella_v1_small",
    "ella_v1_medium",
    "ella_v1_large",
    "ella_v2_small",
    "ella_v2_medium",
    "ella_v2_large",
)

# Rate limiting: max requests per sliding window
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60.0

# Sensitive field names that must be redacted in payloads
SENSITIVE_FIELDS = frozenset({
    "api_key", "token", "secret", "password", "credential",
    "auth_token", "access_key", "private_key",
})

# ---------------------------------------------------------------------------
# Rate Limiter (pure in-memory, no I/O)
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Simple sliding-window rate limiter using only time.time()."""

    def __init__(self, max_requests: int, window_seconds: float):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._timestamps = []

    def allow(self) -> bool:
        now = time.time()
        cutoff = now - self._window_seconds
        # Remove expired timestamps
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        if len(self._timestamps) >= self._max_requests:
            return False
        self._timestamps.append(now)
        return True

    def reset(self) -> None:
        self._timestamps = []


# Module-level rate limiter instance
_ella_rate_limiter = _RateLimiter(RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _validate_sigma(sigma: float) -> tuple:
    """Validate sigma is a finite non-negative float. Returns (ok, reason)."""
    if not isinstance(sigma, (int, float)):
        return False, "sigma must be a number"
    if isinstance(sigma, float) and (sigma != sigma or sigma in (float("inf"), float("-inf"))):
        return False, "sigma must be a finite number"
    if sigma < 0:
        return False, "sigma must be non-negative"
    return True, "ok"


def _validate_strength(strength: float) -> tuple:
    """Validate strength is in [0, 1]. Returns (ok, reason)."""
    if not isinstance(strength, (int, float)):
        return False, "strength must be a number"
    if isinstance(strength, float) and (strength != strength or strength in (float("inf"), float("-inf"))):
        return False, "strength must be a finite number"
    if strength < 0.0 or strength > 1.0:
        return False, "strength must be in [0, 1]"
    return True, "ok"


def _validate_model(model_id: str) -> tuple:
    """Validate model_id is in the allow-list. Returns (ok, reason)."""
    if not isinstance(model_id, str):
        return False, "model_id must be a string"
    if model_id not in ALLOWED_ELLA_MODELS:
        return False, f"model_id '{model_id}' not in allow-list"
    return True, "ok"


def _redact_sensitive(payload: dict) -> dict:
    """Return a copy of payload with sensitive fields redacted (recursively)."""
    redacted = {}
    for key, value in payload.items():
        if key in SENSITIVE_FIELDS:
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = _redact_sensitive(value)
        else:
            redacted[key] = value
    return redacted


def _format_request_payload(
    conditioning: dict,
    sigma: float,
    strength: float,
    model_id: str,
) -> str:
    """
    Format the ELLA connector request as a JSON string.
    Sensitive fields are redacted before serialization.
    """
    payload = {
        "type": "ella_semantic_connector",
        "model": model_id,
        "sigma": sigma,
        "strength": strength,
        "conditioning": conditioning,
    }
    redacted = _redact_sensitive(payload)
    return json.dumps(redacted, sort_keys=True, separators=(",", ":"))


def _parse_response(response_text: str) -> tuple:
    """
    Parse the ELLA connector response JSON text.
    Returns (ok, parsed_dict_or_error_string).
    """
    if not isinstance(response_text, str):
        return False, "response must be a string"
    try:
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, ValueError):
        return False, "invalid JSON in response"
    if not isinstance(parsed, dict):
        return False, "response must be a JSON object"
    if "conditioning" not in parsed:
        return False, "response missing 'conditioning' field"
    return True, parsed


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_ELLA_Request_Formatter:
    """
    Validate ELLA parameters and format a redacted JSON request payload.

    It does not run ELLA, does not touch a CONDITIONING tensor and does not
    change the conditioning you give it; the conditioning is only copied into
    the payload (with sensitive fields redacted). No GPU, torch, network, or
    file I/O is performed.

    Inputs:
        conditioning: JSON text of a dict, copied into the payload
        sigma: Timestep sigma (float, >= 0)
        ella_model: Model identifier (must be in allow-list)
        strength: Strength in [0, 1]

    Outputs:
        request_payload: The formatted (redacted) request JSON text

    Raises ValueError on invalid input or when the rate limit is exceeded.
    """

    DESCRIPTION = ("Validates ELLA parameters and formats a redacted JSON "
                   "request payload. It does not run ELLA and does not change "
                   "any conditioning.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "conditioning": ("STRING", {"default": "{}", "multiline": True}),
                "sigma": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1e9, "step": 0.001}),
                "ella_model": (list(ALLOWED_ELLA_MODELS),),
                "strength": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("request_payload",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, conditioning, sigma, ella_model, strength):
        for ok, reason in (_validate_sigma(sigma), _validate_strength(strength),
                           _validate_model(ella_model)):
            if not ok:
                raise ValueError(reason)

        if not isinstance(conditioning, str):
            raise ValueError("conditioning must be a JSON string")
        try:
            cond_dict = json.loads(conditioning)
        except (json.JSONDecodeError, ValueError):
            raise ValueError("invalid JSON in conditioning")
        if not isinstance(cond_dict, dict):
            raise ValueError("conditioning must be a JSON object")

        if not _ella_rate_limiter.allow():
            raise ValueError("rate limit exceeded")

        return (_format_request_payload(cond_dict, sigma, strength, ella_model),)


# ---------------------------------------------------------------------------
# Module-level mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_ELLA_Request_Formatter": PSN_ELLA_Request_Formatter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ELLA_Request_Formatter": "ELLA Request Formatter (does not run ELLA)",
}
