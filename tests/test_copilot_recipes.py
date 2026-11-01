"""The recipe library ported from the founders' earlier studio: safe for work, nothing private, honest about proof, and "can run" only from a real check. Fixtures only: no live port, no GPU."""
import hashlib, json, os, re, wave
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import studio.server as S
from studio import loras as L, recipe_check as C, recipes as R, sfw
from studio.goals import values_for, GOALS, WF
from studio.graph_template import fill
from studio.sound import render as SND, synth as SY

ROOT = Path(__file__).resolve().parent.parent
# sha256 prefixes, so the names themselves stay out of the repo
NAMES_THAT_STAY_PRIVATE = {"73423c7707c42ee6", "ef94d492bb48fd31", "e1fc45f7880e0505", "1f437c6739b0dc1c", "fe384adb7e67d54e", "c49b876c05fd3769", "3b630e7964f745a6"}
ALSO_ADULT = re.compile(r"\b(bikini|swimwear|sensual|seductive|boudoir|cleavage|lingerie|schoolgirl|underage)\b", re.I)
def words_of(text): return {hashlib.sha256(w.encode()).hexdigest()[:16] for w in re.findall(r"[a-z]+", text.lower())}
def text_of(obj): return json.dumps(obj, ensure_ascii=False)
def data_files(): return sorted((ROOT / "studio" / "recipe_library").glob("*.json")) + [ROOT / "studio" / "lora_recipes.json"]

# ---------- what is in the data
def test_the_library_is_valid_in_the_apps_own_format():
    rows = R.library(); assert len(rows) > 600 and R.validate({"recipes": rows}) == []
def test_ids_do_not_collide_with_each_other_or_the_flagships():
    ids = [r["id"] for r in R.library()] + [r["id"] for r in R.load()["recipes"]]; assert len(ids) == len(set(ids))
def test_the_flagship_list_stays_as_it_was():
    assert 8 <= len(R.load()["recipes"]) <= 12
@pytest.mark.parametrize("path", data_files(), ids=lambda p: p.name)
def test_data_file_has_nothing_private_or_adult(path):
    t = path.read_text(encoding="utf-8"); assert not sfw.flagged(t.replace("safe-for-work", "")), path; assert not ALSO_ADULT.search(t), ALSO_ADULT.search(t)
    assert not words_of(t) & NAMES_THAT_STAY_PRIVATE
    home = "/" + "home/"; disk = "/" + "mnt/"
    assert home not in t and disk not in t and not re.search(r"\bowner( 20\d\d|'s| said| liked| rule)", t) and not re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", t)
def test_crew_notes_and_guides_name_nothing_private():
    bad = ("Parametric_Studio" + "_to_be_added", "comfy" + "_copilot", "comfy" + "-copilot", "camp" + "-b", "uncensored", "abliterated")
    for p in sorted((ROOT / "studio" / "crew_notes").rglob("*.md")) + sorted((ROOT / "studio" / "processes").glob("*.md")):
        t = p.read_text(encoding="utf-8"); assert not words_of(t) & NAMES_THAT_STAY_PRIVATE, p; assert not [b for b in bad if b in t.lower() or b in t], p
def test_every_row_is_marked_safe_for_work():
    assert all(r["rating"] == "sfw" for r in R.library()) and all(r["rating"] == "sfw" for r in L.curated())
def test_a_real_person_never_appears_in_a_lora_row():
    assert not [r["title"] for r in L.curated() if re.search(r"real[- ]person|likeness|celebrity|actress", text_of(r), re.I)]
def test_proof_is_only_what_was_recorded_and_nothing_claims_tested_here():
    for r in R.library():
        assert not r.get("tested"), r["id"]; assert r["proof"]["level"] in ("verified", "load-tested", "recipe", "warned") and r["proof"]["note"], r["id"]
        v = R.view(r); assert v["status"] == "untested" and v["tested"] is None
    assert all("never" in r["proof"]["note"].lower() or "not" in r["proof"]["note"].lower() for r in R.library() if r["proof"]["level"] == "recipe")
    assert all("earlier studio" in r["proof"]["note"] and "Not re-rendered" in r["proof"]["note"] for r in L.curated() if r["proof"]["level"] == "verified")
def test_the_page_says_a_card_without_a_picture_has_no_render_to_show():
    js = (ROOT / "studio/web/recipes.js").read_text(); assert "Recipe: no render shown" in js and "Verified on the earlier studio" in js and "A card without one has no render to show you yet" in js
