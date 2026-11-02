"""The Game Builder: the spec, the levels, the pipeline's promises and the page. No live ports, no GPU. Godot's own checks run here when a Godot binary is available and are skipped when it isn't; the real end-to-end runs are recorded in docs/GAME_BUILDER.md."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException

from studio.gamebuilder import assemble as AS
from studio.gamebuilder import levels as LV
from studio.gamebuilder import pipeline as P
from studio.gamebuilder import procedural as PR
from studio.gamebuilder import spec as SP
from studio import feature_gamebuilder as F

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "studio" / "gamebuilder" / "template"
PROMPTS = {"platformer": "a platformer in a mushroom forest, collect golden acorns, avoid grumpy pinecones", "arena": "top-down arena survival on the moon, waves of round drones", "kart": "kart racing through a desert canyon", "quest": "an exploration adventure across a snowy island to find lost runes", "mystery": "a detective mystery in an old harbour town, a stolen bell, three suspects"}


def make(kit, **kw):
    s, bad = SP.validate(SP.deterministic([PROMPTS[kit]], kit=kit, **kw))
    assert not bad, bad
    return s


# ---------- the spec
@pytest.mark.parametrize("kit", list(SP.KITS))
def test_the_words_choose_each_kit(kit):
    assert SP.choose_kit(PROMPTS[kit].lower())[0] == kit
    assert SP.deterministic([PROMPTS[kit]])["kit"] == kit


def test_the_vehicle_is_what_you_drive_not_where():
    s = SP.deterministic(["Kart racing through a sunset desert canyon.", "Drive a stubby go-kart with chunky wheels. Called Canyon Dash."])
    assert s["player"]["description"] == "a stubby go-kart" and s["title"] == "Canyon Dash"
    assert "canyon" not in SP.deterministic(["Kart racing through a desert canyon."])["player"]["description"]


def test_no_genre_word_still_gives_a_game_and_says_why():
    s = SP.deterministic(["something lovely"])
    assert s["kit"] == "platformer" and "no genre word" in s["kit_why"] and s["source"] == "words"
    assert SP.validate(s)[1] == []


def test_the_same_words_give_the_same_spec():
    assert SP.deterministic(["a kart race"]) == SP.deterministic(["a kart race"])
    assert SP.deterministic(["a kart race"])["seed"] != SP.deterministic(["a kart race on ice"])["seed"]


def test_words_found_in_a_sentence_reach_the_spec():
    s = SP.deterministic(['A platformer called "Pearl Run". You play as a tired mail carrier collecting glowing pearls while avoiding angry crabs.'])
    assert s["title"] == "Pearl Run"
    assert "mail carrier" in s["player"]["description"] and "adult" in s["player"]["description"]
    assert s["items"][0]["name"] == "Glowing Pearl" and s["items"][0]["plural"] == "glowing pearls"
    assert "crab" in s["enemies"][0]["description"]


@pytest.mark.parametrize("words", ["a game about nude dancers", "a platformer starring Mario", "a kart race with Pikachu", "a gory bloodbath arena", "a schoolgirl platformer", "a game with someone who looks like a famous actress"])
def test_refused_words(words):
    assert SP.text_problems(words)
    with pytest.raises(HTTPException):
        F.check_body({"prompts": [words]})


def test_validate_refuses_a_bad_spec_and_clamps_numbers():
    s = make("arena")
    s["title"] = ""
    s["setting"]["palette"]["sky"] = "red"
    s["kit"] = "golf"
    bad = SP.validate(s)[1]
    assert any("title" in b for b in bad) and any("palette" in b for b in bad) and any("kit must" in b for b in bad)
    s = make("arena")
    s["enemies"][0]["speed"] = 900
    assert SP.validate(s)[0]["enemies"][0]["speed"] == 7.0


def test_the_hero_must_be_an_invented_adult():
    s = make("platformer")
    s["player"]["description"] = "a little child in shorts"
    assert any("child" in b for b in SP.validate(s)[1])


def test_a_mystery_must_be_solvable():
    s = make("mystery")
    assert len(s["story"]["suspects"]) == 3 and len(s["story"]["clues"]) == 4
    guilty = s["story"]["suspects"][s["story"]["culprit"]]["name"]
    others = [x["name"] for x in s["story"]["suspects"] if x["name"] != guilty]
    alibis = " ".join(c["text"] for c in s["story"]["clues"])
    assert all(n in alibis for n in others) and guilty not in alibis
    s["story"]["culprit"] = 9
    assert any("culprit" in b for b in SP.validate(s)[1])


# ---------- a model's answer
def test_qwen_off_falls_back_and_says_so():
    def ask(_s, _u):
        raise ConnectionError("no")
    s, note = SP.from_model(["a kart race"], ask)
    assert s["source"] == "words" and "isn't running" in note and SP.validate(s)[1] == []


def test_qwen_garbage_falls_back():
    s, note = SP.from_model(["a kart race"], lambda _s, _u: "I would love to help!")
    assert s["source"] == "words" and "wasn't JSON" in note


def test_qwen_words_are_used_and_checked():
    ans = {"title": "Dune Dash", "tagline": "Sand in your teeth.", "kit": "kart", "time": "golden", "weather": "clear", "palette": {"sky": "#112233", "nope": "#000000"}, "props": ["a rusty water tank"], "mood": "surf rock", "intro": ["Go.", "Now."], "win": "Yes.", "lose": "No."}
    s, note = SP.from_model(["some game"], lambda _s, _u: json.dumps(ans))
    assert s["source"] == "qwen" and s["title"] == "Dune Dash" and s["kit"] == "kart" and s["setting"]["palette"]["sky"] == "#112233" and "nope" not in s["setting"]["palette"]
    assert s["props"][0]["description"] == "a rusty water tank" and "Written by Qwen" in note


def test_qwen_cannot_slip_past_the_checks():
    ans = {"title": "Mario Kart Pro", "kit": "kart"}
    s, note = SP.from_model(["a game"], lambda _s, _u: json.dumps(ans))
    assert s["source"] == "words" and "failed the checks" in note and "Mario" not in s["title"]


def test_qwen_never_gets_the_level_or_code():
    assert "level" not in SP.QWEN_FIELDS and "code" not in SP.QWEN_FIELDS
    ans = {"title": "OK", "kit": "arena", "level": {"size": "huge"}, "seed": "x", "script": "OS.execute('rm')"}
    s, _ = SP.from_model(["arena"], lambda _s, _u: json.dumps(ans))
    assert s["level"]["size"] == "medium" and "script" not in s and isinstance(s["seed"], int)


# ---------- levels
@pytest.mark.parametrize("kit", list(SP.KITS))
@pytest.mark.parametrize("size", SP.SIZES)
@pytest.mark.parametrize("seed", [1, 2, 3, 77])
def test_every_level_is_finishable(kit, size, seed):
    s = make(kit, size=size, seed=seed)
    lv = LV.build(s)
    assert LV.problems(s, lv) == []
    json.dumps(lv)


def test_the_jump_check_catches_an_impossible_jump():
    s = make("platformer", size="small", seed=1)
    lv = LV.build(s)
    last = lv["route"][3]["p"]
    lv["platforms"][last]["pos"][0] += 60
    assert LV.platformer_problems(lv)


def test_the_jump_numbers_match_the_kit():
    src = (TEMPLATE / "core" / "player3p.gd").read_text()
    assert f"var jump_velocity := {LV.JUMP_V}" in src and f"var gravity_up := {LV.G_UP}" in src and f"var fall_mult := {LV.FALL_MULT}" in src and f"var speed := {LV.RUN}" in src


def test_a_track_that_crosses_itself_is_refused():
    lv = LV.build(make("kart", size="small", seed=1))
    assert LV.kart_problems(lv) == []
    lv["center"] = lv["center"] + [p for p in lv["center"]]
    assert LV.kart_problems(lv)


# ---------- the kits are real files
def test_every_kit_has_a_win_a_lose_and_a_bot():
    for kit in SP.KITS:
        src = (TEMPLATE / "kits" / f"{kit}.gd").read_text()
        assert "extends KitBase" in src and "Game.win(" in src and "func bot_tick" in src and "func build" in src
        if kit != "mystery":
            assert "Game.lose(" in src
    assert 'Game.lose("wrong twice")' in (TEMPLATE / "kits" / "mystery.gd").read_text()


def test_the_bot_only_presses_keys():
    src = (TEMPLATE / "core" / "bot.gd").read_text()
    assert "Input.action_press" in src and "global_position" not in src and ".position =" not in src
    for kit in SP.KITS:
        body = (TEMPLATE / "kits" / f"{kit}.gd").read_text().split("func bot_tick", 1)[1]
        assert "player.position =" not in body and "car.position =" not in body and "Game.win" not in body and ".collect()" not in body


def test_no_lettering_comes_from_a_picture():
    from studio.gamebuilder import models as M
    assert "no text" in M.NO_TEXT and "no letters" in M.NO_TEXT
    assert "font" in (TEMPLATE / "core" / "ui.gd").read_text()


# ---------- the pipeline with fake models
class Fakes:
    """Every model answers from nothing: a tiny file. What's being tested is the pipeline's bookkeeping, and it's what a test can honestly say."""
    def __init__(self, broken=()):
        self.calls = []
        self.broken = set(broken)

    def _go(self, what):
        self.calls.append(what)
        if what in self.broken:
            raise RuntimeError(f"{what} is broken")

    def ask_qwen(self, _s, _u):
        raise ConnectionError("off")

    def image(self, prompt, seed, work, *, width=1024, height=1024, want=(), prefix=""):
        self._go("image")
        from PIL import Image
        Path(work).mkdir(parents=True, exist_ok=True)
        p = Path(work) / f"pic{seed}.png"
        Image.new("RGB", (64, 64), (seed % 255, 80, 120)).save(p)
        return p, want[0] if want else "image"

    def mesh_from_picture(self, picture, seed, work, prefix, want=()):
        self._go("mesh")
        p = Path(work) / "raw.glb"
        p.write_bytes(b"glTF")
        return p, "trellis2_main"

    def mesh_from_words(self, words, seed, work):
        self._go("words_mesh")
        p = Path(work) / "words.glb"
        p.write_bytes(b"glTF")
        return p, "shap_e"

    def game_ready(self, model, out, faces, texture, work):
        self._go("game_ready")
        Path(out).write_bytes(b"glTF")
        return {"faces": faces}

    def character_sheet(self, name, description, *a):
        self._go("sheet")
        from PIL import Image
        p = Path("/tmp") if False else None
        d = Path(self.tmp)
        d.mkdir(parents=True, exist_ok=True)
        q = d / "sheet.png"
        Image.new("RGB", (32, 32)).save(q)
        return q, "cid"

    def rig(self, mesh, work):
        self._go("rig")
        Path(work).mkdir(parents=True, exist_ok=True)
        p = Path(work) / "rigged.glb"
        p.write_bytes(b"glTF")
        return p

    def motion(self, text, seconds, seed, work):
        self._go("motion")
        p = Path(work) / "m.bvh"
        p.write_text("HIERARCHY")
        return p

    def retarget(self, bvh, rig, work):
        self._go("retarget")
        Path(work).mkdir(parents=True, exist_ok=True)
        p = Path(work) / "clip.fbx"
        p.write_bytes(b"fbx")
        return p

    def assemble_character(self, rig, clips, height, out, work):
        self._go("assemble")
        Path(out).write_bytes(b"glTF")
        return {"clips": [{"name": n} for n, _ in clips]}

    def place(self, brief, seed, work, *, textures="auto"):
        self._go("place")
        Path(work).mkdir(parents=True, exist_ok=True)
        p = Path(work) / "place.glb"
        p.write_bytes(b"glTF")
        return p, {"kit": "street", "size_m": [40.0, 24.0], "time": "day", "weather": "clear", "textures": textures}

    def music(self, mood, bpm, seed, seconds, work, want=()):
        self._go("music")
        p = Path(work) / "song.wav"
        Path(work).mkdir(parents=True, exist_ok=True)
        PR._write(p, __import__("numpy").zeros(22050 * 8))
        return p, "ace15"


