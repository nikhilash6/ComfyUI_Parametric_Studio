"""The speech steps of the Dub page, each in its own process and never inside ComfyUI. One JSON line out per call.
  dub_steps.py speak --model qwen3_custom_17|qwen3_design_17|qwen3_base_17 --language Spanish --text "..." --out a.wav [--voice NAME_OR_DESCRIPTION] [--reference r.wav --reference-text "..." --reference-consent own|permission|synthetic] [--seed N]
  dub_steps.py translate --audio a16k.wav --out t.json [--device cpu|cuda]      Whisper large-v3's own translate task: any language it hears, written in English
  dub_steps.py similar --a one.wav --b two.wav                                 speaker similarity: cosine of Chatterbox's voice-encoder embeddings (its ve.pt), -1 to 1
Weights come from the models folder, as for the Voices page (voice_speak.py); nothing is downloaded. A reference is refused without a consent word."""
import argparse, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_speak as V      # noqa: E402  the same loaders and models folder as the Voices page

LANGUAGES = ("English", "Spanish", "French", "German", "Italian", "Portuguese", "Russian", "Japanese", "Korean", "Chinese")      # what Qwen3-TTS speaks, from its model card
SPEAKERS = ("Ryan", "Aiden", "Vivian", "Serena", "Dylan", "Eric", "Uncle_Fu", "Ono_Anna", "Sohee")


def speak(a):
    if a.language not in LANGUAGES: raise SystemExit(f"Qwen3-TTS doesn't speak {a.language}")
    if a.reference and not a.reference_consent: raise SystemExit("a reference clip needs --reference-consent: own, permission or synthetic")
    V.seed_all(a.seed)
    if a.model in ("qwen3_custom_17", "qwen3_custom_06"):
        path = V.m("qwen3_tts") if a.model.endswith("17") else V.m("TTS", "qwen3_tts", "Qwen3-TTS-12Hz-0.6B-CustomVoice")
        wavs, sr = V._qwen(path).generate_custom_voice(text=a.text, speaker=a.voice or "Ryan", language=a.language)
    elif a.model == "qwen3_design_17":
        wavs, sr = V._qwen(V.m("TTS", "qwen3_tts", "Qwen3-TTS-12Hz-1.7B-VoiceDesign")).generate_voice_design(text=a.text, instruct=a.voice or "A warm, calm adult narrator with a steady pace.", language=a.language)
    elif a.model in ("qwen3_base_17", "qwen3_base_06"):
        if not a.reference: raise SystemExit("cloning needs --reference with --reference-consent")
        n = "1.7B" if a.model.endswith("17") else "0.6B"
        wavs, sr = V._qwen(V.m("TTS", "qwen3_tts", f"Qwen3-TTS-12Hz-{n}-Base")).generate_voice_clone(text=a.text, language=a.language, ref_audio=a.reference, ref_text=a.reference_text)
    else: raise SystemExit("unknown model " + a.model)
    import numpy as np, soundfile as sf
    wav = np.asarray(wavs[0], dtype="float32").squeeze(); sf.write(a.out, wav, int(sr))
    return {"out": a.out, "sr": int(sr), "seconds": round(len(wav) / sr, 2), "model": a.model, "language": a.language}


def translate(a):
    from faster_whisper import WhisperModel
    import caption_listen as CL
    import numpy as np, soundfile as sf
    model = WhisperModel(CL.folder("whisper_ct2_large3"), device=a.device, compute_type="float16" if a.device == "cuda" else "int8")
    wav, sr = sf.read(a.audio, dtype="float32", always_2d=True)
    if sr != 16000: raise SystemExit(f"expected 16 kHz audio, got {sr} Hz")
    segs, info = model.transcribe(np.ascontiguousarray(wav.mean(axis=1)), task="translate", beam_size=5, vad_filter=True, condition_on_previous_text=False)
    segs = [{"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()} for s in segs]
    rec = {"heard_language": info.language, "language_prob": round(info.language_probability or 0, 3), "text": " ".join(s["text"] for s in segs).strip(), "segments": segs, "model": "whisper_ct2_large3", "task": "translate"}
    with open(a.out, "w", encoding="utf-8") as f: json.dump(rec, f, ensure_ascii=False)
    return {"out": a.out, "heard_language": info.language, "chars": len(rec["text"])}


def similar(a):
    import numpy as np, librosa, torch
    V._pkg_resources()
    from chatterbox.models.voice_encoder import VoiceEncoder
    ve = VoiceEncoder(); ve.load_state_dict(torch.load(V.m("TTS", "chatterbox", "English", "ve.pt"), map_location="cpu", weights_only=True)); ve.eval()
    embs = [ve.embeds_from_wavs([librosa.load(p, sr=16000)[0]], sample_rate=16000, as_spk=True) for p in (a.a, a.b)]
    x, y = (np.asarray(e, dtype="float64").ravel() for e in embs)
    return {"cosine": round(float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y))), 4), "encoder": "Chatterbox voice encoder (ve.pt)"}


def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("speak"); s.add_argument("--model", required=True); s.add_argument("--language", default="English"); s.add_argument("--text", required=True); s.add_argument("--out", required=True)
    s.add_argument("--voice"); s.add_argument("--reference"); s.add_argument("--reference-text"); s.add_argument("--reference-consent", choices=["own", "permission", "synthetic"]); s.add_argument("--seed", type=int, default=7)
    t = sub.add_parser("translate"); t.add_argument("--audio", required=True); t.add_argument("--out", required=True); t.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    c = sub.add_parser("similar"); c.add_argument("--a", required=True); c.add_argument("--b", required=True)
    a = p.parse_args(); t0 = time.time()
    rec = {"speak": speak, "translate": translate, "similar": similar}[a.cmd](a)
    print(json.dumps({**rec, "wall_s": round(time.time() - t0, 1)}, ensure_ascii=False))


if __name__ == "__main__": main()
