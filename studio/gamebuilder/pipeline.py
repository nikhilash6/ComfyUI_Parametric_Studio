"""Prompts -> spec -> textures -> title art -> place -> props -> characters -> music -> sound -> project -> Godot's checks -> the bot plays it -> exports. Every item records its real model, seed, licence and time, or that it's a stand-in and why. An item that fails gets a drawn stand-in, so the game always runs, and it's counted: never passed off as a model's work.
Finished model results live in a cache keyed by the words, seed and model, so a rerun rebuilds only what changed. A stand-in is never cached: the next run tries the model again."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import time
import traceback
import uuid
from contextlib import nullcontext
from pathlib import Path

from psn import paths
from studio.gamebuilder import assemble as AS
from studio.gamebuilder import levels as LV
from studio.gamebuilder import models as M
from studio.gamebuilder import procedural as PR
from studio.gamebuilder import spec as SP

SETTING = "STUDIO_GAMEBUILDER_ROOT"
CACHE_VERSION = 2
STAGES = (("spec", "Spec"), ("textures", "Textures"), ("art", "Title art"), ("place", "Place"), ("props", "Props, items and foes"), ("characters", "Characters, rig and motion"), ("music", "Music"), ("sfx", "Sound effects"), ("voice", "Voice lines"), ("project", "Godot project"), ("check", "Import and check"), ("playtest", "Play-test bot"), ("export", "Export"), ("record", "Play-test video"))
BUDGET = {"prop": (6000, 768), "item": (3000, 512), "foe": (7000, 768), "vehicle": (14000, 1024), "human": (24000, 1024)}
#: What a rigged hero needs, in Kimodo's words. Same words and seed: one generation ever, shared by all games.
CLIPS = {"idle": ("a person stands relaxed in place, breathing, shifting weight slightly", 4), "walk": ("a person walks forward at a steady pace", 4), "run": ("a person runs forward at a jog with arms swinging", 4), "jump": ("a person jumps straight up with both feet and lands", 2)}
NPC_CLIPS = {"idle": CLIPS["idle"], "talk": ("a person stands talking and gestures with both hands", 4)}
MOTION_SEED = 7
FLOURISH_SYSTEM = ("Write one small GDScript 2 file for Godot 4 that adds gentle decoration to a 3D scene, for example a few slowly drifting glowing motes. Start with exactly: extends Node3D. Use only MeshInstance3D, SphereMesh, StandardMaterial3D, Vector3, Color, randf, sin, cos in _ready and _process. No files, no network, no OS, no load or preload. Under 1200 characters. Answer with the code only.")
_ID = re.compile(r"^[a-z0-9_-]{1,80}$")
_THREADS: dict[str, threading.Thread] = {}
_CANCEL: dict[str, threading.Event] = {}
_LOCK = threading.Lock()


def root() -> Path:
    return Path(os.path.expanduser(paths.setting(SETTING, default=paths.home(".local", "share", "parametric-studio", "games"))))


def game_dir(gid: str, base: Path | None = None) -> Path | None:
    if not isinstance(gid, str) or not _ID.match(gid):
        return None
    return (base or root()) / gid


class Cancelled(RuntimeError):
    pass


class Board:
    """The stage board on disk: what the page polls."""

    def __init__(self, gid: str, folder: Path, prompts, options):
        self.path = folder / "state.json"
        self.folder = folder
        self.lock = threading.Lock()
        self.data = {"id": gid, "state": "building", "prompts": prompts, "options": options, "created": time.time(), "updated": time.time(), "title": "", "kit": "", "error": "", "stage": "", "spec_source": "", "spec_note": "",
                     "stages": [{"id": i, "label": l, "status": "pending", "items": [], "seconds": 0.0} for i, l in STAGES], "fallbacks": 0, "playtest": {}, "sizes": {}, "files": {}, "licence_summary": []}
        folder.mkdir(parents=True, exist_ok=True)
        self.save()

    def save(self):
        with self.lock:
            self.data["updated"] = time.time()
            tmp = self.path.with_suffix(f".{threading.get_ident()}.tmp")
            tmp.write_text(json.dumps(self.data, indent=1, default=str), encoding="utf-8")
            os.replace(tmp, self.path)

    def stage(self, sid: str) -> dict:
        return next(s for s in self.data["stages"] if s["id"] == sid)

    def begin(self, sid: str):
        s = self.stage(sid)
        s.update(status="running")
        s["_t"] = time.time()
        self.data["stage"] = sid
        self.save()

    def end(self, sid: str, status: str = "done"):
        s = self.stage(sid)
        s["seconds"] = round(time.time() - s.pop("_t", time.time()), 1)
        s["status"] = status
        self.save()

    def item(self, sid: str, iid: str, what: str, **more) -> dict:
        row = {"id": iid, "what": what, "status": "running", "model": "", "seed": None, "licence": "", "note": "", "seconds": 0.0, "cached": False, **more}
        self.stage(sid)["items"].append(row)
        self.save()
        return row

    def finish(self, row: dict, t0: float, **more):
        row.update(more)
        row["seconds"] = round(time.time() - t0, 1)
        if row.get("status") == "fallback":
            self.data["fallbacks"] += 1
        self.save()


def cache_key(*parts) -> str:
    return hashlib.sha256(json.dumps([CACHE_VERSION, *parts], sort_keys=True, default=str).encode()).hexdigest()[:24]


class Cache:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def dir(self, key: str) -> Path:
        return self.folder / key

    def get(self, key: str) -> dict | None:
        try:
            j = json.loads((self.dir(key) / "result.json").read_text(encoding="utf-8"))
            return j if all((self.dir(key) / f).is_file() for f in j.get("files", {}).values()) else None
        except (OSError, ValueError):
            return None

    def put(self, key: str, files: dict, meta: dict) -> dict:
        d = self.dir(key)
        d.mkdir(parents=True, exist_ok=True)
        names = {}
        for k, src in files.items():
            name = f"{k}{Path(src).suffix.lower()}"
            if Path(src).resolve() != (d / name).resolve():
                shutil.copyfile(src, d / name)
            names[k] = name
        j = {"files": names, **meta}
        tmp = d / "result.tmp"
        tmp.write_text(json.dumps(j, indent=1, default=str), encoding="utf-8")
        os.replace(tmp, d / "result.json")
        return j

    def path(self, key: str, j: dict, name: str = "main") -> Path:
        return self.dir(key) / j["files"][name]


def _credit(what: str, key: str, seed=None, note: str = "") -> dict:
    return {"what": what, "made_by": M.NAMES.get(key, key) + (f", seed {seed}" if seed is not None else ""), "licence": M.LICENCES.get(key, ""), "model": key, "seed": seed, "note": note}


class Game:
    def __init__(self, gid: str, prompts: list, options: dict, *, models=None, base: Path | None = None, cancel=None, godot: str | None = None):
        self.base = Path(base) if base else root()
        self.dir = self.base / gid
        self.gid = gid
        self.prompts = prompts
        self.options = dict(options or {})
        self.models = models or M.RealModels()
        self.board = Board(gid, self.dir, prompts, self.options)
        self.cache = Cache(self.base / "_cache")
        self.cancel = cancel
        self.assets = {"models": {}, "textures": {}}
        self.credits: list[dict] = []
        self.spec: dict = {}
        self.level: dict = {}
        self.godot = godot if godot is not None else AS.godot_path()
        self.a = self.dir / "assets"
        self.a.mkdir(parents=True, exist_ok=True)
        self.work = self.dir / "work"
        if hasattr(self.models, "on_wait"):
            self.models.on_wait = self._waiting

    def _waiting(self, why: str):
        self._check_cancel()
        for st in self.board.data["stages"]:
            for row in st["items"]:
                if row["status"] == "running":
                    row["note"] = why[:300]
        self.board.save()

    def _check_cancel(self):
        if self.cancel is not None and self.cancel.is_set():
            raise Cancelled("cancelled")

    # ---------- spec
    def do_spec(self):
        b = self.board
        b.begin("spec")
        t0 = time.time()
        row = b.item("spec", "spec", "The game spec")
        o = self.options
        given = o.get("spec")
        if isinstance(given, dict):
            spec, note = given, "Given whole, then checked."
        else:
            spec, note = SP.from_model(self.prompts, self.models.ask_qwen, seed=o.get("seed"), kit=o.get("kit"), size=o.get("size") or "medium", difficulty=o.get("difficulty") or "normal")
        spec, bad = SP.validate(spec)
        if bad:
            raise ValueError("; ".join(bad))
        for attempt in range(6):
            lv = LV.build(spec)
            problems = LV.problems(spec, lv)
            if not problems:
                break
            spec["level"]["seed"] = int(spec["level"]["seed"]) + 1
        else:
            raise ValueError("no level came out finishable: " + "; ".join(problems)[:300])
        self.spec, self.level = spec, lv
        is_qwen = spec.get("source") == "qwen"
        b.data.update(title=spec["title"], kit=spec["kit"], spec_source=spec.get("source", ""), spec_note=note)
        b.finish(row, t0, status="done", model="Qwen3.8" if is_qwen else "Prompt words, no model", seed=spec["seed"], licence=M.LICENCES["qwen"] if is_qwen else M.LICENCES["code"], note=f"{note} Kit: {SP.KITS[spec['kit']]['label']} ({spec.get('kit_why')}).")
        (self.dir / "spec.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
        b.end("spec")

    def _kept(self, sid: str, iid: str, what: str, key: str, make, *, fallback=None, credit: bool = True, name: str | None = None):
        """One item: from the cache, or make() -> ({file key: path}, {model, seed, note}), or the stand-in. -> ({file key: path} or None)."""
        self._check_cancel()
        b = self.board
        t0 = time.time()
        row = b.item(sid, iid, what)
        hit = self.cache.get(key)
        if hit:
            files = {k: self.cache.dir(key) / v for k, v in hit["files"].items()}
            b.finish(row, t0, status="done", cached=True, model=M.NAMES.get(hit.get("model"), hit.get("model", "")), seed=hit.get("seed"), licence=M.LICENCES.get(hit.get("model"), ""), note=hit.get("note", ""))
            if credit:
                self.credits.append(_credit(name or what, hit.get("model"), hit.get("seed"), hit.get("note", "")))
            return files
        try:
            files, meta = make(self.work / iid)
            j = self.cache.put(key, files, meta)
            out = {k: self.cache.dir(key) / v for k, v in j["files"].items()}
            b.finish(row, t0, status="done", model=M.NAMES.get(meta.get("model"), meta.get("model", "")), seed=meta.get("seed"), licence=M.LICENCES.get(meta.get("model"), ""), note=meta.get("note", ""))
            if credit:
                self.credits.append(_credit(name or what, meta.get("model"), meta.get("seed"), meta.get("note", "")))
            return out
        except Cancelled:
            raise
        except Exception as exc:
            why = f"{exc}"[:400] or type(exc).__name__
            self._log(f"{iid}: {traceback.format_exc()}")
            if fallback is None:
                b.finish(row, t0, status="fallback", model="Stand-in, drawn by the kit", licence=M.LICENCES["code"], note=f"Stand-in. No model made this: {why}")
                if credit:
                    self.credits.append(_credit(name or what, "code", None, "A stand-in, because the model step failed."))
                return None
            got = fallback(self.work / iid)
            b.finish(row, t0, status="fallback", model="Drawn by code", licence=M.LICENCES["code"], note=f"Stand-in. No model made this: {why}")
            if credit:
                self.credits.append(_credit(name or what, "code", None, "A stand-in, because the model step failed."))
            return got

    def _log(self, text: str):
        with open(self.dir / "build.log", "a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")

    # ---------- textures
    def do_textures(self):
        s, b = self.spec, self.board
        b.begin("textures")
        st = s["setting"]
        pal = st["palette"]
        wanted = [("ground", st.get("ground") or "grass", pal.get("ground")), ("rock", st.get("rock") or "grey rock", pal.get("accent2"))]
        if s["kit"] == "kart":
            wanted.append(("road", st.get("road") or "asphalt road surface", "#3c3c40"))
        for i, (name, what, tint) in enumerate(wanted):
            seed = int(s["seed"]) + 11 + i
            prompt = f"seamless tileable texture of {what}, flat top-down orthographic view, even diffuse light, no shadows, no objects, the texture fills the whole frame"

            def make(work, prompt=prompt, seed=seed, name=name):
                from studio.worldkit import textures as T
                work.mkdir(parents=True, exist_ok=True)
                pic, key = self.models.image(prompt, seed, work, width=1024, height=1024, want=("image", "krea2"), prefix=f"gamebuilder/tex_{name}")
                out = work / f"{name}.png"
                T.make_tileable(pic, out, size=1024)
                return {"main": out}, {"model": key, "seed": seed, "note": ""}

            def fb(work, what=what, seed=seed, tint=tint, name=name):
                work.mkdir(parents=True, exist_ok=True)
                return {"main": PR.texture(what, work / f"{name}.png", seed=seed, tint=tint)}

            got = self._kept("textures", f"tex_{name}", f"Texture: {what}", cache_key("tex", prompt, seed), make, fallback=fb, name=f"Surface texture ({name})")
            self.assets["textures"][name] = got["main"]
        b.end("textures")

    # ---------- title art
    def do_art(self):
        s, b = self.spec, self.board
        b.begin("art")
        st = s["setting"]
        seed = int(s["seed"]) + 21
        # Only nouns and pictures go in: a sentence from the prompts tends to come back painted on the picture as lettering.
        prompt = f"Video game key art, a wide scenic view of {st['name']}, {st['time']} light, {st['weather']} weather, {s['player']['description'][:100]} small in the distance, cinematic light, painterly 3D game style, a clean picture with no signs, captions or writing"

        def make(work):
            work.mkdir(parents=True, exist_ok=True)
            pic, key = self.models.image(prompt, seed, work, width=1280, height=720, want=("krea2", "image"), prefix="gamebuilder/title")
            return {"main": pic}, {"model": key, "seed": seed, "note": "The title's lettering is drawn by the game in a font, not by the model."}

        def fb(work):
            work.mkdir(parents=True, exist_ok=True)
            return {"main": PR.title_art(work / "title.png", st["palette"], seed=seed)}

        got = self._kept("art", "title", "Title art", cache_key("title", prompt, seed, "ocr"), make, fallback=fb, name="Title art")
        self.assets["title"] = _as_png(got["main"], self.a / "title.png")
        self.assets["icon"] = PR.icon(self.a / "icon.png", st["palette"])
        self._sky()
        b.end("art")

    def _sky(self):
        """The whole sky, as a panorama. Fog takes its colour from the picture's horizon, so the far distance melts into it."""
        s = self.spec
        st = s["setting"]
        seed = int(s["seed"]) + 23
        prompt = f"A wide panoramic view of only the sky over {st['name']}, {st['time']} light, {st['weather']} weather, layered clouds, soft distant hazy silhouettes along the very bottom of the frame, seamless 360 degree panorama, painterly"

        def make(work):
            work.mkdir(parents=True, exist_ok=True)
            pic, key = self.models.image(prompt, seed, work, width=1536, height=768, want=("krea2", "image"), prefix="gamebuilder/sky")
            out, colours = PR.sky_from_picture(pic, work / "sky.png")
            return {"main": out}, {"model": key, "seed": seed, "note": "The picture's ends are crossfaded to wrap round. A real 360 panorama it is not: the model paints a wide view.", "colours": colours}

        def fb(work):
            work.mkdir(parents=True, exist_ok=True)
            return {"main": PR.sky_art(work / "sky.png", st["palette"], seed=seed)}

        key = cache_key("sky", prompt, seed, 2, "ocr")
        got = self._kept("art", "sky", "The sky", key, make, fallback=fb, name="The sky")
        self.assets["sky"] = got["main"]
        hit = self.cache.get(key)
        if hit and hit.get("colours"):
            st["palette"].update(hit["colours"])


    # ---------- place
    def do_place(self):
        s, b = self.spec, self.board
        if s["kit"] != "mystery" or self.options.get("place") is False:
            b.begin("place")
            b.end("place", "skipped")
            return
        b.begin("place")
        brief = f"{s['setting']['name']} {s['setting'].get('description', '')}"[:400]
        seed = int(s["seed"]) % 100000
        key = cache_key("place", brief, seed)

        def make(work):
            glb, recipe = self.models.place(brief, seed, work)
            return {"main": glb, "recipe": _write_json(work / "recipe.json", recipe)}, {"model": "world_kit", "seed": seed, "note": f"The {recipe.get('kit')} kit, {recipe.get('time')}, {recipe.get('weather')}; textures {recipe.get('textures')}."}

        got = self._kept("place", "place", "The place", key, make, name="The place (World Kit)")
        if got:
            self.assets["models"]["place"] = got["main"]
            recipe = json.loads(Path(got["recipe"]).read_text(encoding="utf-8"))
            self._fit_mystery_to_place(recipe)
        b.end("place")

    def _fit_mystery_to_place(self, recipe: dict):
        lv = self.level
        w, d = recipe["size_m"]
        lv["place"] = "place"
        lv["size"] = [float(w) + 4.0, float(d) + 4.0]
        lv["blocks"] = []
        lv["decor"] = []                 # a World Kit place comes with its own street furniture; more props only crowd the camera
        if recipe.get("kit") == "interior":
            lv["indoor"] = True
        rngs = [(0.42, 0.0), (-0.42, 0.0), (0.2, 0.2), (-0.2, -0.2), (0.33, -0.22), (-0.33, 0.22), (0.0, 0.3), (0.05, -0.3), (0.12, 0.12)]
        st = self.spec["story"]
        for row, (u, v) in zip([*st["suspects"], *st["clues"]], rngs):
            row["spot"] = [round(u * w, 2), 0.0, round(v * d, 2)]

    # ---------- props
    def _mesh_item(self, sid: str, iid: str, what: str, description: str, seed: int, budget: str, *, extra: str = "", name: str | None = None):
        faces, tex = BUDGET[budget]
        words = f"{description}{extra}"
        prompt = f"{words}, a single object, the whole object in view, centred, plain light grey studio background, soft even light, product photo"
        route = tuple(self.options.get("mesh_routes") or ("trellis2_main", "triposr", "hunyuan3d"))
        key = cache_key("mesh", prompt, seed, faces, tex, route)

        def make(work):
            work.mkdir(parents=True, exist_ok=True)
            note = ""
            try:
                pic, img_key = self.models.image(prompt, seed, work, prefix=f"gamebuilder/{iid}")
                raw, mesh_key = self.models.mesh_from_picture(pic, seed, work, f"gamebuilder/{iid}", route)
                note = f"Picture by {M.NAMES.get(img_key, img_key)}, mesh by {M.NAMES.get(mesh_key, mesh_key)}."
            except Exception as exc:
                raw, mesh_key = self.models.mesh_from_words(description, seed, work)
                note = f"Words to mesh, because the picture route failed: {exc}"[:300]
            out = work / "game.glb"
            info = self.models.game_ready(raw, out, faces, tex, work / "gameready")
            return {"main": out}, {"model": mesh_key, "seed": seed, "note": f"{note} {_faces(info)}"}

        got = self._kept(sid, iid, what, key, make, name=name or what)
        if got:
            self.assets["models"][iid] = got["main"]
            return iid
        return ""

    def do_props(self):
        s, b = self.spec, self.board
        b.begin("props")
        seed = int(s["seed"])
        for i, p in enumerate(s["props"]):
            p["asset"] = self._mesh_item("props", f"prop{i}", f"Prop: {p['name']}", p["description"], seed + 31 + i, "prop", name=f"Prop ({p['name']})")
        for i, p in enumerate(s["items"]):
            p["asset"] = self._mesh_item("props", f"item{i}", f"Item: {p['name']}", p["description"], seed + 41 + i, "item", name=f"Item ({p['name']})")
        for i, p in enumerate(s["enemies"]):
            p["asset"] = self._mesh_item("props", f"foe{i}", f"Foe: {p['name']}", p["description"], seed + 51 + i, "foe", extra=", a cute cartoon toy-like creature, facing the camera", name=f"Foe ({p['name']})")
        if s["player"]["kind"] == "vehicle":
            s["player"]["asset"] = self._mesh_item("props", "vehicle", "The vehicle", s["player"]["description"], seed + 61, "vehicle", extra=", seen straight from the front, facing the camera", name="The vehicle")
        b.end("props")

    # ---------- characters
    def _motion(self, clip: str, text: str, seconds: int):
        key = cache_key("motion", text, seconds, MOTION_SEED)

        def make(work):
            work.mkdir(parents=True, exist_ok=True)
            return {"main": self.models.motion(text, seconds, MOTION_SEED, work)}, {"model": "kimodo", "seed": MOTION_SEED, "note": ""}

        return self._kept("characters", f"motion_{clip}", f"Motion: {clip}", key, make, name=f"Motion ({clip})")

    def _character(self, iid: str, row: dict, *, clips: dict, seed: int):
        """Words -> sheet -> mesh -> rig -> clips -> one glb. Falls back a step at a time: a mesh that won't rig stands in the game as a mesh, and says so."""
        words = row["description"]
        name = row.get("name") or iid
        faces, tex = BUDGET["human"]
        key = cache_key("character", words, name, seed, faces, tex, sorted(clips), row.get("height_m", 1.7))
        made_motions = [(c, self._motion(c, *clips[c])) for c in clips]
        motions = [(c, m["main"]) for c, m in made_motions if m]

        def make(work):
            work.mkdir(parents=True, exist_ok=True)
            sheet, cid = self.models.character_sheet(name, words)
            raw, mesh_key = self.models.mesh_from_picture(sheet, seed, work, f"gamebuilder/{iid}", ("trellis2_main",))
            light = work / "light.glb"
            info = self.models.game_ready(raw, light, faces, tex, work / "gameready")
            try:
                rigged = self.models.rig(light, work / "rig")
                fits = []
                for c, bvh in motions:
                    try:
                        fits.append((c, self.models.retarget(bvh, rigged, work / f"retarget_{c}")))
                    except Exception as exc:
                        self._log(f"{iid} retarget {c}: {exc}")
                out = work / "character.glb"
                res = self.models.assemble_character(rigged, fits, float(row.get("height_m", 1.7)), out, work / "assemble")
                names = [c.get("name") for c in res.get("clips") or []]
                return {"main": out, "sheet": sheet}, {"model": "skintokens", "seed": seed, "note": f"Sheet by Krea 2 Turbo, passed the picture check. Mesh by TRELLIS.2 ({_faces(info)}). Rig by SkinTokens. Clips by Kimodo: {', '.join(names) or 'none'}.", "rigged": True, "cid": cid}
            except Exception as exc:
                return {"main": light, "sheet": sheet}, {"model": mesh_key, "seed": seed, "note": f"Mesh only, no rig: {exc}"[:400] + " It moves by a procedural bob.", "rigged": False, "cid": cid}

        got = self._kept("characters", iid, f"Character: {name}", key, make, name=f"Character ({name})")
        if got:
            self.assets["models"][iid] = got["main"]
            return iid
        return ""

    def do_characters(self):
        s, b = self.spec, self.board
        b.begin("characters")
        seed = int(s["seed"])
        if s["player"]["kind"] == "human":
            s["player"]["asset"] = self._character("hero", s["player"], clips=CLIPS, seed=seed + 71)
        story = s["story"]
        for i, row in enumerate(story.get("npcs") or []):
            row["asset"] = self._character(f"npc{i}", row, clips=NPC_CLIPS, seed=seed + 81 + i)
        for i, row in enumerate(story.get("suspects") or []):
            row["asset"] = self._character(f"suspect{i}", row, clips=NPC_CLIPS, seed=seed + 91 + i)
        b.end("characters")

    # ---------- sound
    def do_music(self):
        s, b = self.spec, self.board
        b.begin("music")
        m = s["music"]
        seed = int(s["seed"]) + 5
        seconds = 75
        want = tuple(self.options.get("music_models") or ("ace15",))
        key = cache_key("music", m["mood"], m["bpm"], seed, seconds, want)

        def make(work):
            work.mkdir(parents=True, exist_ok=True)
            raw, k = self.models.music(m["mood"], m["bpm"], seed, seconds, work, want)
            out = work / "music.ogg"
            loop_seam(raw, out)
            return {"main": out}, {"model": k, "seed": seed, "note": f"{m['mood']}. Tail crossfaded into the head so it loops."}

        def fb(work):
            work.mkdir(parents=True, exist_ok=True)
            wav = PR.music_loop(work / "music.wav", seed=seed, bpm=int(m["bpm"]))
            return {"main": PR.to_ogg(wav, work / "music.ogg")}

        got = self._kept("music", "music", "Music", key, make, fallback=fb, name="Music")
        self.assets["music"] = got["main"]
        b.end("music")

    def do_sfx(self):
        b = self.board
        b.begin("sfx")
        t0 = time.time()
        row = b.item("sfx", "sfx", "Jump, pickup, hit, boost and more")
        d = self.a / "sfx"
        names = PR.sfx_set(d, seed=int(self.spec["seed"]) % 1000)
        self.assets["sfx"] = d
        b.finish(row, t0, status="done", model=M.NAMES["code"], licence=M.LICENCES["code"], note=f"{len(names)} effects synthesised from waves and noise. No model.")
        self.credits.append(_credit("Sound effects", "code"))
        b.end("sfx")

    def do_voice(self):
        b = self.board
        b.begin("voice")
        t0 = time.time()
        row = b.item("voice", "voice", "Spoken lines")
        try:
            from studio import voice as V
            has = bool(V.speech().get("tts"))
        except Exception:
            has = False
        b.finish(row, t0, status="skipped", model="None", note="Optional. The game shows every line as text." + ("" if has else " No speech server is running here."))
        b.end("voice", "skipped")

    # ---------- project and Godot
    def do_project(self):
        b = self.board
        b.begin("project")
        t0 = time.time()
        row = b.item("project", "project", "A Godot 4 project from the kit, the spec and the assets")
        self.credits.append({"what": "Engine", "made_by": "Godot Engine 4.7", "licence": "MIT", "model": "", "seed": None, "note": ""})
        self.credits.append({"what": "Font", "made_by": "Archivo", "licence": "SIL Open Font License", "model": "", "seed": None, "note": ""})
        self.credits.append({"what": f"Game code ({self.spec['kit']} kit)", "made_by": "Parametric Studio", "licence": "AGPL-3.0", "model": "", "seed": None, "note": "Written by hand, not by a model."})
        self.project = AS.scaffold(self.spec, self.level, self.assets, self.credits, self.dir / "project")
        b.data["licence_summary"] = licence_summary(self.credits)
        b.finish(row, t0, status="done", model="The kit, written by hand", licence="AGPL-3.0 for the code; each asset keeps its model's licence", note=f"The {SP.KITS[self.spec['kit']]['label']} kit.")
        (self.dir / "spec.json").write_text(json.dumps(self.spec, indent=1), encoding="utf-8")
        b.end("project")

    def do_check(self):
        b = self.board
        b.begin("check")
        t0 = time.time()
        row = b.item("check", "import", "godot --headless --import, then the parser over every script")
        if not self.godot:
            b.finish(row, t0, status="failed", note="Godot isn't installed. Set STUDIO_GODOT to the Godot 4 editor binary.")
            b.end("check", "failed")
            raise AS.GodotError("Godot isn't installed: the project is written, but it can't be checked or exported here. Set STUDIO_GODOT.")
        errs = AS.import_project(self.project, self.godot, self.dir / "log" / "import.log")
        problems = AS.check_scripts(self.project, self.godot, self.dir / "log")
        if problems:
            b.finish(row, t0, status="failed", note="; ".join(problems)[:800])
            b.end("check", "failed")
            raise AS.GodotError("a script didn't parse: " + "; ".join(problems)[:600])
        b.finish(row, t0, status="done", model=f"Godot {AS.VERSION}", licence="MIT", note="Imported and every script parsed." + (f" {len(errs)} import warnings." if errs else ""))
        self._flourish()
        b.end("check")

    def _flourish(self):
        """Optional, and only with Qwen running: a small decorative script of its own. It has to pass two gates, the rule list and Godot's parser, or it's thrown away and the game doesn't miss it."""
        if self.spec.get("source") != "qwen":
            return
        b = self.board
        t0 = time.time()
        row = b.item("check", "flourish", "A small decorative script by Qwen, checked")
        try:
            text = _code_block(self.models.ask_qwen(FLOURISH_SYSTEM, f"The setting: {self.spec['setting']['name']}. {self.spec['setting'].get('description', '')[:200]}"))
            bad = AS.check_constrained(text, self.project, self.godot, self.dir / "log")
        except Exception as exc:
            text, bad = "", [f"{exc}"[:200]]
        if bad:
            b.finish(row, t0, status="skipped", model="Qwen3.8", note="Thrown away, and the game runs without it: " + "; ".join(bad)[:300])
            return
        (Path(self.project) / "core" / "flourish.gd").write_text(text, encoding="utf-8")
        self.credits.append(_credit("Decorative script", "qwen", None, "Written by Qwen. Passed the rule list and Godot's parser."))
        (Path(self.project) / "game" / "credits.json").write_text(json.dumps(self.credits, indent=1), encoding="utf-8")
        b.finish(row, t0, status="done", model="Qwen3.8", licence=M.LICENCES["qwen"], note="Passed the rule list and godot --check-only.")

    def do_playtest(self):
        b = self.board
        b.begin("playtest")
        t0 = time.time()
        row = b.item("playtest", "bot", "The bot plays it with real key presses, no picture, as fast as physics allows")
        rep = AS.playtest(self.project, self.godot, self.dir / "playtest" / "report.json", self.dir / "log" / "playtest.log", timeout_s=int(self.options.get("playtest_timeout") or 900))
        ev = rep.pop("events", [])
        b.data["playtest"] = {**rep, "event_count": len(ev)}
        won = rep.get("result") == "won"
        b.finish(row, t0, status="done" if won else "failed", model="The kit's input bot", note=f"Result: {rep.get('result')} after {rep.get('played_s')} s of play." + (f" Script errors: {'; '.join(rep.get('script_errors') or [])[:300]}" if rep.get("script_errors") else ""))
        b.end("playtest", "done" if won else "failed")

    def do_export(self):
        b = self.board
        b.begin("export")
        out = self.dir / "build"
        files = {}
        state = AS.templates_state()
        for target, dest in (("Linux", out / "linux" / f"{_slug(self.spec['title'])}.x86_64"), ("Web", out / "web" / "index.html")):
            t0 = time.time()
            row = b.item("export", target.lower(), f"{target} build")
            if not state["ready"]:
                b.finish(row, t0, status="failed", note="Godot's export templates aren't installed. The project still opens in Godot; install them from the page, checked against Godot's published hash.")
                continue
            try:
                AS.export(self.project, self.godot, target, dest, self.dir / "log" / f"export_{target.lower()}.log")
                files[target.lower()] = str(dest)
                size = sum(f.stat().st_size for f in dest.parent.rglob("*") if f.is_file())
                b.finish(row, t0, status="done", model=f"Godot {AS.VERSION} templates", licence="MIT", note=f"{size / 1e6:.0f} MB")
                b.data["sizes"][target.lower()] = size
            except AS.GodotError as exc:
                b.finish(row, t0, status="failed", note=str(exc)[:500])
        zips = self.dir / "zips"
        AS.zip_tree(self.project, zips / "project.zip", _slug(self.spec["title"]))
        if "linux" in files:
            AS.zip_tree(out / "linux", zips / "linux.zip", _slug(self.spec["title"]))
        if "web" in files:
            AS.zip_tree(out / "web", zips / "web.zip", _slug(self.spec["title"]))
        b.data["files"] = {k: True for k in files}
        for k in ("project", "linux", "web"):
            z = zips / f"{k}.zip"
            if z.is_file():
                b.data["sizes"][f"{k}_zip"] = z.stat().st_size
        b.end("export", "done" if files else "failed")

    def do_record(self):
        """The bot again, this time with pictures: Godot's Movie Maker writes every frame at a fixed rate, in software, so it takes minutes and tells nothing about frame rate. Skipped where there's no virtual screen."""
        b = self.board
        b.begin("record")
        t0 = time.time()
        row = b.item("record", "video", "A video of the bot playing, and a contact sheet to look at")
        if self.options.get("record") is False or not AS.can_record():
            b.finish(row, t0, status="skipped", note="No video: this needs xvfb-run and ffmpeg." if self.options.get("record") is not False else "Not asked for.")
            b.end("record", "skipped")
            return
        d = self.dir / "playtest"
        rep = AS.record(self.project, self.godot, d, self.dir / "log" / "record.log")
        ok = (d / "play.mp4").is_file()
        b.data["playtest_video"] = {k: rep.get(k) for k in ("result", "played_s", "script_errors")}
        b.finish(row, t0, status="done" if ok else "failed", model="Godot Movie Maker, software rendering", note=f"Result on this run: {rep.get('result')}." + ("" if ok else " No video came out."))
        b.end("record", "done" if ok else "failed")

    def run(self) -> dict:
        b = self.board
        try:
            self.do_spec()
            hold = getattr(self.models, "hold", None)
            with (hold("assets") if hold else nullcontext()):
                for step in (self.do_textures, self.do_art, self.do_place, self.do_props, self.do_characters, self.do_music):
                    self._check_cancel()
                    step()
            for step in (self.do_sfx, self.do_voice, self.do_project, self.do_check, self.do_playtest, self.do_export, self.do_record):
                self._check_cancel()
                step()
            b.data["state"] = "done"
            b.data["stage"] = ""
        except Cancelled:
            b.data.update(state="cancelled", error="cancelled")
        except Exception as exc:
            b.data.update(state="failed", error=f"{exc}"[:900] or type(exc).__name__)
            self._log(traceback.format_exc())
            for s in b.data["stages"]:
                if s["status"] == "running":
                    b.end(s["id"], "failed")
        b.save()
        return b.data


