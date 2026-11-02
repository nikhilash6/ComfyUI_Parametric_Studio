"""The Virtual Set shot: shot.json = the set (a place id, props with transforms), the cast (none by default, up to 2 characters, each with a clip and a mark path), the marks the camera
follows when there is no cast, the camera (a preset or a custom path), the format, the look, the mode with its settings, the seed and the action. The shot is recreated exactly from it. state.json beside it holds the
render steps (worldkit/steps.py), the rerolls and the QC result. The per-mode limits come from the graphs and models in MODE_SPECS; anything above a mode's limit is refused with the reason."""
from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

from studio import goals, vset
from studio.vset import camera
from studio.worldkit import library as L
from studio.worldkit import looks, rigmap, safety

SCHEMA = "vset-shot/1"
MODES = ("A", "B", "C", "D")
ASPECTS = ("9:16", "16:9", "1:1")
CONTROLS = ("depth", "pose")
ENGINES = ("h3", "wan", "ltx")
KEYFRAMES = ("qwen", "raw")
MODE_SPECS = {
    "A": {"label": "A: guide passes (the exact depth or pose pass drives the video)", "fps": 24, "seconds": [5], "aspects": list(ASPECTS)},
    "B": {"label": "B: restyle (the shaded render, H3 follows its exact depth)", "fps": 24, "seconds": [5], "aspects": list(ASPECTS)},
    "C": {"label": "C: keyframes (first and last stills, H3 fills between)", "fps": 24, "seconds": [5, 8, 10], "aspects": list(ASPECTS)},
    "D": {"label": "D: motion copy (H3 copies the shaded render's camera and motion)", "fps": 24, "seconds": [5, 8, 10], "aspects": list(ASPECTS)},
}
#: Mode A on the Wan 2.2 Fun Control graph: the graph's own length and frame rate.
WAN_SPEC = {"fps": 16, "frames": 81, "seconds": [5], "aspects": ["9:16", "16:9"], "sizes": {"9:16": (480, 832), "16:9": (832, 480)}}
#: Mode A on LTX-2.5 Layout to Render (Lightricks' card and graph): 121 frames (8k+1) at 24 fps. Stage 1 runs at these sizes and stage 2 doubles them: 1920x1088 out, each side a multiple of 64 there.
LTX_SPEC = {"fps": 24, "frames": 121, "seconds": [5], "aspects": ["9:16", "16:9"], "sizes": {"9:16": (544, 960), "16:9": (960, 544)}}
SPEC_SECONDS = (5, 15)
MAX_PROMPT = 1500
MAX_CAST = 2
MAX_PROPS = 24
MAX_MARKS = 8
MARK_MARGIN_M = 1.0
_SESSION = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ShotError(ValueError):
    pass


def new_shot(**fields) -> dict:
    now = time.time()
    s = {"schema": SCHEMA, "id": L.new_id(), "name": "", "session_id": "vset", "set": {"place": "", "props": []},
         "cast": [], "marks": [[0, 0]], "camera": {"preset": "push_in", "params": {}}, "format": {"aspect": "16:9", "seconds": 5},
         "look": {"preset": looks.DEFAULT}, "mode": "C", "mode_settings": {}, "seed": 4242, "prompt": "",
         "created": now, "updated": now}
    s.update(fields)
    return s


def is_wan(shot: dict) -> bool:
    return shot["mode"] == "A" and (shot.get("mode_settings") or {}).get("engine", "h3") == "wan"


def is_ltx(shot: dict) -> bool:
    return shot["mode"] == "A" and (shot.get("mode_settings") or {}).get("engine", "h3") == "ltx"


def fps(shot: dict) -> int:
    return WAN_SPEC["fps"] if is_wan(shot) else LTX_SPEC["fps"] if is_ltx(shot) else MODE_SPECS[shot["mode"]]["fps"]


def frames(shot: dict) -> int:
    """Wan's graph is 81 frames. H3 takes 17k+5 frames at 24 fps, snapped up: 5 s -> 124, 8 s -> 192, 10 s -> 243."""
    return WAN_SPEC["frames"] if is_wan(shot) else LTX_SPEC["frames"] if is_ltx(shot) else goals.h3_ref_frames(float(shot["format"]["seconds"]))


def size(shot: dict) -> tuple[int, int]:
    aspect = shot["format"]["aspect"]
    return WAN_SPEC["sizes"][aspect] if is_wan(shot) else LTX_SPEC["sizes"][aspect] if is_ltx(shot) else tuple(goals.H3_VIDEO_SIZES[aspect])


