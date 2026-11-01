"""Hardware Fit: every figure says measured or estimate, nothing is guessed, and suggestions come only from what measurably fits. No live ports."""
import json, re
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from studio import feature_fit as F

WEB = Path(F.__file__).parent / "web"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:9")
    app = FastAPI(); app.include_router(F.router); return TestClient(app)


def test_every_goal_family_and_recipe_has_a_row():
    from studio.goals import GOALS
    r = F.rows(); s = {x["section"] for x in r}; keys = {x["key"] for x in r}
    assert s == {"goal", "family", "recipe"} and all("goal:" + g in keys for g in GOALS)
    fam = json.loads((Path(F.__file__).parent / "family_status.json").read_text())["families"]
    assert sum(1 for x in r if x["section"] == "family") == sum(1 for f in fam.values() for t in f.get("templates") or [] if isinstance(t, dict))


def test_every_number_is_labelled():
    for x in F.rows():
        assert (x["need"] is None and x["basis"] is None) or (x["need"] > 0 and x["basis"] in ("measured", "estimate") and x["note"])


def test_a_measured_figure_really_is_on_record():
    from studio import recipes as R
    gm = F.goal_measured(); renders = R.renders(); fm = F.family_measures()
    for x in F.rows():
        if x["basis"] != "measured": continue
        k = x["key"].split(":", 1)[1]
        if x["section"] == "goal": assert gm[k]["peak_gib"] == x["need"]
        elif x["section"] == "recipe" and k in renders and renders[k].get("peak_scope") == "recipe": assert renders[k]["peak_vram_gib"] == x["need"]


def test_a_whole_card_peak_does_not_stand_for_a_picture_recipe():
    from studio import recipes as R
    rid = next(k for k, v in R.renders().items() if v.get("peak_scope") == "card" and v["kind"] == "picture")
    row = next(x for x in F.rows() if x["key"] == "recipe:" + rid)
    assert row["need"] <= R.renders()[rid]["peak_vram_gib"] and "whole-card" in row["note"]


def test_an_estimate_says_how_it_was_worked_out():
    est = [x for x in F.rows() if x["basis"] == "estimate" and x["section"] == "family"]
    assert est and all(str(F.weights_ratio()) in x["note"] for x in est)


@pytest.mark.parametrize("need,basis,vram,ram,weights,word", [(10, "measured", 24, 64, None, "runs"), (24, "measured", 24, 64, None, "runs"), (30, "measured", 12, 64, None, "offload"), (96, "measured", 12, 64, None, "no"), (10, "measured", 0, 64, None, "no"), (10, "measured", 24, 64, 200, "no"), (None, None, 24, 64, None, "unknown"), (10, "measured", None, None, None, "unknown")])
def test_verdicts(need, basis, vram, ram, weights, word):
    assert F.verdict(need, basis, vram, ram, weights)["verdict"] == word


def test_below_the_peak_is_called_an_estimate():
    assert "estimate" in F.verdict(30, "measured", 12, 64)["why"]


def test_suggestions_only_come_from_measured_rows_that_run():
    t = F.table(12, 32); ok = {r["key"]: r for r in t["rows"] if r["verdict"] == "runs" and r["basis"] == "measured"}; tried = [r for r in t["rows"] if r["try"]]
    assert tried and all(r["try"]["key"] in ok and ok[r["try"]["key"]]["kind"] == r["kind"] for r in tried)


def test_no_measured_fit_means_no_suggestion():
    a = {"key": "a", "kind": "video", "basis": "measured", "need": 1, "open": "x", "label": "A", "section": "goal"}
    assert F.try_instead({"key": "b", "kind": "video"}, [{**a, "basis": "estimate"}]) is None and F.try_instead({"key": "b", "kind": "image"}, [a]) is None and F.try_instead({"key": "b", "kind": "video"}, [a])["key"] == "a"


def test_a_bigger_card_never_runs_less():
    a, b = F.table(8, 64)["tally"], F.table(48, 64)["tally"]
    assert all(b[k]["runs"] >= a[k]["runs"] for k in a)


def test_table_route_and_bad_numbers(client):
    d = client.get("/api/fit/table?vram=12&ram=32").json(); assert d["vram_gib"] == 12 and d["caveat"] and d["rows"]
    assert client.get("/api/fit/table?vram=lots").status_code == 400 and client.get("/api/fit/table?vram=-1").status_code == 400
    assert all(r["verdict"] == "unknown" for r in client.get("/api/fit/table").json()["rows"])


def test_nothing_answering_detects_nothing(client, monkeypatch):
    def none(*a, **k): raise OSError
    monkeypatch.setattr(F.subprocess, "run", none)
    d = client.get("/api/fit/detect").json(); assert d["vram_gib"] is None and d["gpu"] is None


def test_detect_reads_comfy(monkeypatch):
    import io
    body = json.dumps({"system": {"ram_total": 64 * 2**30}, "devices": [{"name": "cuda:0 NVIDIA GeForce RTX 3060 : cudaMallocAsync", "vram_total": 12 * 2**30}]}).encode()
    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(F.urllib.request, "urlopen", lambda *a, **k: R(body))
    d = F.detect(); assert d == {"gpu": "NVIDIA GeForce RTX 3060", "vram_gib": 12, "ram_gib": 64, "from": "ComfyUI"}


def test_pages_carry_the_chip_and_the_labels():
    js = (WEB / "fit.js").read_text()
    assert "r.basis" in js and "—" not in js and not re.search(r"https?://", js)
    assert "FitChip" in (WEB / "recipes.js").read_text() and "FitChip" in (WEB / "families.js").read_text() and "FitChip" in (WEB / "app.js").read_text()
