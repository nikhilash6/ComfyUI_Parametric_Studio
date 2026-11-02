"""The Voices page: routes, consent, licences, proof rules. Stubbed: no ComfyUI, no model, no live port."""
import json, re
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from studio import feature_voices as V, graph_registry as G, server as S

ROOT = Path(__file__).resolve().parents[1]; WEB = ROOT / "studio" / "web"
RUNNER = (ROOT / "studio" / "worldkit" / "runners" / "voice_speak.py").read_text(encoding="utf-8")


@pytest.fixture
def client(): return TestClient(S.app)


def _stub(monkeypatch, tmp_path):
    (tmp_path / "in").mkdir(); (tmp_path / "out").mkdir(); (tmp_path / "in" / "a.wav").write_bytes(b"x")
    monkeypatch.setattr(V.paths, "comfy_input", lambda *_: str(tmp_path / "in")); monkeypatch.setattr(V.paths, "output_dir", lambda *_: str(tmp_path / "out")); monkeypatch.setattr(V, "missing", lambda m, root=None: [])
    started = []
    monkeypatch.setattr(V.threading, "Thread", lambda target, args, **k: type("T", (), {"start": lambda self: started.append(args)})())
    return started


def test_every_model_says_its_licence_and_how_it_runs():
    for m in V.catalogue()["models"]:
        assert m["licence"]["name"] and "commercial" in m["licence"] or m["licence"].get("note"), m["id"]
        assert m["kind"] in ("speech", "design", "reference", "convert", "codec", "listen", "clean") and m["reference"] in ("none", "optional", "required") and m["job"] and m["maker"], m["id"]


def test_a_research_only_licence_never_reads_as_commercial():
    by = {m["id"]: m for m in V.catalogue()["models"]}
    for k in ("vibevoice_large", "vibevoice_15b"): assert by[k]["licence"].get("commercial") is None and "research" in by[k]["licence"]["note"]
    for k in ("f5tts", "phonon_40m"): assert by[k]["licence"]["commercial"] is False


def test_every_model_that_runs_has_an_engine_and_every_engine_is_catalogued():
    ids = {m["id"] for m in V.catalogue()["models"]}; eng = set(re.findall(r'"([a-z0-9_]+)"', " ".join(re.findall(r"@engine\(([^)]*)\)", RUNNER))))
    for m in V.catalogue()["models"]:
        if not m.get("blocked"): assert m["id"] in eng, m["id"]


def test_a_reference_is_refused_without_a_yes(client, monkeypatch, tmp_path):
    _stub(monkeypatch, tmp_path)
    for consent in (None, "", "yes", "true", "synthetic"):
        r = client.post("/api/voices/run", json={"model": "f5tts", "text": "hello there", "reference": "a.wav", "consent": consent})
        assert r.status_code == 400 and "permission" in r.json()["detail"], consent


def test_a_model_that_needs_a_clip_says_so(client, monkeypatch, tmp_path):
    _stub(monkeypatch, tmp_path)
    r = client.post("/api/voices/run", json={"model": "f5tts", "text": "hello there"}); assert r.status_code == 400 and "clip" in r.json()["detail"]


def test_a_yes_lets_it_through_and_reaches_the_runner(client, monkeypatch, tmp_path):
    started = _stub(monkeypatch, tmp_path)
    for yes in ("own", "permission"):
        r = client.post("/api/voices/run", json={"model": "f5tts", "text": "hello there", "reference": "a.wav", "reference_text": "the clip", "consent": yes}); assert r.status_code == 200, r.text
        cmd = started[-1][1]; assert cmd[cmd.index("--reference-consent") + 1] == yes and cmd[cmd.index("--reference") + 1].endswith("a.wav")


def test_a_clip_name_cant_leave_the_input_folder(client, monkeypatch, tmp_path):
    started = _stub(monkeypatch, tmp_path); r = client.post("/api/voices/run", json={"model": "f5tts", "text": "hello", "reference": "../../etc/passwd", "consent": "own"})
    assert r.status_code == 400 and not started


def test_a_model_without_references_refuses_one(client, monkeypatch, tmp_path):
    _stub(monkeypatch, tmp_path); r = client.post("/api/voices/run", json={"model": "kokoro", "text": "hello", "reference": "a.wav", "consent": "own"}); assert r.status_code == 400


