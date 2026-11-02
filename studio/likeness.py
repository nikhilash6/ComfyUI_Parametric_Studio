"""What every route that can move a person's face, voice or body must pass, wherever it is called from: the Motion page, the API, a family template.
Words go through the studio's safe-for-work list and World Kit's words for children and for a real person's likeness. Whoever calls must confirm that the person shown is invented or has given permission. Pictures and video frames go through the picture check: a readable adult face and nothing undressed; a check that cannot run does not pass.
What this cannot do: nothing here can tell a real person from an invented one, and it never sees a voice. The confirmation is the caller's word, kept next to the result. Pro and ComfyUI itself run raw graphs, and no check reaches them."""
from __future__ import annotations

import hashlib, json, subprocess, tempfile, time
from pathlib import Path

from fastapi import HTTPException

from studio import sfw
from studio.worldkit import picturecheck, safety

ASK = "Confirm that the person shown is invented, or has given you permission to use their face, voice and body this way."
LIKENESS_WORDS = "This route is for invented people, or people who have given permission. Your words ask for a real person's likeness, so it will not run."
#: Core and pack templates that puppet a person. Their family forms ask for the same confirmation, and a call without it is refused.
TEMPLATES = {"video_wan_animate2", "video_wan_animate2_distilled", "video_wan21_scail2_character_replacement", "video_wan21_scail2_character_replacement_int8", "video_wan2_1_infinitetalk", "video_wan_dancer", "motion_liveportrait", "motion_wan_animate2", "motion_scail2", "motion_infinitetalk", "motion_wan_dancer", "motion_sam3d_capture"}
FRAME_POINTS = (.1, .5, .9)
EXTRA_LIKENESS = (" deepfake ", " face swap ", " faceswap ", " impersonat", " clone her ", " clone his ", " clone their ", " pretend to be ")


def words_problem(*values) -> str:
    texts = list(sfw._texts(values))
    if sfw.flagged(*texts): return sfw.MESSAGE
    bad = safety.text_problem(*texts) or safety.character_text_problem(*texts)
    if bad: return bad
    joined = " " + " ".join(texts).lower() + " "
    if safety.likeness_problem(*texts) or any(w in joined for w in EXTRA_LIKENESS): return LIKENESS_WORDS
    return ""


def frames_of(video, *, run=subprocess.run, out=None) -> list[Path]:
    """Three frames, at 10, 50 and 90 per cent of a clip, for the picture check."""
    out = Path(out or tempfile.mkdtemp(prefix="motion_frames_")); got = []
    d = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video)], capture_output=True, text=True, timeout=60)
    try: seconds = float(d.stdout.strip())
    except ValueError: raise ValueError("this file cannot be read as a video")
    for i, p in enumerate(FRAME_POINTS):
        f = out / f"f{i}.jpg"; run(["ffmpeg", "-y", "-v", "error", "-ss", f"{seconds * p:.3f}", "-i", str(video), "-frames:v", "1", str(f)], capture_output=True, timeout=120)
        if f.exists(): got.append(f)
    return got


def picture_problem(path, *, check=picturecheck.check) -> str:
    rec = check(path)
    return "" if rec.get("ok") else "; ".join(rec.get("why") or ["the picture check did not pass"])


def video_problem(path, *, check=picturecheck.check, frames=frames_of) -> str:
    """Nothing undressed and nobody who reads as under age in any sampled frame, and at least one readable adult face among them: a body with no readable face cannot be called an adult."""
    fs = frames(path)
    if not fs: return "no frame could be read from this clip"
    why, faced = [], False
    for f in fs:
        rec = check(f); w = [x for x in (rec.get("why") or []) if not x.startswith("no face")]
        faced = faced or not any(x.startswith("no face") for x in rec.get("why") or [])
        why += w
    if why: return "; ".join(dict.fromkeys(why))
    return "" if faced else "no frame shows a face it can read, so it cannot say this person is an adult"


def guard(route: dict, body: dict, inputs: dict, *, check=picturecheck.check, frames=frames_of) -> None:
    """Raises 400 unless this call may run. inputs: {"image": path, "video": path} of what a person is seen in."""
    bad = words_problem(body.get("text"), body.get("prompt"), body.get("name"), [Path(str(v)).name for v in inputs.values()])
    if bad: raise HTTPException(400, bad)
    if not route.get("person"): return
    if body.get("permission") is not True: raise HTTPException(400, ASK)
    for k, p in inputs.items():
        if k == "audio": continue
        why = video_problem(p, check=check, frames=frames) if k == "video" else picture_problem(p, check=check)
        if why: raise HTTPException(400, f"The {k} did not pass the picture check: {why}. Nothing was run.")


def template_guard(tid: str, body: dict) -> None:
    """The Families page and API route to the same graphs: same words, same confirmation. Pictures there are checked by the Motion route only."""
    if tid not in TEMPLATES: return
    bad = words_problem(body.get("values"))
    if bad: raise HTTPException(400, bad)
    if body.get("permission") is not True: raise HTTPException(400, ASK)


def _hash(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def receipt(out, route: dict, body: dict, inputs: dict, seed=None, seconds=None) -> Path:
    """Beside the result: what made it, under which licence, and that the caller confirmed. No picture of anyone is copied into it."""
    p = Path(str(out) + ".json")
    p.write_text(json.dumps({"route": route["id"], "model": route["model"], "licence": route["licence"], "commercial": route["commercial"], "seed": seed, "seconds": seconds, "made": time.strftime("%Y-%m-%d %H:%M:%S"),
                             "permission_confirmed": body.get("permission") is True, "ai_generated": True, "inputs_sha256": {k: _hash(v) for k, v in inputs.items()}}, indent=1), encoding="utf-8")
    return p


def label_args(kind_note="AI-generated") -> list[str]:
    """ffmpeg arguments that say what this file is in its metadata."""
    return ["-metadata", f"comment={kind_note}. Made with Parametric Studio.", "-metadata", "description=AI-generated video of an invented person, or of a person who gave permission."]


def mark(src, dst, *, run=subprocess.run) -> Path:
    """A small AI-generated mark burned into the corner and the same words in the metadata, for anything that shows a person."""
    from PIL import Image, ImageDraw, ImageFont
    probe = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(src)], capture_output=True, text=True, timeout=60)
    w = int(probe.stdout.strip().split(",")[0]); fs = max(12, w // 42); text = "AI-generated"
    font = ImageFont.load_default(size=fs); box = font.getbbox(text); pad = fs // 3
    tag = Image.new("RGBA", (box[2] + pad * 2, box[3] + pad * 2), (0, 0, 0, 150)); ImageDraw.Draw(tag).text((pad, pad - box[1] // 2), text, font=font, fill=(255, 255, 255, 235))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f: tag.save(f.name)
    r = run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-i", f.name, "-filter_complex", f"[0:v][1:v]overlay=W-w-{fs}:H-h-{fs}", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "copy", *label_args(), "-movflags", "+faststart", str(dst)], capture_output=True, text=True, timeout=1800)
    Path(f.name).unlink(missing_ok=True)
    if r.returncode != 0 or not Path(dst).exists(): raise RuntimeError("could not mark the result: " + (r.stderr or "")[-300:])
    return Path(dst)
