"""LTX Finish: graphs, sizes, prompts, what the page offers, the job runner with a fake ComfyUI, and the HDR master checks on tiny clips ffmpeg makes here. No live ports, no GPU."""
import gzip, json, shutil, subprocess
from pathlib import Path
import numpy as np
import pytest
from fastapi import HTTPException
from studio import feature_finish as F, finish_measure as M, graph_audit as GA

REPO = Path(__file__).resolve().parents[1]
SNAP = json.load(gzip.open(REPO / "tests" / "fixtures" / "graph_audit_object_info.json.gz", "rt", encoding="utf-8"))
INFO = {"width": 960, "height": 544, "seconds": 4.042}
ALL = {F.EFFECTS[k]["lora"] for k in F.EFFECTS} | {F.EFFECTS["hdr"]["embedding"]}
needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def test_page_is_a_self_registering_feature_page():
    assert F.PAGE["tab"] == "finish" and F.PAGE["module"] == "finish.js" and F.PAGE["export"] == "Finish" and F.PAGE["css"] == "finish.css"
    js = (REPO / "studio" / "web" / "finish.js").read_text()
    assert "export function Finish" in js and "AI-generated" in js and "</${" not in js
    assert (REPO / "studio" / "web" / "finish.css").exists() and F.router.prefix == "/api/finish"


@pytest.mark.parametrize("effect", list(F.EFFECTS))
def test_every_effect_graph_passes_the_static_check(effect):
    g = F.graph(effect, F.values(effect, INFO, video="clip.mp4", stem="t"))
    assert GA.check(g, SNAP["main"], files=None, model_opts=False) == []


def test_graphs_have_no_unfilled_placeholders_and_no_partner_nodes():
    from studio.graph_template import placeholders
    for e in F.EFFECTS:
        g = F.graph(e, F.values(e, INFO, video="clip.mp4", stem="t"))
        assert not placeholders(g)
        assert not any("Api" in n["class_type"] or n["class_type"].startswith(("Kling", "Runway", "Luma", "OpenAI")) for n in g.values())


def test_lengths_are_8k_plus_1_and_never_longer_than_the_clip():
    assert F.ltx_frames(4, 4.042) == 97 and F.ltx_frames(5, 4.042) == 97 and F.ltx_frames(2) == 49
    for s in (2, 3, 4, 5): assert (F.ltx_frames(s, 10) - 1) % 8 == 0


def test_canvas_keeps_the_shape_and_multiples_of_32():
    assert F.canvas(960, 544, 960) == (960, 544)
    w, h = F.canvas(1920, 1080, 960); assert (w, h) == (960, 544) and w % 32 == 0 and h % 32 == 0
    w, h = F.canvas(1080, 1920, 960); assert h == 960 and w % 32 == 0


def test_upscale_is_exactly_twice_the_guide():
    v = F.values("upscale", {"width": 480, "height": 272, "seconds": 4.04})
    assert (v["width"], v["height"]) == (960, 512) and (v["guide_width"], v["guide_height"]) == (480, 256)     # latent 30x16 divides by the LoRA's factor 2
    v = F.values("upscale", {"width": 1280, "height": 720, "seconds": 4})
    assert v["width"] == 2 * v["guide_width"] and v["height"] == 2 * v["guide_height"] and v["width"] % 64 == 0 and v["height"] % 64 == 0 and v["width"] <= 1920


def test_prompts_follow_each_cards_convention():
    assert F.prompt_for("deblur", "a street").startswith("Reference shows a street, heavily out of focus") and "DEBLUR a street." in F.prompt_for("deblur", "a street")
    assert "ENHANCE QUALITY a street." in F.prompt_for("decompress", "a street")
    c = F.prompt_for("colorize", "a jungle", "green leaves")
    assert "Edited shows the same scene with natural colors restored" in c and "COLORIZE green leaves." in c
    assert F.prompt_for("restore", "") == F.SCENE_DEFAULT


