"""Every asset gets a turntable (preview.mp4) and a thumbnail (thumb.jpg). Then "ingest" copies the built glb and both previews into the asset's library folder and records the facts (scale, rig,
clips, colliders)."""
from __future__ import annotations

from pathlib import Path

from studio.worldkit import steps as S

TURN_FRAMES = 72
TURN_FPS = 24
TURN_SIZE = 512
THUMB_SIZE = 384
TURN_SAMPLES = 16
PREVIEW_LOOK = "day_clear"
BUILD_STEP = {"character": "assemble", "prop": "cleanup", "place": "build", "look": ""}


def steps(meta: dict) -> list[S.Step]:
    return [S.Step("preview", "Turntable + thumbnail (Blender)", local=render), S.Step("ingest", "Into the library", local=ingest)]


def _look(meta: dict) -> dict:
    from studio.worldkit import looks
    if meta["type"] == "look":
        return looks.resolve(**{k: v for k, v in meta["look"].items() if k in ("preset", "time", "weather")})
    if meta["type"] == "place":
        return looks.resolve(**{k: v for k, v in meta["recipe"]["look"].items() if k in ("preset", "time", "weather")})
    return looks.resolve(PREVIEW_LOOK)


def render(ctx: dict, *, blender=None, encode=None) -> dict:
    """TURN_FRAMES frames around the asset (a look: around a test scene) -> preview.mp4 + thumb.jpg."""
    from PIL import Image

    from studio.worldkit import blender as B, media
    bl = blender or ctx.get("blender") or B
    meta = ctx["asset"]
    last = BUILD_STEP[meta["type"]]
    model = S.out_path(ctx, last) if last else ""
    interior = meta["type"] == "place" and meta["recipe"].get("kit") == "interior"
    work = ctx["work"] / "preview"
    frames = work / "frames"
    res = bl.render("wk_turntable.py", {"model": model, "look": _look(meta), "frames": TURN_FRAMES, "size": TURN_SIZE, "out_dir": str(frames), "interior": interior,
                                        "elevation": 0.35, "kit": (meta.get("recipe") or {}).get("kit", "") if meta["type"] == "place" else "", "samples": TURN_SAMPLES}, work=work, name="turntable", timeout=3600)
    mp4 = (encode or media.encode)(frames, TURN_FPS, work / "preview.mp4")
    pngs = sorted(frames.glob("*.png"))
    if not pngs:
        raise RuntimeError(f"Blender wrote no turntable frames into {frames}")
    thumb = work / "thumb.jpg"
    with Image.open(pngs[0]) as im:
        im.convert("RGB").resize((THUMB_SIZE, THUMB_SIZE)).save(thumb, format="JPEG", quality=88)
    out = {"turntable": {"path": str(mp4), "frames": len(pngs), "engine": res.get("engine", "")}, "thumb": {"path": str(thumb)}}
    if res.get("fallback_note"):
        out["turntable"]["note"] = res["fallback_note"]
    return out


def ingest(ctx: dict) -> dict:
    lib, meta = ctx["library"], ctx["asset"]
    aid, o, last = meta["id"], ctx["outputs"], BUILD_STEP[meta["type"]]
    files = {"preview.mp4": o["preview"]["turntable"]["path"], "thumb.jpg": o["preview"]["thumb"]["path"]}
    changes: dict = {}
    if last:
        main = o[last]["main"]
        files["asset.glb"] = main["path"]
        ins = main.get("inspect") or {}
        size = float(ins.get("height_m") or 0.0) if meta["type"] == "character" else max(ins.get("dims_m") or [0.0])
        changes.update(inspect=ins, colliders=int(ins.get("colliders") or 0), scale_m=round(size, 3) if size > 0 else None)
        if main.get("rig"):
            changes["rig"] = main["rig"]
        if main.get("clips") is not None:
            changes["clips"] = main["clips"]
    for name, src in files.items():
        lib.put_file(aid, name, Path(src))
    jobs_ = sorted({x["job_id"] for step in o.values() for x in step.values() if isinstance(x, dict) and x.get("job_id")})
    lib.update(aid, files={n: True for n in files}, source_jobs=jobs_, **changes)
    return {"main": {"files": sorted(files)}}