godot = AS.godot_path()
needs_godot_late = pytest.mark.skipif(not godot, reason="no Godot: set STUDIO_GODOT")


def run_fake(tmp_path, kit, *, broken=(), gid="g1", models=None, stop_at_project=True):
    f = models or Fakes(broken)
    f.tmp = tmp_path / "sheets"
    g = P.Game(gid, [PROMPTS[kit]], {"kit": kit, "size": "small", "seed": 5}, models=f, base=tmp_path, godot="")
    state = g.run()
    return g, state, f


needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="no ffmpeg")


@needs_ffmpeg
def test_a_whole_run_records_model_seed_and_licence(tmp_path):
    g, s, _ = run_fake(tmp_path, "platformer")
    items = {i["id"]: i for st in s["stages"] for i in st["items"]}
    assert items["tex_ground"]["model"] == "FLUX.2 Klein 4B" and items["tex_ground"]["licence"].startswith("Apache")
    assert items["prop0"]["model"] == "TRELLIS.2" and items["prop0"]["seed"] is not None
    assert items["hero"]["model"] == "SkinTokens" and "Clips by Kimodo" in items["hero"]["note"]
    assert items["music"]["model"] == "ACE-Step 1.5 Turbo"
    assert s["fallbacks"] == 0
    # With no Godot it stops at the check, says why, and the project is on disk.
    assert s["state"] == "failed" and "STUDIO_GODOT" in s["error"]
    project = tmp_path / "g1" / "project"
    assert (project / "kits" / "kit.gd").read_text() == (TEMPLATE / "kits" / "platformer.gd").read_text()
    spec = json.loads((project / "game" / "spec.json").read_text())
    assert spec["player"]["asset"] == "hero" and (project / "game" / "models" / "hero.glb").is_file()
    credits = json.loads((project / "game" / "credits.json").read_text())
    assert any("TRELLIS" in c["licence"] for c in credits) and any(c.get("model") == "kimodo" for c in credits)
    assert s["licence_summary"]