def test_sfw_check_covers_the_line_the_voice_and_the_clip_words(client, monkeypatch, tmp_path):
    _stub(monkeypatch, tmp_path); seen = []
    from studio import sfw
    def boom(*t): seen.extend(t); raise HTTPException(400, "no")
    monkeypatch.setattr(sfw, "check", boom)
    r = client.post("/api/voices/run", json={"model": "voxcpm2", "text": "the line", "voice": "the voice", "reference_text": "the words"}); assert r.status_code == 400
    assert {"the line", "the voice", "the words"} <= set(seen)


def test_empty_text_and_blocked_models_are_refused(client, monkeypatch, tmp_path):
    _stub(monkeypatch, tmp_path)
    assert client.post("/api/voices/run", json={"model": "kokoro", "text": "  "}).status_code == 400
    assert client.post("/api/voices/run", json={"model": "nosuch", "text": "x"}).status_code == 404
    b = client.post("/api/voices/run", json={"model": "glm_tts", "text": "x"}); assert b.status_code == 409 and "shard" in b.json()["detail"]


def test_the_runner_itself_refuses_a_clip_without_a_consent_word():
    assert 'if a.reference and not a.reference_consent: raise SystemExit' in RUNNER


def test_rendered_needs_a_real_proof_and_the_page_says_nobody_listened(monkeypatch):
    monkeypatch.setattr(V, "proof", lambda: {"renders": {"kokoro": {"audio": "voices/kokoro.m4a"}}})
    by = {m["id"]: m for m in V.listing()}; assert by["kokoro"]["state"] == "rendered" and by["bark"]["state"] != "rendered"
    assert by["glm_tts"]["state"] == "blocked"; js = (WEB / "voices.js").read_text(encoding="utf-8"); assert "Nobody has listened" in js and V.PAGE["title"][2].endswith("No person has listened yet.")


def test_every_audio_file_on_the_page_is_there():
    p = V.proof()
    for r in [*(p.get("renders") or {}).values(), *(p.get("kokoro") or {}).values()]:
        if r.get("audio"): assert (WEB / r["audio"]).is_file(), r["audio"]


def test_samples_never_used_a_real_person():
    for mid, r in (V.proof().get("renders") or {}).items():
        m = V.model(mid)
        if m["reference"] == "required": assert "Kokoro" in r["voice_note"] and "No real person" in r["voice_note"] or m["kind"] == "convert", mid


def test_voices_are_listed_for_pro_api_and_apps(monkeypatch):
    rows = [r for r in G.all_rows() if r.get("section") == "voices"]; assert rows
    for r in rows:
        assert r["kind"] == "runner" and r["graph_url"] is None and r["call"]["path"] == "/api/voices/run" and r["licence"]["name"]
        if V.model(r["id"])["reference"] == "required": assert r["call"]["body"]["consent"] == "own"


def test_no_box_path_in_what_ships():
    for f in (ROOT / "studio" / "voice_models.json", ROOT / "studio" / "feature_voices.py", ROOT / "studio" / "worldkit" / "runners" / "voice_speak.py", ROOT / "scripts" / "build_voices_page.py", WEB / "voices.js"):
        t = f.read_text(encoding="utf-8"); assert "/mnt/" not in t and "/home/" not in t, f


def test_the_map_moves_only_what_a_passed_render_read():
    import importlib.util
    spec = importlib.util.spec_from_file_location("rvr", ROOT / "scripts" / "record_voice_renders.py"); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
    cat = {"models": [{"id": "a", "label": "A", "files": ["TTS/a/x.pt"]}, {"id": "b", "label": "B", "files": ["TTS/b/y.pt"]}, {"id": "c", "label": "C", "blocked": "needs z", "files": ["TTS/c/z.pt"]}]}
    good, low = R.proofs(cat, {"min_match": 60, "renders": {"a": {"secs": 3, "peak_gib": 1, "match_pct": 95}, "b": {"secs": 3, "peak_gib": 1, "match_pct": 20}}, "kokoro": {"af_x": {"lang": "en", "match_pct": 100}, "jf_y": {"lang": "ja", "match_pct": 10}}})
    rows = [{"disk_path": "/m/" + p, "status": "unreachable", "proof": "", "next_step": ""} for p in ("TTS/a/x.pt", "TTS/b/y.pt", "TTS/c/z.pt", "other/x.pt", "_by_repo/1038lab__KokoroTTS/voices/af_x.pt", "_by_repo/1038lab__KokoroTTS/voices/jf_y.pt")]
    assert R.apply(rows, good, low) == 2 and [r["status"] for r in rows] == ["rendered", "unreachable", "unreachable", "unreachable", "rendered", "unreachable"]
    assert "20%" in rows[1]["next_step"] and "needs z" in rows[2]["next_step"] and rows[3]["next_step"] == "" and "no person listened" in rows[0]["proof"]
