# Crew notes

What the crew answers from on a fresh install: model and technique facts for each model family, with the sources the notes cite. Built by `scripts/build_crew_notes.py` from an allow-list of files, with a filter for anything private or not safe for work. Set `STUDIO_KB` to use a larger knowledge base with the same `model_families/<family>/dossier/*.md` layout.

These are working notes. Check anything important against the model's own documentation.

Newer notes carry a proof label on every paragraph, and `scripts/check_crew_notes.py` checks each cited file and line:

- `model_families/<family>/dossier/STATE.md`: what each family has really done, built by `scripts/build_crew_state.py`.
- `model_families/<family>/dossier/NOW.md`: checked by hand, where a family needs more than that.
- `studio_topics/<topic>/`: one specialist for each part of the studio. `_all-families` is read only by Comfy Prime.
- `evidence/`: the render records those labels cite.

Labels: `[code: file:line]` read in the source, `[test: file]` a test holds it, `[run: file]` a recorded run stored here, `[docs: file]`, `[claim: who]` someone says so and it was not checked, `[inference]` our reasoning. Where an older note disagrees with `STATE.md` or `NOW.md`, the newer one wins.
