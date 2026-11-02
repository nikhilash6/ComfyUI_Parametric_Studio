"""Captions from speech: Whisper's timed words in, SRT and WebVTT out, and an ffmpeg filter that draws them onto the clip.
The letters are real text set by libass from a system font, never pixels a model painted, so they can't come out as gibberish.
Pure apart from the command lines it builds: the transcription runs in studio/worldkit/runners/caption_listen.py, in its own process."""
import re, statistics

# What Whisper writes over silence, music or noise when it has nothing to hear. Dropped only when the segment also looks unheard.
STOCK = {"thank you", "thank you so much", "thanks for watching", "thank you for watching", "thanks for watching and see you next time", "please subscribe",
         "subscribe", "like and subscribe", "bye", "bye bye", "you", "oh", "hmm", "uh", "um", "ah", "so", "okay", "music", "applause", "laughter",
         "subtitles by the amara org community", "transcribed by", "i'll see you next time", "see you next time", "see you in the next video"}
MAX_REPEAT = 2.4      # Whisper's own compression-ratio limit: above it the text is a loop ("m-m-m-m-m")
STYLES = {
    "outline": "BorderStyle=1,Outline=2,Shadow=0,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000",
    "box": "BorderStyle=3,Outline=4,Shadow=0,PrimaryColour=&H00FFFFFF,OutlineColour=&H50000000",
    "yellow": "BorderStyle=1,Outline=2,Shadow=1,PrimaryColour=&H0018C5F5,OutlineColour=&H00000000",
}
SIZES = {"small": 0.05, "medium": 0.062, "large": 0.078}      # share of the short side; libass draws on a 288-line canvas scaled to the clip
PLACES = {"bottom": 2, "top": 8}
FONT = "DejaVu Sans"


def norm(text):
    """Lower case, letters and digits only: for comparing, never for showing."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']+", " ", str(text or "").lower())).strip()


def clean(text):
    """Text that is safe to hand to a subtitle file and to libass: no control characters, no markup, no override braces."""
    t = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", str(text or ""))
    t = t.replace("\\", "/").replace("{", "(").replace("}", ")").replace("<", "").replace(">", "")
    return re.sub(r"\s+", " ", t).strip()


def confidence(seg):
    """Mean word probability, 1.0 when Whisper gave no words."""
    ps = [w[3] for w in seg.get("words") or [] if len(w) > 3 and w[3] is not None]
    return statistics.fmean(ps) if ps else 1.0


def why_dropped(seg):
    """Why a segment is left out of the captions, or "" to keep it. Only the classic hallucinations go: a loop, silence read as words, a stock phrase nobody said."""
    t = norm(seg.get("text"))
    if not t: return "empty"
    if (seg.get("compression") or 0) > MAX_REPEAT: return "repeats itself"
    ns, lp = seg.get("no_speech") or 0.0, seg.get("logprob") if seg.get("logprob") is not None else 0.0
    if ns > 0.6 and lp < -1.0: return "silence read as words"
    if t in STOCK and (ns > 0.1 or confidence(seg) < 0.75 or lp < -0.7): return "stock phrase over no speech"
    return ""


def split_kept(segments):
    kept, dropped = [], []
    for s in segments or []:
        why = why_dropped(s)
        (dropped.append({"start": s.get("start"), "end": s.get("end"), "text": clean(s.get("text")), "why": why}) if why else kept.append(s))
    return kept, dropped


def layout(width, height, size="medium"):
    """(font points on libass's 288-line canvas, characters per line) for a clip. A tall clip gets smaller type and shorter lines, so two lines always fit across it."""
    try: ratio = float(width) / float(height)
    except (TypeError, ValueError, ZeroDivisionError): ratio = 16 / 9
    across = 288.0 * ratio; unit = min(288.0, across * 1.1); pt = round(SIZES.get(size, SIZES["medium"]) * unit, 1)
    return pt, max(12, min(42, int(0.92 * across / (0.62 * pt))))


def wrap(text, width, lines=2):
    """Split text into at most `lines` lines of about `width` characters, balanced so the last line isn't a stub."""
    words = text.split()
    if len(text) <= width or lines < 2 or len(words) < 2: return [text]
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:]); worst = max(len(a), len(b))
        if best is None or worst < best[0]: best = (worst, [a, b])
    return best[1]


