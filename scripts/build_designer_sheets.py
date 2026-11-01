#!/usr/bin/env python3
"""Other views and choice variations for the Designers page: real renders, through a dev studio, using each designer's own composer and the same seed and base choices as its tile (build_designer_art.py).
  check                 print each prompt, and fail on any view or option the designer does not have
  render [--only a,b]   render what is missing into $DESIGNER_SHEETS_RAW and record model, seed, time and peak. Waits its turn at the shared GPU gate (gpu_gate.py, found through GPU_GATE_TOOLS)
  pack                  write studio/web/designer_art/sheets/<id>/<slug>.webp and sheets.json
Run with the studio venv python. STUDIO is the dev studio's address, never the released one."""
import argparse, io, json, os, re, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from studio import packs as P
import build_designer_art as B
if os.environ.get("GPU_GATE_TOOLS"): sys.path.insert(0, os.environ["GPU_GATE_TOOLS"])   # the folder holding gpu_gate.py
OUT = ROOT / "studio/web/designer_art/sheets"; RAW = Path(os.environ.get("DESIGNER_SHEETS_RAW", "designer_sheets_raw")); LOG = RAW / "log.json"
STUDIO = os.environ.get("STUDIO", "http://127.0.0.1:8547"); W, H = 480, 600; MODELS = {"image": "FLUX.2 Klein 4B (base, 20 steps), goal image, mode quality", "flux3": "FLUX.3 Klein, goal flux3"}
PLAN = {
 "character": (["head and shoulders, front", "full body, back", "full body, side"], "colour", ["burgundy", "navy", "black"]),
 "fashion": (["front view on a plain backdrop", "back view on a plain backdrop", "flat lay on a clean background"], "colour", ["black", "burgundy", "navy"]),
 "tshirt": (["flat lay on a clean background, front", "flat lay, back", "ghost mannequin product photo"], "motif", ["stars and moons", "geometric shapes", "botanical leaves and flowers"]),
 "mug": (["front view on a clean white background", "top-down view into the mug", "handle on the left, three-quarter view"], "mug_colour", ["matte black", "dusty pink", "terracotta"]),
 "printify": (["mockup on the product, front", "close-up of the printed artwork", "product catalogue shot"], "motif", ["stars and moons", "mountain and pine silhouette", "botanical leaves and flowers"]),
 "setting": (["interior corner, three-quarter view", "high-angle overview", "symmetrical one-point perspective"], "time", ["blue hour", "morning", "sunset"]),
 "animal": (["close-up of the face", "full body standing, studio", "in action"], "habitat", ["a snowy forest", "a flower meadow", "a sandy beach"]),
 "plant": (["studio specimen on a clean backdrop", "botanical illustration plate", "macro of a leaf"], "foliage", ["variegated green and cream", "burgundy", "silver-green"]),
 "hair": (["front view on a featureless mannequin head", "back view on a featureless mannequin head", "left side view on a featureless mannequin head"], "colour", ["jet black", "honey blonde", "chestnut"]),
 "nail": (["ten nails flat lay on a neutral surface", "macro of two nails", "both hands fanned out"], "finish", ["chrome mirror", "matte", "holographic"]),
 "cosplay": (["full-body on a mannequin, front", "full-body on a mannequin, back", "flat lay of every piece"], "colour", ["silver and royal blue", "crimson and black", "emerald and cream"]),
}
# the designers added here: (base choices, tile view, aspect, seed, goal)
NEW = {
 "sneaker": (dict(kinds="futuristic 3D-printed lattice sneaker", upper="translucent mesh over a visible cage", colourway="gold and obsidian", sole="glowing edge-lit midsole"), "levitating hero shot", "2:3", 11),
 "watch": (dict(kinds="skeleton dress watch", case="polished rose gold", dial="open-worked gears", strap="alligator-texture leather", hands="gold dauphine hands"), "three-quarter hero on black", "2:3", 11),
 "jewellery": (dict(kinds="serpent coil bracelet", metal="yellow gold", stone="emerald", style="art nouveau", setting="pave of tiny diamonds", finish="high polish"), "on black velvet", "2:3", 11),
 "perfume": (dict(kinds="faceted glass flacon", glass="amber", liquid="deep amber", cap="polished gold sphere", note="smoke and oud wood"), "hero on wet black stone", "2:3", 11),
 "architecture": (dict(kinds="cantilevered cliff house", material="board-marked concrete", setting="a sea cliff", time="blue hour with lit windows", feature="infinity pool"), "exterior hero", "2:3", 11),
 "robot": (dict(kinds="towering bipedal war machine", finish="gloss white ceramic plates", accent="cyan glow", head="narrow visor", scale="three storeys tall", wear="rain-soaked"), "hero in a rainy city", "2:3", 11),
 "spaceship": (dict(kinds="manta-winged glider", hull="brushed copper", engine="blue ion drive", place="orbit above a ringed planet", scale="a small crew"), "hero in space", "2:3", 11),
 "creature": (dict(kinds="stag-horned spirit beast", skin="soft fur and feathers", colour="emerald and gold", habitat="a misty old forest", mood="calm and ancient", size="as big as a house"), "hero in its habitat", "2:3", 11),
 "helmet": (dict(kinds="winged ceremonial helm", metal="gilded bronze", engraving="vine scrollwork", crest="gold sunburst", wear="soft museum patina"), "museum spotlight", "2:3", 11),
 "album": (dict(kinds="psychedelic rock album", image="a whale floating over a city", technique="oil paint on canvas", palette="ultraviolet and magenta", finish="heavy film grain"), "square cover art", "1:1", 11),
 "poster": (dict(kinds="retro space travel poster", subject="a rocket over a red planet", palette="teal and burnt orange", technique="flat screen print", composition="big central shape"), "flat poster art", "2:3", 11),
 "stainedglass": (dict(kinds="great rose window", subject="a phoenix rising", palette="ruby and gold", lead="thick black lead lines", glass="faceted jewel glass", light="low golden sun"), "lit from behind in a dark hall", "2:3", 11),
 "textile": (dict(kinds="silk scarf print", motif="peacock feathers", palette="emerald and gold", scale="huge single motif", fibre="raw silk"), "draped folds", "2:3", 11),
 "flash": (dict(kinds="traditional flash sheet", motif="panther and roses", ink="black and red", paper="aged cream paper", line="bold outlines"), "flat sheet", "2:3", 11),
 "cake": (dict(kinds="gravity-defying geometric cake", icing="mirror glaze", colour="deep midnight blue", decor="isomalt crystals", slice="dark chocolate layers"), "hero on a stand", "2:3", 11),
 "stage": (dict(kinds="grand opera set", centre="a giant moon on wires", light="shafts through haze", palette="black and gold", floor="real water"), "from the front row", "2:3", 11),
 "lamp": (dict(kinds="leaded glass dragonfly lamp", material="hand-blown art glass", glow="rainbow through glass", style="art nouveau", room="a dark bare room"), "glowing in a dark room", "2:3", 11),
 "gameprop": (dict(kinds="lantern holding a trapped star", material="gold and lapis", magic="floating rune light", style="painterly hand-painted game art", wear="ancient and chipped"), "floating hero", "2:3", 11),
 # the first furniture tile came out too close to a famous real chair, so this one starts from a different brief
 "furniture": (dict(kinds="accent chair", style="art deco", material="black ash", colour="sage green", upholstery="channel-quilted", detail="brass inlay", scale="generous and deep"), "in a styled living room", "2:3", 11),
 # the first vehicle renders looked too much like one real make, so this starts from a stranger brief
 "vehicle": (dict(kinds="wedge-shaped supercar", style="retro-futuristic", era="1980s", paint="gunmetal grey", wheels="turbine-fan wheels", stance="lowered"), "front three-quarter studio shot", "2:3", 11),
 "toy": (dict(kinds="wind-up tin robot", material="lithographed tin", colour="silver and red", era="1950s", wear="well loved"), "toy shop shelf", "2:3", 11),
}
MORPH = {"vehicle": ("paint", ["candy apple red", "pearl white", "matte black"]), "furniture": ("colour", ["terracotta", "matte black", "cream"]), "sneaker": ("colourway", ["volt yellow on black", "ice blue and silver", "hot coral and teal"]), "watch": ("case", ["black ceramic", "brushed titanium", "sapphire crystal"]), "jewellery": ("stone", ["sapphire", "ruby", "black opal"]), "perfume": ("glass", ["emerald", "cobalt blue", "smoked black"]), "architecture": ("setting", ["a misty pine forest", "red desert dunes", "a snowy mountainside"]), "robot": ("finish", ["scratched gunmetal", "gold anodised", "rust and old paint"]), "spaceship": ("place", ["inside a violet nebula", "over a frozen moon", "landing on a red desert"]), "creature": ("colour", ["deep indigo with cyan glow", "ember orange and black", "bone white"]), "helmet": ("metal", ["polished steel", "blackened iron", "verdigris copper"]), "album": ("technique", ["collage of torn paper", "woodcut print", "airbrush chrome"]), "poster": ("palette", ["cream, red and navy", "black, white and one red", "cobalt and pale pink"]), "stainedglass": ("subject", ["whales and waves", "irises and dragonflies", "a peacock with spread tail"]), "textile": ("motif", ["giant peonies", "ocean waves", "stars and comets"]), "flash": ("motif", ["koi and waves", "moths and moons", "snakes and peonies"]), "cake": ("colour", ["ivory and gold", "emerald green", "blush pink"]), "stage": ("centre", ["a vast spiral staircase", "an enormous hand reaching up", "a wall of a thousand candles"]), "lamp": ("glow", ["deep red", "cool moonlight", "warm candle amber"]), "gameprop": ("magic", ["green poison mist", "ember sparks", "frost crystals"]), "toy": ("material", ["painted beech wood", "soft felt", "brass and clockwork"])}
GOALS = {}   # id -> goal, once picked: "image" (FLUX.2 Klein 4B) or "flux3" (FLUX.3 Klein). Written to goals.json after the comparison.
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]
GOALF = RAW / "new_goals.json"
def goal_of(did): return (json.loads(GOALF.read_text()) if GOALF.exists() else {}).get(did, "image")
def new_jobs(only=None, goal=None, tile_only=False):
    packs = P.load(); out = []
    for did, (ch, view, aspect, seed) in NEW.items():
        if only and did not in only: continue
        p = packs[did]; s = dict(choices=ch, view=view, aspect=aspect, seed=seed, idea=""); g = goal or goal_of(did); base = dict(id=did, s=s, goal=g, new=True)
        out.append({**base, "kind": "tile", "label": view, "slug": "tile-" + g, "view": view, "choices": ch})
        if tile_only: continue
        for v in [x for x in p["views"] if x != view][:3]: out.append({**base, "kind": "view", "label": v, "slug": "v-" + slug(v), "view": v, "choices": ch})
        group, vals = MORPH[did]; gr = next(x for x in p["groups"] if x["id"] == group)
        for x in vals:
            if x not in P._opts(gr): raise SystemExit(f"{did}.{group}: no option {x!r}")
            out.append({**base, "kind": "choice", "group": group, "group_label": gr["label"], "label": x, "slug": "c-" + slug(x), "view": view, "choices": {**ch, group: x}})
    for j in out: j["prompt"] = P.compose(j["id"], j["choices"], "", j["view"])
    return out
