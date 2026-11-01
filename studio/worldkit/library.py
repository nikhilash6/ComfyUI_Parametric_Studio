"""The World Kit asset library: one folder per asset, <root>/<type>/<id>/ with asset.glb, preview.mp4 (turntable), thumb.jpg and
meta.json; the meta schema, approve validation and search by type, tag and name. Delete = move to <root>/_archive/<type>/
(never a hard delete). Licence classes are recorded per asset, informational only."""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import string
import threading
import time
from pathlib import Path

from studio import glb, worldkit
from studio.worldkit import rigmap

SCHEMA = "worldkit-asset/1"
TYPES = ("character", "prop", "place", "look")
STATUSES = ("draft", "approved")
BUILD_STATES = ("pending", "building", "failed", "done")
LICENCE_CLASSES = ("C-OK", "C-COND", "NC", "OWNER", "UNK")
SOURCE_KINDS = ("character", "image", "text", "brief", "preset", "mesh")
FILES = ("asset.glb", "preview.mp4", "thumb.jpg", "meta.json")
SUBDIRS = ("textures",)
ARCHIVE = "_archive"
MAX_NAME = 80
MAX_TAGS = 12
_ID = re.compile(r"^[a-z]{12}$")
_TAG = re.compile(r"^[a-z0-9][a-z0-9 _-]{0,31}$")
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_MU = threading.Lock()


class AssetError(ValueError):
    """A request the library refuses: bad meta, an unknown asset, an approve that fails validation."""


def new_id() -> str:
    """12 lowercase letters. No digits: an id travels in job records and file names that text checks read, and a digit run
    there can read as an age."""
    return "".join(secrets.choice(string.ascii_lowercase) for _ in range(12))


def valid_id(aid) -> bool:
    return isinstance(aid, str) and bool(_ID.match(aid))


def new_meta(type_: str, name: str, *, source: dict, tags=(), session_id: str = "worldkit",
             recipe: dict | None = None, look: dict | None = None, licence_class: str = "UNK",
             licence_note: str = "", now: float | None = None) -> dict:
    now = time.time() if now is None else now
    return {"schema": SCHEMA, "id": new_id(), "type": type_, "name": str(name or "").strip()[:MAX_NAME],
            "tags": [str(t).strip().lower() for t in tags if str(t).strip()][:MAX_TAGS],
            "source": dict(source or {}), "session_id": session_id, "recipe": dict(recipe or {}),
            "look": dict(look or {}), "source_jobs": [], "source_images": [], "scale_m": None,
            "rig": {"bones": 0, "standard": "", "slots": {}}, "colliders": 0, "clips": [],
            "licence_class": licence_class, "licence_note": licence_note, "status": "draft",
            "build": {"state": "pending", "steps": [], "error": ""}, "inspect": {}, "files": {},
            "created": now, "updated": now}


def meta_problems(meta) -> list[str]:
    if not isinstance(meta, dict):
        return ["meta must be an object"]
    bad: list[str] = []
    if meta.get("schema") != SCHEMA:
        bad.append(f"schema must be {SCHEMA!r}")
    if not valid_id(meta.get("id")):
        bad.append("id must be 12 lowercase letters")
    if meta.get("type") not in TYPES:
        bad.append(f"type must be one of {', '.join(TYPES)}")
    name = meta.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > MAX_NAME:
        bad.append(f"name is 1-{MAX_NAME} characters")
    tags = meta.get("tags")
    if not isinstance(tags, list) or len(tags) > MAX_TAGS or not all(isinstance(t, str) and _TAG.match(t) for t in tags):
        bad.append(f"tags are up to {MAX_TAGS} short lowercase words")
    src = meta.get("source")
    if not isinstance(src, dict) or src.get("kind") not in SOURCE_KINDS:
        bad.append(f"source.kind must be one of {', '.join(SOURCE_KINDS)}")
    if meta.get("status") not in STATUSES:
        bad.append(f"status must be one of {', '.join(STATUSES)}")
    if meta.get("licence_class") not in LICENCE_CLASSES:
        bad.append(f"licence_class must be one of {', '.join(LICENCE_CLASSES)}")
    b = meta.get("build")
    if not isinstance(b, dict) or b.get("state") not in BUILD_STATES or not isinstance(b.get("steps"), list):
        bad.append(f"build needs a state ({', '.join(BUILD_STATES)}) and a steps list")
    s = meta.get("scale_m")
    if s is not None and (isinstance(s, bool) or not isinstance(s, (int, float)) or s <= 0):
        bad.append("scale_m is a positive number of metres or null")
    for key in ("source_jobs", "source_images", "clips"):
        if not isinstance(meta.get(key), list):
            bad.append(f"{key} must be a list")
    for key in ("rig", "recipe", "look", "inspect", "files"):
        if not isinstance(meta.get(key), dict):
            bad.append(f"{key} must be an object")
    if not isinstance(meta.get("colliders"), int) or isinstance(meta.get("colliders"), bool):
        bad.append("colliders must be a whole number")
    return bad


