"""Pipelines: every file checks out, a run is recorded the way the page reads it, and nothing of this machine reaches the page. No model and no live port: ComfyUI's address is a dead one."""
import json, shutil, subprocess
from pathlib import Path
import pytest
from studio import pipelines as P, recipes as R

ROOT = Path(__file__).resolve().parent.parent
@pytest.fixture(autouse=True)
def no_live_port(monkeypatch): monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:9")

def test_every_pipeline_checks_out(): assert P.problems() == []
def test_at_least_two_families_each():
    for r in P.rows(): assert len({m["name"] for m in r["models"]} - {"ffmpeg"}) >= 2, r["id"]
def test_every_model_has_a_known_licence_class():
    for r in P.rows():
        for m in r["models"]: assert m["licence_class"] in ("open", "community", "noncommercial") and m["licence"], (r["id"], m["name"])
def test_a_stage_with_no_licence_is_refused(tmp_path, monkeypatch):
    bad = {"id": "bad_one", "order": 1, "kicker": "x", "title": "t", "pitch": "p", "why": "w", "tags": ["x"], "models": [{"name": "A", "licence": "MIT", "licence_class": "open"}], "steps": [{"id": "s", "type": "goal", "goal": "image", "model": "B", "peak_gib": 1, "prompt": "x"}]}
    (tmp_path / "bad_one.json").write_text(json.dumps(bad)); monkeypatch.setattr(P, "DIR", tmp_path); monkeypatch.setitem(P._CACHE, "sig", None); monkeypatch.setitem(P._CACHE, "rows", [])
    assert any("licence" in x for x in P.problems())
def test_find_reaches_pipelines_and_the_engine_knows_the_steps():
    assert R.find(P.rows()[0]["id"]) and {"worldkit", "vset", "worldkit_pack", "worldkit_sheet"} <= set(R.EXTRA_STEPS)
def test_a_recorded_run_has_what_the_page_needs_and_no_local_path(tmp_path):
    if not shutil.which("ffmpeg"): pytest.skip("no ffmpeg")
    import importlib.util as U
    spec = U.spec_from_file_location("record_pipeline", ROOT / "scripts" / "record_pipeline.py"); mod = U.module_from_spec(spec); spec.loader.exec_module(mod); record = mod.record
    data = tmp_path / "data"; data.mkdir(); web = tmp_path / "web"; run = tmp_path / "run"; run.mkdir()
    (data / "p.json").write_text(json.dumps({"id": "p", "models": [{"name": "M", "licence": "MIT", "licence_class": "open"}], "steps": [{"id": "a", "type": "goal", "model": "M", "does": "d", "prompt": "hello {x}"}]}))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=64x64:d=1", str(run / "a.mp4")], check=True)
    (run / "a.graph.json").write_text(json.dumps({"1": {"inputs": {"p": "/" + "mnt/secret/place/file.png"}}}))
    (run / "run.json").write_text(json.dumps({"run": "r1", "recipe": "p", "values": {"x": "w"}, "seconds": 3, "peak_vram_gib": 1.5, "finished": 1, "steps": [{"id": "a", "label": "A", "type": "goal", "status": "done", "seed": 7, "seconds": 3, "peak_gib": 1.5, "final": True, "files": [{"filename": "a.mp4", "kind": "video"}], "error": "/" + "home/someone/x"}]}))
    pr = record(run, "p", {"status": "passed", "verdict": "fine"}, web=web, data=data); s = pr["stages"][0]
    assert s["seed"] == 7 and s["licence"] == "MIT" and s["prompt"] == "hello w" and s["media"][0]["kind"] == "video" and (web / "p" / s["media"][0]["src"]).is_file() and pr["final"]
    blob = (web / "p" / "proof.json").read_text() + (web / "p" / "graphs" / "a.json").read_text()
    assert "/" + "mnt/" not in blob and "/" + "home/" not in blob
def test_essay_marks_every_prediction():
    d = json.loads((ROOT / "studio" / "web" / "future_essay.json").read_text(encoding="utf-8")); ids = {s["id"] for s in d["sources"]}
    going = next(s for s in d["sections"] if s["id"] == "going")
    assert all(b["kind"] == "opinion" for b in going["blocks"])
    for s in d["sections"]:
        for b in s["blocks"]: assert set(b.get("cite") or []) <= ids

def _numbers():
    import importlib.util as U
    spec = U.spec_from_file_location("build_future_numbers", ROOT / "scripts" / "build_future_numbers.py"); mod = U.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def test_future_numbers_add_up_and_refuse_an_unknown_status():
    m = _numbers(); n = m.numbers([{"status": "rendered", "function": "x"}, {"status": "unreachable", "function": "Text-to-speech and voice"}], "1 May")
    assert (n["total"], n["rendered"], n["unreachable"], n["tts_total"], n["tts_unreachable"], n["all_rendered"]) == (2, 1, 1, 1, 1, False)
    assert m.numbers([{"status": "rendered", "function": "x"}], "1 May")["all_rendered"] is True
    with pytest.raises(SystemExit): m.numbers([{"status": "odd", "function": "x"}])
def test_the_shipped_numbers_fill_every_token_in_the_essay():
    d = json.loads((ROOT / "studio" / "web" / "future_essay.json").read_text(encoding="utf-8")); n = json.loads((ROOT / "studio" / "web" / "future_numbers.json").read_text(encoding="utf-8"))
    assert n["total"] == sum(n[s] for s in ("rendered", "graph", "reachable", "unreachable", "not_on_disk")) and "draft" not in d
    live = set(n) | {"ran", "stages", "families", "minutes", "notRun"}
    import re
    assert set(re.findall(r"\{(\w+)\}", json.dumps(d, ensure_ascii=False))) <= live