def jobs(only=None, new=True):
    packs = P.load(); out = new_jobs(only) if new else []
    for did, (views, group, vals) in PLAN.items():
        if only and did not in only: continue
        p, s = packs[did], B.SPEC[did]; gr = next(g for g in p["groups"] if g["id"] == group); opts = P._opts(gr)
        for v in views:
            if v not in p["views"]: raise SystemExit(f"{did}: no view {v!r}. It has {p['views']}")
            out.append(dict(id=did, kind="view", label=v, slug="v-" + slug(v), view=v, choices=s["choices"], s=s))
        for x in vals:
            if x not in opts: raise SystemExit(f"{did}.{group}: no option {x!r}")
            out.append(dict(id=did, kind="choice", group=group, group_label=gr["label"], label=x, slug="c-" + slug(x), view=s["view"], choices={**s["choices"], group: x}, s=s))
    for j in out: j["prompt"] = P.compose(j["id"], j["choices"], j["s"].get("idea", ""), j["view"], j["s"].get("words", ""))
    return out
def call(path, body=None):
    r = urllib.request.Request(STUDIO + path, json.dumps(body).encode() if body is not None else None, {"Content-Type": "application/json"}); return json.load(urllib.request.urlopen(r, timeout=60))
def render(only=None, todo=None):
    import gpu_gate as G
    RAW.mkdir(parents=True, exist_ok=True); log = json.loads(LOG.read_text()) if LOG.exists() else {}
    for j in (todo if todo is not None else jobs(only)):
        key = f"{j['id']}/{j['slug']}"
        if key in log: continue
        goal = j.get("goal", "image"); peak = G.expected("studio:" + goal, 24.0); rid = None
        while rid is None:
            rid, why = G.acquire("looks-designers", key, peak)
            if rid is None: print("gate:", why, flush=True); time.sleep(20)
        try:
            aspect = j["s"].get("aspect") or "2:3"; t0 = time.time()
            job = call("/api/generate", {"goal": goal, "prompt": j["prompt"], "seed": j["s"].get("seed", 11), "options": {"mode": "quality", "aspect": aspect} if goal == "image" else {"aspect": aspect}})["job"]; watch = G.FloorWatch(); st = {}
            while True:
                time.sleep(2); st = call(f"/api/jobs/{job}")
                if st.get("status") in ("done", "error"): break
                if watch.tripped(): call(f"/api/jobs/{job}/cancel", {}); raise SystemExit("the card stayed under its floor: stopped, nothing else touched")
                if time.time() - t0 > 900: raise SystemExit(f"{key}: timed out")
            if st["status"] == "error": print(key, "ERROR", st.get("error"), flush=True); continue
            f = next(x for x in st["files"] if x["kind"] == "image"); data = urllib.request.urlopen(STUDIO + f["url"], timeout=60).read(); dest = RAW / (key.replace("/", "__") + ".png"); dest.write_bytes(data)
            if st.get("peak"): G.record_peak("studio:" + goal, st["peak"])
            log = {**(json.loads(LOG.read_text()) if LOG.exists() else {}), **log}; log[key] = {"goal": goal, "raw": dest.name, "seconds": st.get("seconds"), "peak_vram_gib": st.get("peak"), "seed": st.get("seed"), "job": job, "when": time.strftime("%Y-%m-%d")}; LOG.write_text(json.dumps(log, indent=1)); print(key, st.get("seconds"), st.get("peak"), flush=True)
        finally: G.release(rid)
