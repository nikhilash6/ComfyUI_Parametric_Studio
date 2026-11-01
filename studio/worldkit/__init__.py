"""World Kit: a shared library of real-scale 3D assets (place, prop, character, look) and what makes them. Routes: studio/worldkit/api.py.
The library root is a setting: STUDIO_WORLDKIT_ROOT (environment or the machine's settings file). Everything else lives under it."""
import os
from pathlib import Path

from psn import paths

SETTING = "STUDIO_WORLDKIT_ROOT"


def root() -> Path:
    """Where the library lives. A default under the home folder, so that a missing ComfyUI never moves the library."""
    return Path(os.path.expanduser(paths.setting(SETTING, default=paths.home(".local", "share", "parametric-studio", "worldkit"))))


def work_root() -> Path:
    """Scratch for a build: Blender logs, frames, unfinished files. STUDIO_WORLDKIT_WORK, or <library>/_work."""
    w = paths.setting("STUDIO_WORLDKIT_WORK")
    return Path(os.path.expanduser(w)) if w else root() / "_work"