def test_every_lora_records_a_licence_and_non_commercial_is_labelled():
    for r in L.curated(): assert r["licence"] and r["licence_class"] in ("open", "community", "unverified", "non-commercial"), r["id"]
    for r in L.curated():
        if "non-commercial" in r["licence"].lower(): assert r["licence_class"] == "non-commercial" and "Non-commercial" in r["licence_note"]
    js = (ROOT / "studio/web/recipes.js").read_text(); assert '"Non-commercial"' in js and '"Licence unverified"' in js
def test_tuned_settings_came_through():
    h = next(r for r in L.curated() if r["path"].endswith("handheld_h3_100.safetensors")); assert h["run"]["strength"] == 1.7 and h["run"]["steps"] == 25 and h["run"]["sampler"] == "euler" and h["run"]["loader"] == "LoraLoaderBypassModelOnly" and h["settings"]["strength_range"] == [1.2, 1.7]
    rec = R.find(h["id"]); assert rec["steps"][0]["lora"] == {"id": h["id"], "strength": "{strength}"} and next(f for f in rec["fields"] if f["key"] == "strength")["default"] == "1.7" and any("25 steps" in t for t in rec["tips"])
def test_a_field_with_choices_defaults_to_one_of_them():
    for r in R.library():
        for f in r.get("fields", []):
            if f.get("options"): assert f["default"] in f["options"], (r["id"], f["key"])
def test_every_blank_in_a_prompt_has_a_field():
    for r in R.library():
        keys = {f["key"] for f in r.get("fields", [])}
        for s in r["steps"]:
            for m in re.findall(r"\{([a-z_][a-z0-9_]*)\}", str(s.get("prompt", "")) + text_of(s.get("lora") or {})): assert m in keys, (r["id"], m)
def test_a_reference_card_says_why_and_cannot_be_started(monkeypatch):
    card = next(r for r in R.library() if r.get("reference")); assert card["why_not"] and card["steps"] == []
    r = TestClient(S.app).post(f"/api/recipes/{card['id']}/run", json={}); assert r.status_code == 400 and card["why_not"][:20] in r.json()["detail"]

# ---------- a LoRA in a graph
def h3_graph(goal="h3_video"):
    body = {"prompt": "a shot", "seed": 1, "options": {"speed": "quality", "aspect": "16:9", "quality": "standard", "seconds": 3}}; vals, _ = values_for(goal, body, "x.png"); return fill(json.load(open(os.path.join(WF, GOALS[goal]["template"]))), vals)
RUN = {"id": "lora_x", "path": "minimax_h3/x.safetensors", "run": {"goal": "h3_video", "base": "base_fl2va.safetensors", "loader": "LoraLoaderBypassModelOnly", "strength": 1.7, "steps": 25, "sampler": "euler", "scheduler": "simple", "megapixels": 0.399, "options": {}}}
@pytest.mark.parametrize("goal", ["h3_video", "h3_animate"])
def test_a_lora_goes_in_right_after_the_model_with_its_tuned_settings(monkeypatch, goal):
    monkeypatch.setattr(L, "by_id", lambda i: RUN if i == "lora_x" else None); g = L.apply_to_graph(h3_graph(goal), {"id": "lora_x", "strength": "1.5"})
    unet = next(k for k, n in g.items() if n["class_type"] == "UNETLoader"); lo = g["lora_recipe"]
    assert g[unet]["inputs"]["unet_name"] == "base_fl2va.safetensors" and lo["class_type"] == "LoraLoaderBypassModelOnly" and lo["inputs"]["model"] == [unet, 0] and lo["inputs"]["lora_name"] == RUN["path"] and lo["inputs"]["strength_model"] == 1.5
    assert [k for k, n in g.items() if k != "lora_recipe" and [unet, 0] in n["inputs"].values()] == []                  # nothing skips the LoRA
    assert next(n for n in g.values() if n["class_type"] == "KSamplerSelect")["inputs"]["sampler_name"] == "euler" and next(n for n in g.values() if n["class_type"] == "ResolutionSelector")["inputs"]["megapixels"] == 0.399
    steps = next(n for n in g.values() if n["class_type"] == "BasicScheduler")["inputs"]["steps"]; assert g[g[steps[0]]["inputs"]["on_false"][0]]["inputs"]["value"] == 25
def test_only_a_curated_runnable_lora_can_be_asked_for(monkeypatch):
    with pytest.raises(HTTPException) as e: L.apply_to_graph(h3_graph(), {"id": "../anything.safetensors"})
    assert e.value.status_code == 400
    monkeypatch.setattr(L, "by_id", lambda i: {**RUN, "run": None})
    with pytest.raises(HTTPException): L.apply_to_graph(h3_graph(), {"id": "lora_x"})
