"""Model rotation: keep every model without keeping every model on disk. A model's weights move to a cloud remote and back; its graphs, renders and notes never leave the repo.
Off unless STUDIO_CONFIG_DIR/rotation.json names a remote: {"remote": "name:", "remote_dir": "models", "roots": ["/path/to/models"], "min_free_gb": 150, "link_roots": ["/also/scan/for/symlinks"], "fetch_mb_s": 25}.
Nothing runs on a timer: `plan` only prints, and a local copy is removed only after its upload is verified and only when asked to with --yes (or confirm: true on the API).
Usage: python -m studio.rotation status | scan | plan [--json] | offload PATH [--yes] [--source URL] | fetch PATH | pin PATH | unpin PATH"""
import argparse, hashlib, json, math, os, re, shutil, stat, subprocess, sys, tempfile, threading, time
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request

GB = 1024 ** 3; MB = 1024 ** 2
MODEL_EXT = (".safetensors", ".gguf", ".ckpt", ".pt", ".pth", ".bin", ".sft", ".onnx")
MIN_SIZE = 50 * MB              # smaller files are not worth a round trip
FETCH_MARGIN = GB               # a fetch leaves at least this much free
DEFAULT_RATE = 25               # MB/s until a real fetch has been measured
router = APIRouter()
_lock = threading.Lock()
_job = {"state": "idle"}

class RotationError(Exception):
    pass

class Refused(RotationError):
    """Reasons a file may not be offloaded; none of them are errors in the file."""
    def __init__(self, reasons):
        super().__init__("; ".join(reasons)); self.reasons = reasons

def conf_dir(): return Path(os.environ.get("STUDIO_CONFIG_DIR") or Path.home() / ".config" / "parametric-studio")
def manifest_file(): return conf_dir() / "rotation_manifest.json"

def config():
    """The config, or None when the feature is off (no file, bad file, or no remote)."""
    try: c = json.load(open(conf_dir() / "rotation.json"))
    except (OSError, ValueError): return None
    if not isinstance(c, dict) or not isinstance(c.get("remote"), str) or not c["remote"].strip(): return None
    roots = c.get("roots")
    if not isinstance(roots, list) or not roots or not all(isinstance(r, str) for r in roots): return None
    return {"remote": c["remote"], "remote_dir": str(c.get("remote_dir") or "").strip("/"), "roots": [os.path.abspath(os.path.expanduser(r)) for r in roots],
            "min_free_gb": float(c.get("min_free_gb", 150)), "fetch_mb_s": c.get("fetch_mb_s"),
            "link_roots": [os.path.abspath(os.path.expanduser(r)) for r in c.get("link_roots") or []]}

def need_config():
    c = config()
    if not c: raise RotationError("rotation is off: rotation.json has no remote and roots")
    return c

# ---------- the manifest: one writer at a time, always replaced whole
def load():
    try: m = json.load(open(manifest_file()))
    except (OSError, ValueError): m = {}
    if not isinstance(m, dict) or not isinstance(m.get("files"), dict): m = {"files": {}}
    return m

def _save(m):
    conf_dir().mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=conf_dir(), prefix=".rotation_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f: json.dump(m, f, indent=1)
        os.replace(tmp, manifest_file())
    except BaseException:
        if os.path.exists(tmp): os.remove(tmp)
        raise

def _update(fn):
    """Read, change and write under the lock, so a slow upload never writes back a stale copy."""
    with _lock:
        m = load(); out = fn(m); _save(m); return out

def _in_roots(path, roots): return any(path == r or path.startswith(r.rstrip(os.sep) + os.sep) for r in roots)

def _norm(path, cfg):
    p = os.path.abspath(os.path.expanduser(str(path)))
    if not _in_roots(p, cfg["roots"]): raise RotationError("that path is not inside the model roots")
    return p

def scan(cfg=None):
    """Updates the manifest from what is on disk. Hashes nothing: a checksum is only taken when a file is offloaded."""
    cfg = cfg or need_config(); found = {}
    for root in cfg["roots"]:
        for dp, dns, fns in os.walk(root):
            for n in fns:
                if not n.lower().endswith(MODEL_EXT): continue
                p = os.path.join(dp, n)
                try: st = os.lstat(p)
                except OSError: continue
                if stat.S_ISREG(st.st_mode) and st.st_size >= MIN_SIZE: found[p] = st
    def apply(m):
        fs = m["files"]
        for p in list(fs):
            e = fs[p]
            if p in found: continue
            if e.get("state") == "local" or not _in_roots(p, cfg["roots"]): del fs[p]         # gone, and no cloud copy to remember
            else: e["state"] = "cloud"
        for p, st in found.items():
            e = fs.get(p)
            if not e: fs[p] = {"path": p, "size": st.st_size, "mtime": st.st_mtime, "sha256": None, "state": "local", "remote": None, "last_used": None, "pinned": False, "source": None}; continue
            if e.get("size") != st.st_size or e.get("mtime") != st.st_mtime:                  # changed on disk: the old checksum and cloud copy no longer describe it
                e.update(size=st.st_size, mtime=st.st_mtime, sha256=None, state="local", remote=None)
            elif e.get("state") == "cloud": e["state"] = "both"
        return fs
    return _update(apply)

