"""Speech to timed captions: faster-whisper distil large-v3 on the CPU, one SRT cue per segment. Uses the Voices page's runner for the model folder, so the weights are the same files its proof read.
usage: captions_srt.py --audio IN --out OUT.srt"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_speak as V

def stamp(t): ms = int(round(t * 1000)); return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
def main():
    p = argparse.ArgumentParser(); p.add_argument("--audio", required=True); p.add_argument("--out", required=True); a = p.parse_args(); t = time.time()
    from faster_whisper import WhisperModel
    d = V.view("faster-distil-whisper-large-v3", {"model.bin": V.m("_by_repo", "Systran__faster-distil-whisper-large-v3", "model.bin")})
    segs, _ = WhisperModel(d, device="cpu", compute_type="int8").transcribe(V._load16k(a.audio), language="en", beam_size=3, condition_on_previous_text=False)
    rows = [s for s in segs if s.text.strip()]
    with open(a.out, "w", encoding="utf-8") as f:
        for i, s in enumerate(rows, 1): f.write(f"{i}\n{stamp(s.start)} --> {stamp(s.end)}\n{s.text.strip()}\n\n")
    print(json.dumps({"out": a.out, "cues": len(rows), "text": " ".join(s.text.strip() for s in rows), "wall_s": round(time.time() - t, 1)}))
if __name__ == "__main__": main()
