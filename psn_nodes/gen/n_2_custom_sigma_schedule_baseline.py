"""Parametric Studio - Custom Sigma Schedule Baseline.

Implements the core "Sigma Schedule Manipulation" workflow:
  * PSN_CustomSigmaGenerator: builds a 1D SIGMAS tensor from a chosen
    schedule (Linear / Karras / Exponential / Custom).
  * PSN_KSampler_Graph_Builder: takes a SIGMAS tensor, a sampler name and a
    seed and returns the JSON of one KSampler-style node entry that carries
    the sigma list.  It runs no sampling, has no model, conditioning or latent
    input, and does not submit anything to a backend.  The entry holds no
    links to other nodes, and ComfyUI's stock KSampler has no sigma-list
    input, so it is not a graph that can be queued as is.

Only torch (CPU) and the Python standard library are used.  Inputs are
never modified in place.
"""

import json
import math

import torch

CAT = "ParametricStudio/Sampling"

SIGMAS = "SIGMAS"
PSN_CONFIG = "PSN_CONFIG"

SCHEDULER_TYPES = ("Linear", "Karras", "Exponential", "Custom")
SAMPLER_TYPES = ("euler", "euler_ancestral", "heun", "dpmpp_2m")


def _as_tensor(x):
    """Return x as a torch tensor (no copy if already a tensor)."""
    if isinstance(x, torch.Tensor):
        return x
    return torch.as_tensor(x, dtype=torch.float32)


def _validate_sigmas(sigmas):
    """Validate a SIGMAS input: must be a 1D float tensor, finite, non-negative."""
    t = _as_tensor(sigmas)
    if t.dim() != 1:
        raise ValueError("SIGMAS must be a 1D tensor, got %dD" % t.dim())
    if t.numel() < 1:
        raise ValueError("SIGMAS must contain at least one value")
    if not torch.isfinite(t).all():
        raise ValueError("SIGMAS must be finite (no NaN/Inf)")
    if (t < 0).any():
        raise ValueError("SIGMAS must be non-negative")
    return t


def _linear_sigmas(steps, start_sigma, end_sigma):
    """Linear interpolation from start_sigma down to end_sigma.

    Returns steps+1 values (ComfyUI convention: len(sigmas) == steps + 1,
    last value is 0.0 for a full denoise).
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    n = steps + 1
    if n == 1:
        return torch.tensor([end_sigma], dtype=torch.float32)
    t = torch.linspace(0.0, 1.0, n, dtype=torch.float32)
    return start_sigma + (end_sigma - start_sigma) * t


def _karras_sigmas(steps, start_sigma, end_sigma):
    """Karras-style schedule (from ComfyUI / Stable Diffusion 3).

    sigma_i = (start^rho + i/(steps-1) * (end^rho - start^rho))^(1/rho)
    with rho = 7.0, then rescale so the first value equals start_sigma.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    rho = 7.0
    n = steps + 1
    if n == 1:
        return torch.tensor([end_sigma], dtype=torch.float32)
    eps = 1e-8
    s = max(start_sigma, eps)
    e = max(end_sigma, eps)
    r = torch.arange(n, dtype=torch.float32) / float(n - 1)
    sig = (s ** rho + r * (e ** rho - s ** rho)) ** (1.0 / rho)
    # Rescale so first value is exactly start_sigma and last is end_sigma.
    if sig[0].item() > 0:
        sig = sig * (start_sigma / sig[0].item())
    sig = sig.clone()
    sig[-1] = end_sigma
    return sig


def _exponential_sigmas(steps, start_sigma, end_sigma):
    """Exponential (geometric) interpolation from start_sigma to end_sigma."""
    if steps < 1:
        raise ValueError("steps must be >= 1")
    n = steps + 1
    if n == 1:
        return torch.tensor([end_sigma], dtype=torch.float32)
    eps = 1e-8
    s = max(start_sigma, eps)
    e = max(end_sigma, eps)
    t = torch.linspace(0.0, 1.0, n, dtype=torch.float32)
    sig = s * (e / s) ** t
    sig = sig.clone()
    sig[-1] = end_sigma
    return sig