def links_to_files(cfg):
    """{real path of a file: [symlinks that point at it]}, over the roots and link_roots. A link to a whole folder keeps working, so only links to files count."""
    out, seen = {}, set()
    for root in cfg["roots"] + cfg["link_roots"]:
        if any(root == s or root.startswith(s + os.sep) for s in seen): continue
        seen.add(root)
        for dp, dns, fns in os.walk(root):
            for n in fns:
                p = os.path.join(dp, n)
                if os.path.islink(p):
                    t = os.path.realpath(p)
                    out.setdefault(t, []).append(p)
    return out

def open_files():
    """Every path a process we can see holds open or mapped, or None where that cannot be checked. Another user's processes stay invisible."""
    if not os.path.isdir("/proc/self/fd"): return None
    out = set()
    for pid in os.listdir("/proc"):
        if not pid.isdigit(): continue
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                try: out.add(os.readlink(f"/proc/{pid}/fd/{fd}"))
                except OSError: pass
            with open(f"/proc/{pid}/maps", errors="ignore") as f:
                for line in f:
                    i = line.find("/")
                    if i > 0: out.add(line[i:].rstrip("\n"))
        except OSError: continue
    return out

def refusals(e, links, opened):
    """Why this manifest entry may not be offloaded, in words. Empty means it may."""
    p, out = e["path"], []
    if e.get("pinned"): out.append("pinned")
    try: st = os.lstat(p)
    except OSError: return out + ["not on disk"]
    if not stat.S_ISREG(st.st_mode): out.append("not a regular file")
    if opened is None: out.append("cannot check whether it is in use on this system")
    elif p in opened or os.path.realpath(p) in opened: out.append("open in a running process")
    if links.get(os.path.realpath(p)): out.append(f"{len(links[os.path.realpath(p)])} symlink(s) point at it")
    if st.st_nlink > 1: out.append(f"has {st.st_nlink} hard links, so removing this one frees nothing")
    return out

# ---------- rclone
def run(args):
    """The one place rclone is called. Output is returned to the caller and never holds credentials: only copy, check and list commands go through here."""
    return subprocess.run(["rclone", *args], capture_output=True, text=True)

def _ok(r, what):
    if r.returncode: raise RotationError(f"{what} failed: {(r.stderr or r.stdout or '').strip()[-300:]}")
    return r

def remote_path(cfg, path):
    root = next((r for r in cfg["roots"] if _in_roots(path, [r])), None)
    if root is None: raise RotationError("that path is not inside the model roots")
    rel = os.path.relpath(path, root).replace(os.sep, "/"); name = os.path.basename(root.rstrip(os.sep))
    base = cfg["remote"] if cfg["remote"].endswith((":", "/")) else cfg["remote"] + "/"
    return base + "/".join(x for x in (cfg["remote_dir"], name, rel) if x)

def _is_crypt(cfg):
    """A plain check cannot compare hashes through encryption; cryptcheck can."""
    r = cfg["remote"]
    if ":" not in r: return False
    want = r.split(":", 1)[0] + ":"
    for line in _ok(run(["listremotes", "--long"]), "listing remotes").stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == want: return parts[1] == "crypt"
    raise RotationError(f"no remote called {want}")

def verify(cfg, path, remote):
    """Size first, then content. A check that compared no file at all is a failure, not a pass."""
    size = os.path.getsize(path); parent, name = remote.rsplit("/", 1)
    listed = _ok(run(["lsf", "--format", "s", "--files-only", remote]), "reading the uploaded size").stdout.strip()
    if listed != str(size): raise RotationError(f"size mismatch after upload: local {size}, remote {listed or 'missing'}")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f: f.write(os.path.basename(path) + "\n")
    try:
        r = _ok(run(["cryptcheck" if _is_crypt(cfg) else "check", os.path.dirname(path), parent, "--files-from-raw", f.name, "--one-way"]), "verifying the upload")
    finally: os.remove(f.name)
    if not re.search(r"(?<!\d)1 matching file", (r.stderr or "") + (r.stdout or "")): raise RotationError("the verify step did not compare the file")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(8 * MB): h.update(b)
    return h.hexdigest()

