"""What counts as a job's result, its place in history, and a job ComfyUI has forgotten. ComfyUI is stubbed; nothing touches a live port."""
import json
import pytest
from fastapi.testclient import TestClient
from studio import families_api as F, recipes as R, server as S

SOURCE = {"filename": "studio_abc.mp4", "subfolder": "", "type": "input"}
RENDER = {"filename": "reshoot_00003_.mp4", "subfolder": "video", "type": "output"}
PREVIEW = {"filename": "ComfyUI_temp_1.png", "subfolder": "", "type": "temp"}
ENTRY = {"status": {"status_str": "success", "completed": True}, "outputs": {"4": {"images": [SOURCE], "animated": [True]}, "9": {"images": [RENDER, PREVIEW]}}}          # the order reshoot, orbit and recast report


def test_the_uploaded_clip_is_never_a_result():
    assert [f["filename"] for f in S._files(ENTRY)] == ["reshoot_00003_.mp4"]


def test_a_family_job_drops_the_uploaded_clip_too():
    assert [f["filename"] for f in F._file_rows("fam", ENTRY)] == ["reshoot_00003_.mp4"]


def test_a_finished_job_reports_only_its_render(monkeypatch):
    monkeypatch.setattr(S, "comfy", lambda path, **k: {"j1": ENTRY}); monkeypatch.setattr(S.backends, "JOBS", {})
    d = TestClient(S.app).get("/api/jobs/j1").json()
    assert d["status"] == "done" and [f["type"] for f in d["files"]] == ["output"] and d["files"][0]["filename"] == "reshoot_00003_.mp4"


def test_history_lists_the_render_and_skips_a_job_that_only_echoed_its_source(monkeypatch):
    echo = {"status": {"completed": True}, "outputs": {"4": {"images": [SOURCE]}}}
    monkeypatch.setattr(S, "comfy", lambda path, **k: {"j1": ENTRY, "j2": echo}); monkeypatch.setattr(S, "_family_history", lambda n: []); monkeypatch.setattr(R, "library_rows", lambda n: []); monkeypatch.setattr(S.backends, "JOBS", {})
    rows = TestClient(S.app).get("/api/history?limit=10").json()
    assert [r["job"] for r in rows] == ["j1"] and [f["filename"] for f in rows[0]["files"]] == ["reshoot_00003_.mp4"]


def test_a_family_record_saved_before_the_fix_loses_its_source_tile(tmp_path, monkeypatch):
    (tmp_path / "fam").mkdir(); rec = {"job": "fam-1", "status": "done", "started": 5, "files": [{"filename": "s.mp4", "kind": "video", "type": "input"}, {"filename": "r.mp4", "kind": "video", "type": "output"}]}
    (tmp_path / "fam" / "studio_jobs.jsonl").write_text(json.dumps(rec) + "\n")
    monkeypatch.setattr(F.I, "INSTANCES", str(tmp_path)); monkeypatch.setattr(F.I, "slug", lambda f: "fam"); monkeypatch.setattr(F, "family_names", lambda: ["Fam"])
    assert [f["filename"] for f in F.history_rows(5)[0]["files"]] == ["r.mp4"]


# ---------- history: newest first across every source
def ran(jid, ms, fn):
    return {"status": {"completed": True, "messages": [["execution_start", {"prompt_id": jid, "timestamp": ms}]]}, "outputs": {"9": {"images": [{"filename": fn, "subfolder": "video", "type": "output"}]}}}


@pytest.fixture
def sources(monkeypatch):
    main = {"m_old": ran("m_old", 1_000_000, "old.mp4"), "m_new": ran("m_new", 3_000_000, "new.mp4")}          # ComfyUI lists oldest first
    fam = [{"job": f"fam-{i}", "files": [{"filename": "f.mp4", "kind": "video"}], "family": "fam", "started": 2000 - i} for i in range(60)]
    film = [{"job": "film", "files": [{"filename": "r.mp4", "kind": "video"}], "goal": "recipe", "started": 2500}]
    def comfy(path, **k):
        if not path.startswith("/history"): return {}
        n = int(path.split("max_items=")[1]); return dict(list(main.items())[-n:])
    monkeypatch.setattr(S, "comfy", comfy); monkeypatch.setattr(S, "_family_history", lambda n: fam[:n]); monkeypatch.setattr(R, "library_rows", lambda n: film)
    monkeypatch.setattr(S.backends, "history", lambda: [{"job": "sdk", "files": [{"filename": "s.mp4", "kind": "video"}], "started": 1500}])
    return TestClient(S.app)


def test_history_is_newest_first_across_sources(sources):
    jobs = [r["job"] for r in sources.get("/api/history?limit=4").json()]
    assert jobs == ["m_new", "film", "fam-0", "fam-1"]