def _parse_custom_sigmas(raw):
    """Parse a comma-separated string of floats into a 1D float tensor."""
    if not isinstance(raw, str):
        raise ValueError("Custom sigma string must be a string")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError("Custom sigma string is empty")
    vals = []
    for p in parts:
        try:
            v = float(p)
        except ValueError:
            raise ValueError("Invalid sigma value: %r" % p)
        if not math.isfinite(v):
            raise ValueError("Sigma value must be finite: %r" % p)
        if v < 0:
            raise ValueError("Sigma value must be non-negative: %r" % p)
        vals.append(v)
    return torch.tensor(vals, dtype=torch.float32)


def _build_kgraph(sigmas, sampler, seed):
    """Build a JSON-serialisable dict holding one KSampler-style node entry.

    Only the values this node knows are included: seed, step count (one less
    than the number of sigmas), sampler name and the sigma list.  No links to
    other nodes are made up.
    """
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(seed),
                "steps": int(sigmas.numel() - 1),
                "sampler_name": sampler,
                "custom_sigmas": sigmas.tolist(),
            },
        },
    }


class PSN_CustomSigmaGenerator:
    """Generate a custom SIGMAS schedule (Linear / Karras / Exponential / Custom)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scheduler_type": (SCHEDULER_TYPES,),
                "steps": ("INT", {"default": 20, "min": 1, "max": 1024}),
                "start_sigma": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 100.0}),
                "end_sigma": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 100.0}),
            },
            "optional": {
                "custom_sigma_string": ("STRING", {"default": ""}),
                "config": (PSN_CONFIG,),
            },
        }

    RETURN_TYPES = (SIGMAS,)
    RETURN_NAMES = ("sigmas",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, scheduler_type, steps, start_sigma, end_sigma,
            custom_sigma_string="", config=None):
        if scheduler_type not in SCHEDULER_TYPES:
            raise ValueError("Unknown scheduler_type: %r" % scheduler_type)
        if steps < 1:
            raise ValueError("steps must be >= 1")
        if start_sigma < 0 or end_sigma < 0:
            raise ValueError("start_sigma and end_sigma must be non-negative")

        if scheduler_type == "Custom":
            sigmas = _parse_custom_sigmas(custom_sigma_string)
        elif scheduler_type == "Linear":
            sigmas = _linear_sigmas(steps, start_sigma, end_sigma)
        elif scheduler_type == "Karras":
            sigmas = _karras_sigmas(steps, start_sigma, end_sigma)
        elif scheduler_type == "Exponential":
            sigmas = _exponential_sigmas(steps, start_sigma, end_sigma)
        else:
            raise ValueError("Unknown scheduler_type: %r" % scheduler_type)

        sigmas = _validate_sigmas(sigmas)
        return (sigmas,)


class PSN_KSampler_Graph_Builder:
    """Write a SIGMAS tensor, sampler name and seed into one KSampler-style node entry (JSON).

    Runs no sampling and makes no request.  The entry has no links to a model,
    conditioning or latent, and ComfyUI's stock KSampler has no sigma-list
    input, so it must be wired by whatever consumes it.
    """

    DESCRIPTION = ("Builds the JSON of one KSampler-style node entry holding a custom "
                   "sigma list, a sampler name and a seed. It runs no sampling, has no "
                   "model, conditioning or latent input, and submits nothing.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sigmas": (SIGMAS,),
                "sampler": (SAMPLER_TYPES,),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2 ** 63 - 1}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("node_entry_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, sigmas, sampler, seed=0):
        sig = _validate_sigmas(sigmas)
        if sampler not in SAMPLER_TYPES:
            raise ValueError("Unknown sampler: %r" % (sampler,))
        return (json.dumps(_build_kgraph(sig, sampler, seed)),)


NODE_CLASS_MAPPINGS = {
    "PSN_CustomSigmaGenerator": PSN_CustomSigmaGenerator,
    "PSN_KSampler_Graph_Builder": PSN_KSampler_Graph_Builder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CustomSigmaGenerator": "PSN Custom Sigma Generator",
    "PSN_KSampler_Graph_Builder": "KSampler Node Entry Builder (no sampling)",
}