# ---------- the three moves
def offload(path, yes=False, source=None, cfg=None):
    """Upload, verify, and only then, with yes, remove the local copy. Any failure leaves the local file where it is."""
    cfg = cfg or need_config(); p = _norm(path, cfg); fs = scan(cfg); e = fs.get(p)
    if not e: raise RotationError("that file is not a tracked model")
    if e["state"] == "cloud": raise RotationError("that model is already only in the cloud")
    def check():
        cur = load()["files"].get(p, e); why = refusals(cur, links_to_files(cfg), open_files())
        if why: raise Refused(why)
    check()
    before = os.stat(p); digest = sha256(p); remote = remote_path(cfg, p)
    _ok(run(["copyto", p, remote, "--drive-stop-on-upload-limit"]), "the upload")
    verify(cfg, p, remote)
    def uploaded(m):
        m["files"][p].update(sha256=digest, state="both", remote=remote, source=source or m["files"][p].get("source"))
    _update(uploaded)
    if not yes: return {"path": p, "state": "both", "sha256": digest, "removed": False, "remote": remote}
    now = os.stat(p)
    if (now.st_size, now.st_mtime) != (before.st_size, before.st_mtime): raise RotationError("the file changed during the upload; it stays on disk")
    check()                                                                                   # the upload can take hours; something may have opened or linked it since
    os.remove(p)
    def removed(m): m["files"][p]["state"] = "cloud"
    _update(removed)
    return {"path": p, "state": "cloud", "sha256": digest, "removed": True, "remote": remote, "freed_gb": round(before.st_size / GB, 2)}

def fetch(path, cfg=None):
    """Download beside the target and rename only after the checksum matches, so a broken fetch never looks like a model."""
    cfg = cfg or need_config(); p = _norm(path, cfg); e = load()["files"].get(p)
    if not e or not e.get("remote"): raise RotationError("that model has no cloud copy")
    if not e.get("sha256"): raise RotationError("that model has no recorded checksum")
    if os.path.exists(p): raise RotationError("that model is already on disk")
    parent = os.path.dirname(p); os.makedirs(parent, exist_ok=True)
    need, free = e["size"] + FETCH_MARGIN, shutil.disk_usage(parent).free
    if free < need: raise RotationError(f"not enough space: needs {need / GB:.1f} GB including a margin, {free / GB:.1f} GB free")
    part, t0 = p + ".part", time.time()
    try:
        _ok(run(["copyto", e["remote"], part]), "the download")
        if not os.path.isfile(part): raise RotationError("the download produced no file")
        got = sha256(part)
        if got != e["sha256"]: raise RotationError("checksum mismatch after the download")
        os.replace(part, p)
    finally:
        if os.path.exists(part): os.remove(part)
    st = os.stat(p); secs = max(time.time() - t0, 0.001)
    def done(m):
        m["files"][p].update(state="both", mtime=st.st_mtime); m["rate_mb_s"] = round(st.st_size / MB / secs, 1)
    _update(done)
    return {"path": p, "state": "both", "sha256": got}

def set_pinned(path, value, cfg=None):
    cfg = cfg or need_config(); p = _norm(path, cfg); fs = scan(cfg)
    if p not in fs: raise RotationError("that file is not a tracked model")
    def apply(m): m["files"][p]["pinned"] = bool(value)
    _update(apply); return {"path": p, "pinned": bool(value)}

# ---------- which models were used last
def atime_works(path):
    """Whether the disk records reads at all. Mounted noatime, a file's atime says nothing about use."""
    try:
        rows = [l.split() for l in open("/proc/mounts")]
        real, best = os.path.realpath(path), None
        for row in rows:
            mp = row[1].replace("\\040", " ")
            if real == mp or real.startswith(mp.rstrip("/") + "/"):
                if best is None or len(mp) >= len(best[0]): best = (mp, row[3].split(","))
        return bool(best) and "noatime" not in best[1]
    except OSError: return False

def _names(graph):
    """Every model-looking file name in a graph's inputs."""
    out = set()
    for node in (graph or {}).values():
        if not isinstance(node, dict): continue
        for v in (node.get("inputs") or {}).values():
            if isinstance(v, str) and v.lower().endswith(MODEL_EXT): out.add(v.replace("\\", "/"))
    return out

def _matches(path, name): return path.replace("\\", "/").endswith("/" + name)