def test_hdr_runs_from_the_scene_embedding_and_writes_three_masters():
    v = F.values("hdr", INFO, stem="s"); g = F.graph("hdr", v)
    assert v["scene_embedding"] == F.EFFECTS["hdr"]["embedding"] and "prompt" not in v
    kinds = {n["class_type"]: n["inputs"] for n in g.values()}
    assert kinds["LTXVHDRDecodePostprocess"]["save_exr"] is True and kinds["LTXVHDRDecodePostprocess"]["half_precision"] is True and kinds["LTXVHDRDecodePostprocess"]["exr_color_space"] == "acescg"
    hlg = [n for n in g.values() if n["class_type"] == "CreateVideo" and n["inputs"].get("color_space") == "HDR"]
    assert hlg and hlg[0]["inputs"]["bit_depth"] == 10
    assert g["idt"]["inputs"]["destination"] == "HDR ACEScct" and g["png16"]["inputs"]["format.bit_depth"] == "16-bit"


def test_missing_reads_comfyuis_own_menu():
    assert F.missing("deblur", ALL) == []
    assert F.missing("deblur", {Path(x).name for x in ALL}) == []          # a flat library also counts
    assert F.missing("hdr", ALL - {F.EFFECTS["hdr"]["embedding"]}) == [F.EFFECTS["hdr"]["embedding"]]


def test_only_proven_effects_with_files_are_offered(monkeypatch):
    monkeypatch.setattr(F, "proof", lambda: {"effects": {"deblur": {"peak_vram_gib": 39}}})
    rows = {r["id"]: r for r in F.listing(ALL)}
    assert rows["deblur"]["offered"] and not rows["restore"]["offered"] and rows["restore"]["ready"]
    rows = {r["id"]: r for r in F.listing(set())}
    assert not any(r["offered"] or r["comfy_up"] for r in rows.values())


def test_options_are_checked():
    o = F.options({"effect": "deblur", "scene": " a  street ", "seconds": 3})
    assert o["scene"] == "a street" and o["seconds"] == 3 and o["seed"] == 42
    for bad in ({"effect": "nope"}, {"effect": "deblur", "seconds": 9}, {"effect": "deblur", "quality": "8k"}):
        with pytest.raises(HTTPException): F.options(bad)
    assert len(F.options({"effect": "restore", "scene": "x" * 2000})["scene"]) == 400
    assert F.values("deblur", INFO, strength=5)["strength"] == 1.2


def test_run_refuses_an_effect_without_a_proof(monkeypatch, tmp_path):
    clip = tmp_path / "c.mp4"; clip.write_bytes(b"x")
    monkeypatch.setattr(F, "clip_path", lambda it: clip)
    monkeypatch.setattr(F, "listing", lambda menu=None: [{"id": k, "label": e["label"], "comfy_up": True, "missing": [], "proven": False} for k, e in F.EFFECTS.items()])
    with pytest.raises(HTTPException) as e: F.run_post({"effect": "restore", "clip": {"filename": "c.mp4"}})
    assert e.value.status_code == 409 and "no proof" in e.value.detail


class FakeComfy:
    url = "http://127.0.0.1:1"
    def __init__(self): self.graphs = []
    def upload(self, p): return Path(p).name
    def run(self, g, timeout=3600, tick=None):
        self.graphs.append(g); return {"outputs": {"save": {"images": [{"filename": "ltxfin_00001.mp4", "subfolder": "finish", "type": "output"}]}}}


def test_run_job_fills_the_record(tmp_path):
    c = FakeComfy(); rec = {"job": "fin-abc123", "clip_info": INFO}
    F.run_job(rec, tmp_path / "c.mp4", F.options({"effect": "decompress", "scene": "a greenhouse"}), c)
    assert rec["status"] == "done" and rec["ai_generated"] and rec["files"]["video"]["url"].startswith("/api/view?")
    g = c.graphs[0]; assert g["lora"]["inputs"]["lora_name"] == F.EFFECTS["decompress"]["lora"] and "ENHANCE QUALITY a greenhouse." in g["pos"]["inputs"]["text"]
    assert g["save"]["inputs"]["filename_prefix"].startswith("finish/decompress_")