@pytest.mark.parametrize("limit", [24, 60])
def test_a_main_render_survives_the_cut_that_buried_it(sources, limit):
    rows = sources.get(f"/api/history?limit={limit}").json()
    assert len(rows) == limit and rows[0]["job"] == "m_new" and any(not r.get("family") for r in rows)


def test_only_main_lists_what_the_timeline_can_cut_however_many_family_jobs_ran(sources):
    assert [r["job"] for r in sources.get("/api/history?limit=60&only=main").json()] == ["m_new", "sdk", "m_old"]


def test_a_job_with_no_time_keeps_its_place_after_the_job_before_it(monkeypatch):
    plain = {"status": {"completed": True}, "outputs": {"9": {"images": [{"filename": "p.mp4", "type": "output"}]}}}
    monkeypatch.setattr(S, "comfy", lambda path, **k: {"a": ran("a", 5000_000, "a.mp4"), "b": plain}); monkeypatch.setattr(S, "_family_history", lambda n: [{"job": "fam", "files": [], "started": 1000}]); monkeypatch.setattr(R, "library_rows", lambda n: []); monkeypatch.setattr(S.backends, "JOBS", {})
    assert [r["job"] for r in TestClient(S.app).get("/api/history").json()][-1] == "fam"


def test_history_still_answers_when_comfyui_is_down(monkeypatch):
    def down(path, **k): raise OSError("refused")
    monkeypatch.setattr(S, "comfy", down); monkeypatch.setattr(S, "_family_history", lambda n: [{"job": "fam", "files": [], "started": 1}]); monkeypatch.setattr(S.backends, "history", lambda: [{"job": "sdk", "files": [], "started": 2}])
    c = TestClient(S.app)
    assert [r["job"] for r in c.get("/api/history").json()] == ["sdk", "fam"] and [r["job"] for r in c.get("/api/history?only=main").json()] == ["sdk"]


def test_the_timeline_and_the_create_strip_ask_for_main_renders_only():
    from pathlib import Path
    web = Path(S.__file__).parent / "web"
    assert "/api/history?limit=60&only=main" in (web / "extras.js").read_text() and "/api/history?limit=24&only=main" in (web / "app.js").read_text()


# ---------- a job ComfyUI has forgotten
def box(monkeypatch, history, queue):
    """history: what each /history/<id> call answers, in order. queue: the /queue answer, or an exception to raise."""
    answers = iter(history)
    def comfy(path, **k):
        if path.startswith("/history/"):
            a = next(answers)
            if isinstance(a, Exception): raise a
            return a
        if isinstance(queue, Exception): raise queue
        return queue
    monkeypatch.setattr(S, "comfy", comfy); monkeypatch.setattr(S.backends, "JOBS", {}); return TestClient(S.app)


EMPTY_QUEUE = {"queue_running": [], "queue_pending": []}


def test_a_job_comfyui_forgot_is_lost_not_queued_forever(monkeypatch):
    d = box(monkeypatch, [{}, {}], EMPTY_QUEUE).get("/api/jobs/gone").json()
    assert d["status"] == "error" and d["lost"] is True and "restarted" in d["error"]


def test_a_job_that_finishes_between_the_two_checks_is_not_lost(monkeypatch):
    d = box(monkeypatch, [{}, {"late": ENTRY}], EMPTY_QUEUE).get("/api/jobs/late").json()
    assert d["status"] == "done" and d["files"][0]["filename"] == "reshoot_00003_.mp4"


def test_a_running_and_a_waiting_job_are_not_lost(monkeypatch):
    assert box(monkeypatch, [{}], {"queue_running": [[0, "j"]], "queue_pending": []}).get("/api/jobs/j").json()["status"] == "running"
    d = box(monkeypatch, [{}], {"queue_running": [], "queue_pending": [[0, "x"], [1, "j"]]}).get("/api/jobs/j").json()
    assert d["status"] == "queued" and d["position"] == 2 and "lost" not in d


@pytest.mark.parametrize("history,queue", [([OSError("down")], OSError("down")), ([OSError("blip"), {}], EMPTY_QUEUE), ([{}, OSError("blip")], EMPTY_QUEUE)])
def test_not_hearing_from_comfyui_is_unknown_not_lost(monkeypatch, history, queue):
    d = box(monkeypatch, history, queue).get("/api/jobs/j").json()
    assert d["status"] == "unknown" and "lost" not in d


def test_a_recipe_step_stops_on_a_lost_job(monkeypatch):
    class Srv:
        @staticmethod
        def job(j): return {"status": "error", "lost": True, "error": "ComfyUI no longer knows this job"}
    monkeypatch.setattr(R, "_srv", lambda: Srv); monkeypatch.setattr(R, "_save", lambda run: None); monkeypatch.setattr(R, "POLL", 0)
    with pytest.raises(R.StepError, match="no longer knows"): R._wait_job({}, {}, "gone")
