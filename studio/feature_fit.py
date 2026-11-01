"""Hardware Fit: say or detect a GPU and RAM, and see what really runs on it, for every goal, family template and recipe.
Two kinds of number, always labelled. Measured: a peak recorded when we rendered it, on our 96 GB card. Estimate: the size of the model files times the ratio our own measured runs show, with that sum on the row. A big card's peak is not a minimum, since ComfyUI keeps what it has room for and offloads when it has not, so below the peak the answer is "may run, slower", and that is an estimate too. No data means "not known", never a guess."""
import json, os, re, statistics, subprocess, urllib.request
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/fit")
PAGE = {"tab": "fit", "label": "Hardware Fit", "title": ["Hardware Fit", "Your GPU. What really runs.", "Every goal, family and recipe against your card and memory. Measured where we measured it, and labelled an estimate where we did not."], "module": "fit.js", "export": "HardwareFit", "css": "fit.css"}
HERE = Path(__file__).resolve().parent
MEASURED_ON = "our 96 GB card"; OFFLOAD_FLOOR = 0.25; MIN_VRAM_GIB = 2.0; PRESETS = [0, 6, 8, 12, 16, 24, 32, 48, 96]
KIND = {"picture": "image", "image": "image", "video": "video", "audio": "audio", "sound": "audio", "music": "audio", "3d": "3d", "film": "video", "ai": "video"}
_cache: dict = {}


def _load(name):
    if name not in _cache:
        try: _cache[name] = json.loads((HERE / name).read_text(encoding="utf-8"))
        except (OSError, ValueError): _cache[name] = {}
    return _cache[name]


def detect() -> dict:
    """What this machine says, from ComfyUI first and then nvidia-smi. Nothing answers: null, and the page asks."""
    out = {"gpu": None, "vram_gib": None, "ram_gib": None, "from": None}
    try:
        with urllib.request.urlopen(os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/") + "/system_stats", timeout=4) as r: s = json.load(r)
        d = (s.get("devices") or [{}])[0]
        if d.get("vram_total"): out.update(gpu=re.sub(r"^cuda:\d+\s*", "", str(d.get("name") or "")).split(" : ")[0].strip() or None, vram_gib=round(d["vram_total"] / 2**30), **{"from": "ComfyUI"})
        if (s.get("system") or {}).get("ram_total"): out["ram_gib"] = round(s["system"]["ram_total"] / 2**30)
    except Exception: pass
    if out["vram_gib"] is None:
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                name, mem = r.stdout.splitlines()[0].rsplit(",", 1); out.update(gpu=name.strip(), vram_gib=round(int(mem) / 1024), **{"from": "nvidia-smi"})
        except (OSError, ValueError, subprocess.SubprocessError): pass
    if out["ram_gib"] is None:
        try: out["ram_gib"] = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30)
        except (AttributeError, ValueError, OSError): pass
    return out


# ---------- the numbers ----------
def goal_measured() -> dict: return _load("recipes.json").get("measured") or {}


def family_measures() -> dict:
    """{(family, template): peak}: peaks recorded from our own renders of that template."""
    out = {}
    for name, f in (_load("family_status.json").get("families") or {}).items():
        for m in f.get("media") or []:
            if m.get("own") and m.get("tpl") and m.get("peak_vram_gib"): out[(name, m["tpl"])] = max(out.get((name, m["tpl"]), 0), float(m["peak_vram_gib"]))
        t = f.get("test") or {}
        if t.get("tpl") and t.get("peak_gib"): out[(name, t["tpl"])] = max(out.get((name, t["tpl"]), 0), float(t["peak_gib"]))
    return out


