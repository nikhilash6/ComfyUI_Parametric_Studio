"""
PSN_Modal_Job_Spec

Validates inputs and builds the job spec that would be sent to a Modal GPU
instance. It does NOT submit anything: it opens no sockets, makes no HTTP
requests and imports neither modal, torch nor comfy.

1. Validation of inputs (workflow_json, modal_env, gpu_type, timeout_sec).
2. Serialization of the spec (JSON text) from those inputs.
3. A content-hash key (job_key) over the inputs, so the same inputs give the
   same key. It is not an id issued by Modal.

Inputs:
    workflow_json (STRING): JSON string representing the ComfyUI workflow.
    modal_env (STRING): Environment name for Modal (e.g., "prod", "dev").
    gpu_type (COMBO): One of ["A100", "H100", "L4"].
    timeout_sec (INT): Timeout in seconds for the job.

Outputs:
    job_key (STRING): Content hash of the inputs, empty when invalid.
    job_spec_json (STRING): The spec as JSON text, empty when invalid.
    status (STRING): "validated", or "invalid: <reason>".
"""

import json
import hashlib

# Allowed GPU types
ALLOWED_GPU_TYPES = ["A100", "H100", "L4"]

# Allowed modal environments (simple allow-list for security)
ALLOWED_MODAL_ENVS = ["prod", "dev", "staging", "test"]


def _validate_workflow_json(workflow_json: str) -> tuple[bool, str]:
    """
    Validate that workflow_json is a valid JSON string and represents a dict.
    Returns (is_valid, error_message).
    """
    if not isinstance(workflow_json, str):
        return False, "workflow_json must be a string"
    if not workflow_json.strip():
        return False, "workflow_json must not be empty"
    try:
        parsed = json.loads(workflow_json)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    if not isinstance(parsed, dict):
        return False, "workflow_json must parse to a JSON object (dict)"
    return True, ""


def _validate_modal_env(modal_env: str) -> tuple[bool, str]:
    """
    Validate that modal_env is in the allow-list.
    Returns (is_valid, error_message).
    """
    if not isinstance(modal_env, str):
        return False, "modal_env must be a string"
    if modal_env not in ALLOWED_MODAL_ENVS:
        return False, f"modal_env must be one of {ALLOWED_MODAL_ENVS}, got '{modal_env}'"
    return True, ""


def _validate_gpu_type(gpu_type: str) -> tuple[bool, str]:
    """
    Validate that gpu_type is in the allow-list.
    Returns (is_valid, error_message).
    """
    if not isinstance(gpu_type, str):
        return False, "gpu_type must be a string"
    if gpu_type not in ALLOWED_GPU_TYPES:
        return False, f"gpu_type must be one of {ALLOWED_GPU_TYPES}, got '{gpu_type}'"
    return True, ""


def _validate_timeout_sec(timeout_sec: int) -> tuple[bool, str]:
    """
    Validate that timeout_sec is a positive integer.
    Returns (is_valid, error_message).
    """
    if not isinstance(timeout_sec, int) or isinstance(timeout_sec, bool):
        return False, "timeout_sec must be an integer"
    if timeout_sec <= 0:
        return False, "timeout_sec must be positive"
    if timeout_sec > 86400:  # Max 24 hours
        return False, "timeout_sec must not exceed 86400 seconds"
    return True, ""


def _job_key(workflow_json: str, modal_env: str, gpu_type: str, timeout_sec: int) -> str:
    """Content-hash key over the inputs (same inputs, same key)."""
    content = f"{workflow_json}|{modal_env}|{gpu_type}|{timeout_sec}"
    return "modal-spec-" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _build_spec(workflow_json: str, modal_env: str, gpu_type: str, timeout_sec: int) -> str:
    """Serialize the job spec for already-validated inputs."""
    return json.dumps(
        {
            "workflow": json.loads(workflow_json),
            "modal_env": modal_env,
            "gpu_type": gpu_type,
            "timeout_sec": timeout_sec,
        },
        sort_keys=True,
    )


class PSN_Modal_Job_Spec:
    """
    Validates inputs and builds a Modal job spec. Submits nothing.
    """

    DESCRIPTION = (
        "Validates a workflow JSON, Modal environment, GPU type and timeout, and builds the job "
        "spec as JSON with a content-hash key. Does not contact Modal or submit a job."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "workflow_json": ("STRING", {"default": "{}", "multiline": True}),
                "modal_env": (ALLOWED_MODAL_ENVS, {"default": "prod"}),
                "gpu_type": (ALLOWED_GPU_TYPES, {"default": "A100"}),
                "timeout_sec": ("INT", {"default": 300, "min": 1, "max": 86400, "step": 1}),
            },
            "optional": {},
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("job_key", "job_spec_json", "status")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Modal"
    
    def run(self, workflow_json: str, modal_env: str, gpu_type: str, timeout_sec: int) -> tuple[str, str, str]:
        """
        Validate inputs and build the job spec.

        Returns:
            Tuple of (job_key, job_spec_json, status).
        """
        for ok, err in (
            _validate_workflow_json(workflow_json),
            _validate_modal_env(modal_env),
            _validate_gpu_type(gpu_type),
            _validate_timeout_sec(timeout_sec),
        ):
            if not ok:
                return ("", "", "invalid: " + err)

        return (
            _job_key(workflow_json, modal_env, gpu_type, timeout_sec),
            _build_spec(workflow_json, modal_env, gpu_type, timeout_sec),
            "validated",
        )


NODE_CLASS_MAPPINGS = {
    "PSN_Modal_Job_Spec": PSN_Modal_Job_Spec,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Modal_Job_Spec": "PSN Modal Job Spec (validate only, does not submit)",
}
