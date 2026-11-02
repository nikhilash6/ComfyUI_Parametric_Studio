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


READY = lambda name: {"ready": True, "problems": []}  # noqa


def test_the_store_is_open_by_default_and_shut_with_the_switch_off(monkeypatch):
    started = []
    code, body = api.new_character({"name": "Ada", "description": "tall, auburn hair"}, start=started.append, capability=READY)
    assert code == 200 and started == [body["id"]]
    CS.delete(body["id"])
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "0")
    assert CS.create("Ada", "tall, auburn hair")[0] is None and "off" in CS.create("Ada", "tall")[1]
    assert CS.all_saved() == []
    code, body = api.new_character({"name": "Ada", "description": "tall"}, start=lambda c: pytest.fail("nothing may start"), capability=READY)
    assert code == 403 and CS.all_saved() == []


def test_with_the_picture_model_or_the_picture_check_missing_it_says_so_and_makes_nothing(on):
    missing = lambda name: {"ready": False, "problems": ["Picture check for character sheets: model still downloading or missing"]}  # noqa
    code, body = api.new_character({"name": "Ada", "description": "tall"}, start=lambda c: pytest.fail("nothing may start"), capability=missing)
    assert code == 409 and "Picture check" in body["error"] and CS.all_saved() == []
    code, body = api.new_character({"name": "Ada", "description": "tall"}, start=lambda c: pytest.fail("nothing may start"))     # the real check: this test's models folder is empty
    assert code == 409 and CS.all_saved() == []
    ch, _ = CS.create("Ada", "tall")
    code, body = api.character_again(ch.id, start=lambda c: pytest.fail("nothing may start"), capability=missing)
    assert code == 409 and CS.get(ch.id).take == 0


def test_another_take_uses_the_next_seed_and_goes_through_the_checks_again(on, tmp_path):
    ch, _ = CS.create("Ada", "tall, auburn hair")
    first = CS.sheet_request(ch)["values"]["seed"]
    started = []
    code, body = api.character_again(ch.id, start=started.append, capability=READY)
    assert code == 200 and started == [ch.id] and body["take"] == 1 and CS.sheet_request(CS.get(ch.id))["values"]["seed"] == first + 1
    assert api.character_again(ch.id, start=lambda c: pytest.fail("nothing may start"), sheet_running=lambda c: True, capability=READY)[0] == 409
    assert api.character_again("nosuchchar", start=lambda c: None, capability=READY)[0] == 404
    assert api.character_again(ch.id, start=lambda c: None, capability=READY)[0] == 200
    jobs = Jobs(tmp_path)
    assert CS.build_sheet(ch.id, submit=jobs.submit, wait=jobs.wait, check=lambda p: {"ok": False, "why": ["no face it can read"]}).status == "blocked" and not CS.get(ch.id).sheet().exists()


def test_the_sheet_is_served_only_while_it_holds_a_pass_for_that_exact_file(on, tmp_path):
    ch, _ = CS.create("Ada", "tall, auburn hair")
    assert api.character_sheet_path(ch.id) is None and api.character_sheet_path("../x") is None
    jobs = Jobs(tmp_path)
    got = CS.build_sheet(ch.id, submit=jobs.submit, wait=jobs.wait, check=lambda p: {"ok": True, "version": PC.VERSION, "sha256": PC.sha256(p), "why": []})
    assert got.status == "ready" and api.character_sheet_path(ch.id) == got.sheet()
    assert api.characters_payload([got])[1]["characters"][0]["sheet"] is True
    got.sheet().write_bytes(b"something else")
    assert api.character_sheet_path(ch.id) is None and api.characters_payload([CS.get(ch.id)])[1]["characters"][0]["sheet"] is False


def test_a_sheet_cut_off_by_a_restart_reads_as_interrupted_and_the_limits_go_with_the_list(on):
    ch, _ = CS.create("Ada", "tall")
    ch = CS._update(ch, status="building")
    _, body = api.characters_payload([ch])
    assert body["characters"][0]["status"] == "interrupted" and not body["characters"][0]["running"]
    assert api.characters_payload([ch], sheet_running=lambda c: True)[1]["characters"][0]["status"] == "building"
    for words in ("error of years", "not checked by what they show", "cannot tell whether a face looks like a real person"):
        assert words in body["limits"]


def test_a_saved_character_comes_from_words_and_never_from_a_file(on):
    for extra in ({"image": "a.png"}, {"upload": "x"}, {"sheet": "/tmp/a.png"}, {"source": {"image": "a"}}):
        code, _ = api.new_character({"name": "Ada", "description": "tall", **extra}, start=lambda c: pytest.fail("nothing may start"), capability=READY)
        assert code == 400
    started = []
    code, body = api.new_character({"name": "Ada", "description": "tall, auburn hair, green coat"}, start=started.append, capability=READY)
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
    monkeypatch.setenv("STUDIO_WORLDKIT_CHARACTERS", "0")
    jobs = Jobs(tmp_path)
    assert CS.build_sheet(ch.id, submit=jobs.submit, wait=jobs.wait).status == "draft" and jobs.reqs == []
    assert safety.character_problem()


def test_the_character_route_needs_the_picture_check_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_TOOL_PICTURECHECK", str(tmp_path / "pc"))
    assert any("Picture check" in p and "not installed" in p for p in [C.need("picturecheck")["message"]])
    (tmp_path / "pc").mkdir()
    (tmp_path / "pc" / "run_picturecheck.sh").write_text("#!/bin/sh\n")
    assert C.need("picturecheck")["state"] == "ready"
