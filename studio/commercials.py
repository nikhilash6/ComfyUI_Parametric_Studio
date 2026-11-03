"""Commercials: a brief in, a finished TV-style spot out. A genre template (commercial_genres.json) and the brief make the script and shot list; the recipe engine renders it on the same queue as every recipe:
a cast frame and a product frame (FLUX.2 Klein 4B), one keyframe per shot drawn from them so people and products stay the same, each keyframe moved by MiniMax H3, a score from MiniMax Music 3, a voice-over from a local speech model, then one ffmpeg cut.
Every word on screen is drawn by ffmpeg from a font, never painted by an image model, so it can't come out as gibberish: supers, legal lines, the end card, the captions, the "AI-generated" label and, for parodies, the parody card.
The rules in commercial_safety.py run on the brief, the script and any rewrite. A language-model rewrite is optional and only used when the local model on :8002 is already up and awake; nothing here starts or stops it."""
import json, math, os, re, shutil, subprocess, sys, time, urllib.request
from functools import lru_cache
from pathlib import Path
from fastapi import HTTPException
from studio import recipes as R, commercial_safety as SAFE

HERE = Path(__file__).resolve().parent; GENRES_FILE = HERE / "commercial_genres.json"; VO_RUNNER = HERE / "worldkit" / "runners" / "vo_lines.py"; LISTEN_RUNNER = HERE / "worldkit" / "runners" / "caption_listen.py"
LENGTHS = (15, 30, 60); END_CARD = {15: 3.0, 30: 4.0, 60: 5.0}; PARODY_CARD = 2.5
H3_SECONDS = (2, 3, 4, 5, 6, 8); HEAD = 0.2; MIN_SHOT, MAX_SHOT = 1.8, 7.6; FULL = 7.75      # FULL: the most of an 8 s H3 clip a shot uses, after its head
NEXT_CAMERA = {"locked": "dolly_in", "dolly_in": "orbit_right", "dolly_out": "pan_left", "orbit_left": "dolly_in", "orbit_right": "dolly_in", "crane_up": "orbit_left", "crane_down": "dolly_in", "pan_left": "tracking", "pan_right": "tracking", "tilt_up": "dolly_in", "tracking": "dolly_in", "handheld": "dolly_in", "dolly_zoom": "dolly_in"}
W, H, FPS = 1280, 720, 24
WORDS_PER_SECOND = 2.5            # Kokoro at speed 1.0 reading ad copy, pauses included: 2.53 words a second measured on this box. The cut measures the real files and speeds the read up if it must
MAX_TEMPO = 1.45; LUFS = -16.0
LLM_URL = "http://127.0.0.1:8002"
KLEIN_EDIT = "image_flux2_klein_image_edit_4b_distilled"
NO_TEXT = "No text, no letters, no numbers, no logos, no signs with writing, no badges or emblems on any car or product."
#: Added to every keyframe: Klein tends to draw the cast twice, and to letter any sign, label or printed box it is allowed.
KEY_GUARDS = "Each person appears only once in the frame; nobody is duplicated. No printed text, labels, signs or lettering anywhere: plain surfaces."
FIELD_LABELS = {"brand": "Brand (invented)", "product": "Product (invented)", "what": "What the product looks like", "cast": "Who is in it", "tagline": "Tagline", "cta": "Call to action", "benefit": "The promise", "price": "Price", "condition": "Invented condition", "side_effects": "Invented side effects", "rare_effects": "Invented rare side effects", "candidate": "Invented candidate", "phone": "Fictional phone number", "customer": "The customer", "owner": "The owner"}
VO_ENGINES = {
    "kokoro": {"label": "Kokoro 82M", "licence": "Apache-2.0", "licence_class": "open", "peak_gib": 3, "note": "Fast and steady. Each genre picks one of its built-in voices."},
    "qwen3_design_17": {"label": "Qwen3-TTS 1.7B VoiceDesign", "licence": "Apache-2.0", "licence_class": "open", "peak_gib": 7, "note": "Speaks in a voice described in words, so each genre gets its own announcer. Slower."},
}
MODELS = [
    {"name": "FLUX.2 Klein 4B", "licence": "Apache-2.0", "licence_class": "open", "does": "Cast and product frames, and every keyframe drawn from them."},
    {"name": "MiniMax H3", "licence": "MiniMax H3 Community License", "licence_class": "community", "does": "Moves each keyframe, with its own sound.", "note": "Show the name in commercial products. Read the licence's territory terms before you rely on it."},
    {"name": "MiniMax Music 3", "licence": "MiniMax-Music3 Community License", "licence_class": "community", "does": "The score, instrumental.", "note": "Commercial use must show the name MiniMax-Music3."},
    {"name": "Kokoro 82M", "licence": "Apache-2.0", "licence_class": "open", "does": "The voice-over (default)."},
    {"name": "Qwen3-TTS 1.7B VoiceDesign", "licence": "Apache-2.0", "licence_class": "open", "does": "The voice-over in a described voice (optional)."},
    {"name": "faster-whisper distil-large-v3", "licence": "MIT", "licence_class": "open", "does": "Checks that the finished mix says the script's words."},
    {"name": "ffmpeg", "licence": "LGPL/GPL, runs as a separate tool", "licence_class": "open", "does": "The cut, the mix, and every word on screen."},
]
FONTS = {"sans": ("Lato:black", "DejaVu Sans:bold"), "serif": ("DejaVu Serif:bold", "Liberation Serif:bold"), "condensed": ("Liberation Sans Narrow:bold", "DejaVu Sans Condensed:bold"), "mono": ("DejaVu Sans Mono:bold",), "rounded": ("Ubuntu:bold", "DejaVu Sans:bold")}
ASS_FONT = "Lato"
PARODY_BADGE = {"pharma": "PARODY \u00b7 NOT A REAL PRODUCT", "political_parody": "PARODY \u00b7 FICTIONAL CANDIDATE"}
PARODY_LINES = {"pharma": ("Not a real medicine. Not a real company.", "No medical claims. Not medical advice."), "political_parody": ("Fictional candidate. Fictional party.", "Not a real campaign. Paid for by nobody.")}
PARODY_VO = {"pharma": "A parody. Not a real medicine.", "political_parody": "A parody. Not a real candidate."}


# ---------- the library
@lru_cache(maxsize=1)
def _lib(): return json.loads(GENRES_FILE.read_text(encoding="utf-8"))
def library(): return _lib()
def genres(): return _lib()["genres"]
def tones(): return _lib()["tones"]
def genre(gid):
    g = next((x for x in genres() if x["id"] == gid), None)
    if not g: raise HTTPException(404, "no such genre")
    return g
