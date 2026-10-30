"""Newer ComfyUI templates: V3 dynamic combos store their nested widgets inline, and sub-graph instances may keep promoted values with no proxy list."""
from studio.ui2api import ui_to_api
OI = {"ResizeImageMaskNode": {"input": {"required": {"input": ["IMAGE", {}], "resize_type": ["COMFY_DYNAMICCOMBO_V3", {"options": [{"key": "scale by multiplier", "inputs": {"required": {"multiplier": ["FLOAT", {"default": 1.0}]}}}, {"key": "scale dimensions", "inputs": {"required": {"width": ["INT", {"default": 512}], "height": ["INT", {"default": 512}], "crop": ["COMBO", {"options": ["disabled", "center"]}]}}}]}], "scale_method": [["area", "lanczos"], {}]}}},
      "SaveVideo": {"input": {"required": {"filename_prefix": ["STRING", {"default": "v"}], "format": ["COMFY_DYNAMICCOMBO_V3", {"options": [{"key": "auto", "inputs": {"required": {"codec": [["auto"], {}]}}}]}]}}},
      "Enc": {"input": {"required": {"prompt": ["STRING", {}], "seed": ["INT", {"control_after_generate": True}], "width": ["INT", {}]}}}}
def node(i, t, wv, inputs=None): return {"id": i, "type": t, "widgets_values": wv, "inputs": inputs or []}
def test_nested_widgets_do_not_shift_the_next_widget():
    g, p = ui_to_api({"nodes": [node(1, "ResizeImageMaskNode", ["scale dimensions", 640, 360, "center", "lanczos"])], "links": []}, OI)
    assert not p and g["1"]["inputs"] == {"resize_type": "scale dimensions", "resize_type.width": 640, "resize_type.height": 360, "resize_type.crop": "center", "scale_method": "lanczos"}
    g, _ = ui_to_api({"nodes": [node(1, "ResizeImageMaskNode", ["scale by multiplier", 2, "area"])], "links": []}, OI)
    assert g["1"]["inputs"] == {"resize_type": "scale by multiplier", "resize_type.multiplier": 2, "scale_method": "area"}
def test_an_implicit_dynamic_combo_takes_its_first_option_and_defaults():
    g, _ = ui_to_api({"nodes": [node(1, "SaveVideo", ["out"])], "links": []}, OI)
    assert g["1"]["inputs"]["format"] == "auto" and g["1"]["inputs"]["format.codec"] == "auto"
def test_control_after_generate_still_takes_a_slot():
    g, _ = ui_to_api({"nodes": [node(1, "Enc", ["hi", 7, "fixed", 512])], "links": []}, OI)
    assert g["1"]["inputs"] == {"prompt": "hi", "seed": 7, "width": 512}
def test_promoted_values_follow_the_sub_graphs_own_inputs_and_skip_seed_controls():
    sub = {"id": "S", "name": "S", "inputs": [{"name": "picture"}, {"name": "prompt"}, {"name": "seed"}, {"name": "width"}], "outputs": [], "links": [[3, -10, 0, 6, 0, "IMAGE"], [1, -10, 1, 5, 0, "STRING"], [4, -10, 2, 5, 1, "INT"], [2, -10, 3, 5, 2, "INT"]],
           "nodes": [node(6, "Enc", [], [{"name": "image", "link": 3}]), node(5, "Enc", ["leftover prompt", 1, "fixed", 99], [{"name": "prompt", "link": 1, "widget": {"name": "prompt"}}, {"name": "seed", "link": 4, "widget": {"name": "seed"}}, {"name": "width", "link": 2, "widget": {"name": "width"}}])]}
    ex = {}; g, p = ui_to_api({"nodes": [node(9, "S", ["my prompt", 42, "randomize", 1024], [{"name": "picture", "link": None}])], "links": [], "definitions": {"subgraphs": [sub]}}, OI, ex)
    assert not p and (g["9:5"]["inputs"]["prompt"], g["9:5"]["inputs"]["seed"], g["9:5"]["inputs"]["width"]) == ("my prompt", 42, 1024) and ex[("9", "prompt")] == [("9:5", "prompt")]
def test_a_bypassed_node_hands_its_input_through():
    OI2 = {"Src": {"input": {"required": {}}}, "Fx": {"input": {"required": {"image": ["IMAGE", {}]}}}, "Dst": {"input": {"required": {"image": ["IMAGE", {}]}}}}
    ui = {"nodes": [{"id": 1, "type": "Src", "outputs": [{"type": "IMAGE"}]}, {"id": 2, "type": "Fx", "mode": 4, "inputs": [{"name": "image", "type": "IMAGE", "link": 10}], "outputs": [{"type": "IMAGE"}]}, {"id": 3, "type": "Dst", "inputs": [{"name": "image", "type": "IMAGE", "link": 11}]}], "links": [[10, 1, 0, 2, 0, "IMAGE"], [11, 2, 0, 3, 0, "IMAGE"]]}
    g, p = ui_to_api(ui, OI2)
    assert not p and "2" not in g and g["3"]["inputs"]["image"] == ["1", 0]
