#!/usr/bin/env python3
"""Download the model files a goal, a family, a graph or the whole studio needs, into ComfyUI's models folder.

Standard library only, so the installer can run it before anything is installed. The list is studio/models_manifest.json ("files"): each file's official
link, size, SHA-256, licence and the folder it goes in. Downloads resume from a .part file, are checked against the SHA-256 when one is published, and
files already in place are skipped. A gated repository needs you to accept its licence on its Hugging Face page and to set HF_TOKEN in the environment;
the token is read from the environment only, sent only to huggingface.co and never written anywhere.

Examples:
  python3 scripts/get_models.py --list                         # goals and families you can ask for
  python3 scripts/get_models.py --for image --dry-run          # what the Image goal needs, and what is missing
  python3 scripts/get_models.py --for family:Anima --models-dir ~/ComfyUI/models
  python3 scripts/get_models.py --for all --dry-run            # every file the studio uses
  python3 scripts/get_models.py --for workflows/music3_api     # the files one graph names"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from studio import resumable  # noqa: E402  (standard library only)

MANIFEST = REPO / "studio" / "models_manifest.json"
EXIT_OK, EXIT_FAILED, EXIT_USAGE = 0, 1, 2


def load(path=MANIFEST):
    with open(path, encoding="utf-8") as f:
        man = json.load(f)
    if not man.get("files"):
        raise SystemExit("studio/models_manifest.json has no 'files' list; run scripts/build_model_links.py first")
    return man


def _matches(f, want, goals):
    w = want.strip()
    low = w.lower()
    if low == "all": return True
    if low.startswith("family:"):
        fam = low[7:]
        return (f.get("family") or "").lower() == fam or any(u.lower().startswith(f"family:{fam}/") for u in f["used_by"])
    if low.startswith("goal:") or w in goals:
        g = w.split(":", 1)[1] if low.startswith("goal:") else w
        return f"goal:{g}" in f["used_by"]
    return w in (f["filename"], Path(f["filename"]).name) or any(u == w or u.endswith(":" + w) for u in f["used_by"])


def select(man, wants):
    """-> files matching any of the comma-separated wants, and the wants that matched nothing."""
    goals = set(man.get("goals") or {})
    picked, unmatched = [], []
    for want in [w for w in wants.split(",") if w.strip()]:
        hits = [f for f in man["files"] if _matches(f, want, goals)]
        if not hits: unmatched.append(want)
        for f in hits:
            if f not in picked: picked.append(f)
    return picked, unmatched


def dest_path(models_dir, f):
    rel = f.get("dest") or (f"{f['folder']}/{Path(f['filename']).name}" if f.get("folder") else None)
    return (Path(models_dir) / rel) if rel else None


def sha256_of(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while b := fh.read(chunk): h.update(b)
    return h.hexdigest()


def plan(files, models_dir, token_set, verify=False):
    """-> [(file, action, why)]. action is one of: get, have, gated, nosource, nofolder, differs. Nothing is changed and nothing is fetched."""
    out = []
    for f in files:
        dest = dest_path(models_dir, f)
        if f.get("source") not in ("huggingface", "github", "modelscope") or not f.get("url"):
            out.append((f, "nosource", f.get("note") or "no public source")); continue
        if dest is None:
            out.append((f, "nofolder", "no folder is recorded for it")); continue
        if dest.exists():
            size = dest.stat().st_size
            if f.get("size") and size != f["size"]:
                out.append((f, "differs", f"a file of another size ({size} bytes) is already there; left alone")); continue
            if verify and f.get("sha256") and sha256_of(dest) != f["sha256"]:
                out.append((f, "differs", "already there, but its SHA-256 does not match; left alone")); continue
            out.append((f, "have", "already in place")); continue
        if f.get("gated") and not token_set:
            out.append((f, "gated", "gated: accept the licence on its page, then set HF_TOKEN")); continue
        out.append((f, "get", ""))
    return out


def gib(n): return f"{(n or 0) / 2**30:.2f}"


def print_plan(rows, models_dir):
    print(f"Models folder: {models_dir}")
    for f, action, why in rows:
        size = gib(f.get("size")) if f.get("size") else "?"
        lic = f.get("licence") or "unknown licence"
        flags = (" NON-COMMERCIAL" if f.get("noncommercial") else "") + (" gated" if f.get("gated") else "")
        mark = {"get": "GET ", "have": "have", "gated": "skip", "nosource": "none", "nofolder": "skip", "differs": "skip"}[action]
        print(f"  {mark} {size:>7} GiB  {f.get('dest') or f['filename']}  [{lic}{flags}]" + (f"  ({why})" if why else ""))
        if action == "nosource" and f.get("civitai_url"): print(f"        get it by hand from Civitai: {f['civitai_url']}")
        if action == "get": print(f"        {f['url']}")
    get = [f for f, a, _ in rows if a == "get"]
    print(f"\n{len(get)} to download, {gib(sum(f.get('size') or 0 for f in get))} GiB; "
          f"{sum(1 for _, a, _ in rows if a == 'have')} already in place; "
          f"{sum(1 for _, a, _ in rows if a == 'gated')} gated and skipped; "
          f"{sum(1 for _, a, _ in rows if a == 'nosource')} with no public source; "
          f"{sum(1 for _, a, _ in rows if a in ('differs', 'nofolder'))} left alone.")
    if any(f.get("noncommercial") for f, a, _ in rows if a in ("get", "have")):
        print("Some of these are under a licence the model card marks non-commercial or research-only. Read MODELS.md before using them.")


def download(f, dest, token=None, opener=None, sleep=time.sleep):
    """Fetch one file into dest via dest.part, check its SHA-256 and move it into place. True on success."""
    part = dest.with_name(dest.name + ".part")
    if not f["url"].startswith("https://huggingface.co/"): token = None     # the token is for Hugging Face only
    done = [0]
    started = time.monotonic()

    def progress(n, reset=False):
        done[0] = n if reset else done[0] + n
        if f.get("size"):
            rate = done[0] / max(time.monotonic() - started, 1e-6) / 2**20
            print(f"\r    {done[0] / f['size'] * 100:5.1f}%  {gib(done[0])}/{gib(f['size'])} GiB  {rate:6.1f} MiB/s", end="", flush=True)

    def waiting(fail, tries, seconds, why):
        print(f"\n    connection problem ({why}); waiting {seconds}s, try {fail} of {tries}")

    try:
        resumable.fetch_partial(f["url"], part, token=token, progress=progress, on_wait=waiting, opener=opener, sleep=sleep)
    except resumable.Refused as e:
        msg = "accept the licence on the model page and set HF_TOKEN" if e.status in (401, 403) else "the link did not work"
        print(f"\n    refused ({e.status}): {msg}")
        return False
    except resumable.GaveUp as e:
        print(f"\n    stopped: {e}. What arrived is kept in {part.name}; run the same command again to carry on.")
        return False
    print()
    if f.get("sha256"):
        got = sha256_of(part)
        if got != f["sha256"]:
            print(f"    SHA-256 mismatch for {dest.name}: expected {f['sha256'][:12]}..., got {got[:12]}...; the download was deleted")
            part.unlink(missing_ok=True)
            return False
    part.replace(dest)
    return True


def default_models_dir():
    env = os.environ.get("COMFYUI_MODELS_DIR")
    if env: return Path(env).expanduser()
    for p in (Path.cwd() / "ComfyUI" / "models", Path.cwd() / "models", REPO.parent.parent / "models"):
        if p.is_dir(): return p
    return None


def list_choices(man):
    print("Goals:", ", ".join(sorted(man.get("goals") or {})))
    fams = {}
    for f in man["files"]: fams.setdefault(f.get("family") or "Other", []).append(f)
    print("\nFamilies (use --for family:<name>):")
    for fam in sorted(fams, key=str.lower):
        rows = fams[fam]
        ok = sum(1 for f in rows if f.get("source") in ("huggingface", "github", "modelscope"))
        print(f"  {fam}: {len(rows)} files, {gib(sum(f.get('size') or 0 for f in rows))} GiB" + (f", {len(rows) - ok} with no public source" if ok < len(rows) else ""))


def main(argv=None, opener=None):
    ap = argparse.ArgumentParser(description="Download the model files the studio's goals, families and graphs use.")
    ap.add_argument("--for", dest="want", help="all, a goal (image, video, music...), family:<name>, a graph id (workflows/music3_api) or a file name; comma-separated")
    ap.add_argument("--models-dir", help="ComfyUI's models folder (default: $COMFYUI_MODELS_DIR, else ./ComfyUI/models)")
    ap.add_argument("--dry-run", action="store_true", help="show what would be downloaded; touches no network and changes nothing")
    ap.add_argument("--verify", action="store_true", help="also check the SHA-256 of files already in place (slow for big files)")
    ap.add_argument("--list", action="store_true", help="list the goals and families and exit")
    ap.add_argument("--manifest", default=str(MANIFEST), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    man = load(a.manifest)
    if a.list:
        list_choices(man); return EXIT_OK
    if not a.want:
        ap.print_usage(); print("Say what to fetch with --for (see --list)."); return EXIT_USAGE
    files, unmatched = select(man, a.want)
    if unmatched: print("Nothing matches: " + ", ".join(unmatched) + ". See --list.")
    if not files: return EXIT_USAGE
    models_dir = Path(a.models_dir).expanduser() if a.models_dir else default_models_dir()
    if models_dir is None:
        print("Where is ComfyUI's models folder? Pass --models-dir or set COMFYUI_MODELS_DIR."); return EXIT_USAGE
    token = os.environ.get("HF_TOKEN") or None
    rows = plan(files, models_dir, bool(token), a.verify)
    print_plan(rows, models_dir)
    if a.dry_run: return EXIT_OK
    todo = [f for f, act, _ in rows if act == "get"]
    if not todo: return EXIT_OK
    need = sum(f.get("size") or 0 for f in todo)
    models_dir.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(models_dir).free
    if need and free < need + 2 * 2**30:
        print(f"Not enough free disk: {gib(free)} GiB free, {gib(need)} GiB needed plus 2 GiB to spare."); return EXIT_FAILED
    failed = []
    for i, f in enumerate(todo, 1):
        dest = dest_path(models_dir, f)
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"[{i}/{len(todo)}] {f.get('dest')}  ({gib(f.get('size'))} GiB, {f.get('licence')})")
        if not download(f, dest, token=token, opener=opener): failed.append(f)
    print(f"\nDone: {len(todo) - len(failed)} downloaded, {len(failed)} failed." + (" Run the same command again to retry." if failed else ""))
    return EXIT_FAILED if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