def placeholders(g):
    """Every {field} a genre's text uses."""
    blob = json.dumps({k: g[k] for k in ("beats", "end_card", "legal")})
    return sorted(set(re.findall(r"\{([a-z_]+)\}", blob)))
def fill(text, values): return re.sub(r"\s+", " ", R._fill(text or "", values)).strip()
def beats_for(g, length): return [b for b in g["beats"] if length in b["in"]]


def problems():
    """Everything a genre can get wrong, as sentences. A test keeps this empty."""
    from studio.goals import CAMERA_MOVES, SHOTS
    bad = []; ids = set()
    if len(genres()) < 20: bad.append(f"only {len(genres())} genres; the page promises at least 20")
    for g in genres():
        gid = g.get("id", "?")
        if gid in ids: bad.append(f"{gid}: duplicate id")
        ids.add(gid)
        for k in ("title", "group", "pitch", "lengths", "look", "vo", "music", "type", "fields", "beats", "end_card", "legal", "tone"):
            if not g.get(k): bad.append(f"{gid}: no {k}")
        if g.get("tone") not in tones(): bad.append(f"{gid}: unknown tone {g.get('tone')}")
        for k in placeholders(g):
            if k not in g.get("fields", {}): bad.append(f"{gid}: uses {{{k}}} but has no example for it")
        for L in g.get("lengths", []):
            bs = beats_for(g, L)
            if L not in LENGTHS: bad.append(f"{gid}: length {L} isn't one of {LENGTHS}")
            if len(bs) < 2: bad.append(f"{gid}: a {L} s cut keeps only {len(bs)} beats")
            if L == 60 and len(bs) < 5: bad.append(f"{gid}: a 60 s cut needs at least 5 beats")
        for b in g.get("beats", []):
            where = f"{gid}/{b.get('id')}"
            if b.get("camera") not in CAMERA_MOVES: bad.append(f"{where}: unknown camera {b.get('camera')}")
            if b.get("frame") not in SHOTS: bad.append(f"{where}: unknown framing {b.get('frame')}")
            if b.get("ref") not in ("cast", "product", "none"): bad.append(f"{where}: ref must be cast, product or none")
            if b.get("ref") == "product" and "what" not in g.get("fields", {}): bad.append(f"{where}: a product shot needs the genre's 'what' field")
            if b.get("ref") == "cast" and "cast" not in g.get("fields", {}): bad.append(f"{where}: a cast shot needs the genre's 'cast' field")
            if not b.get("shot") or not b.get("sfx"): bad.append(f"{where}: needs a shot and its sound")
        if g.get("parody") and g["id"] not in PARODY_BADGE: bad.append(f"{gid}: a parody genre needs its parody card text")
        if (g.get("vo") or {}).get("kokoro") and not re.fullmatch(r"[a-z]{2}_[a-z]+", g["vo"]["kokoro"]): bad.append(f"{gid}: bad Kokoro voice {g['vo']['kokoro']}")
        try:
            for L in g.get("lengths", []):
                s = build_script(gid, {"length": L}, check=False); bad += [f"{gid} ({L} s): {p}" for p in script_problems(s)]
                if not s["fits"]: bad.append(f"{gid} ({L} s): the example voice-over is too long: {s['vo_words']} words for {s['vo_room']:.0f} s")
        except HTTPException as e: bad.append(f"{gid}: {e.detail}")
    return bad


# ---------- brief -> script
def _clean(v, n=300): return re.sub(r"\s+", " ", str(v or "")).strip()[:n]
def brief_values(g, brief):
    """The genre's examples, with whatever the brief filled in on top. Only the genre's own fields are taken."""
    vals = dict(g["fields"])
    for k, v in (brief or {}).items():
        if k in vals and _clean(v): vals[k] = _clean(v, 400)
    return vals


def shot_seconds(beats, length, parody):
    """Each beat's time on screen: the picture's share of the spot split by weight, held between MIN_SHOT and two shots' worth, adding up exactly."""
    room = length - END_CARD[length] - (PARODY_CARD if parody else 0); w = [float(b.get("w", 4)) for b in beats]; d = [room * x / sum(w) for x in w]; top = FULL + MAX_SHOT
    for _ in range(6):
        fixed = [min(top, max(MIN_SHOT, x)) for x in d]; free = [i for i, x in enumerate(d) if MIN_SHOT < x < top]; over = room - sum(fixed)
        if abs(over) < 1e-6 or not free: d = fixed; break
        fw = sum(w[i] for i in free); d = [fixed[i] + (over * w[i] / fw if i in free else 0) for i in range(len(d))]
    frames = [int(round(x * FPS)) for x in d]; frames[-1] += int(round(room * FPS)) - sum(frames)
    return [f / FPS for f in frames]


def clip_seconds(d):
    """The shortest H3 length that covers a shot plus the frames trimmed from its head."""
    return next((s for s in H3_SECONDS if s >= d + HEAD + 0.05), H3_SECONDS[-1])


def parts_of(d, camera):
    """A beat longer than one H3 clip becomes a long take in two halves: the second starts on the exact frame where the first is cut, with the next camera move."""
    if d <= MAX_SHOT + 1e-6: return [{"seconds": round(d, 4), "clip_seconds": clip_seconds(d), "camera": camera}]
    a = round(min(FULL, d / 2) * FPS) / FPS; b = d - a
    return [{"seconds": round(a, 4), "clip_seconds": clip_seconds(a), "camera": camera}, {"seconds": round(b, 4), "clip_seconds": clip_seconds(b), "camera": NEXT_CAMERA.get(camera, "dolly_in")}]


def _words(t): return len(re.findall(r"[A-Za-z0-9']+", t or ""))


