"""From checked spec, checked level and made assets to a real Godot project: copy the template and the one chosen kit, write the data, add the import settings. Then Godot itself imports it, parses every script, exports it for Linux and the web, and the play-test bot plays it."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

from psn import paths

TEMPLATE = Path(__file__).with_name("template")
VERSION = "4.7.2"
TEMPLATES_URL = f"https://github.com/godotengine/godot/releases/download/{VERSION}-stable/Godot_v{VERSION}-stable_export_templates.tpz"
SUMS_URL = f"https://github.com/godotengine/godot/releases/download/{VERSION}-stable/SHA512-SUMS.txt"
TEMPLATE_DIR_NAME = f"{VERSION}.stable"
FONT_NAME = "archivo-latin-wdth-normal.woff2"
LICENCE_TEXT = """About this game's licences

This game was assembled by Parametric Studio's Game Builder.

The code (core/, kits/, main.gd) comes from Parametric Studio and is AGPL-3.0. Godot Engine is MIT. The Archivo font is under the SIL Open Font License.
Every generated asset carries the licence of the model that made it. credits.json lists each asset, the model, the seed and that licence. Read those licences before you sell or publish this game: some limit commercial use, some need a name shown, and some exclude regions.
"""


class GodotError(RuntimeError):
    pass


def godot_path() -> str:
    """STUDIO_GODOT, or godot4 / godot on the PATH. "" when there is none."""
    want = paths.setting("STUDIO_GODOT") or ""
    if want and Path(os.path.expanduser(want)).is_file():
        return str(Path(os.path.expanduser(want)))
    return shutil.which("godot4") or shutil.which("godot") or ""


def templates_dir() -> Path:
    return Path(os.path.expanduser(paths.setting("STUDIO_GODOT_TEMPLATES", default=os.path.join("~", ".local", "share", "godot", "export_templates")))) / TEMPLATE_DIR_NAME


def templates_state() -> dict:
    d = templates_dir()
    have = {"web": (d / "web_nothreads_release.zip").is_file(), "linux": (d / "linux_release.x86_64").is_file()}
    return {"dir": "", **have, "ready": all(have.values())}


def install_templates(*, fetch=None, dest: Path | None = None, sums: str | None = None) -> dict:
    """Fetch the export templates from Godot's official release and check them against its published SHA-512 before anything is unpacked. Asked for on purpose: it's over a gigabyte. Web and Linux are all that's kept."""
    dest = Path(dest) if dest else templates_dir()
    fetch = fetch or _download
    work = dest.parent / "_download"
    work.mkdir(parents=True, exist_ok=True)
    tpz = work / Path(TEMPLATES_URL).name
    fetch(TEMPLATES_URL, tpz)
    sum_text = sums if sums is not None else _read_url(SUMS_URL)
    want = next((ln.split()[0] for ln in sum_text.splitlines() if ln.strip().endswith(tpz.name)), "")
    got = hashlib.sha512(tpz.read_bytes()).hexdigest()
    if not want or want.lower() != got:
        tpz.unlink(missing_ok=True)
        raise GodotError("the export templates don't match the SHA-512 Godot publishes, so they were deleted and not used")
    keep = ("templates/version.txt", "templates/web_nothreads_release.zip", "templates/web_nothreads_debug.zip", "templates/linux_release.x86_64", "templates/linux_debug.x86_64")
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(tpz) as z:
        for name in keep:
            if name in z.namelist():
                (dest / Path(name).name).write_bytes(z.read(name))
    tpz.unlink(missing_ok=True)
    return templates_state()


def _download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)


