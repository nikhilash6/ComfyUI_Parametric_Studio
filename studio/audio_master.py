"""Voiceover over music, ducked, then mastered to a loudness target (-14 LUFS integrated, true peak at or under -1 dBTP by default). Standard library plus ffmpeg only.
Every number comes from ffmpeg's own meters: ebur128 for loudness and true peak, silencedetect for where the voice speaks. Nothing here guesses a level.
Ducking is a volume curve drawn on the music from the voice's speech sections, not a compressor, so the depth is exact and can be measured afterwards on the stems."""
import json, math, os, re, shutil, subprocess, tempfile
from pathlib import Path

TARGET_LUFS, TARGET_TP, TOLERANCE = -14.0, -1.0, 0.5
DEPTH_DB, BED_DB, RAMP_S, GAP_S = 12.0, 6.0, 0.25, 0.45      # music this far under the voice while it speaks; this far under between lines; fade time; pauses shorter than this stay ducked
SR = 48000


def ffmpeg(): return shutil.which("ffmpeg") or str(Path.home() / ".local" / "bin" / "ffmpeg")


def _run(cmd, run=subprocess.run, timeout=900):
    r = run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode: raise RuntimeError("ffmpeg failed: " + (r.stderr or "")[-400:])
    return r


def parse_ebur128(text):
    """ffmpeg's ebur128 summary -> {lufs, lra, true_peak}. The summary is the last block; earlier lines are per-frame readings."""
    tail = text[text.rfind("Summary:"):] if "Summary:" in text else text
    def num(label):
        m = re.search(label + r":\s+(-?inf|-?[\d.]+)", tail)
        return None if not m else (-math.inf if "inf" in m.group(1) else float(m.group(1)))
    return {"lufs": num(r"\bI"), "lra": num("LRA"), "true_peak": num("Peak")}


def measure(path, run=subprocess.run, start=None, end=None):
    """Integrated loudness, loudness range and true peak of a file (or a stretch of it), from ebur128 with true-peak metering."""
    cut = ([f"atrim=start={start}:end={end},asetpts=PTS-STARTPTS,"] if start is not None else [""])[0]
    r = _run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", f"{cut}ebur128=peak=true:framelog=quiet", "-f", "null", "-"], run)
    return parse_ebur128(r.stderr or "")


def measure_sections(path, sections, run=subprocess.run):
    """Loudness of only the listed (start, end) stretches, joined: how loud the music is while the voice speaks."""
    if not sections: return {"lufs": None, "lra": None, "true_peak": None}
    parts = ";".join(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[s{i}]" for i, (a, b) in enumerate(sections))
    graph = parts + ";" + "".join(f"[s{i}]" for i in range(len(sections))) + f"concat=n={len(sections)}:v=0:a=1,ebur128=peak=true:framelog=quiet[out]"
    r = _run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-filter_complex", graph, "-map", "[out]", "-f", "null", "-"], run)
    return parse_ebur128(r.stderr or "")


def duration(path, run=subprocess.run):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True, timeout=60)
    try: return float((r.stdout or "0").strip())
    except ValueError: return 0.0


def parse_silences(text, total):
    """silencedetect output -> the speech sections between silences, as [(start, end)]."""
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", text)]; ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", text)]
    quiet = list(zip(starts, ends + [total] * (len(starts) - len(ends))))
    out, t = [], 0.0
    for a, b in quiet:
        if a - t > 0.05: out.append((max(0.0, t), a))
        t = b
    if total - t > 0.05: out.append((t, total))
    return out


def merge(sections, gap=GAP_S):
    """Join speech sections whose pause is shorter than gap, so the music doesn't pump between words."""
    out = []
    for a, b in sorted(sections):
        if out and a - out[-1][1] < gap: out[-1] = (out[-1][0], max(out[-1][1], b))
        else: out.append((a, b))
    return out


def speech_sections(voice, run=subprocess.run, noise_db=-40, min_silence=0.3):
    total = duration(voice, run)
    r = _run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(voice), "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"], run)
    return merge(parse_silences(r.stderr or "", total))


def duck_expression(sections, duck_gain, ramp=RAMP_S):
    """A volume expression for ffmpeg: 1 between lines, duck_gain inside each section, with linear ramps of `ramp` seconds outside each edge."""
    if not sections: return "1"
    terms = [f"clip(min((t-{a - ramp:.3f})/{ramp},({b + ramp:.3f}-t)/{ramp}),0,1)" for a, b in sections]
    inside = terms[0] if len(terms) == 1 else "max(" + ",".join(terms[:2]) + ")"
    for t in terms[2:]: inside = f"max({inside},{t})"
    return f"1-(1-{duck_gain:.6f})*{inside}"


def db(x): return 10 ** (x / 20)


def plan(voice_lufs, music_lufs, depth=DEPTH_DB, bed=BED_DB):
    """Gains for the music: `bed_gain_db` sets it `bed` dB under the voice between lines, and `duck_gain` (a ratio) takes it to `depth` dB under while the voice speaks."""
    bed_gain = voice_lufs - bed - music_lufs
    return {"bed_gain_db": round(bed_gain, 2), "duck_gain": round(db(-(depth - bed)), 6), "depth_db": depth, "bed_db": bed}


def duck_music_command(music, out, seconds, bed_gain_db, expression):
    return [ffmpeg(), "-y", "-hide_banner", "-i", str(music), "-af",
            f"aresample={SR},aformat=channel_layouts=stereo,apad,atrim=0:{seconds:.3f},volume={bed_gain_db:.2f}dB,volume='{expression}':eval=frame", "-ar", str(SR), "-c:a", "pcm_s24le", str(out)]


