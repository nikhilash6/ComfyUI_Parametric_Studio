"""Export approved World Kit assets as a game-engine pack (the bridge from a 3D asset to a game).

A pack is a folder (and a .zip of it) under <library root>/_exports/:
  assets/<type>/<name>-<id4>.glb   the approved glbs
  manifest.json                    worldkit-pack/1: per asset real size, rig, clips, colliders, licence note, placement
  scenes/main.tscn                 a Godot 4 scene that instances the glbs (placements, or a showroom row)
  IMPORT.txt                       what to do in Godot (drop the folder into a project, open scenes/main.tscn)

glTF is Y-up, Blender (and the placements the API takes) are Z-up metres: a Blender (x, y, z) is Godot (x, z, -y). A character faces -Y in Blender, which is +Z in glTF, so yaw 0 needs no
rotation. Godot imports a node named "<x>-colonly" as a collision shape only, which is how a prop's or place's collider arrives. main.tscn uses only the plain text-scene format (ExtResource / instance).
"""
from __future__ import annotations

import json
import math
import re
import shutil
import time
import zipfile
from pathlib import Path

SCHEMA = "worldkit-pack/1"
EXPORTS = "_exports"
MAX_PLACEMENTS = 200
SCALE_RANGE = (0.01, 100.0)
_ZIP = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}-\d{8}-\d{6}\.zip$")
IMPORT_TXT = """World Kit pack (worldkit-pack/1)

Godot 4: copy this folder into your project (so it sits at res://<folder>/), let Godot import the .glb files, then open
scenes/main.tscn. Nodes named "<x>-colonly" in a glb become collision shapes only; a character's glb carries its
AnimationPlayer with the clips listed in manifest.json. Other engines read the .glb files directly (glTF 2.0, metres,
Y-up); manifest.json has each asset's real size, rig and placement.
"""


def slug(name: str, fallback: str = "asset") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")[:40].strip("-")
    return s or fallback


def to_godot(pos) -> list[float]:
    """Blender Z-up metres -> glTF / Godot Y-up."""
    x, y, z = pos
    return [x, z, -y]


def transform(pos, yaw_deg: float = 0.0, scale: float = 1.0) -> str:
    """A Godot 4 Transform3D(...) literal: Y rotation by yaw, uniform scale, origin at the Blender position."""
    c, s = math.cos(math.radians(yaw_deg)) * scale, math.sin(math.radians(yaw_deg)) * scale
    o = to_godot(pos)
    vals = [c, 0, s, 0, scale, 0, -s, 0, c, *o]
    return "Transform3D(" + ", ".join(f"{round(v, 5) + 0.0:g}" for v in vals) + ")"


def _number(v, what: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"{what} must be a number")
    return float(v)


def placements_problems(raw, chosen: set[str]) -> tuple[list[dict], list[str]]:
    """The checked placement list and the problems: each {asset, pos: [x, y, z], yaw_deg, scale}."""
    if raw is None:
        return [], []
    if not isinstance(raw, list) or len(raw) > MAX_PLACEMENTS:
        return [], [f"placements is a list of up to {MAX_PLACEMENTS}"]
    out, bad = [], []
    for i, p in enumerate(raw):
        try:
            if not isinstance(p, dict) or p.get("asset") not in chosen:
                raise ValueError("asset must be one of the exported assets")
            pos = p.get("pos", [0, 0, 0])
            if not isinstance(pos, list) or len(pos) != 3:
                raise ValueError("pos is [x, y, z] in metres")
            scale = _number(p.get("scale", 1.0), "scale")
            if not SCALE_RANGE[0] <= scale <= SCALE_RANGE[1]:
                raise ValueError(f"scale must be {SCALE_RANGE[0]}-{SCALE_RANGE[1]}")
            out.append({"asset": p["asset"], "pos": [_number(v, "pos") for v in pos],
                        "yaw_deg": _number(p.get("yaw_deg", 0.0), "yaw_deg"), "scale": scale})
        except ValueError as exc:
            bad.append(f"placements[{i}]: {exc}")
    return out, bad


def showroom(rows: list[dict]) -> list[dict]:
    """No placements given: the first place sits at the origin; everything else stands in a row along +X, spaced by
    its real size, so the pack opens as something to look at."""
    out, x = [], 0.0
    for r in rows:
        if r["type"] == "place":
            out.append({"asset": r["id"], "pos": [0.0, 0.0, 0.0], "yaw_deg": 0.0, "scale": 1.0})
    placed_place = bool(out)
    for r in rows:
        if r["type"] in ("character", "prop") and r["file"]:
            size = float(r.get("scale_m") or 1.0)
            out.append({"asset": r["id"], "pos": [x, -4.0 if placed_place else 0.0, 0.0], "yaw_deg": 0.0, "scale": 1.0})
            x += max(1.5, size * 1.2)
    return out


