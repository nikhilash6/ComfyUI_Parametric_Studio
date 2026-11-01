"""The Blender runner with a fake Popen: no Blender, no GPU."""
import itertools
import json
import signal
import subprocess
import threading

import pytest

from studio.worldkit import blender as B


class _Proc:
    def __init__(self, rc, hang, pid):
        self.rc, self.hang, self.pid, self.killed = rc, hang, pid, []

    def wait(self, timeout=None):
        if self.hang and not self.killed:
            raise subprocess.TimeoutExpired("blender", timeout)
        return self.rc

    def poll(self):
        return None if self.hang and not self.killed else self.rc


class FakePopen:
    """Each call writes the next (text, rc, hang) into the log and returns a process stand-in."""
    def __init__(self, *runs):
        self.runs = list(runs) or [('PPWK {"ok": true, "n": 1}', 0, False)]
        self.calls, self.procs = [], []

    def __call__(self, cmd, stdout=None, stderr=None, start_new_session=False, env=None):
        text, rc, hang = self.runs[min(len(self.calls), len(self.runs) - 1)]
        with open(cmd[-1], encoding="utf-8") as fh:
            payload = json.load(fh)
        self.calls.append({"cmd": cmd, "start_new_session": start_new_session, "payload": payload, "env": env})
        stdout.write(text + "\n")
        stdout.flush()
        proc = _Proc(rc, hang, 4000 + len(self.calls))
        self.procs.append(proc)
        return proc


def _ok(_peak):
    return ""


def test_run_returns_the_result_line_and_keeps_payload_and_log(tmp_path):
    popen = FakePopen()
    res = B.run("wk_probe.py", {"engine": "cycles"}, work=tmp_path, name="probe", popen=popen)
    assert res == {"ok": True, "n": 1}
    call = popen.calls[0]
    assert call["start_new_session"] is True and call["payload"] == {"engine": "cycles"}
    assert call["cmd"][:3] == [B.blender_path(), "-b", "--factory-startup"]
    assert (tmp_path / "probe.log").read_text().startswith("$ ")


