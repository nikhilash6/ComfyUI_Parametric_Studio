#!/usr/bin/env python3
"""Pack Lab's catalogue: the reviewed picks and the do-not-install list, cut down to what a stranger needs, into studio/pack_lab_picks.json.
Goes in: pack name, section, action, what it adds, nodes, model needs, licence, risk notes, sandbox result. The packs flagged in review go in only as salted hashes: naming third parties without the evidence is not fair to them, and some flags come from a script alone. A flagged pack is dropped from the picks too. The salt is public, so this keeps names off the page; it would not stop someone hashing a list of candidate names.
Stays out: scores, the notes on what is in this box's own Lab or live, and any sentence that names a private folder or file. Fails if a folder path survives.
Usage: build_pack_picks.py PICKS_DIR"""
import glob, hashlib, json, os, re, secrets, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "studio" / "pack_lab_picks.json"
PRIVATE = re.compile(r"\bvenv\b|/mnt/|/home/|~/|nodepack_library|knowledge_base|sampling_atlas|\bledger\b|\bLedger\b|\bour Lab\b|\bbox\b|\blive\b|\bLive\b|\bT8\b.*\bon box\b", re.I)
FIELDS = {"Adds": "adds", "Adds (idea)": "adds", "Idea to borrow": "adds", "Nodes": "nodes", "Model needs": "needs", "Licence (as stated in repo)": "licence", "Risk evidence": "risk", "Why not install": "risk", "Note": "note"}


def clean(text):
    """Drops any sentence naming something private, and reword what was addressed to the founders."""
    text = re.sub(r"[Ff]ounder (review needed|should confirm|needs to read)[^.;]*", "read it yourself before relying on it", text); text = re.sub(r"\b(needs|need) founder\b[^.;]*", "needs reading first", text); text = re.sub(r"[Ff]ounder", "owner", text)
    text = re.sub(r"(?<=\d),(?=\d)", ", ", text)     # a list of line numbers can read like a phone number to the privacy scan
    keep = [s for s in re.split(r"(?<=[.;])\s+", text) if not PRIVATE.search(s)]
    return " ".join(keep).strip()


def main(root):
    picks = {}
    for f in sorted(glob.glob(os.path.join(root, "[0-9]*.md"))):
        t = open(f, encoding="utf-8").read(); section = re.sub(r"^#\s*\d+\s*", "", t.splitlines()[0]).split(":")[0].strip()
        for m in re.finditer(r"^### \d+\. (\S+)\s+\[([^\]]+)\]\n((?:- .*\n?)*)", t, re.M):
            pack, action = m[1], m[2].split(" (")[0].strip(); row = picks.setdefault(pack, {"pack": pack, "repo": pack.replace("__", "/", 1), "action": action, "sections": [], "sandbox": "untested"})
            if section not in row["sections"]: row["sections"].append(section)
            if action == "install-candidate": row["action"] = action
            for line in m[3].splitlines():
                k, _, v = line[2:].partition(":"); v = v.strip()
                if k.strip() == "Sandbox": w = v.lower(); row["sandbox"] = "failed" if w.startswith("failed") else "ok" if w.startswith("ok") else "no nodes seen" if "no nodes" in w[:12] else "untested"
                elif k.strip() in FIELDS and FIELDS[k.strip()] not in row: row[FIELDS[k.strip()]] = clean(v)
    bad = [b["pack"] for b in json.load(open(os.path.join(root, "data", "DO_NOT_INSTALL_2026-11-01.json"), encoding="utf-8"))]
    try: salt = json.loads(OUT.read_text(encoding="utf-8")).get("flag_salt")
    except (OSError, ValueError): salt = None
    salt = salt or secrets.token_hex(16); kept = [p for k, p in sorted(picks.items(), key=lambda kv: kv[0].lower()) if k.lower() not in {b.lower() for b in bad}]
    data = {"about": "Picks reviewed from each pack's text: no pack code was run for these notes. Some packs were flagged in review and are refused. That list is not exhaustive, so a pack that is not refused has not been cleared.", "made": "2026-11-01", "picks": kept, "flag_salt": salt, "flagged": sorted(hashlib.sha256(f"{salt}:{b.lower()}".encode()).hexdigest() for b in bad)}
    text = json.dumps(data, indent=0, ensure_ascii=False)
    if re.search(r"/mnt/|/home/", text): sys.exit("a folder path survived")
    named = sum(1 for b in bad if b.lower() in text.lower() or b.replace("__", "/").lower() in text.lower())
    if named: sys.exit(f"{named} flagged packs are still named in the output")
    OUT.write_text(text, encoding="utf-8"); print(len(kept), "picks,", sum(p["action"] == "install-candidate" for p in kept), "install candidates,", len(bad), "flagged as hashes,", OUT.stat().st_size >> 10, "KB")


if __name__ == "__main__": main(sys.argv[1])