def licence_summary(credits: list) -> list[dict]:
    seen, out = set(), []
    for c in credits:
        if c.get("licence") and c["licence"] not in seen:
            seen.add(c["licence"])
            out.append({"licence": c["licence"], "covers": [x["what"] for x in credits if x.get("licence") == c["licence"]][:12]})
    return out


def _code_block(text: str) -> str:
    m = re.search(r"```(?:\w+)?\n(.*?)```", str(text), re.S)
    return (m.group(1) if m else str(text)).strip() + "\n"


def _faces(info: dict) -> str:
    n = (info or {}).get("tris") or (info or {}).get("faces")
    return f"{n} faces." if n else ""


def _write_json(path: Path, data) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _as_png(src: Path, dest: Path) -> Path:
    from PIL import Image
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im.convert("RGB").save(dest, "PNG")
    return dest


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:40] or "game"


def loop_seam(raw: Path, out: Path, xfade: float = 3.0) -> Path:
    """Fold the last few seconds over the first, so the loop has no click, and write an ogg. Needs ffmpeg."""
    import subprocess

    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(raw), "-ac", "2", "-ar", "44100", "-f", "f32le", "-"], capture_output=True, check=True, timeout=300).stdout
    x = np.frombuffer(pcm, dtype=np.float32).reshape(-1, 2).copy()
    n = int(xfade * 44100)
    if len(x) > n * 3:
        fade = np.linspace(0, 1, n)[:, None]
        x[:n] = x[:n] * fade + x[-n:] * (1 - fade)
        x = x[:-n]
    wav = Path(out).with_suffix(".wav")
    import wave
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes((np.clip(x, -1, 1) * 32000).astype("<i2").tobytes())
    PR.to_ogg(wav, out)
    wav.unlink(missing_ok=True)
    return Path(out)