def test_the_graph_route_applies_it_and_refuses_a_stranger(monkeypatch):
    monkeypatch.setattr(S, "comfy", lambda *a, **k: {}); c = TestClient(S.app); rid = next(r["id"] for r in L.curated() if r["run"] and r["run"]["goal"] == "h3_video")
    g = c.post("/api/graph", json={"goal": "h3_video", "prompt": "a fox", "options": {"speed": "quality"}, "lora": {"id": rid}}); assert g.status_code == 200 and "lora_recipe" in g.json()["graph"]
    assert c.post("/api/graph", json={"goal": "h3_video", "prompt": "a fox", "lora": {"id": "nope"}}).status_code == 400
def test_a_step_passes_its_lora_on_with_the_chosen_strength():
    b = R.goal_body({"goal": "h3_video", "prompt": "{scene}", "lora": {"id": "lora_x", "strength": "{strength}"}}, {"scene": "s", "strength": "0.7"}); assert b["lora"] == {"id": "lora_x", "strength": "0.7"} and b["prompt"] == "s"
def test_the_lora_list_is_mounted(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "_get_models_root", lambda: str(tmp_path)); monkeypatch.setitem(L._cache, "data", None); assert TestClient(S.app).get("/api/loras").status_code == 200; L._cache["data"] = None
def test_the_list_shows_curated_files_only_and_counts_the_rest(tmp_path, monkeypatch):
    p = tmp_path / "loras"; p.mkdir(); row = L.curated()[0]; f = p / row["path"]; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(b"x" * 10); (p / "harmless_sounding.safetensors").write_bytes(b"x" * 10)
    monkeypatch.setattr(L, "_get_models_root", lambda: str(tmp_path)); monkeypatch.setitem(L._cache, "data", None); d = TestClient(S.app).get("/api/loras").json(); L._cache["data"] = None
    assert [i["name"] for i in d["items"]] == [row["path"]] and d["other_files"] == 1 and d["items"][0]["licence"] == row["licence"] and d["items"][0]["proof"] == row["proof"]["level"]

# ---------- the check behind "can run"
OI = {"UNETLoader": {"input": {"required": {"unet_name": [["base.safetensors", "gone.safetensors"]], "weight_dtype": [["default"], {"default": "default"}]}}}, "KSamplerSelect": {"input": {"required": {"sampler_name": [["euler"]]}}}, "Math": {"input": {"required": {"expression": ["STRING"], "values": ["AUTOGROW"]}}}, "LoadImage": {"input": {"required": {"image": [["a.png"]]}}}}
FILES = {"base.safetensors": 10 ** 9}
def good(): return {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "base.safetensors"}}, "2": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}, "3": {"class_type": "Math", "inputs": {"expression": "a", "values.a": ["1", 0]}}, "4": {"class_type": "LoadImage", "inputs": {"image": "an_upload.png"}}}
def test_a_good_graph_passes():
    assert C.check_graph(good(), OI, FILES) == []
@pytest.mark.parametrize("change,word", [(("1", "unet_name", "gone.safetensors"), "not on disk"), (("1", "unet_name", "never.safetensors"), "not known"), (("2", "sampler_name", "beta57"), "not one of its choices"), (("3", "values.a", ["9", 0]), "not in the graph")])
def test_the_check_catches_what_comfyui_would_refuse(change, word):
    g = good(); g[change[0]]["inputs"][change[1]] = change[2]; assert word in " ".join(C.check_graph(g, OI, FILES))
def test_the_check_catches_an_unknown_node_and_an_empty_input():
    g = good(); g["5"] = {"class_type": "Nope", "inputs": {}}; del g["2"]["inputs"]["sampler_name"]; p = " ".join(C.check_graph(g, OI, FILES)); assert "Nope is not installed" in p and "sampler_name is empty" in p
def test_a_stub_or_a_dangling_link_is_not_a_model_file(tmp_path):
    (tmp_path / "real.safetensors").write_bytes(b"x" * 5000); (tmp_path / "pointer.safetensors").write_bytes(b"version https://git-lfs"); (tmp_path / "dead.safetensors").symlink_to(tmp_path / "missing"); (tmp_path / "notes.md").write_bytes(b"x" * 5000)
    assert set(C.model_files(str(tmp_path))) == {"real.safetensors"}
