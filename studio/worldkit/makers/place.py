"""Place maker: a brief ("rainy downtown block", "beach cafe") -> a kit recipe (street / interior / beach, time of day, weather, size, materials, seed) -> one seamless
texture per material -> the procedural Blender build (a street grid with building kits, a room with furniture, a beach front), every solid with a collider, plus four
overview stills. Keyword planning is deterministic; the user edits the recipe (look, size, seed, textures) before or after a build.

Textures: recipe["textures"] is "auto" (the Image goal on ComfyUI when its model is here and ComfyUI answers, otherwise procedural), "generated" (always ask ComfyUI, and a
failed picture falls back to procedural) or "procedural" (no model, no GPU). Each texture's origin is written to the tiles step, so the asset says what it is made of."""
from __future__ import annotations

import hashlib
import re

from studio.worldkit import jobs, looks, textures
from studio.worldkit import capabilities as C
from studio.worldkit import steps as S

KITS = ("street", "interior", "beach")
KIT_WORDS = {"street": ("street", "downtown", "block", "city", "road", "alley", "avenue", "crossing", "sidewalk"),
             "interior": ("café", "cafe", "room", "bar", "restaurant", "kitchen", "bedroom", "office", "shop", "store",
                          "apartment", "lobby", "interior", "inside"),
             "beach": ("beach", "seaside", "shore", "coast", "boardwalk", "pier", "sand")}
TIME_WORDS = {"night": ("night", "midnight", "neon", "evening"), "golden": ("sunset", "golden", "dusk", "sunrise", "dawn"),
              "day": ("day", "noon", "morning", "afternoon")}
WEATHER_WORDS = {"rain": ("rain", "rainy", "wet", "storm", "drizzle"),
                 "overcast": ("overcast", "cloudy", "grey", "gray", "fog", "foggy"), "clear": ("sunny", "clear")}
MATERIALS = {"street": {"ground": "asphalt road surface", "sidewalk": "concrete paving slabs", "wall": "red brick wall",
                        "wall2": "painted plaster wall"},
             "interior": {"floor": "oak wood floorboards", "wall": "painted plaster wall", "counter": "dark walnut wood"},
             "beach": {"ground": "fine pale beach sand", "deck": "weathered wooden boardwalk planks",
                       "wall": "white painted wooden boards"}}
SIZES = {"street": [40.0, 24.0], "interior": [10.0, 8.0], "beach": [40.0, 30.0]}
SIZE_RANGE = (4.0, 200.0)
TEXTURE_SOURCES = ("auto", "generated", "procedural")
TEXTURE_GOAL = "image"
TEXTURE_PROMPT = ("seamless tileable texture of {what}, flat top-down orthographic view, even diffuse light, no shadows, "
                  "no objects, no text, the texture fills the whole frame")
BUILD_STEP = "build"
VIEW_SIZE = 512


def _hits(text: str, words) -> int:
    return sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", text))


def plan(brief: str, *, seed: int | None = None, overrides: dict | None = None) -> dict:
    text = str(brief or "").lower()
    scores = {k: _hits(text, KIT_WORDS[k]) for k in KITS}
    kit = max(KITS, key=lambda k: (scores[k], -KITS.index(k)))
    note = "" if scores[kit] else "no kit word in the brief; using the street kit"
    time = next((t for t in ("night", "golden", "day") if _hits(text, TIME_WORDS[t])), "day")
    weather = next((w for w in ("rain", "overcast", "clear") if _hits(text, WEATHER_WORDS[w])), "clear")
    materials = dict(MATERIALS[kit])
    if weather == "rain" and kit == "street":
        materials["ground"] = "wet asphalt road surface"
    if kit == "interior":
        preset = "interior_night" if time == "night" else "interior_day"
    else:
        preset = {"rain": "rainy", "overcast": "overcast"}.get(weather) or \
            {"night": "night_city", "golden": "golden_hour"}.get(time, "day_clear")
    if seed is None:
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) % 2**31
    r = {"kit": kit, "brief": str(brief or "")[:600], "time": time, "weather": weather,
         "look": {"preset": preset, "time": time, "weather": weather}, "size_m": list(SIZES[kit]),
         "materials": materials, "seed": int(seed), "textures": "auto", "note": note}
    for key in ("size_m", "look", "seed", "textures"):
        if key in (overrides or {}):
            r[key] = overrides[key]
    return r


