#!/usr/bin/env python3
"""Writes studio/music_proof.json and studio/web/music/ from real renders. Nothing is invented: a model appears as rendered only if its file, its render log row and its measurements all exist.
Usage: build_music_page.py WORK_DIR, where WORK_DIR holds brief.py, renders/log.jsonl, renders/measure.json and the rendered files. Needs ffmpeg."""
import ast, importlib.util, json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; WEB = ROOT / "studio" / "web" / "music"; OUT = ROOT / "studio" / "music_proof.json"
KEEP = ("seconds", "lufs", "lra", "true_peak_db", "silent_pct", "last_second_db", "centroid_hz", "bands", "bpm", "key_guess", "peaks", "heard", "lyrics", "words_in_stem")
#: Takes on the "Change a song" part of the page: id in the render log, its label, how it was made, and whether it needs the pack.
CHANGE = [
    ("cover_ace", "ACE-Step cover", "ACE-Step 1.5 Turbo with his Cover guider, in a new style. It keeps the source's structure.", True),
    ("cover_yue2", "YuE2 cover", "ComfyUI's own YuE2 cover graph: SheetSage reads the melody, YuE2 re-sings it in a new style.", False),
    ("edit_ace", "ACE-Step repaint and extend", "His Edit guider redoes 30 to 40 s and adds 15 s at the end. The rest of the source should stay put.", True),
    ("stem_vocals", "Vocals, extracted", "ACE-Step 1.5 XL Base with his Extract guider, asked for the vocals only. The model generates the stem, so it's a new performance of that part rather than a clean separation.", True),
    ("stem_drums", "Drums, extracted", "The same guider, asked for the drums only. Generated, not separated.", True),
    ("stem_bass", "Bass, extracted", "The same guider, asked for the bass only. Generated, not separated.", True),
]


def encode(src, dst, rate="96k"):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "2", "-c:a", "aac", "-b:a", rate, "-movflags", "+faststart", str(dst)], check=True)