def subject_marks(shot: dict) -> list:
    """The path the camera follows: the first cast member's, or with no cast the shot's own marks."""
    cast = shot.get("cast") or []
    return cast[0]["marks"] if cast else (shot.get("marks") or [[0, 0]])


def look_of(shot: dict, library) -> dict:
    lk = shot.get("look") or {}
    if lk.get("asset"):
        lk = library.require(lk["asset"]).get("look") or {}
    return looks.resolve(lk.get("preset", looks.DEFAULT), lk.get("time") or None, lk.get("weather") or None)


def _asset(library, aid, type_: str, what: str, bad: list) -> dict | None:
    meta = library.get(aid) if isinstance(aid, str) else None
    if meta is None:
        bad.append(f"the {what} {aid} is archived or missing")
        return None
    if meta["type"] != type_:
        bad.append(f"{meta['name']} ({aid}) is a {meta['type']}, not a {type_}")
        return None
    if meta["status"] != "approved":
        bad.append(f"the {what} {meta['name']} ({aid}) is not approved yet (approve it in World Kit)")
    if type_ != "look" and not library.path(aid, "asset.glb").is_file():
        bad.append(f"the {what} {meta['name']} ({aid}) has no asset.glb")
    return meta


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _vec(v, n) -> bool:
    return isinstance(v, list) and len(v) == n and all(_num(x) for x in v)


def _marks_problem(marks, lo_xy, hi_xy) -> str:
    if not isinstance(marks, list) or not 1 <= len(marks) <= MAX_MARKS or not all(_vec(m, 2) for m in marks):
        return f"marks is a path of 1-{MAX_MARKS} [x, y] points"
    if lo_xy is not None and any(not (lo_xy[0] <= x <= hi_xy[0] and lo_xy[1] <= y <= hi_xy[1]) for x, y in marks):
        return "a mark is outside the place"
    return ""


def _format_problems(shot: dict, mode: str, bad: list) -> None:
    spec = {**MODE_SPECS[mode], **WAN_SPEC} if is_wan(shot) else {**MODE_SPECS[mode], **LTX_SPEC} if is_ltx(shot) else MODE_SPECS[mode]
    fmt = shot.get("format") if isinstance(shot.get("format"), dict) else {}
    aspect, secs = fmt.get("aspect"), fmt.get("seconds")
    if aspect not in ASPECTS:
        bad.append(f"aspect must be one of {', '.join(ASPECTS)}")
    elif aspect not in spec["aspects"]:
        bad.append(f"mode {mode} on this engine renders {', '.join(spec['aspects'])} only")
    lo, hi = SPEC_SECONDS
    if not isinstance(secs, int) or isinstance(secs, bool) or not lo <= secs <= hi:
        bad.append(f"seconds is a whole number, {lo}-{hi} s")
    elif secs not in spec["seconds"]:
        bad.append(f"mode {mode} renders {', '.join(map(str, spec['seconds']))} s" + ("; modes C and D render 5, 8 or 10 s" if mode in ("A", "B") else ""))


def _settings_problems(mode: str, ms: dict, bad: list) -> None:
    if mode == "A":
        if ms.get("control", "depth") not in CONTROLS:
            bad.append(f"mode A control must be one of {', '.join(CONTROLS)}")
        if ms.get("engine", "h3") not in ENGINES:
            bad.append(f"mode A engine must be one of {', '.join(ENGINES)}")
    if (mode == "C" or (mode == "A" and ms.get("engine") == "ltx")) and ms.get("keyframes", "qwen") not in KEYFRAMES:
        bad.append(f"mode {mode} keyframes must be one of {', '.join(KEYFRAMES)}")


def _cast_problems(cast: list, library, lo_xy, hi_xy, bad: list) -> None:
    if cast:
        off = safety.character_problem()
        if off:
            bad.append(off)
    for c in cast:
        if not isinstance(c, dict):
            bad.append("each cast member is an object")
            continue
        meta = _asset(library, c.get("asset"), "character", "character", bad)
        if meta is not None:
            slots = (meta.get("rig") or {}).get("slots") or {}
            if (meta.get("rig") or {}).get("bones", 0) <= 0 or any(s not in slots for s in rigmap.SLOTS):
                bad.append(f"{meta['name']} has no rig (no complete humanoid map): it cannot act; use it as a static prop instead")
            names = [x.get("name") for x in meta.get("clips") or []]
            if c.get("clip") not in names:
                bad.append(f"{meta['name']} has no clip {c.get('clip')!r} (it has {', '.join(names) or 'none'})")
        why = _marks_problem(c.get("marks"), lo_xy, hi_xy)
        if why:
            bad.append(why)


