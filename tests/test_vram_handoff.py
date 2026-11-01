import json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from psn.vram_handoff import Handoff, llm_url


@pytest.fixture()
def llm():
    """A stub LLM server; no real GPU or live port is touched."""
    state = dict(sleeping=False, calls=[], fail_wait=False)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _ok(self, body):
            self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(body).encode())

        def do_GET(self):
            self._ok({"is_sleeping": state["sleeping"]})

        def do_POST(self):
            state["calls"].append(self.path)
            if "mode=wait" in self.path and state["fail_wait"]:
                self.send_response(503); self.end_headers(); return
            state["sleeping"] = "/sleep" in self.path
            self._ok({})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state["base"] = f"http://127.0.0.1:{srv.server_address[1]}"
    yield state
    srv.shutdown()


def make(llm, tasks=None, freed=None, now=None, base=None):
    tasks = tasks if tasks is not None else [0]
    freed = freed if freed is not None else []
    now = now if now is not None else [0.0]
    return Handoff(base or llm["base"], lambda: tasks[0], lambda: freed.append(1), idle_s=30, wait_s=2, clock=lambda: now[0]), tasks, freed, now


def test_off_by_default_and_local_only():
    assert llm_url({}) == ""
    assert llm_url({"PSN_VRAM_HANDOFF_LLM_URL": "http://127.0.0.1:8002/"}) == "http://127.0.0.1:8002"
    with pytest.raises(ValueError):
        llm_url({"PSN_VRAM_HANDOFF_LLM_URL": "http://example.com:8002"})


def test_render_moves_llm_to_ram_at_level_1_once(llm):
    h, *_ = make(llm)
    h.before_render(); h.before_render()
    assert h.asleep and llm["calls"] == ["/sleep?level=1&mode=wait"]


def test_no_call_ever_uses_level_2(llm):
    h, tasks, _, now = make(llm)
    llm["fail_wait"] = True
    h.before_render()
    tasks[0] = 0; h.tick(); now[0] = 31; h.tick()
    assert not any("level=2" in c for c in llm["calls"])


def test_busy_llm_is_aborted_after_the_wait(llm):
    llm["fail_wait"] = True
    h, *_ = make(llm)
    h.before_render()
    assert h.asleep and llm["calls"] == ["/sleep?level=1&mode=wait", "/sleep?level=1&mode=abort"]


def test_stays_asleep_while_rendering_and_during_the_idle_gap(llm):
    h, tasks, freed, now = make(llm, tasks=[1])
    h.before_render()
    now[0] = 500; assert not h.tick()
    tasks[0] = 0; assert not h.tick()
    now[0] = 529; assert not h.tick()
    assert h.asleep and not freed and "/wake_up" not in llm["calls"]


def test_wakes_after_idle_and_frees_comfy_vram_first(llm):
    order = []
    h = Handoff(llm["base"], lambda: 0, lambda: order.append(list(llm["calls"])), idle_s=30, wait_s=2, clock=lambda: clock[0])
    clock = [0.0]
    h.before_render(); h.tick(); clock[0] = 31
    assert h.tick() and not h.asleep
    assert "/wake_up" not in order[0] and llm["calls"][-1] == "/wake_up"


def test_a_new_job_resets_the_idle_timer(llm):
    h, tasks, _, now = make(llm)
    h.before_render(); h.tick()
    now[0] = 20; h.before_render()
    now[0] = 45; assert not h.tick()
    now[0] = 80; assert h.tick()


def test_a_down_llm_never_stops_a_render():
    h = Handoff("http://127.0.0.1:9", lambda: 0, lambda: None, wait_s=1)
    h.before_render()
    assert not h.asleep


def test_adopts_an_llm_left_asleep(llm):
    llm["sleeping"] = True
    h, _, _, now = make(llm)
    h.adopt()
    assert h.asleep
    h.tick(); now[0] = 31
    assert h.tick() and not llm["sleeping"]


def test_failed_wake_retries(llm):
    h, _, freed, now = make(llm)
    h.before_render(); h.tick(); now[0] = 31
    h.base = "http://127.0.0.1:9"
    assert not h.tick() and h.asleep
    h.base = llm["base"]
    assert h.tick() and not h.asleep
