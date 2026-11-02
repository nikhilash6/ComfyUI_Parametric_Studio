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


# ---------- matte -> cutout: the source clip with the LTX-2.5 Alpha-Gen matte as its alpha channel, ready for compositing
CHECKER = "nullsrc=s={w}x{h}:r=24,geq=lum='if(mod(floor(X/24)+floor(Y/24),2),205,150)':cb=128:cr=128,format=yuv420p"


def probe(p):
    """-> (width, height, seconds) of a video's first stream."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True, timeout=20)
    try:
        lines = [l for l in r.stdout.split() if l]; w, h = (int(x) for x in lines[0].split(",")[:2]); return w, h, float(lines[1])
    except (ValueError, IndexError): raise HTTPException(400, f"{p.name} isn't a readable video") from None


def cutout_filter(w, h, seconds):
    """The source is fitted the way the VFX graph fits it (24 fps, scaled to cover, centre crop), so the matte lands on the frames it was made from."""
    src = f"[0:v]fps=24,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,format=yuv444p,trim=duration={seconds},setpts=PTS-STARTPTS[s]"
    matte = f"[1:v]format=gray,scale={w}:{h},setsar=1,trim=duration={seconds},setpts=PTS-STARTPTS[m]"
    board = CHECKER.format(w=w, h=h) + f",trim=duration={seconds}[bg]"
    return ";".join([src, matte, "[s][m]alphamerge,split[cut][see]", board, "[bg][see]overlay=format=auto,format=yuv420p[prev]"])


@router.post("/api/shotboard/cutout")
def cutout(b: dict):
    if not shutil.which("ffmpeg"): raise HTTPException(503, "ffmpeg isn't installed")
    src, matte = resolve_item({**(b.get("source") or {}), "type": "input"}), resolve_item({**(b.get("matte") or {}), "type": "output"})
    w, h, seconds = probe(matte); seconds = round(min(seconds, MAX_SECONDS * 2), 3)
    out_dir = Path(paths.output_dir(True)) / "shotboard"; out_dir.mkdir(parents=True, exist_ok=True); stem = f"cutout_{time.strftime('%Y%m%d_%H%M%S')}"
    mov, prev = out_dir / f"{stem}.mov", out_dir / f"{stem}_preview.mp4"
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(src), "-i", str(matte), "-filter_complex", cutout_filter(w, h, seconds),
           "-map", "[cut]", "-map", "1:a?", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-c:a", "pcm_s16le", "-shortest", str(mov),
           "-map", "[prev]", "-an", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(prev)]
    try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired: raise HTTPException(504, "the cutout took over 10 minutes") from None
    if r.returncode: raise HTTPException(500, "ffmpeg failed: " + r.stderr.strip()[-300:])
    url = lambda p: "/api/view?" + urllib.parse.urlencode({"filename": p.name, "subfolder": "shotboard", "type": "output"})
    return {"mov": {"filename": mov.name, "url": url(mov)}, "preview": {"filename": prev.name, "url": url(prev)}, "width": w, "height": h, "seconds": seconds}


# ---------- a postable before/after reel of one take: 16:9 wipe, 1:1 crop of it, 9:16 stack; each ends on a card and carries an AI-generated label
REEL_HOLD, REEL_WIPE, REEL_CARD = 0.6, 1.6, 2.0
BG = "0x0a0c0a"


def _text(td, name, s):
    p = os.path.join(td, name); open(p, "w", encoding="utf-8").write(s); return p


def reel_filter(seconds, label_file, before_file, card_files, font):
    """Inputs: 0 source, 1 take. Outputs [r169], [r11], [r916]. Text always comes from files (no escaping of user words)."""
    t = lambda f, size, x, y, extra="": f"drawtext=fontfile='{font}':textfile='{f}':expansion=none:fontcolor=white:fontsize={size}:x={x}:y={y}{extra}"
    ai = lambda size, pad: f"drawbox=x=iw-{size * 8}-{pad}:y={pad}:w={size * 8}:h={int(size * 1.9)}:color=black@0.6:t=fill," + t(card_files["ai"], size, f"w-{size * 8}-{pad}+{size // 2}", f"{pad}+{int(size * 0.45)}")
    fit = lambda i, w, h, extra="": f"[{i}:v]fps=24,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,format=yuv420p{extra}"
    d, after_len = seconds, round(seconds - REEL_HOLD, 3)
    card = lambda w, h, s: (f"color=c={BG}:s={w}x{h}:r=24:d={REEL_CARD},format=yuv420p," + t(card_files["title"], int(s * 1.5), "(w-tw)/2", f"h/2-{int(s * 2.6)}") + "," + t(card_files["what"], s, "(w-tw)/2", f"h/2-{int(s * 0.4)}", ":fontcolor=0xf5c518") + "," + t(card_files["how"], int(s * 0.8), "(w-tw)/2", f"h/2+{int(s * 1.3)}") + "," + t(card_files["tag"], int(s * 0.8), "(w-tw)/2", f"h/2+{int(s * 2.6)}"))
    on_before, on_after = f":enable='lt(t,{REEL_HOLD + REEL_WIPE})'", f":enable='gte(t,{REEL_HOLD})'"
    sides = lambda size, pad: (t(before_file, size, pad, f"h-{pad}-{size}", ":box=1:boxcolor=black@0.55:boxborderw=12" + on_before) + "," +
                               t(label_file, size, f"w-tw-{pad}", f"h-{pad}-{size}", ":box=1:boxcolor=black@0.55:boxborderw=12" + on_after))      # wipeleft brings the take in from the right
    parts = [
        fit(0, 1920, 1080, f",trim=duration={d},setpts=PTS-STARTPTS") + "[b169]",
        fit(1, 1920, 1080, f",trim=start={REEL_HOLD}:duration={after_len},setpts=PTS-STARTPTS") + "[a169]",       # the take, shifted so its frames line up with the source's during the wipe
        f"[b169][a169]xfade=transition=wipeleft:duration={REEL_WIPE}:offset={REEL_HOLD},split[w1][w2]",
        "[w1]" + sides(40, 40) + "," + ai(30, 30) + "[v169]", card(1920, 1080, 46) + "," + ai(30, 30) + "[c169]", "[v169][c169]concat=n=2:v=1:a=0[r169]",
        "[w2]crop=1080:1080,setsar=1," + sides(34, 28) + "," + ai(26, 24) + "[sq]", card(1080, 1080, 30) + "," + ai(26, 24) + "[c11]", "[sq][c11]concat=n=2:v=1:a=0[r11]",
        fit(0, 1080, 608, f",trim=duration={d},setpts=PTS-STARTPTS") + "," + t(before_file, 34, 28, "h-62", ":box=1:boxcolor=black@0.55:boxborderw=10") + "[sb]",
        fit(1, 1080, 608, f",trim=duration={d},setpts=PTS-STARTPTS") + "," + t(label_file, 34, 28, "h-62", ":box=1:boxcolor=black@0.55:boxborderw=10") + "[sa]",
        f"color=c={BG}:s=1080x1920:r=24:d={d},format=yuv420p[tall]", "[tall][sb]overlay=0:300[t1]", "[t1][sa]overlay=0:940," + t(card_files["what"], 44, "(w-tw)/2", "150") + "," + ai(30, 30) + "[s916]",
        card(1080, 1920, 30) + "," + ai(30, 30) + "[c916]", "[s916][c916]concat=n=2:v=1:a=0[r916]",
    ]
    return ";".join(parts)


@router.post("/api/shotboard/reel")
def reel(b: dict):
    if not shutil.which("ffmpeg"): raise HTTPException(503, "ffmpeg isn't installed")
    src, take = resolve_item({**(b.get("source") or {}), "type": "input"}), resolve_item({**(b.get("take") or {}), "type": "output"})
    font = next((f for f in FONTS if os.path.exists(f)), None)
    if not font: raise HTTPException(503, "no font found for the reel's captions")
    seconds = round(min(MAX_SECONDS, duration(src), duration(take)), 3)
    if seconds < REEL_HOLD + REEL_WIPE + 0.5: raise HTTPException(400, "the take is too short for a reel; it needs about 3 seconds")
    label = " ".join(str(b.get("label") or "the take").split())[:40]
    out_dir = Path(paths.output_dir(True)) / "shotboard"; out_dir.mkdir(parents=True, exist_ok=True); stem = f"reel_{time.strftime('%Y%m%d_%H%M%S')}"
    outs = {"16x9": out_dir / f"{stem}_16x9.mp4", "1x1": out_dir / f"{stem}_1x1.mp4", "9x16": out_dir / f"{stem}_9x16.mp4"}
    with tempfile.TemporaryDirectory() as td:
        cards = {"ai": _text(td, "ai.txt", "AI-generated"), "title": _text(td, "title.txt", "One clip in, a whole shoot out"), "what": _text(td, "what.txt", f"Before and after: {label}"),
                 "how": _text(td, "how.txt", "Parametric Studio Shot Board, open weights on one local GPU"), "tag": _text(td, "tag.txt", "#OpenSourceHiggsfield")}
        fc = reel_filter(seconds, _text(td, "label.txt", f"After: {label}"), _text(td, "before.txt", "Before"), cards, font)
        enc = ["-an", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(src), "-i", str(take), "-filter_complex", fc]
        for key, tag in (("16x9", "[r169]"), ("1x1", "[r11]"), ("9x16", "[r916]")): cmd += ["-map", tag, *enc, str(outs[key])]
        try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired: raise HTTPException(504, "the reel took over 10 minutes") from None
    if r.returncode: raise HTTPException(500, "ffmpeg failed: " + r.stderr.strip()[-300:])
    url = lambda p: "/api/view?" + urllib.parse.urlencode({"filename": p.name, "subfolder": "shotboard", "type": "output"})
    return {k: {"filename": p.name, "url": url(p)} for k, p in outs.items()} | {"seconds": round(seconds + REEL_CARD, 3)}
