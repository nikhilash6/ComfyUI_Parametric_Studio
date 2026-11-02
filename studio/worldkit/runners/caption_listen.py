"""Speech to timed words for captions: one audio file in, one JSON file out. Run by the Captions & Sound page in its own process, never inside ComfyUI.
usage: caption_listen.py --audio a.wav --out words.json [--model whisper_ct2_distil|whisper_ct2_large3|whisper_ct2_tiny] [--language en] [--device cpu|cuda]
It uses the same Whisper weights and config files as the Voices page (see voice_speak.py), and downloads nothing.
Silero VAD skips the silent parts before Whisper reads them, which is where most made-up words come from."""
import argparse, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voice_speak import m, view      # noqa: E402  same models folder, same config views

MODELS = {
    "whisper_ct2_distil": ("faster-distil-whisper-large-v3", ("_by_repo", "Systran__faster-distil-whisper-large-v3", "model.bin"), "en"),
    "whisper_ct2_large3": ("faster-whisper-large-v3", ("_complete_pipelines", "LongCat-Avatar-15", "audio_encoders", "model.bin"), None),
    "whisper_ct2_tiny": ("faster-whisper-tiny", ("_by_repo", "Systran__faster-whisper-tiny", "model.bin"), None),
}
NEEDS = ("config.json", "tokenizer.json")


def folder(mid):
    """A folder faster-whisper can open: the weights' own folder when it is a full download, else a view that adds the config files."""
    name, parts, _ = MODELS[mid]; weights = m(*parts); here = os.path.dirname(weights)
    if not os.path.isfile(weights): raise SystemExit(f"{mid}: the weights aren't in the models folder ({os.path.join(*parts)})")
    if all(os.path.isfile(os.path.join(here, f)) for f in NEEDS): return here
    return view(name, {"model.bin": weights})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True); p.add_argument("--out", required=True); p.add_argument("--model", default="whisper_ct2_distil", choices=sorted(MODELS))
    p.add_argument("--language", default=""); p.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    a = p.parse_args()
    from faster_whisper import WhisperModel
    only = MODELS[a.model][2]; lang = only or (a.language or None)
    t = time.time(); model = WhisperModel(folder(a.model), device=a.device, compute_type="float16" if a.device == "cuda" else "int8"); loaded = time.time() - t
    import numpy as np, soundfile as sf
    wav, sr = sf.read(a.audio, dtype="float32", always_2d=True)      # the page hands over 16 kHz mono; faster-whisper's own decoder needs a newer PyAV than some installs have
    if sr != 16000: raise SystemExit(f"expected 16 kHz audio, got {sr} Hz")
    segs, info = model.transcribe(np.ascontiguousarray(wav.mean(axis=1)), language=lang, task="transcribe", beam_size=5, word_timestamps=True, vad_filter=True, vad_parameters={"min_silence_duration_ms": 500},
                                  condition_on_previous_text=False, compression_ratio_threshold=2.4, log_prob_threshold=-1.0, no_speech_threshold=0.6)
    out = [{"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(), "no_speech": round(s.no_speech_prob, 3), "logprob": round(s.avg_logprob, 3), "compression": round(s.compression_ratio, 3),
            "words": [[round(w.start, 3), round(w.end, 3), w.word.strip(), round(w.probability, 3)] for w in (s.words or [])]} for s in segs]
    rec = {"model": a.model, "device": a.device, "language": info.language, "language_prob": round(info.language_probability or 0, 3), "duration": round(info.duration or 0, 3),
           "speech_seconds": round(getattr(info, "duration_after_vad", 0) or 0, 3), "segments": out, "load_s": round(loaded, 1), "wall_s": round(time.time() - t, 1)}
    with open(a.out, "w", encoding="utf-8") as f: json.dump(rec, f, ensure_ascii=False)
    print(json.dumps({"out": a.out, "segments": len(out), "language": info.language, "wall_s": rec["wall_s"], "model": a.model, "device": a.device}))


if __name__ == "__main__": main()
