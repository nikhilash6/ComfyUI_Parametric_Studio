"""Headless Blender runner. One call = `blender -b --factory-startup -t N --python blender_scripts/<script> -- --cycles-device CPU <work>/<name>.json`,
its output in <work>/<name>.log. The script prints one `PPWK {json}` line: the result. A run past its timeout, or a cancelled build, is killed
through its OWN process group by pid (SIGTERM, then SIGKILL), never by name.

CPU is the default and it is forced three ways: CUDA_VISIBLE_DEVICES is empty for the process, Cycles is told --cycles-device CPU, and the scripts
set the scene's device and the add-on's compute device. EEVEE needs the GPU and only runs when STUDIO_WORLDKIT_GPU=1, there is room above the VRAM
floor and it is not a CPU-only step; it falls back to CPU Cycles when it fails. Scripts install nothing (--factory-startup)."""
from __future__ import annotations

import contextlib
import contextvars
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from psn import paths

SCRIPTS = Path(__file__).with_name("blender_scripts")
TAG = "PPWK "
DEFAULT_TIMEOUT_S = 1800.0
KILL_GRACE_S = 10.0
POLL_S = 1.0
#: Measured on real place scenes in the earlier studio: 1.21 GiB per-process peak at 720x1280, plus a 1 GiB margin, rounded up.
EEVEE_PEAK_GIB = 2.5


def blender_path() -> str:
    return paths.setting("STUDIO_BLENDER", default="/snap/bin/blender")


def gpu_allowed() -> bool:
    return paths.setting("STUDIO_WORLDKIT_GPU") == "1"


def threads() -> int:
    """Half the cores unless told otherwise: renders run beside everything else on the machine."""
    try:
        return max(1, int(paths.setting("STUDIO_WORLDKIT_THREADS")))
    except ValueError:
        return max(2, (os.cpu_count() or 4) // 2)


_CPU_ONLY = contextvars.ContextVar("worldkit_blender_cpu_only", default=False)
_CANCEL = contextvars.ContextVar("worldkit_blender_cancel", default=None)


@contextlib.contextmanager
def cpu_only():
    """A CPU-lane step (cleanup, assemble): inside this scope run(gpu=True) and render() raise before any process starts."""
    token = _CPU_ONLY.set(True)
    try:
        yield
    finally:
        _CPU_ONLY.reset(token)


@contextlib.contextmanager
def cancel_scope(event):
    """Blender runs inside this scope die when `event` (a threading.Event) is set."""
    token = _CANCEL.set(event)
    try:
        yield
    finally:
        _CANCEL.reset(token)


class BlenderFailed(RuntimeError):
    """Blender exited non-zero, timed out (and was killed), or printed no PPWK result line."""


class Cancelled(RuntimeError):
    """The build was cancelled while Blender ran."""


def command(script: str, payload_file: Path, *, factory_startup: bool = True, gpu: bool = False) -> list[str]:
    path = SCRIPTS / script
    if not path.is_file():
        raise BlenderFailed(f"no Blender script {script} in {SCRIPTS}")
    cmd = [blender_path(), "-b"]
    if factory_startup:
        cmd.append("--factory-startup")
    cmd += ["-t", str(threads()), "--python", str(path), "--"]
    if not gpu:
        cmd += ["--cycles-device", "CPU"]
    return [*cmd, str(payload_file)]


def environment(gpu: bool = False) -> dict:
    env = dict(os.environ)
    if not gpu:
        env["CUDA_VISIBLE_DEVICES"] = ""
    return env


def result_line(text: str) -> dict | None:
    for line in reversed(text.splitlines()):
        if line.startswith(TAG):
            try:
                res = json.loads(line[len(TAG):])
            except ValueError:
                return None
            return res if isinstance(res, dict) else None
    return None


def vram_problem(peak_gib: float, *, free=None) -> str:
    """"" when the card can take a GPU render of `peak_gib` above the floor now; else why not."""
    from psn import instances as I
    try:
        f = (free or I.free_vram_gb)()
    except (OSError, ValueError, IndexError, subprocess.SubprocessError) as exc:
        return f"could not read the GPU's free memory ({type(exc).__name__}: {exc})"
    need = peak_gib + I.FLOOR_GB
    if f is None or f < need:
        return f"only {f if f is not None else 0:.1f} GB free; a Blender GPU render needs {need:.1f} GB ({peak_gib} peak + {I.FLOOR_GB} floor)"
    return ""


def _kill(proc, killpg) -> None:
    for sig, grace in ((signal.SIGTERM, KILL_GRACE_S), (signal.SIGKILL, 5.0)):
        try:
            killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=grace)
            return
        except subprocess.TimeoutExpired:
            continue


