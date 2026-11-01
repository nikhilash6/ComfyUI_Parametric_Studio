#!/usr/bin/env python3
"""Eval set for the Qwen agents (psn/subagents/agents.py). Only --live calls the model, and it may wake it, so run it when the machine has a slot for it.
Without --live it checks the eval set itself: every agent, expected id and data file is real. It makes no model call and reports no score.
Usage: eval_qwen_agents.py [--cases FILE ...] [--agent NAME] [--live --yes-call-qwen] [--out results.json]
Scoring: a case passes when the agent's own verifier accepted the output and the case's expectations hold. Live results state the model, the date and how many cases were skipped for missing data."""
import argparse, json, os, shutil, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DEFAULT_CASES = ROOT / "tests" / "fixtures" / "qwen_agents_eval.jsonl"
FIXTURE = ROOT / "tests" / "fixtures" / "knowledge"


def prepare_fixture(dest):
    """A throwaway copy of the fake pack and model data, with absolute page paths. Returns (worker folder, library folder)."""
    dest = Path(dest); shutil.copytree(FIXTURE, dest / "knowledge"); worker, library = dest / "knowledge" / "worker", dest / "knowledge" / "library"
    index = worker / "PACK_PICKS_2026-11-01" / "data" / "PACK_INDEX_2026-11-01.tsv"; index.write_text(index.read_text().replace("{LIB}", str(library)))
    return str(worker), str(library)


def load_cases(paths, agent=None):
    cases = []
    for p in paths:
        with open(p, encoding="utf-8") as f: cases += [json.loads(line) for line in f if line.strip() and not line.startswith("#")]
    return [c for c in cases if not agent or c["agent"] == agent]


def get_path(obj, dotted):
    for part in str(dotted).split("."):
        if isinstance(obj, list):
            try: obj = obj[int(part)]
            except (ValueError, IndexError): return None
        elif isinstance(obj, dict): obj = obj.get(part)
        else: return None
    return obj


def score(case, ok, output):
    """-> list of the expectations that did not hold."""
    want = case.get("expect", {}); bad = []; blob = json.dumps(output, ensure_ascii=False, default=str).lower()
    if ok != want.get("verifier_ok", True): bad.append(f"the verifier said {ok}, expected {want.get('verifier_ok', True)}")
    for t in want.get("contains_all", []):
        if t.lower() not in blob: bad.append(f"output lacks '{t}'")
    if want.get("contains_any") and not any(t.lower() in blob for t in want["contains_any"]): bad.append(f"output has none of {want['contains_any']}")
    for t in want.get("not_contains", []):
        if t.lower() in blob: bad.append(f"output holds '{t}'")
    for path, value in (want.get("fields") or {}).items():
        if get_path(output, path) != value: bad.append(f"{path} is {get_path(output, path)!r}, expected {value!r}")
    return bad


def make_image(kind, folder):
    """Pictures for the QC cases, made here so the eval needs no render."""
    from PIL import Image, ImageDraw
    p = os.path.join(folder, f"{kind}.png"); im = Image.new("RGB", (256, 256), (0, 0, 0))
    if kind == "circle":
        im = Image.new("RGB", (256, 256), (200, 210, 225)); ImageDraw.Draw(im).ellipse((64, 64, 192, 192), fill=(200, 40, 40))
    elif kind == "white": im = Image.new("RGB", (256, 256), (255, 255, 255))
    im.save(p); return p


def build_ctx(case, tmp):
    """The context a case needs. Returns (ctx, reason it must be skipped or None)."""
    c = dict(case.get("ctx") or {})
    oi = c.pop("object_info_file", None)
    if oi:
        path = ROOT / oi
        if not path.is_file(): return c, f"no object_info file {oi}"
        c["object_info"] = json.load(open(path, encoding="utf-8"))
    img = c.pop("make_image", None)
    if img: c["image_path"] = make_image(img, tmp)
    return c, None


def check_cases(cases, tmp):
    """Problems in the eval set itself: nothing here calls a model."""
    from psn import knowledge as K
    from psn.subagents.agents import AGENTS
    probs = []; ids = set()
    for c in cases:
        if c["id"] in ids: probs.append(f"{c['id']}: duplicate id")
        ids.add(c["id"])
        if c["agent"] not in AGENTS: probs.append(f"{c['id']}: unknown agent {c['agent']}"); continue
        _, skip = build_ctx(c, tmp)
        if skip: probs.append(f"{c['id']}: {skip}")
        for e in c.get("truth", {}).get("atlas", []):
            if not K.sampling_entry(e): probs.append(f"{c['id']}: atlas entry {e} does not exist")
        for e in c.get("truth", {}).get("lessons", []):
            if not K.lesson_read(e): probs.append(f"{c['id']}: lesson {e} does not exist")
        for e in c.get("truth", {}).get("packs", []):
            if K.worker_dir() and not K.pack_exact(e): probs.append(f"{c['id']}: pack {e} is not in the index")
    return probs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", action="append", type=Path); ap.add_argument("--agent"); ap.add_argument("--live", action="store_true"); ap.add_argument("--yes-call-qwen", action="store_true"); ap.add_argument("--out", type=Path); ap.add_argument("--fixture-data", action="store_true", help="use the fake pack and model data the default cases expect")
    a = ap.parse_args(argv); cases = load_cases(a.cases or [DEFAULT_CASES], a.agent)
    tmp = tempfile.mkdtemp(prefix="qwen-eval-")
    try:
        if a.fixture_data or not a.cases:
            worker, library = prepare_fixture(tmp); os.environ["PSN_KNOWLEDGE_WORKER"] = worker; os.environ["PSN_KNOWLEDGE_LIBRARY"] = library
        probs = check_cases(cases, tmp)
        for p in probs: print("BAD CASE:", p)
        if not a.live:
            print(f"{len(cases)} cases checked, {len(probs)} problems. No model was called, so this is no score."); return 1 if probs else 0
        if not a.yes_call_qwen: print("--live calls the local model, which may wake it. Add --yes-call-qwen when you have the slot.", file=sys.stderr); return 2
        if probs: return 1
        from psn.subagents.agents import run_agent
        rows = []
        for c in cases:
            ctx, skip = build_ctx(c, tmp)
            if skip: rows.append({"id": c["id"], "agent": c["agent"], "skipped": skip}); continue
            t = time.time(); res = run_agent(c["agent"], c["task"], ctx); bad = score(c, res.ok, res.output)
            rows.append({"id": c["id"], "agent": c["agent"], "passed": not bad, "verifier_ok": res.ok, "failed": bad, "problems": res.problems[:5], "attempts": res.attempts, "steps": res.steps, "tokens": res.tokens, "seconds": round(time.time() - t, 1), "output": res.output})
            print(f"{'PASS' if not bad else 'FAIL'} {c['id']} attempts={res.attempts} steps={res.steps} {bad[:2]}", flush=True)
        ran = [r for r in rows if "skipped" not in r]; by = {}
        for r in ran: by.setdefault(r["agent"], []).append(r["passed"])
        summary = {"model": "local Qwen via psn.subagents.llm", "date": time.strftime("%Y-%m-%d %H:%M"), "cases": len(cases), "ran": len(ran), "passed": sum(r["passed"] for r in ran), "by_agent": {k: f"{sum(v)}/{len(v)}" for k, v in sorted(by.items())}}
        print(json.dumps(summary, indent=1))
        if a.out: a.out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, default=str))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__": sys.exit(main())
