"""Commercials: the genre library checks out, the hard rules hold in code, every spot carries its labels, the optional rewrite never wakes or starts a model, and the real ffmpeg cut makes a spot of exactly the right length.
No model and no live port: ComfyUI's address is a dead one, the language model is stubbed, and the cut runs on clips ffmpeg makes here."""
import json, re, shutil, subprocess
from pathlib import Path
import pytest
from fastapi import HTTPException
from studio import commercials as C, commercial_safety as S, recipes as R

ROOT = Path(__file__).resolve().parent.parent
FF = shutil.which("ffmpeg")


@pytest.fixture(autouse=True)
def no_live_port(monkeypatch): monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:9")


# ---------- the library
def test_the_library_checks_out(): assert C.problems() == []


def test_the_genres_asked_for_are_all_there():
    want = {"pharma", "big_game", "car_launch", "perfume", "fast_food", "tech_reveal", "insurance_mascot", "infomercial", "charity_psa", "retro_80s", "sports_drink", "backyard_soda", "travel", "bank", "toy", "game_trailer", "political_parody", "real_estate", "fashion", "energy_drink"}
    have = {g["id"] for g in C.genres()}
    assert want <= have and len(have) >= 20


def test_every_cut_of_every_genre_is_exactly_its_length():
    for g in C.genres():
        for L in g["lengths"]:
            s = C.build_script(g["id"], {"length": L})
            assert sum(C.frames_for(s)) == L * C.FPS, (g["id"], L)
            for b in s["beats"]:
                assert C.MIN_SHOT - 1e-6 <= b["seconds"] and len(b["parts"]) in (1, 2), (g["id"], L, b)
                for p in b["parts"]: assert p["clip_seconds"] in C.H3_SECONDS and p["clip_seconds"] >= p["seconds"] + C.HEAD, (g["id"], L, p)


def test_specs_are_steps_the_recipe_engine_accepts():
    for gid, L in (("pharma", 30), ("big_game", 60), ("perfume", 15), ("political_parody", 30)):
        s = C.build_script(gid, {"length": L}); steps = C.specs(s)
        rec = {"id": f"t_{gid}", "title": "t", "pitch": "p", "why": "w", "tags": ["ad"], "fields": [], "models": [{"name": m["name"], "licence": m["licence"]} for m in C.MODELS], "steps": steps}
        assert R.validate({"recipes": [rec]}) == [], gid
        kinds = [x.get("goal") or x["type"] for x in steps]
        assert kinds.index("h3_animate") > max(i for i, k in enumerate(kinds) if k in ("image", "template")), "frames and keyframes come before every shot, so each model loads once"
        assert steps[-1]["type"] == "commercial_cut" and steps[-1]["final"]
        assert len(steps[-1]["shots"]) == sum(len(b["parts"]) for b in s["beats"])


def test_a_long_beat_becomes_a_long_take_from_the_exact_cut_frame():
    s = C.build_script("big_game", {"length": 60}); steps = {x["id"]: x for x in C.specs(s)}
    two = [i for i, b in enumerate(s["beats"], 1) if len(b["parts"]) == 2]; assert two
    i = two[0]; assert steps[f"shot{i}b"]["image"] == f"@cut{i}" and steps[f"cut{i}"]["at"] == pytest.approx(C.HEAD + s["beats"][i - 1]["parts"][0]["seconds"])


def test_the_image_models_are_never_asked_for_words_and_people_are_adults():
    for g in C.genres():
        s = C.build_script(g["id"], {"length": g["lengths"][0]})
        for x in C.specs(s):
            p = x.get("prompt") or (x.get("set") or {}).get("75:74", {}).get("text") or ""
            if x.get("goal") == "image" or x.get("type") == "template":
                assert C.NO_TEXT in p, (g["id"], x["id"])
                if x["id"] != "product": assert "adult" in p.lower(), (g["id"], x["id"])
            if x.get("goal") == "h3_animate": assert "Nobody speaks" in p and "No speech, no music" in p


def test_every_keyframe_asks_for_one_of_each_person_and_plain_surfaces():
    for g in C.genres():
        s = C.build_script(g["id"], {"length": g["lengths"][0]})
        for b in s["beats"]: assert C.key_prompt(s, b).endswith(C.KEY_GUARDS), (g["id"], b["id"])
        keys = [x for x in C.specs(s) if x["id"].startswith("key")]
        assert keys and all(C.KEY_GUARDS in (x.get("prompt") or x["set"]["75:74"]["text"]) for x in keys), g["id"]


