"""ComfyUI custom node: Multi-View 2D Shift Preview.

Makes several copies of an image, each rolled (rotated in the image plane)
and/or shifted sideways or up and down with plain 2D geometry. There is no
model and no 3D, so the copies are not new camera views of the subject.
"""

import json
import math

import torch

CAT = "ParametricStudio/MultiView"


def _as_tensor(x):
    """Ensure x is a torch tensor."""
    if isinstance(x, torch.Tensor):
        return x
    raise TypeError(f"Expected torch.Tensor, got {type(x)}")


def _validate_image(image):
    """Validate that image is a proper IMAGE tensor [B,H,W,C] in 0..1."""
    t = _as_tensor(image)
    if t.dim() != 4:
        raise ValueError(f"IMAGE must be 4D [B,H,W,C], got {t.dim()}D")
    if t.shape[-1] not in (1, 3, 4):
        raise ValueError(f"IMAGE last dim must be 1, 3 or 4, got {t.shape[-1]}")
    if t.min() < -1e-6 or t.max() > 1 + 1e-6:
        raise ValueError("IMAGE values must be in [0, 1]")
    return t


def _parse_angles(angles_str):
    """Parse angles JSON string into a list of angle dicts.
    
    Expected format: list of dicts with keys like 'yaw', 'pitch', 'roll'
    or a single dict that will be repeated.
    Returns a list of dicts, one per view.
    """
    if not isinstance(angles_str, str):
        raise TypeError(f"angles must be a JSON string, got {type(angles_str)}")
    
    try:
        data = json.loads(angles_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in angles: {e}")
    
    if isinstance(data, dict):
        # Single angle spec, repeat for all views
        return [data]
    elif isinstance(data, list):
        if not all(isinstance(d, dict) for d in data):
            raise ValueError("angles list must contain only dicts")
        return data
    else:
        raise ValueError(f"angles must be a JSON object or list of objects, got {type(data)}")


def _apply_rotation_2d(img, angle_deg):
    """Apply 2D rotation to an image tensor [H,W,C] by angle_deg degrees.
    
    Uses bilinear interpolation via torch grid_sample.
    """
    H, W, C = img.shape
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    # Create grid in normalized coordinates [-1, 1]
    grid_y, grid_x = torch.meshgrid(
        torch.linspace(-1, 1, H, device=img.device),
        torch.linspace(-1, 1, W, device=img.device),
        indexing='ij'
    )
    
    # Rotation matrix (inverse for sampling)
    # x' = cos*x + sin*y
    # y' = -sin*x + cos*y
    src_x = cos_a * grid_x + sin_a * grid_y
    src_y = -sin_a * grid_x + cos_a * grid_y
    
    # Stack to [H, W, 2]
    grid = torch.stack([src_x, src_y], dim=-1)
    
    # grid_sample expects [N, C, H, W] and grid [N, H_out, W_out, 2]
    img_4d = img.unsqueeze(0).permute(0, 3, 1, 2)  # [1, C, H, W]
    grid_4d = grid.unsqueeze(0)  # [1, H, W, 2]
    
    rotated = torch.nn.functional.grid_sample(
        img_4d, grid_4d, mode='bilinear', padding_mode='zeros', align_corners=True
    )
    
    # Back to [H, W, C]
    rotated = rotated.permute(0, 2, 3, 1).squeeze(0)
    return rotated


def _apply_shift(img, shift_x, shift_y):
    """Translate the image by shifting the sampling grid (zeros fill the border).
    
    shift_x, shift_y are in range [-1, 1] representing how much to shift.
    """
    H, W, C = img.shape
    
    # Create grid
    grid_y, grid_x = torch.meshgrid(
        torch.linspace(-1, 1, H, device=img.device),
        torch.linspace(-1, 1, W, device=img.device),
        indexing='ij'
    )
    
    # Shift the sampling grid
    src_x = grid_x + shift_x * 0.3
    src_y = grid_y + shift_y * 0.3
    
    grid = torch.stack([src_x, src_y], dim=-1)
    
    img_4d = img.unsqueeze(0).permute(0, 3, 1, 2)
    grid_4d = grid.unsqueeze(0)
    
    shifted = torch.nn.functional.grid_sample(
        img_4d, grid_4d, mode='bilinear', padding_mode='zeros', align_corners=True
    )
    
    shifted = shifted.permute(0, 2, 3, 1).squeeze(0)
    return shifted


def _make_view(image_single, angle_spec, view_index, num_views):
    """Make one rolled/shifted copy of the input image from the angle spec.
    
    image_single: [H, W, C] tensor
    angle_spec: dict with optional 'yaw', 'pitch', 'roll' keys (degrees)
    view_index: int
    num_views: int
    """
    H, W, C = image_single.shape
    
    yaw = angle_spec.get('yaw', 0.0)
    pitch = angle_spec.get('pitch', 0.0)
    roll = angle_spec.get('roll', 0.0)
    
    # If no angles specified, distribute evenly
    if yaw == 0.0 and pitch == 0.0 and roll == 0.0 and num_views > 1:
        yaw = (view_index / num_views) * 360.0
    
    result = image_single.clone()
    
    # Apply roll (2D rotation)
    if roll != 0.0:
        result = _apply_rotation_2d(result, roll)
    
    # Apply yaw as a horizontal shift
    if yaw != 0.0:
        shift_x = math.sin(math.radians(yaw)) * 0.5
        result = _apply_shift(result, shift_x, 0.0)
    
    # Apply pitch as a vertical shift
    if pitch != 0.0:
        shift_y = math.sin(math.radians(pitch)) * 0.5
        result = _apply_shift(result, 0.0, shift_y)
    
    # Clamp to [0, 1]
    result = torch.clamp(result, 0.0, 1.0)
    
    return result


class PSN_MultiView_Shift_Preview:
    """Make several rolled/shifted copies of an image with 2D geometry.

    Roll rotates in the image plane; yaw and pitch only translate the image
    horizontally and vertically (zeros fill the border). No model, no 3D.
    """

    DESCRIPTION = (
        "Rolls and shifts the input image once per view with 2D geometry. "
        "Runs no model and no 3D, so the outputs are not new camera views of "
        "the subject."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "num_views": ("INT", {"default": 4, "min": 1, "max": 32}),
                "angles": ("STRING", {"default": "[]", "multiline": True}),
            },
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("shifted_copies",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, image, num_views, angles):
        """Make num_views rolled/shifted copies of each input image."""
        # Validate image
        img = _validate_image(image)
        
        # Validate num_views
        if num_views < 1:
            raise ValueError(f"num_views must be >= 1, got {num_views}")
        if num_views > 32:
            raise ValueError(f"num_views must be <= 32, got {num_views}")
        
        # Parse angles
        angle_specs = _parse_angles(angles)
        
        # If fewer angle specs than num_views, cycle through them
        # If more, truncate
        if len(angle_specs) == 0:
            angle_specs = [{}] * num_views
        elif len(angle_specs) < num_views:
            # Repeat the specs to fill num_views
            extended = []
            i = 0
            while len(extended) < num_views:
                extended.append(angle_specs[i % len(angle_specs)])
                i += 1
            angle_specs = extended
        else:
            angle_specs = angle_specs[:num_views]
        
        # Process each image in the batch
        B = img.shape[0]
        views = []
        
        for b in range(B):
            for v in range(num_views):
                view = _make_view(img[b], angle_specs[v], v, num_views)
                views.append(view)
        
        # Stack into batch [B * num_views, H, W, C]
        result = torch.stack(views, dim=0)
        
        return (result,)


NODE_CLASS_MAPPINGS = {
    "PSN_MultiView_Shift_Preview": PSN_MultiView_Shift_Preview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MultiView_Shift_Preview": "Multi-View 2D Shift Preview",
}