def weights_ratio() -> float:
    """How our measured peaks compare with the size of the files, the median over the templates with both. This is what an estimate multiplies by."""
    if "ratio" in _cache: return _cache["ratio"]
    fam = _load("family_status.json").get("families") or {}; measured = family_measures(); ratios = []
    for (name, tpl), peak in measured.items():
        t = next((x for x in fam[name].get("templates") or [] if isinstance(x, dict) and x.get("name") == tpl), None)
        if t and t.get("gb") and t["gb"] >= 1: ratios.append(peak / t["gb"])
    _cache["ratio"] = round(statistics.median(ratios), 2) if ratios else 1.5
    return _cache["ratio"]


def goal_weights() -> dict:
    """{goal: GB of files} from the manifest."""
    return {g: round(sum(f.get("size_gb") or 0 for f in row.get("files") or []), 1) for g, row in (_load("models_manifest.json").get("goals") or {}).items()}


def verdict(need, basis, vram, ram, weights=None) -> dict:
    """One row against one machine. need: peak in GiB, or None when nothing is known."""
    if need is None: return {"verdict": "unknown", "word": "Not known", "why": "We have no measurement and no file sizes for this one."}
    if vram is None: return {"verdict": "unknown", "word": "Tell us your GPU", "why": "No card size yet."}
    w = f"{'Measured peak' if basis == 'measured' else 'Estimated peak'} {need:g} GiB"
    if vram < MIN_VRAM_GIB: return {"verdict": "no", "word": "Needs a GPU", "why": f"{w}. Nothing here is set up to run on the CPU."}
    if ram is not None and weights and weights > ram + vram: return {"verdict": "no", "word": "Too big", "why": f"{w}. Its files come to {weights:g} GB, more than your {vram:g} GiB card and {ram:g} GiB of memory hold together."}
    if need <= vram: return {"verdict": "runs", "word": "Runs", "why": f"{w}, and your card has {vram:g} GiB."}
    if vram >= need * OFFLOAD_FLOOR: return {"verdict": "offload", "word": "May run, slower", "why": f"{w} on {MEASURED_ON if basis == 'measured' else 'a card with room'}. Below that ComfyUI moves parts to system memory. We have not run it on a card your size, so this is an estimate."}
    return {"verdict": "no", "word": "Unlikely", "why": f"{w}, more than four times your {vram:g} GiB card. This is an estimate: nobody here has tried it."}


# ---------- every row ----------
def rows() -> list:
    if "rows" in _cache: return _cache["rows"]
    out = []; gm = goal_measured(); ratio = weights_ratio(); gw = goal_weights()
    from studio.goals import GOALS
    for g, row in GOALS.items():
        m = gm.get(g) or {}; w = gw.get(g)
        if m.get("peak_gib"): need, basis, note = float(m["peak_gib"]), "measured", f"From a real render on {MEASURED_ON}."
        elif w: need, basis, note = round(w * ratio, 1), "estimate", f"{w:g} GB of files x {ratio:g}, the ratio our measured runs show."
        else: need, basis, note = None, None, ""
        out.append({"key": "goal:" + g, "section": "goal", "label": row["label"], "sub": row.get("family"), "kind": KIND.get(row.get("kind"), row.get("kind")), "need": need, "basis": basis, "note": note, "weights": w, "open": "create"})
    measured = family_measures()
    for name, f in (_load("family_status.json").get("families") or {}).items():
        for t in f.get("templates") or []:
            if not isinstance(t, dict): continue
            peak = measured.get((name, t.get("name"))); w = t.get("gb")
            if peak: need, basis, note = round(peak, 1), "measured", f"From our own render of this template on {MEASURED_ON}."
            elif w and w >= 0.5: need, basis, note = round(w * ratio, 1), "estimate", f"{w:g} GB of files x {ratio:g}, the ratio our measured runs show."
            else: need, basis, note = None, None, ""
            out.append({"key": f"family:{f.get('slug')}/{t.get('name')}", "section": "family", "label": t.get("title") or t.get("name"), "sub": name, "kind": KIND.get(f.get("kind"), f.get("kind")), "need": need, "basis": basis, "note": note, "weights": w, "open": "families/" + str(f.get("slug"))})
    from studio import recipes as R
    renders = R.renders(); seen = set()
    for r in [*R.load()["recipes"], *R.library()]:
        if r["id"] in seen or r.get("reference"): continue
        seen.add(r["id"]); x = renders.get(r["id"]) or {}; peaks = [float(s["peak_gib"]) for s in r.get("steps") or [] if s.get("peak_gib")]
        if x.get("peak_vram_gib") and x.get("peak_scope") == "recipe": need, basis, note = float(x["peak_vram_gib"]), "measured", f"The peak of this recipe's own render on {MEASURED_ON}."
        elif x.get("peak_vram_gib") and peaks and all(s.get("goal") in gm for s in r["steps"] if s.get("peak_gib")): need, basis, note = max(peaks), "measured", f"The biggest step's model, measured on {MEASURED_ON}. This recipe's own run only has a whole-card figure ({x['peak_vram_gib']:g} GiB), with other work counted in it."
        elif x.get("peak_vram_gib"): need, basis, note = float(x["peak_vram_gib"]), "measured", f"Peak of the whole card while this ran on {MEASURED_ON}, so other work may be counted in it."
        elif peaks and all(s.get("goal") in gm for s in r["steps"] if s.get("peak_gib")): need, basis, note = max(peaks), "measured", f"The biggest step's model, measured on {MEASURED_ON}. This recipe itself has not rendered here."
        elif peaks: need, basis, note = max(peaks), "estimate", "The figure its author gave for the biggest step."
        else: need, basis, note = None, None, ""
        out.append({"key": "recipe:" + r["id"], "section": "recipe", "label": r.get("title") or r["id"], "sub": r.get("group") or "Recipe", "kind": KIND.get(r.get("kind"), "video"), "need": need, "basis": basis, "note": note, "weights": None, "open": "recipes"})
    _cache["rows"] = out; return out