def write_json_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically with a temporary file, ensuring no partial writes."""
    d = path.parent
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f"{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    try:
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _matches(meta: dict, q: str) -> bool:
    hay = " ".join([str(meta.get("name", "")), str(meta.get("type", "")), *map(str, meta.get("tags", []))]).lower()
    return all(w in hay for w in str(q).lower().split())


class Library:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else worldkit.root()
        with _LOCKS_MU:
            self._mu = _LOCKS.setdefault(os.path.abspath(self.root), threading.Lock())

    def dir(self, type_: str, aid: str) -> Path:
        if type_ not in TYPES or not valid_id(aid):
            raise AssetError("bad asset type or id")
        return self.root / type_ / aid

    def _write(self, meta: dict) -> None:
        d = self.dir(meta["type"], meta["id"])
        write_json_atomic(d / "meta.json", meta)

    def create(self, meta: dict) -> dict:
        bad = meta_problems(meta)
        if bad:
            raise AssetError("; ".join(bad))
        with self._mu:
            if self.get(meta["id"]) is not None:
                raise AssetError(f"an asset with id {meta['id']} exists")
            self._write(meta)
        return dict(meta)

    def get(self, aid: str) -> dict | None:
        if not valid_id(aid):
            return None
        for t in TYPES:
            p = self.root / t / aid / "meta.json"
            if p.is_file():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    return None
        return None

    def require(self, aid: str) -> dict:
        meta = self.get(aid)
        if meta is None:
            raise AssetError(f"no asset {aid}")
        return meta

    def update(self, aid: str, **changes) -> dict:
        if {"id", "type", "schema"} & set(changes):
            raise AssetError("id, type and schema never change")
        with self._mu:
            meta = self.require(aid)
            meta.update(changes)
            meta["updated"] = time.time()
            bad = meta_problems(meta)
            if bad:
                raise AssetError("; ".join(bad))
            self._write(meta)
            return dict(meta)

    def list(self, *, type_: str | None = None, tag: str | None = None, q: str | None = None,
             status: str | None = None) -> list[dict]:
        out = []
        for t in (TYPES if type_ is None else [type_]):
            base = self.root / t
            if t not in TYPES or not base.is_dir():
                continue
            for p in base.glob("*/meta.json"):
                try:
                    m = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue                    # one unreadable asset must not hide the others
                if status and m.get("status") != status:
                    continue
                if tag and str(tag).lower() not in m.get("tags", []):
                    continue
                if q and not _matches(m, q):
                    continue
                out.append(m)
        return sorted(out, key=lambda m: m.get("created", 0), reverse=True)

    def path(self, aid: str, name: str) -> Path:
        if name not in FILES:
            raise AssetError(f"no asset file {name!r}")
        meta = self.require(aid)
        return self.dir(meta["type"], aid) / name

    def put_file(self, aid: str, name: str, src: Path) -> Path:
        """A copy, published atomically: later writes in a work folder must not change a library file."""
        dest = self.path(aid, name)
        part = dest.with_name(dest.name + ".part")
        part.unlink(missing_ok=True)
        shutil.copy2(src, part)
        os.replace(part, dest)
        return dest

    def keep_mesh(self, aid: str, src) -> Path:
        """Copy a work-folder mesh into the asset's own folder (so a static prop made from it survives a clean-up); its path under the library root."""
        meta = self.require(aid)
        dest = self.dir(meta["type"], aid) / f"kept_mesh{Path(src).suffix.lower()}"
        shutil.copy2(src, dest)
        return dest.relative_to(self.root)

    def subdir(self, aid: str, sub: str) -> Path:
        if sub not in SUBDIRS:
            raise AssetError(f"no asset folder {sub!r}")
        meta = self.require(aid)
        d = self.dir(meta["type"], aid) / sub
        d.mkdir(parents=True, exist_ok=True)
        return d

    def archive(self, aid: str) -> Path:
        """Delete = move the whole folder to <root>/_archive/<type>/<id>-<stamp> (never a hard delete)."""
        with self._mu:
            meta = self.require(aid)
            src = self.dir(meta["type"], aid)
            dest = self.root / ARCHIVE / meta["type"] / f"{aid}-{time.strftime('%Y%m%d-%H%M%S')}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            return dest

    def approve(self, aid: str) -> dict:
        """Approve for sets: only a finished build that passes validate()."""
        meta = self.require(aid)
        if (meta.get("build") or {}).get("state") != "done":
            raise AssetError("the asset is still building or its build failed; it cannot be approved yet")
        glb_path = None if meta["type"] == "look" else self.dir(meta["type"], aid) / "asset.glb"
        bad = validate(meta, glb_path)
        if bad:
            raise AssetError("; ".join(bad))
        return self.update(aid, status="approved")


