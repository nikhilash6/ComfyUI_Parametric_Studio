"""One test per bug the backend debug pass confirmed. No network and no real ports: ComfyUI is a stub, and HOME-level state stays in tmp_path."""
import asyncio, io, json, os, socket, time, urllib.error
import httpx, pytest
os.environ.setdefault("COMFYUI_URL", "http://127.0.0.1:9")
from fastapi.testclient import TestClient
from studio import server as S, sfw, recipes as R

NO_COMFY = urllib.error.URLError("connection refused")
def _down(*a, **k): raise NO_COMFY

@pytest.fixture
def api(monkeypatch):
    """The real app, with every call to ComfyUI stubbed to 'down'."""
    monkeypatch.setattr(S, "comfy", _down); monkeypatch.setattr(S, "comfy_up", lambda: False)
    monkeypatch.setattr(S, "adopt_comfy_paths", lambda: None)
    return TestClient(S.app, raise_server_exceptions=False)

# ---------- 1: the safe-for-work filter reads nested text, and only text is accepted
@pytest.mark.parametrize("body", [{"prompt": ["nude explicit"]}, {"prompt": {"a": "nude"}}, {"prompt": "ok words", "lyrics": ["nude porn"]}, {"prompt": "ok words", "scene": [["porn"]]}])
def test_filter_sees_lists_and_dicts(api, body):
    for path in ("/api/graph", "/api/generate"):
        r = api.post(path, json={"goal": "image", **body}); assert r.status_code == 400 and "safe-for-work" in r.json()["detail"], (path, r.text)

def test_flagged_keeps_its_plain_behaviour():
    assert sfw.flagged("a nude figure") and not sfw.flagged("a fox in snow", None, 12, ["a fox"], {"k": "snow"})

@pytest.mark.parametrize("prompt", [123, True, ["a fox"], {"a": "fox"}])
def test_a_prompt_that_is_not_text_is_refused(api, prompt):
    r = api.post("/api/graph", json={"goal": "image", "prompt": prompt}); assert r.status_code == 400 and "must be text" in r.json()["detail"]

def test_a_null_prompt_does_not_become_the_word_none(api):
    r = api.post("/api/graph", json={"goal": "image", "prompt": None}); assert r.status_code == 400 and "write a prompt" in r.json()["detail"]

def test_compose_and_presets_check_their_text(api):
    assert api.post("/api/presets/apply", json={"prompt": "a nude figure"}).status_code == 400
    assert api.post("/api/presets/apply", json={"prompt": "a fox in snow"}).status_code == 200
    assert api.post("/api/packs/anything/compose", json={"idea": "explicit scene"}).status_code == 400

# ---------- 2: an edited film plan goes through the same filter as the sentence
def _plan(action): return {"title": "t", "character": "a fox", "shots": [{"action": action, "camera": "tracking"}] * 5}

def test_recipe_plan_is_filtered(api, monkeypatch, tmp_path):
    monkeypatch.setattr(R, "_ensure_worker", lambda: None); monkeypatch.setattr(R, "_save", lambda run: None); monkeypatch.setattr(R.QUEUE, "put", lambda rid: None)
    bad = api.post("/api/recipes/short_film/run", json={"values": {"sentence": "a fox in snow"}, "plan": _plan("explicit nude scene")})
    assert bad.status_code == 400 and "safe-for-work" in bad.json()["detail"]
    ok = api.post("/api/recipes/short_film/run", json={"values": {"sentence": "a fox in snow"}, "plan": _plan("a fox runs through snow")}); assert ok.status_code == 200

# ---------- 3: cancelling a job leaves everyone else's render alone
def _comfy_log(monkeypatch, running):
    calls = []
    def fake(path, payload=None, timeout=30, raw=False):
        calls.append((path, payload)); return {"queue_running": [[0, j] for j in running], "queue_pending": []} if path == "/queue" and payload is None else {}
    monkeypatch.setattr(S, "comfy", fake); return calls

