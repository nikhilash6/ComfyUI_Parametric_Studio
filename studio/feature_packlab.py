"""Pack Lab for everyone: browse the reviewed node packs, read each one's risk notes, and try one in a throwaway sandbox, never in your live ComfyUI.
The isolation is a Docker container and nothing else: an internal network with no way out, a read-only system, no home folder, no GPU, no model folder, all capabilities dropped, and one writable folder of its own. So without a working Docker on Linux this refuses and says so plainly: there is no second-best mode that runs a stranger's code on your machine.
Reviewed does not mean safe, and nothing here says otherwise. A pack flagged in review cannot be installed at all. Those are kept only as salted hashes, and the list is not exhaustive. Nothing is pip-installed: a pack whose libraries are missing fails to load, and the page reports that."""
import hashlib, json, os, platform, re, shutil, subprocess, threading, time, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/packlab")
PAGE = {"tab": "packlab", "label": "Pack Lab", "title": ["Pack Lab", "Try a node pack. Keep it away from your work.", "Reviewed picks with their risks in plain sight, and a sandbox to load one in. Reviewed does not mean safe."], "module": "packlab.js", "export": "PackLab", "css": "packlab.css"}
DATA = Path(__file__).resolve().parent / "pack_lab_picks.json"
NETWORK = "psn-pack-sandbox"; PREFIX = "psn-pack-sandbox-"; IMAGE = "ubuntu:24.04"; PORT = 8188; START_LIMIT_S = 600; POLL_S = 10; MEMORY = "16g"; PIDS = "2000"
NAME_OK = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}__[A-Za-z0-9][A-Za-z0-9._-]{0,120}")
WARNINGS = ["This runs the pack's own code, inside the sandbox, as soon as it loads. That is the point of the sandbox, and it is why the pack never goes near your live ComfyUI.", "Nobody here has proved anything about this pack's safety. The notes come from reading its text. Being a pick does not make it safe, and a sandbox can have holes.", "The sandbox has no internet, no GPU and no models, so it shows whether a pack loads and what nodes it adds. It will not render anything.", "Its libraries are not installed for it. A pack that needs one you lack fails to load, and that is a real result."]
REFUSE_NO_DOCKER = "This machine has no working Docker, so Pack Lab will not install anything. Docker is the isolation: without it a pack's code would run with your files and your internet. There is no other mode, and it will never install into your live ComfyUI. You can still read every pack's notes here."
REFUSE_OS = "Pack Lab's sandbox only runs on Linux, because it borrows the system's own folders read-only. On this machine it will not install anything, and it will never install into your live ComfyUI. You can still read every pack's notes here."
FLAGGED = "This pack was flagged in review, so Pack Lab will not install it, even in the sandbox."
FLAG_NOTE = "Some packs were flagged in our review, and Pack Lab refuses them. We do not name them here: some flags come from a script alone and could be false alarms. This list is not exhaustive. A pack that is not refused has not been cleared."
_lock = threading.Lock(); _cache: dict = {}; _threads: dict = {}


def picks() -> dict:
    if "d" not in _cache:
        try: _cache["d"] = json.loads(DATA.read_text(encoding="utf-8"))
        except (OSError, ValueError): _cache["d"] = {"picks": [], "flagged": [], "flag_salt": "", "about": ""}
    return _cache["d"]


def is_flagged(pack: str) -> bool:
    d = picks(); return hashlib.sha256(f"{d.get('flag_salt', '')}:{pack.lower()}".encode()).hexdigest() in set(d.get("flagged") or [])


def root() -> Path:
    return Path(os.environ.get("STUDIO_PACK_SANDBOX_DIR") or Path.home() / ".local" / "share" / "parametric-studio" / "pack_sandbox")


def _run(args, timeout=60, **k):
    """Every outside command goes through here, so tests can stand in for Docker and git."""
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, **k)


def _setting(name):
    from psn import paths
    return paths.setting(name)


def comfy_paths():
    """(ComfyUI folder, its Python). Both must be told: nothing is guessed about what gets mounted into a container."""
    return _setting("STUDIO_COMFY_ROOT"), _setting("STUDIO_COMFY_PYTHON")


