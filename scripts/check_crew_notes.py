#!/usr/bin/env python3
"""Check the crew's hand-written and generated state notes: every paragraph carries a proof label, every cited file and line exists in this repo, and nothing private or not safe for work is in the text.
Labels, written in square brackets at the end of a paragraph: [code: path:line] read in the source, [test: path] a test in this repo holds it, [run: path] a recorded run stored in this repo, [docs: path] a document in this repo, [claim: who] someone says so and it was not checked, [inference] our reasoning.
Usage: python3 scripts/check_crew_notes.py [--root REPO]. Exit 1 on any problem. Standard library only."""
import argparse, re, sys
from pathlib import Path

LABEL = re.compile(r"\[(code|test|run|docs|claim|inference)(?::\s*([^\]]*))?\]")
NEEDS_PATH = ("code", "test", "run", "docs")
CITE = re.compile(r"^([\w./+-]+?)(?::(\d+)(?:-(\d+))?)?$")
CHECKED_NAMES = ("NOW.md", "STATE.md", "GUIDE.md")     # in model_families/*/dossier: older notes there came from the knowledge base and carry no labels
PRIVATE = re.compile(r"/" r"mnt/|/" r"home/|~/|127\.0\.0\.1|localhost|\b0\.0\.0\.0\b|:(?:80|81|82|83)\d\d\b|:11434\b|\bour box\b|\bthis box\b|\bthis machine\b|\bowner\b|\bfounders?\b", re.I)
UNSAFE = re.compile(r"\bnsfw\b|\bnude\b|\bnaked\b|\blingerie\b|\bporn\w*|\bhentai\b|\berotic\w*|\btopless\b|\bfetish\b|\bgore\b", re.I)
PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|\bFIXME\b")


def note_files(root):
    notes = Path(root) / "studio" / "crew_notes"
    out = sorted((notes / "studio_topics").rglob("*.md")) if (notes / "studio_topics").is_dir() else []
    for name in CHECKED_NAMES: out += sorted((notes / "model_families").glob(f"*/dossier/{name}"))
    out += sorted((notes / "parts").rglob("*.md")) if (notes / "parts").is_dir() else []
    return out


def paragraphs(text):
    """(line number, paragraph) for each paragraph that makes a statement. Headings and table header rows state nothing."""
    out, start, cur = [], 1, []
    for i, line in enumerate(text.splitlines() + [""], 1):
        if line.strip(): cur.append(line); start = start if len(cur) > 1 else i; continue
        if cur:
            body = "\n".join(x for x in cur if not x.startswith("#"))
            if body.strip(): out.append((start, body))
        cur = []
    return out


def check_cite(root, kind, cite):
    probs = []
    for one in re.split(r"[,;]\s*", (cite or "").strip()):
        if not one: continue
        m = CITE.match(one)
        if not m: probs.append(f"cannot read the citation '{one}'"); continue
        path = Path(root) / m.group(1)
        if not path.exists(): probs.append(f"cites a file that is not in the repo: {m.group(1)}"); continue
        if m.group(2):
            if not path.is_file(): probs.append(f"cites a line of something that is not a file: {one}"); continue
            n = sum(1 for _ in open(path, "rb")); last = int(m.group(3) or m.group(2))
            if last > n: probs.append(f"cites line {last} of {m.group(1)}, which has {n} lines")
    return probs


def check_file(root, path):
    text = Path(path).read_text(encoding="utf-8"); rel = str(Path(path).relative_to(root)); probs = []
    for rx, why in ((PRIVATE, "private or box-specific wording"), (UNSAFE, "not safe for work wording"), (PLACEHOLDER, "a placeholder")):
        m = rx.search(text)
        if m: probs.append(f"{rel}:{text.count(chr(10), 0, m.start()) + 1}: {why}: '{m.group(0)}'")
    for line, para in paragraphs(text):
        found = LABEL.findall(para)
        if not found: probs.append(f"{rel}:{line}: paragraph has no proof label"); continue
        for kind, cite in found:
            if kind in NEEDS_PATH and not cite.strip(): probs.append(f"{rel}:{line}: [{kind}] names no file")
            if kind in NEEDS_PATH: probs += [f"{rel}:{line}: {p}" for p in check_cite(root, kind, cite)]
    return probs


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent)); a = ap.parse_args(argv)
    files = note_files(a.root); probs = [p for f in files for p in check_file(a.root, f)]
    for p in probs: print(p)
    print(f"{len(files)} note files checked, {len(probs)} problems"); return 1 if probs else 0


if __name__ == "__main__": sys.exit(main())
