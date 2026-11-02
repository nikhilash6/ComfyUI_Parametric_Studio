"""The real models behind the Game Builder, each in the same shape: words in, a file and a record out, or an exception saying why not. The pipeline catches the exception and uses a drawn stand-in, and says so. Tests hand the pipeline a fake with these same methods; nothing here runs at import."""
from __future__ import annotations

import json
import os
import shutil
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from psn import paths
from studio.worldkit import capabilities as C

LICENCES = {
    "krea2": "Krea 2 Community License: you own the output, but commercial use is free only under US$1M company-wide annual revenue",
    "image": "Apache-2.0 (FLUX.2 Klein 4B)",
    "trellis2_main": "MIT (TRELLIS.2); its image encoder DINOv3 has the DINOv3 License",
    "triposr": "MIT (TripoSR)",
    "shap_e": "MIT (Shap-E)",
    "hunyuan3d": "Tencent Hunyuan community licence: excludes the EU, the UK and South Korea, and that reaches outputs",
    "skintokens": "MIT (SkinTokens)",
    "kimodo": "NVIDIA Open Model License (Kimodo); text encoder Meta Llama 3 Community License, Built with Meta Llama 3",
    "ace15": "MIT (ACE-Step 1.5)",
    "music3": "MiniMax-Music3 Community License: a commercial product must show \"MiniMax-Music3\" and has further terms",
    "world_kit": "AGPL-3.0 (World Kit's Blender scripts in this repo)",
    "code": "AGPL-3.0 (drawn by this repo's code, no model)",
    "qwen": "Qwen3.8 licence (the words of the spec)",
}
NAMES = {"krea2": "Krea 2 Turbo", "image": "FLUX.2 Klein 4B", "trellis2_main": "TRELLIS.2", "triposr": "TripoSR", "shap_e": "Shap-E", "hunyuan3d": "Hunyuan3D 2", "skintokens": "SkinTokens", "kimodo": "Kimodo", "ace15": "ACE-Step 1.5 Turbo", "music3": "MiniMax Music 3", "world_kit": "World Kit (Blender)", "code": "Drawn by code", "qwen": "Qwen3.8"}
PEAK = {"krea2": 26.0, "image": 15.0, "trellis2_main": 22.0, "triposr": 4.0, "shap_e": 4.5, "hunyuan3d": 6.0, "skintokens": 6.0, "kimodo": 17.0, "ace15": 8.0, "music3": 26.0}
SESSION_PEAK = 27.0            # the biggest one model takes; they run one after another
TRELLIS_GRAPH = "worldkit_trellis2_character_api.json"
KREA_GRAPH = "worldkit_krea2_t2i_api.json"
ACE_GRAPH = "gamebuilder_ace15_music_api.json"
NO_TEXT = "no text, no letters, no words, no logos, no signature, no watermark"
GATE_WAIT_S = int(paths.setting("STUDIO_GAMEBUILDER_GATE_WAIT_S", default="3600") or 3600)


class ModelUnavailable(RuntimeError):
    pass