def test_cpu_is_forced_by_the_environment_and_the_command_and_threads_are_limited(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_THREADS", "6")
    popen = FakePopen()
    B.run("wk_probe.py", {}, work=tmp_path, popen=popen)
    call = popen.calls[0]
    assert call["env"]["CUDA_VISIBLE_DEVICES"] == ""
    cmd = call["cmd"]
    assert cmd[cmd.index("--cycles-device") + 1] == "CPU" and cmd[cmd.index("-t") + 1] == "6"
    assert cmd.index("--") < cmd.index("--cycles-device") and cmd[-1].endswith(".json")


def test_a_failed_run_names_the_error_and_the_log(tmp_path):
    popen = FakePopen(('PPWK {"ok": false, "error": "no mesh with faces"}', 1, False))
    with pytest.raises(B.BlenderFailed, match="no mesh with faces.*probe.log"):
        B.run("wk_probe.py", {}, work=tmp_path, name="probe", popen=popen)
    with pytest.raises(B.BlenderFailed, match="exited 0"):
        B.run("wk_probe.py", {}, work=tmp_path, name="probe2", popen=FakePopen(("no result line", 0, False)))


def test_an_unknown_script_is_refused(tmp_path):
    with pytest.raises(B.BlenderFailed, match="no Blender script"):
        B.run("nope.py", {}, work=tmp_path, popen=FakePopen())


def test_timeout_kills_the_process_group_by_pid_never_by_name(tmp_path):
    popen = FakePopen(("still working", 0, True))
    kills = []

    def killpg(pid, sig):
        kills.append((pid, sig))
        popen.procs[-1].killed.append(sig)

    with pytest.raises(B.BlenderFailed, match="timed out after 5 s and was killed"):
        B.run("wk_probe.py", {}, work=tmp_path, name="hang", timeout=5, popen=popen, killpg=killpg,
              monotonic=itertools.count(0, 1).__next__)
    assert kills == [(popen.procs[-1].pid, signal.SIGTERM)]
    assert not any("pkill" in str(c) for c in popen.calls[0]["cmd"])
    assert "[killed after 5 s]" in (tmp_path / "hang.log").read_text()


def test_render_is_cpu_cycles_by_default_and_never_asks_about_the_card(tmp_path):
    popen = FakePopen(('PPWK {"ok": true}', 0, False))
    res = B.render("wk_probe.py", {"x": 1}, work=tmp_path, name="p", popen=popen, vram=lambda p: pytest.fail("no GPU question on the CPU path"))
    assert [c["payload"]["engine"] for c in popen.calls] == ["cycles"] and res["engine"] == "cycles" and "fallback_note" not in res
    assert popen.calls[0]["env"]["CUDA_VISIBLE_DEVICES"] == ""


def test_with_the_gpu_switched_on_eevee_falls_back_to_cycles(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_GPU", "1")
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    popen = FakePopen(('PPWK {"ok": false, "error": "no GPU context"}', 1, False), ('PPWK {"ok": true}', 0, False))
    res = B.render("wk_probe.py", {"x": 1}, work=tmp_path, name="probe", popen=popen, vram=_ok)
    assert [c["payload"]["engine"] for c in popen.calls] == ["eevee", "cycles"]
    assert res["engine"] == "cycles" and "no GPU context" in res["fallback_note"]
    assert "CUDA_VISIBLE_DEVICES" not in popen.calls[0]["env"] and popen.calls[1]["env"]["CUDA_VISIBLE_DEVICES"] == ""


def test_with_the_gpu_on_but_short_it_renders_on_the_cpu_and_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_WORLDKIT_GPU", "1")
    popen = FakePopen()
    res = B.render("wk_probe.py", {}, work=tmp_path, popen=popen, vram=lambda peak: "only 1.0 GB free")
    assert [c["payload"]["engine"] for c in popen.calls] == ["cycles"] and "only 1.0 GB free" in res["fallback_note"]


def test_vram_problem_keeps_the_floor():
    assert B.vram_problem(2.5, free=lambda: 50.0) == ""
    assert "floor" in B.vram_problem(2.5, free=lambda: 6.0)
    assert "could not read" in B.vram_problem(2.5, free=lambda: (_ for _ in ()).throw(OSError("no smi")))


def test_cancel_while_rendering_kills_the_group_and_logs(tmp_path):
    popen, kills, ev = FakePopen(("rendering", 0, True)), [], threading.Event()

    def killpg(pid, sig):
        kills.append((pid, sig))
        popen.procs[-1].killed.append(sig)

    ticks = itertools.count(1)

    def clock():
        if next(ticks) > 3:
            ev.set()
        return 0.0

    with B.cancel_scope(ev), pytest.raises(B.Cancelled):
        B.run("wk_probe.py", {}, work=tmp_path, name="c", popen=popen, killpg=killpg, timeout=9999, monotonic=clock)
    assert kills == [(popen.procs[-1].pid, signal.SIGTERM)]
    assert "[cancelled]" in (tmp_path / "c.log").read_text()


def test_an_error_mid_run_kills_a_live_blender(tmp_path):
    popen, events = FakePopen(("rendering", 0, True)), []

    def killpg(pid, sig):
        events.append("kill")
        popen.procs[-1].killed.append(sig)

    def boom():
        raise OSError("disk full")

    with pytest.raises(OSError):
        B.run("wk_probe.py", {}, work=tmp_path, name="e", popen=popen, killpg=killpg, timeout=9999, monotonic=boom)
    assert events == ["kill"]


def test_a_gpu_run_inside_cpu_only_raises_before_any_process(tmp_path):
    popen = FakePopen()
    with B.cpu_only():
        with pytest.raises(RuntimeError, match="CPU-only"):
            B.run("wk_probe.py", {}, work=tmp_path, gpu=True, popen=popen)
        with pytest.raises(RuntimeError, match="never renders"):
            B.render("wk_probe.py", {}, work=tmp_path, popen=popen)
        assert B.run("wk_probe.py", {}, work=tmp_path, popen=popen)["ok"]
    assert len(popen.calls) == 1
