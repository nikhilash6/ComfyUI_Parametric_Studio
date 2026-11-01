"""PSN Workflow Preset Management nodes for ComfyUI.

Provides PSN_PresetLoader (JSON text -> graph dict) and
PSN_Preset_Json_Build (graph dict -> JSON text). Neither reads or writes
files.
"""

import json

CAT = "ParametricStudio/PresetManagement"


def _validate_graph(graph):
    """Validate that a graph dict has the expected structure."""
    if not isinstance(graph, dict):
        raise ValueError("Graph must be a dict, got %s" % type(graph).__name__)
    if "nodes" not in graph:
        raise ValueError("Graph must contain a 'nodes' key")
    if not isinstance(graph["nodes"], list):
        raise ValueError("Graph 'nodes' must be a list")
    for i, node in enumerate(graph["nodes"]):
        if not isinstance(node, dict):
            raise ValueError("Node at index %d must be a dict" % i)
        if "id" not in node:
            raise ValueError("Node at index %d missing 'id'" % i)
        if "type" not in node:
            raise ValueError("Node at index %d missing 'type'" % i)
    return True


def _deep_copy(obj):
    """Deep copy via JSON round-trip (only JSON-serializable data)."""
    return json.loads(json.dumps(obj))


class PSN_PresetLoader:
    """Loads a predefined workflow preset from a JSON string.

    The preset is passed as a JSON-encoded string (since direct file I/O
    is not available in this sandbox). The preset_dir is accepted for
    compatibility but not used for actual I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "preset_name": ("STRING", {"default": "default"}),
                "preset_dir": ("STRING", {"default": "./presets"}),
                "preset_json": ("STRING", {"default": "{}"}),
            }
        }

    RETURN_TYPES = ("GRAPH",)
    RETURN_NAMES = ("GRAPH",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, preset_name, preset_dir, preset_json):
        if not isinstance(preset_name, str):
            raise ValueError("preset_name must be a string")
        if not isinstance(preset_dir, str):
            raise ValueError("preset_dir must be a string")
        if not isinstance(preset_json, str):
            raise ValueError("preset_json must be a string")

        try:
            graph = json.loads(preset_json)
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON in preset_json: %s" % e)

        _validate_graph(graph)

        # Return a deep copy so the caller cannot mutate our internal state
        return (_deep_copy(graph),)


class PSN_Preset_Json_Build:
    """Serializes a workflow graph to preset JSON text.

    Returns the JSON string (sorted keys, 2-space indent) for the next node
    to use. Writes no file and chooses no path.
    """

    DESCRIPTION = ("Builds preset JSON text from a workflow graph and returns "
                   "it. Writes no file and returns no path.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph": ("GRAPH",),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("preset_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph):
        _validate_graph(graph)
        return (json.dumps(graph, sort_keys=True, indent=2),)


NODE_CLASS_MAPPINGS = {
    "PSN_PresetLoader": PSN_PresetLoader,
    "PSN_Preset_Json_Build": PSN_Preset_Json_Build,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PresetLoader": "PSN Preset Loader",
    "PSN_Preset_Json_Build": "PSN Build Preset JSON Text",
}
