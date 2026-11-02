#!/usr/bin/env python3
"""Writes studio/voice_proof.json and studio/web/voices/ from real renders. Nothing is invented: a model appears as rendered only if its file, its render log row and its measurements all exist.
Usage: build_voices_page.py WORK_DIR, where WORK_DIR holds line.py, renders/log.jsonl, renders/measure.json, renders/kokoro_sweep.json and the rendered files. Needs ffmpeg."""
import difflib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; STUDIO = ROOT / "studio"; WEB = STUDIO / "web" / "voices"
#: Under this share of the words, a render is shown with its number but doesn't count as proof.
MIN_MATCH = 60


def small(src, dst):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "1", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(dst)], check=True)


def words(t):
    t = t.lower()
    if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", t): return [c for c in t if re.match(r"[\u3040-\u30ff\u4e00-\u9fff]", c)]
    return re.sub(r"[^\w' ]+", " ", t).split()


def scored(heard, line):
    h, r = words(heard), words(line); hit = sum(b.size for b in difflib.SequenceMatcher(None, r, h, autojunk=False).get_matching_blocks())
    return {"match_pct": round(100 * hit / max(1, len(r)))}


def main(work):
    work = Path(work); ns = {}; exec((work / "line.py").read_text(encoding="utf-8"), ns); line = ns["LINE"]
    log = {}
    for l in (work / "renders" / "log.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(l); log[r["tag"]] = r
    meas = json.loads((work / "renders" / "measure.json").read_text(encoding="utf-8")); cat = json.loads((STUDIO / "voice_models.json").read_text(encoding="utf-8"))["models"]
    WEB.mkdir(parents=True, exist_ok=True); out = {}
    for m in cat:
        tag = m.get("tag") or m["id"]; r = log.get(tag)
        if not r or r.get("status") != "success": continue
        src = Path(r["out"]); rec = {"status": "success", "secs": r.get("secs"), "peak_gib": r.get("peak_gib"), "voice_note": m.get("note", "")}
        if m["kind"] == "listen":
            if not src.is_file(): continue
            text = src.read_text(encoding="utf-8").strip(); out[m["id"]] = {**rec, "text": text, **scored(text, ns["LINES"][m.get("listen_lang", "en")])}; continue
        d = meas.get(tag)
        if not d or not src.is_file(): continue
        small(src, WEB / f"{m['id']}.m4a"); rec.update({k: d.get(k) for k in ("seconds", "peak", "lufs", "true_peak_db", "silent_pct", "clipped_pct", "sample_rate", "match_pct", "wer_pct", "heard", "peaks", "sdr_in", "sdr_out")}, audio=f"voices/{m['id']}.m4a"); out[m["id"]] = rec
    kokoro = {}; sweep = work / "renders" / "kokoro_sweep.json"
    if sweep.exists():
        for v, r in json.loads(sweep.read_text(encoding="utf-8")).items():
            src = work / "renders" / "kokoro" / f"{v}.wav"
            if r.get("status") != "success" or not src.is_file(): continue
            small(src, WEB / f"kokoro_{v}.m4a"); pk = _peaks(src); kokoro[v] = {"lang": r["lang"], "seconds": r["seconds"], "peak": r["peak"], "lufs": r["lufs"], "match_pct": r["match_pct"], "heard": r["heard"], "secs": r["secs"], "peaks": pk, "audio": f"voices/kokoro_{v}.m4a"}
    proof = {"line": line, "measured": "Whisper (faster-distil-whisper large-v3 for English, large-v3 for other languages), ffmpeg ebur128 and a peak check. No person has listened.", "min_match": MIN_MATCH, "renders": out, "kokoro": kokoro}
    (STUDIO / "voice_proof.json").write_text(json.dumps(proof, ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(out), "models,", len(kokoro), "Kokoro voices,", sum(f.stat().st_size for f in WEB.iterdir()) // 1024, "KB of audio")


def _peaks(src, n=48):
    import numpy as np, soundfile as sf
    y, _ = sf.read(str(src), dtype="float32"); seg = np.array_split(np.abs(y if y.ndim == 1 else y.mean(axis=1)), n); pk = np.array([float(s.max()) if len(s) else 0 for s in seg])
    return [round(float(v), 2) for v in pk / (pk.max() + 1e-9)]


if __name__ == "__main__": main(sys.argv[1])