def build_script(gid, brief, check=True):
    """A genre and a brief -> the full script: beats with their times, shots, voice-over, supers and legal lines, the end card, and an estimate of whether the read fits."""
    g = genre(gid); brief = brief or {}
    try: L = int(brief.get("length") or (30 if 30 in g["lengths"] else g["lengths"][0]))
    except (TypeError, ValueError): raise HTTPException(400, "length must be 15, 30 or 60") from None
    if L not in g["lengths"]: raise HTTPException(400, f"{g['title']} comes in {', '.join(str(x) for x in g['lengths'])} second cuts")
    tone = brief.get("tone") or g["tone"]
    if tone not in tones(): raise HTTPException(400, "unknown tone")
    vals = brief_values(g, brief)
    if check: SAFE.check({k: v for k, v in vals.items() if brief.get(k)}, g, [k for k in SAFE.NAME_FIELDS if brief.get(k)])
    parody = bool(g.get("parody")); bs = beats_for(g, L); secs = shot_seconds(bs, L, parody); t = 0.0; beats = []
    for b, d in zip(bs, secs):
        beats.append({"id": b["id"], "start": round(t, 3), "seconds": round(d, 3), "parts": parts_of(d, b["camera"]), "ref": b["ref"], "frame": b["frame"], "camera": b["camera"], "shot": fill(b["shot"], vals), "sfx": fill(b["sfx"], vals),
                      "vo": fill(b.get("vo"), vals), "rate": float(b.get("rate", 1.0)), "super": fill(b.get("super"), vals), "legal": fill(b.get("legal"), vals)}); t += d
    end = {"start": round(t, 3), "seconds": END_CARD[L], "lines": [x for x in (fill(l, vals) for l in g["end_card"]["lines"]) if x], "vo": fill(g["end_card"].get("vo"), vals)}
    pc = {"start": round(t + END_CARD[L], 3), "seconds": PARODY_CARD, "title": "PARODY", "lines": list(PARODY_LINES.get(g["id"], ())), "vo": PARODY_VO.get(g["id"], ""), "badge": PARODY_BADGE.get(g["id"], "")} if parody else None
    tn = tones()[tone]; pace = tn["pace"]
    speech = sum(_words(b["vo"]) / (WORDS_PER_SECOND * b["rate"] * pace) + (0.25 if b["vo"] else 0) for b in beats); room = end["start"] - 0.3
    s = {"genre": g["id"], "title": g["title"], "length": L, "tone": tone, "values": vals, "parody": parody, "look": g["look"], "type": g["type"], "vo_style": g["vo"], "music": g["music"], "beats": beats, "end_card": end, "parody_card": pc,
         "legal": fill(g["legal"], vals), "vo_words": sum(_words(b["vo"]) for b in beats) + _words(end["vo"]), "vo_seconds": round(speech, 1), "vo_room": round(room, 1), "fits": speech <= room * MAX_TEMPO * 0.92, "writer": "template", "label": "AI-generated"}
    if check:
        bad = script_problems(s)
        if bad: raise HTTPException(400, " ".join(bad[:6]))
    return s


def script_text(s):
    """Every piece of text a script will show, say or send to a model, labelled."""
    out = {"legal": s["legal"], "end card": " / ".join(s["end_card"]["lines"]), "end card voice-over": s["end_card"]["vo"]}
    for b in s["beats"]:
        for k in ("vo", "super", "legal", "shot", "sfx"): out[f"{b['id']} {k}"] = b[k]
    for k in SAFE.NAME_FIELDS:
        if k in s["values"]: out[k] = s["values"][k]
    return out


def script_problems(s):
    return SAFE.problems(script_text(s), genre(s["genre"]), [k for k in SAFE.NAME_FIELDS if k in s["values"]])


# ---------- the optional rewrite: only if the local model is already up and awake
REWRITE_RULES = """You punch up the voice-over of a TV commercial script. Answer with JSON only: {"vo": ["line 1", "line 2", ...], "end": "end card line"}.
Rules: keep exactly the same number of lines, in the same order, each about the same length or shorter. An empty line stays empty. Keep the product and brand names exactly as written.
Every brand, product and person is invented: never add a real brand, company, celebrity, politician, party or medicine. Adults only. Nothing sexual. No alcohol or tobacco. No medical claims.
Tone: {tone}. Genre: {genre}.
The lines:
"""
def llm_ready(url=LLM_URL):
    """The model on :8002, if it answers right now and isn't asleep. A sleeping model is left asleep."""
    try:
        with urllib.request.urlopen(url + "/v1/models", timeout=3) as r: ids = [m["id"] for m in json.load(r).get("data") or []]
    except Exception: return None
    try:
        with urllib.request.urlopen(url + "/is_sleeping", timeout=3) as r:
            if json.load(r).get("is_sleeping"): return None
    except Exception: pass
    return {"url": url + "/v1", "model": ids[0]} if ids else None


def rewrite(s, chat=None, ready=None):
    """The script with a language model's voice-over, or the template's with a note saying why not. Any rewrite that breaks a rule, changes the shape or runs long is thrown away."""
    c = (ready or llm_ready)()
    if not c: return {**s, "writer": "template (the local model on :8002 isn't up, so nothing was rewritten)"}
    lines = [b["vo"] for b in s["beats"]]; prompt = REWRITE_RULES.replace("{tone}", tones()[s["tone"]]["label"]).replace("{genre}", s["title"]) + json.dumps({"vo": lines, "end": s["end_card"]["vo"]})
    try: raw = R._json_in((chat or R._chat)(c, prompt, 120))
    except Exception as e: return {**s, "writer": f"template (the rewrite failed: {type(e).__name__})"}
    new = (raw or {}).get("vo"); end = (raw or {}).get("end")
    if not isinstance(new, list) or len(new) != len(lines) or not isinstance(end, str): return {**s, "writer": "template (the rewrite changed the script's shape)"}
    s2 = json.loads(json.dumps(s))
    for b, old, v in zip(s2["beats"], lines, new):
        v = _clean(v, 400); b["vo"] = "" if not old else v
        if old and (not v or _words(v) > _words(old) * 1.25 + 2): return {**s, "writer": "template (the rewrite ran long)"}
    s2["end_card"]["vo"] = _clean(end, 200) or s["end_card"]["vo"]
    if script_problems(s2): return {**s, "writer": "template (the rewrite broke a rule, so it was thrown away)"}
    s2["writer"] = c["model"]; return s2


# ---------- script -> the recipe engine's steps
def _ref_word(s, b):
    return "character" if b["ref"] == "cast" else "product"
def key_prompt(s, b):
    from studio.goals import SHOTS
    v = s["values"]; tone = tones()[s["tone"]]["picture"]; frame = SHOTS.get(b["frame"], "")
    if b["ref"] == "cast": who = f"The same {_ref_word(s, b)} as in the reference picture, with the same face, hair, clothing and colours: {v['cast']}. Place them in the scene described, not in front of the reference's plain backdrop." + (f" Any product in the scene is {v['what']}, plain and unprinted." if v.get("what") else "")
    elif b["ref"] == "product": who = f"The same product as in the reference picture, same shape, colours and materials, completely blank: {v['what']}."
    else: who = ""
    return re.sub(r"\s+", " ", f"{frame} Film still from a TV commercial. {who} {b['shot']}. {s['look']}. {tone} Any people are adults, fully clothed. {NO_TEXT} {KEY_GUARDS}").strip()


