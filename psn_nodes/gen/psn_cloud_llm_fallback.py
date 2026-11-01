"""PSN_LLM_Route_Decision: decides whether a prompt should go to a local or a cloud LLM. It calls no LLM.

What it does:
- scores prompt complexity (whitespace token count + keyword density, 0.0 to 1.0)
- returns the route: "cloud" if the score is above the threshold or the resource guard flag is off, else "local"
- returns the prompt prefixed with "[LOCAL] " or "[CLOUD] " so a downstream node can see the route

What it does not do: send the prompt anywhere, load a model, or produce an answer.
No torch, no ComfyUI imports, no network, no file/OS access.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/LLM"

# Keyword list that signals "complex" tasks (used for keyword-density scoring)
_COMPLEX_KEYWORDS = frozenset({
    "analyze", "compare", "evaluate", "optimize", "debug", "refactor",
    "architect", "design", "implement", "integrate", "migrate", "scale",
    "benchmark", "profile", "diagnose", "troubleshoot", "synthesize",
    "abstract", "generalize", "formalize", "derive", "prove", "verify",
})

# Allowed source labels
_SOURCES = ("local", "cloud")


def _estimate_complexity(task_prompt: str) -> float:
    """Estimate task complexity in [0.0, 1.0] from token count and keyword density.

    - token_count: number of whitespace-separated tokens
    - keyword_hits: number of tokens (lowercased) that appear in _COMPLEX_KEYWORDS
    - score = min(1.0, 0.6 * min(token_count / 50.0, 1.0) + 0.4 * min(keyword_hits / 5.0, 1.0))
    """
    if not isinstance(task_prompt, str):
        task_prompt = str(task_prompt)
    tokens = task_prompt.split()
    token_count = len(tokens)
    lower_tokens = [t.lower().strip(".,;:!?\"'()[]{}") for t in tokens]
    keyword_hits = sum(1 for t in lower_tokens if t in _COMPLEX_KEYWORDS)

    token_score = min(token_count / 50.0, 1.0)
    keyword_score = min(keyword_hits / 5.0, 1.0)
    score = 0.6 * token_score + 0.4 * keyword_score
    return max(0.0, min(1.0, score))


def _format_local_payload(task_prompt: str) -> str:
    """Prefix the prompt with the local route tag."""
    return f"[LOCAL] {task_prompt}"


def _format_cloud_payload(task_prompt: str) -> str:
    """Prefix the prompt with the cloud route tag."""
    return f"[CLOUD] {task_prompt}"


class PSN_LLM_Route_Decision:
    """Scores prompt complexity and returns "local" or "cloud" plus the prompt tagged with that route. Calls no LLM."""

    DESCRIPTION = ("Scores prompt complexity (length + keywords) and returns the route 'local' or 'cloud' "
                   "plus the prompt prefixed with [LOCAL] or [CLOUD]. It calls no LLM and produces no answer.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "task_prompt": ("STRING", {"default": "", "multiline": True}),
                "complexity_threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "resource_guard_ok": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("route", "tagged_prompt")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, task_prompt, complexity_threshold, resource_guard_ok=True):
        """
        Estimate complexity and pick local or cloud.

        Returns:
            route (str): "local" or "cloud"
            tagged_prompt (str): the prompt prefixed with "[LOCAL] " or "[CLOUD] "
        """
        # Validate inputs
        if not isinstance(task_prompt, str):
            task_prompt = str(task_prompt)
        if not isinstance(complexity_threshold, (int, float)):
            complexity_threshold = 0.5
        complexity_threshold = max(0.0, min(1.0, float(complexity_threshold)))
        if not isinstance(resource_guard_ok, bool):
            resource_guard_ok = bool(resource_guard_ok)

        complexity = _estimate_complexity(task_prompt)

        # Cloud if complexity exceeds threshold OR resource guard says local is unavailable
        use_cloud = (complexity > complexity_threshold) or (not resource_guard_ok)

        if use_cloud:
            return ("cloud", _format_cloud_payload(task_prompt))
        return ("local", _format_local_payload(task_prompt))


NODE_CLASS_MAPPINGS = {
    "PSN_LLM_Route_Decision": PSN_LLM_Route_Decision,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LLM_Route_Decision": "LLM Route Decision (local or cloud, calls no LLM)",
}
