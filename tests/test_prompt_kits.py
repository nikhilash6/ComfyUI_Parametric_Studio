"""Per-model prompt kits and the enhancer that uses them: every Create goal with a kit gets its own notes, the writer's answer is used only when it passes, the formula takes over
when it doesn't, H3 always comes back in its three fields, and nothing private, adult or copied from a vendor's writer prompt is in the data. The language model is stubbed: no live port."""
import importlib.util, json, re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from studio import feature_prompt_kits as K, sfw
from studio.goals import GOALS

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "studio" / "prompt_kits.json").read_text(encoding="utf-8"))
app = FastAPI(); app.include_router(K.router); client = TestClient(app)


def stub(prompt=None, ok=True, problems=()):
    seen = {}
    def runner(role, task, ctx, **kw):
        seen.update(role=role, task=task, ctx=ctx, kw=kw)
        return SimpleNamespace(ok=ok, output={"prompt": prompt or "", "negative": ""}, problems=list(problems))
    return runner, seen


def test_every_kit_is_complete_and_points_at_real_goals():
    ids = [k["id"] for k in DATA["kits"]]; assert len(ids) == len(set(ids)) == 7
    for k in DATA["kits"]:
        assert k["notes"] and k["sources"] and k["kind"] in ("image", "video") and k["words"][0] < k["words"][1], k["id"]
        for g in k["goals"]: assert g in GOALS, (k["id"], g)
        for s in k["sources"]: assert s["url"].startswith("https://") and s["what"], k["id"]
    assert {g for k in DATA["kits"] for g in k["goals"]} >= {"image", "flux3", "product", "video", "animate", "video_ltx", "animate_ltx", "h3_video", "h3_animate", "director"}


def test_nothing_adult_private_or_copied():
    text = json.dumps(DATA, ensure_ascii=False)
    assert not sfw.flagged(text) and not re.search(r"lustify|pornmaster|babes|desire|/home/|/mnt/", text, re.I)
    for vendor in ("You are the prompt upsampler", "Output only the caption", "Work through the eight steps", "Image Prompt Rewriting Expert", "Attribute Disentanglement at Full Strength"):
        assert vendor.lower() not in text.lower(), vendor           # the vendors' writer prompts are summarised, never pasted
    assert len(DATA["sdxl_checkpoints"]["rows"]) == 13 and DATA["sdxl_checkpoints"]["fallback"]["cfg"] == 4.0


def test_the_writer_gets_the_goals_own_notes_and_its_answer_is_used():
    good = "Full-color outdoor photograph, a red fox sitting on a mossy stump at the edge of a pine forest in early morning light. " * 2
    runner, seen = stub(good)
    r = K.enhance("a red fox in a forest", goal="flux3", runner=runner)
    assert r["source"] == "model" and r["prompt"] == good and r["kit"] == "flux3_klein"
    assert seen["role"] == "prompt_enhancer" and "Target model family: FLUX.3 Klein" in seen["task"] and "Idea: a red fox in a forest" in seen["task"]
    assert seen["ctx"]["must_keep"] == ["red"] and seen["ctx"]["min_words"] == 80 and seen["ctx"]["video"] is False


def test_video_kits_ask_for_one_camera_move():
    runner, seen = stub("x")
    K.enhance("waves on a beach", goal="video_ltx", runner=runner)
    assert seen["ctx"]["video"] is True and "LTX-2.5" in seen["task"] and "no other camera movement" in seen["task"]


def test_a_failed_or_missing_writer_falls_back_and_says_why():
    runner, _ = stub(ok=False, problems=["prompt has 3 words (80-390)"])
    r = K.enhance("a lighthouse", goal="flux3", runner=runner)
    assert r["source"] == "fallback" and r["prompt"].startswith("Full-color photograph, a lighthouse") and "prompt has 3 words (80-390)" in r["problems"]
    def boom(*a, **k): raise ConnectionError("no model")
    r = K.enhance("a lighthouse", goal="image", runner=boom)
    assert r["source"] == "fallback" and any("did not answer" in p for p in r["problems"])
    assert K.enhance("a lighthouse", goal="image", runner=boom, seed=3)["prompt"] == K.enhance("a lighthouse", goal="image", runner=boom, seed=3)["prompt"]   # same seed, same formula


def test_h3_always_comes_back_in_its_three_fields():
    runner, _ = stub("Live-action, cinematic, a fisherman mends a net on a pier at dawn. The camera pushes in with small amplitude at slow speed. " * 3)
    for r in (K.enhance("a fisherman mending a net", goal="h3_video", runner=runner), K.enhance("a fisherman", goal="h3_video", runner=stub(ok=False)[0])):
        p = r["prompt"]; at = [p.index(f) for f in K.H3_FIELDS]
        assert at == sorted(at) and at[0] == 0 and p.count("non_diegetic_music:") == 1


def test_lint_catches_what_each_kit_warns_about():
    k = K.kit_for("video_ltx")
    probs = K.lint(k, "We see a man walk in. The camera pans left and then orbits around him. " * 3)
    assert any("avoid \"we see\"" in p for p in probs) and any("camera moves" in p for p in probs)
    assert any("words" in p for p in K.lint(K.kit_for("flux3"), "a cat"))


def test_routes_check_the_text_and_refuse_what_they_cannot_do():
    assert client.get("/api/prompt-kits").json()["kits"][0]["id"]
    assert client.get("/api/prompt-kits/for/flux3").json()["id"] == "flux3_klein"
    assert client.get("/api/prompt-kits/for/music").status_code == 404
    assert client.post("/api/prompt-kits/enhance", json={"goal": "flux3", "prompt": "nude"}).status_code == 400
    assert client.post("/api/prompt-kits/enhance", json={"goal": "flux3", "prompt": "  "}).status_code == 400
    assert client.post("/api/prompt-kits/enhance", json={"goal": "music", "prompt": "a song"}).status_code == 404
    assert client.post("/api/prompt-kits/lint", json={"goal": "h3_video", "prompt": "[Push in] a cat"}).json()["problems"]


def test_the_create_page_has_the_button_and_the_server_mounts_the_routes():
    app_js = (ROOT / "studio" / "web" / "app.js").read_text()
    assert 'import { ImprovePrompt } from "./prompt_kit.js";' in app_js and "<${ImprovePrompt} goal=${goal} prompt=${prompt} setPrompt=${setPrompt}/>" in app_js
    js = (ROOT / "studio" / "web" / "prompt_kit.js").read_text()
    assert "/api/prompt-kits/enhance" in js and "Undo" in js and "fixed formula" in js
    import studio.server as S
    assert TestClient(S.app).get("/api/prompt-kits/for/h3_video").status_code == 200


def test_the_family_guides_pass_the_checker():
    spec = importlib.util.spec_from_file_location("ccn", ROOT / "scripts" / "check_crew_notes.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    for folder in ("20-Qwen-Image-Qwen-Image-Edit", "10-Flux.2-Klein", "31-Z-Image-Lumina2"):
        g = ROOT / "studio" / "crew_notes" / "model_families" / folder / "dossier" / "GUIDE.md"
        assert m.check_file(ROOT, g) == [] and "studio/prompt_kits.json" in g.read_text(), folder
