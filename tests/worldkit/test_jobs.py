"""The bridge to the studio's job flow, with the server stubbed: nothing here reaches a port."""
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from studio.worldkit import jobs


class Server:
    WF = ""
    COMFY = "http://stub"
    CLIENT_ID = "t"

    def __init__(self, tmp):
        self.JOBS, self.posted, self.statuses, self.cancelled, self.WF = {}, [], [], [], str(tmp)

    def _generate(self, b):
        self.posted.append(b)
        if b.get("prompt") == "refuse":
            raise HTTPException(400, "write a prompt first")
        return {"job": "main-1"}

    def comfy_up(self):
        return True

    def comfy(self, path, payload=None, timeout=30, raw=False):
        if raw:
            return b"bytes"
        self.posted.append((path, payload))
        return {"prompt_id": "p1"}

    def job(self, jid):
        return self.statuses.pop(0)

    def cancel(self, jid):
        self.cancelled.append(jid)


@pytest.fixture
def srv(tmp_path, monkeypatch):
    s = Server(tmp_path)
    monkeypatch.setattr(jobs, "server", lambda: s)
    return s


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def test_a_goal_goes_through_the_same_call_as_api_generate(srv):
    assert jobs.submit(jobs.goal("image", "a fox", {"aspect": "1:1"})) == "main-1"
    assert srv.posted[0] == {"goal": "image", "prompt": "a fox", "options": {"aspect": "1:1"}}


def test_a_refusal_keeps_its_own_words(srv):
    with pytest.raises(RuntimeError, match="write a prompt first"):
        jobs.submit(jobs.goal("image", "refuse"))


def test_a_graph_is_filled_queued_and_visible_to_the_jobs_route(srv, tmp_path):
    (tmp_path / "g.json").write_text(json.dumps({"1": {"class_type": "LoadImage", "inputs": {"image": "${image}"}}}))
    assert jobs.submit(jobs.graph("g.json", {"image": "a.png"}, "cut-out")) == "p1"
    assert srv.posted[0][1]["prompt"]["1"]["inputs"]["image"] == "a.png" and srv.JOBS["p1"]["prompt"] == "cut-out"


def test_the_shipped_graphs_fill_with_only_a_picture_name():
    from studio.graph_template import fill, placeholders
    wf = Path(__file__).parents[2] / "workflows"
    for name in ("worldkit_cutout_api.json", "worldkit_body_photo_api.json"):
        g = json.load(open(wf / name, encoding="utf-8"))
        assert placeholders(g) == {"image"}, name
        fill(g, {"image": "a.png"})
    cut = json.load(open(wf / "worldkit_cutout_api.json", encoding="utf-8"))
    assert cut["5"]["inputs"]["alpha"] == ["4", 0] and cut["4"]["class_type"] == "InvertMask"     # JoinImageWithAlpha inverts its mask: a foreground mask must be inverted first


def test_wait_returns_the_local_file_of_a_finished_job(srv, tmp_path):
    out = tmp_path / "output" / "sub"
    out.mkdir(parents=True)
    (out / "a.png").write_bytes(b"png")
    srv.statuses = [{"status": "running"}, {"status": "done", "files": [{"filename": "a.png", "subfolder": "sub", "type": "output"}, {"filename": "in.png", "type": "input"}]}]
    c = Clock()
    res = jobs.wait("main-1", work=tmp_path / "w", sleep=c.sleep, clock=c, poll_s=1)
    assert res["status"] == "done" and res["artifacts"] == [{"path": str(out / "a.png"), "media_type": "image"}]


def test_a_file_this_machine_cannot_see_is_fetched_through_view(srv, tmp_path):
    srv.statuses = [{"status": "done", "files": [{"filename": "far.mp4", "subfolder": "", "type": "output"}]}]
    res = jobs.wait("j", work=tmp_path / "w")
    assert Path(res["artifacts"][0]["path"]).read_bytes() == b"bytes" and res["artifacts"][0]["media_type"] == "video"


def test_an_error_a_vanished_job_and_a_timeout(srv, tmp_path):
    srv.statuses = [{"status": "error", "error": "out of memory"}]
    assert jobs.wait("j", work=tmp_path)["error"] == "out of memory"
    srv.statuses = [{"status": "queued", "position": 0}] * 200
    c = Clock()
    assert jobs.wait("j", work=tmp_path, sleep=c.sleep, clock=c, poll_s=10)["status"] == "interrupted"
    srv.statuses = [{"status": "queued", "position": 3}] * 400
    c = Clock()
    res = jobs.wait("j", work=tmp_path, sleep=c.sleep, clock=c, poll_s=10, timeout_s=50)
    assert res["status"] == "failed" and "timed out" in res["error"] and srv.cancelled == ["j"]


def test_a_cancel_stops_the_wait_and_the_job(srv, tmp_path):
    res = jobs.wait("j", work=tmp_path, cancelled=lambda: True)
    assert res["error"] == "cancelled" and srv.cancelled == ["j"]


def test_a_family_refusal_and_finish_come_back_in_the_same_shape(monkeypatch, tmp_path):
    from studio import families_api as F
    monkeypatch.setattr(F.I, "INSTANCES", str(tmp_path))
    answers = [{"status": "refused", "message": "Pixal3D needs about 30 GB"}, {"status": "done", "files": [{"filename": "m.glb", "subfolder": "", "type": "output"}]}]
    monkeypatch.setattr(F, "job_get", lambda slug, jid: answers.pop(0))
    assert "30 GB" in jobs.wait("pixal3d/fam-1", work=tmp_path)["error"]
    res = jobs.wait("pixal3d/fam-1", work=tmp_path)
    assert res["status"] == "done" and res["artifacts"][0]["path"].endswith("pixal3d/output/m.glb") and res["artifacts"][0]["media_type"] == "file"


def test_a_family_picture_finds_the_loader_in_a_ui_or_an_api_template(tmp_path, monkeypatch):
    from psn import instances as I
    monkeypatch.setattr(I, "INSTANCES", str(tmp_path))
    from PIL import Image
    pic = tmp_path / "p.png"; Image.new("RGB", (2, 2)).save(pic)
    ui = tmp_path / "ui.json"; ui.write_text('{"nodes": [{"id": 7, "type": "LoadImage"}]}')
    api = tmp_path / "api.json"; api.write_text('{"122": {"class_type": "LoadImage", "inputs": {}}}')
    a, b = {}, {}
    jobs._family_image({"slug": "s"}, str(pic), a, str(ui)); jobs._family_image({"slug": "s"}, str(pic), b, str(api))
    assert list(a) == ["7|image"] and list(b) == ["122|image"] and (tmp_path / "s" / "input" / a["7|image"]).exists()
