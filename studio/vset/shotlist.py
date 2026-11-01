"""Shot lists: a script becomes an ordered list of shots in ONE set under ONE look: one shot per line, the camera picked from words in the line (or rotated), consecutive seeds."""
from __future__ import annotations

import copy
import json
import re
import time
from pathlib import Path

from studio import vset
from studio.vset import shot as SH
from studio.worldkit import library as L

SCHEMA = "vset-list/1"
MAX_SHOTS = 12
SEED_STEP = 101
PRESET_WORDS = (("pov", ("pov", "point of view", "first person")),
                ("orbit", ("orbit", "circle around", "spin around", "turnaround", "reveal")),
                ("push_in", ("push in", "push-in", "dolly in", "close in", "zoom in")),
                ("handheld", ("handheld", "hand-held", "shaky")),
                ("static", ("static", "locked off", "tripod", "wide shot")),
                ("walk_along", ("walk along", "walk-along", "tracking", "follow", "walking")))
ROTATION = ("push_in", "walk_along", "orbit")
_LEAD = re.compile(r"^\s*(?:shot\s*\d+\s*[:.)-]?|\d+\s*[:.)-]|[-*•])\s*", re.I)


def split_script(text: str) -> list[str]:
    out = []
    for line in str(text or "").splitlines():
        s = _LEAD.sub("", line).strip()
        if s:
            out.append(s[:SH.MAX_PROMPT])
    return out


def camera_for(line: str, i: int) -> str:
    t = line.lower()
    for preset, words in PRESET_WORDS:
        if any(w in t for w in words):
            return preset
    return ROTATION[i % len(ROTATION)]


def from_script(text: str, *, base: dict, name: str = "Shot list") -> list[dict]:
    lines = split_script(text)
    if not lines:
        raise ValueError("the script has no lines to turn into shots")
    if len(lines) > MAX_SHOTS:
        raise ValueError(f"at most {MAX_SHOTS} shots per list")
    seed0 = int(base.get("seed", 4242))
    shared = {k: base[k] for k in ("set", "cast", "marks", "look", "mode", "mode_settings", "format", "session_id") if k in base}
    return [SH.new_shot(**copy.deepcopy(shared), name=f"{name} #{i + 1}", prompt=line, camera={"preset": camera_for(line, i), "params": {}}, seed=(seed0 + i * SEED_STEP) % 2 ** 32)
            for i, line in enumerate(lines)]


def new_list(name: str, shot_ids: list, *, base: dict, script: str = "") -> dict:
    now = time.time()
    return {"schema": SCHEMA, "id": L.new_id(), "name": str(name or "Shot list")[:80], "shots": list(shot_ids), "base": copy.deepcopy(base), "script": str(script)[:20000], "state": {}, "created": now, "updated": now}


def lists_dir(root=None) -> Path:
    return Path(root or vset.root()) / "lists"


def save_list(lst: dict, root=None) -> dict:
    if not L.valid_id(lst.get("id")):
        raise SH.ShotError("bad list id")
    lst = {**lst, "updated": time.time()}
    L.write_json_atomic(lists_dir(root) / f"{lst['id']}.json", lst)
    return lst


def load_list(lid: str, root=None) -> dict:
    if not L.valid_id(lid):
        raise SH.ShotError(f"bad list id {lid!r}")
    try:
        return json.loads((lists_dir(root) / f"{lid}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SH.ShotError(f"no shot list {lid}") from None


def list_lists(root=None) -> list[dict]:
    out = []
    for p in lists_dir(root).glob("*.json") if lists_dir(root).is_dir() else []:
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return sorted(out, key=lambda x: x.get("created", 0), reverse=True)
