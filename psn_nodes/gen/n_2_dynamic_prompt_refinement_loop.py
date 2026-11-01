"""ParametricStudio - Dynamic Prompt Refinement Loop.

Two ComfyUI custom nodes:
  * PSN_Prompt_Scripted_Rewrite - walks a list of (score, rewrite) turns that
    you supply in the ``script`` input, or a length/keyword heuristic, until
    the score reaches a threshold or max iterations is reached.  It calls no
    LLM, so the score is not a quality judgement.
  * PSN_Prompt_Structure_Enforcer - rewrites a free-form prompt into a fixed
    structural template (subject, env, light, style).

No network, no external LLM.  The 'script' input is a STRING that holds the
turns to walk, e.g.:

    script:score=0.4,rewrite=a more detailed prompt;score=0.9,rewrite=final prompt

Each semicolon-separated segment is one turn.  If the script is empty (or runs
out of turns) the node falls back to a built-in heuristic that scores by word
count and detail keywords and, for short low-scoring prompts, appends a fixed
phrase.
"""

import json
import re

CAT = "ParametricStudio/Prompt"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_DETAIL_KEYWORDS = (
    "lighting", "shadow", "color", "texture", "detail", "style", "mood",
    "atmosphere", "composition", "angle", "lens", "focus", "depth", "tone",
    "palette", "contrast", "vignette", "grain", "brush", "render", "photograph",
    "cinematic", "dramatic", "soft", "harsh", "warm", "cool", "bright", "dark",
)


def _heuristic_score(prompt: str) -> float:
    """Return a 0..1 quality score based on length and detail keywords."""
    if not prompt or not prompt.strip():
        return 0.0
    p = prompt.lower()
    words = len(p.split())
    kw_hits = sum(1 for k in _DETAIL_KEYWORDS if k in p)
    # length component: 0 at 0 words, 1 at >= 30 words
    length_score = min(1.0, words / 30.0)
    # keyword component: 0 at 0 hits, 1 at >= 5 hits
    kw_score = min(1.0, kw_hits / 5.0)
    return round(0.5 * length_score + 0.5 * kw_score, 4)


def _parse_script(script: str):
    """Parse a script string into a list of (score, rewrite) tuples.

    Format: script:score=0.4,rewrite=...;score=0.9,rewrite=...
    Returns [] if the script is empty or does not start with ``script:``.
    """
    if not script or not script.strip():
        return []
    h = script.strip()
    if not h.startswith("script:"):
        return []
    body = h[len("script:"):]
    turns = []
    for seg in body.split(";"):
        seg = seg.strip()
        if not seg:
            continue
        score_m = re.search(r"score=([\d.]+)", seg)
        rewrite_m = re.search(r"rewrite=(.*)", seg)
        if score_m is None:
            continue
        score = float(score_m.group(1))
        rewrite = rewrite_m.group(1).strip() if rewrite_m else ""
        turns.append((score, rewrite))
    return turns


def _scripted_turn(prompt: str, turns, turn_index: int):
    """Take one turn from the script, or from the heuristic when it is exhausted.

    Returns (score: float, new_prompt: str).
    """
    if turns and turn_index < len(turns):
        score, rewrite = turns[turn_index]
        return score, (rewrite if rewrite else prompt)
    # fallback: heuristic
    score = _heuristic_score(prompt)
    # heuristic rewrite: append a fixed detail phrase if the prompt is short
    if score < 0.5 and len(prompt.split()) < 15:
        new_prompt = prompt.rstrip(".") + ", cinematic lighting, detailed texture, dramatic mood"
    else:
        new_prompt = prompt
    return score, new_prompt


# ---------------------------------------------------------------------------
# Node 1: PSN_Prompt_Scripted_Rewrite
# ---------------------------------------------------------------------------