def can_sandbox() -> dict:
    """Whether this machine can really isolate a pack, checked by asking. {"ok", "why", "docker"}"""
    if platform.system() != "Linux": return {"ok": False, "why": REFUSE_OS, "docker": None}
    if not shutil.which("docker"): return {"ok": False, "why": REFUSE_NO_DOCKER, "docker": False}
    try: r = _run(["docker", "version", "--format", "{{.Server.Version}}"], 15)
    except (OSError, subprocess.SubprocessError): return {"ok": False, "why": REFUSE_NO_DOCKER, "docker": False}
    if r.returncode != 0 or not r.stdout.strip(): return {"ok": False, "why": REFUSE_NO_DOCKER + " (Docker is installed, but its service did not answer.)", "docker": False}
    cr, py = comfy_paths()
    if not cr or not py or not os.path.isfile(os.path.join(cr, "main.py")) or not os.path.isfile(py): return {"ok": False, "why": "Docker works, but the studio does not know where ComfyUI and its Python are. Set STUDIO_COMFY_ROOT and STUDIO_COMFY_PYTHON in the studio's settings file. They are mounted read-only, and nothing is guessed.", "docker": True}
    return {"ok": True, "why": "", "docker": True, "version": r.stdout.strip()}


def slug(pack: str) -> str: return re.sub(r"[^a-z0-9-]+", "-", pack.lower()).strip("-")[:48]


def sandbox_dir(pack: str) -> Path:
    d = (root() / slug(pack)).resolve()
    if root().resolve() not in d.parents: raise HTTPException(400, "bad pack name")
    return d


def _state_path(pack): return sandbox_dir(pack) / "state.json"


def state(pack):
    try: return json.loads(_state_path(pack).read_text())
    except (OSError, ValueError): return None


def _save(pack, **k):
    with _lock:
        s = state(pack) or {"pack": pack}; s.update(k); p = _state_path(pack); p.parent.mkdir(parents=True, exist_ok=True); t = p.with_suffix(".tmp"); t.write_text(json.dumps(s)); os.replace(t, p); return s


