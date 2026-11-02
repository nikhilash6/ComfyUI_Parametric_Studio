"""Saved characters. A saved character is a folder in <library>/_characters/<id>/: character.json {"id", "name", "description", "status", "check", "source"} and body_front.png. The sheet is made here, from words, by an image model on
this machine; no route accepts an upload for this, ever, and there is no way to hand in a photo of someone. STUDIO_WORLDKIT_CHARACTERS=0 turns them off: then nothing can be created or built.
Status: "draft" (words saved), "building", "ready" (the sheet passed the picture check), "blocked" (it did not), "failed" (it could not be made). Only "ready" with a stored pass for that exact file can become a 3D character. See safety.py and picturecheck.py for what is and is not checked."""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from studio import worldkit
from studio.worldkit import picturecheck, safety

USABLE = ("ready",)
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SHEET_ROLE = "body_front"
MAX_NAME = 60
MAX_DESCRIPTION = 400
SHEET_PROMPT = ("Full-body front view of an invented adult character: {description}. Fully clothed, standing straight with both arms held out from the sides at about 45 degrees, hands open and well clear of the body, legs slightly apart, the whole body in frame from head to feet, face clearly visible, neutral expression, "
                "plain light grey studio background, even soft light.")


@dataclass
class Character:
    id: str
    name: str
    description: str
    status: str
    folder: Path
    check: dict = field(default_factory=dict)
    error: str = ""
    take: int = 0

    def sheet(self) -> Path:
        return self.folder / f"{SHEET_ROLE}.png"


def store() -> Path:
    return worldkit.root() / "_characters"


def get(cid) -> Character | None:
    if not isinstance(cid, str) or not _ID.match(cid):
        return None
    d = store() / cid
    try:
        j = json.loads((d / "character.json").read_text(encoding="utf-8"))
        return Character(id=cid, name=str(j["name"]), description=str(j.get("description", "")), status=str(j.get("status", "")), folder=d, check=j.get("check") if isinstance(j.get("check"), dict) else {}, error=str(j.get("error", "")), take=int(j.get("take") or 0))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def all_saved() -> list[Character]:
    try:
        names = sorted(p.name for p in store().iterdir() if p.is_dir())
    except OSError:
        return []
    return [c for c in (get(n) for n in names) if c is not None]


def sheet_problem(ch: Character | None) -> str:
    """"" when a saved character may become a 3D character."""
    if ch is None:
        return "no such saved character"
    bad = safety.character_text_problem(ch.name, ch.description)
    if bad:
        return bad
    if ch.status not in USABLE:
        return f"{ch.name}'s sheet is {ch.status or 'not built'}; only a built sheet can become a 3D character"
    if not ch.sheet().is_file():
        return f"{ch.name}'s sheet has no full-body front shot ({SHEET_ROLE}.png) on disk"
    if not picturecheck.passed(ch.check, ch.sheet()):
        return f"{ch.name}'s sheet has not passed the picture check"
    return ""


def _write(d: Path, j: dict) -> None:
    tmp = d / "character.json.tmp"
    tmp.write_text(json.dumps(j, indent=1), encoding="utf-8")
    os.replace(tmp, d / "character.json")


def _update(ch: Character, **changes) -> Character:
    j = json.loads((ch.folder / "character.json").read_text(encoding="utf-8"))
    j.update(changes, updated=time.time())
    _write(ch.folder, j)
    return get(ch.id)


def create(name, description) -> tuple[Character | None, str]:
    """Save a character's words, once they pass the text checks. (character, "") or (None, why)."""
    off = safety.character_problem()
    if off:
        return None, off
    name, description = str(name or "").strip(), str(description or "").strip()
    if not name or len(name) > MAX_NAME:
        return None, f"a character needs a name of up to {MAX_NAME} letters"
    if not description or len(description) > MAX_DESCRIPTION:
        return None, f"describe the character in up to {MAX_DESCRIPTION} letters"
    bad = safety.character_text_problem(name, description) or safety.likeness_problem(name, description)
    if bad:
        return None, bad
    from studio.worldkit import library as L
    cid = L.new_id()
    d = store() / cid
    d.mkdir(parents=True, exist_ok=False)
    _write(d, {"id": cid, "name": name, "description": description, "status": "draft", "source": "words", "created": time.time()})
    return get(cid), ""


def sheet_request(ch: Character) -> dict:
    """The sheet's job: Krea 2 Turbo on the main ComfyUI. Nothing about it comes from a file a person supplied."""
    from studio.worldkit import jobs
    from studio.worldkit.makers import prop
    return jobs.graph(prop.KREA_GRAPH, {"prompt": SHEET_PROMPT.format(description=ch.description), "width": 832, "height": 1216, "seed": int(ch.id.encode().hex()[:8], 16) + ch.take, "prefix": f"worldkit/character_{ch.id}"}, f"Character sheet: {ch.name}")


def build_sheet(cid: str, *, submit=None, wait=None, check=None) -> Character | None:
    """words -> a picture -> the picture check -> ready or blocked. A sheet that does not pass is deleted, and only the reason is kept."""
    from studio.worldkit import jobs
    ch = get(cid)
    if ch is None or safety.character_problem() or safety.character_text_problem(ch.name, ch.description) or safety.likeness_problem(ch.name, ch.description):
        return ch
    submit, wait, check = submit or jobs.submit, wait or jobs.wait, check or picturecheck.check
    ch = _update(ch, status="building", error="", check={})
    try:
        res = wait(submit(sheet_request(ch)))
        if res.get("status") != "done":
            return _update(ch, status="failed", error=str(res.get("error") or res.get("status"))[:400])
        src = next(Path(a["path"]) for a in res.get("artifacts") or [] if a.get("media_type") == "image")
        tmp = ch.folder / "checking.png"
        from PIL import Image
        with Image.open(src) as im:
            im.convert("RGB").save(tmp, format="PNG")
        rec = check(tmp)
        if rec.get("ok"):
            shutil.move(str(tmp), ch.sheet())
            return _update(ch, status="ready", check=rec)
        tmp.unlink(missing_ok=True)
        ch.sheet().unlink(missing_ok=True)
        return _update(ch, status="blocked", check=rec, error="; ".join(rec.get("why") or [])[:400])
    except Exception as exc:
        (ch.folder / "checking.png").unlink(missing_ok=True)
        return _update(ch, status="failed", error=f"{type(exc).__name__}: {exc}"[:400])


def next_take(cid: str) -> Character | None:
    """Another try at the sheet from the same words: the next seed. The old sheet stays until the new one has passed or failed."""
    ch = get(cid)
    return None if ch is None else _update(ch, take=ch.take + 1, status="draft", error="")


def delete(cid: str) -> bool:
    ch = get(cid)
    if ch is None:
        return False
    shutil.rmtree(ch.folder)
    return True