def test_run_job_reports_comfyuis_words(tmp_path):
    class Broken(FakeComfy):
        def run(self, g, timeout=3600, tick=None): raise RuntimeError("ComfyUI stopped: out of memory")
    rec = {"job": "fin-x", "clip_info": INFO}; F.run_job(rec, tmp_path / "c.mp4", F.options({"effect": "deblur"}), Broken())
    assert rec["status"] == "error" and "out of memory" in rec["error"]


def test_vram_check_reads_the_card_only_for_a_local_comfyui():
    class Far: url = "http://192.0.2.4:8188"
    assert F.vram_problem("hdr", Far()) == ""
    assert "only 10.0 GB" in F.vram_problem("hdr", FakeComfy(), free=lambda: 10.0)
    assert F.vram_problem("deblur", FakeComfy(), free=lambda: 90.0) == ""


# ---------- measurements on tiny clips made here
def _clip(path, vf="testsrc2=size=128x96:rate=24", frames=17, extra=()):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", vf, "-frames:v", str(frames), *extra, "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


@needs_ffmpeg
def test_psnr_and_ssim_see_damage_and_identity(tmp_path):
    a = _clip(tmp_path / "a.mp4"); b = _clip(tmp_path / "b.mp4", extra=("-vf", "gblur=sigma=3"))
    same = M.psnr_ssim(a, a); worse = M.psnr_ssim(b, a)
    assert same["ssim"] == 1.0 and worse["ssim"] < 0.99 and worse["psnr_db"] < 40 and worse["frames"] == 17
    rep = M.fidelity_report(b, a, a); assert rep["ssim_gain"] > 0 and "ssim" in rep["better_on"]


@needs_ffmpeg
def test_colour_report_tells_grey_from_colour(tmp_path):
    a = _clip(tmp_path / "a.mp4"); g = _clip(tmp_path / "g.mp4", extra=("-vf", "hue=s=0"))
    r = M.colour_report(g, a, a, every=4)
    assert r["chroma_above_grey"] and r["closer_to_original"] and r["mean_chroma"]["grey"] < 1 and r["delta_e2000_vs_original"]["after"] < 0.5


@needs_ffmpeg
def test_prores_master_from_16_bit_frames_is_tagged_hlg(tmp_path):
    d = tmp_path / "png"; d.mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=24", "-frames:v", "9", "-pix_fmt", "rgb48be", str(d / "f_%05d_.png")], check=True)
    out = M.prores_from_png16(d, tmp_path / "m.mov"); t = M.colour_tags(out)
    assert t["codec_name"] == "prores" and t["profile"].startswith("4444") and M.is_hlg_10bit(t)


def test_hlg_check_needs_all_three_tags():
    assert M.is_hlg_10bit({"color_primaries": "bt2020", "color_transfer": "arib-std-b67", "bits": 10})
    assert not M.is_hlg_10bit({"color_primaries": "bt2020", "color_transfer": "arib-std-b67", "bits": 8})
    assert not M.is_hlg_10bit({"color_primaries": "bt709", "color_transfer": "arib-std-b67", "bits": 10})


def test_exr_report_reads_half_floats_and_peaks(tmp_path):
    OpenEXR = pytest.importorskip("OpenEXR")
    px = np.full((8, 8, 3), 0.5, np.float16); px[0, 0] = 4.0
    with OpenEXR.File({"compression": OpenEXR.ZIP_COMPRESSION, "type": OpenEXR.scanlineimage}, {"RGB": px}) as f: f.write(str(tmp_path / "frame_00000.exr"))
    r = M.exr_report(tmp_path)
    assert r["frames"] == 1 and r["half_float"] and r["above_1"] and r["peak_channel"] == 4.0 and 0 < r["pixels_above_1_pct"] < 5


def test_proof_file_when_present_only_lists_measured_ai_marked_effects():
    p = F.proof()
    for k, e in (p.get("effects") or {}).items():
        assert k in F.EFFECTS and e["ai_generated"] is True and e["measured"] and e["looked"] and (REPO / "studio" / "web" / e["src"]).exists()