def h3_prompt(s, b, camera=None, more=False):
    from studio.goals import CAMERA_MOVES
    tone = tones()[s["tone"]]["picture"]; go = "The moment carries on from the first frame. " if more else ""
    desc = re.sub(r"\s+", " ", f"{s['look']}. {go}{b['shot']}. {CAMERA_MOVES.get(camera or b['camera'], '')} {tone} Nobody speaks. No logos, badges or writing appear. One continuous shot, no cuts.").strip()
    return f"For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\nintegrated_multimodal_description: [Shot 1] {desc}\n\noverall_soundscape: {b['sfx']}. No speech, no music.\n\nnon_diegetic_music: N/A"


def music_caption(s):
    m = s["music"]; extra = tones()[s["tone"]]["music"]
    return (f"Global Metadata\nBasic Attributes: bpm is {m['bpm']}. {m['style']}.\nGlobal Emotional Progression: {m['mood']} {extra}\nApplication Scenarios & Imagery: The score of a {s['length']} second TV commercial, under a voice-over from start to finish.\nSonics & Production Profile: A clean, polished broadcast mix that sits under a voice, with a clear ending.\n"
            f"Vocal Details\nVocal Gender & Timbre: No vocals. Purely instrumental.\nVocal Style: No vocals.\nHarmony/Backing Vocals: None.\nVocal FX: None.\nArrangement\nInstrument Lifecycle Description (Primary/Secondary Layering):\nPrimary: {m['instruments']}.\nSecondary: Light textures that leave room for the voice.\nGroove & Foundation Progression: A clear, even {m['bpm']} BPM pulse.\nEmbellishments, Textures & Spatial FX: A lift into the final section and a clean button ending.")


def _klein_edit(sid, label, prompt, seed, ref):
    return {"id": sid, "type": "template", "template": KLEIN_EDIT, "label": label, "model": "FLUX.2 Klein 4B, with a reference picture", "peak_gib": 23, "seed": seed, "seed_node": "75:73", "seed_input": "noise_seed", "values": {"76|image": ref},
            "swap": {"flux-2-klein-4b-fp8.safetensors": "flux-2-klein-4b.safetensors"}, "set": {"75:74": {"text": prompt}, "75:66": {"width": 1344, "height": 768}, "75:62": {"width": 1344, "height": 768}}, "prompt_note": prompt[:200]}


def vo_lines(s):
    out = [{"id": b["id"], "text": b["vo"]} for b in s["beats"] if b["vo"]]
    if s["end_card"]["vo"]: out.append({"id": "end", "text": s["end_card"]["vo"]})
    if s["parody_card"] and s["parody_card"]["vo"]: out.append({"id": "parody", "text": s["parody_card"]["vo"]})
    return out


def specs(s, seed=7100, engine="kokoro"):
    """The steps, grouped by model so each model loads once: frames, keyframes, shots, score, voice, cut."""
    if engine not in VO_ENGINES: raise HTTPException(400, "unknown voice-over model")
    v = s["values"]; refs = {b["ref"] for b in s["beats"]}; steps = []
    if "cast" in refs: steps.append({"id": "cast", "type": "goal", "goal": "image", "label": "Cast frame", "model": "FLUX.2 Klein 4B", "peak_gib": 23, "seed": seed, "options": {"aspect": "2:3", "mode": "quality"},
                                     "prompt": f"Character reference photograph of {v['cast']}, facing the camera, the whole upper body in frame, plain light grey studio background, soft even light. Adults only, fully clothed. {NO_TEXT}"})
    if "product" in refs: steps.append({"id": "product", "type": "goal", "goal": "image", "label": "Product frame", "model": "FLUX.2 Klein 4B", "peak_gib": 23, "seed": seed + 1, "options": {"aspect": "1:1", "mode": "quality"},
                                        "prompt": f"Commercial product photograph of {v['what']}, centred on a plain pale grey seamless background, soft studio light, the whole object in frame. The product is completely blank: no print, no label text. {NO_TEXT}"})
    for i, b in enumerate(s["beats"], 1):
        p = key_prompt(s, b)
        if b["ref"] in ("cast", "product"): steps.append(_klein_edit(f"key{i}", f"Keyframe {i}: {b['id']}", p, seed + 10 + i, "@" + b["ref"]))
        else: steps.append({"id": f"key{i}", "type": "goal", "goal": "image", "label": f"Keyframe {i}: {b['id']}", "model": "FLUX.2 Klein 4B", "peak_gib": 23, "seed": seed + 10 + i, "options": {"aspect": "16:9", "mode": "quality"}, "prompt": p})
    for i, b in enumerate(s["beats"], 1):
        for j, pt in enumerate(b["parts"]):
            sid = f"shot{i}" + ("b" if j else ""); img = f"@key{i}"
            if j: steps.append({"id": f"cut{i}", "type": "commercial_frame", "label": f"Shot {i}: the frame where part one ends", "model": "ffmpeg", "peak_gib": 1, "clip": f"@shot{i}", "at": HEAD + b["parts"][0]["seconds"]}); img = f"@cut{i}"
            steps.append({"id": sid, "type": "goal", "goal": "h3_animate", "label": f"Shot {i}{', part two' if j else ''}: {b['id']}", "model": "MiniMax H3", "peak_gib": 47, "seed": seed + 30 + i + 50 * j, "image": img, "prompt": h3_prompt(s, b, pt["camera"], bool(j)),
                          "options": {"aspect": "16:9", "quality": "high", "seconds": pt["clip_seconds"], "speed": "fast"}})
    steps.append({"id": "score", "type": "goal", "goal": "music", "label": "Score", "model": "MiniMax Music 3", "peak_gib": 27, "seed": seed + 60, "options": {"seconds": 30 if s["length"] <= 30 else 60}, "prompt": music_caption(s), "lyrics": "[intro]\n\n[instrumental]\n\n[outro]"})
    e = VO_ENGINES[engine]; voice = s["vo_style"].get("kokoro") if engine == "kokoro" else s["vo_style"].get("design")
    steps.append({"id": "vo", "type": "commercial_vo", "label": "Voice-over", "model": e["label"], "peak_gib": e["peak_gib"], "seed": seed + 70, "engine": engine, "voice": voice, "lines": vo_lines(s)})
    steps.append({"id": "cut", "type": "commercial_cut", "label": "Cut, mix, captions and on-screen text", "model": "ffmpeg", "peak_gib": 1, "final": True, "shots": shot_refs(s), "audio": "@score", "vo": "@vo"})
    return steps


