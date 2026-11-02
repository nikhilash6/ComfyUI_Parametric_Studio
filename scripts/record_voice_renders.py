#!/usr/bin/env python3
"""Moves map rows to rendered when the Voices page's proof says a render really read that file. A render under the page's word bar stays out, with its number in next_step.
Usage: record_voice_renders.py MAP.tsv. Rewrites the file in place, atomically. Only speech rows it can prove are touched."""
import csv, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def proofs(cat=None, proof=None):
    """{path under the models folder: proof text} for every file a passed render read."""
    cat = cat or json.loads((ROOT / "studio" / "voice_models.json").read_text(encoding="utf-8")); proof = proof or json.loads((ROOT / "studio" / "voice_proof.json").read_text(encoding="utf-8"))
    bar = proof.get("min_match", 60); out = {}; low = {}
    for m in cat["models"]:
        r = (proof.get("renders") or {}).get(m["id"])
        if not r:
            if m.get("blocked"):
                for f in m.get("files") or []: low.setdefault(f, f"{m['label']}: {m['blocked']}")
            continue
        what = f"rendered voices/{m['id']} ({r.get('secs')} s, peak {r.get('peak_gib')} GB, Whisper {r.get('match_pct')}% of the words, no person listened)"
        for f in m.get("files") or []:
            if r.get("match_pct", 0) >= bar: out.setdefault(f, what)
            else: low[f] = f"Rendered voices/{m['id']}, but Whisper heard only {r.get('match_pct')}% of the words."
    for v, r in (proof.get("kokoro") or {}).items():
        f = f"_by_repo/1038lab__KokoroTTS/voices/{v}.pt"
        if r.get("match_pct", 0) >= bar: out[f] = f"rendered voices/kokoro/{v} ({r.get('lang')}, Whisper {r.get('match_pct')}% of the words, no person listened)"
        else: low[f] = f"Rendered voices/kokoro/{v}, but Whisper heard only {r.get('match_pct')}% of the {r.get('lang')} line."
    return out, low


def apply(rows, good, low, root="/"):
    moved = 0
    for r in rows:
        rel = os.path.relpath(r["disk_path"], root) if r.get("disk_path") else ""
        hit = next((k for k in good if rel.endswith("/" + k)), None)
        if hit and r["status"] != "rendered": r.update(status="rendered", proof=good[hit], next_step=""); moved += 1
        elif not hit and r["status"] != "rendered":
            lo = next((k for k in low if rel.endswith("/" + k)), None)
            if lo: r["next_step"] = low[lo]
    return moved


def main(path):
    with open(path, newline="", encoding="utf-8") as f: rd = csv.DictReader(f, delimiter="\t"); cols = rd.fieldnames; rows = list(rd)
    good, low = proofs(); moved = apply(rows, good, low); tmp = path + f".{os.getpid()}.tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f: w = csv.DictWriter(f, cols, delimiter="\t"); w.writeheader(); w.writerows(rows)
    os.replace(tmp, path); print("moved", moved, "rendered now", sum(1 for r in rows if r["status"] == "rendered"), "of", len(rows))


if __name__ == "__main__": main(sys.argv[1])
