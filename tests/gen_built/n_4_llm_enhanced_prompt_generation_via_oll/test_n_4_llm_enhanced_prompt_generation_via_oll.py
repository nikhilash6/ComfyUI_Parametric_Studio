"""Tests for n_4_llm_enhanced_prompt_generation_via_oll.py

Run:  python3 -B test_n_4_llm_enhanced_prompt_generation_via_oll.py
Must print 'ok' and exit 0.
"""

import io
import json
import sys
import urllib.error
import urllib.request

# Import the module under test
sys.path.insert(0, ".")
from n_4_llm_enhanced_prompt_generation_via_oll import (
    PSN_Ollama_Prompt_Enhancer,
    _template_enhance,
    _parse_ollama_response,
    _STYLE_PRESETS,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _default_ollama_request,
)

# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert "PSN_Ollama_Prompt_Enhancer" in NODE_CLASS_MAPPINGS, \
    "NODE_CLASS_MAPPINGS must contain PSN_Ollama_Prompt_Enhancer"
assert NODE_CLASS_MAPPINGS["PSN_Ollama_Prompt_Enhancer"] is PSN_Ollama_Prompt_Enhancer
assert "PSN_Ollama_Prompt_Enhancer" in NODE_DISPLAY_NAME_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Ollama_Prompt_Enhancer"] == "Ollama Prompt Enhancer"

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES structure
# ---------------------------------------------------------------------------
node = PSN_Ollama_Prompt_Enhancer()
input_types = PSN_Ollama_Prompt_Enhancer.INPUT_TYPES()
assert "required" in input_types, "INPUT_TYPES must have 'required'"
assert "short_prompt" in input_types["required"]
assert "style" in input_types["required"]
assert "max_tokens" in input_types["required"]
assert "optional" in input_types
assert "ollama_url" in input_types["optional"]
assert "model_name" in input_types["optional"]

# RETURN_TYPES / RETURN_NAMES / FUNCTION / CATEGORY
assert node.RETURN_TYPES == ("STRING", "STRING", "STRING")
assert node.RETURN_NAMES == ("enhanced_prompt", "negative_prompt", "source")
assert node.FUNCTION == "run"
assert node.CATEGORY == "ParametricStudio/LLM"

# ---------------------------------------------------------------------------
# 3. Template-based enhancement (offline fallback)
# ---------------------------------------------------------------------------
enhanced, negative = _template_enhance("a cat", "realistic", 128)
assert isinstance(enhanced, str) and len(enhanced) > 0
assert "a cat" in enhanced
assert "photorealistic" in enhanced
assert "8k uhd" in enhanced
assert isinstance(negative, str) and len(negative) > 0
assert "cartoon" in negative

# Anime style
enhanced_anime, neg_anime = _template_enhance("a warrior", "anime", 128)
assert "anime style" in enhanced_anime
assert "photorealistic" in neg_anime

# Cinematic style
enhanced_cine, neg_cine = _template_enhance("a city", "cinematic", 128)
assert "cinematic" in enhanced_cine
assert "dramatic lighting" in enhanced_cine

# None style
enhanced_none, neg_none = _template_enhance("a tree", "none", 128)
assert "highly detailed" in enhanced_none

# ---------------------------------------------------------------------------
# 4. Edge case: empty short_prompt
# ---------------------------------------------------------------------------
enhanced_empty, neg_empty = _template_enhance("", "realistic", 128)
assert isinstance(enhanced_empty, str) and len(enhanced_empty) > 0
assert "a beautiful scene" in enhanced_empty

# ---------------------------------------------------------------------------
# 5. Edge case: unknown style falls back to "none"
# ---------------------------------------------------------------------------
enhanced_unknown, neg_unknown = _template_enhance("a dog", "watercolor", 128)
assert "highly detailed" in enhanced_unknown  # 'none' preset

