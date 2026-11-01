#!/usr/bin/env python3
"""Checks every ComfyUniversity graph with ComfyUI's own code, in this process, with no server and no GPU.
Each graph goes through execution.validate_prompt on the real core node classes. Model-file menus (empty on a machine without that file) are the one allowed failure, and only for graphs with runs="model".
Graphs with runs="cpu" are also really executed, with output going to a throw-away folder. Results go to studio/university/graphs/verified.json. node_defs.json (the small saved copy of node definitions the tests and the page use) is rewritten from the same loaded classes.
Usage: python scripts/verify_university_graphs.py --comfy <ComfyUI dir> [--only id ...] [--dry-run]"""
import argparse, asyncio, hashlib, json, os, shutil, sys, tempfile, time, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; G = ROOT / "studio" / "university" / "graphs"

def prog_setup(comfy):
    os.environ["CUDA_VISIBLE_DEVICES"] = ""; sys.path.insert(0, str(comfy)); os.chdir(comfy); sys.argv = ["verify"]
    from comfy.cli_args import args; args.cpu = True; args.disable_all_custom_nodes = True
    import folder_paths; tmp = tempfile.mkdtemp(prefix="cu_verify_")
    for sub in ("out", "tmp", "in"): os.makedirs(f"{tmp}/{sub}", exist_ok=True)
    folder_paths.set_output_directory(f"{tmp}/out"); folder_paths.set_temp_directory(f"{tmp}/tmp"); folder_paths.set_input_directory(f"{tmp}/in")
    return tmp

class FakeServer:
    client_id = None; last_node_id = None; last_prompt_id = None
    def send_sync(self, *a, **k): pass
    def queue_updated(self): pass

MODEL_INPUTS = {"ckpt_name", "lora_name", "control_net_name", "vae_name", "unet_name", "clip_name", "clip_name1", "clip_name2", "clip_name3", "model_name", "style_model_name", "image", "audio", "model_file", "folder", "folder_name", "video", "file"}

