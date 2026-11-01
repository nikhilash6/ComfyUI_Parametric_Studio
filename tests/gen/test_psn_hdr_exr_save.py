"""Tests for psn_nodes.gen.psn_hdr_exr_save (PSN_EXR_Save_Plan: EXR path check and size estimate; writes nothing)."""

import json

from psn_nodes.gen.psn_hdr_exr_save import (
    PSN_EXR_Save_Plan,
    _psn_validate_path,
    _psn_validate_compression,
    _psn_estimate_bytes,
)


def test_psn_validate_path_accepts_safe_relative():
    ok, why = _psn_validate_path("out/exr/frame.exr")
    assert ok is True
    assert why == "ok"


def test_psn_validate_path_rejects_traversal():
    ok, why = _psn_validate_path("../etc/passwd.exr")
    assert ok is False
    assert "traversal" in why


def test_psn_validate_path_rejects_absolute_and_bad_ext():
    ok1, _ = _psn_validate_path("/tmp/x.exr")
    assert ok1 is False
    ok2, why2 = _psn_validate_path("out/image.png")
    assert ok2 is False
    assert "extension" in why2


def test_psn_validate_compression_allowlist():
    assert _psn_validate_compression("Zip")[0] is True
    ok, why = _psn_validate_compression("LZW")
    assert ok is False
    assert "compression" in why


def test_psn_estimate_bytes_math():
    # 2x3x3 channels * 4 bytes = 72
    assert _psn_estimate_bytes(2, 3, 3) == 72


def test_psn_run_success_returns_planned_and_plan():
    node = PSN_EXR_Save_Plan()
    status, plan_json = node.run(
        height=2, width=3, channels=3,
        file_path="out/frame.exr",
        compression="Piz",
        free_space=1000.0,
    )
    assert status == "Planned"
    plan = json.loads(plan_json)
    assert plan["required_bytes"] == 72
    assert plan["fits"] is True
    assert plan["compression"] == "Piz"


def test_psn_run_insufficient_space_reports_error():
    node = PSN_EXR_Save_Plan()
    status, plan_json = node.run(
        height=100, width=100, channels=3,
        file_path="out/frame.exr",
        compression="None",
        free_space=10.0,
    )
    assert status.startswith("Error: insufficient disk space")
    plan = json.loads(plan_json)
    assert plan["fits"] is False
    assert plan["required_bytes"] > plan["free_space_bytes"]


def test_psn_run_bad_path_returns_error():
    node = PSN_EXR_Save_Plan()
    status, plan_json = node.run(
        height=2, width=2, channels=3,
        file_path="../../evil.exr",
        compression="Zip",
        free_space=1e9,
    )
    assert status.startswith("Error:")
    assert "traversal" in status
    assert json.loads(plan_json)["error"] == "path traversal is not allowed"


def test_psn_run_bad_compression_returns_error():
    node = PSN_EXR_Save_Plan()
    status, plan_json = node.run(
        height=2, width=2, channels=3,
        file_path="out/frame.exr",
        compression="Bogus",
        free_space=1e9,
    )
    assert status.startswith("Error:")
    assert "compression" in status


def test_psn_run_null_byte_path_rejected():
    node = PSN_EXR_Save_Plan()
    status, _ = node.run(
        height=2, width=2, channels=3,
        file_path="out/bad\x00name.exr",
        compression="Zip",
        free_space=1e9,
    )
    assert status.startswith("Error:")
    assert "null byte" in status


def test_nothing_is_written_and_status_never_says_saved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    status, plan_json = PSN_EXR_Save_Plan().run(
        height=4, width=4, channels=3, file_path="out/exr/frame.exr", compression="Zip", free_space=1e6)
    assert status == "Planned" and "Saved" not in status
    assert list(tmp_path.iterdir()) == []           # no file and no directory created
    plan = json.loads(plan_json)
    assert plan["required_bytes"] == 4 * 4 * 3 * 4 and plan["file_path"] == "out/exr/frame.exr"


def test_no_image_input_and_mappings():
    from psn_nodes.gen import psn_hdr_exr_save as m
    inputs = PSN_EXR_Save_Plan.INPUT_TYPES()
    assert "image" not in inputs["required"] and "image" not in inputs["optional"]
    assert list(m.NODE_CLASS_MAPPINGS) == ["PSN_EXR_Save_Plan"]
    assert "writes nothing" in m.NODE_DISPLAY_NAME_MAPPINGS["PSN_EXR_Save_Plan"]
    assert "writes no file" in PSN_EXR_Save_Plan.DESCRIPTION
