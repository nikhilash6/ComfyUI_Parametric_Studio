"""PSN_WorkflowBundle: bundle a loader output, a controller dict and a sampler input into one dict.

This is a pass-through node. It checks only that controller_settings is a dict and
that loader_output and sampler_input are not None, then returns them together as
{"loader", "controller", "sampler"}. It does not check what the loader or sampler
values are, and it enforces no workflow order or structure.

No GPU, torch, ComfyUI internals, network, file I/O, or subprocess usage. Only pure Python standard
library (json) is used for serialization.
"""

import json

class _AnyType(str):
    """ComfyUI wildcard socket type: compares equal to every type."""
    def __ne__(self, other): return False
ANY = _AnyType("*")


CAT = "ParametricStudio/Structure"


class PSN_WorkflowBundle:
    """Bundle a loader output, a controller dict and a sampler input into one dict.

    The only checks: controller_settings is a dict, and loader_output and
    sampler_input are not None. Nothing else about the values is validated.
    """

    DESCRIPTION = (
        "Bundles loader output, controller dict and sampler input into one dict; inputs_present only means the "
        "controller is a dict and the other two inputs are not None."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "loader_output": (ANY,),
                "controller_settings": ("DICT",),
                "sampler_input": (ANY,),
            },
            "optional": {
                "log_structure": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("DICT", "BOOLEAN")
    RETURN_NAMES = ("bundled_data", "inputs_present")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, loader_output, controller_settings, sampler_input, log_structure=False):
        """Bundle the three inputs after checking the controller is a dict and the others are not None.

        Args:
            loader_output: Output from the Loader section.
            controller_settings: Settings from the Controller section (must be a dict).
            sampler_input: Input to the Sampler section.
            log_structure: If True, include a serialized structure summary in the output.

        Returns:
            Tuple of (bundled_data, inputs_present)
        """
        # Validate controller_settings is a dict
        if not isinstance(controller_settings, dict):
            return ({}, False)

        # Only presence is checked (not None); the values themselves are not inspected
        if loader_output is None or sampler_input is None:
            return ({}, False)

        # Build the bundle
        structured_data = {
            "loader": loader_output,
            "controller": controller_settings,
            "sampler": sampler_input,
        }

        # Optionally include a serialized structure summary for debugging
        if log_structure:
            try:
                # Create a safe summary that only includes types and keys, not full values
                summary = {
                    "loader_type": type(loader_output).__name__,
                    "controller_keys": list(controller_settings.keys()),
                    "sampler_type": type(sampler_input).__name__,
                }
                structured_data["structure_summary"] = json.dumps(summary, sort_keys=True)
            except (TypeError, ValueError):
                # If serialization fails, just omit the summary
                pass

        return (structured_data, True)


# ComfyUI node mappings
NODE_CLASS_MAPPINGS = {
    "PSN_WorkflowBundle": PSN_WorkflowBundle,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_WorkflowBundle": "PSN Workflow Bundle (loader, controller, sampler)",
}