def _read_url(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


_TEX_IMPORT = """[remap]

importer="texture"
type="CompressedTexture2D"

[params]

compress/mode={mode}
compress/lossy_quality=0.8
mipmaps/generate={mips}
process/fix_alpha_border=true
detect_3d/compress_to=0
"""
_GLB_IMPORT = """[remap]

importer="scene"
importer_version=1
resource_type="PackedScene"

[params]

nodes/import_as_skeleton_bones=false
meshes/ensure_tangents=false
meshes/generate_lods=false
meshes/create_shadow_meshes=false
meshes/light_baking=0
animation/import=true
animation/fps=30
animation/trimming=false
gltf/naming_version=2
gltf/embedded_image_handling=2
"""


def font_source() -> Path:
    return Path(__file__).resolve().parent.parent / "web" / "vendor" / "fonts" / FONT_NAME


def _safe_text(s) -> str:
    return re.sub(r'["\\\n\r]', " ", str(s))[:120]


def scaffold(spec: dict, level: dict, assets: dict, credits: list, dest: Path) -> Path:
    """Write the project. assets: {"models": {name: glb}, "textures": {name: png}, "title": png, "icon": png, "music": ogg, "sfx": dir}. Each name is checked: this builds paths."""
    dest = Path(dest)
    if dest.exists():
        keep = dest / ".godot"
        for p in dest.iterdir():
            if p != keep:
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE / "core", dest / "core", dirs_exist_ok=True)
    (dest / "kits").mkdir(exist_ok=True)
    shutil.copyfile(TEMPLATE / "kits" / f"{spec['kit']}.gd", dest / "kits" / "kit.gd")
    shutil.copyfile(TEMPLATE / "main.gd", dest / "main.gd")
    shutil.copyfile(TEMPLATE / "main.tscn", dest / "main.tscn")
    shutil.copyfile(TEMPLATE / "export_presets.cfg", dest / "export_presets.cfg")
    text = (TEMPLATE / "project.godot").read_text(encoding="utf-8").replace("{{TITLE}}", _safe_text(spec["title"])).replace("{{TAGLINE}}", _safe_text(spec.get("tagline", "")))
    (dest / "project.godot").write_text(text, encoding="utf-8")
    g = dest / "game"
    for sub in ("models", "tex", "art", "audio", "fonts"):
        (g / sub).mkdir(parents=True, exist_ok=True)
    for name, src in (assets.get("models") or {}).items():
        if not re.fullmatch(r"[a-z0-9_]+", name):
            raise ValueError(f"bad asset name {name!r}")
        shutil.copyfile(src, g / "models" / f"{name}.glb")
        (g / "models" / f"{name}.glb.import").write_text(_GLB_IMPORT, encoding="utf-8")
    for name, src in (assets.get("textures") or {}).items():
        if not re.fullmatch(r"[a-z0-9_]+", name):
            raise ValueError(f"bad asset name {name!r}")
        shutil.copyfile(src, g / "tex" / f"{name}.png")
        (g / "tex" / f"{name}.png.import").write_text(_TEX_IMPORT.format(mode=1, mips="true"), encoding="utf-8")
    for key, name, mode in (("title", "title", 1), ("icon", "icon", 0), ("sky", "sky", 1)):
        if assets.get(key):
            shutil.copyfile(assets[key], g / "art" / f"{name}.png")
            (g / "art" / f"{name}.png.import").write_text(_TEX_IMPORT.format(mode=mode, mips="false"), encoding="utf-8")
    if assets.get("music"):
        shutil.copyfile(assets["music"], g / "audio" / "music.ogg")
    if assets.get("sfx"):
        for f in sorted(Path(assets["sfx"]).glob("sfx_*.wav")):
            shutil.copyfile(f, g / "audio" / f.name)
    if font_source().is_file():
        shutil.copyfile(font_source(), g / "fonts" / "Archivo.woff2")
    (g / "spec.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
    (g / "level.json").write_text(json.dumps(level), encoding="utf-8")
    (g / "credits.json").write_text(json.dumps(credits, indent=1), encoding="utf-8")
    (dest / "LICENCES.txt").write_text(LICENCE_TEXT, encoding="utf-8")
    (dest / ".gitignore").write_text(".godot/\nbuild/\n", encoding="utf-8")
    (dest / ".gdignore_build").unlink(missing_ok=True)
    return dest


LOG_CAP = 20_000_000          # bytes kept of one Godot run's output; past this the run is stopped
SAME_LINE_CAP = 400           # the same line this many times in a row is a loop, and the run is stopped


def user_logs(project) -> Path | None:
    """Where Godot would keep this project's own log files: <user data>/app_userdata/<config/name>/logs. None when the cmd isn't for a project."""
    try:
        text = (Path(project) / "project.godot").read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r'^config/name="([^"]*)"', text, re.M)
    if not m:
        return None
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "godot" / "app_userdata" / m.group(1) / "logs"


def _size(d: Path | None) -> int:
    try:
        return sum(f.stat().st_size for f in d.iterdir() if f.is_file()) if d else 0
    except OSError:
        return 0


