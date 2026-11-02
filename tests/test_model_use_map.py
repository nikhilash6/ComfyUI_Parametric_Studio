"""The downloaded-file map, on a tiny fake box. No network and no live ports."""
import importlib.util, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("use_map", ROOT / "scripts" / "build_model_use_map.py"); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def test_yaml_folders_and_reach(tmp_path):
    y = tmp_path / "e.yaml"; y.write_text("lib:\n    base_path: /m/\n    vae: vae\n    loras: |\n        loras\n        _complete_pipelines/X/loras\n")
    f = M.comfy_folders(y)
    assert f == {"vae": "vae", "loras": "loras", "_complete_pipelines/X/loras": "loras"}
    assert M.reach("_complete_pipelines/X/loras/a/b.safetensors", f) == "loras" and M.reach("3d/shap-e/x.bin", f) == ""


def test_status_is_earned():
    assert M.decide({}, False, True, ["g"], "p")[0] == "not_on_disk"
    assert M.decide({}, True, False, ["g"], "rendered x")[0] == "rendered"
    assert M.decide({}, True, False, ["g"], "")[0] == "graph"
    assert M.decide({}, True, True, [], "")[0] == "reachable"
    assert M.decide({}, True, False, [], "")[0] == "unreachable"


def test_a_partial_file_is_not_on_disk(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 10)
    assert M.on_disk(tmp_path, {"rel": "a.bin", "bytes": "100"})[0] is False and M.on_disk(tmp_path, {"rel": "a.bin", "bytes": "10"})[0] is True


def test_card_text_skips_front_matter_and_markup():
    t = "---\nlicense: mit\n---\n# Title\n\n![x](y.png)\n\nThis model turns a single photo into a textured mesh in seconds.\n\nMore."
    assert M.first_paragraph(t).startswith("This model turns")


def test_graph_names_reads_nested_values(tmp_path):
    p = tmp_path / "g.json"; p.write_text(json.dumps({"1": {"inputs": {"unet_name": "3d/a.safetensors", "x": 3, "y": ["1", 0]}}}))
    assert M.graph_names(p) == {"a.safetensors"}


def test_a_generic_file_name_does_not_borrow_another_models_graph():
    assert M.GENERIC.match("diffusion_pytorch_model.safetensors") and M.GENERIC.match("model-00001-of-00003.safetensors") and M.GENERIC.match("denoiser.pt")
    assert not M.GENERIC.match("flux1-dev.safetensors") and not M.GENERIC.match("model_a_v2.safetensors")


def test_a_tool_run_proves_only_what_the_tool_loaded():
    proofs = {"anigen": {"seconds": 191, "sheet": "s"}}
    used = ["tool anigen, 3D page"]
    assert M.tool_proof("x/ckpts/anigen/ss_flow_solo/ckpts/denoiser.pt", used, proofs)
    assert not M.tool_proof("x/ckpts/anigen/ss_flow_duet/ckpts/denoiser.pt", used, proofs)


def test_the_looked_at_ledger_skips_comments(tmp_path):
    p = tmp_path / "l.tsv"; p.write_text("# note\nkrea2_t2i\ton brief\n")
    assert M.load_viewed(str(p)) == {"krea2_t2i": "on brief"} and M.load_viewed(str(tmp_path / "none")) == {}