def problems(shot, *, library) -> list[str]:
    if not isinstance(shot, dict):
        return ["the shot must be an object"]
    bad: list[str] = []
    if shot.get("schema") != SCHEMA:
        bad.append(f"schema must be {SCHEMA!r}")
    if not L.valid_id(shot.get("id")):
        bad.append("id must be 12 lowercase letters")
    if not _SESSION.match(str(shot.get("session_id") or "")):
        bad.append("invalid session id")
    mode = shot.get("mode")
    if mode not in MODES:
        return bad + [f"mode must be one of {', '.join(MODES)}"]
    ms = shot.get("mode_settings") if isinstance(shot.get("mode_settings"), dict) else {}
    _settings_problems(mode, ms, bad)
    _format_problems({**shot, "mode_settings": ms}, mode, bad)
    prompt = shot.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        bad.append("describe the action (what happens in this shot)")
    elif len(prompt) > MAX_PROMPT:
        bad.append(f"the action is at most {MAX_PROMPT} characters")
    text = safety.text_problem(shot.get("name"), prompt, shot.get("mode_settings"))
    if text:
        bad.append(text)
    seed = shot.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2 ** 32:
        bad.append("seed is a whole number from 0 to 4294967295")
    st = shot.get("set") if isinstance(shot.get("set"), dict) else {}
    place = _asset(library, st.get("place"), "place", "place", bad)
    props = st.get("props") or []
    if not isinstance(props, list) or len(props) > MAX_PROPS:
        bad.append(f"props is a list of up to {MAX_PROPS}")
        props = []
    for p in props:
        if not isinstance(p, dict) or not _vec(p.get("pos"), 3) or not _vec(p.get("rot_deg", [0, 0, 0]), 3) \
                or not _num(p.get("scale", 1.0)) or p.get("scale", 1.0) <= 0:
            bad.append("each prop has pos [x, y, z], rot_deg [x, y, z] and a positive scale")
            continue
        _asset(library, p.get("asset"), "prop", "prop", bad)
    lo_xy = hi_xy = None
    if place and (place.get("inspect") or {}).get("lo"):
        lo_xy = [place["inspect"]["lo"][i] - MARK_MARGIN_M for i in (0, 1)]
        hi_xy = [place["inspect"]["hi"][i] + MARK_MARGIN_M for i in (0, 1)]
    cast = shot.get("cast")
    if cast is None:
        cast = []
    if not isinstance(cast, list) or len(cast) > MAX_CAST:
        bad.append(f"a shot has up to {MAX_CAST} cast members")
        cast = []
    _cast_problems(cast, library, lo_xy, hi_xy, bad)
    if mode == "A" and ms.get("control") == "pose" and not cast:
        bad.append("a pose pass draws the cast, and this shot has none: use the depth pass")
    if not cast:
        why = _marks_problem(shot.get("marks", [[0, 0]]), lo_xy, hi_xy)
        if why:
            bad.append(why)
    bad += camera.problems(shot.get("camera"))
    lk = shot.get("look") if isinstance(shot.get("look"), dict) else {}
    if lk.get("asset"):
        _asset(library, lk["asset"], "look", "look", bad)
    else:
        bad += looks.problems(lk.get("preset"), lk.get("time") or None, lk.get("weather") or None)
    return bad


def shots_dir(root=None) -> Path:
    return Path(root or vset.root()) / "shots"


def shot_dir(sid: str, root=None) -> Path:
    if not L.valid_id(sid):
        raise ShotError(f"bad shot id {sid!r}")
    return shots_dir(root) / sid


def save(shot: dict, root=None) -> dict:
    shot = {**shot, "updated": time.time()}
    L.write_json_atomic(shot_dir(shot["id"], root) / "shot.json", shot)
    return shot


def load(sid: str, root=None) -> dict:
    p = shot_dir(sid, root) / "shot.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ShotError(f"no shot {sid}") from None


def list_shots(root=None) -> list[dict]:
    out = []
    for p in shots_dir(root).glob("*/shot.json") if shots_dir(root).is_dir() else []:
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return sorted(out, key=lambda s: s.get("created", 0), reverse=True)


def load_state(sid: str, root=None) -> dict:
    p = shot_dir(sid, root) / "state.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(sid: str, state: dict, root=None) -> None:
    L.write_json_atomic(shot_dir(sid, root) / "state.json", state)