def test_cancel_does_not_interrupt_another_job(api, monkeypatch):
    calls = _comfy_log(monkeypatch, ["someone-elses"]); assert api.post("/api/jobs/not-mine/cancel").json() == {"ok": True}
    assert ("/queue", {"delete": ["not-mine"]}) in calls and not any(p == "/interrupt" for p, _ in calls)

def test_cancel_interrupts_the_job_that_is_running(api, monkeypatch):
    calls = _comfy_log(monkeypatch, ["mine"]); api.post("/api/jobs/mine/cancel"); assert ("/interrupt", {"prompt_id": "mine"}) in calls

# ---------- 4: a hung ComfyUI does not freeze the rest of the API
def test_a_slow_comfyui_does_not_block_other_requests(monkeypatch):
    monkeypatch.setattr(S, "comfy", lambda *a, **k: time.sleep(1.0) or {}); monkeypatch.setattr(S, "comfy_up", lambda: False)
    done = []
    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=S.app), base_url="http://127.0.0.1") as c:
            async def slow(): r = await c.post("/api/generate", json={"goal": "image", "prompt": "a fox"}); done.append("generate"); return r
            async def fast(): await asyncio.sleep(0.2); r = await c.get("/api/goals"); done.append("goals"); return r
            return await asyncio.gather(slow(), fast())
    slow, fast = asyncio.run(go()); assert fast.status_code == 200 and slow.status_code == 503 and done == ["goals", "generate"]

def test_the_recipe_worker_can_still_call_generate_directly(monkeypatch):
    monkeypatch.setattr(S, "comfy", _down); monkeypatch.setattr(S, "comfy_up", lambda: False)
    with pytest.raises(S.HTTPException) as e: asyncio.run(S.generate(R._Req({"goal": "image", "prompt": "a fox"})))
    assert e.value.status_code == 503

# ---------- 5, 6: the scheduler runs with the server, and the installer brings what it needs
from studio import schedule as Sched

def test_the_server_starts_and_stops_the_scheduler(monkeypatch, tmp_path):
    monkeypatch.setattr(Sched, "FILE", lambda: tmp_path / "schedules.json"); monkeypatch.setattr(Sched, "CONF", tmp_path); monkeypatch.setattr(S, "adopt_comfy_paths", lambda: None)
    Sched.save([{"id": "j1", "enabled": True, "cron": "0 8 * * *"}, {"id": "off", "enabled": False, "cron": "0 8 * * *"}, {"id": "broken", "enabled": True, "cron": "not a cron"}])
    with TestClient(S.app):
        assert [j.id for j in Sched._sched["s"].get_jobs()] == ["j1"]
    assert Sched._sched["s"] is None

def test_the_installer_installs_apscheduler():
    import install; assert "apscheduler" in install.STUDIO_PACKAGES

def test_a_missing_apscheduler_says_so(monkeypatch):
    def gone(cron): raise ImportError("no apscheduler")
    monkeypatch.setattr(Sched, "trigger", gone)
    with pytest.raises(ValueError, match="apscheduler"): Sched.validate({"cron": "0 8 * * *", "goal": "image", "prompt": "a fox"})

def test_schedules_refuse_impossible_dates_and_drop_junk_options():
    with pytest.raises(ValueError, match="never comes round"): Sched.validate({"cron": "0 0 31 2 *", "goal": "image", "prompt": "a fox"})
    with pytest.raises(ValueError, match="options"): Sched.validate({"cron": "0 8 * * *", "goal": "image", "prompt": "a fox", "options": "notadict"})
    assert Sched.validate({"cron": "0 8 * * *", "goal": "image", "prompt": "a fox", "options": {"aspect": "1:1", "aspect2": "x", "mode": "junk"}})["options"] == {"aspect": "1:1"}

# ---------- 7: other sites cannot drive the studio
def _local(): return TestClient(S.app, client=("127.0.0.1", 5000), base_url="http://127.0.0.1:8310", raise_server_exceptions=False)