HEIGHT_M = (1.5, 2.0)
PROP_SIZE_M = (0.02, 30.0)
PLACE_MIN_M = 4.0
MIN_BONES = rigmap.MIN_BONES


def validate(meta: dict, glb_path) -> list[str]:
    """Why the asset is not usable yet ([] = valid): the glb loads in headless Blender (meta["inspect"],
    written by the build's Blender step), sane scale (characters 1.5-2.0 m tall), a rig for characters, a collider for
    props and places. A look has no glb: its preset must be known."""
    t = meta.get("type")
    if t == "look":
        from studio.worldkit import looks
        return [] if (meta.get("look") or {}).get("preset") in looks.LOOKS else ["the look's preset is unknown"]
    if glb_path is None or not Path(glb_path).is_file():
        return ["no asset.glb yet"]
    try:
        f = glb.facts(glb_path)
    except glb.GlbError as exc:
        return [str(exc)]
    ins = meta.get("inspect") or {}
    bad: list[str] = []
    if not ins.get("loaded"):
        bad.append("headless Blender has not loaded this glb yet (no inspect report)")
    dims = list(ins.get("dims_m") or [0.0, 0.0, 0.0])
    height = float(ins.get("height_m") or 0.0)
    if t == "character":
        lo, hi = HEIGHT_M
        if not lo <= height <= hi:
            bad.append(f"a character is {lo}-{hi} m tall; this one is {height:.2f} m")
        rig = meta.get("rig") or {}
        if f["skins"] < 1 or int(rig.get("bones") or 0) < MIN_BONES:
            bad.append(f"a character needs a rig (a skinned armature of at least {MIN_BONES} bones)")
        missing = [s for s in rigmap.SLOTS if s not in (rig.get("slots") or {})]
        if missing:
            bad.append("the rig's humanoid map is missing " + ", ".join(missing))
    elif t == "prop":
        lo, hi = PROP_SIZE_M
        if not lo <= max(dims) <= hi:
            bad.append(f"a prop is {lo}-{hi} m across; this one is {max(dims):.2f} m")
        if f["colliders"] < 1:
            bad.append("a prop needs a collider")
    elif t == "place":
        if max(dims[:2]) < PLACE_MIN_M:
            bad.append(f"a place is at least {PLACE_MIN_M:.0f} m across; this one is {max(dims[:2]):.1f} m")
        if f["colliders"] < 1:
            bad.append("a place needs a collider")
    return bad
