"""Voice personas: 56 adult voice descriptions for the Voices page's design models, built from neutral trait phrases, never a person or a brand, and short enough to reach the model whole."""
import re
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from studio import feature_voice_personas as V, feature_voices as FV

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(); app.include_router(V.router); client = TestClient(app)
SUGGESTIVE = re.compile(r"\b(sultry|sensual|flirt\w*|seduct\w*|bedroom|intimate|sexy|teen\w*|girl|boy|child\w*|kid)\b", re.I)


def test_the_catalogue_is_sound_and_counted():
    assert V.problems() == []
    d = client.get("/api/voices/personas").json()
    assert d["counts"]["personas"] == 56 and d["counts"]["groups"] == 21 and len(d["personas"]) == 56
    assert all(g["options"][0]["key"] == "auto" for g in d["groups"])
    assert "dialect" not in {g["id"] for g in d["groups"]}            # cloning only, so not offered for design


def test_nothing_suggestive_or_young_anywhere():
    d = V.load()
    for c in d["categories"]:
        for o in c["options"]: assert not SUGGESTIVE.search(o["label"] + " " + o["phrase"]), (c["id"], o["key"])
    for p in V.personas(): assert not SUGGESTIVE.search(p["label"] + " " + p["blurb"] + " " + p["text"]), p["id"]
    ages = [o["key"] for o in d["_cats"]["age"]["options"] if o["key"] != "auto"]
    assert all(not re.match(r"^(1\d|20)_", k) for k in ages)          # 21 and over only


def test_every_persona_reads_as_an_adult_and_fits_whole():
    for p in V.personas():
        assert p["text"].startswith("An adult ") and p["text"].endswith(".") and len(p["text"]) <= V.LIMIT, p["id"]
        assert p["dropped"] == [] and p["warnings"] == [], p["id"]


def test_the_description_reaches_the_design_model_unchanged():
    m = {"id": "qwen3_design_17", "reference": "none", "voice_default": "x"}
    for p in V.personas():
        cmd = FV.command(m, {"text": "Hello there.", "voice": p["text"]}, "/tmp/x.wav")
        assert cmd[cmd.index("--voice") + 1] == p["text"], p["id"]


def test_compose_route_takes_a_persona_and_overrides():
    r = client.post("/api/voices/personas/compose", json={"persona": "news_anchor_f", "picks": {"accent_en": "scottish_glasgow"}}).json()
    assert r["text"].startswith("An adult woman in her early forties") and "Scottish" in r["text"]
    assert client.post("/api/voices/personas/compose", json={"persona": "nobody"}).status_code == 404
    assert client.post("/api/voices/personas/compose", json={"picks": {"pace": "warp_speed"}}).status_code == 400
    assert client.post("/api/voices/personas/compose", json={"picks": {"nonsense": "x"}}).status_code == 400


def test_auto_and_clone_only_traits_are_left_out():
    r = V.compose({"presentation": "man", "age": "auto", "dialect": "fujian", "pace": "auto"})
    assert r["text"] == "An adult man." and r["language"] == "English"


def test_over_the_limit_the_least_important_trait_goes_first():
    picks = V.load()["_personas"]["vlogger_warm"]["picks"]
    full = V.compose(picks)["text"]; r = V.compose(picks, limit=len(full) - 1)
    assert r["dropped"] == [V.load()["drop_order"][0]] and len(r["text"]) < len(full)
    assert r["text"].startswith("An adult woman in her mid twenties")      # the head is never dropped


def test_traits_that_pull_against_each_other_are_flagged():
    d = V.load(); tagged = {}
    for c in d["categories"]:
        if "design" not in c.get("use", []): continue
        for o in c["options"]:
            for t in o.get("tags") or []: tagged.setdefault(t, []).append((c["id"], o["key"]))
    (ca, ka), (cb, kb) = next((x, y) for a, b in d["conflicts"] for x in tagged.get(a, []) for y in tagged.get(b, []) if x[0] != y[0])
    assert V.compose({ca: ka, cb: kb})["warnings"]


def test_the_voices_page_offers_the_personas_for_design_models():
    js = (ROOT / "studio" / "web" / "voices.js").read_text()
    assert 'import { PersonaPick } from "./voice_personas.js";' in js and '<${PersonaPick} onPick=${(t) => up("voice", t)}/>' in js
    assert "/api/voices/personas" in (ROOT / "studio" / "web" / "voice_personas.js").read_text()
    import studio.server as S
    assert TestClient(S.app).get("/api/voices/personas").status_code == 200