@pytest.mark.parametrize("origin", ["https://evil.example", "null", "http://127.0.0.1:9999"])
def test_a_post_from_another_site_is_refused(monkeypatch, origin):
    monkeypatch.setattr(S, "_generate", lambda b: pytest.fail("the job started")); monkeypatch.setattr(S, "comfy", _down)
    r = _local().post("/api/generate", content=b'{"prompt": "a fox"}', headers={"Content-Type": "text/plain", "Origin": origin}); assert r.status_code == 403

def test_a_rebound_host_name_is_refused():
    assert _local().get("/api/goals", headers={"Host": "evil.example:8310"}).status_code == 403

@pytest.mark.parametrize("host", ["127.0.0.1:8310", "localhost:8310", "[::1]:8310", "192.168.1.20:8310", "box.tail1234.ts.net"])
def test_the_studios_own_addresses_still_work(host):
    assert _local().get("/api/goals", headers={"Host": host}).status_code == 200

def test_the_studios_own_page_and_tailscale_serve_can_post(monkeypatch):
    monkeypatch.setattr(S, "_generate", lambda b: {"job": "x"})
    assert _local().post("/api/generate", json={}, headers={"Origin": "http://127.0.0.1:8310"}).status_code == 200
    assert _local().post("/api/generate", json={}).status_code == 200                                 # curl, the scheduler, the worker: no Origin
    assert _local().post("/api/generate", json={}, headers={"Host": "box.tail1234.ts.net", "Origin": "https://box.tail1234.ts.net"}).status_code == 200
    assert _local().post("/api/generate", json={}, headers={"Origin": "https://box.tail1234.ts.net", "X-Forwarded-Host": "box.tail1234.ts.net"}).status_code == 200

def test_an_extra_host_name_can_be_allowed(monkeypatch):
    monkeypatch.setenv("STUDIO_ALLOWED_HOSTS", "studio.lan, other.lan"); assert _local().get("/api/goals", headers={"Host": "studio.lan:8310"}).status_code == 200

def test_a_paired_phone_on_the_lan_still_works(monkeypatch):
    monkeypatch.setenv("STUDIO_TOKEN", "tok"); c = TestClient(S.app, client=("192.168.1.9", 5000), base_url="http://192.168.1.20:8310")
    assert c.get("/api/goals").status_code == 401 and c.get("/api/goals", headers={"X-Studio-Token": "tok"}).status_code == 200
    assert c.post("/api/graph", json={"prompt": "a nude figure"}, headers={"X-Studio-Token": "tok", "Origin": "http://192.168.1.20:8310"}).status_code == 400

# ---------- 8: the attach allow-list reads the real host, and the test button uses it
from studio import attach as AT

@pytest.mark.parametrize("url", ["http://127.0.0.1:80@evil.example.com/", "http://10.1.example.com/", "http://192.168.example.com:8188", "http://172.16.example.com", "http://user@127.0.0.1:8188", "http://127.0.0.1\\@evil.example.com/", "http://2130706433/", "http://169.254.169.254/", "http://example.com", "ftp://localhost", "http://", "http://127.0.0.1:notaport"])
def test_allow_list_refuses(monkeypatch, url):
    monkeypatch.delenv("STUDIO_ALLOW_REMOTE", raising=False)
    with pytest.raises(ValueError): AT._validate_url(url)

@pytest.mark.parametrize("url", ["http://127.0.0.1:8188", "http://localhost:8188/", "http://[::1]:8188", "http://10.0.0.5:8188", "http://172.20.1.1", "http://192.168.1.2:8188", "https://[fd00::1]:8188"])
def test_allow_list_accepts(monkeypatch, url):
    monkeypatch.delenv("STUDIO_ALLOW_REMOTE", raising=False); AT._validate_url(url)