@needs_ffmpeg
def test_a_rerun_rebuilds_nothing_a_model_already_made(tmp_path):
    _, _, f = run_fake(tmp_path, "arena", gid="g1")
    n = len(f.calls)
    assert n > 5
    _, s, f2 = run_fake(tmp_path, "arena", gid="g2")
    assert f2.calls == []
    items = [i for st in s["stages"] for i in st["items"]]
    assert any(i["cached"] for i in items)


@needs_ffmpeg
def test_a_broken_model_gets_a_marked_stand_in_and_the_game_still_assembles(tmp_path):
    g, s, _ = run_fake(tmp_path, "platformer", broken=("image", "mesh", "words_mesh", "sheet", "music"))
    items = {i["id"]: i for st in s["stages"] for i in st["items"]}
    assert s["fallbacks"] >= 5
    for iid in ("tex_ground", "title", "prop0", "hero", "music"):
        assert items[iid]["status"] == "fallback" and "Stand-in" in items[iid]["note"] and "broken" in items[iid]["note"]
        assert "TRELLIS" not in items[iid]["model"] and "Klein" not in items[iid]["model"]
    project = tmp_path / "g1" / "project"
    spec = json.loads((project / "game" / "spec.json").read_text())
    assert spec["player"]["asset"] == "" and spec["props"][0]["asset"] == ""
    assert (project / "game" / "tex" / "ground.png").is_file() and (project / "game" / "audio" / "music.ogg").is_file()
    assert any("stand-in" in c.get("note", "") for c in json.loads((project / "game" / "credits.json").read_text()))


