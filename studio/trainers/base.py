"""What every external trainer does: find itself, start a process, follow its log, stop it by exact pid, resume it, hand back the finished file."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path


def settings_file() -> Path:
    return Path(os.environ.get("STUDIO_TRAIN_DIR") or Path.home() / ".local" / "share" / "parametric-studio" / "train") / "trainers.json"


def trainer_paths(name: str) -> dict:
    """Where a trainer lives on this machine: env first (STUDIO_TRAINER_<NAME>_DIR and _PYTHON), then trainers.json in the Train data folder."""
    key = name.upper().replace("-", "_")
    out = {}
    try: out = (json.loads(settings_file().read_text()).get(name) or {})
    except (OSError, ValueError): pass
    for field, env in (("dir", f"STUDIO_TRAINER_{key}_DIR"), ("python", f"STUDIO_TRAINER_{key}_PYTHON")):
        if os.environ.get(env): out[field] = os.environ[env]
    if os.environ.get(f"STUDIO_TRAINER_{key}_FILES"): out["files"] = json.loads(os.environ[f"STUDIO_TRAINER_{key}_FILES"])
    return out


def proc_start_ticks(pid: int) -> str | None:
    """The kernel's start time for a pid, so a recycled pid is never signalled."""
    try: return open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError): return None


class ExternalTrainer:
    name = "external"

    # ---- to fill in
    def missing_install(self) -> list[str]: raise NotImplementedError
    def check(self, base: dict, info) -> tuple[str | None, list[str]]: raise NotImplementedError
    def command(self, job: dict, base: dict) -> list[str]: raise NotImplementedError
    def write_config(self, job: dict, base: dict, info) -> None: raise NotImplementedError
    def preview(self, base: dict, settings: dict) -> str: raise NotImplementedError
    def parse_log(self, text: str) -> list: raise NotImplementedError
    def list_samples(self, job: dict) -> list[dict]: return []
    def list_checkpoints(self, job: dict) -> list[str]: return []
    def result(self, job: dict) -> Path | None: raise NotImplementedError

    # ---- the same for all
    def env(self, job: dict) -> dict:
        return {**os.environ, "PYTHONUNBUFFERED": "1", "HF_HUB_DISABLE_TELEMETRY": "1", "DISABLE_TELEMETRY": "YES"}

    def cwd(self) -> str | None:
        return trainer_paths(self.name).get("dir")

    def spawn(self, job: dict, base: dict) -> None:
        """Starts in its own session, so stopping it takes its children and nothing else. STUDIO_TRAIN_WRAP puts a command in front, for a machine that shares its GPU through a queue: {key} and {peak} are filled in."""
        run = Path(job["run_dir"])
        log = run / "train.log"
        wrap = os.environ.get("STUDIO_TRAIN_WRAP", "").split()
        wrap = [w.replace("{key}", job["base"]).replace("{peak}", str(base.get("peak_gib") or 24)) for w in wrap]
        out = open(log, "ab")
        p = subprocess.Popen(wrap + self.command(job, base), cwd=getattr(self, "_cwd", None) or self.cwd(), env=self.env(job), stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        out.close()
        job["proc"] = {"pid": p.pid, "ticks": proc_start_ticks(p.pid), "log": str(log)}
        job["pid"] = p.pid
        self._child = p

    def start(self, job: dict, base: dict, info) -> None:
        self.write_config(job, base, info)
        self.spawn(job, base)

    def resume(self, job: dict) -> None:
        from studio.train_bases import BASES
        self.spawn(job, BASES[job["base"]])

    def alive(self, job: dict) -> bool:
        proc = job.get("proc") or {}
        if not proc.get("pid"): return False
        child = getattr(self, "_child", None)
        if child is not None and child.pid == proc["pid"]: child.poll()       # reaps it, so a finished child does not linger as a zombie
        try:
            if open(f"/proc/{proc['pid']}/stat").read().rsplit(")", 1)[1].split()[0] == "Z": return False
        except OSError: return False
        return proc_start_ticks(proc["pid"]) == proc.get("ticks")

    def stop(self, job: dict) -> None:
        """SIGINT to this run's own process group, then SIGTERM if it is still there after a while. Exact pid, checked against its start time."""
        if not self.alive(job): return
        pid = job["proc"]["pid"]
        try: os.killpg(pid, signal.SIGINT)
        except OSError: return
        job["stop_sent"] = time.time()

    def follow(self, job: dict) -> bool:
        """Reads the log and the run folder into the job. True while the process lives."""
        proc = job.get("proc") or {}
        try: text = Path(proc.get("log", "")).read_text(encoding="utf-8", errors="replace")
        except OSError: text = ""
        last = job["curve"][-1][0] if job["curve"] else -1
        now = time.time()
        for step, total, loss in self.parse_log(text):
            if step <= last: continue
            job["curve"].append([step, loss, now]); last = step
            job["curve_source"] = "trainer log"
            if loss != loss or abs(loss) == float("inf"): job["loss_nan"] = True
        job["samples"] = self.list_samples(job)
        job["checkpoints"] = self.list_checkpoints(job)
        alive = self.alive(job)
        if alive and job.get("stop_sent") and now - job["stop_sent"] > 60:
            try: os.killpg(job["proc"]["pid"], signal.SIGTERM)
            except OSError: pass
        return alive

    def last_error(self, job: dict) -> str | None:
        try: lines = Path(job["proc"]["log"]).read_text(encoding="utf-8", errors="replace").replace("\r", "\n").splitlines()
        except (OSError, KeyError): return None
        useful = [l.strip() for l in lines if l.strip() and "%|" not in l]
        return " ".join(useful[-3:])[-600:] or None
