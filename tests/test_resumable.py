"""Real sockets on loopback with a server that misbehaves on purpose. Nothing reaches the internet."""
import hashlib, http.server, os, socket, struct, sys, threading, time
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import install
from studio import resumable as R

BODY = os.urandom(3 << 20); SHA = hashlib.sha256(BODY).hexdigest()
def no_wait(_): pass

@pytest.fixture
def server():
    """serve(fault, times): the first `times` requests send half of what is left, then fail in the way `fault` says."""
    made = []
    def serve(fault="", times=1, status=None):
        state = {"left": times, "starts": [], "release": threading.Event()}
        class H(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            def log_message(self, *a): pass
            def do_GET(self):
                rng = self.headers.get("Range"); start = int(rng[6:-1]) if rng else 0; state["starts"].append(start)
                if status: self.send_response(status); self.send_header("Content-Length", "0"); self.end_headers(); return
                rest = BODY[start:]
                self.send_response(206 if start else 200); self.send_header("Content-Length", str(len(rest)))
                if start: self.send_header("Content-Range", f"bytes {start}-{len(BODY) - 1}/{len(BODY)}")
                self.end_headers()
                if state["left"] <= 0: self.wfile.write(rest); return
                state["left"] -= 1; self.wfile.write(rest[:len(rest) // 2]); self.wfile.flush()
                if fault == "close": self.connection.shutdown(socket.SHUT_RDWR); self.close_connection = True
                elif fault == "reset": self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)); self.connection.close(); self.close_connection = True
                elif fault == "stall": state["release"].wait(20); self.close_connection = True
        s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); s.daemon_threads = True; threading.Thread(target=s.serve_forever, daemon=True).start(); made.append((s, state))
        return f"http://127.0.0.1:{s.server_port}/f", state
    yield serve
    for s, state in made: state["release"].set(); s.shutdown()

@pytest.mark.parametrize("fault", ["close", "reset"])
def test_a_dropped_connection_carries_on_from_the_bytes_on_disk(server, tmp_path, fault):
    url, st = server(fault); dest = tmp_path / "f.bin"
    assert install.download_file(url, dest, SHA, sleep=no_wait)
    assert dest.read_bytes() == BODY and len(st["starts"]) == 2 and st["starts"][0] == 0
    if fault == "close": assert st["starts"][1] > 0      # a reset may throw away what the client had not read yet

def test_a_stalled_connection_times_out_and_carries_on(server, tmp_path):
    url, st = server("stall"); dest = tmp_path / "f.bin"; t = time.time()
    assert install.download_file(url, dest, SHA, opener=R.default_opener(timeout=0.5), sleep=no_wait)
    assert dest.read_bytes() == BODY and st["starts"][1] > 0 and time.time() - t < 15

def test_giving_up_keeps_the_bytes_for_the_next_run(server, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(R, "TRIES", 3); monkeypatch.setattr(R.fetch_partial, "__defaults__", tuple(3 if d == 12 else d for d in R.fetch_partial.__defaults__))
    url, st = server("close", times=99); dest = tmp_path / "f.bin"
    assert not install.download_file(url, dest, SHA, sleep=no_wait)
    part = tmp_path / "f.bin.part"; assert part.stat().st_size > 0 and not dest.exists() and "run the same command again" in capsys.readouterr().out
    st["left"] = 0
    assert install.download_file(url, dest, SHA, sleep=no_wait) and dest.read_bytes() == BODY and not part.exists()

def test_a_refusal_is_not_retried(server, tmp_path):
    url, st = server(status=403); got = []
    with pytest.raises(R.Refused) as e: R.fetch_partial(url, tmp_path / "f.part", sleep=got.append)
    assert e.value.status == 403 and not got and len(st["starts"]) == 1

def test_a_server_error_is_retried(tmp_path):
    import urllib.error
    calls = []
    class Ok:
        status, headers = 200, {}
        def __init__(self): self.d = [b"abc", b""]
        def read(self, n): return self.d.pop(0)
    def opener(req):
        calls.append(1)
        if len(calls) == 1: raise urllib.error.HTTPError("http://x", 503, "busy", {}, None)
        return Ok()
    waits = []
    assert R.fetch_partial("http://x", tmp_path / "f.part", opener=opener, sleep=waits.append).read_bytes() == b"abc" and waits == [5]

def test_cancel_works_while_bytes_flow_and_keeps_them(server, tmp_path):
    url, st = server(times=0); seen = []
    with pytest.raises(R.Cancelled): R.fetch_partial(url, tmp_path / "f.part", progress=lambda n, reset=False: seen.append(n), cancelled=lambda: len(seen) > 2)
    size = (tmp_path / "f.part").stat().st_size; assert 0 < size < len(BODY)
    assert R.fetch_partial(url, tmp_path / "f.part").read_bytes() == BODY and st["starts"][-1] == size

def test_progress_reports_every_chunk_from_the_resume_point(server, tmp_path):
    url, _ = server(times=0); part = tmp_path / "f.part"; part.write_bytes(BODY[:1000]); seen = []
    R.fetch_partial(url, part, progress=lambda n, reset=False: seen.append((n, reset)))
    assert seen[0] == (1000, True) and sum(n for n, r in seen[1:]) == len(BODY) - 1000 and len(seen) > 2

def test_a_full_disk_stops_at_once(tmp_path):
    import errno
    def opener(req): raise OSError(errno.ENOSPC, "No space left on device")
    waits = []
    with pytest.raises(OSError): R.fetch_partial("http://x", tmp_path / "f.part", opener=opener, sleep=waits.append)
    assert not waits

def test_the_token_goes_only_to_huggingface():
    import urllib.request
    for host, kept in (("https://cdn-lfs.huggingface.co/a", True), ("https://huggingface.co/a", True), ("https://cdn.example.net/a", False), ("https://evilhuggingface.co/a", False)):
        req = urllib.request.Request("https://huggingface.co/a", headers={"Authorization": "Bearer t"})
        assert (R.DropTokenOnRedirect().redirect_request(req, None, 302, "x", {}, host).get_header("Authorization") is not None) is kept

def test_the_studio_announces_itself_after_comfyui_is_up(capsys):
    pytest.importorskip("fastapi"); from studio import server as S
    states = iter([False, True, True]); S.announce("http://127.0.0.1:8310", wait_s=10, up=lambda: next(states), sleep=no_wait)
    out = capsys.readouterr().out; assert "Open http://127.0.0.1:8310" in out and "ComfyUI is ready" in out
    S.announce("http://127.0.0.1:8310", wait_s=4, up=lambda: False, sleep=no_wait); assert "not answering" in capsys.readouterr().out

def test_blender_is_looked_for_on_the_path_and_the_message_says_how_to_get_it(monkeypatch):
    pytest.importorskip("fastapi"); from studio.worldkit import blender as B, capabilities as C
    monkeypatch.delenv("STUDIO_BLENDER", raising=False); monkeypatch.setattr(B.paths, "setting", lambda k, default=None: default)
    monkeypatch.setattr(B.shutil, "which", lambda n: "/opt/b/blender" if n == "blender" else None); assert B.blender_path() == "/opt/b/blender"
    monkeypatch.setattr(B.shutil, "which", lambda n: None); monkeypatch.setattr(C.Path, "exists", lambda self: False)
    why = C.blender_problem(); assert "not installed" in why and "STUDIO_BLENDER" in why and "/snap" not in why.replace("snap install", "")
