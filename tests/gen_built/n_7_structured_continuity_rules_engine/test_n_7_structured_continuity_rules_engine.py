"""Tests for n_7_structured_continuity_rules_engine."""

import torch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import n_7_structured_continuity_rules_engine as mod
from n_7_structured_continuity_rules_engine import (
    PSN_ContinuityRuleDefiner,
    PSN_ContinuityColourCheck,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _parse_rule_text,
    _parse_rule_line,
    _colour_fraction,
)

# ---------------------------------------------------------------------------
# 1. Rule parsing: basic "must have red hair"
# ---------------------------------------------------------------------------
rules = _parse_rule_text("must have red hair")
assert len(rules) == 1, f"Expected 1 rule, got {len(rules)}"
assert rules[0]["polarity"] == "+", f"Expected +, got {rules[0]['polarity']}"
assert rules[0]["attr"] == "hair", f"Expected 'hair', got {rules[0]['attr']}"
assert rules[0]["colour"] == "red", f"Expected 'red', got {rules[0]['colour']}"
print("test 1 passed: basic rule parsing")

# ---------------------------------------------------------------------------
# 2. Rule parsing: negative rule "must not have blue eyes"
# ---------------------------------------------------------------------------
rules2 = _parse_rule_text("must not have blue eyes")
assert len(rules2) == 1
assert rules2[0]["polarity"] == "-", f"Expected -, got {rules2[0]['polarity']}"
assert rules2[0]["attr"] == "eyes", f"Expected 'eyes', got {rules2[0]['attr']}"
assert rules2[0]["colour"] == "blue", f"Expected 'blue', got {rules2[0]['colour']}"
print("test 2 passed: negative rule parsing")

# ---------------------------------------------------------------------------
# 3. Rule parsing: multiple rules separated by semicolons
# ---------------------------------------------------------------------------
rules3 = _parse_rule_text("must have red hair; must not have green shirt; no hat")
assert len(rules3) == 3, f"Expected 3 rules, got {len(rules3)}"
assert rules3[0]["colour"] == "red"
assert rules3[1]["colour"] == "green"
assert rules3[1]["polarity"] == "-"
assert rules3[2]["attr"] == "hat"
assert rules3[2]["polarity"] == "-"
print("test 3 passed: multi-rule parsing")

# ---------------------------------------------------------------------------
# 4. Rule parsing: empty / bad input
# ---------------------------------------------------------------------------
assert _parse_rule_text("") == [], "Empty string should give no rules"
assert _parse_rule_text(None) == [], "None should give no rules"
assert _parse_rule_text(123) == [], "Non-string should give no rules"
print("test 4 passed: empty/bad input handling")

# ---------------------------------------------------------------------------
# 5. PSN_ContinuityRuleDefiner node: end-to-end
# ---------------------------------------------------------------------------
definer = PSN_ContinuityRuleDefiner()
(result,) = definer.run(character_profile="must have red hair", scene_rules="no background fire")
assert isinstance(result, dict), "rule_set should be a dict"
assert "character_rules" in result
assert "scene_rules" in result
assert "all_rules" in result
assert len(result["character_rules"]) == 1
assert len(result["scene_rules"]) == 1
assert len(result["all_rules"]) == 2
print("test 5 passed: RuleDefiner node")

# ---------------------------------------------------------------------------
# 6. PSN_ContinuityColourCheck: image WITH red hair -> PASS
# ---------------------------------------------------------------------------
# Create a small 8x8x3 image that is mostly red
red_img = torch.zeros(1, 8, 8, 3)
red_img[0, :, :, 0] = 0.80  # R
red_img[0, :, :, 1] = 0.15  # G
red_img[0, :, :, 2] = 0.15  # B

rule_set_red = {
    "character_rules": [{"polarity": "+", "attr": "hair", "colour": "red", "raw": "must have red hair"}],
    "scene_rules": [],
    "all_rules": [{"polarity": "+", "attr": "hair", "colour": "red", "raw": "must have red hair"}],
}

enforcer = PSN_ContinuityColourCheck()
pass_fail, unverified, report = enforcer.run(red_img, rule_set_red)
assert pass_fail is True, f"Expected PASS for red image, got FAIL. Report: {report}"
assert unverified == 0
assert "red pixel fraction over whole image=1.000 -> PASS" in report
assert "checked=1 failed=0 unverified=0" in report
print("test 6 passed: Enforcer PASS on matching image")

# ---------------------------------------------------------------------------
# 7. PSN_ContinuityColourCheck: image WITHOUT red hair -> FAIL
# ---------------------------------------------------------------------------
blue_img = torch.zeros(1, 8, 8, 3)
blue_img[0, :, :, 0] = 0.15
blue_img[0, :, :, 1] = 0.25
blue_img[0, :, :, 2] = 0.85

pass_fail2, _, report2 = enforcer.run(blue_img, rule_set_red)
assert pass_fail2 is False, f"Expected FAIL for blue image, got PASS. Report: {report2}"
assert "red pixel fraction over whole image=0.000 -> FAIL" in report2
print("test 7 passed: Enforcer FAIL on non-matching image")

# ---------------------------------------------------------------------------
# 8. PSN_ContinuityColourCheck: bad input (not a tensor)
# ---------------------------------------------------------------------------
pass_fail3, _, report3 = enforcer.run("not a tensor", rule_set_red)
assert pass_fail3 is False, "Non-tensor input should FAIL"
assert "ERROR" in report3, f"Expected ERROR in report, got: {report3}"
print("test 8 passed: bad input (non-tensor)")