def recipe_problems(r: dict) -> list[str]:
    bad = []
    if r.get("kit") not in KITS:
        bad.append(f"kit must be one of {', '.join(KITS)}")
    size = r.get("size_m")
    lo, hi = SIZE_RANGE
    if not (isinstance(size, list) and len(size) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                                              and lo <= v <= hi for v in size)):
        bad.append(f"size_m is [width, depth], each {lo:.0f}-{hi:.0f} m")
    look = r.get("look") if isinstance(r.get("look"), dict) else {}
    bad += looks.problems(look.get("preset"), look.get("time"), look.get("weather"))
    if not isinstance(r.get("seed"), int) or isinstance(r.get("seed"), bool):
        bad.append("seed is a whole number")
    if not isinstance(r.get("materials"), dict) or not r["materials"]:
        bad.append("materials is a list of surfaces")
    if r.get("textures", "auto") not in TEXTURE_SOURCES:
        bad.append(f"textures must be one of {', '.join(TEXTURE_SOURCES)}")
    return bad


def _wants_generated(r: dict, ctx: dict) -> bool:
    how = r.get("textures", "auto")
    if how == "procedural":
        return False
    return how == "generated" or (ctx.get("textures_generated") or C.textures_generated)()


def steps(meta: dict) -> list[S.Step]:
    r, aid = meta["recipe"], meta["id"]
    bad = recipe_problems(r)
    if bad:
        raise ValueError("; ".join(bad))
    out = []
    for m, what in r["materials"].items():
        def req(ctx, what=what, i=len(out)):
            if not _wants_generated(r, ctx):
                return None
            return jobs.goal(TEXTURE_GOAL, TEXTURE_PROMPT.format(what=what), {"aspect": "1:1", "mode": "fast"}, seed=int(r["seed"]) + i)
        out.append(S.Step(f"tex_{m}", f"Texture '{m}'", optional=True, pick=S.pick_first(media_type=("image",)), request=req))

    def tiles(ctx):
        d = ctx["library"].subdir(aid, "textures")
        made = {}
        for i, (m, what) in enumerate(r["materials"].items()):
            if f"tex_{m}" in ctx["outputs"]:
                textures.make_tileable(S.out_path(ctx, f"tex_{m}"), d / f"{m}.png")
                made[m] = "generated"
            else:
                textures.procedural(what, d / f"{m}.png", seed=int(r["seed"]) + i)
                made[m] = "procedural"
        return {"main": {"materials": made}}

    out.append(S.Step("tiles", "Tileable textures", local=tiles))
    out.append(S.Step(BUILD_STEP, "Build (Blender)", local=build))
    return out


def build(ctx: dict, *, blender=None) -> dict:
    """The procedural build + four views (CPU Cycles unless the GPU is switched on)."""
    from PIL import Image

    from studio.worldkit import blender as B
    bl = blender or ctx.get("blender") or B
    lib, meta = ctx["library"], ctx["asset"]
    aid, r = meta["id"], meta["recipe"]
    tex = {p.stem: str(p) for p in sorted(lib.subdir(aid, "textures").glob("*.png"))}
    work = ctx["work"] / BUILD_STEP
    out, views = work / "place.glb", work / "views"
    detail = {}
    if r["kit"] == "beach":          # water is built in, not one of the materials a model is asked for
        detail["sea"] = str(textures.procedural("sea water", work / "sea.png", seed=int(r["seed"])))
    res = bl.render("wk_place.py", {"recipe": r, "textures": tex, "detail_textures": detail, "look": looks.resolve(**r["look"]), "out": str(out),
                                    "views": str(views), "size": VIEW_SIZE, "samples": 16}, work=work, name="place",
                    timeout=2400)
    sheet = views_sheet([views / f"view_{i}.png" for i in range(4)], work / "views.png", cell=VIEW_SIZE, image=Image)
    ins = dict(res["inspect"])
    ins.pop("bones", None)
    main = {"path": str(out), "inspect": ins, "engine": res.get("engine", "")}
    if res.get("fallback_note"):
        main["note"] = res["fallback_note"]
    return {"main": main, "views": {"path": str(sheet)}}


def views_sheet(pngs: list, dest, cell: int = 512, image=None):
    """A 2 x 2 sheet of the four views."""
    from pathlib import Path

    from PIL import Image
    image = image or Image
    sheet = image.new("RGB", (cell * 2, cell * 2), (9, 9, 10))
    for i, p in enumerate(pngs[:4]):
        with image.open(p) as im:
            sheet.paste(im.convert("RGB").resize((cell, cell)), ((i % 2) * cell, (i // 2) * cell))
    dest = Path(dest)
    sheet.save(dest, format="PNG")
    return dest
