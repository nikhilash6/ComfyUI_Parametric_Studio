"""Resumable steps with fake submit/wait: no ComfyUI, no GPU."""
import pytest

from studio.worldkit import jobs, steps as S


class Studio:
    """submit records requests and returns j1, j2, ...; wait answers from a script (default: done, one glb)."""
    def __init__(self, results=None):
        self.reqs, self.waited, self.results = [], [], dict(results or {})

    def submit(self, req):
        self.reqs.append(req)
        return f"j{len(self.reqs)}"

    def wait(self, jid):
        self.waited.append(jid)
        return self.results.get(jid) or {"status": "done", "error": "",
                                         "artifacts": [{"path": f"/o/{jid}.png", "media_type": "image"},
                                                       {"path": f"/o/{jid}.glb", "media_type": "file",
                                                        "kind3d": "mesh"}]}


def _steps(log=None):
    return [
        S.Step("mesh", "Mesh", request=lambda ctx: jobs.goal("mesh", "x"),
               pick=S.pick_first(suffix=(".glb",))),
        S.Step("note", "Note", local=lambda ctx: {"main": {"seen": S.out_path(ctx, "mesh")}}),
        S.Step("clean", "Cleanup", request=lambda ctx: jobs.goal("clean", S.out_path(ctx, "mesh")),
               pick=S.pick_first(suffix=(".glb",))),
    ]


def test_a_run_chains_job_refs_and_local_outputs():
    st, saved = Studio(), []
    state = S.run({}, _steps(), ctx={}, submit=st.submit, wait=st.wait, save=saved.append)
    assert state["state"] == "done" and [r["status"] for r in state["steps"]] == ["done"] * 3
    assert st.reqs[1]["prompt"] == "/o/j1.glb"
    assert state["steps"][1]["outputs"]["main"]["seen"] == "/o/j1.glb"
    assert saved and saved[-1]["state"] == "done"


def test_requests_name_the_live_job_flow():
    assert jobs.goal("image", "a fox", {"aspect": "1:1"}, seed=3) == {"kind": "goal", "goal": "image", "prompt": "a fox", "options": {"aspect": "1:1"}, "seed": 3}
    assert jobs.graph("g.json", {"image": "a.png"}, "l")["kind"] == "graph" and jobs.family("Pixal3D", "t", image="/a.png")["image"] == "/a.png"


def test_a_failure_stops_names_the_step_and_retry_reruns_only_that_step():
    st = Studio({"j2": {"status": "failed", "error": "out of memory", "artifacts": []}})
    state = S.run({}, _steps(), ctx={}, submit=st.submit, wait=st.wait, save=lambda s: None)
    assert state["state"] == "failed" and state["error"] == "Cleanup: out of memory"
    assert [r["status"] for r in state["steps"]] == ["done", "done", "failed"]
    st.results.clear()
    state = S.run(S.retry(state), _steps(), ctx={}, submit=st.submit, wait=st.wait, save=lambda s: None)
    assert state["state"] == "done" and len(st.reqs) == 3                  # the mesh job ran once


def test_a_restart_waits_on_the_recorded_job_and_never_resubmits_it():
    st = Studio()
    state = S.new_state(["mesh", "note", "clean"])
    state["steps"][0].update(status="running", job_id="j7", attempts=1)
    state = S.run(state, _steps(), ctx={}, submit=st.submit, wait=st.wait, save=lambda s: None)
    assert st.waited[0] == "j7" and state["steps"][0]["outputs"]["main"]["job_id"] == "j7"
    assert [r["goal"] for r in st.reqs] == ["clean"]


def test_an_interrupted_job_is_resubmitted_once():
    st = Studio({"j7": {"status": "interrupted", "error": "the server restarted", "artifacts": []}})
    state = S.new_state(["mesh", "note", "clean"])
    state["steps"][0].update(status="running", job_id="j7", attempts=1)
    state = S.run(state, _steps(), ctx={}, submit=st.submit, wait=st.wait, save=lambda s: None)
    assert state["state"] == "done" and st.reqs[0]["goal"] == "mesh"


def test_a_skipped_and_an_optional_step():
    st = Studio({"j1": {"status": "failed", "error": "kimodo busy", "artifacts": []}})
    steps = [S.Step("clip", "Clip", request=lambda ctx: jobs.goal("clip", "walk"),
                    pick=S.pick_first(suffix=(".bvh",)), optional=True),
             S.Step("image", "Image", request=lambda ctx: None, pick=S.pick_first()),
             S.Step("end", "End", local=lambda ctx: {"main": {"clip_done": "clip" in ctx["outputs"]}})]
    state = S.run({}, steps, ctx={}, submit=st.submit, wait=st.wait, save=lambda s: None)
    assert state["state"] == "done" and [r["status"] for r in state["steps"]] == ["failed", "skipped", "done"]
    assert state["steps"][2]["outputs"]["main"]["clip_done"] is False and "optional" in state["steps"][0]["note"]