# ---------- the hard rules
@pytest.mark.parametrize("field,text,word", [
    ("brand", "Nike", "real brand"), ("product", "Coca-Cola Zero", "real"), ("product", "Koka-Kola", "real"), ("product", "Addidas Runner", "too close"), ("brand", "Nykee", "real brand"),
    ("cast", "a man who looks like Tom Hanks", "real person"), ("cast", "Taylor Swift in a red coat", "real person"), ("tagline", "As endorsed by Barack Obama", "real politician"),
    ("cta", "Vote Republican", "real political party"), ("tagline", "Better than McDonald's", "real brand"), ("brand", "Acme™", "trademark"),
])
def test_real_names_are_refused(field, text, word):
    bad = S.problems({field: text}, None, [field] if field in S.NAME_FIELDS else [])
    assert any(word in b for b in bad), bad


def test_everyday_words_that_are_also_brands_are_not_refused_in_running_text():
    assert S.problems({"shot": "an apple orchard at dawn, a soft chime, a seat at the table, a trump card, the target of the joke, ginger ale"}) == []
    assert S.problems({"product": "Dove Soap"}, None, ["product"])                       # in a name, an everyday brand word is still refused


@pytest.mark.parametrize("text,word", [("two kids laughing", "adults only"), ("a toddler with a balloon", "adults only"), ("a seductive model in lingerie", "sexual"), ("friends sharing a cold beer", "alcohol"),
                                       ("a cowboy smoking a cigarette", "tobacco"), ("a woman in a bikini", "sexual")])
def test_children_sex_alcohol_and_tobacco_are_refused(text, word):
    assert any(word in b for b in S.problems({"cast": text})), S.problems({"cast": text})


def test_the_soda_genre_may_say_it_has_no_alcohol(): assert S.problems({"legal": "A soft drink. Non-alcoholic.", "x": "root beer float, alcohol-free"}) == []


def test_pharma_parodies_name_no_real_drug_condition_or_claim():
    g = C.genre("pharma")
    for brief, word in (({"product": "Lipitor"}, "real medicine"), ({"product": "Ozempik"}, "real"), ({"condition": "type 2 diabetes"}, "real medical condition"), ({"benefit": "cure your arthritis"}, "medical")):
        with pytest.raises(HTTPException) as e: C.build_script("pharma", brief)
        assert word in e.value.detail, e.value.detail
    s = C.build_script("pharma", {"product": "Sockozen", "condition": "Restless Remote Syndrome"})
    assert s["parody"] and s["parody_card"]["title"] == "PARODY" and "not a real medicine" in s["legal"].lower()
    assert S.problems({"x": "clinically proven"}, g) and not S.problems({"x": "clinically proven"})


def test_the_political_parody_is_always_fictional():
    s = C.build_script("political_parody", {"candidate": "Dot Fernsby"}); assert s["parody_card"] and "Fictional candidate" in " ".join(s["parody_card"]["lines"])
    for bad in ({"candidate": "Kamala Harris"}, {"brand": "The Labour Party"}, {"tagline": "Make it great like Trump"}):
        with pytest.raises(HTTPException): C.build_script("political_parody", bad)


def test_every_template_passes_its_own_rules():
    for g in C.genres():
        for L in g["lengths"]: assert C.script_problems(C.build_script(g["id"], {"length": L}, check=False)) == [], (g["id"], L)


# ---------- labels on every spot
def test_every_spot_of_every_genre_carries_the_ai_label_for_its_whole_length():
    for g in C.genres():
        for L in g["lengths"]:
            s = C.build_script(g["id"], {"length": L}); items = C.overlay_items(s)
            lab = [x for x in items if x["kind"] == "ai_label"]
            assert len(lab) == 1 and lab[0]["text"] == "AI-GENERATED" and lab[0]["t0"] == 0 and lab[0]["t1"] == L, (g["id"], L)
            assert any(x["kind"] == "legal" and x["t1"] == s["end_card"]["start"] + s["end_card"]["seconds"] for x in items), "the legal line is on the end card"
            if g.get("parody"):
                assert any(x["kind"] == "parody" and x["text"] == "PARODY" for x in items) and any(x["kind"] == "badge" for x in items), g["id"]


def test_drawtext_reads_text_from_files_so_nothing_can_break_the_filter(tmp_path):
    items = [{"text": "50% off: it's 'great', isn't it? \\ {x}", "t0": 0, "t1": 1, "size": 20, "color": "#ffffff", "x": "center", "y": 10, "font": "sans", "border": 0, "kind": "super"}]
    f = C.drawtext_chain(items, tmp_path, fonts={"sans": None})
    assert "textfile=t000.txt" in f and "expansion=none" in f and "great" not in f and (tmp_path / "t000.txt").read_text() == items[0]["text"]