def pack():
    from PIL import Image
    import hashlib
    log = json.loads(LOG.read_text()); rows = []; art = [a for a in json.loads((OUT.parent / "art.json").read_text()) if a["id"] not in NEW and a["id"] in P.load()]
    # a new designer only goes in once all its pictures exist and none has been rejected
    rejected = set(json.loads((RAW / "rejected.json").read_text())) if (RAW / "rejected.json").exists() else set()
    complete = {d for d in NEW if all(f"{j['id']}/{j['slug']}" in log for j in new_jobs({d})) and not any(f"{j['id']}/{j['slug']}" in rejected for j in new_jobs({d}) if j["kind"] == "tile")}
    skip = set(json.loads((RAW / "rejected.json").read_text())) if (RAW / "rejected.json").exists() else set()
    for j in jobs():
        key = f"{j['id']}/{j['slug']}"
        if key not in log or key in skip or (j["id"] in NEW and j["id"] not in complete): continue
        if j["kind"] == "tile":
            im = B.crop45(Image.open(RAW / log[key]["raw"]).convert("RGB")).resize((640, 800), Image.LANCZOS); f = OUT.parent / f"{j['id']}.webp"; im.save(f, quality=78, method=6); b = f.read_bytes()
            art.append({"id": j["id"], "file": f"designer_art/{j['id']}.webp", "w": 640, "h": 800, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "prompt": j["prompt"], "seed": log[key]["seed"], "options": {}, "choices": j["choices"], "view": j["view"], "model": MODELS[log[key].get("goal", "image")], "seconds": log[key]["seconds"], "peak_vram_gib": log[key]["peak_vram_gib"], "made": log[key]["when"]}); continue
        d = OUT / j["id"]; d.mkdir(parents=True, exist_ok=True); im = Image.open(RAW / log[key]["raw"]).convert("RGB"); im = B.crop45(im, j["s"].get("focus", 0.5)) if hasattr(B, "crop45") else im; im = im.resize((W, H), Image.LANCZOS); f = d / (j["slug"] + ".webp"); im.save(f, quality=74, method=6)
        rows.append({"id": j["id"], "kind": j["kind"], "group": j.get("group"), "group_label": j.get("group_label"), "label": j["label"], "file": f"designer_art/sheets/{j['id']}/{j['slug']}.webp", "prompt": j["prompt"], "seed": log[key]["seed"], "seconds": log[key]["seconds"], "peak_vram_gib": log[key]["peak_vram_gib"], "model": MODELS[log[key].get("goal", "image")], "made": log[key]["when"]})
    (OUT.parent / "sheets.json").write_text(json.dumps(rows, indent=1) + "\n"); (OUT.parent / "art.json").write_text(json.dumps(art, indent=1) + "\n"); print(len(rows), "sheet images,", len(art), "tiles")
if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("cmd", choices=["check", "render", "pack", "compare"]); a.add_argument("--only", default=""); o = a.parse_args(); only = set(o.only.split(",")) - {""}
    if o.cmd == "check":
        for j in jobs(only): print(j["id"], "|", j["label"], "|", j["prompt"][:150])
        print(len(jobs(only)), "jobs")
    elif o.cmd == "render": render(only)
    elif o.cmd == "compare": render(todo=new_jobs(only, "image", True) + new_jobs(only, "flux3", True))
    else: pack()