@needs_ffmpeg
def test_a_stand_in_is_not_cached_so_the_next_run_tries_the_model_again(tmp_path):
    run_fake(tmp_path, "arena", broken=("image",), gid="g1")
    _, s, f = run_fake(tmp_path, "arena", gid="g2")
    assert "image" in f.calls


@needs_ffmpeg
def test_a_failed_rig_keeps_the_mesh_and_says_so(tmp_path):
    _, s, _ = run_fake(tmp_path, "platformer", broken=("rig",))
    hero = next(i for st in s["stages"] for i in st["items"] if i["id"] == "hero")
    assert hero["model"] == "TRELLIS.2" and "no rig" in hero["note"] and "SkinTokens" not in hero["model"]


@needs_ffmpeg
def test_a_mystery_uses_a_place_and_its_people(tmp_path):
    g, s, f = run_fake(tmp_path, "mystery")
    assert "place" in f.calls
    assert g.level["place"] == "place" and g.level["size"] == [44.0, 28.0]
    assert all(r["spot"] != [0, 0, 0] for r in g.spec["story"]["suspects"])
    assert g.spec["story"]["suspects"][0]["asset"] == "suspect0"


def test_cancel_stops_at_the_next_item(tmp_path):
    import threading
    ev = threading.Event()
    ev.set()
    f = Fakes()
    f.tmp = tmp_path / "x"
    s = P.Game("g1", ["a kart race"], {}, models=f, base=tmp_path, cancel=ev, godot="").run()
    assert s["state"] == "cancelled" and f.calls == []


