"""Shot Board's export: one contact video of a clip and everything made from it, each cell captioned. The renders themselves go through /api/generate.
Files come only from the studio's output and input folders. Clips shorter than the longest hold their last frame."""
import math, os, shutil, subprocess, tempfile, time, urllib.parse
from pathlib import Path
from fastapi import APIRouter, HTTPException
from psn import paths

router = APIRouter()
CELL_W, CELL_H, MAX_SECONDS, MAX_ITEMS = 640, 360, 6.0, 16
FONTS = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf")


def _root(kind):
    if kind == "input": return Path(paths.comfy_input(True)).resolve()
    if kind == "output": return Path(paths.output_dir(True)).resolve()
    raise HTTPException(400, "a clip must come from the studio's input or output folder")


def resolve_item(it):
    if not isinstance(it, dict) or not isinstance(it.get("filename"), str): raise HTTPException(400, "each clip needs a file name")
    root = _root(it.get("type") or "output"); p = (root / str(it.get("subfolder") or "") / it["filename"]).resolve()
    if root not in p.parents or not p.is_file(): raise HTTPException(404, f"no such clip: {it['filename']}")
    return p


def duration(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True, timeout=20)
    try: return float(r.stdout.strip())
    except ValueError: raise HTTPException(400, f"{p.name} isn't a readable video") from None


def grid_for(n):
    cols = min(4, math.ceil(math.sqrt(n))); return cols, math.ceil(n / cols)


def build_filter(n, length, captions):
    """captions: a text file per cell, or None per cell when no font was found."""
    cols, _ = grid_for(n); font = next((f for f in FONTS if os.path.exists(f)), None); parts = []
    for i in range(n):
        f = f"[{i}:v]scale={CELL_W}:{CELL_H}:force_original_aspect_ratio=decrease,pad={CELL_W}:{CELL_H}:(ow-iw)/2:(oh-ih)/2:black,fps=24,format=yuv420p,tpad=stop_mode=clone:stop_duration={length},trim=duration={length},setpts=PTS-STARTPTS"
        if font and captions[i]:
            f += f",drawbox=x=0:y={CELL_H - 44}:w={CELL_W}:h=44:color=black@0.55:t=fill,drawtext=fontfile='{font}':textfile='{captions[i]}':expansion=none:fontcolor=white:fontsize=22:x=14:y={CELL_H - 33}"
        parts.append(f + f"[c{i}]")
    if n == 1: return ";".join(parts), "[c0]"
    layout = "|".join(f"{(i % cols) * CELL_W}_{(i // cols) * CELL_H}" for i in range(n))
    parts.append("".join(f"[c{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}:fill=black[out]")
    return ";".join(parts), "[out]"


@router.post("/api/shotboard/export")
def export(b: dict):
    items = b.get("items")
    if not isinstance(items, list) or not 2 <= len(items) <= MAX_ITEMS: raise HTTPException(400, f"pick 2 to {MAX_ITEMS} clips")
    if not shutil.which("ffmpeg"): raise HTTPException(503, "ffmpeg isn't installed")
    files = [resolve_item(x) for x in items]; length = round(min(MAX_SECONDS, max(duration(p) for p in files)), 3)
    out_dir = Path(paths.output_dir(True)) / "shotboard"; out_dir.mkdir(parents=True, exist_ok=True); name = f"shotboard_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
    with tempfile.TemporaryDirectory() as td:
        caps = []
        for i, x in enumerate(items):
            p = os.path.join(td, f"c{i}.txt"); open(p, "w", encoding="utf-8").write(str(x.get("label") or "")[:48]); caps.append(p)
        fc, last = build_filter(len(files), length, caps); cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error"]
        for p in files: cmd += ["-i", str(p)]
        cmd += ["-filter_complex", fc, "-map", last, "-an", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_dir / name)]
        try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired: raise HTTPException(504, "the export took over 10 minutes") from None
    if r.returncode: raise HTTPException(500, "ffmpeg failed: " + r.stderr.strip()[-300:])
    return {"filename": name, "subfolder": "shotboard", "seconds": length, "url": "/api/view?" + urllib.parse.urlencode({"filename": name, "subfolder": "shotboard", "type": "output"})}