def test_remote_opt_in_still_refuses_a_password_in_the_url(monkeypatch):
    monkeypatch.setenv("STUDIO_ALLOW_REMOTE", "1"); AT._validate_url("https://comfy.example.com")
    with pytest.raises(ValueError): AT._validate_url("http://127.0.0.1:80@comfy.example.com/")

def test_attach_test_validates_before_fetching(monkeypatch):
    monkeypatch.delenv("STUDIO_ALLOW_REMOTE", raising=False); monkeypatch.setattr(AT, "test_connection", lambda url, opener=None: pytest.fail("it fetched " + url))
    assert _local().post("/api/attach/test", json={"url": "http://example.com"}).status_code == 400

def test_attach_import_only_reads_the_workflows_folder(monkeypatch, tmp_path):
    (tmp_path / "wf").mkdir(); (tmp_path / "wf" / "bad.json").write_text("{not json"); secret = tmp_path / "secret.json"; secret.write_text('{"a": 1}')
    monkeypatch.setattr(AT, "load", lambda: {"workflows_dir": str(tmp_path / "wf")}); monkeypatch.setattr(AT, "APPS_DIR", tmp_path / "apps")
    assert _local().post("/api/attach/import", json={"file": str(secret), "inputs": [], "outputs": []}).status_code == 400
    r = _local().post("/api/attach/import", json={"file": str(tmp_path / "wf" / "bad.json"), "inputs": [], "outputs": []}); assert r.status_code == 400 and r.json()["detail"] == "That file is not a JSON workflow"

# ---------- 9: a bad edit list gets a clear refusal, and only numbers reach ffmpeg
from studio import timeline_render as TR

@pytest.mark.parametrize("edl", [{}, {"fps": 12, "tracks": []}, {"fps": 12, "duration": None}, {"fps": True, "duration": 5}])
def test_timeline_without_a_good_duration_is_a_400(api, edl):
    r = api.post("/api/timeline/render", json={"edl": edl}); assert r.status_code == 400 and "invalid" in r.json()["detail"]

def test_timeline_too_long_is_still_refused():
    assert "duration exceeds 600s" in TR.edl_problems({"fps": 12, "duration": 601, "tracks": []}, "/nowhere")

@pytest.mark.parametrize("clip", [{"dur": "2,hue=s=0"}, {"start": None}, {"in": "0"}, {"dur": -1}, {"dur": float("inf")}, {"start": True}, {"src": ["a.mp4"]}])
def test_timeline_clip_fields_must_be_numbers(tmp_path, clip):
    (tmp_path / "a.mp4").write_bytes(b"x"); p = TR.edl_problems({"fps": 12, "duration": 5, "tracks": [{"kind": "video", "clips": [{"src": "a.mp4", **clip}]}]}, str(tmp_path)); assert p and "track 0 clip 0" in p[0]