def _tail(text: str, n: int = 6) -> str:
    return " | ".join(text.strip().splitlines()[-n:])[-600:]


def _wait(proc, killpg, fh, timeout, poll_s, monotonic, name, logfile) -> int:
    """Poll the process about once a second, so a cancelled build or the timeout kills its process group."""
    deadline = monotonic() + timeout
    while True:
        ev = _CANCEL.get()
        if ev is not None and ev.is_set():
            _kill(proc, killpg)
            fh.write("\n[cancelled]\n")
            raise Cancelled(f"Blender {name} was cancelled")
        left = deadline - monotonic()
        if left <= 0:
            _kill(proc, killpg)
            fh.write(f"\n[killed after {timeout:.0f} s]\n")
            raise BlenderFailed(f"Blender {name} timed out after {timeout:.0f} s and was killed; log {logfile}")
        try:
            return proc.wait(timeout=min(poll_s, left))
        except subprocess.TimeoutExpired:
            continue


def run(script: str, payload: dict, *, work: Path, name: str = "", timeout: float = DEFAULT_TIMEOUT_S,
        factory_startup: bool = True, gpu: bool = False, popen=None, killpg=None, poll_s: float = POLL_S,
        monotonic=None) -> dict:
    if gpu and _CPU_ONLY.get():
        raise RuntimeError(f"Blender {name or script} asked for the GPU inside a CPU-only step")
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    name = name or Path(script).stem
    pfile, log = work / f"{name}.json", work / f"{name}.log"
    pfile.write_text(json.dumps(payload), encoding="utf-8")
    cmd = command(script, pfile, factory_startup=factory_startup, gpu=gpu)
    proc = None
    popen, killpg = popen or subprocess.Popen, killpg or os.killpg
    try:
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("$ " + " ".join(cmd) + "\n")
            fh.flush()
            proc = popen(cmd, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True, env=environment(gpu))
            rc = _wait(proc, killpg, fh, timeout, poll_s, monotonic or time.monotonic, name, log)
    finally:
        if proc is not None and proc.poll() is None:           # any exit path: never leave a live Blender behind
            _kill(proc, killpg)
    text = log.read_text(encoding="utf-8", errors="replace")
    res = result_line(text)
    if rc != 0 or res is None or not res.get("ok"):
        why = (res or {}).get("error") or _tail(text)
        raise BlenderFailed(f"Blender {name} exited {rc}: {why}; log {log}"[:1500])
    return res


def render(script: str, payload: dict, *, work: Path, name: str = "", timeout: float = DEFAULT_TIMEOUT_S, vram=None,
           **kw) -> dict:
    """CPU Cycles, unless the GPU is switched on and has room: then EEVEE first and CPU Cycles if EEVEE fails."""
    if _CPU_ONLY.get():
        raise RuntimeError("Blender render() may use the GPU; a CPU-only step (cleanup, assemble) never renders")
    base = name or Path(script).stem
    note = ""
    if gpu_allowed():
        why = (vram or vram_problem)(EEVEE_PEAK_GIB)
        if why:
            note = f"rendered on the CPU: {why}"
        else:
            try:
                res = run(script, {**payload, "engine": "eevee"}, work=work, name=f"{base}_eevee", timeout=timeout,
                          gpu=True, **kw)
                return {**res, "engine": "eevee"}
            except BlenderFailed as exc:
                note = f"EEVEE failed, rendered on the CPU (Cycles): {str(exc)[:300]}"
    res = run(script, {**payload, "engine": "cycles"}, work=work, name=f"{base}_cycles", timeout=timeout, gpu=False,
              **kw)
    return {**res, "engine": "cycles", **({"fallback_note": note} if note else {})}


def inspect(model, *, work: Path, **kw) -> dict:
    """The headless-Blender facts of one model (CPU, no render): {"loaded": True, "height_m", "dims_m", "bones", ...}."""
    return run("wk_inspect.py", {"model": str(model)}, work=work, name="inspect", timeout=300, gpu=False, **kw)["inspect"]