def mix_command(voice, music_stem, out, voice_offset=0.0):
    delay = int(round(voice_offset * 1000))
    return [ffmpeg(), "-y", "-hide_banner", "-i", str(voice), "-i", str(music_stem), "-filter_complex",
            f"[0:a]aresample={SR},aformat=channel_layouts=stereo,adelay={delay}:all=1[v];[v][1:a]amix=inputs=2:duration=longest:normalize=0[m]", "-map", "[m]", "-ar", str(SR), "-c:a", "pcm_s24le", str(out)]


def loudnorm_first(src, target=TARGET_LUFS, tp=TARGET_TP, run=subprocess.run):
    """loudnorm's first pass: what it measured, as its JSON."""
    r = _run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(src), "-af", f"loudnorm=I={target}:TP={tp - 0.5}:LRA=20:print_format=json", "-f", "null", "-"], run)
    text = r.stderr or ""; j = text[text.rfind("{"):text.rfind("}") + 1]
    return json.loads(j)


def master_command(src, dst, m, target=TARGET_LUFS, tp=TARGET_TP):
    """loudnorm's second pass in linear mode (one gain for the whole file, so the mix keeps its dynamics), with the first pass's numbers."""
    ln = (f"loudnorm=I={target}:TP={tp - 0.5}:LRA=20:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    return [ffmpeg(), "-y", "-hide_banner", "-i", str(src), "-af", f"{ln},aresample={SR}", "-ar", str(SR), "-c:a", "pcm_s24le", str(dst)]


def fix_command(src, dst, gain_db, tp=TARGET_TP):
    """A last trim when linear loudnorm couldn't reach the target without clipping: the gain, then a limiter run 4x oversampled so true peaks are caught, not only samples."""
    limit = db(tp - 0.6)
    return [ffmpeg(), "-y", "-hide_banner", "-i", str(src), "-af", f"volume={gain_db:.2f}dB,aresample={SR * 4},alimiter=limit={limit:.5f}:attack=1:release=60:level=disabled,aresample={SR}",
            "-ar", str(SR), "-c:a", "pcm_s24le", str(dst)]


def within(m, target=TARGET_LUFS, tp=TARGET_TP, tol=TOLERANCE):
    return m.get("lufs") is not None and abs(m["lufs"] - target) <= tol and m.get("true_peak") is not None and m["true_peak"] <= tp


def master(src, dst, target=TARGET_LUFS, tp=TARGET_TP, run=subprocess.run):
    """Master one file to the target. Two loudnorm passes, then at most two trims with a true-peak limiter. -> the report, with the final measurement and whether it passes."""
    steps = []
    with tempfile.TemporaryDirectory() as td:
        first = loudnorm_first(src, target, tp, run); steps.append({"step": "loudnorm measure", "input_i": float(first["input_i"]), "input_tp": float(first["input_tp"])})
        cur = Path(td) / "pass2.wav"; _run(master_command(src, cur, first, target, tp), run); got = measure(cur, run); steps.append({"step": "loudnorm linear", **got})
        for i in range(2):
            if within(got, target, tp): break
            nxt = Path(td) / f"fix{i}.wav"; _run(fix_command(cur, nxt, target - got["lufs"], tp), run); cur = nxt; got = measure(cur, run); steps.append({"step": f"trim {i + 1}", **got})
        Path(dst).parent.mkdir(parents=True, exist_ok=True); shutil.copy(cur, dst)
    return {"target_lufs": target, "target_tp": tp, "tolerance": TOLERANCE, "final": got, "passes": within(got, target, tp), "steps": steps}


def voiceover(voice, music, dst, *, target=TARGET_LUFS, tp=TARGET_TP, depth=DEPTH_DB, bed=BED_DB, voice_offset=0.5, tail=1.5, run=subprocess.run, stems_dir=None):
    """Voice over music: music levelled under the voice, ducked while it speaks, mixed, mastered. Measures the depth on the stems afterwards.
    -> report {sections, plan, ducking: {voice_lufs, music_lufs_under_voice, depth_db, passes}, master: {...}}"""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td); stems = Path(stems_dir) if stems_dir else td; stems.mkdir(parents=True, exist_ok=True)
        v = stems / "voice.wav"; _run([ffmpeg(), "-y", "-hide_banner", "-i", str(voice), "-af", f"aresample={SR},aformat=channel_layouts=stereo,adelay={int(voice_offset * 1000)}:all=1", "-ar", str(SR), "-c:a", "pcm_s24le", str(v)], run)
        secs = [(round(a, 3), round(b, 3)) for a, b in speech_sections(v, run)]
        total = duration(v, run) + tail
        vl = measure_sections(v, secs, run)["lufs"]; ml = measure(music, run)["lufs"]
        if vl is None or ml is None or vl == -math.inf or ml == -math.inf: raise RuntimeError("the voice or the music is silent")
        p = plan(vl, ml, depth, bed)
        ms = stems / "music_ducked.wav"; _run(duck_music_command(music, ms, total, p["bed_gain_db"], duck_expression(secs, p["duck_gain"])), run)
        under = measure_sections(ms, secs, run)["lufs"]
        mixed = td / "mix.wav"; _run(mix_command(v, ms, mixed, 0.0), run)
        mreport = master(mixed, dst, target, tp, run)
    depth_measured = None if under is None else round(vl - under, 2)
    return {"sections": secs, "plan": p, "ducking": {"voice_lufs": round(vl, 2), "music_lufs_under_voice": under, "depth_db": depth_measured, "passes": depth_measured is not None and depth_measured >= 8.0}, "master": mreport}
