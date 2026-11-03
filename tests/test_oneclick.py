"""The Edit page's one-click tools (studio/feature_oneclick.py), stubbed: no ComfyUI, no GPU, no live port. ffmpeg is a recorded stub."""
import json, re
from pathlib import Path
import pytest
from fastapi import HTTPException
from studio import feature_oneclick as O, graph_registry as G
from studio.graph_template import placeholders

ROOT = Path(__file__).resolve().parents[1]; WEB = ROOT / "studio" / "web"; WF = ROOT / "workflows"


def graph_of(tid, **b):
    g, v, o, labels, name = O.build(tid, b); return g, v, labels, name


def files_in(g):
    return {x for n in g.values() for k, x in n["inputs"].items() if isinstance(x, str) and k.endswith(("_name", "file")) and x.endswith(".safetensors")}


@pytest.fixture(autouse=True)
def no_probe(monkeypatch):
    monkeypatch.setattr(O, "image_aspect", lambda name: "9:16")
    import studio.goals as goals
    monkeypatch.setattr(goals, "probe_input", lambda name: {"width": 1280, "height": 720, "duration": 5.2})


CASES = [("angles", {"image": "a.png", "options": {"set": s}}) for s in O.ANGLE_SETS] + [("relight", {"image": "a.png", "options": {"light": l}}) for l in O.LIGHTS] + \
        [("effects", {"image": "a.jpg", "options": {"effect": e, "output": out}}) for e in O.EFFECTS for out in ("still", "still + clip")] + [("matte", {"video": "c.mp4", "options": {"seconds": s}}) for s in (2, 5)]


@pytest.mark.parametrize("tid,b", CASES)
def test_every_option_fills_its_graph_completely(tid, b):
    g, v, labels, name = graph_of(tid, **b)
    assert not placeholders(g) and (WF / name).exists()
    assert set(labels) <= set(g), "every labelled output is a node of the graph"
    for nid in labels: assert g[nid]["class_type"] in ("SaveImage", "SaveVideo")


def test_every_graph_is_registered_and_opens_on_the_edit_page():
    files = {p.name for p in WF.glob("oneclick_*.json")}
    assert files == {t["graph"] for t in O.TOOLS.values()} | {t["graph_clip"] for t in O.TOOLS.values() if t.get("graph_clip")}
    rows = {r["id"]: r for r in G.all_rows() if r["kind"] == "workflow"}
    for f in files:
        assert rows[f]["open"] == "edit" and rows[f]["sub"] == "Edit" and rows[f]["call"]["path"].startswith("/api/oneclick/") and rows[f]["call"]["poll"] == "/api/oneclick/jobs/ID"
        assert rows[f]["call"]["path"].split("/")[3] in O.TOOLS


@pytest.mark.parametrize("tid,b", CASES)
def test_every_model_a_graph_loads_is_listed_with_its_licence(tid, b):
    g, v, labels, name = graph_of(tid, **b)
    listed = {m["file"] for m in O.models_of(tid)}
    for f in files_in(g):
        if f.startswith(("qwen_image_vae", "ltx-2.5-video-vae", "ltx-2.5-audio-vae", "ae.", "gemma4", "qwen_3_4b")): continue   # VAEs and encoders ride with their model's entry
        assert f in listed, f
    for m in O.models_of(tid):
        assert m["licence"] and m["url"].startswith("https://") and isinstance(m["limits"], list)


def test_ltx_models_say_their_revenue_cap_where_they_are_picked():
    for tid in ("effects", "matte"):
        caps = [m for m in O.models_of(tid) if m["id"] in ("ltx", "alpha")]
        assert caps and all(m["badge"] == "Revenue cap" for m in caps)
    assert all(not m["limits"] for m in O.models_of("angles") + O.models_of("relight"))


def test_angle_prompts_use_the_lora_cards_grammar():
    for name, shots in O.ANGLE_SETS.items():
        assert len(shots) == 4 and len({s[0] for s in shots}) == 4
        for label, p in shots:
            az = next(a for a in sorted(O.AZIMUTHS, key=len, reverse=True) if p.startswith(a)); rest = p[len(az) + 1:]
            el = next(e for e in O.ELEVATIONS if rest.startswith(e)); assert rest[len(el) + 1:] in O.DISTANCES
    g, v, labels, _ = graph_of("angles", image="a.png", options={"set": "turnaround"})
    assert [g[f"pos{i}"]["inputs"]["prompt"] for i in range(1, 5)] == ["<sks> " + s[1] for s in O.ANGLE_SETS["turnaround"]]
    assert list(labels.values()) == [s[0] for s in O.ANGLE_SETS["turnaround"]]
    assert g["look"]["inputs"]["lora_name"] == "qwen-image-edit-2511-multiple-angles-lora.safetensors" and 0.8 <= g["look"]["inputs"]["strength_model"] <= 1.0
    assert g["ks1"]["inputs"]["steps"] == 4 and g["ks1"]["inputs"]["cfg"] == 1.0 and g["fast"]["inputs"]["lora_name"].startswith("Qwen-Image-Edit-2511-Lightning-4steps")