def _word_rows(seg):
    ws = [w for w in seg.get("words") or [] if len(w) >= 3 and str(w[2]).strip()]
    if ws: return [(float(w[0]), float(w[1]), clean(w[2])) for w in ws]
    # no word timings: spread the segment's words evenly over its span
    toks = clean(seg.get("text")).split(); a, b = float(seg.get("start") or 0), float(seg.get("end") or 0)
    if not toks: return []
    step = max(0.01, (b - a) / len(toks)); return [(a + i * step, a + (i + 1) * step, t) for i, t in enumerate(toks)]


def cues(segments, width=42, lines=2, max_secs=6.0, min_secs=0.8, gap=0.9):
    """Kept segments -> [{start, end, lines}]. A cue ends at a full stop once its first line is mostly full, at a pause, when it would overflow, or after max_secs."""
    rows = [r for s in segments or [] for r in _word_rows(s)]
    out, cur = [], []
    limit = width * lines

    def flush():
        if cur:
            text = " ".join(w for _, _, w in cur).strip()
            if text: out.append({"start": cur[0][0], "end": cur[-1][1], "lines": wrap(text, width, lines)})
        cur.clear()

    for r in rows:
        if cur:
            text = " ".join(w for _, _, w in cur + [r])
            if len(text) > limit or r[1] - cur[0][0] > max_secs or r[0] - cur[-1][1] > gap: flush()
        cur.append(r)
        if re.search(r"[.!?]$", r[2]) and len(" ".join(w for _, _, w in cur)) >= width * 0.6: flush()
    flush()
    for i, c in enumerate(out):      # long enough to read, never over the next one
        nxt = out[i + 1]["start"] if i + 1 < len(out) else None
        want = max(c["end"], c["start"] + min_secs)
        c["end"] = round(min(want, nxt) if nxt is not None else want, 3); c["start"] = round(max(0.0, c["start"]), 3)
        if c["end"] <= c["start"]: c["end"] = round(c["start"] + 0.05, 3)
    return out


def _stamp(t, sep):
    ms = int(round(max(0.0, float(t)) * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def srt(cs):
    return "".join(f"{i}\n{_stamp(c['start'], ',')} --> {_stamp(c['end'], ',')}\n" + "\n".join(c["lines"]) + "\n\n" for i, c in enumerate(cs, 1))


def vtt(cs):
    body = "".join(f"{_stamp(c['start'], '.')} --> {_stamp(c['end'], '.')}\n" + "\n".join(x.replace("&", "&amp;") for x in c["lines"]) + "\n\n" for c in cs)
    return "WEBVTT\n\n" + body


def transcript(cs): return " ".join(" ".join(c["lines"]) for c in cs).strip()


def force_style(style="outline", pt=18.0, place="bottom"):
    """The libass style line for the burn-in. Unknown names fall back to the defaults rather than reaching ffmpeg."""
    st = STYLES.get(style, STYLES["outline"]); pt = max(4.0, min(60.0, float(pt))); al = PLACES.get(place, PLACES["bottom"])
    return f"FontName={FONT},Bold=1,Fontsize={pt},{st},Alignment={al},MarginV=14,MarginL=12,MarginR=12,WrapStyle=0"


def burn_command(ffmpeg, clip, srt_name, out, style="outline", pt=18.0, place="bottom", copy_audio=True):
    """ffmpeg drawing the captions onto the clip. Run it with cwd set to the folder holding srt_name, so no path ever goes through the filter's own quoting."""
    if not re.fullmatch(r"[\w.-]+\.srt", srt_name): raise ValueError("the caption file name must be plain")
    vf = f"subtitles=filename={srt_name}:charenc=UTF-8:force_style='{force_style(style, pt, place)}'"
    return [ffmpeg, "-nostdin", "-y", "-v", "error", "-i", str(clip), "-vf", vf, "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-pix_fmt", "yuv420p", *(["-c:a", "copy"] if copy_audio else ["-c:a", "aac", "-b:a", "192k"]), "-movflags", "+faststart", str(out)]


def audio_command(ffmpeg, clip, wav):
    """The clip's first audio track as 16 kHz mono, which is what Whisper hears."""
    return [ffmpeg, "-nostdin", "-y", "-v", "error", "-i", str(clip), "-vn", "-map", "0:a:0", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)]
