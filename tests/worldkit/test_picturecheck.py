"""The sheet check's rule, the saved-character store and how they fail. No model, no live port: the tool is stubbed, and no test picture shows a person. What the real check did on harmless pictures is in the report, not here."""
import json

import pytest
from PIL import Image

from studio.worldkit import api, capabilities as C, characters as CS, picturecheck as PC, safety

ADULT = {"faces": [{"age": 31.0, "score": 0.9, "box": [0, 0, 9, 9]}], "exposed": []}


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "1")


def test_it_passes_only_a_readable_adult_face_with_nothing_undressed():
    assert PC.judge(ADULT) == []
    assert "no face" in PC.judge({"faces": [], "exposed": []})[0]
    assert "no face" in PC.judge({"faces": [{"age": 40, "score": 0.1}], "exposed": []})[0]             # a face it barely sees cannot be aged
    assert "under 20" in PC.judge({"faces": [{"age": 19.0, "score": 0.9}], "exposed": []})[0]
    assert "under 20" in " ".join(PC.judge({"faces": [{"age": 40, "score": 0.9}, {"age": 12, "score": 0.8}], "exposed": []}))      # any face
    for cls in ("FEMALE_GENITALIA_EXPOSED", "MALE_GENITALIA_EXPOSED", "ANUS_EXPOSED", "FEMALE_BREAST_EXPOSED", "BUTTOCKS_EXPOSED", "MALE_BREAST_EXPOSED", "BELLY_EXPOSED"):
        assert PC.judge({**ADULT, "exposed": [{"class": cls, "score": 0.9}]})
    assert PC.judge({**ADULT, "exposed": [{"class": "FEET_EXPOSED", "score": 0.9}, {"class": "BELLY_EXPOSED", "score": 0.2}]}) == []


class Run:
    def __init__(self, facts=ADULT, rc=0):
        self.facts, self.rc = facts, rc

    def __call__(self, cmd, **kw):
        return type("P", (), {"returncode": self.rc, "stdout": PC.TAG + json.dumps({"path": cmd[-1], **self.facts}), "stderr": "boom"})()


def _png(tmp_path, name="s.png"):
    p = tmp_path / name
    Image.new("RGB", (8, 8), (90, 90, 90)).save(p)
    return p


def test_a_check_that_cannot_run_does_not_pass(tmp_path):
    p = _png(tmp_path)
    assert PC.check(p, run=Run())["ok"] is True
    assert PC.check(p, run=Run(rc=3))["ok"] is False
    assert PC.check(p, run=lambda c, **k: (_ for _ in ()).throw(OSError("gone")))["ok"] is False
    assert PC.check(tmp_path / "missing.png", run=Run())["ok"] is False
    assert PC.check(p, run=lambda c, **k: type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})())["ok"] is False


def test_a_pass_counts_only_for_that_exact_file_and_this_rule(tmp_path):
    p = _png(tmp_path)
    rec = PC.check(p, run=Run())
    assert PC.passed(rec, p)
    assert not PC.passed({**rec, "version": PC.VERSION + 1}, p) and not PC.passed({**rec, "ok": False}, p) and not PC.passed({}, p) and not PC.passed(None, p)
    Image.new("RGB", (8, 8), (10, 10, 10)).save(p)
    assert not PC.passed(rec, p)                                                                       # the file was changed after the check


