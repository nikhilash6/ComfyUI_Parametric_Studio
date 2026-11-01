#!/usr/bin/env python3
"""Q&A training rows from verified Sampling Atlas entries only: a second reader checked the entry against the code and either agreed or its correction was applied. Our own words; no pack text, no README claims, no inference, no RES4LYF, no Qwen tail. Each row carries its source and label.
Usage: build_sampling_training.py <ATLAS.json> <measures.json> <renders.json> <out dir>"""
import json, re, sys, zlib
AT, ME, RE, OUT = sys.argv[1:5]
a = json.load(open(AT)); m = json.load(open(ME)); r = json.load(open(RE))
SYS = "You are the ComfyUI_Parametric_Studio assistant. Answer from the Sampling Atlas, keep its proof labels, and say 'not stated' when it is not there."
def split(k): return "val" if zlib.crc32(k.encode()) % 20 == 0 else "train"
def row(q, ans, source, label, key): return {"messages": [{"role": "system", "content": SYS}, {"role": "user", "content": q}, {"role": "assistant", "content": ans}], "source": source, "label": label, "split": split(key)}
def where(e): return "ComfyUI core" if e["in_core"] else "a pack that is live on this box" if e["live"] else "a pack that is not installed here"
qa = []; excluded = {"inference": 0, "res4lyf": 0, "no second reader": 0, "second reader objected, no fix": 0}
for e in a["entries"]:
    au = e.get("audit")
    if not au: excluded["no second reader"] += 1; continue
    if not (au["verdict"] == "correct" or au["fixed"]): excluded["second reader objected, no fix"] += 1; continue
    if e["label"] != "from code": excluded["inference"] += 1; continue
    if any("RES4LYF" in p["pack"] for p in e["providers"]) and not e["in_core"]: excluded["res4lyf"] += 1; continue
    src = [x["where"] for x in e["evidence"][:3]]; n = e["name"]; k = e["id"]
    qa.append(row(f"What does {n} do?", f"{e['plain']} It comes from {where(e)}. [from code: {src[0]}]", src, "from code", k))
    qa.append(row(f"What is the formula for {n} as the code implements it?", f"{e['math']}\n[from code: {src[0]}]", src, "from code", k))
    prov = [p for p in e["providers"] if p["pack"] != "core"][:6]
    credit = "; ".join(p["pack"] + (f" ({p['licence']})" if p["licence"] and p["licence"] != "none-found" else " (no licence file found)") for p in prov)
    qa.append(row(f"Can I run {n} here, and who provides it?", ("Yes, it is in ComfyUI core." if e["in_core"] else "Yes, a live pack provides it." if e["live"] else "Not without installing a pack, which needs the founders' OK and the sandbox first.") + (f" Packs: {credit}." if credit else ""), src, "from code", k))
    if e["surprise"] and not re.search(r"inference|not run|untested", e["surprise"], re.I): qa.append(row(f"Is there anything surprising about {n}?", f"{e['surprise']} [from code: {src[0]}]", src, "from code", k))
    p = e["props"]
    if e["family"] == "sampler" and p.get("stages") not in (None, ""): qa.append(row(f"How many model calls per step does {n} make?", f"{p['stages']}. This is as coded, before guidance multiplies the passes. [from code: {src[0]}]", src, "from code", k))
measured = []
for name, s in m["solvers"].items():
    e = s.get("eps") or {}
    if e.get("error"): continue
    det = e["same_answer_with_other_noise_seed"]
    t = f"On the toy Gaussian problem with the Karras schedule, {name} made {e['calls']['20']} model calls for 20 steps and is {'deterministic' if det else 'stochastic'}. "
    t += f"Its error to the exact answer at 5, 10, 20 and 40 steps was {', '.join(str(e['rmse_to_exact'][n]) for n in ('5', '10', '20', '40'))}." if det else f"Its variance error at 20 steps was {e['variance_error']['20']}."
    measured.append(row(f"What did the solver bench measure for {name}?", t + " This has no neural network in it and says nothing about picture quality.", "measures.json solvers", "measured here", "bench" + name))
for x in r["renders"]:
    if x.get("seen"): measured.append(row(f"What happened with {x['label']} in the {x['set']} proof renders?", f"On {r['models'][x['model']]['name']}, seed {r['seed']}, {r['steps']} steps, {x['sampler']} / {x['scheduler']}, CFG {x['cfg']}: {x['seen']} One seed and one prompt only.", "renders.json " + x["id"], "measured here", x["id"]))
for sch, row_ in m["schedules"]["sd_eps"]["by_steps"]["20"].items():
    if isinstance(row_, list): measured.append(row(f"What sigmas does the {sch} scheduler give on SD 1.5 at 20 steps?", f"It starts at {row_[0]}, its last non-zero sigma is {row_[-2]}, then {row_[-1]}. Full list: {', '.join(map(str, row_))}.", "measures.json schedules", "measured here", "sched" + sch))
for fn, rows in (("sampling_qa.jsonl", qa), ("sampling_measured.jsonl", measured)):
    with open(f"{OUT}/{fn}", "w") as f:
        for x in rows: f.write(json.dumps(x, ensure_ascii=False) + "\n")
print({"qa": len(qa), "measured": len(measured), "excluded": excluded})