def lettering(path) -> list[str]:
    """Words tesseract reads in a picture with confidence: an image model's attempt at lettering, which this studio never ships. [] when tesseract isn't installed, and the note says the check didn't run."""
    import csv
    import io
    import subprocess
    if not shutil.which("tesseract"):
        return []
    try:
        out = subprocess.run(["tesseract", str(path), "stdout", "--psm", "11", "tsv"], capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    found = []
    for row in csv.DictReader(io.StringIO(out), delimiter="\t"):
        t = (row.get("text") or "").strip()
        try:
            conf = float(row.get("conf") or -1)
        except ValueError:
            conf = -1
        if conf >= 70 and sum(ch.isalpha() for ch in t) >= 4:
            found.append(t)
    return found


def _load_gate():
    """A box may name a shared VRAM gate with STUDIO_GPU_GATE (a Python file with acquire and release). Without one, the studio's own check above the VRAM floor."""
    path = paths.setting("STUDIO_GPU_GATE") or ""
    if not path or not Path(path).is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("studio_gpu_gate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RealModels:
    def __init__(self, sleep=time.sleep):
        self._gate = _load_gate()
        self._sleep = sleep
        self._session = ""
        self._session_rid = None
        self.on_wait = None            # told why a job is waiting for the card, so the board can say so

    def _wait_for_room(self, key: str, peak: float, heavy: bool, port):
        """-> a reservation id, or None when the studio's own check says go. Waits its turn; never evicts anyone."""
        from studio.worldkit import blender as B
        deadline = time.time() + GATE_WAIT_S
        while True:
            if self._gate is not None:
                rid, why = self._gate.acquire("gamebuilder", key, peak, heavy, port)
                if rid:
                    return rid
            else:
                why = B.vram_problem(peak)
                if not why:
                    return None
            if time.time() > deadline:
                raise ModelUnavailable(f"no room on the card after {GATE_WAIT_S // 60} minutes: {why}")
            if self.on_wait:
                self.on_wait(f"Waiting for room on the card: {why}")
            self._sleep(20)

    @contextmanager
    def hold(self, label: str):
        """One turn on a shared card for many short jobs in a row: one place in the queue, not one per job. The turn is taken by the first job that needs the card, so a rerun that comes wholly from the cache never waits. On a card with a shared gate it counts as a heavy job and waits its turn with the others."""
        self._session = label
        try:
            yield
        finally:
            self._session = ""
            rid, self._session_rid = self._session_rid, None
            if rid and self._gate is not None:
                self._gate.release(rid)

    @contextmanager
    def turn(self, model: str):
        """Room for one job, or the stage's whole turn if one is open."""
        if self._session:
            if self._session_rid is None and self._gate is not None:
                self._session_rid = self._wait_for_room(f"gamebuilder_{self._session}", SESSION_PEAK, True, 8200)
            elif self._gate is None:
                self._wait_for_room(f"gamebuilder_{model}", PEAK.get(model, 12.0), False, None)
            yield
            return
        rid = self._wait_for_room(f"gamebuilder_{model}", PEAK.get(model, 12.0), False, 8200 if model in ("krea2", "image", "trellis2_main", "ace15", "music3") else None)
        try:
            yield
        finally:
            if rid and self._gate is not None:
                self._gate.release(rid)

    def _need(self, key: str) -> None:
        n = C.need(key)
        if n["state"] != "ready":
            raise ModelUnavailable(n["message"])

    def _comfy(self) -> None:
        if not C.comfy_up():
            raise ModelUnavailable("ComfyUI isn't reachable")

    def _job(self, req: dict, work: Path) -> list:
        from studio.worldkit import jobs
        res = jobs.wait(jobs.submit(req), work=Path(work) / "_downloads")
        if res.get("status") != "done":
            raise ModelUnavailable(str(res.get("error") or res.get("status")))
        return res.get("artifacts") or []

    # ---- words
    def ask_qwen(self, system: str, user: str) -> str:
        """Only if it is already running: this never starts or wakes a service."""
        base = (paths.setting("PP_LLM_URL") or "").rstrip("/")
        if not base:
            raise ModelUnavailable("no local LLM is set")
        with urllib.request.urlopen(base + "/v1/models", timeout=3) as r:
            r.read()
        body = {"model": paths.setting("PP_LLM_MODEL") or "default", "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "temperature": 0.7, "max_tokens": 1400, "chat_template_kwargs": {"enable_thinking": False}}
        req = urllib.request.Request(base + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=240) as r:
            return json.load(r)["choices"][0]["message"]["content"]

    # ---- pictures
    def image(self, prompt: str, seed: int, work: Path, *, width: int = 1024, height: int = 1024, want: tuple = ("krea2", "image"), prefix: str = "gamebuilder/image", tries: int = 3) -> tuple[Path, str]:
        """Words to a picture with no lettering in it. A picture tesseract reads two or more words in is thrown away and the next seed tried. -> (path, the model's key)."""
        last = []
        for k in range(tries):
            pic, key = self._picture(prompt, seed + k * 1000, work, width, height, want, prefix)
            last = lettering(pic)
            if len(last) < 2:
                self.last_note = "" if shutil.which("tesseract") else "Not checked for lettering: tesseract isn't installed."
                return pic, key
        raise ModelUnavailable(f"every picture had lettering in it ({' '.join(last[:6])})")

    def _picture(self, prompt, seed, work, width, height, want, prefix) -> tuple[Path, str]:
        self._comfy()
        full = f"{prompt}, {NO_TEXT}"
        problems = []
        for key in want:
            n = C.need(key)
            if n["state"] != "ready":
                problems.append(n["message"])
                continue
            from studio.worldkit import jobs
            with self.turn(key):
                if key == "krea2":
                    arts = self._job(jobs.graph(KREA_GRAPH, {"prompt": full, "width": width, "height": height, "seed": int(seed), "prefix": prefix}, f"Game Builder: {prompt[:50]}"), work)
                else:
                    aspect = "16:9" if width > height else "1:1"
                    arts = self._job(jobs.goal("image", full, {"aspect": aspect, "mode": "fast"}, seed=int(seed)), work)
            pic = next((a for a in arts if a.get("media_type") == "image"), None)
            if pic:
                return Path(pic["path"]), key
            problems.append(f"{key} made no picture")
        raise ModelUnavailable("; ".join(problems) or "no picture model")

    # ---- meshes
    def mesh_from_picture(self, picture: Path, seed: int, work: Path, prefix: str, want: tuple = ("trellis2_main", "triposr", "hunyuan3d")) -> tuple[Path, str]:
        """A picture to a raw mesh, trying each route until one works. -> (glb, the model's key)."""
        from studio.worldkit import jobs
        problems = []
        for key in want:
            try:
                if key == "trellis2_main":
                    self._need("trellis2_main")
                    self._comfy()
                    name = jobs.to_input(picture)
                    with self.turn(key):
                        arts = self._job({**jobs.graph(TRELLIS_GRAPH, {"image": name, "prefix": prefix}, f"Game Builder mesh: {prefix}"), "portable": True}, work)
                    glb = next((a for a in arts if str(a.get("path", "")).lower().endswith(".glb")), None)
                    if not glb:
                        raise ModelUnavailable("TRELLIS.2 finished with no GLB")
                    return Path(glb["path"]), key
                if key == "triposr":
                    self._need("triposr")
                    from studio.worldkit.makers.prop import _runner
                    cut = self._cutout(picture, work)
                    with self.turn(key):
                        return Path(_runner("triposr", ["--image", str(cut)], Path(work) / "triposr")), key
                if key == "hunyuan3d":
                    self._need("hunyuan3d")
                    fam, tid = C.NEEDS["hunyuan3d"]["family"]
                    with self.turn(key):
                        arts = self._job(jobs.family(fam, tid, image=str(picture)), work)
                    glb = next((a for a in arts if str(a.get("path", "")).lower().endswith(".glb")), None)
                    if glb:
                        return Path(glb["path"]), key
                    raise ModelUnavailable("Hunyuan3D finished with no GLB")
            except Exception as exc:
                problems.append(f"{NAMES.get(key, key)}: {exc}"[:300])
        raise ModelUnavailable("; ".join(problems) or "no mesh model")

    def _cutout(self, picture: Path, work: Path) -> Path:
        from studio.worldkit import jobs
        from studio.worldkit.makers.prop import CUTOUT_GRAPH
        self._need("cutout")
        self._comfy()
        with self.turn("image"):
            arts = self._job(jobs.graph(CUTOUT_GRAPH, {"image": jobs.to_input(picture)}, "Game Builder cut-out"), work)
        return Path(next(a["path"] for a in arts if a.get("media_type") == "image"))

    def mesh_from_words(self, words: str, seed: int, work: Path) -> tuple[Path, str]:
        from studio.worldkit.makers.prop import _runner
        self._need("shap_e")
        with self.turn("shap_e"):
            return Path(_runner("shap_e", ["--prompt", words, "--seed", int(seed)], Path(work) / "shap_e")), "shap_e"

    def game_ready(self, model: Path, out: Path, faces: int, texture: int, work: Path) -> dict:
        """Blender, CPU: fewer faces, smaller textures, pivot at the feet."""
        from studio.worldkit import blender as B
        Path(work).mkdir(parents=True, exist_ok=True)
        with B.cpu_only():
            res = B.run("gb_gameready.py", {"model": str(model), "out": str(out), "faces": faces, "texture": texture}, work=Path(work), name="gameready", timeout=900, gpu=False)
        return res.get("inspect") or {}

    # ---- characters
    def character_sheet(self, name: str, description: str, seed_take: int = 0, tries: int = 3):
        """An invented adult from words: the World Kit sheet (Krea 2, then the picture check). -> (sheet path, saved character's id). A sheet that doesn't pass is thrown away and the next seed is tried; three strikes raises."""
        from studio.worldkit import characters as CS, jobs
        self._comfy()
        self._need("krea2")
        self._need("picturecheck")
        ch, why = CS.create(name, description)
        if ch is None:
            raise ModelUnavailable(why)
        last = ""
        for _ in range(tries):
            with self.turn("krea2"):
                got = CS.build_sheet(ch.id)
            if got and got.status == "ready" and got.sheet().is_file():
                return got.sheet(), ch.id
            last = (got.error if got else "") or (got.status if got else "gone")
            ch = CS.next_take(ch.id)
        raise ModelUnavailable(f"the sheet didn't pass the picture check: {last}"[:300])

    def rig(self, mesh: Path, work: Path) -> Path:
        from studio.worldkit import tools
        self._need("skintokens")
        with self.turn("skintokens"):
            return Path(tools.skintokens(mesh, Path(work)))

    def motion(self, text: str, seconds: int, seed: int, work: Path) -> Path:
        from studio.worldkit import tools
        self._need("kimodo")
        with self.turn("kimodo"):
            return Path(tools.kimodo(text, Path(work), seconds=seconds, seed=seed))

    def retarget(self, bvh: Path, rig: Path, work: Path) -> Path:
        from studio.worldkit import tools
        return Path(tools.retarget(bvh, rig, Path(work)))

    def assemble_character(self, rig: Path, clips: list, height_m: float, out: Path, work: Path) -> dict:
        from studio.worldkit import blender as B
        Path(work).mkdir(parents=True, exist_ok=True)
        with B.cpu_only():
            return B.run("wk_assemble.py", {"rig": str(rig), "clips": [{"name": n, "path": str(p)} for n, p in clips], "height_m": height_m, "out": str(out)}, work=Path(work), name="assemble", timeout=1800, gpu=False)

    # ---- places
    def place(self, brief: str, seed: int, work: Path, *, textures: str = "auto") -> tuple[Path, dict]:
        """A World Kit place from a brief, without the library. -> (glb, recipe)."""
        from studio.worldkit import jobs, steps as S
        from studio.worldkit.makers import place as PL
        recipe = PL.plan(brief, seed=seed, overrides={"textures": textures})
        recipe["kit"] = recipe["kit"]
        work = Path(work)
        work.mkdir(parents=True, exist_ok=True)

        class Lib:
            def subdir(self, aid, name):
                d = work / name
                d.mkdir(parents=True, exist_ok=True)
                return d
        meta = {"id": "gb_place", "name": "place", "type": "place", "recipe": recipe}
        ctx = {"asset": meta, "library": Lib(), "work": work}
        st = S.run(None, PL.steps(meta), ctx=ctx, submit=jobs.submit, wait=lambda j: jobs.wait(j, work=work / "_downloads"), save=lambda _s: None)
        if st.get("state") != "done":
            raise ModelUnavailable(str(st.get("error"))[:300])
        return Path(S.outputs(st)[PL.BUILD_STEP]["main"]["path"]), recipe

    # ---- sound
    def music(self, mood: str, bpm: int, seed: int, seconds: int, work: Path, want: tuple = ("ace15",)) -> tuple[Path, str]:
        """An instrumental from a mood. -> (audio file, the model's key)."""
        from studio.worldkit import jobs
        self._comfy()
        problems = []
        for key in want:
            try:
                if key == "ace15":
                    root = C.models_root()
                    if not any((root / p).is_file() for p in ("diffusion_models/acestep_v1.5_turbo.safetensors", "_complete_pipelines/ACE-Step-1.5/diffusion_models/acestep_v1.5_turbo.safetensors")):
                        raise ModelUnavailable("the ACE-Step 1.5 Turbo weights aren't here")
                    with self.turn(key):
                        arts = self._job({**jobs.graph(ACE_GRAPH, {"style": f"instrumental video game music, {mood}, seamless loop", "lyrics": "[instrumental]", "seconds": seconds, "seed": int(seed), "bpm": int(bpm), "key": "C major", "prefix": "gamebuilder/music"}, "Game Builder music"), "portable": True}, work)
                else:
                    with self.turn(key):
                        arts = self._job(jobs.goal("music", f"{mood}, instrumental, no vocals", {}, seed=int(seed)), work)
                got = next((a for a in arts if str(a.get("path", "")).lower().endswith((".flac", ".mp3", ".wav", ".ogg", ".m4a", ".opus"))), None)
                if got:
                    return Path(got["path"]), key
                raise ModelUnavailable("no audio file came back")
            except Exception as exc:
                problems.append(f"{NAMES.get(key, key)}: {exc}"[:300])
        raise ModelUnavailable("; ".join(problems))

    def speech(self, text: str, voice: str, dest: Path) -> Path:
        """Only if a speech server is running here. Voice lines are optional: a game without them shows the words."""
        from studio import voice as V
        s = V.speech()
        if not s.get("tts"):
            raise ModelUnavailable(V.NONE)
        raise ModelUnavailable("voice lines aren't wired to this speech server yet")


def copy_into(src, dest) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return dest