def container_args(pack: str, d: Path, comfy_root: str, python: str) -> list:
    """The container, with pack_staging's isolation: internal network, read-only, no home, no capabilities. One writable folder, and no GPU or model folder at all."""
    venv = os.path.dirname(os.path.dirname(python)); a = ["docker", "run", "-d", "--name", PREFIX + slug(pack), "--network", NETWORK, "--read-only", "--user", f"{os.getuid()}:{os.getgid()}", "--tmpfs", "/tmp:size=4g", "--tmpfs", "/home", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--memory", MEMORY, "--pids-limit", PIDS]
    for m in ("/usr", "/lib", "/lib64", "/etc/ssl", "/etc/ld.so.cache"):
        if os.path.exists(m): a += ["-v", f"{m}:{m}:ro"]
    a += ["-v", f"{comfy_root}:/comfy:ro", "-v", f"{venv}:{venv}:ro", "-v", f"{d}:/sandbox"]
    for e in ("HOME=/tmp", "PYTHONDONTWRITEBYTECODE=1", "HF_HUB_OFFLINE=1", "PIP_NO_INDEX=1", "PIP_NO_INPUT=1", "PYTHONUNBUFFERED=1", "CUDA_VISIBLE_DEVICES="): a += ["-e", e]
    return a + ["-w", "/comfy", IMAGE, python, "/comfy/main.py", "--cpu", "--listen", "127.0.0.1", "--port", str(PORT), "--disable-auto-launch", "--base-directory", "/sandbox", "--input-directory", "/sandbox/input", "--output-directory", "/sandbox/output", "--temp-directory", "/sandbox/temp", "--user-directory", "/sandbox/user"]


def isolation_problems(args: list) -> list:
    """The same list a reviewer would check, run on the real command. Anything here stops the start."""
    out = []; text = " ".join(args); home = str(Path.home())
    for need in ("--read-only", "--cap-drop ALL", "no-new-privileges", "--network " + NETWORK): 
        if need not in text: out.append(f"missing {need}")
    if "--privileged" in text or "--device" in text or "--gpus" in text or "--network host" in text or "-p " in text: out.append("gives the sandbox more than it should have")
    for i, x in enumerate(args):
        if x == "-v":
            src = args[i + 1].split(":")[0]; ro = args[i + 1].endswith(":ro")
            if not ro and args[i + 1].split(":")[1] != "/sandbox": out.append(f"a writable mount other than the sandbox: {src}")
            if src in (home, "/", "/home", "/var/run/docker.sock"): out.append(f"mounts {src}")
    return out


def network_ready() -> bool:
    r = _run(["docker", "network", "inspect", NETWORK, "--format", "{{.Internal}}"], 15)
    if r.returncode != 0: _run(["docker", "network", "create", "--internal", NETWORK], 30); r = _run(["docker", "network", "inspect", NETWORK, "--format", "{{.Internal}}"], 15)
    return r.returncode == 0 and r.stdout.strip() == "true"


def fetch(pack: str, dest: Path) -> str:
    """Puts the pack's files in the sandbox, with no code of it run: a local library copy if one is set, else a shallow clone with hooks, submodules and links off. Links in it are dropped. -> where it came from."""
    lib = _setting("STUDIO_PACK_LIBRARY"); src = Path(lib) / pack if lib else None
    def drop_links(top):
        for dp, dn, fn in os.walk(top):
            for n in dn + fn:
                p = os.path.join(dp, n)
                if os.path.islink(p): os.remove(p)
    if src and src.is_dir():
        shutil.copytree(src, dest, symlinks=True, ignore=shutil.ignore_patterns(".git")); drop_links(dest); return "this machine's pack library"
    owner, name = pack.split("__", 1); url = f"https://github.com/{owner}/{name}.git"
    r = _run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.symlinks=false", "-c", "protocol.file.allow=never", "clone", "--quiet", "--depth", "1", "--no-recurse-submodules", "--", url, str(dest)], 300)
    if r.returncode != 0: raise RuntimeError(f"Could not fetch {url}. It may have moved or gone private.")
    shutil.rmtree(dest / ".git", ignore_errors=True); drop_links(dest); return url


def _exec_py(name: str, py: str, code: str, timeout=30):
    return _run(["docker", "exec", name, py, "-c", code], timeout)


def _no_way_out(name: str, py: str) -> bool:
    """Tries to reach the internet from inside. Only a failed attempt counts as cut off."""
    r = _exec_py(name, py, "import socket;socket.setdefaulttimeout(4)\ntry:\n socket.create_connection(('1.1.1.1',443));print('REACHABLE')\nexcept Exception:print('blocked')", 20)
    return r.returncode == 0 and r.stdout.strip() == "blocked"


def _home_hidden(name: str, py: str) -> bool:
    """Looks for this machine's private folders from inside. Only finding none counts."""
    home = str(Path.home()); probe = [os.path.join(home, x) for x in (".ssh", ".config", ".gnupg", "Documents")]
    r = _exec_py(name, py, f"import os;print('FOUND' if any(os.path.exists(p) for p in {probe!r}) else 'hidden')", 20)
    return r.returncode == 0 and r.stdout.strip() == "hidden"


def remove_container(pack: str) -> None:
    _run(["docker", "rm", "-f", PREFIX + slug(pack)], 60)                 # this exact name: only a sandbox of ours


def _install(pack: str) -> None:
    name = PREFIX + slug(pack); d = sandbox_dir(pack); cr, py = comfy_paths()
    try:
        _save(pack, state="fetching", note="Getting the pack's files. None of its code runs yet.")
        shutil.rmtree(d / "custom_nodes", ignore_errors=True)
        for s in ("custom_nodes", "input", "output", "temp", "user"): (d / s).mkdir(parents=True, exist_ok=True)
        dest = (d / "custom_nodes" / pack).resolve()
        if d not in dest.parents or (cr and Path(cr).resolve() in dest.parents): raise RuntimeError("Refused: that folder is not inside the sandbox.")
        origin = fetch(pack, dest); _save(pack, origin=origin, state="starting", note="Starting the sandbox.")
        if not network_ready(): raise RuntimeError("Docker could not make a network with no way out, so nothing was started.")
        if _run(["docker", "image", "inspect", IMAGE], 15).returncode != 0:
            _save(pack, note=f"Getting the {IMAGE} base image from Docker Hub.")
            if _run(["docker", "pull", IMAGE], 600).returncode != 0: raise RuntimeError(f"Could not get the {IMAGE} image.")
        args = container_args(pack, d, cr, py); bad = isolation_problems(args)
        if bad: raise RuntimeError("Refused to start a sandbox that is not sealed: " + "; ".join(bad))
        remove_container(pack); r = _run(args, 300)
        if r.returncode != 0: raise RuntimeError("Docker would not start it: " + r.stderr.strip()[-300:])
        if not _no_way_out(name, py):
            time.sleep(3)
            if not _no_way_out(name, py): remove_container(pack); raise RuntimeError("The sandbox could reach the internet, or could not be tested, so it was shut down at once.")
        if not _home_hidden(name, py): remove_container(pack); raise RuntimeError("Your home folder could be seen from inside the sandbox, or that could not be tested, so it was shut down at once.")
        _save(pack, state="loading", note="The pack is loading inside the sandbox.", no_internet=True, home_hidden=True); t0 = time.time(); info = None; code = f"import urllib.request as u,sys;sys.stdout.write(u.urlopen('http://127.0.0.1:{PORT}/object_info',timeout=60).read().decode())"
        while time.time() - t0 < START_LIMIT_S:
            if _run(["docker", "inspect", "-f", "{{.State.Running}}", name], 15).stdout.strip() != "true": break
            r = _exec_py(name, py, code, 90)
            if r.returncode == 0 and r.stdout.startswith("{"): info = json.loads(r.stdout); break
            time.sleep(POLL_S)
        logs = _run(["docker", "logs", "--tail", "200", name], 30); text = logs.stdout + logs.stderr
        if info is None: _save(pack, state="failed", note="ComfyUI did not come up with this pack loaded.", log=_scrub_log(text)); remove_container(pack); return
        mine = sorted(k for k, v in info.items() if str(v.get("python_module") or "").startswith(f"custom_nodes.{pack}") or f"custom_nodes/{pack}" in str(v.get("python_module") or ""))
        failed = "IMPORT FAILED" in text and pack in text
        _save(pack, state="failed" if failed else "loaded", note="It failed to import. See the log." if failed else f"It loaded and added {len(mine)} nodes." if mine else "It loaded, but no nodes were seen from it. Some packs register in a way this count misses.", nodes=mine[:200], node_count=len(mine), log=_scrub_log(text), finished=time.time()); remove_container(pack)
    except Exception as e:
        try: remove_container(pack)
        except Exception: pass
        _save(pack, state="failed", note="Docker took too long to answer, so nothing was left running. Try it again when the machine is less busy." if isinstance(e, subprocess.TimeoutExpired) else str(e)[:400])
    finally:
        with _lock: _threads.pop(pack, None)


def _scrub_log(text: str) -> str:
    """The last of the log, for the page: no folder of this machine in it."""
    home = str(Path.home()); out = text[-6000:].replace(home, "~")
    return re.sub(r"(?<![\w.])/(?:mnt|home|Users|root|media)/\S*", "(a folder)", out)


# ---------- routes ----------
@router.get("/picks")
def list_picks():
    c = can_sandbox(); rows = []
    for p in picks()["picks"]:
        s = state(p["pack"]) or {}
        rows.append({**p, "installable": p["action"] == "install-candidate" and not is_flagged(p["pack"]), "sandbox_state": s.get("state"), "sandbox_nodes": s.get("node_count")})
    return {"about": picks().get("about"), "made": picks().get("made"), "can": c, "warnings": WARNINGS, "picks": rows, "flag_note": FLAG_NOTE}


@router.get("/sandbox/{pack}")
def get_sandbox(pack: str):
    if not NAME_OK.fullmatch(pack): raise HTTPException(404, "no such pack")
    return state(pack) or {"pack": pack, "state": None}


@router.post("/sandbox")
def install(b: dict):
    pack = b.get("pack")
    if not isinstance(pack, str) or not NAME_OK.fullmatch(pack): raise HTTPException(400, "Which pack?")
    if is_flagged(pack): raise HTTPException(403, FLAGGED)
    row = next((p for p in picks()["picks"] if p["pack"] == pack), None)
    if not row: raise HTTPException(404, "That pack is not one of the reviewed picks. Pack Lab only installs those.")
    if row["action"] != "install-candidate": raise HTTPException(409, "This pick is here for its idea or its docs. Pack Lab does not install it.")
    if b.get("understood") is not True: raise HTTPException(400, "Read the warnings and press the button: nothing installs without it.")
    c = can_sandbox()
    if not c["ok"]: raise HTTPException(409, c["why"])
    with _lock:
        if pack in _threads: raise HTTPException(409, "This one is already being installed.")
        t = threading.Thread(target=_install, args=(pack,), daemon=True); _threads[pack] = t
    _save(pack, state="fetching", note="Starting.", started=time.time(), id=uuid.uuid4().hex[:8], nodes=[], node_count=None, log="", no_internet=None); t.start(); return {"pack": pack, "state": "fetching"}


@router.delete("/sandbox/{pack}")
def uninstall(pack: str):
    if not NAME_OK.fullmatch(pack): raise HTTPException(404, "no such pack")
    if shutil.which("docker"): remove_container(pack)
    shutil.rmtree(sandbox_dir(pack), ignore_errors=True); return {"pack": pack, "state": None}
