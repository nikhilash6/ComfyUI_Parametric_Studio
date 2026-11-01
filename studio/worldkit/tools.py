"""Third-party 3D tools, each in its own folder and its own virtual environment, run as a subprocess with a timeout and killed through their own process group by pid. Nothing from
those folders is imported into the studio. Each runner names its tool's folder through capabilities.tool_home, and writes into the step's work folder.
GPU tools ask for room above the VRAM floor first and never evict anything."""
from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

from studio.worldkit import capabilities as C
from studio.worldkit import blender as B
from studio.worldkit.steps import StepError

PEAK_GB = {"sam3d_objects": 32.0, "skintokens": 6.0, "kimodo": 17.0}
TIMEOUT_S = {"sam3d_objects": 1800, "skintokens": 900, "autoremesher": 1800, "kimodo": 2400, "retarget": 900}
AR_LODS = (20000, 5000, 1500)


def require(key: str) -> None:
    n = C.need(key)
    if n["state"] != "ready":
        raise StepError(n["message"])


def vram_gate(tool: str, *, free=None) -> None:
    why = B.vram_problem(PEAK_GB[tool], free=free)
    if why:
        raise StepError(f"{tool}: {why}. Nothing was evicted; press Retry when there is room.")


def call(cmd: list, log: Path, timeout: int, *, cwd: Path | None = None, cpu: bool = False, popen=None, killpg=None) -> int:
    popen, killpg = popen or subprocess.Popen, killpg or os.killpg
    log.parent.mkdir(parents=True, exist_ok=True)
    env = B.environment(not cpu)
    with open(log, "w", encoding="utf-8") as fh:
        proc = popen([str(c) for c in cmd], stdout=fh, stderr=subprocess.STDOUT, start_new_session=True, env=env, cwd=str(cwd) if cwd else None)
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=10)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            raise StepError(f"{Path(cmd[0]).name} ran past {timeout} s and was killed; log {log}") from None
        finally:
            if proc.poll() is None:
                try:
                    killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


def _tail(log: Path) -> str:
    try:
        return " | ".join(log.read_text(errors="replace").strip().splitlines()[-5:])[-500:]
    except OSError:
        return ""


def _made(path: Path, rc: int, tool: str, log: Path) -> Path:
    """Some tools print an error and still exit 0: the file decides."""
    if rc != 0 or not path.is_file() or path.stat().st_size == 0:
        raise StepError(f"{tool} exited {rc} without {path.name}; log {log}: {_tail(log)}"[:900])
    return path


def _alpha_mask(image: Path, dest: Path) -> Path:
    from PIL import Image
    with Image.open(image) as im:
        if im.mode not in ("RGBA", "LA"):
            raise StepError("SAM 3D needs to know which object to build: the picture has no cut-out")
        im.getchannel("A").point(lambda v: 255 if v > 127 else 0).save(dest)
    return dest


def sam3d_objects(image, work: Path, *, seed: int = 42, run=None) -> Path:
    """One RGBA picture -> one GLB."""
    require("sam3d_objects")
    vram_gate("sam3d_objects")
    work = Path(work); out = work / "sam3d"; out.mkdir(parents=True, exist_ok=True)
    mask = _alpha_mask(Path(image), work / "mask.png"); log = work / "sam3d.log"
    runner = C.tool_home("sam3d_objects") / "run_sam3d.sh"
    rc = (run or call)([runner, "--image", image, "--mask", mask, "--out-dir", out, "--name", "object", "--seed", seed], log, TIMEOUT_S["sam3d_objects"])
    return _made(out / "object.glb", rc, "SAM 3D Objects", log)


def skintokens(mesh, work: Path, *, run=None) -> Path:
    """A finished mesh -> a rigged GLB, texture and scale kept."""
    require("skintokens")
    vram_gate("skintokens")
    work = Path(work); work.mkdir(parents=True, exist_ok=True); out = work / "rigged.glb"; log = work / "skintokens.log"
    rc = (run or call)([C.tool_home("skintokens") / "run_skintokens.sh", "--input", mesh, "--output", out, "--use_transfer"], log, TIMEOUT_S["skintokens"])
    return _made(out, rc, "SkinTokens", log)


def autoremesher(mesh, work: Path, *, run=None) -> Path:
    """Quad LODs, CPU. Geometry only: UVs and colour are dropped. Returns LOD 0's GLB."""
    require("autoremesher")
    work = Path(work); out = work / "remesh"; out.mkdir(parents=True, exist_ok=True); log = work / "autoremesher.log"
    staged = out / f"model{Path(mesh).suffix.lower()}"
    staged.write_bytes(Path(mesh).read_bytes())
    rc = (run or call)([C.tool_home("autoremesher") / "run_autoremesher.sh", staged, out, *AR_LODS], log, TIMEOUT_S["autoremesher"], cpu=True)
    return _made(out / f"model_lod0_{AR_LODS[0]}q.glb", rc, "AutoRemesher", log)


def kimodo(text: str, work: Path, *, seconds: int = 5, seed: int = 7, run=None) -> Path:
    """A motion description -> a BVH."""
    require("kimodo")
    vram_gate("kimodo")
    work = Path(work); work.mkdir(parents=True, exist_ok=True); stem = work / "motion"; log = work / "kimodo.log"
    rc = (run or call)([C.tool_home("kimodo") / "run_kimodo.sh", " ".join(str(text).split()), "--output", stem, "--duration", seconds, "--bvh", "--seed", seed], log, TIMEOUT_S["kimodo"])
    return _made(stem.with_suffix(".bvh"), rc, "Kimodo", log)


def _src_map(motion) -> str:
    """The retarget script's source map: the SOMA77 slot map for a Kimodo BVH, otherwise it detects the rig itself."""
    try:
        joints = {ln.split()[1] for ln in Path(motion).read_text(errors="replace").splitlines() if ln.strip().startswith(("ROOT", "JOINT")) and len(ln.split()) > 1}
    except OSError:
        joints = set()
    return str(Path(__file__).with_name("data") / "soma77_slots.json") if {"LeftShin", "RightShin", "Spine1", "Chest"} <= joints else "detect"


def retarget(motion, target, work: Path, *, run=None) -> Path:
    """A BVH onto a rigged character -> an FBX of the clip on that rig (CPU, Blender, no render)."""
    require("retarget")
    work = Path(work); work.mkdir(parents=True, exist_ok=True); out = work / "clip.fbx"; log = work / "retarget.log"; home = C.tool_home("retarget")
    cmd = [B.blender_path(), "-b", "--python", home / "retarget.py", "--", "--src", motion, "--src-map", _src_map(motion), "--report", work / "report.json", "--target", target, "--preset", "auto", "--out-fbx", out]
    rc = (run or call)(cmd, log, TIMEOUT_S["retarget"], cpu=True)
    return _made(out, rc, "Retarget", log)
