"""Tests for n_7_llm_agent_chat_interface (offline, no network)."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import n_7_llm_agent_chat_interface as mod
from n_7_llm_agent_chat_interface import (
    AgentInstance,
    PSN_LLM_Agent_Init,
    PSN_LLM_Chat_Request_Build,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

# ---------------------------------------------------------------------------
# 1. Module-level registration
# ---------------------------------------------------------------------------
assert "PSN_LLM_Agent_Init" in NODE_CLASS_MAPPINGS, "Init node missing from mappings"
assert "PSN_LLM_Chat_Request_Build" in NODE_CLASS_MAPPINGS, "Builder node missing from mappings"
assert NODE_CLASS_MAPPINGS["PSN_LLM_Agent_Init"] is PSN_LLM_Agent_Init
assert NODE_CLASS_MAPPINGS["PSN_LLM_Chat_Request_Build"] is PSN_LLM_Chat_Request_Build
assert "PSN_LLM_Agent_Init" in NODE_DISPLAY_NAME_MAPPINGS
assert "PSN_LLM_Chat_Request_Build" in NODE_DISPLAY_NAME_MAPPINGS
print("1. registration ok")

# ---------------------------------------------------------------------------
# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
# ---------------------------------------------------------------------------
init_types = PSN_LLM_Agent_Init.INPUT_TYPES()
assert "required" in init_types and "provider" in init_types["required"]
assert "model_name" in init_types["required"]
assert "system_prompt" in init_types["required"]
assert "optional" in init_types and "api_key" in init_types["optional"]
assert PSN_LLM_Agent_Init.RETURN_TYPES == ("AGENT_INSTANCE",)
assert PSN_LLM_Agent_Init.FUNCTION == "run"
assert PSN_LLM_Agent_Init.CATEGORY == "ParametricStudio/LLM"

chat_types = PSN_LLM_Chat_Request_Build.INPUT_TYPES()
assert "agent_instance" in chat_types["required"]
assert "user_message" in chat_types["required"]
assert PSN_LLM_Chat_Request_Build.RETURN_TYPES == ("STRING",)
assert PSN_LLM_Chat_Request_Build.RETURN_NAMES == ("request_json",)
assert PSN_LLM_Chat_Request_Build.FUNCTION == "run"
print("2. input/return types ok")

# ---------------------------------------------------------------------------
# 3. Init node: valid provider
# ---------------------------------------------------------------------------
node = PSN_LLM_Agent_Init()
agent, = node.run(provider="openai", model_name="gpt-4o-mini",
                  system_prompt="Be concise.", api_key="sk-test")
assert isinstance(agent, AgentInstance)
assert agent.provider == "openai"
assert agent.model_name == "gpt-4o-mini"
assert agent.api_key == "sk-test"
assert agent.system_prompt == "Be concise."
assert agent.history == []
print("3. init valid ok")

# ---------------------------------------------------------------------------
# 4. Init node: bad provider raises
# ---------------------------------------------------------------------------
try:
    node.run(provider="bogus", model_name="m", system_prompt="")
    raise AssertionError("expected ValueError for bad provider")
except ValueError:
    pass

# Init node: empty model_name raises
try:
    node.run(provider="ollama", model_name="   ", system_prompt="")
    raise AssertionError("expected ValueError for empty model_name")
except ValueError:
    pass
print("4. init bad input ok")

# ---------------------------------------------------------------------------
# 5. Builder: request JSON has real values and no fabricated reply or usage
# ---------------------------------------------------------------------------
chat_node = PSN_LLM_Chat_Request_Build()
agent2, = node.run(provider="ollama", model_name="llama3", system_prompt="sys",
                   api_key="sk-secret")
out = chat_node.run(agent2, user_message="Hello")
assert len(out) == 1
req = json.loads(out[0])
assert req == {
    "provider": "ollama",
    "model": "llama3",
    "messages": [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "Hello"},
    ],
}
assert "sk-secret" not in out[0]
assert not hasattr(mod, "_mock_completion")
assert not hasattr(mod, "_estimate_tokens")
assert not hasattr(AgentInstance, "complete")
print("5. builder basic ok")

# ---------------------------------------------------------------------------
# 6. Builder does not change the agent and is repeatable
# ---------------------------------------------------------------------------
out2 = chat_node.run(agent2, user_message="Hello")
assert out2 == out
assert agent2.history == []
print("6. builder pure ok")

# ---------------------------------------------------------------------------
# 7. Builder: bad agent_instance type raises
# ---------------------------------------------------------------------------
try:
    chat_node.run("not-an-agent", user_message="hi")
    raise AssertionError("expected TypeError for bad agent_instance")
except TypeError:
    pass

# Builder: None user_message raises
try:
    chat_node.run(agent2, user_message=None)
    raise AssertionError("expected ValueError for None user_message")
except ValueError:
    pass
print("7. chat bad input ok")

# ---------------------------------------------------------------------------
# 8. Extra history lines and agent history become user messages, in order
# ---------------------------------------------------------------------------
agent3, = node.run(provider="azure", model_name="gpt-4", system_prompt="")
agent3.history = ["earlier"]
req3 = json.loads(chat_node.run(agent3, user_message="Hi", history="line1\n\nline2")[0])
assert req3["provider"] == "azure"
assert req3["messages"] == [
    {"role": "user", "content": "earlier"},
    {"role": "user", "content": "line1"},
    {"role": "user", "content": "line2"},
    {"role": "user", "content": "Hi"},
]
print("8. extra history ok")

print("ok")