def scene_text(rows: list[dict], placements: list[dict]) -> str:
    """Godot 4 text scene: one ExtResource per glb, one instanced node per placement."""
    by = {r["id"]: r for r in rows if r["file"]}
    ext = {aid: i + 1 for i, aid in enumerate(sorted({p["asset"] for p in placements if p["asset"] in by}))}
    lines = [f"[gd_scene load_steps={len(ext) + 1} format=3]", ""]
    for aid, i in ext.items():
        lines.append(f'[ext_resource type="PackedScene" path="res://{{pack}}/{by[aid]["file"]}" id="{i}_{aid[:4]}"]')
    lines += ["", '[node name="Main" type="Node3D"]']
    used: dict[str, int] = {}
    for p in placements:
        if p["asset"] not in ext:
            continue
        base = re.sub(r"[^A-Za-z0-9_]", "_", by[p["asset"]]["name"]).strip("_") or "Asset"
        used[base] = used.get(base, 0) + 1
        node = base if used[base] == 1 else f"{base}_{used[base]}"
        lines += ["", f'[node name="{node}" parent="." instance=ExtResource("{ext[p["asset"]]}_{p["asset"][:4]}")]',
                  f'transform = {transform(p["pos"], p["yaw_deg"], p["scale"])}']
    return "\n".join(lines) + "\n"


def _row(meta: dict, dest_rel: str) -> dict:
    return {"id": meta["id"], "type": meta["type"], "name": meta["name"], "tags": meta.get("tags", []),
            "file": dest_rel, "scale_m": meta.get("scale_m"), "colliders": meta.get("colliders", 0),
            "rig": meta.get("rig") or {}, "clips": [c.get("name") for c in meta.get("clips") or []],
            "look": meta.get("look") or {}, "licence_class": meta.get("licence_class"),
            "licence_note": meta.get("licence_note", ""), "source_jobs": meta.get("source_jobs", [])}


def export_root(lib) -> Path:
    return lib.root / EXPORTS


def build_pack(lib, payload, *, now: float | None = None) -> tuple[int, dict]:
    """POST /api/worldkit/export: {name?, assets?: [ids] (default: every approved asset), placements?: [...]}."""
    def err(code, msg):
        return code, {"error": msg}
    if not isinstance(payload, dict):
        return err(400, "send a JSON object")
    ids = payload.get("assets")
    if ids is None:
        metas = [m for m in lib.list(status="approved")]
    elif isinstance(ids, list) and ids and all(isinstance(i, str) for i in ids):
        metas = []
        for aid in dict.fromkeys(ids):
            m = lib.get(aid)
            if m is None:
                return err(404, f"no such asset {aid}")
            metas.append(m)
    else:
        return err(400, "assets is a list of asset ids (leave it out for every approved asset)")
    notready = [m["name"] for m in metas if m.get("status") != "approved"]
    if notready:
        return err(400, "approve these first (Approve for sets): " + ", ".join(notready))
    if not metas:
        return err(400, "nothing to export: approve some assets first")
    placements, bad = placements_problems(payload.get("placements"), {m["id"] for m in metas})
    if bad:
        return err(400, "; ".join(bad))
    name = slug(payload.get("name") or "worldkit-pack", "worldkit-pack")
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    pack_name = f"{name}-{stamp}"
    pack = export_root(lib) / pack_name
    rows: list[dict] = []
    try:
        for m in metas:
            rel = ""
            if m["type"] != "look":
                src = lib.path(m["id"], "asset.glb")
                if not src.is_file():
                    return err(400, f"{m['name']} has no asset.glb")
                rel = f"assets/{m['type']}/{slug(m['name'])}-{m['id'][:4]}.glb"
                (pack / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, pack / rel)
            rows.append(_row(m, rel))
        use = placements or showroom(rows)
        for r in rows:
            r["placements"] = [{k: p[k] for k in ("pos", "yaw_deg", "scale")} for p in use if p["asset"] == r["id"]]
        (pack / "scenes").mkdir(parents=True, exist_ok=True)
        (pack / "scenes" / "main.tscn").write_text(scene_text(rows, use).replace("{pack}", pack_name), encoding="utf-8")
        (pack / "IMPORT.txt").write_text(IMPORT_TXT, encoding="utf-8")
        manifest = {"schema": SCHEMA, "name": name, "created": now if now is not None else time.time(),
                    "units": "metres", "up_axis": "+Y (glTF); placements are Blender Z-up", "engine": "godot4",
                    "scene": "scenes/main.tscn", "assets": rows}
        (pack / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        zpath = export_root(lib) / f"{pack_name}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(pack.rglob("*")):
                if f.is_file():
                    z.write(f, f"{pack_name}/{f.relative_to(pack).as_posix()}")
    except OSError as exc:
        return err(500, f"export failed: {exc}")
    return 200, {"pack": pack_name, "dir": str(pack), "zip": f"{pack_name}.zip", "assets": len(rows),
                 "placements": len(use), "manifest": manifest}


def list_exports(lib) -> list[dict]:
    root = export_root(lib)
    out = []
    for z in sorted(root.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True) if root.is_dir() else []:
        if _ZIP.match(z.name):
            out.append({"zip": z.name, "bytes": z.stat().st_size, "created": z.stat().st_mtime})
    return out


def zip_path(lib, name: str) -> Path | None:
    """The export zip for a download, or None (the name is matched against a strict pattern, never joined raw)."""
    if not isinstance(name, str) or not _ZIP.match(name):
        return None
    p = export_root(lib) / name
    return p if p.is_file() else None


__all__ = ["SCHEMA", "build_pack", "list_exports", "zip_path", "scene_text", "transform", "showroom"]
