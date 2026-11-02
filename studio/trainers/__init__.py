"""External trainers the Train page can drive. Each adapter writes the trainer's own config from our template, starts the process and follows its log. Nothing here installs anything."""
from __future__ import annotations

from studio.trainers.base import ExternalTrainer
from studio.trainers.aitoolkit import AiToolkit
from studio.trainers.simpletuner import SimpleTuner

_ALL = {"ai-toolkit": AiToolkit(), "simpletuner": SimpleTuner()}


def get(name: str) -> ExternalTrainer:
    return _ALL[name]


def view_all(listed: dict) -> list[dict]:
    rows = [{"id": "comfy", **listed["comfy"], "here": True, "missing": []}]
    for name, t in _ALL.items():
        missing = t.missing_install()
        rows.append({"id": name, **(listed.get(name) or {}), "here": not missing, "missing": missing})
    return rows
