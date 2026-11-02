"""fill_dynamic: nested choices of a V3 dynamic combo go under their dotted names; a bare copy only where the node takes that name. No live ports."""
from studio import apps as A

RESIZE = {"input": {"required": {"input": ["IMAGE", {}], "resize_type": ["COMFY_DYNAMICCOMBO_V3", {"options": [{"key": "scale dimensions", "inputs": {"required": {"width": ["INT", {"default": 512}], "height": ["INT", {"default": 512}], "crop": [["center", "disabled"], {}]}}}]}], "scale_method": [["area"], {}]}}}
SAVE = {"input": {"required": {"video": ["VIDEO", {}], "format": ["COMFY_DYNAMICCOMBO_V3", {"options": [{"key": "auto", "inputs": {"required": {"codec": ["COMFY_DYNAMICCOMBO_V3", {"options": [{"key": "auto", "inputs": {"required": {}}}]}]}}}]}]}, "optional": {"codec": ["COMFY_DYNAMICCOMBO_V3", {"hidden": True, "options": [{"key": "auto", "inputs": {"required": {}}}]}]}}}


def test_a_nested_value_is_not_copied_to_a_name_the_node_does_not_take():
    g = {"r": {"class_type": "ResizeImageMaskNode", "inputs": {"input": ["x", 0], "resize_type": "scale dimensions", "resize_type.width": 544, "resize_type.height": 832, "resize_type.crop": "center", "scale_method": "area"}}}
    A.fill_dynamic(g, {"ResizeImageMaskNode": RESIZE})
    ins = g["r"]["inputs"]; assert ins["resize_type.width"] == 544 and "width" not in ins and "height" not in ins and "crop" not in ins


def test_a_bare_name_left_by_an_earlier_fill_is_removed():
    g = {"r": {"class_type": "ResizeImageMaskNode", "inputs": {"input": ["x", 0], "resize_type": "scale dimensions", "resize_type.width": 544, "width": 544}}}
    A.fill_dynamic(g, {"ResizeImageMaskNode": RESIZE}); assert "width" not in g["r"]["inputs"]


def test_save_video_keeps_its_bare_codec():
    g = {"s": {"class_type": "SaveVideo", "inputs": {"video": ["v", 0], "filename_prefix": "x", "format": "auto"}}}
    A.fill_dynamic(g, {"SaveVideo": SAVE}); ins = g["s"]["inputs"]; assert ins["format.codec"] == "auto" and ins.get("codec") == "auto"


def test_an_unwired_subgraph_input_takes_the_inner_widget_value():
    from studio.ui2api import ui_to_api
    oi = {"PrimitiveInt": {"input": {"required": {"value": ["INT", {"default": 0}]}}},
          "ImageFromBatch": {"input": {"required": {"image": ["IMAGE", {}], "batch_index": ["INT", {}], "length": ["INT", {}]}}},
          "ComfyMathExpression": {"input": {"required": {"expression": ["STRING", {}]}, "optional": {"values.a": ["INT", {"forceInput": True}], "values.b": ["INT", {"forceInput": True}]}}},
          "LoadImage": {"input": {"required": {"image": [["a.png"], {}]}}}, "PreviewAny": {"input": {"required": {"source": ["*", {}]}}}}
    sub = {"id": "S", "name": "s", "inputs": [{"name": "length", "type": "INT"}], "outputs": [{"name": "o", "type": "INT"}],
           "nodes": [{"id": 1, "type": "ImageFromBatch", "inputs": [{"name": "image", "link": None}, {"name": "length", "link": 11}], "widgets_values": [0, 81]},
                     {"id": 2, "type": "ComfyMathExpression", "inputs": [{"name": "values.b", "link": 12}], "widgets_values": ["b * 2"]}],
           "links": [{"id": 11, "origin_id": -10, "origin_slot": 0, "target_id": 1, "target_slot": 1}, {"id": 12, "origin_id": -10, "origin_slot": 0, "target_id": 2, "target_slot": 0}, {"id": 13, "origin_id": 2, "origin_slot": 0, "target_id": -20, "target_slot": 0}]}
    ui = {"nodes": [{"id": 5, "type": "S", "inputs": [{"name": "length", "link": None}], "widgets_values": []}, {"id": 6, "type": "PreviewAny", "inputs": [{"name": "source", "link": 20}]}],
          "links": [[20, 5, 0, 6, 0, "INT"]], "definitions": {"subgraphs": [sub]}}
    g, _ = ui_to_api(ui, oi); assert g["5:2"]["inputs"]["values.b"] == 81
