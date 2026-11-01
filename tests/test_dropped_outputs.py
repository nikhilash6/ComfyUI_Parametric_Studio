"""A graph ComfyUI only partly accepts is an error, not a success with nothing saved. Stubbed: no live ports."""
from studio import apps as A
from studio import families_api as F

RES = {"prompt_id": "p1", "node_errors": {"9": {"class_type": "CLIPLoader", "errors": [{"message": "Value not in list", "details": "clip_name: 'gone.safetensors' not in []"}]}}}


def test_a_clean_answer_has_nothing_dropped():
    assert A.dropped_outputs({"prompt_id": "p1", "node_errors": {}}) == "" and A.dropped_outputs({"prompt_id": "p1"}) == "" and A.dropped_outputs(None) == ""


def test_a_partial_answer_names_the_node_and_the_reason():
    m = A.dropped_outputs(RES)
    assert "CLIPLoader" in m and "gone.safetensors" in m


def test_a_family_job_with_a_dropped_output_is_an_error(monkeypatch):
    posts = []
    def post(url, body, timeout=30):
        posts.append(url); return RES if url.endswith("/prompt") else {}
    monkeypatch.setattr(F, "_post", post); monkeypatch.setattr(F, "_ensure", lambda f: {"port": 1, "slug": "s"}); monkeypatch.setattr(F, "_info", lambda f: {"port": 1})
    monkeypatch.setattr(F.I, "is_up", lambda p: True); monkeypatch.setattr(F, "free_gb", lambda: 90.0); monkeypatch.setattr(F, "_oi", lambda p: {}); monkeypatch.setattr(F, "_persist", lambda r: None)
    monkeypatch.setattr(F.A, "build_graph", lambda p, v, o: {}); monkeypatch.setattr(F.A, "fill_dynamic", lambda g, o: None)
    rec = {"slug": "s", "status": "queued", "need_gb": 1, "values": {}}
    F._work(rec, "fam", "path", {})
    assert rec["status"] == "error" and "CLIPLoader" in rec["error"] and "files" not in rec
