"""What counts as a family's render, and the file format. No live ports."""
import importlib.util, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("rec", ROOT / "scripts" / "record_family_renders.py"); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
JOB = {"template": "t1", "status": "done", "seed": 7, "prompt": "a lighthouse", "graph": {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "sub/m.safetensors"}}}}


def row(**k): return {"slug": "f", "level": "nodes", "media": [], "test": {"nodes": 1}, **k}


def test_the_file_format_round_trips_byte_for_byte():
    t = (ROOT / "studio" / "family_status.json").read_text(encoding="utf-8")
    assert R.dump(json.loads(t)) == t


def test_a_real_render_raises_the_level_and_carries_model_and_seed(tmp_path):
    f = tmp_path / "o.png"; f.write_bytes(b"x")
    r = row(); said = R.apply_family("F", r, {"tries": [{"template": "t1", "status": "done", "files": [str(f)], "wall_s": 5}]}, {"t1": JOB}, web=tmp_path, copy=lambda s, b: {"kind": "image", "src": f"families/{b.name}.webp"})
    assert r["level"] == "render" and r["media"][0]["model"] == "m.safetensors" and r["media"][0]["seed"] == 7 and said


def test_another_familys_model_proves_nothing():
    rec = {"tries": [{"template": "video_wan2_2_5B_ti2v", "status": "done", "files": ["x.mp4"]}]}
    assert R.proven("Matrix-3D", rec, {}) == [] and R.proven("Wan2.2", rec, {})


def test_a_safety_card_and_an_echoed_upload_are_not_renders():
    assert R.proven("Ideogram4", {"tries": [{"template": "ideogram4_json_t2i", "status": "done", "files": ["a.png"]}]}, {}) == []
    assert R.proven("sam3", {"tries": [{"template": "v", "status": "done", "files": ["sam3_studio_876.mp4"]}]}, {}) == []


def test_a_failed_try_changes_nothing(tmp_path):
    r = row(); assert R.apply_family("F", r, {"tries": [{"template": "t1", "status": "error", "files": []}]}, {}, web=tmp_path) == [] and r["level"] == "nodes"


def test_demote_keeps_only_the_library_sample():
    r = row(level="render", media=[{"own": True, "tpl": "w"}, {"library": True}]); R.demote(r, "why")
    assert r["level"] == "nodes" and r["media"] == [{"library": True}] and r["test"]["note"] == "why"
