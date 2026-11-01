"""What every mode shares: the scene step (the Blender passes), the prompt words (who, where, the action, the look), a pass put in ComfyUI's input folder, and a graph request whose final words have been through the safe-for-work check.
The final prompt is checked again here because it also carries words from the assets."""
from __future__ import annotations

from studio.vset import passes
from studio.vset import shot as SH
from studio.worldkit import jobs, safety
from studio.worldkit import steps as S

VIDEO_TAIL = "Photoreal, real materials on every surface, steady exposure."


def scene_step(shot: dict) -> S.Step:
    return S.Step("scene", "Blender passes", local=lambda ctx: passes.scene_step_outputs(shot, ctx))


def who(shot: dict, *, library) -> str:
    parts = []
    for c in shot.get("cast") or []:
        s = library.require(c["asset"]).get("source") or {}
        desc = str(s.get("description") or "").strip()[:200]
        name = s.get("name") or "a person"
        parts.append(f"{name}, {desc}" if desc else str(name))
    return " and ".join(parts)


def where(shot: dict, *, library) -> str:
    place = library.require(shot["set"]["place"])
    return str((place.get("recipe") or {}).get("brief") or place["name"])


def video_prompt(shot: dict, *, library) -> str:
    look = SH.look_of(shot, library)
    people = who(shot, library=library)
    action = shot["prompt"].strip().rstrip(".")
    return f"{people + ': ' if people else ''}{action}. In {where(shot, library=library)}, {look['label'].lower()}. {VIDEO_TAIL}"


def uploaded(ctx: dict, step: str, key: str = "main") -> str:
    """A step's output file, in ComfyUI's input folder: its name there."""
    return ctx["to_input"](S.out_path(ctx, step, key), f"vset_{key}_")


def request(shot: dict, ctx: dict, template: str, label: str, values: dict) -> dict:
    bad = safety.text_problem(values.get("prompt", ""))
    if bad:
        raise S.StepError(bad)
    return {**jobs.graph(template, {"seed": ctx["seed"], "prefix": f"vset/{shot['id']}", **values}, label), "portable": True}