def touch(graph):
    """Records that a graph used these models. Never allowed to get in the way of the render."""
    try:
        names = _names(graph)
        if not names or not config(): return
        now = time.time()
        def apply(m):
            for p, e in m["files"].items():
                if any(_matches(p, n) for n in names): e["last_used"] = now
        _update(apply)
    except Exception as e: print(f"[rotation] could not record use: {e}")

def cloud_only(graph):
    """The models a graph needs that are only in the cloud right now."""
    if not config(): return []
    names = _names(graph)
    return [e for e in load()["files"].values() if e.get("state") == "cloud" and any(_matches(e["path"], n) for n in names)] if names else []

def require_local(graph):
    """A cloud-only model would otherwise fail deep inside ComfyUI, or get silently swapped for a look-alike."""
    miss = cloud_only(graph)
    if miss:
        names = ", ".join(os.path.basename(e["path"]) for e in miss)
        raise HTTPException(409, f"{names} is in the cloud. Fetch it first: Models page > Fetch, or python -m studio.rotation fetch \"{miss[0]['path']}\"")

def _rate(cfg, m): return cfg.get("fetch_mb_s") or m.get("rate_mb_s") or DEFAULT_RATE

def eta_min(size, rate): return max(1, math.ceil(size / MB / rate / 60))

def plan(cfg=None):
    """Least recently used first, until each disk is back above min_free_gb. Moves nothing."""
    cfg = cfg or need_config(); fs = scan(cfg); links, opened = links_to_files(cfg), open_files()
    use_atime = {r: atime_works(r) for r in cfg["roots"]}; target = int(cfg["min_free_gb"] * GB)
    disks, refused, recorded = {}, [], 0
    for e in fs.values():
        if e["state"] == "cloud": continue
        why = refusals(e, links, opened)
        if why: refused.append({"path": e["path"], "gb": round(e["size"] / GB, 2), "why": why}); continue
        root = next(r for r in cfg["roots"] if _in_roots(e["path"], [r])); st = os.stat(e["path"])
        used = e.get("last_used"); how = "recorded"
        if used: recorded += 1
        elif use_atime[root]: used, how = st.st_atime, "atime"
        else: used, how = 0, "never recorded"
        disks.setdefault(st.st_dev, {"root": root, "rows": []})["rows"].append({"path": e["path"], "gb": round(e["size"] / GB, 2), "size": e["size"], "used": used, "how": how})
    moves, summary = [], []
    for d in disks.values():
        free = shutil.disk_usage(d["root"]).free; short = max(0, target - free); freed = 0
        for row in sorted(d["rows"], key=lambda r: (r["used"], -r["size"])):                  # with no usage yet, largest first: the fewest files for the space
            if freed >= short: break
            moves.append(row); freed += row["size"]
        summary.append({"root": d["root"], "free_gb": round(free / GB, 1), "short_gb": round(short / GB, 1), "would_free_gb": round(freed / GB, 1), "still_short_gb": round(max(0, short - freed) / GB, 1)})
    return {"moves": moves, "refused": refused, "disks": summary, "target_free_gb": cfg["min_free_gb"], "total_gb": round(sum(r["size"] for r in moves) / GB, 1), "with_recorded_use": recorded,
            "atime_works": use_atime, "order": "by recorded use" if recorded else "NO USE RECORDED YET: order is largest first, not least recently used",
            "cannot_see_open_files": opened is None, "no_known_source": sum(1 for r in moves if not fs[r["path"]].get("source"))}

def status():
    cfg = config()
    if not cfg: return {"enabled": False}
    m = load(); rate = _rate(cfg, m); fs = m["files"].values(); disks = []
    for r in cfg["roots"]:
        try: disks.append({"root": r, "free_gb": round(shutil.disk_usage(r).free / GB, 1), "atime_works": atime_works(r)})
        except OSError: disks.append({"root": r, "free_gb": None, "atime_works": False})
    cloud = [{"path": e["path"], "name": os.path.basename(e["path"]), "gb": round(e["size"] / GB, 2), "eta_min": eta_min(e["size"], rate), "last_used": e.get("last_used")} for e in fs if e.get("state") == "cloud"]
    return {"enabled": True, "min_free_gb": cfg["min_free_gb"], "disks": disks, "tracked": len(m["files"]), "both": sum(1 for e in fs if e.get("state") == "both"), "pinned": sum(1 for e in fs if e.get("pinned")),
            "with_recorded_use": sum(1 for e in fs if e.get("last_used")), "rate_mb_s": rate, "rate_measured": bool(m.get("rate_mb_s")), "cloud": sorted(cloud, key=lambda c: c["name"].lower()), "job": dict(_job)}

