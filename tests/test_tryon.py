"""The try-on methods, stubbed: no ComfyUI, no GPU, no live port."""
from pathlib import Path
import pytest
from fastapi import HTTPException
from studio import tryon as T, graph_registry as G

FAKE = [{"id": "a", "direction": "on", "ready": True, "commercial": False}, {"id": "b", "direction": "on", "ready": True, "commercial": True}, {"id": "c", "direction": "off", "ready": False, "commercial": True}]


def test_the_default_is_the_first_ready_one():
    assert T.default("on", FAKE) == "a" and T.default("off", FAKE) == ""
    assert T.default("on", [{**FAKE[0], "ready": False}, FAKE[1]]) == "b"


def test_the_order_on_the_page_is_the_order_we_judged():
    assert [m["id"] for m in T.METHODS if m["direction"] == "on"][0] == "klein4b" and not T.method("klein4b")["commercial"] and not T.method("qwen21")["commercial"] and T.method("fashn")["commercial"]


def test_every_method_says_its_licence_and_direction():
    for m in T.METHODS: assert m["licence"] and m["direction"] in ("on", "off") and "commercial" in m and m["note"]
    assert {m["direction"] for m in T.METHODS} == {"on", "off"}


def test_a_listing_says_why_one_cannot_run():
    rows = T.listing(lambda m: "needs x" if m["id"] == "fashn" else ""); f = next(r for r in rows if r["id"] == "fashn")
    assert not f["ready"] and f["why_not"] == "needs x"


def test_an_unknown_method_is_a_404():
    with pytest.raises(HTTPException): T.method("nope")


def test_a_runner_method_gets_both_pictures(tmp_path, monkeypatch):
    pics = {"p.png": tmp_path / "p.png", "g.png": tmp_path / "g.png"}; monkeypatch.setattr(T, "_picture", lambda n: pics[n]); monkeypatch.setattr(T, "_out", lambda mid: tmp_path / "o.png"); seen = {}
    def run(m, person, garment, b, out, log): seen.update(person=person, garment=garment); return out
    assert T.execute(T.method("fashn"), {"person": "p.png", "garment": "g.png"}, tmp_path, runner=run) == tmp_path / "o.png" and seen == {"person": pics["p.png"], "garment": pics["g.png"]}


def test_try_off_takes_no_garment(tmp_path, monkeypatch):
    (tmp_path / "r.png").write_bytes(b"x"); monkeypatch.setattr(T, "_picture", lambda n: tmp_path / n); monkeypatch.setattr(T, "_out", lambda mid: tmp_path / "o.png")
    def fam(m, person, garment): assert garment is None; return tmp_path / "r.png"
    assert T.execute(T.method("qwen21_off"), {"person": "p.png"}, tmp_path, family=fam).exists()


def test_a_runner_method_is_on_the_one_list():
    keys = {r["key"] for r in G.all_rows()}
    for m in T.METHODS:
        if m["via"] == "runner": assert "tryon:" + m["id"] in keys
        else: assert f"family:{__import__('studio.families_api', fromlist=['x'])._slug(m['family'])}/{m['template']}" in keys