def load_brief(work):
    spec = importlib.util.spec_from_file_location("brief", work / "brief.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main(work):
    work = Path(work); WEB.mkdir(parents=True, exist_ok=True); B = load_brief(work)
    log = {}
    for line in (work / "renders" / "log.jsonl").read_text().splitlines():
        r = json.loads(line); log[r["id"]] = r       # the newest row for an id wins
    measure = json.loads((work / "renders" / "measure.json").read_text())
    date = time.strftime("%Y-%m-%d"); ids = [m["id"] for m in json.loads((ROOT / "studio" / "music_models.json").read_text())["models"]]; renders = {}
    def take(key, seed=B.SEED):
        r = log.get(key); m = measure.get(key)
        if not r or r.get("status") != "success" or not m or not r.get("outputs"): return None
        src = next((Path(o) for o in r["outputs"] if re.search(r"\.(flac|wav|mp3)$", o)), None)
        if not src or not src.exists(): return None
        dst = WEB / f"{key}.m4a"; encode(src, dst)
        d = {k: m[k] for k in KEEP if k in m}; d.update(status="success", audio=f"music/{key}.m4a", secs=r.get("secs"), peak_gib=r.get("peak_gib"), seed=seed, date=date, bytes=dst.stat().st_size); return d
    for i in ids:
        d = take(i)
        if not d: continue
        f = log.get("feat_" + i)
        if f and f.get("status") == "success" and f.get("text"):
            tr = [json.loads(ast.literal_eval(f["text"][k])[0]) for k in ("30", "31", "32")]      # PreviewAny's text: a list holding one JSON string
            norm = lambda a: [round(x / (max(a) or 1), 3) for x in a]
            (WEB / f"{i}.features.json").write_text(json.dumps({"fps": 15, "rms": norm(tr[0]), "onset": norm(tr[1]), "centroid": norm(tr[2])}, separators=(",", ":")))
            d["features"] = f"music/{i}.features.json"
        renders[i] = d
    change = []
    for key, label, how, pack in CHANGE:
        d = take(key); row = log.get(key)
        if d: change.append({"id": key, "label": label, "how": how, "pack": pack, **d})
        elif row: change.append({"id": key, "label": label, "how": how, "pack": pack, "problem": "This one failed when it was tried: " + _why(row)})
    vis = None; v = log.get("visual")
    if v and v.get("status") == "success" and v.get("outputs"):
        src = Path(v["outputs"][0]); dst = WEB / "reactive.mp4"; poster = WEB / "reactive.webp"
        # his frames are white on black; the tint to the studio's yellow is the only change made afterwards
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-vf", "colorchannelmixer=rr=0.96:rg=0:rb=0:gr=0:gg=0.77:gb=0:br=0:bg=0:bb=0.09", "-c:v", "libx264", "-crf", "30", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(dst)], check=True)
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", "12", "-i", str(dst), "-frames:v", "1", "-q:v", "70", str(poster)], check=True)
        vis = {"video": "music/reactive.mp4", "poster": "music/reactive.webp", "caption": "FlexAudioVisualizerCircular draws the frequencies around a ring. An energy track from AudioFeatureExtractor drives its radius and FlexImageBloom; an onset track drives FlexImageChromaticAberration. Tinted yellow afterwards. Audio: the Music 3 render.", "secs": v.get("secs")}
    OUT.write_text(json.dumps({"schema": 1, "note": "Written by scripts/build_music_page.py from real renders. Nobody has listened to any of this audio.", "measured_with": {"loudness": "ffmpeg ebur128", "spectrum and tempo": "librosa", "lyrics": "faster-whisper distil-large-v3, line match by difflib"}, "brief": {"title": B.TITLE, "seed": B.SEED, "seconds": B.SECONDS, "style": B.STYLE, "instrumental": B.INSTRUMENTAL, "caption": B.CAPTION, "lyrics": B.LYRICS, "bpm": B.BPM, "key": B.KEY}, "renders": renders, "extras": {"change": change, "visual": vis}}, indent=0, ensure_ascii=False))
    write_crew_notes(renders, change, vis, B)
    print("rendered:", ", ".join(renders), "| change:", len(change), "| visual:", bool(vis), "| web/music bytes:", sum(p.stat().st_size for p in WEB.iterdir()))


def write_crew_notes(renders, change, vis, B):
    """The music specialist's notes on the page, built from the same records so they can't drift from it. Every paragraph carries the proof label scripts/check_crew_notes.py wants."""
    cat = json.loads((ROOT / "studio" / "music_models.json").read_text(encoding="utf-8")); P = "[run: studio/music_proof.json]"; C = "[code: studio/music_models.json]"; by = {m["id"]: m for m in cat["models"]}
    out = [f"# Music page: state on {time.strftime('%Y-%m-%d')}", "", f"The Music page is in the studio's rail, and every music model has its own page at #music/ID. Where this file and older notes in this folder disagree, this file wins. Nobody has listened to any render on it: a program measured them and Whisper transcribed them, so don't describe how anything sounds. [code: studio/feature_music.py:1-3] {P}", ""]
    out += ["## The brief", "", f"Every render used one original brief, written for the page: the song \"{B.TITLE}\", seed {B.SEED}, a {B.SECONDS} s ceiling. Models with no lyric input got the instrumental line. {P}", "", "## What rendered", ""]
    for i, r in renders.items():
        ly = f"Whisper matched {r['lyrics']['lines_heard']} of {r['lyrics']['lines_total']} unique lyric lines." if r.get("lyrics") else "No lyrics to check."
        out += [f"{by[i]['label']}: {r['seconds']} s long, {r['lufs']} LUFS, true peak {r['true_peak_db']} dB, {r.get('bpm')} BPM found, rendered in {r['secs']} s at {r['peak_gib']} GiB peak on the test machine, one run, not a promise for others. {ly} Licence: {by[i]['licence']['name']}. {P}", ""]
    out += ["## Models with no render on the page", ""]
    for m in cat["models"]:
        if m["id"] not in renders: out += [f"{m['label']} has no render on the page. It is listed for: {m['job']} Licence: {m['licence']['name']}. {C}", ""]
    out += ["## Change a song", ""]
    for c in change:
        out += [f"{c['label']}: " + (f"made a real take, {c['seconds']} s, {c['lufs']} LUFS. " if c.get("audio") else c.get("problem", "") + " ") + c["how"] + f" {P}", ""]
    r = cat["roti"]
    out += ["## RyanOnTheInside", "", f"RyanOnTheInside wrote the audio-reactive idea and the ACE-Step guiders the page shows. His pack is ComfyUI_RyanOnTheInside, MIT, at {r['pack']} and it is not bundled. It ran on a separate ComfyUI; its nodes are called by name in workflows/music_roti_*.json, which need it installed, and /api/music/run answers 409 with how to install it when ComfyUI doesn't have it. [code: studio/feature_music.py] {C}", "", "Before installing his pack in a shared ComfyUI: " + " ".join(r["risks"]) + f" {C}", ""]
    if vis: out += [f"The reactive video is real output of his FlexAudioVisualizerCircular, FlexImageBloom and FlexImageChromaticAberration, tinted yellow afterwards. The ring beside it is the page's own drawing from numbers his AudioFeatureExtractor made, and is not a render. {P}", ""]
    out += ["## Choosing", "", "Sell the song: ACE-Step 1.5 is MIT; MiniMax Music 3 needs its name shown prominently; YuE2, MuLaCover, TangoFlux and MusicGen are non-commercial. For how they compare on this one brief, read the measurements above and say they come from one run. " + C, ""]
    d = ROOT / "studio" / "crew_notes" / "model_families" / "17-Music-song-models" / "dossier"; d.mkdir(parents=True, exist_ok=True); (d / "NOW.md").write_text("\n".join(out), encoding="utf-8")


def _why(row):
    m = re.search(r'"exception_message": "([^"]{0,200})', str(row.get("error") or ""))
    return m.group(1).strip() if m else str(row.get("status"))


if __name__ == "__main__": main(sys.argv[1])