# ---------- the optional rewrite
def test_a_font_file_named_with_brackets_cannot_break_the_filter(tmp_path):
    font = tmp_path / "fonts" / "Ubuntu[wdth,wght].ttf"; font.parent.mkdir(); font.write_bytes(b"not really a font")
    items = [{"text": "50% off", "t0": 0, "t1": 1, "size": 20, "color": "#ffffff", "x": "center", "y": 10, "font": "rounded", "border": 0, "kind": "super"}]
    f = C.drawtext_chain(items, tmp_path, fonts={"rounded": str(font)})
    assert "fontfile=font_rounded.ttf:" in f and "[" not in f and "wdth,wght" not in f and (tmp_path / "font_rounded.ttf").read_bytes() == b"not really a font"
    assert C.safe_font("/usr/share/fonts/truetype/lato/Lato-Black.ttf", "sans", tmp_path) == "/usr/share/fonts/truetype/lato/Lato-Black.ttf" and C.safe_font(None, "sans", tmp_path) is None


def test_the_rewrite_only_runs_when_the_model_is_already_up():
    s = C.build_script("fast_food", {})
    assert C.rewrite(s, ready=lambda: None)["writer"].startswith("template")
    good = lambda c, p, t: json.dumps({"vo": ["Sizzling hot.", "Three patties, all melt.", "The Triple Stack Melt.", "Only $4.99 for now."], "end": "Bun Voyage. Built bigger."})
    r = C.rewrite(s, chat=good, ready=lambda: {"url": "x", "model": "stub"}); assert r["writer"] == "stub" and r["beats"][0]["vo"] == "Sizzling hot."
    sneaky = lambda c, p, t: json.dumps({"vo": ["Hotter than a Big Mac.", "x", "y", "z"], "end": "e"})
    assert C.rewrite(s, chat=sneaky, ready=lambda: {"url": "x", "model": "stub"})["writer"].startswith("template (the rewrite broke a rule")
    short = lambda c, p, t: json.dumps({"vo": ["one"], "end": "e"})
    assert "shape" in C.rewrite(s, chat=short, ready=lambda: {"url": "x", "model": "stub"})["writer"]


def test_checking_for_the_model_only_asks_and_never_wakes_or_starts_it(monkeypatch):
    seen = []
    class Resp:
        def __init__(self, body): self.b = body
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(self.b).encode()
    def fake(req, timeout=0):
        url = req if isinstance(req, str) else req.full_url; seen.append((url, getattr(req, "method", "GET") if not isinstance(req, str) else "GET"))
        return Resp({"data": [{"id": "qwen"}]} if url.endswith("/v1/models") else {"is_sleeping": True})
    monkeypatch.setattr(C.urllib.request, "urlopen", fake)
    assert C.llm_ready() is None                                       # asleep: left asleep
    assert seen and all(u.startswith("http://127.0.0.1:8002/") and m == "GET" for u, m in seen) and not any("wake" in u for u, _ in seen)


# ---------- the voice-over fits, or says why not
def test_the_read_is_placed_in_order_inside_the_picture_and_sped_up_only_when_it_must():
    s = C.build_script("infomercial", {"length": 30}); lines = [{"id": x["id"], "seconds": 2.0} for x in C.vo_lines(s)]
    placed, f = C.place_vo(lines, s); body = [placed[b["id"]] for b in s["beats"] if b["vo"]]
    assert f == 1.0 and all(a["start"] + a["seconds"] <= b["start"] for a, b in zip(body, body[1:])) and body[-1]["start"] + body[-1]["seconds"] <= s["end_card"]["start"]
    long = [{"id": x["id"], "seconds": 5.5} for x in C.vo_lines(s)]; placed, f = C.place_vo(long, s); assert 1.0 < f <= C.MAX_TEMPO
    with pytest.raises(R.StepError): C.place_vo([{"id": x["id"], "seconds": 30.0} for x in C.vo_lines(s)], s)


def test_captions_follow_the_read():
    s = C.build_script("pharma", {}); lines = [{"id": x["id"], "text": x["text"], "seconds": 3.0} for x in C.vo_lines(s)]
    placed, _ = C.place_vo(lines, s); cues = C.caption_cues(lines, placed)
    assert cues and all(len(l) <= 42 for c in cues for l in c["lines"]) and all(len(c["lines"]) <= 2 for c in cues)
    assert all(a["end"] <= b["start"] + 1e-6 for a, b in zip(cues, cues[1:]))


