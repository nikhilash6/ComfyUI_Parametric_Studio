"""Tests for h_use_a_declarative_agent_pattern_wi.py"""

import sys
import os
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from h_use_a_declarative_agent_pattern_wi import (
    Agent,
    check_handoff_chain,
    parse_pipeline,
    validate_payload,
    PSN_AgentSchemaCheck,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

# ---------------------------------------------------------------------------
# 1. Agent creation and validation
# ---------------------------------------------------------------------------

agent = Agent("upscaler", "upscaling", "doubles resolution", {"image": "tensor", "log": "str"})
assert agent.name == "upscaler"
assert agent.role == "upscaling"
assert agent.output_schema == {"image": "tensor", "log": "str"}

ok, errors = agent.validate({"image": torch.zeros(1, 4, 4, 3), "log": "hi"})
assert ok, "valid payload should pass"
assert errors == []

ok, errors = agent.validate({"image": torch.zeros(1, 4, 4, 3)})
assert not ok, "missing key should fail"
assert any("missing key" in e for e in errors)

ok, errors = agent.validate({"image": "not a tensor", "log": "hi"})
assert not ok, "wrong type should fail"
assert any("expected tensor" in e for e in errors)

# ---------------------------------------------------------------------------
# 2. Pipeline parsing
# ---------------------------------------------------------------------------

pipeline_text = (
    "upscaler | upscaling | doubles resolution | image:tensor,log:str | style_transfer\n"
    "style_transfer | style | applies style | image:tensor,style:str |"
)
agents = parse_pipeline(pipeline_text)
assert len(agents) == 2
assert agents[0].name == "upscaler"
assert agents[0].handoff == "style_transfer"
assert agents[1].name == "style_transfer"
assert agents[1].handoff is None

# Empty pipeline should raise
try:
    parse_pipeline("")
    assert False, "empty pipeline should raise"
except ValueError:
    pass

# Bad line should raise
try:
    parse_pipeline("badline")
    assert False, "bad line should raise"
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 3. check_handoff_chain happy path
# ---------------------------------------------------------------------------

initial = {"image": torch.zeros(1, 4, 4, 3), "style": "anime", "log": ""}
final, trace = check_handoff_chain(agents, initial)
assert len(trace) == 2
assert trace[0]["agent"] == "upscaler"
assert trace[0]["ok"] is True
assert trace[1]["agent"] == "style_transfer"
assert trace[1]["ok"] is True
assert isinstance(final["image"], torch.Tensor)

# ---------------------------------------------------------------------------
# 4. check_handoff_chain with validation failure
# ---------------------------------------------------------------------------

agents2 = parse_pipeline(
    "upscaler | upscaling | doubles resolution | image:tensor,log:str | style_transfer\n"
    "style_transfer | style | applies style | image:tensor,style:str |"
)
bad_initial = {"image": torch.zeros(1, 4, 4, 3), "log": ""}  # missing 'style'
final2, trace2 = check_handoff_chain(agents2, bad_initial)
assert trace2[0]["ok"] is True  # upscaler passes
assert trace2[1]["ok"] is False  # style_transfer fails (missing 'style')

# ---------------------------------------------------------------------------
# 5. ComfyUI node: happy path
# ---------------------------------------------------------------------------

node = PSN_AgentSchemaCheck()
latent = {"samples": torch.rand(1, 8, 8, 3)}
out_latent, trace_str = node.run(latent, pipeline_text, style="anime")
assert isinstance(out_latent, dict)
assert "samples" in out_latent
assert out_latent["samples"].shape == (1, 8, 8, 3)
assert "upscaler" in trace_str
assert "style_transfer" in trace_str
assert trace_str == "[0] upscaler: schema ok\n[1] style_transfer: schema ok"
assert torch.equal(out_latent["samples"], latent["samples"]), "latent must come back unchanged"

# ---------------------------------------------------------------------------
# 6. ComfyUI node: bad input (missing required key in payload)
# ---------------------------------------------------------------------------

pipeline_bad = "checker | check | needs data | data:int |"
out_latent2, trace_str2 = node.run(latent, pipeline_bad)
assert trace_str2.splitlines()[0] == "[0] checker: schema FAIL"
assert "    error: missing key: data" in trace_str2
assert torch.equal(out_latent2["samples"], latent["samples"])

# 6b. A stage that claims to double the resolution does not: nothing runs
doubler = "upscaler | upscaling | doubles resolution | image:tensor |"
out_dbl, _ = node.run(latent, doubler)
assert out_dbl["samples"].shape == latent["samples"].shape
assert "Runs no agents" in PSN_AgentSchemaCheck.DESCRIPTION

# ---------------------------------------------------------------------------
# 7. Node metadata checks
# ---------------------------------------------------------------------------

assert "PSN_AgentSchemaCheck" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_AgentSchemaCheck"] is PSN_AgentSchemaCheck
assert "PSN_AgentSchemaCheck" in NODE_DISPLAY_NAME_MAPPINGS
assert PSN_AgentSchemaCheck.FUNCTION == "run"
assert PSN_AgentSchemaCheck.CATEGORY == "ParametricStudio/Agents"
assert PSN_AgentSchemaCheck.RETURN_TYPES == ("LATENT", "STRING")
assert PSN_AgentSchemaCheck.RETURN_NAMES == ("latent_unchanged", "schema_trace")

it = PSN_AgentSchemaCheck.INPUT_TYPES()
assert "latent" in it["required"]
assert "pipeline" in it["required"]

# ---------------------------------------------------------------------------
# 8. Edge case: single-agent pipeline (terminal)
# ---------------------------------------------------------------------------

single_text = "solo | solo | does nothing | image:tensor |"
agents_solo = parse_pipeline(single_text)
assert len(agents_solo) == 1
assert agents_solo[0].handoff is None

final_solo, trace_solo = check_handoff_chain(agents_solo, {"image": torch.zeros(1, 2, 2, 3)})
assert len(trace_solo) == 1
assert trace_solo[0]["ok"] is True

# ---------------------------------------------------------------------------
# 9. Edge case: handoff to non-existent agent
# ---------------------------------------------------------------------------

try:
    bad_handoff_text = "a | r | d | x:int | nonexistent"
    agents_bad = parse_pipeline(bad_handoff_text)
    check_handoff_chain(agents_bad, {"x": 1})
    assert False, "should raise for missing handoff target"
except ValueError as e:
    assert "not found" in str(e)

# ---------------------------------------------------------------------------
# 10. Never mutate inputs
# ---------------------------------------------------------------------------

original = {"image": torch.zeros(1, 4, 4, 3), "style": "anime", "log": ""}
original_copy = {"image": original["image"].clone(), "style": original["style"], "log": original["log"]}
check_handoff_chain(agents, original)
assert torch.equal(original["image"], original_copy["image"]), "input tensor must not be mutated"
assert original["style"] == original_copy["style"]
assert original["log"] == original_copy["log"]

print("ok")
