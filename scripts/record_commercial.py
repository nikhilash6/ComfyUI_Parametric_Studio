#!/usr/bin/env python3
"""Put a real Commercials run on the page, after a person has looked at it.
  python scripts/record_commercial.py <run folder> --id <spot id> [--review review.json] [--measured measured.json]
<run folder> is the studio's studio_recipes/<run> folder. The spot is copied into studio/web/commercials/<id>/ at web size, with a poster, one strip of frames per shot (first, middle and last frame of what's on screen) and a contact sheet, and studio/commercial_proof.json gets its entry.
Run it once without --review to make the strips, look at every one, then again with the review:
  {"status": "passed|flawed|failed", "verdict": "What you saw.", "flaws": ["..."], "shots": {"bicycle": {"status": "flawed", "note": "..."}}}
--measured is what the render driver measured outside the studio: {"my_peak_gib": 46.1, "declared_gib": 48}. Nobody listening is recorded as such: the audio facts come from ffmpeg and Whisper only."""
import argparse, json, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from studio import commercials as C, recipes as R          # noqa: E402
WEB = ROOT / "studio" / "web" / "commercials"; PROOF = ROOT / "studio" / "commercial_proof.json"


def ff(*a): subprocess.run(["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error", *map(str, a)], check=True)


def windows(s):
    """(id, start, end) of each shot, the end card and the parody card on the finished spot's clock."""
    out = []; t = 0.0
    for b in s["beats"]:
        out.append((b["id"], b["start"], b["start"] + b["seconds"])); t = b["start"] + b["seconds"]
    out.append(("end card", s["end_card"]["start"], s["end_card"]["start"] + s["end_card"]["seconds"]))
    if s["parody_card"]: out.append(("parody card", s["parody_card"]["start"], s["parody_card"]["start"] + s["parody_card"]["seconds"]))
    return out


def strips(video, s, d):
    """One image per window: its first, middle and last frame side by side, 480 px each."""
    rows = []
    for n, (wid, a, z) in enumerate(windows(s), 1):
        fr = []
        for k, t in enumerate((a + 0.08, (a + z) / 2, z - 0.12)):
            f = d / f".f{n}_{k}.png"; ff("-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", "scale=480:-2", f); fr.append(f)
        out = d / f"shot{n}.webp"; ff(*sum((["-i", f] for f in fr), []), "-filter_complex", "[0][1][2]hstack=3", "-quality", "82", out)
        for f in fr: f.unlink()
        rows.append((wid, out.name))
    sheet = d / "sheet.webp"; ff(*sum((["-i", d / r[1]] for r in rows), []), "-filter_complex", "".join(f"[{i}]" for i in range(len(rows))) + f"vstack={len(rows)}", "-quality", "80", sheet)
    return rows


def main():
    p = argparse.ArgumentParser(); p.add_argument("run"); p.add_argument("--id", required=True); p.add_argument("--review"); p.add_argument("--measured")
    a = p.parse_args(); rd = Path(a.run); run = json.loads((rd / "run.json").read_text()); s = run["script"]; g = C.genre(s["genre"])
    if run.get("status") != "done": print(f"the run is {run.get('status')}, recording it as failed")
    d = WEB / a.id; d.mkdir(parents=True, exist_ok=True); src = rd / "commercial.mp4"; rows = []
    if src.is_file():
        ff("-i", src, "-c:v", "libx264", "-preset", "slow", "-crf", "25", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-map_metadata", "0", d / "commercial.mp4")
        mid = next(b for b in s["beats"] if b["ref"] == "cast" or b["ref"] == "product"); ff("-ss", f"{mid['start'] + mid['seconds'] / 2:.3f}", "-i", src, "-frames:v", "1", "-vf", "scale=1280:-2", "-quality", "82", d / "poster.webp")
        rows = strips(src, s, d)
    rv = json.loads(Path(a.review).read_text()) if a.review else {"status": "flawed", "verdict": "NOT YET REVIEWED by eye.", "flaws": ["Not reviewed yet."]}
    me = json.loads(Path(a.measured).read_text()) if a.measured else {}
    cut = next((x for x in run["steps"] if x["id"] == "cut"), {}); f = cut.get("facts") or {}; w = f.get("whisper") or {}; vo = next((x for x in run["steps"] if x["id"] == "vo"), {})
    notes = rv.get("shots") or {}
    entry = {"id": a.id, "genre": g["id"], "genre_title": g["title"], "title": s["values"].get("product") or s["title"], "length": s["length"], "tone": s["tone"], "status": rv["status"] if src.is_file() else "failed",
             "verdict": rv["verdict"], "flaws": rv.get("flaws") or [], "video": f"{a.id}/commercial.mp4" if src.is_file() else None, "poster": f"{a.id}/poster.webp" if src.is_file() else None, "sheet": f"{a.id}/sheet.webp" if rows else None,
             "shots": [{"id": wid, "frame": f"{a.id}/{img}", "status": (notes.get(wid) or {}).get("status", "ok"), "note": (notes.get(wid) or {}).get("note", "")} for wid, img in rows],
             "audio": {"lufs": (f.get("loudness") or {}).get("lufs"), "true_peak_db": (f.get("loudness") or {}).get("true_peak_db"), "lra": (f.get("loudness") or {}).get("lra"), "whisper_match": w.get("match_pct"), "heard": w.get("heard"), "vo_tempo": f.get("vo_tempo"), "stem_gains": f.get("stem_gains"), "listened_by_a_person": False},
             "seconds_of_work": run.get("seconds"), "my_peak_gib": round(me["my_peak_gib"], 1) if me.get("my_peak_gib") else None, "declared_gib": me.get("declared_gib"), "voice_model": (C.VO_ENGINES.get((vo.get("facts") or {}).get("engine") or "kokoro") or {}).get("label"), "voice": (vo.get("facts") or {}).get("voice"),
             "writer": s.get("writer"), "run": run["run"], "seeds": {x["id"]: x.get("seed") for x in run["steps"] if x.get("seed") is not None}, "rendered": time.strftime("%Y-%m-%d", time.localtime(run.get("finished") or time.time())), "brief": {k: v for k, v in s["values"].items()}}
    try: proof = json.loads(PROOF.read_text())
    except (OSError, ValueError): proof = {"note": "", "spots": []}
    proof["spots"] = [x for x in proof.get("spots", []) if x["id"] != a.id] + [entry]
    proof["note"] = "Each spot is one real run on this machine: its own ComfyUI lane, through the shared GPU gate. A person looked at the first, middle and last frame of every shot; nobody has listened to the audio, which ffmpeg and Whisper measured."
    PROOF.write_text(json.dumps(proof, indent=1, ensure_ascii=False) + "\n"); print(json.dumps({k: entry[k] for k in ("id", "status", "video")}), "shots:", len(rows))


if __name__ == "__main__": main()
