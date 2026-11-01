"""PSN Device Layer Plan.

Writes a round-robin layer-to-device text plan from a comma-separated device
list. It does not load, move or split any model, measure VRAM or run on
several devices.
"""

CAT = "ParametricStudio/MultiGPU"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _parse_device_map(device_map: str):
    """Parse a comma-separated device map string into a list of device names.

    Accepts e.g. ``"cuda:0,cuda:1"`` or ``"cpu"``.
    Returns a list of strings.
    """
    if not isinstance(device_map, str) or not device_map.strip():
        raise ValueError("device_map must be a non-empty string")
    parts = [p.strip() for p in device_map.split(",") if p.strip()]
    if not parts:
        raise ValueError("device_map must contain at least one device")
    return parts


def _validate_device(dev: str):
    """Validate a single device string."""
    if dev == "cpu":
        return
    if dev.startswith("cuda:"):
        idx = dev[5:]
        if not idx.isdigit():
            raise ValueError(f"Invalid cuda device index: {dev!r}")
        return
    if dev == "cuda":
        return
    raise ValueError(f"Unknown device: {dev!r}")


def _compute_layer_assignment(num_layers: int, devices: list):
    """Compute which layers go to which device using round-robin.

    Returns a list of lists: assignment[i] = list of layer indices on device i.
    """
    n = len(devices)
    assignment = [[] for _ in range(n)]
    for layer_idx in range(num_layers):
        assignment[layer_idx % n].append(layer_idx)
    return assignment


# ---------------------------------------------------------------------------
# Node: PSN_Device_Layer_Plan
# ---------------------------------------------------------------------------

class PSN_Device_Layer_Plan:
    """Round-robin layer-to-device text plan from a device list.

    Takes no model and moves nothing; the output is a text plan only.
    """

    DESCRIPTION = (
        "Writes a round-robin layer-to-device text plan from a comma-separated "
        "device list and a layer count. It does not move or split any model, "
        "estimate memory or run on several devices."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "device_map": ("STRING", {"default": "cuda:0,cuda:1"}),
                "num_layers": ("INT", {"default": 32, "min": 1, "max": 1024}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("layer_plan",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, device_map, num_layers):
        devices = _parse_device_map(device_map)
        for d in devices:
            _validate_device(d)

        assignment = _compute_layer_assignment(num_layers, devices)
        lines = [f"Device map: {', '.join(devices)}"]
        for dev, layers in zip(devices, assignment):
            lines.append(f"  {dev}: layers {layers}")
        return ("\n".join(lines),)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Device_Layer_Plan": PSN_Device_Layer_Plan,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Device_Layer_Plan": "Device Layer Plan (text only)",
}
