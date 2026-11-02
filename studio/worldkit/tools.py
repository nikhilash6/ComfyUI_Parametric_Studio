"""Third-party 3D tools, each in its own folder and its own virtual environment, run as a subprocess with a timeout and killed through their own process group by pid. Nothing from
those folders is imported into the studio. Each runner names its tool's folder through capabilities.tool_home, and writes into the step's work folder.
GPU tools ask for room above the VRAM floor first and never evict anything."""
from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path

from psn import paths
from studio.worldkit import capabilities as C
from studio.worldkit import blender as B
from studio.worldkit.steps import StepError

PEAK_GB = {"anigen": 11.0, "sam3d_objects": 32.0, "skintokens": 6.0, "unirig": 8.0, "kimodo": 17.0, "kimodo_cpu_text": 3.0}
TIMEOUT_S = {"anigen": 1500, "sam3d_objects": 1800, "skintokens": 900, "unirig": 1500, "autoremesher": 1800, "kimodo": 2400, "retarget": 900}
AR_LODS = (20000, 5000, 1500)


def require(key: str) -> None:
    n = C.need(key)
    if n["state"] != "ready":
        raise StepError(n["message"])


def vram_gate(tool: str, *, free=None) -> None:
    why = B.vram_problem(PEAK_GB[tool], free=free)
    if why:
        raise StepError(f"{tool}: {why}. Nothing was evicted; press Retry when there is room.")


def call(cmd: list, log: Path, timeout: int, *, cwd: Path | None = None, cpu: bool = False, popen=None, killpg=None, env_extra: dict | None = None) -> int:
    popen, killpg = popen or subprocess.Popen, killpg or os.killpg
    log.parent.mkdir(parents=True, exist_ok=True)
    env = {**B.environment(not cpu), **(env_extra or {})}
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


def _borrowed_rtree(work: Path) -> list:
    """AniGen's venv has no rtree, which its trimesh step needs, and nothing here pips into a venv: lend it this Python's copy, alone, for one run. -> an env prefix for the command, or nothing when the studio has none either."""
    try:
        import rtree
    except (ImportError, OSError):
        return []
    pkg = Path(rtree.__file__).parent; libs = sorted((pkg.parent / "rtree.libs").glob("libspatialindex*.so*"))
    if not libs:
        return []
    only = Path(work) / "rtree_only"; only.mkdir(parents=True, exist_ok=True)
    if not (only / "rtree").exists():
        (only / "rtree").symlink_to(pkg)
    return ["/usr/bin/env", f"PYTHONPATH={only}", f"SPATIALINDEX_C_LIBRARY={libs[0]}"]


def anigen(image, work: Path, *, seed: int = 42, run=None) -> Path:
    """One picture -> one GLB with a skeleton and skin weights."""
    require("anigen")
    vram_gate("anigen")
    work = Path(work); out = work / "anigen"; out.mkdir(parents=True, exist_ok=True); log = work / "anigen.log"; image = Path(image)
    rc = (run or call)([*_borrowed_rtree(work), C.tool_home("anigen") / "run_anigen.sh", "--image_path", image, "--output_dir", out, "--seed", seed], log, TIMEOUT_S["anigen"])
    return _made(out / image.stem / "mesh.glb", rc, "AniGen", log)


def skintokens(mesh, work: Path, *, run=None) -> Path:
    """A finished mesh -> a rigged GLB, texture and scale kept. The voxel skin post-process keeps a bone's pull inside its own limb, so a raised arm stops dragging the jacket with it."""
    require("skintokens")
    vram_gate("skintokens")
    work = Path(work); work.mkdir(parents=True, exist_ok=True); out = work / "rigged.glb"; log = work / "skintokens.log"
    rc = (run or call)([C.tool_home("skintokens") / "run_skintokens.sh", "--input", mesh, "--output", out, "--use_transfer", "--use_postprocess"], log, TIMEOUT_S["skintokens"])
    return _made(out, rc, "SkinTokens", log)


def unirig(mesh, work: Path, *, run=None) -> Path:
    """A finished mesh -> a rigged GLB with its own skeleton and skin. The Blender steps run in the tool's own Blender route."""
    require("unirig")
    vram_gate("unirig")
    home = C.tool_home("unirig"); work = Path(work); work.mkdir(parents=True, exist_ok=True); out = work / "rigged.glb"; log = work / "unirig.log"
    rc = (run or call)([home / ".venv" / "bin" / "python", home / "run_unirig.py", "--input", mesh, "--output", out, "--work", work / "steps"], log, TIMEOUT_S["unirig"])
    return _made(out, rc, "UniRig", log)