def test_sync_makes_later_steps_stale_when_a_step_is_inserted():
    state = S.new_state(["mesh", "rig", "assemble"])
    for r in state["steps"]:
        r.update(status="done", outputs={"main": {"index": 0}})
    new = S.sync(state, ["mesh", "rig", "clip_walk", "assemble"])
    assert [r["status"] for r in new["steps"]] == ["done", "done", "pending", "pending"]
    assert "stale" in new["steps"][3]["note"] and new["state"] == "pending"
    assert [r["status"] for r in S.reset_from(state, "rig")["steps"]] == ["done", "pending", "pending"]


def test_pick_helpers():
    arts = [{"path": "/a/x.png", "media_type": "image"}, {"path": "/a/y.mp4", "media_type": "video"}]
    assert S.pick_first(media_type=("video",))(arts, {}) == {"main": {"index": 1, "path": "/a/y.mp4", "media_type": "video"}}
    with pytest.raises(S.StepError, match=".glb"):
        S.pick_first(suffix=(".glb",))(arts, {})


def test_retry_keeps_a_running_record_with_a_job_and_resets_the_rest():
    state = S.new_state(["mesh", "note", "clean"])
    state["steps"][0].update(status="running", job_id="j7", attempts=1)
    state["steps"][1].update(status="failed", error="x", attempts=1)
    state["steps"][2].update(status="running", job_id="", attempts=1)
    new = S.retry(state)
    assert [r["status"] for r in new["steps"]] == ["running", "pending", "pending"]
    assert new["steps"][0]["job_id"] == "j7"
    st = Studio()
    S.run(new, _steps(), ctx={}, submit=st.submit, wait=st.wait, save=lambda s: None)
    assert st.waited[0] == "j7" and [r["goal"] for r in st.reqs] == ["clean"]


def test_an_interrupted_job_is_resubmitted_at_most_once():
    intr = {"status": "interrupted", "error": "the server restarted", "artifacts": []}
    st = Studio({"j7": intr, "j1": intr})                      # the resubmitted job (j1) is interrupted too
    state = S.new_state(["mesh", "note", "clean"])
    state["steps"][0].update(status="running", job_id="j7", attempts=1)
    state = S.run(state, _steps(), ctx={}, submit=st.submit, wait=st.wait, save=lambda s: None)
    assert state["state"] == "failed" and state["error"].startswith("Mesh:") and len(st.reqs) == 1


def test_a_job_already_resubmitted_once_is_not_resubmitted_again():
    st = Studio({"j7": {"status": "interrupted", "error": "the server restarted", "artifacts": []}})
    state = S.new_state(["mesh", "note", "clean"])
    state["steps"][0].update(status="running", job_id="j7", attempts=2)          # already the resubmission
    state = S.run(state, _steps(), ctx={}, submit=st.submit, wait=st.wait, save=lambda s: None)
    assert state["state"] == "failed" and st.reqs == [] and "restarted" in state["error"]


def _built(*rows, state="done"):
    return {"state": state, "error": "", "steps": [{"name": n, "status": st, "note": note, "outputs": {"main": {"path": n}}, "error": ""} for n, st, note in rows]}


LOST = ("motion_idle", "done", ""), ("retarget_idle", "done", ""), ("motion_wave", "failed", "optional: the build continues without it"), ("retarget_wave", "skipped", ""), ("assemble", "done", ""), ("preview", "done", "")


def test_a_lost_motion_is_named_once_the_build_has_ended():
    assert S.lost_motions(_built(*LOST)) == ["wave"]
    assert S.lost_motions(_built(*LOST, state="building")) == [] and S.lost_motions(None) == []
    assert S.lost_motions(_built(("motion_my_wave", "done", ""), ("retarget_my_wave", "failed", "optional: x"))) == ["my_wave"]


def test_retrying_a_lost_motion_keeps_the_other_clips():
    got = {r["name"]: r["status"] for r in S.retry_motion(_built(*LOST), "wave", "assemble")["steps"]}
    assert got == {"motion_idle": "done", "retarget_idle": "done", "motion_wave": "pending", "retarget_wave": "pending", "assemble": "pending", "preview": "pending"}


def test_the_motion_retry_verb_needs_a_lost_motion():
    from studio.worldkit import api as A
    meta = {"id": "a", "type": "character", "name": "x", "status": "approved", "build": _built(*LOST), "recipe": {}}
    class Lib:
        def get(self, aid): return meta
        def update(self, aid, **k): meta.update(k); return meta
    started = []
    code, _ = A.action(Lib(), "a", "retry-motion", {"name": "idle"}, start=started.append, is_running=lambda a: False); assert code == 400 and not started
    code, _ = A.action(Lib(), "a", "retry-motion", {"name": "wave"}, start=started.append, is_running=lambda a: True); assert code == 409 and not started
    code, got = A.action(Lib(), "a", "retry-motion", {"name": "wave"}, start=started.append, is_running=lambda a: False)
    assert code == 200 and started == ["a"] and meta["status"] == "draft" and {r["name"]: r["status"] for r in meta["build"]["steps"]}["motion_wave"] == "pending"
