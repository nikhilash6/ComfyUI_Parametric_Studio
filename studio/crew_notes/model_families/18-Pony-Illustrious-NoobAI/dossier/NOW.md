# Pony, Illustrious and NoobAI: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## Still nothing run in the studio

Pony, Illustrious and NoobAI still have no studio family record, no studio template and no recorded render as of 2026-11-03. That is why this folder has no STATE.md. Everything in GUIDE.md comes from research, not from runs here. [run: studio/family_status.json] [code: studio/family_templates/index.json] [docs: studio/crew_notes/model_families/18-Pony-Illustrious-NoobAI/dossier/GUIDE.md]

LoRA files whose names contain pony or illustrious are grouped under SDXL by the studio's LoRA sorter. [code: studio/loras.py:106, studio/loras.py:122]

SDXL tools that did run in the final session (the xinsir depth, scribble and tile ControlNets and the SDXL IP-Adapters) were run on the SDXL 1.0 base only. Whether they behave the same on a Pony, Illustrious or NoobAI checkpoint has not been tested here. [run: studio/family_status.json:9518-9637] [inference]

Illustrious LoRA tools, a node pack with a crop, tag and review step before SDXL training, was looked at in Pack Lab and marked borrow-the-idea only. Its own README says it has not been validated on a full GPU run. [code: studio/pack_lab_picks.json:808-818]

## What is missing

To give this specialist real records, the studio would need a Pony, Illustrious or NoobAI checkpoint on disk, a family entry and one template with the settings from GUIDE.md, and a viewed render. [inference]
