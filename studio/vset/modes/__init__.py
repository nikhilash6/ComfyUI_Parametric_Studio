"""The render modes. Each only produces job requests for steps.run, so it is tested with fakes; each one's last step is named "video" (the reroll target)."""
from __future__ import annotations

import importlib

MODULES = {"A": "guide", "B": "restyle", "C": "keyframes", "D": "motioncopy"}


def steps(shot: dict, *, library) -> list:
    return importlib.import_module(f"studio.vset.modes.{MODULES[shot['mode']]}").steps(shot, library=library)