def shot_refs(s): return [f"@shot{i}" + ("b" if j else "") for i, b in enumerate(s["beats"], 1) for j in range(len(b["parts"]))]


def _run_frame(run, st, spec, ctx):
    """The frame of a clip at a time: where a long take's second part starts."""
    src = R._pick(ctx, spec["clip"], "video")["local"]; out = R._root() / run["run"] / f"{spec['id']}.png"
    R._ff(["-ss", f"{float(spec['at']):.3f}", "-i", str(src), "-frames:v", "1", "-update", "1", str(out)])
    if not out.is_file(): raise R.StepError("could not read that frame")
    return [{"filename": out.name, "subfolder": "", "type": "recipe", "kind": "image", "local": str(out), "url": f"/api/recipes/files/{run['run']}/{out.name}"}]


# ---------- the voice-over step: one process reads every line
def _models_root():
    from psn import paths
    return paths.models_root() or ""
def _run_vo(run, st, spec, ctx):
    d = R._root() / run["run"] / "vo"; d.mkdir(parents=True, exist_ok=True); (d / "lines.json").write_text(json.dumps(spec["lines"]))
    if not spec["lines"]: raise R.StepError("the script has no voice-over to read")
    py = os.environ.get("STUDIO_VOICE_PYTHON") or sys.executable; root = _models_root()
    cmd = [py, str(VO_RUNNER), "--model", spec["engine"], "--lines", str(d / "lines.json"), "--out", str(d), "--seed", str(int(spec.get("seed") or 7) + ctx["seed_add"])] + (["--voice", spec["voice"]] if spec.get("voice") else [])
    st["note"] = f"Reading {len(spec['lines'])} lines"; R._save(run)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env={**os.environ, "PSN_MODELS_ROOT": root, "STUDIO_MODELS_ROOT": root})
    t0 = time.time()
    while p.poll() is None:
        if run.get("_cancel"): p.kill(); raise R.Cancelled()
        if time.time() - t0 > 1200: p.kill(); raise R.StepError("the voice-over took over 20 minutes")
        time.sleep(1)
    out, err = p.communicate()
    if p.returncode: raise R.StepError("the voice-over failed: " + (err or out or "").strip()[-300:])
    man = json.loads((d / "manifest.json").read_text()); st["facts"] = {"lines": len(man["lines"]), "seconds": round(sum(x["seconds"] for x in man["lines"]), 2), "engine": spec["engine"], "voice": spec.get("voice")}
    files = [{"filename": "manifest.json", "subfolder": "", "type": "recipe", "kind": "file", "local": str(d / "manifest.json"), "url": ""}]
    for x in man["lines"]:
        dst = R._root() / run["run"] / f"vo_{x['id']}.wav"; shutil.copy2(x["file"], dst); x["file"] = str(dst)
        files.append({"filename": dst.name, "subfolder": "", "type": "recipe", "kind": "audio", "local": str(dst), "url": f"/api/recipes/files/{run['run']}/{dst.name}"})
    (d / "manifest.json").write_text(json.dumps(man)); return files


