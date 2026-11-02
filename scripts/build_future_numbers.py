#!/usr/bin/env python3
"""The Future page's numbers: totals from the model use map, written to studio/web/future_numbers.json. The map stays private; only these totals ship. build_model_use_map.py calls this each time it writes the map, or run it alone:
python scripts/build_future_numbers.py --map path/to/MODEL_USE_MAP.tsv"""
import argparse, collections, csv, json, re, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "studio" / "web" / "future_numbers.json"
STATUSES = ("rendered", "graph", "reachable", "unreachable", "not_on_disk")

def numbers(rows, when=None):
    """Totals by status, over every file and over the text-to-speech files. A status the map doesn't know is refused rather than dropped, so the totals always add up."""
    rows = list(rows); c = collections.Counter(r["status"] for r in rows); tts = collections.Counter(r["status"] for r in rows if r["function"].startswith("Text-to-speech"))
    odd = set(c) - set(STATUSES)
    if odd: raise SystemExit(f"the map has a status this script doesn't know: {sorted(odd)}")
    n = {"total": len(rows), **{s: c[s] for s in STATUSES}, "tts_total": sum(tts.values()), **{f"tts_{s}": tts[s] for s in STATUSES}}
    n["all_rendered"] = n["total"] > 0 and n["rendered"] == n["total"]; n["as_of"] = when or time.strftime("%-d %B %Y"); return n
def write(map_path, out=OUT, when=None):
    with open(map_path, encoding="utf-8", newline="") as f: n = numbers(csv.DictReader(f, delimiter="\t"), when)
    Path(out).write_text(json.dumps(n, indent=1) + "\n", encoding="utf-8"); return n
if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--map", required=True); a.add_argument("--out", default=str(OUT)); o = a.parse_args(); print(write(o.map, o.out))