def test_the_vision_opinion_is_off_by_default_and_fails_closed_when_on(tmp_path, monkeypatch):
    p = _png(tmp_path)
    assert PC.check(p, run=Run(), post=lambda b: pytest.fail("the vision check must not run unless switched on"))["vision"] is False
    monkeypatch.setenv("STUDIO_WORLDKIT_VISION_CHECK", "1")
    assert PC.check(p, run=Run())["ok"] is False                                                        # on, and no server named
    monkeypatch.setenv("STUDIO_WORLDKIT_VISION_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("STUDIO_WORLDKIT_VISION_MODEL", "m")
    say = lambda text: (lambda b: {"choices": [{"message": {"content": text}}]})
    assert PC.check(p, run=Run(), post=say('{"child_or_teen": false, "undressed_or_sexual": false, "real_famous_person": false}'))["ok"] is True
    assert PC.check(p, run=Run(), post=say('{"child_or_teen": true, "undressed_or_sexual": false, "real_famous_person": false}'))["ok"] is False
    assert PC.check(p, run=Run(), post=say('{"child_or_teen": false}'))["ok"] is False                  # an unanswered question counts as doubt
    assert PC.check(p, run=Run(), post=say("I think so"))["ok"] is False
    assert PC.check(p, run=Run(), post=lambda b: (_ for _ in ()).throw(OSError("down")))["ok"] is False


def test_the_store_stays_shut_with_the_switch_off():
    assert CS.create("Ada", "tall, auburn hair")[0] is None and "off" in CS.create("Ada", "tall")[1]
    assert CS.all_saved() == []
    code, body = api.new_character({"name": "Ada", "description": "tall"}, start=lambda c: pytest.fail("nothing may start"))
    assert code == 403 and CS.all_saved() == []


def test_a_saved_character_comes_from_words_and_never_from_a_file(on):
    for extra in ({"image": "a.png"}, {"upload": "x"}, {"sheet": "/tmp/a.png"}, {"source": {"image": "a"}}):
        code, _ = api.new_character({"name": "Ada", "description": "tall", **extra}, start=lambda c: pytest.fail("nothing may start"))
        assert code == 400
    started = []
    code, body = api.new_character({"name": "Ada", "description": "tall, auburn hair, green coat"}, start=started.append)
    assert code == 200 and started == [body["id"]] and CS.get(body["id"]).status == "draft"


@pytest.mark.parametrize("desc", ["a little girl", "a teenage boy", "a 15 year old", "nude", "looks like a famous actress", "portrait of my neighbour", "based on a real person", "resembling the president"])
def test_words_for_a_child_undress_or_a_real_person_are_refused(on, desc):
    assert CS.create("Ada", desc)[0] is None and CS.all_saved() == []


class Jobs:
    def __init__(self, tmp_path, status="done"):
        self.tmp, self.status, self.reqs = tmp_path, status, []

    def submit(self, req):
        self.reqs.append(req)
        return "j1"

    def wait(self, jid):
        p = _png(self.tmp, "made.png")
        return {"status": self.status, "error": "busy", "artifacts": [{"path": str(p), "media_type": "image"}]}


def test_a_sheet_that_passes_is_ready_and_usable(on, tmp_path):
    ch, _ = CS.create("Ada", "tall, auburn hair")
    jobs = Jobs(tmp_path)
    got = CS.build_sheet(ch.id, submit=jobs.submit, wait=jobs.wait, check=lambda p: PC.check(p, run=Run()))
    assert got.status == "ready" and got.sheet().is_file() and CS.sheet_problem(got) == ""
    assert jobs.reqs[0]["template"] == "worldkit_krea2_t2i_api.json" and "invented adult" in jobs.reqs[0]["values"]["prompt"] and "Fully clothed" in jobs.reqs[0]["values"]["prompt"]
    Image.new("RGB", (8, 8), (1, 1, 1)).save(got.sheet())
    assert "has not passed" in CS.sheet_problem(CS.get(ch.id))                                         # swapped by hand afterwards


def test_a_sheet_that_fails_is_deleted_and_blocked(on, tmp_path):
    ch, _ = CS.create("Ada", "tall, auburn hair")
    jobs = Jobs(tmp_path)
    got = CS.build_sheet(ch.id, submit=jobs.submit, wait=jobs.wait, check=lambda p: PC.check(p, run=Run({"faces": [{"age": 12.0, "score": 0.9}], "exposed": []})))
    assert got.status == "blocked" and "under 20" in got.error and not got.sheet().exists() and "blocked" in CS.sheet_problem(got)
    assert not (got.folder / "checking.png").exists()
    got = CS.build_sheet(ch.id, submit=jobs.submit, wait=jobs.wait, check=lambda p: PC.check(p, run=Run(rc=2)))
    assert got.status == "blocked" and "could not run" in got.error and not got.sheet().exists()
    failed = Jobs(tmp_path, status="failed")
    assert CS.build_sheet(ch.id, submit=failed.submit, wait=failed.wait, check=lambda p: pytest.fail("no picture")).status == "failed"


def test_turning_characters_off_stops_a_build_and_the_maker(monkeypatch, on, tmp_path):
    ch, _ = CS.create("Ada", "tall, auburn hair")
    monkeypatch.delenv("STUDIO_WORLDKIT_CHARACTERS")
    jobs = Jobs(tmp_path)
    assert CS.build_sheet(ch.id, submit=jobs.submit, wait=jobs.wait).status == "draft" and jobs.reqs == []
    assert safety.character_problem()


def test_the_character_route_needs_the_picture_check_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_TOOL_PICTURECHECK", str(tmp_path / "pc"))
    assert any("Picture check" in p and "not installed" in p for p in [C.need("picturecheck")["message"]])
    (tmp_path / "pc").mkdir()
    (tmp_path / "pc" / "run_picturecheck.sh").write_text("#!/bin/sh\n")
    assert C.need("picturecheck")["state"] == "ready"