def test_nothing_is_claimed_when_comfyui_cannot_be_asked():
    rec = next(r for r in R.library() if r["kind"] == "picture"); st = C.check_recipe(rec, None, {}); assert st["ready"] is None and "not checked" in st["why"]
def test_a_real_library_recipe_is_refused_when_a_model_is_missing():
    C._cache.clear(); rec = next(r for r in R.library() if r["kind"] == "picture"); st = C.check_recipe(rec, {"UNETLoader": {"input": {"required": {"unet_name": [[]]}}}}, {}); assert st["ready"] is False and st["problems"]
def test_a_sound_needs_nothing_but_the_cpu():
    assert C.check_recipe(next(r for r in R.library() if r["kind"] == "sound"), None, {})["ready"] is True

# ---------- the routes
@pytest.fixture
def no_comfy(monkeypatch):
    C._cache.clear(); monkeypatch.setattr(C, "context", lambda: ({}, {})); return TestClient(S.app)
def test_the_library_route_filters_and_pages(no_comfy):
    d = no_comfy.get("/api/recipe-library?kind=sound&limit=5").json(); assert d["total"] == d["counts"]["sound"] and len(d["recipes"]) == 5 and all(r["kind"] == "sound" and r["ready"] is True for r in d["recipes"]) and d["ready"] == d["total"]
    assert no_comfy.get("/api/recipe-library?q=zzzzznothing").json()["total"] == 0
    assert no_comfy.get("/api/recipe-library?kind=picture&ready_only=true").json()["total"] == 0                       # an empty object_info knows no nodes
def test_a_library_recipe_opens_and_a_blocked_one_is_refused_with_the_reason(no_comfy):
    rid = next(r["id"] for r in R.library() if r["kind"] == "picture"); assert no_comfy.get(f"/api/recipes/{rid}").json()["kind"] == "picture"
    r = no_comfy.post(f"/api/recipes/{rid}/run", json={}); assert r.status_code == 409 and "not installed" in r.json()["detail"]
    assert no_comfy.get(f"/api/recipe-ready/{rid}").json()["ready"] is False and no_comfy.get("/api/recipe-ready/nope").status_code == 404
def test_the_recipe_graph_route_finds_library_recipes():
    rid = next(r["id"] for r in R.library() if r["kind"] == "picture"); d = TestClient(S.app).get(f"/api/recipe-graphs/{rid}").json(); assert d["steps"][0]["goal"] == "image" and d["steps"][0]["graph"]

# ---------- sound
SOUNDS = [r for r in R.library() if r["kind"] == "sound"]
def test_every_sound_recipe_names_real_sounds_and_presets():
    assert len(SOUNDS) >= 40
    for r in SOUNDS:
        c = SND.clean(r["steps"][0]["sound"]); assert c["layers"] and all(l["sound"] in SY.KINDS for l in c["layers"]), r["id"]
def test_a_sound_is_repeatable_and_not_silent():
    rec = SOUNDS[0]["steps"][0]["sound"]; a, _ = SND.render(rec); b, _ = SND.render(rec); assert a.size > 1000 and (a == b).all() and abs(a).max() > 0.01
def test_a_layer_with_a_model_is_refused():
    with pytest.raises(SND.SoundError): SND.clean({"layers": [{"engine": "voice", "text": "hi"}]})
def test_the_sound_step_writes_audio_the_chain_can_pass_on(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "_root", lambda: tmp_path); run = {"run": "abc", "steps": []}; st = {}; files = R._cpu(run, st, {"id": "s", "op": "sound", "sound": SOUNDS[0]["steps"][0]["sound"]}, {"out": {}, "values": {}, "seed_add": 0})
    assert files[0]["kind"] == "audio" and files[0]["filename"] == "s.wav"
    with wave.open(files[0]["local"]) as w: assert w.getnframes() > 1000

def test_provenance_records_the_port_and_the_licence():
    t = (ROOT / "PROVENANCE.md").read_text(); assert "studio/recipe_library" in t and "studio/sound" in t and "lora_recipes.json" in t and "AGPL-3.0-or-later" in t
def test_downloaded_lora_rows_are_reference_cards_that_claim_nothing():
    rows = [r for r in L.curated() if r.get("mode") == "reference"]
    assert rows and all(not r["run"] and r["proof"]["level"] == "recipe" and "Never rendered" in r["proof"]["note"] and r["why_not"] for r in rows)
    assert not [r["path"] for r in rows if re.search("faceid|infl8", r["path"], re.I)]