def test_ids_are_checked(tmp_path):
    assert P.game_dir("../../etc", tmp_path) is None and P.game_dir("a/b", tmp_path) is None and P.read_state("..", tmp_path) is None


def test_loop_seam_shortens_by_the_fold(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("no ffmpeg")
    import numpy as np
    wav = tmp_path / "a.wav"
    PR._write(wav, np.zeros(22050 * 12))
    out = P.loop_seam(wav, tmp_path / "o.ogg")
    assert out.is_file() and out.stat().st_size > 0


def test_procedural_sounds_and_art(tmp_path):
    names = PR.sfx_set(tmp_path / "s", seed=3)
    for n in ("jump", "coin", "win", "lose", "engine"):
        assert n in names and (tmp_path / "s" / f"sfx_{n}.wav").stat().st_size > 100
    used = set()
    import re
    for f in [*TEMPLATE.glob("core/*.gd"), *TEMPLATE.glob("kits/*.gd")]:
        used |= set(re.findall(r'Game\.(?:sfx|loop_start)\("(\w+)"', f.read_text()))
    assert used <= set(names), used - set(names)
    from PIL import Image
    t = PR.title_art(tmp_path / "t.png", {"sky": "#112233", "horizon": "#aabbcc", "ground": "#334411"}, seed=2)
    with Image.open(t) as im:
        assert im.size == (1280, 720)


def test_a_godot_log_cannot_grow_without_bound(tmp_path):
    import sys
    rc, text = AS._run([sys.executable, "-c", "while True: print('SCRIPT ERROR: the same thing')"], tmp_path / "a.log", 60)
    assert rc == -2 and "repeated" in text and (tmp_path / "a.log").stat().st_size < 50_000
    rc, text = AS._run([sys.executable, "-c", "import itertools\nfor i in itertools.count(): print(i)"], tmp_path / "b.log", 60, cap=300_000)
    assert rc == -2 and "reached" in text and (tmp_path / "b.log").stat().st_size < 400_000
    rc, text = AS._run([sys.executable, "-c", "print('fine')"], tmp_path / "c.log", 60)
    assert rc == 0 and text.strip() == "fine"


def test_godots_own_log_file_is_off_in_every_kits_project(tmp_path):
    for kit in SP.KITS:
        s = make(kit)
        p = AS.scaffold(s, LV.build(s), {"models": {}, "textures": {}}, [], tmp_path / kit)
        text = (p / "project.godot").read_text()
        assert "\n[debug]\n" in text and "file_logging/enable_file_logging=false" in text and "file_logging/enable_file_logging.pc=false" in text


def test_the_runner_also_watches_godots_user_log(tmp_path, monkeypatch):
    import sys
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "project.godot").write_text('[application]\nconfig/name="Runaway Test"\n')
    logs = AS.user_logs(proj)
    assert logs == tmp_path / "data" / "godot" / "app_userdata" / "Runaway Test" / "logs"
    logs.mkdir(parents=True)
    writer = f"import time\nf=open({str(logs / 'godot.log')!r},'w')\nwhile True:\n f.write('x'*100000); f.flush(); time.sleep(0.01)\n"
    rc, text = AS._run([sys.executable, "-c", writer, "--path", str(proj)], tmp_path / "run.log", 60, cap=2_000_000)
    assert rc == -2 and "own log" in text and (logs / "godot.log").stat().st_size < 20_000_000


