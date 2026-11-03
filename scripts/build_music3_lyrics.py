#!/usr/bin/env python3
"""Adds the finished lyrics of the owner's Music 3 genre batch to the style library: studio/music3_lyrics.json.

The batch (toolbox/audio-music/music3-genres) wrote lyrics for 256 of its 645 styles with a local LLM. Each set is screened
twice before it is kept: by the rules below (the studio's own safe-for-work words, a wider explicit list, real artists'
names), and by a full read of every set (a review file: {"fail": [{"style_id", "check", "evidence", "why"}], ...}).
A set either check fails is dropped; only its id and the reason are kept, never its text.
The batch's render records (QC flags, length) are carried as history: those FLACs are not on disk, and nobody has listened.
Usage: python3 scripts/build_music3_lyrics.py MANIFEST RESULTS_JSONL REVIEW_JSON [REVIEW_JSON ...]"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from studio import sfw

EXPLICIT = re.compile(r"\b(cocaine|heroin|meth|crack pipe|bitch\w*|whore\w*|slut\w*|cunt\w*|dick\w*|pussy|cock\w*|shit\w*|motherf\w*|nigg\w*|fag\w*|retard\w*|rape\w*|orgasm\w*|horny|strip(per|club)|blowjob|cum\b)", re.I)
EXPLICIT_ZH = re.compile(r"(做爱|性爱|裸体|毒品|吸毒|妈的|他妈|操你|婊子|强奸)")
#: Real musicians whose names an LLM reaches for when it writes "in the style of". Word-bounded, case-insensitive. Not complete: the full read is the main check.
ARTISTS = ["Taylor Swift", "Beyonce", "Beyoncé", "Drake", "Rihanna", "Adele", "Eminem", "Kanye", "Jay-Z", "Jay Z", "Elvis", "Presley", "Beatles", "Lennon", "McCartney", "Madonna", "Prince",
           "Michael Jackson", "Whitney", "Mariah", "Bob Dylan", "Dylan", "Springsteen", "Johnny Cash", "Dolly Parton", "Willie Nelson", "Garth Brooks", "Shania", "Kenny Rogers", "Hank Williams",
           "Bob Marley", "Marley", "Tupac", "2Pac", "Biggie", "Notorious B.I.G", "Snoop", "Dr. Dre", "Kendrick", "Nicki Minaj", "Cardi B", "Lady Gaga", "Bruno Mars", "Ed Sheeran", "Billie Eilish",
           "Ariana", "Justin Bieber", "Bieber", "Weeknd", "Post Malone", "Dua Lipa", "Harry Styles", "BTS", "Blackpink", "BLACKPINK", "Bad Bunny", "Shakira", "J Balvin", "Daddy Yankee",
           "Frank Sinatra", "Sinatra", "Miles Davis", "Coltrane", "Louis Armstrong", "Ella Fitzgerald", "Billie Holiday", "Nina Simone", "Aretha", "Stevie Wonder", "Marvin Gaye", "James Brown",
           "Freddie Mercury", "Queen", "Led Zeppelin", "Pink Floyd", "Rolling Stones", "Jagger", "Nirvana", "Kurt Cobain", "Metallica", "AC/DC", "Bon Jovi", "Coldplay", "Radiohead", "U2", "Bono",
           "Daft Punk", "Avicii", "Skrillex", "Calvin Harris", "David Guetta", "Tiesto", "Kraftwerk", "Bowie", "Elton John", "ABBA", "Fela", "Burna Boy", "Wizkid", "Davido", "Tems",
           "Jay Chou", "周杰伦", "邓丽君", "王菲", "张学友", "林俊杰", "陈奕迅", "五月天", "Teresa Teng", "Faye Wong", "Jacky Cheung", "JJ Lin", "Eason Chan", "Mayday", "Leslie Cheung", "张国荣", "Beyond"]
ARTIST_RE = re.compile(r"(?<![\w])(" + "|".join(re.escape(a) for a in sorted(ARTISTS, key=len, reverse=True)) + r")(?![\w])", re.I)
CASE_SENSITIVE = {"Queen", "Prince", "Drake", "Beyond", "Mayday", "Whitney", "Dylan", "Marley", "Ariana", "Elvis"}       # ordinary words or first names unless capitalised as a name


def rule_problems(text):
    out = []
    if sfw.flagged(text): out.append(("explicit", "matches the studio's safe-for-work word list"))
    m = EXPLICIT.search(text) or EXPLICIT_ZH.search(text)
    if m: out.append(("explicit", f"explicit word: {m.group(0)}"))
    for m in ARTIST_RE.finditer(text):
        name = m.group(0); canon = next((a for a in ARTISTS if a.lower() == name.lower()), name)
        if canon in CASE_SENSITIVE and name != canon: continue
        if canon in CASE_SENSITIVE:      # a capitalised common word at the start of a line is just a line
            start = text.rfind("\n", 0, m.start()) + 1
            if text[start:m.start()].strip() == "": continue
        out.append(("real_name", f"names {name}")); break
    return out


def main():
    if len(sys.argv) < 4: sys.exit(__doc__)
    man = json.loads(Path(sys.argv[1]).read_text()); res = {}
    for line in Path(sys.argv[2]).read_text().splitlines():
        try: r = json.loads(line)
        except ValueError: continue
        if r.get("via") or not r.get("style_id"): continue
        res[r["style_id"]] = r                     # the last QC record of a style wins (re-renders append)
    review, read = {}, 0
    for f in sys.argv[3:]:
        d = json.loads(Path(f).read_text()); read += int(d.get("read") or 0)
        for x in d.get("fail") or []: review.setdefault(x["style_id"], []).append((x.get("check") or "review", f"{x.get('why', '')}: {x.get('evidence', '')}".strip(": ")))
    lib = json.loads((ROOT / "studio" / "music3_styles.json").read_text()); ids = {st["id"] for f in lib["families"] for st in f["styles"]}
    sets = [s for s in man["styles"] if s.get("lyrics")]; kept, dropped = {}, []
    for s in sets:
        why = rule_problems(s["lyrics"]) + review.get(s["style_id"], [])
        if s["style_id"] not in ids: why.append(("not_in_library", "the style is not in the studio's style library (children's styles are left out of it)"))
        if why: dropped.append({"style_id": s["style_id"], "checks": sorted({c for c, _ in why}), "why": "; ".join(w for _, w in why)[:300]}); continue
        r = res.get(s["style_id"]) or {}
        kept[s["style_id"]] = {"template_id": s["template_id"], "language": s["language"], "vocal": s.get("vocal"), "lyrics": s["lyrics"], "seed": s.get("seed"), "target_s": s.get("target_s"),
                               "sung_lines": (s.get("lyrics_meta") or {}).get("sung_lines"),
                               "batch_render": {"status": r.get("status"), "flags": r.get("flags") or [], "seconds": r.get("duration_s"), "when": r.get("t"), "file_on_disk": False} if r else None}
    by = {}
    for x in dropped:
        for c in x["checks"]: by[c] = by.get(c, 0) + 1
    out = {"schema": 1, "about": "Finished lyrics for styles in the Music 3 style library, from the owner's genre batch. Generated by scripts/build_music3_lyrics.py; do not edit by hand.",
           "written_by": f"a local LLM ({man.get('lyric_model')}) in the owner's batch, 2026-10-09 to 10-11",
           "screened": {"rules": "the studio's safe-for-work words, a wider explicit list in English and Chinese, and a list of real artists' names",
                        "read": f"every set read in full for real names, quoted lyrics and explicit content ({read} read)", "human_read": False},
           "counts": {"in_batch": len(man["styles"]), "with_lyrics": len(sets), "kept": len(kept), "dropped": len(dropped), "dropped_by_check": by,
                      "batch_rendered_ok": sum(1 for v in kept.values() if (v["batch_render"] or {}).get("status") == "ok")},
           "note": "The batch rendered these songs on the old stack; the files are not on this machine, and nobody has listened to them. A render record says it finished and lists its machine QC flags, nothing more.",
           "sets": kept, "dropped": dropped}
    (ROOT / "studio" / "music3_lyrics.json").write_text(json.dumps(out, indent=0, ensure_ascii=False) + "\n")
    print(json.dumps(out["counts"]))


if __name__ == "__main__": main()
