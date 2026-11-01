import torch

from n_10_workflow_group_control import (
    PSN_Group_Bypass,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# --- module-level wiring ----------------------------------------------------
assert "PSN_Group_Bypass" in NODE_CLASS_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Group_Bypass"]

# --- INPUT_TYPES / metadata -------------------------------------------------
bt = PSN_Group_Bypass.INPUT_TYPES()
assert "group_id" in bt["required"] and "enabled" in bt["required"]
assert PSN_Group_Bypass.RETURN_TYPES == ("BOOLEAN",)
assert PSN_Group_Bypass.FUNCTION == "run"
assert PSN_Group_Bypass.CATEGORY.startswith("ParametricStudio/")

# --- group bypass signal ----------------------------------------------------
gb = PSN_Group_Bypass()
# enabled=True  -> group runs -> bypass False
assert gb.run("audio", True) == (False,)
# enabled=False -> group skipped -> bypass True
assert gb.run("audio", False) == (True,)
# 0/1 coercion
assert gb.run("audio", 0) == (True,)
assert gb.run("audio", 1) == (False,)

# bad group_id
try:
    gb.run("", True)
    raise AssertionError("empty group_id should raise")
except ValueError:
    pass
try:
    gb.run(123, True)
    raise AssertionError("non-string group_id should raise")
except TypeError:
    pass

# --- the node gate is gone (it altered data of enabled groups and blocked nothing) ----
import n_10_workflow_group_control as mod
assert not hasattr(mod, "PSN_Node_Gate")
assert not hasattr(mod, "_process")
assert "PSN_Node_Gate" not in NODE_CLASS_MAPPINGS
assert "PSN_Node_Gate" not in NODE_DISPLAY_NAME_MAPPINGS
assert sorted(NODE_CLASS_MAPPINGS) == ["PSN_Group_Bypass"]

# --- _as_bool coercion through the bypass node ---------------------------------
assert gb.run("g", torch.tensor(1)) == (False,)
assert gb.run("g", torch.tensor(0)) == (True,)
for bad in (0.5, 2):
    try:
        gb.run("g", bad)
        raise AssertionError("%r enabled flag should raise" % (bad,))
    except ValueError:
        pass
try:
    gb.run("g", "yes")
    raise AssertionError("string enabled flag should raise")
except TypeError:
    pass

print("ok")