# ---------- the cut: pure functions over files, so tests run them for real
def fontfile(style):
    """A font file for a style, found by fontconfig. None lets ffmpeg use its default."""
    for name in FONTS.get(style, FONTS["sans"]):
        try:
            r = subprocess.run(["fc-match", "-f", "%{file}", name], capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout and os.path.isfile(r.stdout): return r.stdout
        except (OSError, subprocess.SubprocessError): pass
    return None


def place_vo(lines, s):
    """Where each read line starts, and how much faster it must go to fit. lines: [{id, seconds}] in script order. -> ({id: {start, seconds, tempo}}, body tempo)."""
    pace = tones()[s["tone"]]["pace"]; beats = {b["id"]: b for b in s["beats"]}; end = s["end_card"]; pc = s["parody_card"]
    body = [x for x in lines if x["id"] in beats]; limit = end["start"] - 0.15; factor = 1.0
    def lay(factor, anchored):
        out = {}; t = 0.0
        for x in body:
            b = beats[x["id"]]; tempo = (b["rate"] if b["rate"] != 1.0 else pace) * factor; dur = x["seconds"] / tempo
            start = max(b["start"] + 0.25, t + 0.15) if anchored else max(b["start"] - 1.5, t + 0.3, 0.25)
            out[x["id"]] = {"start": round(start, 3), "seconds": round(dur, 3), "tempo": round(tempo, 4)}; t = start + dur
        return out, t
    out, t = lay(1.0, True)
    if t > limit: out, t = lay(1.0, False)                    # first let a long line start a little early, then read faster
    for _ in range(8):
        over = t - limit
        if over <= 0 or factor >= MAX_TEMPO: break
        spoken = sum(v["seconds"] for v in out.values()); factor = min(MAX_TEMPO, factor * (spoken + over) / max(spoken, 0.1) + 0.01); out, t = lay(factor, False)
    if body and t > limit + 0.05: raise R.StepError(f"the voice-over runs {t - limit:.1f} s past the end card even read {MAX_TEMPO}x faster. Cut some words or pick a longer spot.")
    for x in lines:
        if x["id"] == "end":
            stop = (pc["start"] if pc else s["length"]) - 0.15; start = end["start"] + 0.3; tempo = max(pace, x["seconds"] / max(0.5, stop - start)); tempo = min(tempo, MAX_TEMPO)
            out["end"] = {"start": round(start, 3), "seconds": round(x["seconds"] / tempo, 3), "tempo": round(tempo, 4)}
        if x["id"] == "parody" and pc:
            start = pc["start"] + 0.15; tempo = min(MAX_TEMPO, max(1.0, x["seconds"] / max(0.5, s["length"] - 0.1 - start)))
            out["parody"] = {"start": round(start, 3), "seconds": round(x["seconds"] / tempo, 3), "tempo": round(tempo, 4)}
    return out, round(factor, 3)


def caption_cues(lines, placed, width=42):
    """Captions from the read lines, split into pieces of at most two lines, each piece timed by its share of the letters."""
    from studio import captions as C
    cues = []
    for x in lines:
        p = placed.get(x["id"])
        if not p or not x["text"].strip(): continue
        words = C.clean(x["text"]).split(); chunks, cur = [], []
        for w in words:
            if cur and len(" ".join(cur + [w])) > width * 2: chunks.append(" ".join(cur)); cur = []
            cur.append(w)
            if re.search(r"[.!?]$", w) and len(" ".join(cur)) > width * 0.9: chunks.append(" ".join(cur)); cur = []
        if cur: chunks.append(" ".join(cur))
        total = sum(len(c) for c in chunks) or 1; t = p["start"]
        for c in chunks:
            d = p["seconds"] * len(c) / total; cues.append({"start": round(t, 3), "end": round(t + d, 3), "lines": C.wrap(c, width)}); t += d
    return cues


def _wrap_px(text, size, max_w=W * 0.86):
    """Split a line so it fits across the frame at this size: most fonts' bold letters average about 0.56 of the size."""
    per = max(8, int(max_w / (0.56 * size))); words = text.split(); rows, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > per: rows.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    if cur: rows.append(cur)
    return rows


def overlay_items(s):
    """Every piece of text drawn on the picture, with its window: supers, legal lines, end card, parody card and the labels that stay on the whole time."""
    ty = s["type"]; items = []; L = s["length"]; ink, accent = ty["ink"], ty["accent"]; end = s["end_card"]
    super_y = {"upper": 0.13, "center": 0.42, "lower": 0.52}.get(ty.get("super"), 0.52)
    for b in s["beats"]:
        a, z = b["start"], b["start"] + b["seconds"]
        if b["super"]:
            rows = _wrap_px(b["super"], 64)
            for i, r in enumerate(rows): items.append({"text": r, "t0": a + 0.3, "t1": z - 0.1, "size": 64, "color": ink, "x": "center", "y": int(H * super_y) + i * 72, "font": ty["font"], "border": 3, "fade": 0.25, "kind": "super"})
        if b["legal"]:
            for i, r in enumerate(reversed(_wrap_px(b["legal"], 17, W * 0.9))): items.append({"text": r, "t0": a, "t1": z, "size": 17, "color": "#ffffff", "x": "center", "y": H - 30 - i * 21, "font": "sans", "border": 1, "box": True, "kind": "legal"})
    e0, e1 = end["start"], end["start"] + end["seconds"]; sizes = [76, 40, 30]; y = int(H * 0.30)
    for n, line in enumerate(end["lines"][:3]):
        size = sizes[n]; rows = _wrap_px(line, size)
        while len(rows) > 2 and size > 22: size -= 4; rows = _wrap_px(line, size)
        for r in rows: items.append({"text": r, "t0": e0 + 0.15 + n * 0.3, "t1": e1, "size": size, "color": ink if n != 2 else accent, "x": "center", "y": y, "font": ty["font"], "border": 0 if n else 2, "fade": 0.3, "kind": "end"}); y += int(size * 1.25)
        y += 14
    for i, r in enumerate(reversed(_wrap_px(s["legal"], 17, W * 0.9))): items.append({"text": r, "t0": e0, "t1": e1, "size": 17, "color": "#ffffff", "x": "center", "y": H - 30 - i * 21, "font": "sans", "border": 1, "box": True, "kind": "legal"})
    pc = s["parody_card"]
    if pc:
        p0, p1 = pc["start"], pc["start"] + pc["seconds"]; items.append({"text": pc["title"], "t0": p0, "t1": p1, "size": 120, "color": "#ffd23f", "x": "center", "y": int(H * 0.26), "font": "sans", "border": 0, "kind": "parody"})
        for i, r in enumerate(pc["lines"]): items.append({"text": r, "t0": p0, "t1": p1, "size": 34, "color": "#ffffff", "x": "center", "y": int(H * 0.26) + 160 + i * 48, "font": "sans", "border": 0, "kind": "parody"})
        items.append({"text": pc["badge"], "t0": 0, "t1": p0, "size": 18, "color": "#141006", "x": 18, "y": 18, "font": "sans", "border": 0, "box": "#ffd23f", "kind": "badge"})
    items.append({"text": "AI-GENERATED", "t0": 0, "t1": L, "size": 18, "color": "#ffffff", "x": "right", "y": 18, "font": "sans", "border": 0, "box": True, "kind": "ai_label"})
    return items


def _hex(c): return "0x" + c.lstrip("#")[:6]


def safe_font(path, style, workdir):
    """A font path the filter can't misread. Some font files are named like Ubuntu[wdth,wght].ttf, and brackets, commas, colons or quotes end a filter early; such a file is linked into the work folder under a plain name, as the text is."""
    if not path or re.fullmatch(r"[A-Za-z0-9_./+-]+", path): return path
    name = f"font_{re.sub(r'[^a-z0-9]', '', style or 'x')}{Path(path).suffix.lower() if re.fullmatch(r'[.][A-Za-z0-9]+', Path(path).suffix) else ''}"; dst = Path(workdir) / name
    if not dst.exists():
        try: dst.symlink_to(path)
        except OSError: shutil.copy2(path, dst)
    return name


def drawtext_chain(items, workdir, fonts=None):
    """The drawtext filters for the overlay items. Text goes through files, so nothing in it can break the filter."""
    fonts = fonts or {}; parts = []
    for n, it in enumerate(items):
        name = f"t{n:03d}.txt"; (Path(workdir) / name).write_text(it["text"], encoding="utf-8"); ff = safe_font(fonts.get(it["font"]) if it["font"] in fonts else fontfile(it["font"]), it["font"], workdir)
        x = "(w-text_w)/2" if it["x"] == "center" else "w-text_w-18" if it["x"] == "right" else str(it["x"]); a, z = it["t0"], it["t1"]
        f = (f"drawtext=textfile={name}:expansion=none" + (f":fontfile={ff}" if ff else "") + f":fontsize={it['size']}:fontcolor={_hex(it['color'])}:x={x}:y={it['y']}:enable='between(t,{a:.3f},{z:.3f})'")
        if it.get("fade"): f += f":alpha='min(1,max(0,(t-{a:.3f})/{it['fade']}))'"
        if it.get("border"): f += f":borderw={it['border']}:bordercolor=0x000000@0.7"
        if it.get("box"): f += f":box=1:boxborderw=6:boxcolor={_hex(it['box']) if isinstance(it['box'], str) else '0x000000'}@{'1.0' if isinstance(it['box'], str) else '0.55'}"
        parts.append(f)
    return ",".join(parts)


def caption_style(legal_rows=0, pt=15.0):
    """libass style for the burned-in captions: a thin outline and a little letter spacing, so words stay apart at TV size."""
    return f"FontName={ASS_FONT},Bold=1,Fontsize={pt},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=1,Outline=1.1,Shadow=0.7,Spacing=0.6,Alignment=2,MarginV={int(16 + 8.5 * legal_rows)},MarginL=24,MarginR=24,WrapStyle=0"


def frames_for(s):
    """Each shot's and card's length in frames, so the whole spot is exactly its length."""
    parts = [p["seconds"] for b in s["beats"] for p in b["parts"]] + [s["end_card"]["seconds"]] + ([s["parody_card"]["seconds"]] if s["parody_card"] else [])
    fr = [int(round(x * FPS)) for x in parts]; fr[-1] += s["length"] * FPS - sum(fr); return fr


def picture(s, shots, workdir):
    """Pass 1: the shots trimmed to their beats, the end card on a blurred last frame, the parody card. -> pic.mp4 (no text) and sfx.wav (the shots' own sound, in place)."""
    wd = Path(workdir); fr = frames_for(s); n = len(shots); bg = wd / "endbg.png"; R.frame(shots[-1], bg, "last"); infos = [R.probe(c) for c in shots]; args = []
    for c in shots: args += ["-i", str(c)]
    args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{fr[n] / FPS + 0.5:.3f}", "-i", str(bg)]
    if s["parody_card"]: args += ["-f", "lavfi", "-t", f"{fr[-1] / FPS + 0.5:.3f}", "-i", f"color=c=0x101010:s={W}x{H}:r={FPS}"]
    card = _hex(s["type"]["card"]); parts = []; alab = []
    for i in range(n):
        parts.append(f"[{i}:v]trim=start={HEAD},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=3,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},format=yuv420p,trim=end_frame={fr[i]},setpts=PTS-STARTPTS[v{i}]")
        d = fr[i] / FPS
        if infos[i]["audio"]: parts.append(f"[{i}:a]atrim=start={HEAD},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={d:.4f},atrim=0:{d:.4f}[a{i}]")
        else: parts.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{d:.4f}[a{i}]")
        alab.append(f"[a{i}]")
    parts.append(f"[{n}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=22:2,eq=brightness=-0.12:saturation=0.75,drawbox=x=0:y=0:w=iw:h=ih:color={card}@0.6:t=fill,setsar=1,fps={FPS},format=yuv420p,trim=end_frame={fr[n]},setpts=PTS-STARTPTS[ve]")
    tail = (fr[n] + (fr[-1] if s["parody_card"] else 0)) / FPS; vl = "".join(f"[v{i}]" for i in range(n)) + "[ve]"
    if s["parody_card"]: parts.append(f"[{n + 1}:v]format=yuv420p,setsar=1,trim=end_frame={fr[-1]},setpts=PTS-STARTPTS[vp]"); vl += "[vp]"
    parts.append(vl + f"concat=n={n + 1 + bool(s['parody_card'])}:v=1:a=0[vo]")
    parts.append("".join(alab) + f"concat=n={n}:v=0:a=1,apad=pad_dur={tail:.4f},atrim=0:{s['length']}[ao]")
    R._ff(args + ["-filter_complex", ";".join(parts), "-map", "[vo]", "-c:v", "libx264", "-preset", "medium", "-crf", "15", "-pix_fmt", "yuv420p", "-r", str(FPS), str(wd / "pic.mp4"), "-map", "[ao]", "-c:a", "pcm_s16le", "-ar", "48000", str(wd / "sfx.wav")])
    return wd / "pic.mp4", wd / "sfx.wav"


def mix(s, lines, placed, music, sfx, workdir):
    """Pass 2: the voice-over in place, the score under it and ducked by it, the shots' own sound low underneath. Each stem is measured and set to its level first, then the whole is normalised to LUFS. -> mix.wav and vo.wav."""
    wd = Path(workdir); L = s["length"]; args = []; parts = []; vl = []; k = 0; pad = f"asetpts=N/SR/TB,apad=whole_dur={L + 1},atrim=0:{L}"
    for x in lines:
        p = placed.get(x["id"])
        if not p: continue
        args += ["-i", x["file"]]; parts.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=mono,atempo={p['tempo']:.4f},adelay={int(p['start'] * 1000)}:all=1,{pad}[l{k}]"); vl.append(f"[l{k}]"); k += 1
    args += ["-i", str(music)]
    parts.append(("".join(vl) + f"amix=inputs={len(vl)}:normalize=0:duration=longest,aformat=channel_layouts=stereo,{pad}[vo]") if vl else f"anullsrc=r=48000:cl=stereo,atrim=0:{L}[vo]")
    parts.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{L},{pad},afade=t=out:st={max(0, L - 1.6):.3f}:d=1.5[mus]")
    R._ff(args + ["-filter_complex", ";".join(parts), "-map", "[vo]", "-c:a", "pcm_s16le", "-ar", "48000", str(wd / "vo.wav"), "-map", "[mus]", "-c:a", "pcm_s16le", "-ar", "48000", str(wd / "music.wav")])
    gain = lambda f, want: 0.0 if (loudness(f)["lufs"] is None or loudness(f)["lufs"] < -70) else max(-40.0, min(30.0, want - loudness(f)["lufs"]))
    gv, gm, gb = gain(wd / "vo.wav", -17.0), gain(wd / "music.wav", -23.0), gain(sfx, -31.0)
    fc = (f"[0:a]volume={gv:.2f}dB,asplit=2[v1][v2];[1:a]volume={gm:.2f}dB[m];[m][v2]sidechaincompress=threshold=0.03:ratio=2.5:attack=30:release=450:makeup=1[duck];[2:a]aresample=48000,aformat=channel_layouts=stereo,volume={gb:.2f}dB[b];"
          f"[v1][duck][b]amix=inputs=3:normalize=0:duration=first,loudnorm=I={LUFS}:TP=-1.5:LRA=11,aresample=48000,{pad}[ao]")
    R._ff(["-i", str(wd / "vo.wav"), "-i", str(wd / "music.wav"), "-i", str(sfx), "-filter_complex", fc, "-map", "[ao]", "-c:a", "pcm_s16le", str(wd / "mix.wav")])
    return wd / "mix.wav", wd / "vo.wav", {"voice_db": round(gv, 1), "music_db": round(gm, 1), "shot_sound_db": round(gb, 1), "targets_lufs": {"voice": -17, "music": -23, "shot_sound": -31, "mix": LUFS}}


def finish(s, pic, mixed, cues, workdir, out):
    """Pass 3: captions and every word on screen over the picture, with the mix. Runs inside the work folder so file names never pass through the filter's quoting."""
    from studio import captions as C
    wd = Path(workdir); (wd / "captions.srt").write_text(C.srt(cues), encoding="utf-8"); items = overlay_items(s)
    legal_rows = max([sum(1 for it in items if it["kind"] == "legal" and it["t0"] <= c["start"] < it["t1"]) for c in cues] or [0])
    vf = f"subtitles=filename=captions.srt:charenc=UTF-8:force_style='{caption_style(legal_rows)}'," + drawtext_chain(items, wd)
    meta = ["-metadata", f"title={s['values'].get('product') or s['title']} (AI-generated)", "-metadata", "comment=AI-generated. Fictional brand, product and people." + (" Parody." if s["parody"] else "") + " Made with Parametric Studio."]
    cmd = ["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error", "-i", str(pic), "-i", str(mixed), "-vf", vf, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest"] + meta + [str(Path(out).resolve())]
    r = subprocess.run(cmd, cwd=str(wd), capture_output=True, text=True, timeout=R.FF_TIMEOUT)
    if r.returncode: raise R.StepError("ffmpeg failed: " + (r.stderr or "").strip()[-300:])
    return {"items": len(items), "captions": len(cues)}


def loudness(path):
    """Integrated loudness and true peak of a file, by ffmpeg's EBU R128 meter."""
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, timeout=300)
    txt = r.stderr or ""; tail = txt[txt.rfind("Summary:"):] if "Summary:" in txt else txt
    i = re.search(r"I:\s*(-?[0-9.]+) LUFS", tail); p = re.search(r"Peak:\s*(-?[0-9.]+) dBFS", tail); lra = re.search(r"LRA:\s*(-?[0-9.]+) LU", tail)
    return {"lufs": float(i.group(1)) if i else None, "true_peak_db": float(p.group(1)) if p else None, "lra": float(lra.group(1)) if lra else None}


def listen(wav, workdir, script_words):
    """Whisper on the finished mix: how many of the script's words it heard. None when the listener can't run here."""
    wd = Path(workdir); w16 = wd / "mix16k.wav"
    try:
        R._ff(["-i", str(wav), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(w16)])
        r = subprocess.run([os.environ.get("STUDIO_VOICE_PYTHON") or sys.executable, str(LISTEN_RUNNER), "--audio", str(w16), "--out", str(wd / "heard.json"), "--model", "whisper_ct2_distil", "--language", "en"], capture_output=True, text=True, timeout=900, cwd=str(wd), env={**os.environ, "PSN_MODELS_ROOT": _models_root(), "STUDIO_MODELS_ROOT": _models_root()})
        if r.returncode: return {"error": (r.stderr or r.stdout).strip()[-200:]}
        heard = " ".join(x["text"] for x in json.loads((wd / "heard.json").read_text())["segments"])
    except Exception as e: return {"error": f"{type(e).__name__}: {e}"[:200]}
    return {"heard": heard, "match_pct": match_pct(script_words, heard)}


def match_pct(said, heard):
    """The share of the script's words Whisper heard, in order (a longest common subsequence of words)."""
    from studio import captions as C
    a, b = C.norm(said).split(), C.norm(heard).split()
    if not a: return None
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b): cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return round(100 * prev[-1] / len(a), 1)


