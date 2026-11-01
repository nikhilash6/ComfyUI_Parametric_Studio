"""Our own recipe renders on the Recipes page: every file is small, clean of metadata and tied to a real library recipe, and a recipe without one shows none. Fixtures only: no live port, no GPU."""
import json, re, struct
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import studio.server as S
from studio import recipe_check as C, recipes as R, sfw

ROOT = Path(__file__).resolve().parent.parent; WEB = ROOT / "studio" / "web"; FOLDER = WEB / "recipe_renders"; DATA = ROOT / "studio" / "recipe_renders.json"; JS = WEB / "recipes.js"
ALSO_ADULT = re.compile(r"\b(bikini|swimwear|sensual|seductive|boudoir|cleavage|lingerie|schoolgirl|underage)\b", re.I)
SMALL_KB = {"picture": 64, "video": 1100, "audio": 200}; TOTAL_MB = 150
ROWS = json.loads(DATA.read_text(encoding="utf-8"))["renders"]
def of(kind): return {i: r for i, r in ROWS.items() if r["kind"] == kind}

def webp_chunks(path):
    """The chunk names inside a WebP file, read from its RIFF container."""
    b = path.read_bytes(); assert b[:4] == b"RIFF" and b[8:12] == b"WEBP", path; out = []; i = 12
    while i < len(b): name, size = b[i:i + 4].decode("latin1"), struct.unpack("<I", b[i + 4:i + 8])[0]; out.append(name); i += 8 + size + (size & 1)
    return out
@pytest.fixture
def client(monkeypatch):
    C._cache.clear(); monkeypatch.setattr(C, "context", lambda: ({}, {})); return TestClient(S.app)

def test_every_kind_is_there_and_the_folder_stays_under_the_limit():
    assert of("picture") and of("video") and of("audio") and sum(p.stat().st_size for p in FOLDER.iterdir()) < TOTAL_MB * 1e6
def test_each_mapped_file_exists_and_is_small():
    ext = {"picture": "webp", "video": "mp4", "audio": "m4a"}
    for rid, r in ROWS.items():
        p = WEB / r["file"]; assert p.is_file(), rid; assert p.parent == FOLDER and p.name == f"{rid}.{ext[r['kind']]}", rid; assert 1024 < p.stat().st_size <= SMALL_KB[r["kind"]] * 1024, (rid, p.stat().st_size)
def test_each_picture_and_poster_is_a_webp_about_512_on_its_long_side():
    for rid, r in ROWS.items():
        for key in ("file", "poster"):
            if r["kind"] != "picture" and key == "file" or not r.get(key): continue
            with Image.open(WEB / r[key]) as im: assert im.format == "WEBP" and max(im.size) == 512, rid
        if r["kind"] == "picture":
            with Image.open(WEB / r["file"]) as im: assert im.size == (r["width"], r["height"]), rid
def test_no_webp_carries_metadata():
    for rid, r in ROWS.items():
        for key in ("file", "poster"):
            if str(r.get(key, "")).endswith(".webp"): assert not {"EXIF", "XMP ", "ICCP"} & set(webp_chunks(WEB / r[key])), rid
def test_clips_and_sounds_are_real_mp4_containers():
    for rid, r in {**of("video"), **of("audio")}.items(): assert (WEB / r["file"]).read_bytes()[4:8] == b"ftyp", rid
def test_every_id_is_in_the_library():
    ids = {r["id"] for r in R.library()}; assert not set(ROWS) - ids
def test_no_stray_files_either_way():
    named = {Path(r[k]).name for r in ROWS.values() for k in ("file", "poster") if r.get(k)}; assert {p.name for p in FOLDER.iterdir()} == named
def test_a_row_keeps_what_the_run_recorded():
    for rid, r in ROWS.items():
        assert r["seconds"] >= 0 and r["peak_scope"] in ("recipe", "card", "none") and r["card_peak_vram_gib"] >= r["peak_vram_gib"] and r["model"] and re.fullmatch(r"[0-9a-f]{12}", r["run"]) and re.fullmatch(r"\d{4}-\d\d-\d\d", r["rendered"]), rid
        if r["kind"] != "audio": assert isinstance(r["seed"], int) and r["seconds"] > 0 and r["peak_vram_gib"] > 0 and r["model"].endswith(".safetensors") and r["prompt"].strip(), rid
def test_a_clip_says_how_much_of_the_output_it_is_and_has_a_poster():
    for rid, r in of("video").items(): assert 0 < r["clip_seconds"] <= r["full_seconds"] + 0.1 and r["clip_seconds"] <= 20.1 and (WEB / r["poster"]).is_file(), rid
def test_a_sound_carries_its_shape():
    for rid, r in of("audio").items(): assert len(r["peaks"]) == 48 and max(r["peaks"]) == 1.0 and r["seed"] is None, rid
def test_data_names_no_private_path_and_nothing_adult():
    t = DATA.read_text(encoding="utf-8"); assert "/" + "home/" not in t and "/" + "mnt/" not in t and not sfw.flagged(t) and not ALSO_ADULT.search(t)
def test_a_rendered_recipe_carries_its_render_and_others_carry_none(client):
    rid = next(iter(ROWS)); assert client.get(f"/api/recipes/{rid}").json()["render"] == ROWS[rid]
    other = next(r["id"] for r in R.library() if r["id"] not in ROWS); assert client.get(f"/api/recipes/{other}").json()["render"] is None
    rows = {r["id"]: r for r in client.get("/api/recipe-library?kind=picture&limit=200").json()["recipes"]}; assert rows and all(r["render"] == ROWS.get(i) for i, r in rows.items())
    d = client.get("/api/recipe-library?limit=1").json(); assert d["rendered"] == len(ROWS) and d["total"] == len(R.library())
def test_rendered_recipes_come_first_and_can_be_shown_alone(client):
    rows = client.get("/api/recipe-library?limit=200").json()["recipes"]; flags = [bool(r["render"]) for r in rows]; assert flags == sorted(flags, reverse=True)
    d = client.get("/api/recipe-library?rendered_only=true&limit=5").json(); assert d["total"] == len(ROWS) and all(r["render"] for r in d["recipes"])
def test_a_render_does_not_count_as_tested(client):
    rid = next(iter(ROWS)); d = client.get(f"/api/recipes/{rid}").json(); assert d["tested"] is None and d["status"] == "untested"
@pytest.mark.parametrize("kind,mime", [("picture", "image/webp"), ("video", "video/mp4"), ("audio", "audio/")])
def test_the_files_are_served_from_the_web_folder(client, kind, mime):
    r = client.get("/" + next(iter(of(kind).values()))["file"]); assert r.status_code == 200 and r.headers["content-type"].startswith(mime), r.headers["content-type"]
def test_the_page_labels_a_render_and_only_shows_one_when_there_is_one():
    js = JS.read_text(); assert '"Our own render"' in js and "if (!x) return" in js and "recipe.proof && !recipe.render" in js and "!run && recipe.render" in js and "not yet judged by ear" in js
