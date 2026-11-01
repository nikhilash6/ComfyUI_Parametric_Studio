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

# ---------- recipes rewritten so the model is never asked to draw lettering it can't spell
ASKS_FOR_TEXT = re.compile(r"\b(words?|text|letter\w*|lettered|hand-lettered|spelling|reading|logos?|labels?|labelled|captions?|handwritten\w*|typefaces?|typographic|calligraph\w*|tags?|posters?|symbols?|speech bubbles?|masthead|headline|monogram|denomination|postmark|notes)\b", re.I)
SAYS_BLANK = re.compile(r"\b(blank|plain|unlabelled|wordless|empty)\b", re.I)
TEXT_FREE = ["pic_inf_social_carousel", "pic_inf_social_short_video_cover", "pic_inf_fit_boxing", "pic_inf_car_driver_seat", "pic_inf_life_festival", "pic_inf_travel_airport", "pic_inf_prod_fashion_try", "pic_art_con_scifi_vehicle", "pic_art_street_neon_alley", "pic_art_city_oil_night", "pic_art_city_ink_sketch", "pic_art_comic_manga_page", "pic_art_comic_indie", "pic_art_cyber_street", "pic_art_photo_instant_snapshot", "pic_art_edit_surreal_collage", "pic_art_gd_magazine_cover", "pic_art_gd_logo_mockup", "pic_art_gd_postage_stamp", "pic_art_map_fantasy", "pic_art_map_metro", "pic_art_con_fantasy_hero_gear", "pic_art_con_character_sheet", "pic_art_draw_sketchbook_page", "pic_art_still_trompe", "pic_art_street_stencil", "pic_art_street_sticker_wall", "pic_art_street_wildstyle", "pic_art_kids_map_adventure", "pic_art_sci_anatomy_plate", "pic_art_type_chalk_lettering", "pic_art_type_graffiti_lettering", "pic_art_type_sign_painting", "pic_art_type_swiss_poster", "pic_art_type_neon_sign", "pic_art_type_brush_calligraphy", "pic_art_type_ornamental_monogram", "pic_art_comic_golden_age", "pic_art_con_prop_design", "pic_art_map_infographic_icons", "pic_art_kids_watercolour_story", "pic_art_y2k", "vid_product_hero_10", "lora_7149bee562"]
def visual_part(prompt): return prompt.split("overall_soundscape")[0]
def filled(rid):
    r = R.find(rid); vals = R.field_defaults(r)
    return [visual_part(R._fill(s["prompt"], vals)) for s in r["steps"] if s.get("prompt")]
@pytest.mark.parametrize("rid", TEXT_FREE)
def test_a_rewritten_recipe_asks_for_no_text_and_says_so(rid):
    ps = filled(rid); assert ps, rid
    for p in ps: assert not ASKS_FOR_TEXT.search(p), (rid, ASKS_FOR_TEXT.search(p).group(0), p)
    assert SAYS_BLANK.search(" ".join(ps)), rid
def test_every_product_shot_says_the_product_is_blank():
    for r in R.library():
        for s in r["steps"]:
            if r["id"].startswith("vid_") and "{product}" in str(s.get("prompt", "")): assert "plain and unlabelled" in s["prompt"] and "the {product}" not in s["prompt"], (r["id"], s["id"])
def test_rewritten_stylizers_ask_for_blank_and_unbranded():
    for rid, word in (("style_ukiyo_e", "no inscription"), ("style_cyberpunk", "blank"), ("style_toy_bricks", "unbranded"), ("style_ink_wash", "blank")):
        assert word in json.dumps(R.find(rid)["steps"]), rid
def test_a_recipe_about_lettering_says_it_leaves_that_to_you():
    assert all(R.find(i).get("text_note") for i in ("pic_inf_social_carousel", "pic_art_type_chalk_lettering", "pic_art_type_gothic_blackletter")) and "text_note" in JS.read_text()