def strip(spec):
    """Input spec without the long tooltips: the type or the menu, and the numeric limits. Menus of model files are dropped because they differ per machine."""
    t = spec[0] if isinstance(spec, (list, tuple)) else spec; opts = spec[1] if isinstance(spec, (list, tuple)) and len(spec) > 1 and isinstance(spec[1], dict) else {}
    keep = {k: opts[k] for k in ("default", "min", "max") if k in opts and not (isinstance(opts[k], str) and len(opts[k]) > 120)}
    return [t, keep] if keep else [t]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--comfy", required=True); ap.add_argument("--only", nargs="*", default=[]); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    tmp = prog_setup(Path(a.comfy).resolve())
    import nodes, execution, comfy.model_management
    asyncio.run(nodes.init_extra_nodes(init_custom_nodes=False, init_api_nodes=False))
    import torch; from PIL import Image
    Image.new("RGB", (64, 64), (200, 160, 40)).save(f"{tmp}/in/example.png"); Image.new("L", (64, 64), 128).save(f"{tmp}/in/depth_map.png")
    ex = execution.PromptExecutor(FakeServer(), cache_type=execution.CacheType.NONE, cache_args={"lru": 0, "ram": 0.0, "ram_inactive": 0.0})
    res = {}; files = sorted(p for p in G.glob("*.json") if p.name not in ("verified.json", "node_defs.json"))
    used = set()
    for p in files:
        d = json.loads(p.read_text()); gid = p.stem; g = d["graph"]; m = d["meta"]; used |= {n["class_type"] for n in g.values()}
        if a.only and gid not in a.only: continue
        unknown = sorted({n["class_type"] for n in g.values()} - set(nodes.NODE_CLASS_MAPPINGS))
        row = {"sha": hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest()[:16], "runs": m["runs"], "unknown": unknown}
        if unknown:
            row["validate"] = "needs a pack" if m.get("packs") else "unknown node"; res[gid] = row; print(gid, row["validate"], unknown); continue
        ok, err, outs, node_err = asyncio.run(execution.validate_prompt(str(uuid.uuid4()), json.loads(json.dumps(g)), None))
        allowed = []; other = []
        for nid, e in (node_err or {}).items():
            for x in e.get("errors", []):
                name = (x.get("extra_info") or {}).get("input_name")
                (allowed if x["type"] == "value_not_in_list" and name in MODEL_INPUTS else other).append(f'{nid} {g[nid]["class_type"]}.{name}: {x["type"]}' if nid in g else str(x))
        if not ok and not node_err: other.append(str(err))
        row["validate"] = "ok" if not other else "failed"; row["file_menus_skipped"] = len(allowed); row["errors"] = other
        if m["runs"] == "cpu" and not other:
            t = time.time(); ex.reset(); ex.execute(json.loads(json.dumps(g)), str(uuid.uuid4()), {}, sorted(outs)); row["ran"] = bool(ex.success); row["ran_seconds"] = round(time.time() - t, 2)
            if not ex.success: row["errors"] = [str(x)[:300] for x in ex.status_messages if x[0] == "execution_error"]
        res[gid] = row; print(gid, row["validate"], "ran" if row.get("ran") else "", row["errors"] or "")
    if not a.dry_run:
        old = {}
        if (G / "verified.json").exists(): old = json.loads((G / "verified.json").read_text()).get("graphs", {})
        old.update(res); cur = {p.stem for p in files}; old = {k: v for k, v in old.items() if k in cur}
        (G / "verified.json").write_text(json.dumps({"comfyui": _ver(a.comfy), "torch": torch.__version__, "graphs": old}, indent=1) + "\n")
    defs = {}
    for c in sorted(used):
        k = nodes.NODE_CLASS_MAPPINGS.get(c)
        if not k: continue
        info = k.INPUT_TYPES(); out = list(getattr(k, "RETURN_TYPES", []) or []); mod = getattr(k, "RELATIVE_PYTHON_MODULE", "nodes")
        names = list(getattr(k, "RETURN_NAMES", []) or out)
        defs[c] = {"input": {g2: {n: strip(s) for n, s in (info.get(g2) or {}).items()} for g2 in ("required", "optional")}, "output": [x if isinstance(x, str) else "COMBO" for x in out], "output_name": names, "module": str(mod), "is_output": bool(getattr(k, "OUTPUT_NODE", False))}
        for g2 in ("required", "optional"):
            for n, s in defs[c]["input"][g2].items():
                if isinstance(s[0], list) and (n in MODEL_INPUTS or len(s[0]) > 80): s[0] = "FILE"
    broken = ROOT / "tests" / "fixtures" / "university_broken.json"
    if broken.exists() and not a.only:
        real = []
        for b in json.loads(broken.read_text()):
            ok, err, outs, node_err = asyncio.run(execution.validate_prompt(str(uuid.uuid4()), json.loads(json.dumps(b["graph"])), None)); types = sorted({x["type"] for e in (node_err or {}).values() for x in e.get("errors", []) if (x.get("extra_info") or {}).get("input_name") != "ckpt_name"})
            real.append({"name": b["name"], "ok": bool(ok), "top": (err or {}).get("type"), "types": types})
        if not a.dry_run: (ROOT / "tests" / "fixtures" / "university_broken_real.json").write_text(json.dumps(real, indent=0) + "\n")
    if not a.dry_run and not a.only: (G.parent / "node_defs.json").write_text(json.dumps(defs, indent=0, ensure_ascii=False, default=str) + "\n")
    shutil.rmtree(tmp, ignore_errors=True); bad = [k for k, v in res.items() if v.get("errors") or (v.get("unknown") and v["validate"] != "needs a pack")]
    print(f"{len(res)} graphs, {len(bad)} with problems", bad); sys.exit(1 if bad else 0)

def _ver(c):
    import subprocess
    return subprocess.run(["git", "-C", c, "describe", "--tags", "--always"], capture_output=True, text=True).stdout.strip()

if __name__ == "__main__": main()
