"""ParametricStudio - Subgraph Port and Dict Router.

Implemented (torch / stdlib only):
  * PSN_SubgraphPort   - typed entry/exit point; validates data types and
                         passes values through unchanged (no in-place edits).
  * PSN_Dict_Router    - validates the entries of an input dict against an
                         input_map, renames them according to an output_map and
                         returns the result.  It runs no stages and no nested
                         graph: values are only checked, copied and renamed.

NOT implemented:
  * Any execution of pipeline stages or nested ComfyUI nodes.
  * "Use Everywhere" auto-linking for MODEL/CLIP/VAE.
  * pydantic schema validation of input/output maps (lightweight manual
    validation is used instead).
"""

import torch

CAT = "ParametricStudio/Subgraphs"

# Canonical ComfyUI tensor types we know how to validate.
_TENSOR_TYPES = {
    "IMAGE": (4, "[B,H,W,C]"),   # float tensor, values in 0..1
    "MASK": (3, "[B,H,W]"),      # float tensor
    "LATENT": (4, "[B,C,H,W]"),  # dict {"samples": tensor}

}


def _is_image(x):
    return (
        isinstance(x, torch.Tensor)
        and x.dim() == 4
        and x.is_floating_point()
        and bool(((x >= 0.0) & (x <= 1.0)).all())
    )


def _is_mask(x):
    return isinstance(x, torch.Tensor) and x.dim() == 3 and x.is_floating_point()


def _is_latent(x):
    return (
        isinstance(x, dict)
        and "samples" in x
        and isinstance(x["samples"], torch.Tensor)
        and x["samples"].dim() == 4
    )


_VALIDATORS = {
    "IMAGE": _is_image,
    "MASK": _is_mask,
    "LATENT": _is_latent,
    "MODEL": lambda x: x is not None,
    "CLIP": lambda x: x is not None,
    "VAE": lambda x: x is not None,
    "STRING": lambda x: isinstance(x, str),
    "INT": lambda x: isinstance(x, int) and not isinstance(x, bool),
    "FLOAT": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
    "DYNAMIC": lambda x: True,
}


def _validate(data_type, value):
    """Return (ok, message)."""
    fn = _VALIDATORS.get(data_type)
    if fn is None:
        return False, "unknown data type: %r" % (data_type,)
    if not fn(value):
        return False, "value does not match type %s" % (data_type,)
    return True, ""


def _clone(value):
    """Deep-copy tensor-bearing values so inputs are never mutated."""
    if isinstance(value, torch.Tensor):
        return value.clone()
    if isinstance(value, dict):
        return {k: _clone(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clone(v) for v in value]
    return value


class PSN_SubgraphPort:
    """Typed entry/exit point for a subgraph.

    Validates that the incoming value matches the declared data type and
    passes a copy through, guaranteeing type safety between the parent
    graph and the subgraph.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "port_name": ("STRING", {"default": "in_0"}),
                "data_type": (
                    sorted(_VALIDATORS.keys()),
                    {"default": "DYNAMIC"},
                ),
                "value": ("DYNAMIC",),
            }
        }

    RETURN_TYPES = ("DYNAMIC", "STRING")
    RETURN_NAMES = ("port_value", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, port_name, data_type, value):
        if not isinstance(port_name, str) or not port_name.strip():
            return (_clone(value), "error: port_name must be a non-empty string")
        ok, msg = _validate(data_type, value)
        if not ok:
            return (_clone(value), "error: %s" % msg)
        return (_clone(value), "ok")


class PSN_Dict_Router:
    """Validate and rename dict entries between an input_map and an output_map.

    `input_map`  : {external_name: (internal_name, data_type)}
    `output_map` : {external_name: (internal_name, data_type)}

    Each entry of `inputs` named in input_map is type-checked and copied under
    its internal name.  Each output_map entry then takes the value held under
    its internal name (type-checked again) and appears under its external
    name.  No stage, model or nested graph is run.
    """

    DESCRIPTION = (
        "Validates and renames dict entries between input_map and output_map. "
        "Runs no stages."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "router_id": ("STRING", {"default": "sg_0"}),
                "input_map": ("DICT", {"default": {}}),
                "output_map": ("DICT", {"default": {}}),
                "inputs": ("DYNAMIC",),
            }
        }

    RETURN_TYPES = ("DYNAMIC", "STRING")
    RETURN_NAMES = ("routed_dict", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    @staticmethod
    def _parse_map(raw, kind):
        """Accept {name: (internal, type)} or {name: type} or {name: internal}."""
        if not isinstance(raw, dict):
            raise ValueError("%s map must be a dict" % kind)
        parsed = {}
        for name, spec in raw.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("%s map keys must be non-empty strings" % kind)
            if isinstance(spec, str):
                parsed[name] = (name, spec)
            elif isinstance(spec, (list, tuple)) and len(spec) == 2:
                internal, dtype = spec
                if not isinstance(internal, str) or not isinstance(dtype, str):
                    raise ValueError("%s map values must be (name, type) pairs" % kind)
                parsed[name] = (internal, dtype)
            else:
                raise ValueError("%s map values must be a type string or (name, type)" % kind)
        return parsed

    def run(self, router_id, input_map, output_map, inputs):
        if not isinstance(router_id, str) or not router_id.strip():
            return ({}, "error: router_id must be a non-empty string")
        try:
            in_spec = self._parse_map(input_map, "input")
            out_spec = self._parse_map(output_map, "output")
        except ValueError as exc:
            return ({}, "error: %s" % exc)

        if not isinstance(inputs, dict):
            return ({}, "error: inputs must be a dict")

        # Validate and copy inputs under their internal names.
        routed = {}
        for ext, (internal, dtype) in in_spec.items():
            if ext not in inputs:
                return ({}, "error: missing input %r" % ext)
            ok, msg = _validate(dtype, inputs[ext])
            if not ok:
                return ({}, "error: input %r: %s" % (ext, msg))
            routed[internal] = _clone(inputs[ext])

        # Rename to the external output names.
        result = {}
        for ext, (internal, dtype) in out_spec.items():
            if internal not in routed:
                return ({}, "error: no routed entry named %r" % internal)
            ok, msg = _validate(dtype, routed[internal])
            if not ok:
                return ({}, "error: output %r: %s" % (ext, msg))
            result[ext] = _clone(routed[internal])

        return (result, "routed %d entries" % len(result))


NODE_CLASS_MAPPINGS = {
    "PSN_SubgraphPort": PSN_SubgraphPort,
    "PSN_Dict_Router": PSN_Dict_Router,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SubgraphPort": "Subgraph Port",
    "PSN_Dict_Router": "Dict Router",
}
