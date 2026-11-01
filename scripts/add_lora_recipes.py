"""Gives the LoRAs downloaded on 2026-11-01 a reference row in studio/lora_recipes.json, so they show in the Recipes page and the LoRA list. A row states the licence from the repo's own model card, or says it is unverified; none is marked as tested. Run: python scripts/add_lora_recipes.py --map MODEL_USE_MAP.tsv --cards CARDS_DIR"""
import argparse, csv, hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; DATA = ROOT / "studio" / "lora_recipes.json"
#: Left out on purpose. FaceID and ID LoRAs copy a real face from a photo, and INFL8 is a body-inflation effect: neither belongs in a safe-for-work, no-likeness list.
SKIP = re.compile(r"faceid|infl8|-id-lora", re.I)
FAMILIES = (("flux2", r"flux2|flux\.2|flux_2"), ("flux1", r"flux1|uso-flux|removal_timestep"), ("qwen", r"qwen"), ("wan22", r"wan2\.2|chronoedit"), ("wan21", r"wan21|wan2\.1|wan_alpha|lightx2v_"), ("ltx", r"ltx"), ("z-image", r"z_image|z-image"), ("anima", r"anima"), ("krea2", r"krea"), ("moss", r"moss"), ("flux1", r"hunyuanworld"), ("fibo", r"fibo"))
PURPOSES = (("style", "Style", r"style|illustration|pixel|brush|uso-|alpha"), ("speed", "Speed & few steps", r"lightning|turbo|lightx2v|causvid|distill|chronoedit"), ("control", "Control & guidance", r"control|depth|canny|union|layout|ingredients"), ("camera", "Camera & shot", r"dolly|360|transition|panodit"), ("edit", "Editing & removal", r"edit|relight|removal|inpaint|action|squish"))


def guess(name, table):
    n = name.lower()
    return next((row for row in table if re.search(row[-1], n)), None)


def card_licence(text):
    """-> (licence, class, note), from the model card's front matter only."""
    m = re.match(r"---\n(.*?)\n---", text or "", re.S); front = m.group(1) if m else ""
    lic = re.search(r"^license:\s*(\S+)", front, re.M); name = re.search(r"^license_name:\s*(\S+)", front, re.M); v = (name or lic)
    if not v: return "not stated", "unverified", "The model card states no licence. Read it before you rely on this."
    val = v.group(1).lower()
    if "nc" in re.split(r"[-_]", val) or "non-commercial" in val: return val, "non-commercial", "Non-commercial only, by the model card."
    if val in ("apache-2.0", "mit", "bsd-3-clause", "cc0-1.0", "cc-by-4.0", "openrail"): return val, "open", ""
    if val == "other": return "other", "unverified", "The model card says 'other' with no named licence. Read it before you rely on this."
    return val, "community", "A named model licence. Read it before you rely on this."


def summary_of(text, repo, first_paragraph):
    s = first_paragraph(text) if text else ""
    return f"From {repo}: {s}" if s else f"From {repo}. Its model card has no plain description here."


def row_for(name, repo, text, first_paragraph):
    fam = guess(name, FAMILIES); pur = guess(name, PURPOSES) or ("other", "Other", ""); lic, cls, note = card_licence(text)
    return {"id": "lora_" + hashlib.sha256(name.encode()).hexdigest()[:10], "path": name, "family": fam[0] if fam else "other", "title": re.sub(r"\.safetensors$", "", name), "summary": summary_of(text, repo, first_paragraph), "purpose": pur[0], "purpose_label": pur[1], "rating": "sfw", "licence": lic, "licence_class": cls, "licence_note": note,
            "proof": {"level": "recipe", "note": "Never rendered through a recipe here. Downloaded 2026-11-01; its settings are not tuned."}, "confidence": "low", "class": "C", "mode": "reference", "settings": {}, "run": None, "why_not": "A reference card: no tuned settings yet, so this LoRA has no one-click run. Add it in a family's graph with a LoRA loader."}


def main(argv=None):
    a = argparse.ArgumentParser(); a.add_argument("--map", required=True); a.add_argument("--cards", required=True); a = a.parse_args(argv)
    import importlib.util
    s = importlib.util.spec_from_file_location("use_map", ROOT / "scripts" / "build_model_use_map.py"); M = importlib.util.module_from_spec(s); s.loader.exec_module(M)
    d = json.load(open(DATA, encoding="utf-8")); have = {r["path"] for r in d["loras"]}; added = []
    for r in csv.DictReader(open(a.map), delimiter="\t"):
        m = re.search(r"/loras/([^/]+\.safetensors)$", r["disk_path"]); name = m and m.group(1)
        if not name or r["on_disk"] != "yes" or "/_complete_pipelines/" in r["disk_path"] or name in have or SKIP.search(name): continue
        p = Path(a.cards) / (r["repo"].replace("/", "__") + ".md"); d["loras"].append(row_for(name, r["repo"], p.read_text() if p.exists() else "", M.first_paragraph)); have.add(name); added.append(name)
    DATA.write_text(json.dumps(d, ensure_ascii=False, indent=0), encoding="utf-8"); print(len(added), "rows added of", len(d["loras"]))


if __name__ == "__main__": main()
