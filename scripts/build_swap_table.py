#!/usr/bin/env python3
"""Writes the README's "Swap the person, on any model" table from studio/swap_showcase.json, the same file the studio's Swap page reads, so the two cannot drift.
Only rows whose graph and render are both in the repo are shown as done; the rest are listed as coming, with no picture. tests/test_swap_showcase.py fails if the README is stale.
Usage: build_swap_table.py [--check]"""
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "studio" / "swap_showcase.json"; WEB = "studio/web/"; README = REPO / "README.md"
START, END = "<!-- swap-table:start (scripts/build_swap_table.py writes this) -->", "<!-- swap-table:end -->"


def done(r):
    p = r.get("proof") or {}
    return r["status"] == "rendered" and (REPO / r["graph"]).is_file() and bool(p) and (REPO / WEB / p["src"]).is_file() and (REPO / WEB / p["poster"]).is_file()


def table():
    rows = json.loads(DATA.read_text(encoding="utf-8"))["rows"]
    shown = [r for r in rows if done(r)]
    out = [f'{len(shown)} graphs with a render, on {len({r["family"] for r in shown})} model families ({", ".join(dict.fromkeys(r["family"] for r in shown))}).', "", "| Render | Swap | Core model | What it swaps | Out | Graph and proof | Licence |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        if not done(r): continue
        p = r["proof"]; src, poster = WEB + p["src"], WEB + p["poster"]
        pic = f'[<img src="{poster}" width="120" alt="{r["name"]}: {r["looked"]}">]({src})'
        took = f'{p["seconds"]:g} s{" (swap step)" if p.get("step") == "swap" else ""}, peak {p["peak_vram_gib"]:g} GiB'
        out.append(f'| {pic} | **{r["name"]}** | {r["core"]} | {r["swaps"]} | {"video" if r["output"] == "video" else "still"} | [graph]({r["graph"]}) · [render]({src}) · record `{p["record"]}` ({p["key"]}), {took}. {r["flaw"]} | {r["licence"]} |')
    later = [r for r in rows if not done(r)]
    if later:
        out += ["", "**Coming** (graph written, proof render under way; each gets a row above once its render is on record): " + "; ".join(f'**{r["name"]}** ({r["core"]}; {r["output"]}; swaps {r["swaps"]})' for r in later) + "."]
    return "\n".join(out)


def main():
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text: sys.exit(f"README.md has no {START} ... {END} block")
    head, rest = text.split(START, 1); _, tail = rest.split(END, 1)
    new = head + START + "\n" + table() + "\n" + END + tail
    if "--check" in sys.argv: sys.exit(0 if new == text else "README.md's swap table is stale: run scripts/build_swap_table.py")
    README.write_text(new, encoding="utf-8"); print("README swap table written")


if __name__ == "__main__":
    main()