# ---------- the real cut, on clips made here
def _clip(path, seconds, freq):
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc2=s=640x368:r=24:d={seconds}", "-f", "lavfi", "-i", f"sine=f={freq}:d={seconds}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)


@pytest.mark.skipif(not FF, reason="no ffmpeg")
def test_the_cut_makes_a_labelled_spot_of_exactly_its_length(tmp_path):
    s = C.build_script("pharma", {"length": 30}); shots = []
    for i, b in enumerate(s["beats"]):
        for j, p in enumerate(b["parts"]): f = tmp_path / f"s{i}{j}.mp4"; _clip(f, p["clip_seconds"], 200 + 50 * i); shots.append(f)
    lines = []
    for x in C.vo_lines(s):
        f = tmp_path / f"{x['id']}.wav"; d = round(len(x["text"].split()) / 2.6, 2)
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f=440:d={d}", "-ar", "24000", str(f)], check=True); lines.append({**x, "file": str(f), "seconds": d})
    music = tmp_path / "m.wav"; subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=110:d=30", str(music)], check=True)
    out = tmp_path / "spot.mp4"; facts = C.assemble(s, shots, {"lines": lines}, music, tmp_path / "cut", out, hear=False)
    assert facts["seconds"] == pytest.approx(30.0, abs=0.05) and facts["width"] == 1280 and facts["listened_by_a_person"] is False
    assert facts["loudness"]["lufs"] == pytest.approx(C.LUFS, abs=1.5) and facts["loudness"]["true_peak_db"] <= -1.0
    meta = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags=comment", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout
    assert "AI-generated" in meta and "Parody" in meta
    if shutil.which("tesseract"):
        frame = tmp_path / "f.png"; subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-ss", "28.6", "-i", str(out), "-frames:v", "1", str(frame)], check=True)
        txt = subprocess.run(["tesseract", str(frame), "-", "--psm", "6"], capture_output=True, text=True).stdout.upper()
        assert "PARODY" in txt and "AI-GENERATED" in txt.replace(" ", ""), txt


# ---------- the page's routes
def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from studio import feature_commercials as F
    app = FastAPI(); app.include_router(F.router); return TestClient(app), F


def test_the_page_lists_the_library_and_refuses_a_real_name():
    c, F = _client(); d = c.get("/api/commercials/genres").json()
    assert len(d["genres"]) >= 20 and d["rules"] and all(m["licence"] for m in d["models"]) and set(d["vo_engines"]) == set(C.VO_ENGINES)
    r = c.post("/api/commercials/script", json={"genre": "car_launch", "brief": {"brand": "Porsche"}}); assert r.status_code == 400 and "Porsche" in r.json()["detail"]
    r = c.post("/api/commercials/script", json={"genre": "toy", "length": 15, "brief": {"product": "Gizmo the Clockwork Owl"}}); assert r.status_code == 200 and r.json()["script"]["length"] == 15


def test_a_run_rebuilds_the_script_and_checks_edited_lines(monkeypatch):
    c, F = _client(); got = {}
    monkeypatch.setattr(C, "start", lambda s, engine="kokoro", seed_add=0: got.update(s=s, engine=engine) or {"run": "x", "status": "queued", "position": 1})
    s = C.build_script("perfume", {}); vo = [b["vo"] for b in s["beats"]]
    assert c.post("/api/commercials/run", json={"genre": "perfume", "vo": vo, "end_vo": "Wear the night."}).status_code == 200 and got["s"]["genre"] == "perfume"
    vo[1] = "Worn by Beyonce."; r = c.post("/api/commercials/run", json={"genre": "perfume", "vo": vo}); assert r.status_code == 400 and "Beyonce" in r.json()["detail"]
    assert c.post("/api/commercials/run", json={"genre": "perfume", "vo": ["only one"]}).status_code == 400


def test_the_proof_on_the_page_is_consistent():
    from studio import feature_commercials as F
    assert F.problems() == []
    for sp in F._proof().get("spots", []):
        assert sp["audio"]["listened_by_a_person"] is False and sp["status"] in ("passed", "flawed", "failed")
        if sp["status"] != "passed": assert sp.get("flaws"), sp["id"]
        assert not re.search(r"/(mnt|home|tmp)/", json.dumps(sp)), "no local path reaches the page"
