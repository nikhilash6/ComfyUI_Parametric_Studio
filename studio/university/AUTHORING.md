# Writing a ComfyUniversity lesson

A lesson is one folder, `<level>/CU-nnn-slug/`, with `course.json`, `lesson.md`, `lab.py`, `lab_output.txt` and `quiz.json`.

## course.json
`code`, `title`, `level`, `prereq`, `char`, `hook`, `track` (a slug from tracks.json), `order` (a number, lessons sort by it inside a track), `kit: true` once it has everything below, `graphs` (ids in `graphs/`), `code_refs` (`file:Class.method` or `file:name`, looked up by a test), `verified` and `unchecked`.

`verified` is a list of `{"claim", "how", "ref"}`, where `how` is `source`, `run here`, `docs` or `test`. It is shown to the reader. `unchecked` is a list of plain sentences: everything you say that you could not check. Leave nothing out to look tidier. Don't write `status: "draft"` once a lesson is audited; do leave it if you have not checked it.

## lesson.md
First line `# CU-nnn - Title`. Then `**Objective.** ... Taught by <teacher>.` Then `## ` sections, always including `## What goes wrong`, `## Lab` and `## Sources`.

Embeds, each on a line of its own:
- `{{play:name}}`: a browser lab from `web/university_plays.js`.
- `{{graph:id}}`: a graph file.
- `{{wipe:a.jpg|b.jpg|Label A|Label B|Caption}}`: a before and after, with paths inside `web/`.
- `![Caption](path.jpg)`, `{{video:path.mp4|Caption}}`, `{{audio:path.mp3|Caption}}`.

Rules: no LaTeX, write Unicode. No stray asterisks in prose. No em dashes. Every line in a ```text block inside `## Lab` must appear exactly in `lab_output.txt`. Every link under `## Sources` must have an entry in `sources.json` or `sources.d/*.json`, and you must have opened it.

## lab.py
Plain Python and torch, CPU, fixed seeds, under a minute, at least one `assert`, the same output every run. Imports are limited to the list in `build.py`.

## Graphs
`graphs/<id>.json` is `{"meta": {"title", "about", "runs": "cpu" or "model", "needs": [...], "packs": [...], "notes": {"node id": "what it does"}}, "graph": {...api format...}}`. `runs: "cpu"` graphs are really executed by `scripts/verify_university_graphs.py`. Every graph goes through ComfyUI's own `validate_prompt`.

## Accuracy
Read the source, run it, or fetch the official docs. Never write from a name. Say which version you read. If a claim rests on one run, say so. Numbers on the page come from labs or tests. Don't copy pack code or README text. Recommend a pack only if it is on our hand-read list or you read it yourself.

Check with: `python studio/university/build.py --labs --only CU-nnn --check-only`.
