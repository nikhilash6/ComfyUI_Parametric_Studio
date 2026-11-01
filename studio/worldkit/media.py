"""ffmpeg helpers for frame folders (World Kit turntables, Virtual Set passes)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def encode(frames_dir, fps: int, out, *, pattern: str = "%04d.png", crf: int = 16, run=None) -> Path:
    out = Path(out)
    part = out.with_name(out.stem + ".part" + out.suffix)
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(int(fps)), "-i", str(Path(frames_dir) / pattern),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-crf", str(int(crf)),
           "-movflags", "+faststart", str(part)]
    p = (run or subprocess.run)(cmd, capture_output=True, text=True, timeout=900)
    if p.returncode != 0 or not part.is_file():
        part.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg could not encode {frames_dir}: {(p.stderr or '')[-400:]}")
    os.replace(part, out)
    return out


def frame_count(video, *, run=None) -> int:
    p = (run or subprocess.run)(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                                 "stream=nb_read_frames", "-of", "csv=p=0", str(video)],
                                capture_output=True, text=True, timeout=300)
    try:
        return int((p.stdout or "").strip().split(",")[0])
    except ValueError:
        raise RuntimeError(f"ffprobe could not count the frames of {video}") from None
