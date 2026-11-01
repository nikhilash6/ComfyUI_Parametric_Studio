"""Model files that landed since the last scan. Skips partials, download temp folders and any file still changing: a file counts once it is older than --settle seconds and its size matches the previous scan, or it has settled for an hour. python scripts/scan_new_models.py --root DIR [--root DIR] --state scan.json [--out new.tsv]"""
import argparse, json, os, sys, time
from pathlib import Path

WEIGHTS = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".sft", ".onnx", ".pkl", ".tar")
PARTIAL = (".incomplete", ".part", ".partial", ".tmp", ".aria2", ".lock")
SKIP_DIRS = {"_workbench", ".cache", "__pycache__", ".git", "dl_tmp", "tmp", "_archive"}


def is_temp_dir(name):
    return name in SKIP_DIRS or name.startswith(("dl_", "tmp", ".tmp")) or name.endswith((".incomplete", ".tmp"))


def walk(root):
    for dp, dn, fs in os.walk(root, followlinks=False):
        dn[:] = [d for d in dn if not is_temp_dir(d)]
        for f in fs:
            if f.endswith(WEIGHTS) and not f.endswith(PARTIAL): yield os.path.join(dp, f)


def scan(roots, seen, *, settle=120, now=None):
    """-> (new settled files [(path, size)], state to keep). `seen` is {path: size} from the last scan; a file seen at another size is still arriving."""
    now = now or time.time(); new, state = [], {}
    for r in roots:
        for p in walk(r):
            try: st = os.stat(p)
            except OSError: continue
            age = now - st.st_mtime; old = seen.get(p)
            if isinstance(old, dict) and old.get("done"): state[p] = old; continue
            if age >= settle and (old == st.st_size or age > 3600 or old is None and age > settle * 5):
                new.append((p, st.st_size)); state[p] = {"done": True, "size": st.st_size}
            else: state[p] = st.st_size
    return new, state


def main(argv=None):
    a = argparse.ArgumentParser(); a.add_argument("--root", action="append", required=True); a.add_argument("--state", required=True); a.add_argument("--out"); a.add_argument("--first-as-baseline", action="store_true"); a = a.parse_args(argv)
    try: seen = json.load(open(a.state))
    except (OSError, ValueError): seen = {}
    new, state = scan([r for r in a.root if os.path.isdir(r)], seen)
    json.dump(state, open(a.state, "w"))
    if a.out:
        with open(a.out, "w") as f:
            for p, s in sorted(new): f.write(f"{p}\t{s}\n")
    print(len(new), "new files,", round(sum(s for _, s in new) / 1e9, 1), "GB,", sum(1 for v in state.values() if not isinstance(v, dict)), "still arriving")
    if not a.first_as_baseline:
        for p, s in sorted(new, key=lambda x: -x[1])[:40]: print(round(s / 1e9, 2), p)


if __name__ == "__main__": main()