def autoremesher(mesh, work: Path, *, run=None) -> Path:
    """Quad LODs, CPU. Geometry only: UVs and colour are dropped. Returns LOD 0's GLB."""
    require("autoremesher")
    work = Path(work); out = work / "remesh"; out.mkdir(parents=True, exist_ok=True); log = work / "autoremesher.log"
    staged = out / f"model{Path(mesh).suffix.lower()}"
    staged.write_bytes(Path(mesh).read_bytes())
    rc = (run or call)([C.tool_home("autoremesher") / "run_autoremesher.sh", staged, out, *AR_LODS], log, TIMEOUT_S["autoremesher"], cpu=True)
    return _made(out / f"model_lod0_{AR_LODS[0]}q.glb", rc, "AutoRemesher", log)


def kimodo(text: str, work: Path, *, seconds: int = 5, seed: int = 7, run=None, free=None) -> Path:
    """A motion description -> a BVH. The text encoder runs on the CPU by default: about 2 GB on the card instead of 17 and 16 GB of RAM, measured here at 131 s for a 5 s clip. STUDIO_KIMODO_TEXT_DEVICE=cuda puts it back on the card when there is room for it."""
    require("kimodo")
    device = paths.setting("STUDIO_KIMODO_TEXT_DEVICE", default="cpu")
    vram_gate("kimodo" if device != "cpu" else "kimodo_cpu_text", free=free)
    work = Path(work); work.mkdir(parents=True, exist_ok=True); stem = work / "motion"; log = work / "kimodo.log"
    rc = (run or call)([C.tool_home("kimodo") / "run_kimodo.sh", " ".join(str(text).split()), "--output", stem, "--duration", seconds, "--bvh", "--seed", seed], log, TIMEOUT_S["kimodo"], env_extra={"TEXT_ENCODER_DEVICE": device})
    return _made(stem.with_suffix(".bvh"), rc, "Kimodo", log)


def _src_map(motion) -> str:
    """The retarget script's source map: the SOMA77 slot map for a Kimodo BVH, otherwise it detects the rig itself."""
    try:
        joints = {ln.split()[1] for ln in Path(motion).read_text(errors="replace").splitlines() if ln.strip().startswith(("ROOT", "JOINT")) and len(ln.split()) > 1}
    except OSError:
        joints = set()
    return str(Path(__file__).with_name("data") / "soma77_slots.json") if {"LeftShin", "RightShin", "Spine1", "Chest"} <= joints else "detect"


def retarget(motion, target, work: Path, *, run=None) -> Path:
    """A BVH onto a rigged character -> an FBX of the clip on that rig (CPU, Blender, no render). Kimodo's SOMA BVH is fitted from joint positions (wk_fit_motion.py); any other goes through the retarget tool."""
    require("retarget")
    work = Path(work); work.mkdir(parents=True, exist_ok=True); out = work / "clip.fbx"; log = work / "retarget.log"; home = C.tool_home("retarget")
    from studio.worldkit import mhr_bvh
    try:
        mhr = mhr_bvh.is_mhr(Path(motion).read_text(errors="replace"))
    except OSError:
        mhr = False
    if mhr:                                    # SAM 3D Body's numbered joints, renamed to the SOMA names the fit reads
        motion = mhr_bvh.rename(motion, work / "motion_soma.bvh")
    if _src_map(motion) != "detect":
        pfile = work / "fit.json"
        pfile.write_text(json.dumps({"motion": str(motion), "rig": str(target), "out": str(out)}), encoding="utf-8")
        return _made(out, (run or call)(B.command("wk_fit_motion.py", pfile, factory_startup=True, gpu=False), log, TIMEOUT_S["retarget"], cpu=True), "Motion fit", log)
    cmd = [B.blender_path(), "-b", "--python", home / "retarget.py", "--", "--src", motion, "--src-map", _src_map(motion), "--report", work / "report.json", "--target", target, "--preset", "auto", "--out-fbx", out]
    rc = (run or call)(cmd, log, TIMEOUT_S["retarget"], cpu=True)
    return _made(out, rc, "Retarget", log)