class PSN_Prompt_Scripted_Rewrite:
    """Walk a supplied list of (score, rewrite) turns, or a length/keyword heuristic, until the threshold is met."""

    DESCRIPTION = ("Walks the (score, rewrite) turns you supply, or a length/keyword heuristic "
                   "that appends a fixed phrase to short prompts, until the score reaches the "
                   "threshold. It calls no LLM, so the score is not a quality judgement.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "initial_prompt": ("STRING", {"default": "a cat", "multiline": True}),
                "script": ("STRING", {"default": "", "multiline": True}),
                "max_iterations": ("INT", {"default": 5, "min": 1, "max": 50}),
                "quality_threshold": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.05}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "FLOAT")
    RETURN_NAMES = ("rewritten_prompt", "iteration_count", "score")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, initial_prompt, script, max_iterations, quality_threshold):
        prompt = (initial_prompt or "").strip()
        if not prompt:
            return ("", 0, 0.0)

        turns = _parse_script(script)
        threshold = float(quality_threshold)
        max_iter = int(max_iterations)

        score = 0.0
        iteration = 0
        for i in range(max_iter):
            iteration = i + 1
            score, new_prompt = _scripted_turn(prompt, turns, i)
            prompt = new_prompt.strip()
            if score >= threshold:
                break

        return (prompt, iteration, round(score, 4))


# ---------------------------------------------------------------------------
# Node 2: PSN_Prompt_Structure_Enforcer
# ---------------------------------------------------------------------------

_LIGHT_WORDS = ("lighting", "light", "shadow", "sunlight", "moonlight", "neon", "backlit", "rim light")
_STYLE_WORDS = ("style", "render", "photograph", "cinematic", "painting", "sketch", "3d", "anime", "oil", "watercolor")
_ENV_WORDS = ("environment", "background", "setting", "scene", "landscape", "city", "forest", "room", "studio", "outdoor", "indoor")


def _extract_components(prompt: str):
    """Heuristically split a prompt into subject / env / light / style."""
    p = (prompt or "").strip()
    if not p:
        return {"subject": "", "env": "", "light": "", "style": ""}

    lower = p.lower()
    light = ""
    style = ""
    env = ""

    # try to find light segment
    for w in _LIGHT_WORDS:
        idx = lower.find(w)
        if idx != -1:
            # grab from this word to next comma or end
            rest = p[idx:]
            comma = rest.find(",")
            light = rest[:comma].strip() if comma != -1 else rest.strip()
            break

    # try to find style segment
    for w in _STYLE_WORDS:
        idx = lower.find(w)
        if idx != -1:
            # grab from the start of the comma-separated segment containing this word
            seg_start = lower.rfind(",", 0, idx)
            seg_start = seg_start + 1 if seg_start != -1 else 0
            seg_end = lower.find(",", idx)
            seg_end = len(p) if seg_end == -1 else seg_end
            style = p[seg_start:seg_end].strip()
            break

    # try to find env segment
    for w in _ENV_WORDS:
        idx = lower.find(w)
        if idx != -1:
            rest = p[idx:]
            comma = rest.find(",")
            env = rest[:comma].strip() if comma != -1 else rest.strip()
            break

    # subject = whatever is left (remove matched segments)
    subject = p
    for seg in (light, style, env):
        if seg:
            subject = subject.replace(seg, "")
    # clean up leftover commas / spaces
    subject = re.sub(r"\s*,\s*", ", ", subject).strip(", ")
    subject = re.sub(r"^\s*,\s*", "", subject).strip()

    return {"subject": subject, "env": env, "light": light, "style": style}


class PSN_Prompt_Structure_Enforcer:
    """Rewrite a free-form prompt into a fixed structural template."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "a cat in a forest, warm lighting, oil painting style", "multiline": True}),
                "template": ("STRING", {"default": "{subject}, {env}, {light}, {style}", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("structured_prompt",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt, template):
        comps = _extract_components(prompt)
        # fill template; missing components become empty string
        try:
            result = template.format(**comps)
        except (KeyError, IndexError):
            # template has unknown placeholders - fall back to simple join
            parts = [comps[k] for k in ("subject", "env", "light", "style") if comps[k]]
            result = ", ".join(parts)
        # clean up: remove empty segments (consecutive commas, leading/trailing commas)
        parts = [p.strip() for p in result.split(",")]
        parts = [p for p in parts if p]
        result = ", ".join(parts)
        return (result.strip(),)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Prompt_Scripted_Rewrite": PSN_Prompt_Scripted_Rewrite,
    "PSN_Prompt_Structure_Enforcer": PSN_Prompt_Structure_Enforcer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Prompt_Scripted_Rewrite": "Scripted Prompt Rewrite (calls no LLM)",
    "PSN_Prompt_Structure_Enforcer": "PSN Prompt Structure Enforcer",
}
