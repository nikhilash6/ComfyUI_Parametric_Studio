# Prism, LongCat, VOID and JoyAI: corrections on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## LongCat-Video-Avatar audio CFG

PROMPTING.md, RECIPES.md and PITFALLS.md in this folder say LongCat-Video-Avatar 1.5's audio CFG works best at 3 to 5. That is the model card's tip. On the earlier studio a side-by-side at audio CFG 4 inflated the lips into a glossy round "O" on open vowels, while CFG 1, the official inference script's value, moved them naturally. Keep audio CFG at 1. The talking-avatar model belongs to the Faces specialist, whose NOW.md has the full record. [docs: studio/processes/avatar-longcat.md, studio/crew_notes/model_families/08-Faces-identity-portrait-animation/dossier/NOW.md]