def test_relight_uses_the_trigger_word_and_keeps_the_people():
    g, v, labels, _ = graph_of("relight", image="a.png", options={"light": "neon night"})
    p = g["pos1"]["inputs"]["prompt"]
    assert p.startswith("重新照明") and "neon" in p and "Keep the people" in p and g["look"]["inputs"]["lora_name"] == "Qwen-Image-Edit-2509-Relight.safetensors"
    assert g["unet"]["inputs"]["unet_name"] == "qwen_image_edit_2509_int8_convrot.safetensors"
    g, *_ = graph_of("relight", image="a.png", text={"direction": "cold blue moonlight from above"})
    assert "cold blue moonlight" in g["pos1"]["inputs"]["prompt"]


def test_effects_inflate_uses_the_lora_and_statues_do_not():
    g, v, labels, name = graph_of("effects", image="a.png", options={"effect": "inflate"}, text={"subject": "woman's coat"})
    assert g["look"]["inputs"]["strength_model"] == 1.0 and g["pos1"]["inputs"]["prompt"] == "Inflate the woman's coat." and name == "oneclick_effect_api.json" and list(labels) == ["save1"]
    g, *_ = graph_of("effects", image="a.png", options={"effect": "gold statue"})
    assert g["look"]["inputs"]["strength_model"] == 0.0 and "gold statue" in g["pos1"]["inputs"]["prompt"] and "the person" in g["pos1"]["inputs"]["prompt"]


def test_effects_clip_runs_ltx_from_the_photo_to_the_edit():
    g, v, labels, name = graph_of("effects", image="a.png", options={"effect": "inflate", "output": "still + clip", "seconds": 4})
    assert name == "oneclick_effect_clip_api.json" and list(labels) == ["save1", "l_save"]
    assert (v["width"], v["height"]) == O.LTX_SIZES["9:16"] and v["frames"] == 97 and (v["frames"] - 1) % 8 == 0
    assert g["first"]["inputs"]["image"] == ["src", 0] and g["unload"]["inputs"]["image_pass"] == ["dec1", 0]
    assert g["l_i2v"]["inputs"]["image"] == ["first_p", 0] and g["l_i2v"]["inputs"]["strength"] == 1.0 and "g_first" not in g, "a guide on both ends dissolved; the photo starts in place"
    assert g["g_last"]["inputs"]["latent"] == ["l_i2v", 0] and g["g_last"]["inputs"]["frame_idx"] == -1 and g["l_crop"]["inputs"]["latent"] == ["l_sep", 0]
    assert g["unload"]["class_type"] == "VRAM_Debug" and g["unload"]["inputs"]["unload_all_models"] is True and g["last"]["inputs"]["image"] == ["unload", 1], "Qwen leaves the card before LTX loads"
    assert "no fades" in g["l_pos"]["inputs"]["text"] and "second by second" in g["l_pos"]["inputs"]["text"]


def test_matte_is_the_vfx_matte_pass_with_a_new_set():
    g, v, labels, _ = graph_of("matte", video="c.mp4", options={"seconds": 5}, text={"background": "a rooftop garden at dusk"})
    vfx = json.loads((WF / "ltx25_vfx_api.json").read_text())
    for k in ("guide", "guider", "sig", "samp", "crop", "dec"): assert g[k]["class_type"] == vfx[k]["class_type"]
    assert g["lora"]["inputs"]["lora_name"] == "ltx-2.5-22b-ic-lora-alpha-gen-0.9.safetensors" and g["alpha"]["inputs"]["image"] == ["dec", 0]
    assert g["over"]["inputs"]["mask"] == ["alpha", 0] and g["bg"]["inputs"]["amount"] == v["frames"] and "rooftop garden" in g["z_pos"]["inputs"]["text"]
    assert v["frames"] == 121 and (v["width"], v["height"]) == O.LTX_SIZES["16:9"]
    assert list(labels.values()) == ["On the new set", "The new set", "Matte", "Plate"]


def test_matte_never_asks_for_more_frames_than_the_clip_has(monkeypatch):
    import studio.goals as goals
    monkeypatch.setattr(goals, "probe_input", lambda name: {"width": 720, "height": 1280, "duration": 2.0})
    _, v, *_ = graph_of("matte", video="c.mp4", options={"seconds": 5})
    assert v["frames"] <= 48 and (v["frames"] - 1) % 8 == 0 and (v["width"], v["height"]) == O.LTX_SIZES["9:16"]


@pytest.mark.parametrize("tid,b", [("angles", {}), ("angles", {"image": "../etc/x.png"}), ("relight", {"image": "a.gif"}), ("matte", {"video": "a.png"}), ("effects", {"image": "a.png", "seed": "x"})])
def test_bad_inputs_are_refused(tid, b):
    with pytest.raises(HTTPException) as e: O.build(tid, b)
    assert e.value.status_code == 400


@pytest.mark.parametrize("words", ["a nude statue", "a deepfake of her"])
def test_words_are_checked(words):
    with pytest.raises(HTTPException) as e: O.build("effects", {"image": "a.png", "text": {"subject": words}})
    assert e.value.status_code == 400