# ---------------------------------------------------------------------------
# 6. Edge case: max_tokens truncation
# ---------------------------------------------------------------------------
enhanced_long, _ = _template_enhance("a very long prompt about a cat", "realistic", 16)
# 16 tokens * 4 chars = 64 chars max
assert len(enhanced_long) <= 64, f"Expected <= 64 chars, got {len(enhanced_long)}"

# ---------------------------------------------------------------------------
# 7. Ollama response parsing: JSON message format
# ---------------------------------------------------------------------------
raw_json = json.dumps({"message": {"content": "a detailed cat, photorealistic"}})
parsed = _parse_ollama_response(raw_json)
assert parsed == "a detailed cat, photorealistic"

# ---------------------------------------------------------------------------
# 8. Ollama response parsing: JSON response format
# ---------------------------------------------------------------------------
raw_json2 = json.dumps({"response": "a cinematic scene"})
parsed2 = _parse_ollama_response(raw_json2)
assert parsed2 == "a cinematic scene"

# ---------------------------------------------------------------------------
# 9. Ollama response parsing: plain text fallback
# ---------------------------------------------------------------------------
parsed3 = _parse_ollama_response("just a plain text prompt")
assert parsed3 == "just a plain text prompt"

# ---------------------------------------------------------------------------
# 10. Ollama response parsing: empty / whitespace
# ---------------------------------------------------------------------------
assert _parse_ollama_response("") == ""
assert _parse_ollama_response("   ") == ""

# ---------------------------------------------------------------------------
# 11. Node run: unreachable service -> template, and it is reported
# ---------------------------------------------------------------------------
class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_seen = {}


def _canned_urlopen(req, timeout=None):
    _seen["url"] = req.full_url
    _seen["method"] = req.get_method()
    _seen["body"] = json.loads(req.data.decode("utf-8"))
    _seen["timeout"] = timeout
    return _Resp(json.dumps({"response": "a vivid sunset over hills, golden hour"}).encode())


def _refused_urlopen(req, timeout=None):
    raise urllib.error.URLError("connection refused")


_real_urlopen = urllib.request.urlopen
try:
    urllib.request.urlopen = _refused_urlopen
    node2 = PSN_Ollama_Prompt_Enhancer()
    enhanced_out, negative_out, source_out = node2.run(
        short_prompt="a sunset",
        style="cinematic",
        max_tokens=128,
    )
    assert "a sunset" in enhanced_out and "cinematic" in enhanced_out
    assert len(negative_out) > 0
    assert source_out.startswith("template (fallback: URLError"), source_out
    assert "connection refused" in source_out

    # 11b. Real request path: POST /api/generate with stream false
    urllib.request.urlopen = _canned_urlopen
    e2, n2, s2 = PSN_Ollama_Prompt_Enhancer().run(
        short_prompt="a sunset", style="realistic", max_tokens=64,
        ollama_url="http://localhost:11434/", model_name="llama3",
    )
    assert e2 == "a vivid sunset over hills, golden hour", e2
    assert s2 == "ollama"
    assert _seen["url"] == "http://localhost:11434/api/generate"
    assert _seen["method"] == "POST"
    assert _seen["body"]["model"] == "llama3"
    assert _seen["body"]["stream"] is False
    assert _seen["body"]["options"]["num_predict"] == 64
    assert "Short prompt: a sunset" in _seen["body"]["prompt"]
    assert _seen["timeout"] and _seen["timeout"] > 0

    # 11c. Non-http URL is refused before any request and reported
    _seen.clear()
    e3, n3, s3 = PSN_Ollama_Prompt_Enhancer().run(
        short_prompt="a bird", style="none", max_tokens=64,
        ollama_url="file:///etc/passwd",
    )
    assert "url" not in _seen
    assert s3.startswith("template (fallback: ValueError"), s3

    # 11d. Empty reply from Ollama is reported as such
    urllib.request.urlopen = lambda req, timeout=None: _Resp(json.dumps({"response": ""}).encode())
    e4, n4, s4 = PSN_Ollama_Prompt_Enhancer().run(short_prompt="a bird", style="none", max_tokens=64)
    assert s4 == "template (fallback: Ollama returned no text)", s4