def test_every_godot_run_goes_through_the_capped_runner():
    src = (ROOT / "studio" / "gamebuilder" / "assemble.py").read_text()
    body = src.split("def _run(", 1)[1]
    assert "subprocess.run(" not in body.split("def can_record", 1)[0].replace("subprocess.run([\"ffmpeg\"", "")
    game = (TEMPLATE / "core" / "game.gd").read_text()
    assert "OS.add_logger" in game and "RUNAWAY_SAME" in game and '_stop("error_loop"' in game
    main = (TEMPLATE / "main.gd").read_text()
    assert "Game.fatal(" in main and "if kit == null" in main


def test_constrained_scripts_are_refused_before_godot_sees_them():
    assert AS.constrained_script_problems("extends Node3D\nfunc _process(d):\n\trotation.y += d\n") == []
    for bad in ("extends Node3D\nfunc _ready():\n\tOS.execute('rm', [])\n", "extends Node3D\nvar f = FileAccess.open('x', 1)\n", "extends Node3D\nvar s = load('res://x.gd')\n", "extends Node\n", "extends Node3D\n" + "#" * 2000, "extends Node3D\nvar h = HTTPRequest.new()\n"):
        assert AS.constrained_script_problems(bad), bad


@needs_godot_late
def test_a_model_script_has_to_pass_godots_parser(tmp_path):
    s = make("arena")
    p = AS.scaffold(s, LV.build(s), {"models": {}, "textures": {}}, [], tmp_path / "p")
    AS.import_project(p, godot, tmp_path / "i.log", timeout=240)
    assert AS.check_constrained("extends Node3D\nfunc _process(d):\n\trotation.y += d\n", p, godot, tmp_path) == []
    assert AS.check_constrained("extends Node3D\nfunc _process(d):\n\trotation.y += \n", p, godot, tmp_path)
    assert not (p / "core" / "_candidate.gd").exists()


def test_templates_are_refused_when_the_hash_is_wrong(tmp_path):
    import zipfile
    def fetch(url, dest):
        with zipfile.ZipFile(dest, "w") as z:
            z.writestr("templates/version.txt", "x")
    with pytest.raises(AS.GodotError, match="SHA-512"):
        AS.install_templates(fetch=fetch, dest=tmp_path / "t", sums="deadbeef  " + Path(AS.TEMPLATES_URL).name)
    assert not (tmp_path / "t" / "version.txt").exists()
    import hashlib

    def good(url, dest):
        fetch(url, dest)
        good.sum = hashlib.sha512(Path(dest).read_bytes()).hexdigest()
    z = tmp_path / "z"
    z.mkdir()
    good(AS.TEMPLATES_URL, z / "x.tpz")
    assert AS.install_templates(fetch=fetch, dest=tmp_path / "t2", sums=f"{good.sum}  {Path(AS.TEMPLATES_URL).name}") is not None
    assert (tmp_path / "t2" / "version.txt").is_file()


