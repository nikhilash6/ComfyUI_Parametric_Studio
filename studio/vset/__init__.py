"""Virtual Set: 3D shots in World Kit places that steer the video models, with an exact camera move and exact depth, pose and shaded passes. Routes: studio/vset/api.py.
Shots live under a setting: STUDIO_VSET_ROOT (environment or the machine's settings file)."""
import os
from pathlib import Path

from psn import paths

SETTING = "STUDIO_VSET_ROOT"


def root() -> Path:
    """Shots and shot lists. A default under the home folder, beside the World Kit library, so that a missing ComfyUI never moves them."""
    return Path(os.path.expanduser(paths.setting(SETTING, default=paths.home(".local", "share", "parametric-studio", "vset"))))