def test_timeline_good_clip_passes(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x"); assert TR.edl_problems({"fps": 12, "duration": 5, "tracks": [{"kind": "video", "clips": [{"src": "a.mp4", "start": 0, "dur": 2.5, "in": 0}]}]}, str(tmp_path)) == []

# ---------- 10: bad input gets a 400, a broken answer from ComfyUI gets a 502 or 503, never a bare 500
@pytest.mark.parametrize("raw", [b"not json", b"", b"null", b"[1]", b'"text"', b"\xff\xfe"])
@pytest.mark.parametrize("path", ["/api/graph", "/api/generate", "/api/browse/download", "/api/timeline/render"])
def test_a_body_that_is_not_an_object_is_a_400(api, path, raw):
    r = api.post(path, content=raw, headers={"Content-Type": "application/json"}); assert r.status_code == 400 and r.json()["detail"] == "send a JSON object"

@pytest.mark.parametrize("goal", ["nope", None, ["x"], {"a": 1}, 3])
@pytest.mark.parametrize("path", ["/api/graph", "/api/generate"])
def test_an_unknown_goal_is_a_400(api, path, goal):
    r = api.post(path, json={"goal": goal, "prompt": "a fox"}); assert r.status_code == 400 and r.json()["detail"] == "unknown goal"

@pytest.mark.parametrize("field,value,word", [("seed", "abc", "seed"), ("seed", [1], "seed"), ("options", "notadict", "options"), ("negative", 3, "negative")])
def test_bad_fields_are_a_400(api, field, value, word):
    r = api.post("/api/graph", json={"goal": "image", "prompt": "a fox", field: value}); assert r.status_code == 400 and word in r.json()["detail"]

def test_good_requests_still_build_a_graph(api):
    r = api.post("/api/graph", json={"goal": "image", "prompt": "a fox", "seed": "12", "options": {"aspect": "1:1"}}); assert r.status_code == 200 and r.json()["values"]["seed"] == 12

def _rejecting(monkeypatch, code, body):
    def fake(path, payload=None, timeout=30, raw=False):
        if path == "/prompt": raise urllib.error.HTTPError("http://x/prompt", code, "no", {}, io.BytesIO(body))
        return {}
    monkeypatch.setattr(S, "comfy", fake); monkeypatch.setattr(S, "comfy_up", lambda: True)

@pytest.mark.parametrize("body,status,text", [(b'{"error": "plain words"}', 400, "plain words"), (b'{"error": {"message": "bad node"}, "node_errors": {"3": {"errors": [{"message": "no such file"}]}}}', 400, "no such file"), (b"<html>proxy</html>", 502, "not JSON"), (b"[]", 400, "rejected"), (b'{"node_errors": "x"}', 400, "rejected")])
def test_comfyui_refusals_of_any_shape(api, monkeypatch, body, status, text):
    _rejecting(monkeypatch, 400, body); r = api.post("/api/generate", json={"prompt": "a fox"}); assert r.status_code == status and text in r.json()["detail"]

@pytest.mark.parametrize("b", [{"source": "civitai", "confirm": True}, {"source": "civitai", "confirm": True, "file": "x"}, {"source": "huggingface", "confirm": True}, {"source": "huggingface", "confirm": True, "repo_id": "a/b"}, {"source": "other", "confirm": True}])
def test_browse_download_without_what_it_needs_is_a_400(api, b):
    assert api.post("/api/browse/download", json=b).status_code == 400

@pytest.mark.parametrize("brief", [{"name": ["x"]}, {"name": 3}, {"name": {"a": 1}}, {"name": "ok", "facts": ["x"]}, {"name": "ok", "facts": "x"}, {"name": "ok", "pages": "Home"}, {"name": "ok", "pages": [1]}])
def test_site_brief_with_wrong_types_is_refused_before_any_model_call(api, monkeypatch, brief):
    from studio import site_api; monkeypatch.setattr(site_api, "build_site", lambda *a, **k: pytest.fail("it called the writer"))
    assert api.post("/api/site/build", json={"brief": brief}).status_code == 400

# ---------- lower severity
def _urlopen_raises(monkeypatch, exc):
    def fake(*a, **k): raise exc
    monkeypatch.setattr(S.urllib.request, "urlopen", fake)

def test_view_tells_a_missing_file_from_a_missing_comfyui(api, monkeypatch):
    _urlopen_raises(monkeypatch, urllib.error.URLError("refused")); assert api.get("/api/view?filename=a.png").status_code == 503
    _urlopen_raises(monkeypatch, urllib.error.HTTPError("u", 404, "no", {}, None)); assert api.get("/api/view?filename=a.png").status_code == 404
    _urlopen_raises(monkeypatch, urllib.error.HTTPError("u", 500, "no", {}, None)); assert api.get("/api/view?filename=a.png").status_code == 502

def test_job_status_says_why_it_is_unknown(api):
    d = api.get("/api/jobs/abc").json(); assert d["status"] == "unknown" and "not reachable" in d["detail"]

@pytest.mark.parametrize("limit,want", [(-1, 1), (0, 1), (2, 2), (10**6, 500)])
def test_history_limit_is_clamped(monkeypatch, limit, want):
    asked = []
    def fake(path, **k): asked.append(path); return {}
    monkeypatch.setattr(S, "comfy", fake); monkeypatch.setattr(S, "_family_history", lambda n: [{"job": i} for i in range(1000)])
    rows = TestClient(S.app).get(f"/api/history?limit={limit}").json(); assert f"max_items={want}" in asked[0] and len(rows) == want

# ---------- 11: the university checks
from studio.university import build as UB

def _course(tmp_path, body):
    d = tmp_path / "c"; d.mkdir(); (d / "lesson.md").write_text(body); [(d / n).write_text(t) for n, t in (("lab.py", "assert 1"), ("lab_output.txt", ""), ("quiz.json", '{"questions": []}'))]
    return {"dir": d, "code": "CU-1", "title": "t"}

def test_stray_star_check_ignores_inline_code_and_still_finds_real_ones(tmp_path):
    ok = UB.check_course(_course(tmp_path, "# CU-1 - t\nthe sum `(strength * alpha) * diff`\n"), [], {})
    assert not any("stray" in p for p in ok)
    (tmp_path / "c" / "lesson.md").write_text("# CU-1 - t\nthe norm |BA − ΔW*|² here\n"); assert any("stray" in p for p in UB.check_course({"dir": tmp_path / "c", "code": "CU-1", "title": "t"}, [], {}))

def test_source_keys_have_no_trailing_slash():
    assert not [k for k in UB.SOURCES() if k.endswith("/")]

# ---------- UI pass: a handler written JSX style is a plain string in htm, and htm then crashes the whole render
def test_no_jsx_style_handlers_in_the_web_files():
    import pathlib, re
    web = pathlib.Path(S.__file__).parent / "web"; bad = [f"{p.name}: {m.group(0)}" for p in web.glob("*.js") for m in re.finditer(r"\bon[A-Za-z]+=\{(?!\{)", p.read_text(encoding="utf-8"))]
    assert not bad, bad

def test_offline_comfyui_is_not_reported_as_busy(api, monkeypatch):
    from studio import calibrate as C, schedule as SC
    monkeypatch.setattr(C, "comfy_idle", lambda: None); r = api.post("/api/calibrate", json={"confirm": True}); assert r.status_code == 503 and "not reachable" in r.json()["detail"]
    monkeypatch.setattr(C, "comfy_idle", lambda: False); r = api.post("/api/calibrate", json={"confirm": True}); assert r.status_code == 409 and "busy" in r.json()["detail"]
    job = {"id": "j", "enabled": True, "runs_today": 0, "max_per_day": 3, "prompt": "a fox in snow", "lyrics": "", "day": ""}
    monkeypatch.setattr(SC, "load", lambda: [dict(job)]); monkeypatch.setattr(SC, "save", lambda *a, **k: None)
    assert SC.fire("j", idle=lambda: None) == "skipped: ComfyUI is offline"
    assert SC.fire("j", idle=lambda: False) == "skipped: busy"

def test_answers_from_notes_carry_no_paths_or_markup():
    from studio.crew_api import public_text as P
    assert P("See old-backend/docs/research/klein.md for **steps**") == "See for steps"
    box = "/" + "home/someone/notes/a.md"; assert box not in P("from " + box) and P("# Title\n- one `two`") == "Title\none two"
    assert P("read https://example.com/a/b/c.md and and/or/else") == "read https://example.com/a/b/c.md and and/or/else"

def test_demo_shim_serves_saved_graphs_and_knows_its_answers():
    import pathlib, re
    src = (pathlib.Path(S.__file__).parent.parent / "scripts" / "build_pages.py").read_text(encoding="utf-8")
    assert '"graphs__"' in src and "_index.json" in src and "STUDIO_DEMO" in src and '"free_gb"' in src