def _run(cmd: list, log: Path, timeout: int, env: dict | None = None, *, cap: int | None = None, same_cap: int | None = None) -> tuple[int, str]:
    """Run Godot (or anything) with its output going to a log that can't grow without bound: it stops at `cap` bytes or at one line repeated `same_cap` times, and the process group is killed. A killed run returns -2 and says why at the end of the log."""
    import threading
    cap = LOG_CAP if cap is None else cap
    same_cap = SAME_LINE_CAP if same_cap is None else same_cap
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    e = {**os.environ, **(env or {})}
    proc = subprocess.Popen([str(c) for c in cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True, env=e)
    why: list[str] = []
    # Godot can also write its own log in the user-data folder, whatever this runner captures: that is watched too.
    project = next((Path(str(cmd[i + 1])) for i, c in enumerate(cmd[:-1]) if str(c) == "--path"), None)
    ulogs = user_logs(project) if project else None
    ulogs_start = _size(ulogs)

    def kill():
        for sig in (15, 9):
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                return
            try:
                proc.wait(timeout=10)
                return
            except subprocess.TimeoutExpired:
                pass

    def pump():
        written, last, same = 0, b"", 0
        with open(log, "wb") as fh:
            for line in proc.stdout:
                key = line.strip()
                if key and key == last:
                    same += 1
                else:
                    last, same = key, 1
                if written + len(line) > cap:
                    why.append(f"the log reached {cap // 1_000_000} MB")
                elif same > same_cap:
                    why.append(f"one line repeated {same_cap} times: {key[:160].decode('utf-8', 'replace')}")
                if why:
                    fh.write(f"\nSTOPPED BY THE STUDIO: {why[0]}\n".encode())
                    kill()
                    break
                fh.write(line)
                written += len(line)
        proc.stdout.close()

    def watch_user_log():
        while proc.poll() is None:
            if _size(ulogs) - ulogs_start > cap:
                why.append(f"Godot's own log in {ulogs.name} grew past {cap // 1_000_000} MB")
                kill()
                return
            time.sleep(2)

    t = threading.Thread(target=pump, daemon=True)
    t.start()
    if ulogs is not None:
        threading.Thread(target=watch_user_log, daemon=True).start()
    try:
        rc = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill()
        rc = -1
    t.join(timeout=30)
    if why:
        rc = -2
        if not log.read_text(errors="replace").rstrip().endswith(why[0]):
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(f"\nSTOPPED BY THE STUDIO: {why[0]}\n")
    return rc, log.read_text(errors="replace")


def _errors(text: str) -> list[str]:
    bad = [ln.strip() for ln in text.splitlines() if re.match(r"\s*(SCRIPT ERROR|ERROR):", ln) or "Parse Error" in ln or "Failed to load script" in ln]
    # Godot says this about any project it opens for the first time, whatever is in it.
    return [ln for ln in bad if not any(x in ln for x in ("root certificate store", "at: _editor_init", "still in use at exit", "RID allocations", "were leaked at exit"))]


def import_project(project: Path, godot: str, log: Path, timeout: int = 1800) -> list[str]:
    rc, text = _run([godot, "--headless", "--path", project, "--import"], log, timeout)
    if rc != 0:                      # the editor has been seen to abort once on its way out after a good import
        rc, text = _run([godot, "--headless", "--path", project, "--import"], log, timeout)
    errs = _errors(text)
    if rc != 0 and "reimport" not in text:
        raise GodotError(f"Godot's import exited {rc}: " + "; ".join(errs[:6])[:800])
    return errs


def check_scripts(project: Path, godot: str, log_dir: Path) -> list[str]:
    """Godot's own parser over every script, from inside the project so the autoload is there. -> the problems."""
    rc, text = _run([godot, "--headless", "--path", project, "--", "--bot-check=1"], Path(log_dir) / "check.log", 180)
    errs = [ln.strip()[:400] for ln in text.splitlines() if "Parse Error" in ln or "Compile Error" in ln or "CHECK FAIL" in ln]
    if rc != 0 and not errs:
        errs = [f"Godot exited {rc} while checking the scripts"]
    if "CHECK DONE" not in text and not errs:
        errs = ["Godot never finished checking the scripts"]
    return errs


FORBIDDEN_IN_SCRIPT = re.compile(r"\b(OS|FileAccess|DirAccess|HTTPRequest|HTTPClient|JavaScriptBridge|ProjectSettings|ResourceSaver|Thread|StreamPeer\w*|TCPServer|UDPServer|PacketPeer\w*|WebSocket\w*|ClassDB|Engine|Expression)\b|\b(load|preload)\s*\(")
SCRIPT_RULES = ("extends Node3D", "func _process")


def constrained_script_problems(text: str) -> list[str]:
    """What a model's small script may not do, before Godot even parses it: no files, no network, no OS, no loading other code. It decorates; that's all."""
    bad = []
    if len(text) > 1500:
        bad.append("it's longer than 1500 characters")
    if not text.lstrip().startswith("extends Node3D"):
        bad.append("it must start with extends Node3D")
    hit = FORBIDDEN_IN_SCRIPT.search(text)
    if hit:
        bad.append(f"it uses {hit.group(0).strip()}, which a decoration has no need of")
    return bad


def check_constrained(text: str, project: Path, godot: str, log_dir: Path) -> list[str]:
    """Both gates: the rules above, then godot --headless --check-only."""
    bad = constrained_script_problems(text)
    if bad:
        return bad
    path = Path(project) / "core" / "_candidate.gd"
    path.write_text(text, encoding="utf-8")
    try:
        rc, out = _run([godot, "--headless", "--path", project, "--check-only", "-s", "res://core/_candidate.gd"], Path(log_dir) / "candidate.log", 120)
        errs = [ln.strip() for ln in out.splitlines() if "Parse Error" in ln or "SCRIPT ERROR" in ln]
        return errs[:3] or ([f"Godot exited {rc}"] if rc not in (0,) else [])
    finally:
        path.unlink(missing_ok=True)


def export(project: Path, godot: str, target: str, out: Path, log: Path, timeout: int = 900) -> Path:
    """target: "Linux" or "Web". -> the file Godot wrote."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rc, text = _run([godot, "--headless", "--path", project, "--export-release", target, out], log, timeout)
    if rc != 0 or not out.is_file() or out.stat().st_size == 0:
        raise GodotError(f"{target} export failed ({rc}): " + "; ".join(_errors(text)[:4])[:600])
    return out


def playtest(project: Path, godot: str, report: Path, log: Path, *, timeout_s: int = 900, seconds: int = 600, headless: bool = True, movie: Path | None = None, env: dict | None = None) -> dict:
    """The bot plays the real project. Headless it runs with no picture, as fast as physics allows. With a movie path, Godot's own Movie Maker records every frame at a fixed rate."""
    report = Path(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    cmd = [godot, "--path", project]
    if headless:
        cmd += ["--headless", "--fixed-fps", "60"]
    if movie:
        cmd = [godot, "--path", project, "--rendering-driver", "opengl3", "--resolution", "1280x720", "--write-movie", movie, "--fixed-fps", "30"]
    cmd += ["--", "--bot", f"--bot-timeout={seconds}", f"--bot-report={report}"]
    rc, text = _run(cmd, log, timeout_s, env)
    errs = _errors(text)
    if report.is_file():
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except ValueError:
            data = {"result": "bad report"}
    else:
        data = {"result": "no report", "rc": rc}
    data["script_errors"] = errs[:12]
    data["rc"] = rc
    if rc == -2:
        data["result"] = "error_loop"
        data["stopped"] = text.rsplit("STOPPED BY THE STUDIO:", 1)[-1].strip()[:300]
    return data


def can_record() -> bool:
    return bool(shutil.which("xvfb-run") and shutil.which("ffmpeg"))


def record(project: Path, godot: str, out_dir: Path, log: Path, *, timeout_s: int = 3000, seconds: int = 900) -> dict:
    """The bot played once more with Movie Maker on, in a virtual screen. Leaves play.mp4, sheet.jpg and report_video.json in out_dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    avi, report = out_dir / "play.avi", out_dir / "report_video.json"
    cmd = ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24", godot, "--path", project, "--rendering-driver", "opengl3", "--resolution", "1280x720", "--write-movie", avi, "--fixed-fps", "30", "--", "--bot", f"--bot-timeout={seconds}", f"--bot-report={report}"]
    rc, text = _run(cmd, Path(log), timeout_s)
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {"result": "no report", "rc": rc}
    data["script_errors"] = _errors(text)[:12]
    if avi.is_file():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(avi), "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out_dir / "play.mp4")], timeout=1800, check=False)
        frames = max(1, int(float(data.get("wall_s") or 60) * 30 / 12))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(avi), "-vf", f"select='not(mod(n,{frames}))',scale=480:-1,tile=3x4", "-fps_mode", "passthrough", "-frames:v", "1", str(out_dir / "sheet.jpg")], timeout=600, check=False)
        avi.unlink(missing_ok=True)
    return data


def zip_tree(src: Path, dest: Path, prefix: str = "") -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(Path(src).rglob("*")):
            if f.is_file() and ".godot" not in f.parts and "build" not in f.relative_to(src).parts:
                z.write(f, os.path.join(prefix, f.relative_to(src).as_posix()))
    return dest