def test_project_names_are_checked_and_quotes_cannot_break_the_file(tmp_path):
    s = make("arena")
    s["title"] = 'Bad "Title"\n[autoload]'
    p = AS.scaffold(s, LV.build(s), {"models": {}, "textures": {}}, [], tmp_path / "p")
    text = (p / "project.godot").read_text()
    assert text.splitlines().count("[autoload]") == 1 and not any(ln.startswith("config/name") and ln.count('"') != 2 for ln in text.splitlines())
    with pytest.raises(ValueError):
        AS.scaffold(s, {}, {"models": {"../evil": tmp_path / "x"}}, [], tmp_path / "q")


# ---------- the routes
def test_routes_check_what_they_are_sent():
    with pytest.raises(HTTPException):
        F.check_body({"prompts": []})
    with pytest.raises(HTTPException):
        F.check_body({"prompts": ["x"], "kit": "golf"})
    with pytest.raises(HTTPException):
        F.check_body({"prompts": ["x"], "size": "enormous"})
    prompts, o = F.check_body({"prompts": ["a kart race"], "kit": "auto", "seed": "12"})
    assert prompts == ["a kart race"] and o["seed"] == 12 and "kit" not in o


def test_plan_labels_where_the_words_came_from():
    def off(_s, _u):
        raise ConnectionError
    got = F.plan({"prompts": ["a kart race"]}, ask=off)
    assert got["source"] == "words" and "isn't running" in got["note"]


def test_only_one_build_at_a_time(monkeypatch):
    monkeypatch.setattr(P, "list_games", lambda: [{"running": True}])
    with pytest.raises(HTTPException) as e:
        F.start({"prompts": ["a kart race"]}, starter=lambda *_: "x")
    assert e.value.status_code == 409


def test_web_files_cannot_climb_out(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "root", lambda: tmp_path)
    (tmp_path / "g1" / "build" / "web").mkdir(parents=True)
    (tmp_path / "g1" / "state.json").write_text("{}")
    (tmp_path / "g1" / "build" / "web" / "index.wasm").write_bytes(b"x")
    assert F.game_web("g1", "index.wasm").media_type == "application/wasm"
    for bad in ("..", "../state.json", ".hidden", "a/b"):
        with pytest.raises(HTTPException):
            F.game_web("g1", bad)
    with pytest.raises(HTTPException):
        F.game_download("g1", "../../x")


def test_templates_route_needs_a_clear_yes():
    with pytest.raises(HTTPException):
        F.templates_post({})


def test_readiness_says_what_is_missing():
    r = F.readiness(need=lambda k: {"state": "missing", "message": f"{k} is missing"}, comfy=lambda: False)
    assert r["comfy"] is False and not any(m["ready"] for m in r["models"]) and "stand-in" in r["note"]


def test_the_page_is_wired_in():
    assert F.PAGE["tab"] == "gamebuilder" and (ROOT / "studio" / "web" / F.PAGE["module"]).is_file() and (ROOT / "studio" / "web" / F.PAGE["css"]).is_file()
    assert "#f5c518" in (ROOT / "studio" / "web" / "gamebuilder.css").read_text()
    from studio import graph_registry as G
    rows = {r["key"]: r for r in G._game_rows()}
    assert set(rows) == {f"gamebuilder:{k}" for k in SP.KITS} and all(r["open"] == "gamebuilder" for r in rows.values())
    assert "gamebuilder_ace15_music_api.json" in G.WORKFLOWS and "gamebuilder_ace15_music_api.json" in G.workflow_files()