def test_run_and_job_with_comfyui_stubbed(monkeypatch):
    sent = {}
    def comfy(path, payload=None, timeout=30):
        if path == "/object_info": return {}
        if path == "/prompt": sent["g"] = payload["prompt"]; return {"prompt_id": "j1", "node_errors": {}}
        if path.startswith("/history/"):
            return {"j1": {"status": {"completed": True, "status_str": "success"}, "outputs": {f"save{i}": {"images": [{"filename": f"angle{i}_00001_.png", "subfolder": "oneclick_angles", "type": "output"}]} for i in (2, 1, 3, 4)} | {"prev": {"images": [{"filename": "x.png", "type": "temp"}]}}}}
        raise AssertionError(path)
    monkeypatch.setattr(O, "_comfy", comfy)
    r = O.oneclick_run("angles", {"image": "a.png", "seed": 7})
    assert r == {"job": "j1", "seed": 7, "options": {"set": "coverage", "strength": "standard"}} and sent["g"]["ks1"]["inputs"]["seed"] == 7
    d = O.oneclick_job("j1")
    assert d["status"] == "done" and [f["label"] for f in d["files"]] == [s[0] for s in O.ANGLE_SETS["coverage"]] and all(f["url"].startswith("/api/view?") for f in d["files"])
    assert d["workflow"] == "oneclick_angles_api.json" and "Multiple-Angles LoRA for 2511 (fal)" in d["models"]


def test_alpha_files_merge_plate_and_matte_with_ffmpeg(tmp_path):
    (tmp_path / "oneclick_matte").mkdir()
    for n in ("plate_00001_.mp4", "matte_00001_.mp4"): (tmp_path / "oneclick_matte" / n).write_bytes(b"x")
    files = [{"node": "save_plate", "filename": "plate_00001_.mp4", "subfolder": "oneclick_matte"}, {"node": "save_matte", "filename": "matte_00001_.mp4", "subfolder": "oneclick_matte"}]
    calls = []
    class R: returncode, stderr = 0, ""
    out, note = O.alpha_files(files, out_dir=tmp_path, run=lambda a, **k: calls.append(a) or R())
    assert note == "" and [f["filename"] for f in out] == ["alpha_00001_.mov", "alpha_00001_.webm"] and all(f["alpha"] for f in out)
    mov, webm = calls
    assert "prores_ks" in mov and "4444" in mov and "alphamerge" in mov[mov.index("-filter_complex") + 1] and "yuva444p10le" in mov[mov.index("-filter_complex") + 1]
    assert "libvpx-vp9" in webm and "yuva420p" in webm[webm.index("-filter_complex") + 1]
    assert O.alpha_files(files[:1], out_dir=tmp_path)[0] == []
    assert "another machine" in O.alpha_files([{**f, "subfolder": "gone"} for f in files], out_dir=tmp_path)[1]


def open_components(js):
    """How many <${Component} ...> tags are not self-closed, skipping ${...} expressions inside the tag (an arrow function's => is not the tag's end)."""
    n = 0
    for m in re.finditer(r"<\$\{\w+\}", js):
        i, depth = m.end(), 0
        while i < len(js):
            c = js[i]
            if js.startswith("${", i): depth += 1; i += 2; continue
            if c == "{" and depth: depth += 1
            elif c == "}" and depth: depth -= 1
            elif c == ">" and not depth: n += js[i - 1] != "/"; break
            i += 1
    return n


def test_the_page_closes_every_component_and_sits_on_the_edit_page():
    js = (WEB / "oneclick.js").read_text(encoding="utf-8"); app = (WEB / "app.js").read_text(encoding="utf-8")
    assert open_components(js) == js.count("<//>")
    assert 'import { OneClick } from "./oneclick.js"' in app and 'k: "oneclick"' in app and "<${OneClick}/>" in app
    assert "Our own render" in js and "licence" in js and (WEB / "oneclick.css").exists()


def test_examples_are_our_own_renders_and_exist():
    ex = O.examples()
    for tid, e in ex.items():
        assert tid in O.TOOLS and e["items"] and e.get("seconds") and e.get("peak_vram_gib") and e["note"]
        for x in [e.get("source"), *(i["src"] for i in e["items"])]:
            if x: assert (WEB / x).exists(), x


def test_routes_answer_on_the_app():
    from fastapi.testclient import TestClient
    from studio import server as S
    c = TestClient(S.app)
    tools = c.get("/api/oneclick").json()["tools"]
    assert [t["id"] for t in tools] == list(O.TOOLS) and all(t["models"] and t["graphs"] for t in tools)
    r = c.post("/api/oneclick/angles/graph", json={"image": "a.png", "seed": 3}).json()
    assert r["workflow"] == "workflows/oneclick_angles_api.json" and r["graph"]["ks4"]["inputs"]["seed"] == 3
    assert c.post("/api/oneclick/nope/run", json={}).status_code == 404 and c.get("/api/oneclick/jobs/unknown").status_code == 404