def try_instead(row: dict, ok: list):
    """The biggest thing of the same kind that measurably runs, a goal first. None when nothing measured fits, because a wrong suggestion is worse than none."""
    same = [r for r in ok if r["kind"] == row["kind"] and r["key"] != row["key"] and r["basis"] == "measured"]
    if not same: return None
    pick = sorted(same, key=lambda r: (r["section"] != "goal", r["section"] != "family", -(r["need"] or 0)))[0]
    return {"key": pick["key"], "label": pick["label"], "need": pick["need"], "open": pick["open"], "section": pick["section"]}


def table(vram, ram) -> dict:
    all_rows = [{**r, **verdict(r["need"], r["basis"], vram, ram, r.get("weights"))} for r in rows()]
    ok = [r for r in all_rows if r["verdict"] == "runs"]
    for r in all_rows:
        r["try"] = try_instead(r, ok) if r["verdict"] in ("offload", "no") else None
    tally = {}
    for r in all_rows:
        t = tally.setdefault(r["section"], {"all": 0, "runs": 0, "offload": 0, "no": 0, "unknown": 0, "measured": 0}); t["all"] += 1; t[r["verdict"]] += 1; t["measured"] += r["basis"] == "measured"
    return {"vram_gib": vram, "ram_gib": ram, "rows": all_rows, "tally": tally, "ratio": weights_ratio(), "measured_on": MEASURED_ON, "presets": PRESETS, "caveat": "Measured peaks are from one card with room to spare, one run each. ComfyUI holds what it has room for, so a peak can be more than a render really needs. Treat them as what it used, not what it must have."}


def _num(v, name):
    if v in (None, ""): return None
    try: x = float(v)
    except (TypeError, ValueError): raise HTTPException(400, f"{name} must be a number of GiB.") from None
    if not 0 <= x <= 4096: raise HTTPException(400, f"{name} must be between 0 and 4096 GiB.")
    return x


@router.get("/detect")
def detect_route(): return detect()


@router.get("/table")
def table_route(vram: str = "", ram: str = ""): return table(_num(vram, "Video memory"), _num(ram, "Memory"))