def test_the_page_logic(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("no node")
    script = tmp_path / "t.mjs"
    logic = ROOT / "studio" / "web" / "gamebuilder_logic.js"
    script.write_text(f"""import * as L from "{logic.as_uri()}";
const a = (x, m) => {{ if (!x) throw new Error(m); }};
a(L.bytes(25000000) === "25 MB", "bytes"); a(L.clock(75) === "1 min 15", "clock"); a(L.clock(9) === "9 s", "clock s");
a(L.progress([{{status:"done"}},{{status:"skipped"}},{{status:"running"}},{{status:"pending"}}]).pct === 50, "progress");
a(L.whyNot([" "], false, {{godot:true}}).includes("Say what"), "empty"); a(L.whyNot(["x"], true, {{godot:true}}).includes("one at a time"), "busy"); a(L.whyNot(["x"], false, {{godot:false}}).includes("Godot"), "godot"); a(L.whyNot(["x"], false, {{godot:true}}) === "", "ok");
a(L.endWord({{state:"done", playtest:{{result:"won"}}}}).includes("win"), "won"); a(L.endWord({{state:"done", playtest:{{result:"lost"}}}}).includes("didn't"), "lost");
a(L.standIns(0).includes("Every"), "none"); a(L.standIns(2).includes("2 things"), "two");
""")
    subprocess.run([node, str(script)], check=True, timeout=60)


# ---------- Godot itself, when it's here
needs_godot = pytest.mark.skipif(not godot, reason="no Godot: set STUDIO_GODOT")


@needs_godot
@needs_ffmpeg
@pytest.mark.parametrize("kit", list(SP.KITS))
def test_each_kit_parses_and_the_bot_wins_with_stand_ins(tmp_path, kit):
    """The real engine and the real kit, headless, with every asset a stand-in: a person could play this. On easy, because on normal the arena can beat the bot, as it should a person now and then."""
    s = make(kit, size="small", seed=3, difficulty="easy")
    a = tmp_path / "a"
    a.mkdir()
    PR.sfx_set(a)
    assets = {"models": {}, "textures": {"ground": PR.texture(s["setting"]["ground"], a / "g.png", seed=1, tint="#556644"), "rock": PR.texture(s["setting"]["rock"], a / "r.png", seed=1, tint="#555555")}, "title": PR.title_art(a / "t.png", s["setting"]["palette"]), "icon": PR.icon(a / "i.png", s["setting"]["palette"]), "sfx": a}
    p = AS.scaffold(s, LV.build(s), assets, [], tmp_path / "p")
    AS.import_project(p, godot, tmp_path / "i.log", timeout=240)
    assert AS.check_scripts(p, godot, tmp_path) == []
    r = AS.playtest(p, godot, tmp_path / "r.json", tmp_path / "play.log", timeout_s=300, seconds=280)
    assert r["result"] == "won", (r.get("stats"), r.get("script_errors"))
    assert r["script_errors"] == []


@needs_godot
def test_a_broken_or_looping_game_stops_itself(tmp_path):
    s = make("arena", size="small", seed=3)
    p = AS.scaffold(s, LV.build(s), {"models": {}, "textures": {}}, [], tmp_path / "p")
    AS.import_project(p, godot, tmp_path / "i.log", timeout=240)
    kit = (p / "kits" / "kit.gd").read_text()
    (p / "kits" / "kit.gd").write_text(kit.replace("func hud_tick(_dt: float) -> void:", "func hud_tick(_dt: float) -> void:\n\tvar n = null\n\tn.foo()"))
    r = AS.playtest(p, godot, tmp_path / "r.json", tmp_path / "l.log", timeout_s=200)
    assert r["result"] == "error_loop" and (tmp_path / "l.log").stat().st_size < 1_000_000
    (p / "kits" / "kit.gd").write_text(kit + "\nfunc broken(:\n")
    r = AS.playtest(p, godot, tmp_path / "r2.json", tmp_path / "l2.log", timeout_s=120)
    assert r["result"] == "broken"
