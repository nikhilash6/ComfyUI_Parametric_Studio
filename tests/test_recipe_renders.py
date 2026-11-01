"""Our own recipe renders on the Recipes page: every picture is small, clean of metadata and tied to a real library recipe, and a recipe without one shows none. Fixtures only: no live port, no GPU."""
import json, re, struct
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import studio.server as S
from studio import recipe_check as C, recipes as R, sfw

ROOT = Path(__file__).resolve().parent.parent; WEB = ROOT / "studio" / "web"; FOLDER = WEB / "recipe_renders"; DATA = ROOT / "studio" / "recipe_renders.json"; JS = WEB / "recipes.js"
ALSO_ADULT = re.compile(r"\b(bikini|swimwear|sensual|seductive|boudoir|cleavage|lingerie|schoolgirl|underage)\b", re.I)
SMALL_KB, TOTAL_MB = 64, 25
ROWS = json.loads(DATA.read_text(encoding="utf-8"))["renders"]

def chunks(path):
    """The chunk names inside a WebP file, read from its RIFF container."""
    b = path.read_bytes(); assert b[:4] == b"RIFF" and b[8:12] == b"WEBP", path; out = []; i = 12
    while i < len(b): name, size = b[i:i + 4].decode("latin1"), struct.unpack("<I", b[i + 4:i + 8])[0]; out.append(name); i += 8 + size + (size & 1)
    return out
@pytest.fixture
def client(monkeypatch):
    C._cache.clear(); monkeypatch.setattr(C, "context", lambda: ({}, {})); return TestClient(S.app)

def test_there_are_renders_and_the_folder_stays_under_the_limit():
    assert ROWS and sum(p.stat().st_size for p in FOLDER.iterdir()) < TOTAL_MB * 1e6
def test_each_mapped_file_exists_and_is_small():
    for rid, r in ROWS.items():
        p = WEB / r["file"]; assert p.is_file(), rid; assert p.parent == FOLDER and p.name == f"{rid}.webp", rid; assert 1024 < p.stat().st_size <= SMALL_KB * 1024, (rid, p.stat().st_size)
def test_each_file_is_a_webp_of_the_recorded_size_and_about_512_on_its_long_side():
    for rid, r in ROWS.items():
        with Image.open(WEB / r["file"]) as im: assert im.format == "WEBP" and im.size == (r["width"], r["height"]) and max(im.size) == 512, rid
def test_no_file_carries_metadata():
    for rid, r in ROWS.items(): assert not {"EXIF", "XMP ", "ICCP"} & set(chunks(WEB / r["file"])), rid
def test_every_id_is_in_the_library():
    ids = {r["id"] for r in R.library()}; assert not set(ROWS) - ids
def test_no_stray_files_either_way():
    assert {p.name for p in FOLDER.iterdir()} == {Path(r["file"]).name for r in ROWS.values()}
def test_a_row_keeps_what_the_run_recorded():
    for rid, r in ROWS.items():
        assert isinstance(r["seed"], int) and r["seconds"] > 0 and r["peak_vram_gib"] > 0 and r["card_peak_vram_gib"] >= r["peak_vram_gib"] and r["peak_scope"] in ("recipe", "card"), rid
        assert r["model"].endswith(".safetensors") and r["prompt"].strip() and re.fullmatch(r"[0-9a-f]{12}", r["run"]) and re.fullmatch(r"\d{4}-\d\d-\d\d", r["rendered"]), rid
def test_data_names_no_private_path_and_nothing_adult():
    t = DATA.read_text(encoding="utf-8"); assert "/" + "home/" not in t and "/" + "mnt/" not in t and not sfw.flagged(t) and not ALSO_ADULT.search(t)
def test_a_rendered_recipe_carries_its_render_and_others_carry_none(client):
    rid = next(iter(ROWS)); assert client.get(f"/api/recipes/{rid}").json()["render"] == ROWS[rid]
    other = next(r["id"] for r in R.library() if r["id"] not in ROWS); assert client.get(f"/api/recipes/{other}").json()["render"] is None
    rows = {r["id"]: r for r in client.get("/api/recipe-library?kind=picture&limit=200").json()["recipes"]}; assert rows and all(r["render"] == ROWS.get(i) for i, r in rows.items())
    d = client.get("/api/recipe-library?limit=1").json(); assert d["rendered"] == len(ROWS) and d["total"] == len(R.library())
def test_a_render_does_not_count_as_tested(client):
    rid = next(iter(ROWS)); d = client.get(f"/api/recipes/{rid}").json(); assert d["tested"] is None and d["status"] == "untested"
def test_the_files_are_served_from_the_web_folder(client):
    rid = next(iter(ROWS)); r = client.get("/" + ROWS[rid]["file"]); assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
def test_the_page_labels_a_render_and_only_shows_one_when_there_is_one():
    js = JS.read_text(); assert '"Our own render"' in js and "r.render ? html`<img" in js and "recipe.proof && !recipe.render" in js and "!run && recipe.render" in js
