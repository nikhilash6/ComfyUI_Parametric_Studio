"""ParametricStudio - Audio sigma schedules.

PSN_AudioScheduler builds a sigma schedule (Linear / Karras / AudioOptimized).
It is only a list of numbers; there is no audio sampler in this module and no
audio diffusion model.
"""

import math

import torch

CAT = "ParametricStudio/Audio"


def _karras_sigmas(steps, sigma_max, sigma_min):
    """Karras-style schedule: smoothstep between sigma_min and sigma_max."""
    rho = 7.0
    sigmas = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        # smoothstep
        s = t * t * (3.0 - 2.0 * t)
        # karras: sigma = (sigma_max^(1/rho) + s * (sigma_min^(1/rho) - sigma_max^(1/rho)))^rho
        a = sigma_max ** (1.0 / rho)
        b = sigma_min ** (1.0 / rho)
        sig = (a + s * (b - a)) ** rho
        sigmas.append(sig)
    sigmas.append(0.0)
    return torch.tensor(sigmas, dtype=torch.float32)


def _linear_sigmas(steps, sigma_max, sigma_min):
    sigmas = torch.linspace(sigma_max, sigma_min, steps, dtype=torch.float32)
    sigmas = torch.cat([sigmas, torch.zeros(1, dtype=torch.float32)])
    return sigmas


def _audio_optimized_sigmas(steps, sigma_max, sigma_min):
    """Audio-optimized: front-loaded schedule (more steps at high sigma) to
    capture coarse temporal structure first, then refine fine detail."""
    # Use a power curve: t^gamma with gamma < 1 to front-load
    gamma = 0.6
    sigmas = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        s = t ** gamma
        sig = sigma_max + s * (sigma_min - sigma_max)
        sigmas.append(sig)
    sigmas.append(0.0)
    return torch.tensor(sigmas, dtype=torch.float32)


class PSN_AudioScheduler:
    """Generate a sigma schedule tailored for audio diffusion models."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": 20, "min": 1, "max": 512}),
                "scheduler_type": ("Linear", "Karras", "AudioOptimized"),
                "sigma_max": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 100.0}),
                "sigma_min": ("FLOAT", {"default": 0.001, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("SIGMAS",)
    RETURN_NAMES = ("sigmas",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, steps, scheduler_type, sigma_max, sigma_min):
        if steps < 1:
            raise ValueError("steps must be >= 1")
        if sigma_max <= 0:
            raise ValueError("sigma_max must be > 0")
        if sigma_min < 0:
            raise ValueError("sigma_min must be >= 0")
        if sigma_min >= sigma_max:
            raise ValueError("sigma_min must be < sigma_max")

        if scheduler_type == "Linear":
            sigmas = _linear_sigmas(steps, sigma_max, sigma_min)
        elif scheduler_type == "Karras":
            sigmas = _karras_sigmas(steps, sigma_max, sigma_min)
        elif scheduler_type == "AudioOptimized":
            sigmas = _audio_optimized_sigmas(steps, sigma_max, sigma_min)
        else:
            raise ValueError(f"unknown scheduler_type: {scheduler_type}")

        return (sigmas,)


NODE_CLASS_MAPPINGS = {
    "PSN_AudioScheduler": PSN_AudioScheduler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_AudioScheduler": "Audio Scheduler",
}