finally:
    urllib.request.urlopen = _real_urlopen

# 11e. Direct call of the default hook rejects a non-http URL
try:
    _default_ollama_request("ftp://x", "m", "p", 8)
    assert False, "expected ValueError"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 12. Node run: injected hook returning a canned reply
# ---------------------------------------------------------------------------
def _canned_ollama_request(url, model, prompt, max_tokens):
    return json.dumps({"message": {"content": "a canned enhanced prompt, very detailed"}})

node3 = PSN_Ollama_Prompt_Enhancer()
node3._ollama_request = staticmethod(_canned_ollama_request)
enhanced_canned, negative_canned, source_canned = node3.run(
    short_prompt="a bird",
    style="anime",
    max_tokens=128,
)
assert "canned enhanced prompt" in enhanced_canned
assert source_canned == "ollama"
assert isinstance(negative_canned, str) and len(negative_canned) > 0

# ---------------------------------------------------------------------------
# 13. Node run: injected hook with negative prompt in response
# ---------------------------------------------------------------------------
def _canned_ollama_with_neg(url, model, prompt, max_tokens):
    return json.dumps({"message": {"content": "a detailed scene, beautiful. Negative: blurry, ugly"}})

node4 = PSN_Ollama_Prompt_Enhancer()
node4._ollama_request = staticmethod(_canned_ollama_with_neg)
enhanced_neg, negative_neg, _src = node4.run(
    short_prompt="a forest",
    style="realistic",
    max_tokens=128,
)
assert "a detailed scene" in enhanced_neg
assert "blurry" in negative_neg

# ---------------------------------------------------------------------------
# 14. Bad input: non-string short_prompt
# ---------------------------------------------------------------------------
node5 = PSN_Ollama_Prompt_Enhancer()
try:
    node5.run(short_prompt=12345, style="realistic", max_tokens=128)
    assert False, "Expected TypeError for non-string short_prompt"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 15. Bad input: non-string style
# ---------------------------------------------------------------------------
node6 = PSN_Ollama_Prompt_Enhancer()
try:
    node6.run(short_prompt="a cat", style=42, max_tokens=128)
    assert False, "Expected TypeError for non-string style"
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 16. Bad input: invalid max_tokens
# ---------------------------------------------------------------------------
node7 = PSN_Ollama_Prompt_Enhancer()
try:
    node7.run(short_prompt="a cat", style="realistic", max_tokens=0)
    assert False, "Expected ValueError for max_tokens=0"
except ValueError:
    pass

try:
    node7.run(short_prompt="a cat", style="realistic", max_tokens=-5)
    assert False, "Expected ValueError for negative max_tokens"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 17. All style presets exist and have positive + negative
# ---------------------------------------------------------------------------
for style_name in ["realistic", "anime", "cinematic", "none"]:
    assert style_name in _STYLE_PRESETS, f"Missing style preset: {style_name}"
    assert "positive" in _STYLE_PRESETS[style_name]
    assert "negative" in _STYLE_PRESETS[style_name]
    assert len(_STYLE_PRESETS[style_name]["positive"]) > 0
    assert len(_STYLE_PRESETS[style_name]["negative"]) > 0

# ---------------------------------------------------------------------------
# 18. Node run: whitespace-only short_prompt
# ---------------------------------------------------------------------------
node8 = PSN_Ollama_Prompt_Enhancer()
enhanced_ws, neg_ws, _s = node8.run(short_prompt="   ", style="none", max_tokens=64)
assert isinstance(enhanced_ws, str) and len(enhanced_ws) > 0
assert "a beautiful scene" in enhanced_ws

# ---------------------------------------------------------------------------
print("ok")
