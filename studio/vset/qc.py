"""Quality checks per shot, on the CPU, from the finished video. A flicker score (second-order frame difference on consecutive frames: smooth motion scores about 0, strobing and boiling score high) and how well the video keeps the set's structure (edge overlap
with the Blender edge pass, a number for review, never a gate). For a shot list, a set-consistency score across shots (colour-histogram correlation of each shot's frames with the first shot's). The face match is optional and off here: it needs a saved character
in the shot AND a face classifier handed in as `classify`, and this studio ships no face classifier, so `face` is None and the result says so. FLICKER_MAX and SET_MIN are starting guesses until real videos have been judged."""
from __future__ import annotations

import json
import statistics
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

FACE_MIN = 0.5
FLICKER_MAX = 6.0
SET_MIN = 0.6
FACE_FRAMES = 12
RUN_FRAMES = 24
SIDE = 128
LAYOUT_SIDE = 256


def _probe(video, run=None) -> tuple[float, float]:
    p = (run or subprocess.run)(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                 "stream=avg_frame_rate:format=duration", "-of", "json", str(video)],
                                capture_output=True, text=True, timeout=120)
    try:
        d = json.loads(p.stdout or "{}")
        dur = float(d["format"]["duration"])
        num, den = (float(x) for x in d["streams"][0]["avg_frame_rate"].split("/"))
        return dur, (num / den if den else 24.0)
    except (KeyError, IndexError, ValueError, ZeroDivisionError):
        raise RuntimeError(f"ffprobe could not read {video}") from None


def _extract(args: list, out_dir: Path, run=None) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        old.unlink()
    p = (run or subprocess.run)(["ffmpeg", "-y", "-v", "error", *args, str(out_dir / "%03d.png")],
                                capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg could not sample frames: {(p.stderr or '')[-300:]}")
    return sorted(out_dir.glob("*.png"))


def sample_frames(video, out_dir, n: int = FACE_FRAMES, *, run=None, full_size: bool = False) -> list[Path]:
    dur, _ = _probe(video, run)
    rate = n / max(dur, 1e-3)
    scale = "" if full_size else f",scale={SIDE * 2}:-2"
    return _extract(["-i", str(video), "-vf", f"fps={rate:.6f}{scale}", "-frames:v", str(n)], out_dir, run)


def run_frames(video, out_dir, n: int = RUN_FRAMES, *, run=None) -> list[Path]:
    dur, fps = _probe(video, run)
    start = max(0.0, dur / 2 - n / (2 * fps))
    return _extract(["-ss", f"{start:.3f}", "-i", str(video), "-vf", f"scale={SIDE}:-2", "-frames:v", str(n)],
                    out_dir, run)


def luma(path, side: int = SIDE) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("L").resize((side, side)), dtype=np.float32)


def flicker_score(frames: list) -> float:
    if len(frames) < 3:
        return 0.0
    d2 = [float(np.mean(np.abs(frames[t + 1] - 2 * frames[t] + frames[t - 1]))) for t in range(1, len(frames) - 1)]
    return round(float(np.mean(d2)), 4)


def face_score(frames, anchor, *, classify) -> float | None:
    """The median best match over the frames. classify(paths, anchor) -> {path: {"faces": [{"sim": float}, ...]}}."""
    res = classify([str(p) for p in frames], str(anchor))
    sims = [max(f["sim"] for f in r["faces"]) for r in res.values() if r.get("faces")]
    return float(statistics.median(sims)) if sims else None


def hist(path) -> np.ndarray:
    with Image.open(path) as im:
        a = np.asarray(im.convert("HSV").resize((64, 64)), dtype=np.int32)
    idx = (a[..., 0] * 8 // 256) * 16 + (a[..., 1] * 4 // 256) * 4 + (a[..., 2] * 4 // 256)
    v = np.bincount(idx.ravel(), minlength=128).astype(np.float64)
    return v / v.sum()


def set_score(a, b) -> float:
    ha, hb = np.mean([hist(p) for p in a], axis=0), np.mean([hist(p) for p in b], axis=0)
    if ha.std() == 0 or hb.std() == 0:
        return 1.0 if np.allclose(ha, hb) else 0.0
    return float(np.corrcoef(ha, hb)[0, 1])


def _edge_map(a: np.ndarray, thr: float = 24.0) -> np.ndarray:
    gx = np.abs(np.diff(a, axis=1, prepend=a[:, :1]))
    gy = np.abs(np.diff(a, axis=0, prepend=a[:1, :]))
    e = (gx > thr) | (gy > thr)
    grown = e.copy()
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        grown |= np.roll(np.roll(e, dy, axis=0), dx, axis=1)
    return grown


def _line_mask(path, side: int = LAYOUT_SIDE) -> np.ndarray:
    """The Blender edge pass at the working size. Its lines are one pixel wide, so they are thickened before the frame is shrunk, or they fade away."""
    with Image.open(path) as im:
        return np.asarray(im.convert("L").filter(ImageFilter.MaxFilter(5)).resize((side, side)), dtype=np.float32) > 60


def layout_score(output_frames, edge_frames) -> float:
    """Mean IoU between the output's edges and the Blender edge pass (both grown 1 px): does the video keep the set's structure and the camera move? A number for review, never a gate."""
    scores = []
    for o, e in zip(output_frames, edge_frames):
        oe = _edge_map(luma(o, LAYOUT_SIDE))
        ee = _line_mask(e)
        union = np.logical_or(oe, ee).sum()
        scores.append(float(np.logical_and(oe, ee).sum() / union) if union else 0.0)
    return round(float(np.mean(scores)), 4) if scores else 0.0


def judge(video, *, work, anchor: str = "", classify=None, edges: str = "", run=None) -> dict:
    work = Path(work)
    checks_face = bool(anchor and classify)
    face = face_score(sample_frames(video, work / "spread", run=run), anchor, classify=classify) if checks_face else None
    flick = flicker_score([luma(p) for p in run_frames(video, work / "run", run=run)])
    reasons = []
    if checks_face and (face is None or face < FACE_MIN):
        reasons.append(f"face match {'none' if face is None else f'{face:.2f}'.rstrip('0').rstrip('.')} < {FACE_MIN}")
    if flick > FLICKER_MAX:
        reasons.append(f"flicker {flick:.1f} > {FLICKER_MAX}")
    out = {"ok": not reasons, "face": face, "flicker": flick, "reasons": reasons, "face_checked": checks_face}
    if edges:
        out["layout"] = layout_score(sample_frames(video, work / "out", n=FACE_FRAMES, run=run), sample_frames(edges, work / "edges", n=FACE_FRAMES, run=run, full_size=True))
    return out


def list_consistency(firsts: dict) -> dict:
    ids = list(firsts)
    if len(ids) < 2:
        return {"scores": {}, "min": None, "ok": True}
    scores = {sid: round(set_score(firsts[ids[0]], firsts[sid]), 4) for sid in ids[1:]}
    lo = min(scores.values())
    return {"scores": scores, "min": lo, "ok": lo >= SET_MIN}
