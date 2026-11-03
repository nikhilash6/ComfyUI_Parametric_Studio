"""Several lines of a voice-over in one process, so the speech model loads once: the Commercials page's voice step. Each line is one WAV; manifest.json lists them with their lengths.
usage: vo_lines.py --model kokoro|qwen3_design_17 --lines lines.json --out DIR [--voice NAME_OR_DESCRIPTION] [--seed N]
lines.json: [{"id": "beat id", "text": "what to read"}]. Uses voice_speak.py's engines and models folder, and downloads nothing. No reference voices: nobody's voice is copied."""
import argparse, functools, json, os, sys, time
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_speak as V      # noqa: E402
ALLOWED = ("kokoro", "qwen3_design_17")


def main():
    p = argparse.ArgumentParser(); p.add_argument("--model", required=True, choices=ALLOWED); p.add_argument("--lines", required=True); p.add_argument("--out", required=True); p.add_argument("--voice"); p.add_argument("--seed", type=int, default=7)
    a = p.parse_args(); lines = json.load(open(a.lines, encoding="utf-8")); os.makedirs(a.out, exist_ok=True)
    if hasattr(V, "_qwen"): V._qwen = functools.lru_cache(maxsize=2)(V._qwen)      # load the speech model once for every line
    import numpy as np, soundfile as sf
    out = []; t0 = time.time()
    for n, x in enumerate(lines):
        V.seed_all(a.seed + n); t = time.time()
        wav, sr = V.ENGINES[a.model](SimpleNamespace(model=a.model, text=x["text"], voice=a.voice, reference=None, reference_text=None, reference_consent=None, audio=None, seed=a.seed + n))
        wav = np.asarray(wav, dtype="float32").squeeze(); f = os.path.join(a.out, f"{x['id']}.wav"); sf.write(f, wav, int(sr))
        out.append({"id": x["id"], "text": x["text"], "file": f, "seconds": round(len(wav) / sr, 3), "sr": int(sr), "wall_s": round(time.time() - t, 1)})
    rec = {"model": a.model, "voice": a.voice, "lines": out, "wall_s": round(time.time() - t0, 1)}
    with open(os.path.join(a.out, "manifest.json"), "w", encoding="utf-8") as f: json.dump(rec, f, ensure_ascii=False)
    print(json.dumps({"lines": len(out), "wall_s": rec["wall_s"], "model": a.model}))


if __name__ == "__main__": main()