# ---------------------------------------------------------------------------
# 9. PSN_ContinuityColourCheck: bad input (wrong dims)
# ---------------------------------------------------------------------------
bad_img = torch.zeros(8, 8, 3)  # 3-D, missing batch dim
pass_fail4, _, report4 = enforcer.run(bad_img, rule_set_red)
assert pass_fail4 is False, "3-D image should FAIL"
assert "ERROR" in report4
print("test 9 passed: bad input (wrong dims)")

# ---------------------------------------------------------------------------
# 10. PSN_ContinuityColourCheck: empty rule set -> nothing checked, not a pass
# ---------------------------------------------------------------------------
empty_rules = {"character_rules": [], "scene_rules": [], "all_rules": []}
pass_fail5, unv5, report5 = enforcer.run(red_img, empty_rules)
assert pass_fail5 is False, "Empty rule set must not report a pass"
assert "nothing was checked" in report5
print("test 10 passed: empty rule set")

# ---------------------------------------------------------------------------
# 10b. Non-colour rules are UNVERIFIED and never count as passed
# ---------------------------------------------------------------------------
hat_rule = {"polarity": "+", "attr": "hat", "colour": None, "raw": "must have hat"}
only_hat = {"all_rules": [hat_rule]}
pf, unv, rep = enforcer.run(red_img, only_hat)
assert pf is False and unv == 1
assert "UNVERIFIED" in rep and "assumed PASS" not in rep
assert "checked=0 failed=0 unverified=1" in rep
# a colour rule that passes plus a hat rule: pass reflects the colour rule
# only, and the unverified hat is counted separately
mixed = {"all_rules": [rule_set_red["all_rules"][0], hat_rule]}
pf2, unv2, rep2 = enforcer.run(red_img, mixed)
assert pf2 is True and unv2 == 1
assert "checked=1 failed=0 unverified=1" in rep2
# a failing colour rule still fails
pf3, unv3, rep3 = enforcer.run(blue_img, mixed)
assert pf3 is False and unv3 == 1
# negative colour rule: red image must not have red -> FAIL; blue image -> PASS
no_red = {"all_rules": [{"polarity": "-", "attr": "shirt", "colour": "red", "raw": "no red shirt"}]}
assert enforcer.run(red_img, no_red)[0] is False
assert enforcer.run(blue_img, no_red)[0] is True
# the old class and its assumed-pass behaviour are gone
assert not hasattr(mod, "PSN_ContinuityEnforcer")
assert "PSN_ContinuityEnforcer" not in NODE_CLASS_MAPPINGS
print("test 10b passed: unverified rules")

# ---------------------------------------------------------------------------
# 11. NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS exist and are correct
# ---------------------------------------------------------------------------
assert "PSN_ContinuityRuleDefiner" in NODE_CLASS_MAPPINGS
assert "PSN_ContinuityColourCheck" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_ContinuityRuleDefiner"] is PSN_ContinuityRuleDefiner
assert NODE_CLASS_MAPPINGS["PSN_ContinuityColourCheck"] is PSN_ContinuityColourCheck
assert "PSN_ContinuityRuleDefiner" in NODE_DISPLAY_NAME_MAPPINGS
assert "PSN_ContinuityColourCheck" in NODE_DISPLAY_NAME_MAPPINGS
print("test 11 passed: node mappings")

# ---------------------------------------------------------------------------
# 12. INPUT_TYPES classmethod returns proper dict
# ---------------------------------------------------------------------------
it1 = PSN_ContinuityRuleDefiner.INPUT_TYPES()
assert "required" in it1
assert "character_profile" in it1["required"]
assert "scene_rules" in it1["required"]

it2 = PSN_ContinuityColourCheck.INPUT_TYPES()
assert "required" in it2
assert "generated_asset" in it2["required"]
assert "rule_set" in it2["required"]
print("test 12 passed: INPUT_TYPES")

# ---------------------------------------------------------------------------
# 13. RETURN_TYPES and FUNCTION are correct
# ---------------------------------------------------------------------------
assert PSN_ContinuityRuleDefiner.RETURN_TYPES == ("PSN_RULE_SET",)
assert PSN_ContinuityRuleDefiner.FUNCTION == "run"
assert PSN_ContinuityColourCheck.RETURN_TYPES == ("BOOLEAN", "INT", "STRING")
assert PSN_ContinuityColourCheck.FUNCTION == "run"
print("test 13 passed: RETURN_TYPES / FUNCTION")

# ---------------------------------------------------------------------------
# 14. Colour fraction helper: red image has high red fraction
# ---------------------------------------------------------------------------
frac = _colour_fraction(red_img, "red")
assert frac > 0.9, f"Expected high red fraction, got {frac}"
frac_blue = _colour_fraction(red_img, "blue")
assert frac_blue < 0.1, f"Expected low blue fraction, got {frac_blue}"
print("test 14 passed: colour fraction helper")

# ---------------------------------------------------------------------------
# 15. 4-channel image (RGBA) is handled correctly
# ---------------------------------------------------------------------------
rgba_img = torch.zeros(1, 8, 8, 4)
rgba_img[0, :, :, 0] = 0.80
rgba_img[0, :, :, 1] = 0.15
rgba_img[0, :, :, 2] = 0.15
rgba_img[0, :, :, 3] = 1.0  # alpha

pass_fail6, _, report6 = enforcer.run(rgba_img, rule_set_red)
assert pass_fail6 is True, f"RGBA red image should PASS. Report: {report6}"
print("test 15 passed: RGBA image handling")

print("ok")
