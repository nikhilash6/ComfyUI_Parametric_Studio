"""
PSN_Random_Image_Selector

Random image selector. It never opens or loads an image and uses no GPU.

It does read one directory listing: when no file_names are supplied, it lists
folder_path (non-recursive, via os.listdir) and keeps the files with an image
extension (.png .jpg .jpeg .webp .bmp .gif .tif .tiff), sorted by name.
If file_names is supplied it is used as given and the folder is not read.

The node:
- Validates that a folder path is a non-empty string
- Validates that num_images is a positive integer
- Validates that seed (if provided) is an integer
- Shuffles the file names using the provided seed (or a random seed if none is
  given) and selects the first num_images entries

Inputs:
    folder_path (STRING): The folder to list when file_names is not given, and
        the prefix of the returned file_paths
    num_images (INT): Number of images to select (must be >= 1)
    seed (INT, optional): Random seed for reproducibility
    file_names (LIST[STRING], optional): File names to choose from instead of
        listing the folder

Outputs:
    selected_indices (LIST[INT]): Indices into the file name list used
    selected_file_names (LIST[STRING]): The selected file names
    file_paths (LIST[STRING]): Full paths constructed from folder_path + file name
    reason (STRING): Human-readable explanation of the selection or error
"""

import os
import random
import string

# File extensions treated as images when listing a folder.
_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff")

# Allowed characters for file names (basic validation)
_ALLOWED_FILE_CHARS = set(string.ascii_letters + string.digits + "._-")

# Allowed characters for folder path segments
_ALLOWED_PATH_CHARS = set(string.ascii_letters + string.digits + "._-/\\")


def _validate_folder_path(folder_path):
    """
    Validate that folder_path is a non-empty string with reasonable characters.
    Returns (is_valid, error_message).
    """
    if not isinstance(folder_path, str):
        return False, "folder_path must be a string"
    if not folder_path.strip():
        return False, "folder_path must not be empty"
    # Check for null bytes or control characters
    for ch in folder_path:
        if ord(ch) < 32 or ord(ch) == 127:
            return False, "folder_path contains invalid control characters"
    return True, ""


def _validate_num_images(num_images):
    """
    Validate that num_images is a positive integer.
    Returns (is_valid, error_message).
    """
    if not isinstance(num_images, int) or isinstance(num_images, bool):
        return False, "num_images must be an integer"
    if num_images < 1:
        return False, "num_images must be at least 1"
    return True, ""


def _validate_seed(seed):
    """
    Validate that seed is an integer or None.
    Returns (is_valid, error_message).
    """
    if seed is None:
        return True, ""
    if not isinstance(seed, int) or isinstance(seed, bool):
        return False, "seed must be an integer or None"
    return True, ""


def _validate_file_names(file_names):
    """
    Validate that file_names is a list of strings.
    Returns (is_valid, error_message).
    """
    if file_names is None:
        return True, ""  # No file names provided; selection will be empty
    if not isinstance(file_names, (list, tuple)):
        return False, "file_names must be a list of strings"
    for i, name in enumerate(file_names):
        if not isinstance(name, str):
            return False, f"file_names[{i}] must be a string"
        if not name.strip():
            return False, f"file_names[{i}] must not be empty"
    return True, ""


def _list_image_files(folder_path):
    """Sorted names of the image files directly inside folder_path ([] if it cannot be read)."""
    try:
        names = os.listdir(folder_path)
    except OSError:
        return []
    return sorted(
        n for n in names
        if n.lower().endswith(_IMAGE_EXTENSIONS) and os.path.isfile(os.path.join(folder_path, n))
    )


def select_random_images(folder_path, num_images, seed, file_names=None):
    """
    Core selection logic: given a list of file names, shuffle and select
    the first num_images entries.

    Args:
        folder_path: Validated folder path string
        num_images: Validated positive integer
        seed: Optional integer seed for reproducibility
        file_names: Optional list of file name strings

    Returns:
        (selected_indices, selected_file_names, file_paths, reason)
    """
    if file_names is None:
        file_names = []

    if not file_names:
        return [], [], [], "No files available in folder"

    # Clamp num_images to available count
    actual_count = min(num_images, len(file_names))

    # Create a list of indices and shuffle
    indices = list(range(len(file_names)))

    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    rng.shuffle(indices)

    selected_indices = indices[:actual_count]
    selected_file_names = [file_names[i] for i in selected_indices]

    # Construct full paths
    normalized_folder = folder_path.rstrip("/\\")
    file_paths = [f"{normalized_folder}/{name}" for name in selected_file_names]

    reason = f"Selected {actual_count} of {len(file_names)} available files"
    if seed is not None:
        reason += f" (seed={seed})"

    return selected_indices, selected_file_names, file_paths, reason


class PSN_Random_Image_Selector:
    """
    Select random images from a directory for testing.

    Validates inputs, then shuffles a list of file names using an optional seed and
    returns the selected indices, file names, and constructed file paths. The names
    come from file_names if given, otherwise from listing folder_path for files with
    an image extension. It does not open or load any image.
    """

    DESCRIPTION = (
        "Selects random image files from a folder (listed by extension) or from a supplied name list; "
        "returns names and paths only, loads no image."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "", "multiline": False}),
                "num_images": ("INT", {"default": 3, "min": 1, "max": 10000, "step": 1}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647, "step": 1}),
                "file_names": ("LIST[STRING]", {"default": []}),
            },
        }

    RETURN_TYPES = ("LIST[INT]", "LIST[STRING]", "LIST[STRING]", "STRING")
    RETURN_NAMES = ("selected_indices", "selected_file_names", "file_paths", "reason")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Selection"

    def run(self, folder_path, num_images, seed=0, file_names=None):
        # Validate inputs
        valid, err = _validate_folder_path(folder_path)
        if not valid:
            return ([], [], [], f"Validation error: {err}")

        valid, err = _validate_num_images(num_images)
        if not valid:
            return ([], [], [], f"Validation error: {err}")

        # Treat seed=0 as "no seed" for backward compatibility, or use as-is
        # We'll use the seed value directly; if user wants no seed, they can
        # pass a large random value. For reproducibility, seed=0 is valid.
        valid, err = _validate_seed(seed)
        if not valid:
            return ([], [], [], f"Validation error: {err}")

        valid, err = _validate_file_names(file_names)
        if not valid:
            return ([], [], [], f"Validation error: {err}")

        # No names supplied: list the folder for image files.
        if not file_names:
            file_names = _list_image_files(folder_path)

        # Perform selection
        selected_indices, selected_file_names, file_paths, reason = select_random_images(
            folder_path, num_images, seed, file_names
        )

        return (selected_indices, selected_file_names, file_paths, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Random_Image_Selector": PSN_Random_Image_Selector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Random_Image_Selector": "PSN Random Image Selector",
}