# ---------- API
def _start(kind, path, work):
    global _job
    with _lock:
        if _job.get("state") == "running": raise HTTPException(409, f"already busy: {_job.get('kind')} of {os.path.basename(_job.get('path', ''))}")
        _job = {"state": "running", "kind": kind, "path": path, "started": time.time()}
    def go():
        global _job
        try: r = work(); out = {"state": "done", "kind": kind, "path": path, "result": r}
        except RotationError as e: out = {"state": "error", "kind": kind, "path": path, "error": str(e)}
        except Exception as e: out = {"state": "error", "kind": kind, "path": path, "error": f"{type(e).__name__}: {str(e)[:200]}"}
        _job = out
    threading.Thread(target=go, daemon=True).start()
    return {"state": "running", "kind": kind, "path": path}

async def _target(req):
    cfg = config()
    if not cfg: raise HTTPException(409, "rotation is off: add a remote and roots to rotation.json")
    try: b = await req.json()
    except ValueError: raise HTTPException(400, "send a JSON object") from None
    if not isinstance(b, dict) or not isinstance(b.get("path"), str): raise HTTPException(400, "send the model's path")
    if b["path"] not in load()["files"]: raise HTTPException(404, "that file is not a tracked model")
    return b, cfg

@router.get("/api/rotation/status")
def api_status(): return status()

@router.post("/api/rotation/fetch")
async def api_fetch(req: Request):
    b, cfg = await _target(req)
    return _start("fetch", b["path"], lambda: fetch(b["path"], cfg))

@router.post("/api/rotation/offload")
async def api_offload(req: Request):
    b, cfg = await _target(req)
    if b.get("confirm") is not True: raise HTTPException(400, "offloading removes the local copy after a verified upload: send confirm: true")
    return _start("offload", b["path"], lambda: offload(b["path"], yes=True, cfg=cfg))

# ---------- command line
def _print_plan(p, out=sys.stdout):
    print(f"Target: {p['target_free_gb']:.0f} GB free per disk. {p['order']}. Nothing has been moved.", file=out)
    for d in p["disks"]: print(f"  {d['root']}: {d['free_gb']} GB free, {d['short_gb']} GB short, plan frees {d['would_free_gb']} GB, still short {d['still_short_gb']} GB", file=out)
    print(f"Would move {len(p['moves'])} files, {p['total_gb']} GB ({p['no_known_source']} with no known source).", file=out)
    for r in p["moves"]: print(f"  {r['gb']:8.2f} GB  {r['how']:15}  {r['path']}", file=out)
    reasons = {}
    for r in p["refused"]:
        for w in r["why"]:
            k = re.sub(r"\d+", "N", w); reasons.setdefault(k, [0, 0.0]); reasons[k][0] += 1; reasons[k][1] += r["gb"]
    print(f"Refused {len(p['refused'])} files, {sum(r['gb'] for r in p['refused']):.1f} GB:", file=out)
    for k, (n, gb) in sorted(reasons.items(), key=lambda x: -x[1][1]): print(f"  {n:5d} files {gb:8.1f} GB  {k}", file=out)
    for r in p["refused"]: print(f"  {r['gb']:8.2f} GB  {'; '.join(r['why'])}  {r['path']}", file=out)

def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m studio.rotation", description="Move model weights to a cloud remote and back, verified.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status"); sub.add_parser("scan")
    p = sub.add_parser("plan"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("offload"); p.add_argument("path"); p.add_argument("--yes", action="store_true", help="remove the local copy after a verified upload"); p.add_argument("--source", help="where this model can be downloaded again")
    for name in ("fetch", "pin", "unpin"): sub.add_parser(name).add_argument("path")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "status": print(json.dumps(status(), indent=1))
        elif a.cmd == "scan":
            fs = scan(); print(f"{len(fs)} models tracked, {sum(1 for e in fs.values() if e['state'] == 'cloud')} only in the cloud")
        elif a.cmd == "plan":
            r = plan()
            if a.json: print(json.dumps(r, indent=1))
            else: _print_plan(r)
        elif a.cmd == "offload": print(json.dumps(offload(a.path, yes=a.yes, source=a.source), indent=1))
        elif a.cmd == "fetch": print(json.dumps(fetch(a.path), indent=1))
        else: print(json.dumps(set_pinned(a.path, a.cmd == "pin"), indent=1))
    except RotationError as e:
        print(f"refused: {e}" if isinstance(e, Refused) else f"failed: {e}", file=sys.stderr); return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
