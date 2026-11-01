"""ParametricStudio - LLM agent config and chat request builder.

Nothing here contacts an LLM: no network, no SDK.

  * PSN_LLM_Agent_Init          - holds provider, model, system prompt and
                                  optional api key in an AgentInstance.
  * PSN_LLM_Chat_Request_Build  - turns an AgentInstance plus a user message
                                  into an OpenAI-style chat request as JSON
                                  text. It sends nothing and returns no reply
                                  or token usage. The api key is never put in
                                  the request text.
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional

CAT = "ParametricStudio/LLM"

_PROVIDERS = ("openai", "ollama", "azure")


# ---------------------------------------------------------------------------
# Agent instance (plain Python object, no tensors)
# ---------------------------------------------------------------------------

@dataclass
class AgentInstance:
    """Holds the configuration for one LLM agent (plain data, no client)."""
    provider: str
    model_name: str
    api_key: Optional[str]
    system_prompt: str
    # prior conversation lines, sent as user-role messages by the builder
    history: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ComfyUI nodes
# ---------------------------------------------------------------------------

class PSN_LLM_Agent_Init:
    """Initialize an LLM agent with a provider, model and system prompt."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (list(_PROVIDERS),),
                "model_name": ("STRING", {"default": "gpt-4o-mini", "multiline": False}),
                "system_prompt": ("STRING", {"default": "You are a helpful assistant.", "multiline": True}),
            },
            "optional": {
                "api_key": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("AGENT_INSTANCE",)
    RETURN_NAMES = ("agent_instance",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, provider: str, model_name: str, system_prompt: str,
            api_key: str = "") -> tuple:
        if provider not in _PROVIDERS:
            raise ValueError(f"Unknown provider: {provider!r}")
        if not model_name or not model_name.strip():
            raise ValueError("model_name must be a non-empty string")
        agent = AgentInstance(
            provider=provider,
            model_name=model_name.strip(),
            api_key=api_key or None,
            system_prompt=system_prompt or "",
        )
        return (agent,)


class PSN_LLM_Chat_Request_Build:
    """Build an OpenAI-style chat request (JSON text) from an agent config.

    Calls no LLM and returns no reply. Messages are the system prompt (if
    any), the agent's history lines and the extra history lines (each as a
    user-role message, since history carries no roles), then the user message.
    """

    DESCRIPTION = ("Builds an OpenAI-style chat request as JSON text from an "
                   "agent config and a message. Calls no LLM and returns no "
                   "reply or token usage.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "agent_instance": ("AGENT_INSTANCE",),
                "user_message": ("STRING", {"default": "Hello", "multiline": True}),
            },
            "optional": {
                "history": ("STRING", {"default": "", "multiline": True,
                                       "tooltip": "Optional extra history, one entry per line."}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("request_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, agent_instance: AgentInstance, user_message: str,
            history: str = "") -> tuple:
        if not isinstance(agent_instance, AgentInstance):
            raise TypeError("agent_instance must be an AgentInstance")
        if user_message is None:
            raise ValueError("user_message must not be None")

        lines = list(agent_instance.history)
        if history:
            lines += [ln for ln in history.splitlines() if ln.strip()]

        messages = []
        if agent_instance.system_prompt:
            messages.append({"role": "system", "content": agent_instance.system_prompt})
        messages += [{"role": "user", "content": ln} for ln in lines]
        messages.append({"role": "user", "content": user_message})

        request = {
            "provider": agent_instance.provider,
            "model": agent_instance.model_name,
            "messages": messages,
        }
        return (json.dumps(request),)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_LLM_Agent_Init": PSN_LLM_Agent_Init,
    "PSN_LLM_Chat_Request_Build": PSN_LLM_Chat_Request_Build,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LLM_Agent_Init": "LLM Agent Init (ParametricStudio)",
    "PSN_LLM_Chat_Request_Build": "Build LLM Chat Request JSON (ParametricStudio)",
}
