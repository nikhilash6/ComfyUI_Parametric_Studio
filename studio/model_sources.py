"""Where a model file comes from, by file name, from the studio's own two lists: the goal manifest (with its published hash) and the family templates. A file on neither list has no known source, and callers say so."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_cache: dict = {}


def sources() -> dict:
    """{file name: {url, dir, sha256, size_gb, gated}}. A name in both lists keeps the manifest's row, which has a hash."""
    if "d" in _cache: return _cache["d"]
    out = {}
    try:
        for f in json.loads((HERE / "family_status.json").read_text(encoding="utf-8")).get("families", {}).values():
            for t in f.get("templates") or []:
                for m in (t.get("models") or []) if isinstance(t, dict) else []:
                    if m.get("name") and m.get("url"): out.setdefault(m["name"].split("/")[-1], {"url": m["url"], "dir": m.get("dir"), "sha256": None, "size_gb": None, "gated": False})
    except (OSError, ValueError): pass
    try:
        for g in json.loads((HERE / "models_manifest.json").read_text(encoding="utf-8")).get("goals", {}).values():
            for m in g.get("files") or []:
                name = str(m.get("dest") or m.get("path") or "").split("/")[-1]
                if name and m.get("repo") and m.get("path"): out[name] = {"url": f"https://huggingface.co/{m['repo']}/resolve/main/{m['path']}", "dir": str(m.get("dest") or "").rsplit("/", 1)[0] or None, "sha256": m.get("sha256"), "size_gb": m.get("size_gb"), "gated": bool(m.get("gated"))}
    except (OSError, ValueError): pass
    _cache["d"] = out
    return out


def source(name: str):
    return sources().get(str(name).replace("\\", "/").split("/")[-1])
