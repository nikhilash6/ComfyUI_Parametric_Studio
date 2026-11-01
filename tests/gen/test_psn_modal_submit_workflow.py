"""
Tests for PSN_Modal_Job_Spec node.

The node validates inputs and builds a job spec. It contacts nothing, so these
tests check the values it returns and that no completion claim is made.
"""

import json

from psn_nodes.gen.psn_modal_submit_workflow import (
    PSN_Modal_Job_Spec,
    _validate_workflow_json,
    _validate_timeout_sec,
    _job_key,
    ALLOWED_GPU_TYPES,
    ALLOWED_MODAL_ENVS,
)

WF = json.dumps({"nodes": [], "links": []})


class TestPSNModalJobSpec:
    def test_valid_inputs_build_spec_and_validated_status(self):
        key, spec, status = PSN_Modal_Job_Spec().run(WF, "prod", "A100", 300)
        assert status == "validated"
        assert key.startswith("modal-spec-")
        assert len(key) == len("modal-spec-") + 16
        assert json.loads(spec) == {
            "workflow": {"nodes": [], "links": []},
            "modal_env": "prod",
            "gpu_type": "A100",
            "timeout_sec": 300,
        }

    def test_no_completion_is_claimed(self):
        key, spec, status = PSN_Modal_Job_Spec().run(WF, "prod", "H100", 60)
        assert status != "completed"
        assert "completed" not in status
        assert PSN_Modal_Job_Spec.RETURN_NAMES == ("job_key", "job_spec_json", "status")
        assert "does not" in PSN_Modal_Job_Spec.DESCRIPTION.lower()

    def test_invalid_json(self):
        key, spec, status = PSN_Modal_Job_Spec().run("not valid json", "prod", "A100", 300)
        assert (key, spec) == ("", "")
        assert status.startswith("invalid: Invalid JSON")

    def test_empty_workflow_json(self):
        key, spec, status = PSN_Modal_Job_Spec().run("", "prod", "A100", 300)
        assert (key, spec) == ("", "")
        assert status == "invalid: workflow_json must not be empty"

    def test_invalid_modal_env(self):
        key, spec, status = PSN_Modal_Job_Spec().run(WF, "invalid_env", "A100", 300)
        assert (key, spec) == ("", "")
        assert "modal_env must be one of" in status

    def test_invalid_gpu_type(self):
        key, spec, status = PSN_Modal_Job_Spec().run(WF, "prod", "V100", 300)
        assert (key, spec) == ("", "")
        assert "gpu_type must be one of" in status

    def test_invalid_timeout(self):
        node = PSN_Modal_Job_Spec()
        for t, msg in ((0, "positive"), (-10, "positive"), (100000, "exceed")):
            key, spec, status = node.run(WF, "prod", "A100", t)
            assert (key, spec) == ("", "")
            assert msg in status

    def test_key_is_deterministic_and_input_sensitive(self):
        wf1 = json.dumps({"nodes": [{"id": 1}]})
        wf2 = json.dumps({"nodes": [{"id": 2}]})
        assert _job_key(wf1, "prod", "A100", 300) == _job_key(wf1, "prod", "A100", 300)
        assert _job_key(wf1, "prod", "A100", 300) != _job_key(wf2, "prod", "A100", 300)
        assert _job_key(wf1, "prod", "A100", 300) != _job_key(wf1, "dev", "A100", 300)

    def test_all_gpu_types_and_envs_reach_spec(self):
        node = PSN_Modal_Job_Spec()
        for gpu in ALLOWED_GPU_TYPES:
            _, spec, status = node.run(WF, "prod", gpu, 300)
            assert status == "validated" and json.loads(spec)["gpu_type"] == gpu
        for env in ALLOWED_MODAL_ENVS:
            _, spec, status = node.run(WF, env, "A100", 300)
            assert status == "validated" and json.loads(spec)["modal_env"] == env

    def test_validate_workflow_json_rejects_non_dict_and_non_string(self):
        assert _validate_workflow_json("[1, 2, 3]") == (False, "workflow_json must parse to a JSON object (dict)")
        assert _validate_workflow_json(123) == (False, "workflow_json must be a string")
        assert _validate_workflow_json(None)[0] is False

    def test_validate_timeout_rejects_bool(self):
        assert _validate_timeout_sec(True) == (False, "timeout_sec must be an integer")
        assert _validate_timeout_sec(300) == (True, "")

    def test_input_types_and_names(self):
        req = PSN_Modal_Job_Spec.INPUT_TYPES()["required"]
        assert req["workflow_json"][0] == "STRING"
        assert req["modal_env"][0] == ALLOWED_MODAL_ENVS
        assert req["gpu_type"][0] == ALLOWED_GPU_TYPES
        assert req["timeout_sec"][0] == "INT"
        assert PSN_Modal_Job_Spec.RETURN_TYPES == ("STRING", "STRING", "STRING")
        assert PSN_Modal_Job_Spec.FUNCTION == "run"