# ---------- running one in the background
def new_id(title_hint: str = "") -> str:
    return f"g{time.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"


def start(prompts: list, options: dict, *, models=None, base: Path | None = None) -> str:
    gid = new_id()
    ev = threading.Event()

    def go():
        try:
            Game(gid, prompts, options, models=models, base=base, cancel=ev).run()
        finally:
            with _LOCK:
                _THREADS.pop(gid, None)
                _CANCEL.pop(gid, None)

    t = threading.Thread(target=go, daemon=True, name=f"gamebuilder-{gid}")
    with _LOCK:
        _THREADS[gid], _CANCEL[gid] = t, ev
    t.start()
    return gid


def cancel(gid: str) -> bool:
    with _LOCK:
        ev = _CANCEL.get(gid)
    if ev is None:
        return False
    ev.set()
    return True


def is_running(gid: str) -> bool:
    with _LOCK:
        t = _THREADS.get(gid)
        return t is not None and t.is_alive()


def read_state(gid: str, base: Path | None = None) -> dict | None:
    d = game_dir(gid, base)
    if d is None:
        return None
    try:
        return json.loads((d / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def list_games(base: Path | None = None) -> list[dict]:
    b = base or root()
    out = []
    try:
        names = sorted((p.name for p in b.iterdir() if p.is_dir() and not p.name.startswith("_")), reverse=True)
    except OSError:
        return []
    for n in names[:60]:
        s = read_state(n, b)
        if s:
            out.append({k: s.get(k) for k in ("id", "title", "kit", "state", "created", "fallbacks", "sizes", "files")} | {"result": (s.get("playtest") or {}).get("result"), "running": is_running(n)})
    return out
