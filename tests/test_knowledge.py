"""psn.knowledge answers from data, with evidence, and says so when the data is not there. No model, server or network here."""
import json, os, re, socket, sys
from pathlib import Path
import pytest
from psn import knowledge as K

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import eval_qwen_agents as EV


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k): raise AssertionError("a knowledge lookup tried to reach the network")
    monkeypatch.setattr(socket, "create_connection", refuse); monkeypatch.setattr(socket.socket, "connect", refuse)


@pytest.fixture
def data(tmp_path, monkeypatch):
    worker, library = EV.prepare_fixture(tmp_path); monkeypatch.setenv("PSN_KNOWLEDGE_WORKER", worker); monkeypatch.setenv("PSN_KNOWLEDGE_LIBRARY", library); K._json_cached.cache_clear(); K._tsv_cached.cache_clear(); return worker, library


@pytest.fixture
def no_data(monkeypatch):
    monkeypatch.setenv("PSN_SETTINGS", os.devnull); monkeypatch.delenv("PSN_KNOWLEDGE_WORKER", raising=False); monkeypatch.delenv("PSN_KNOWLEDGE_LIBRARY", raising=False)


def line_holds(evidence, text):
    path, line = evidence.rsplit(":", 1); path = path if os.path.isabs(path) else str(ROOT / path)
    with open(path, encoding="utf-8") as f: return text in f.read().splitlines()[int(line) - 1]


def test_sampling_keeps_the_label_and_cites_real_code():
    r = K.sampling("ddim alias")
    assert r["rows"][0]["id"] == "core-ddim-alias" and r["rows"][0]["label"] == "from code" and r["rows"][0]["in_core"] is True
    assert r["rows"][0]["code"] and r["rows"][0]["evidence"] == "studio/sampling_lab/atlas.json#core-ddim-alias"


def test_sampling_quote_text_holds_the_entry_prose():
    assert "does essentially nothing" in K.atlas_entry_text(K.sampling_entry("gigachad-cfg-rescale-noop"))


def test_sampling_finds_nothing_rather_than_guessing():
    assert K.sampling("zorblax")["total"] == 0


def test_lessons_count_and_marks_match_the_files():
    ls = K.lessons(); assert len(ls) == 162
    assert all(c["second_read"] in ("checked", "pending") for c in ls.values()) and ls["CU-230"]["second_read"] == "checked"


def test_lesson_evidence_points_at_the_matching_line():
    row = K.lesson_search("quantization")["rows"][0]; assert row["code"] == "CU-211"
    assert line_holds(row["evidence"], row["line"][:40])


def test_recipe_rows_tell_a_stored_render_from_a_port():
    rows = {r["id"]: r for r in K.recipe("loop", limit=100)["rows"]}
    unrendered = [r for r in rows.values() if not r["rendered"]]
    assert rows["loop_breathing"]["rendered"] is True and rows["loop_breathing"]["seconds"] > 0 and all(not r.get("seconds") for r in unrendered)
    assert line_holds(rows["loop_breathing"]["evidence"], "loop_breathing")


def test_process_row_has_a_guide_on_disk():
    r = K.process("trellis")["rows"][0]; assert r["id"] == "3d-trellis-hunyuan" and (ROOT / r["guide"]).is_file() and line_holds(r["evidence"], r["id"])


def test_public_rows_name_no_folder_of_this_machine():
    for r in K.sampling("ddim")["rows"] + K.lesson_search("clip")["rows"] + K.recipe("loop")["rows"] + K.process("3d")["rows"]:
        assert not os.path.isabs(r["evidence"]) and str(ROOT) not in json.dumps(r)


def test_missing_private_data_says_so(no_data):
    for r in (K.pack("x"), K.model("x"), K.psn_node("x"), K.copilot("x"), K.node_purpose("x")):
        assert r["rows"] == [] and "not available" in r["missing"]
    assert "not available" in K.licence_read("x")["missing"]


def test_pack_row_has_evidence_and_the_do_not_install_entry(data):
    rows = {r["pack"]: r for r in K.pack("interpolation")["rows"]}
    assert rows["acme__Bad-Pack"]["do_not_install"]["category"] == "encrypted payload" and rows["acme__Bad-Pack"]["risk"]["flags"]["payload"] == "loader.py:1"
    assert line_holds(rows["acme__Good-Pack"]["evidence"], "acme__Good-Pack") and rows["acme__Good-Pack"]["risk"]["flags"] == {}
    assert rows["acme__Copy-Pack"]["fam_original"] == "acme__Good-Pack"


def test_licence_read_finds_restrictive_wording_the_index_missed(data):
    r = K.licence_read("acme__Trick-Licence"); assert r["index_licence"] == "MIT" and "commercial" in r["files"][0]["restrictive_wording"].lower()
    assert K.licence_read("acme__Good-Pack")["files"][0]["restrictive_wording"] == "" and K.licence_read("acme__No-Licence")["files"] == []


def test_licence_read_cannot_leave_the_library(data):
    assert K.licence_read("../..")["missing"] and K.licence_read("/etc")["missing"]


def test_model_row_says_what_ran(data):
    r = K.model("fake")["rows"]; assert r[0]["file"] == "fake_image_model.safetensors" and r[0]["status"] == "rendered" and line_holds(r[0]["evidence"], "fake_image_model")


def test_psn_node_label(data):
    assert K.psn_node("Hollow")["rows"][0]["label"] == "hollow"


def test_node_io_reads_real_inputs_from_the_snapshot():
    r = K.node_io("KSampler")["rows"]; k = next(x for x in r if x["class"] == "KSampler")
    assert k["required"]["model"]["type"] == "MODEL" and k["required"]["sampler_name"]["type"] == "COMBO" and "euler" in k["required"]["sampler_name"]["choices"] and k["outputs"][0][1] == "LATENT"


def test_grep_docs_cites_file_and_line_and_refuses_an_unknown_scope():
    r = K.grep_docs("guidance scale", "crew")["rows"]; assert r and line_holds(r[0]["evidence"], r[0]["text"][:30])
    assert "unknown" in K.grep_docs("x", "nope")["missing"]


def test_pipelines_count_real_weights_only(tmp_path):
    d = tmp_path / "Fam" / "unet"; d.mkdir(parents=True); (d / "real.safetensors").write_bytes(b"0" * 5000); (d / "stub.safetensors").write_bytes(b"0"); (d / "real.safetensors.sha256-ok").write_text("x")
    assert K.pipelines(str(tmp_path)) == {"Fam": {"files": 1, "gb": 0.0}}


def test_command_line_prints_evidence(capsys):
    assert K.main(["sampling", "ddim", "alias", "--max", "1"]) == 0
    assert "studio/sampling_lab/atlas.json#core-ddim-alias" in capsys.readouterr().out


def test_command_line_says_when_data_is_missing(no_data, capsys):
    assert K.main(["pack", "x"]) == 2 and "not available" in capsys.readouterr().err