def assemble(s, shots, manifest, music, workdir, out, hear=True):
    """The whole cut. -> facts about the finished file."""
    wd = Path(workdir); wd.mkdir(parents=True, exist_ok=True); lines = manifest["lines"]; t0 = time.time()
    placed, factor = place_vo(lines, s); pic, sfx = picture(s, shots, wd); mixed, vo, stems = mix(s, lines, placed, music, sfx, wd)
    script_lines = [{"id": x["id"], "text": x["text"]} for x in lines]; cues = caption_cues(script_lines, placed); made = finish(s, pic, mixed, cues, wd, out)
    p = R.probe(out); facts = {"seconds": round(p["duration"], 2), "width": p["width"], "height": p["height"], "vo_tempo": factor, "placed": placed, **made, "loudness": loudness(out), "stem_gains": stems, "label": "AI-generated", "cut_s": round(time.time() - t0, 1)}
    if hear: facts["whisper"] = listen(mixed, wd, " ".join(x["text"] for x in lines))
    facts["listened_by_a_person"] = False
    return facts


def _run_cut(run, st, spec, ctx):
    s = run["script"]; shots = [R._pick(ctx, r, "video")["local"] for r in spec["shots"]]; music = R._pick(ctx, spec["audio"], "audio")["local"]
    vo = next(f for f in ctx["out"][spec["vo"][1:]] if f["filename"] == "manifest.json"); man = json.loads(Path(vo["local"]).read_text())
    d = R._root() / run["run"]; out = d / "commercial.mp4"; st["note"] = "Cutting, mixing and listening"; R._save(run)
    facts = assemble(s, shots, man, music, d / "cut", out); st["facts"] = facts; shutil.copy2(d / "cut" / "captions.srt", d / "captions.srt")
    return [{"filename": out.name, "subfolder": "", "type": "recipe", "kind": "video", "local": str(out), "url": f"/api/recipes/files/{run['run']}/{out.name}"},
            {"filename": "captions.srt", "subfolder": "", "type": "recipe", "kind": "file", "local": str(d / "captions.srt"), "url": f"/api/recipes/files/{run['run']}/captions.srt"}]


R.EXTRA_STEPS.update(commercial_vo=_run_vo, commercial_cut=_run_cut, commercial_frame=_run_frame)


# ---------- a run on the recipe queue
def start(s, engine="kokoro", seed_add=0):
    import uuid
    bad = script_problems(s)
    if bad: raise HTTPException(400, " ".join(bad[:6]))
    steps = specs(s, 7100, engine); rid = uuid.uuid4().hex[:12]
    run = {"run": rid, "recipe": "commercial", "title": f"{s['title']}: {s['values'].get('product', '')}", "status": "queued", "created": time.time(), "values": {"genre": s["genre"], "length": s["length"], "tone": s["tone"], "engine": engine},
           "uploads": {}, "seed_add": int(seed_add), "steps": [R._step_state(x) for x in steps], "specs": steps, "script": s}
    with R._LOCK: R.RUNS[rid] = run
    R._save(run); R._ensure_worker(); R.QUEUE.put(rid); return {"run": rid, "position": R.position(run), "status": "queued"}
