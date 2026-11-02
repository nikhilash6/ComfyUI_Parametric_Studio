"""SimpleTuner (AGPL-3): `simpletuner train env=<name>` reads config/<name>/config.json in its working folder. We write that config and its dataset file, in the run's own folder.

Read from its source (@82a589d): tqdm postfix step_loss=..., checkpoints output_dir/checkpoint-N, resume_from_checkpoint=latest picks up the newest, the final file output_dir/pytorch_lora_weights.safetensors, audio validations under output_dir/validation_images."""
from __future__ import annotations

import json
import re
from pathlib import Path

from studio.trainers.base import ExternalTrainer, trainer_paths

PROGRESS = re.compile(r"(\d+)/(\d+)\s*\[[^\]]*?step_loss=([-+0-9.eE]+|nan|inf)")
AUDIO = (".wav", ".flac", ".mp3", ".ogg")
SAMPLE_STEP = re.compile(r"(?:^|[_-])(\d+)[_-]")


def parse_progress(text: str) -> list:
    out = []
    for m in PROGRESS.finditer(text.replace("\r", "\n")):
        try: out.append([int(m.group(1)), int(m.group(2)), float(m.group(3))])
        except ValueError: pass
    return out


class SimpleTuner(ExternalTrainer):
    name = "simpletuner"

    def missing_install(self) -> list[str]:
        p = trainer_paths(self.name)
        miss = []
        if not p.get("python") or not Path(p["python"]).is_file(): miss.append("SimpleTuner installed in its own Python, set in STUDIO_TRAINER_SIMPLETUNER_PYTHON.")
        return miss

    def cwd(self) -> str | None:
        return None

    def _pipeline(self, base: dict) -> Path | None:
        from studio import train as T
        rel = base["st"]["folder"]
        own = (trainer_paths(self.name).get("files") or {}).get(rel)
        if own and Path(own).is_dir(): return Path(own)
        for root in [Path(r) for r in T._comfy_folder("diffusers")] + [Path(T.paths.models_root(True)) / "diffusers"]:
            if (root / rel).is_dir(): return root / rel
        return None

    def check(self, base: dict, info):
        missing = self.missing_install()
        folder = self._pipeline(base)
        if not folder: missing.append(f"The {base['st']['folder']} folder from {base.get('repo')} is not installed (models folder diffusers).")
        else:
            for sub, pattern in base["st"].get("needs", {}).items():
                if not list((folder / sub).glob(pattern) if sub != "." else folder.glob(pattern)): missing.append(f"{folder.name}/{sub} has no {pattern} in it. Download it from {base.get('repo')}.")
        if missing: return " ".join(missing), missing
        return None, []

    def _config(self, job: dict | None, base: dict, s: dict, pipeline: str, run: str, trigger: str, prompt: str) -> tuple[dict, list]:
        spec = base["st"]
        every = max(25, s["steps"] // 4)
        cfg = {"model_family": spec["family"], "model_flavour": spec["flavour"], "model_type": "lora", "pretrained_model_name_or_path": pipeline, "pretrained_vae_model_name_or_path": pipeline, "resolution": 512, "mixed_precision": "bf16", "base_model_precision": "int8-quanto", "text_encoder_1_precision": "int8-quanto", "gradient_checkpointing": True,
               "lora_rank": s["rank"], "lora_format": "comfyui", "optimizer": "adamw_bf16", "learning_rate": s["learning_rate"], "train_batch_size": s["batch"], "vae_batch_size": 1, "max_train_steps": s["steps"], "num_train_epochs": 0, "checkpoint_step_interval": every, "lr_scheduler": "constant", "lr_warmup_steps": 0, "seed": s["seed"], "report_to": "none", "output_dir": f"{run}/output", "data_backend_config": f"{run}/config/run/multidatabackend.json",
               "validation_prompt": prompt, "validation_lyrics": "", "validation_audio_duration": 20, "validation_guidance": 1.7, "validation_num_inference_steps": 30, "validation_steps": every, "validation_seed": 42, "validation_on_startup": True, "validation_disable_unconditional": True, "resume_from_checkpoint": "latest", "tracker_project_name": "lora", "tracker_run_name": "run"}
        data = [{"id": "audio", "type": "local", "dataset_type": "audio", "instance_data_dir": f"{run}/dataset", "metadata_backend": "discovery", "caption_strategy": "textfile", "audio": {"bucket_strategy": "duration", "duration_interval": 3.0, "max_duration_seconds": 60, "lyrics_filename_format": "{filename}.lyrics"}, "cache_dir_vae": f"{run}/cache/vae"},
                {"id": "text-embeds", "dataset_type": "text_embeds", "default": True, "type": "local", "cache_dir": f"{run}/cache/text"}]
        return cfg, data

    def write_config(self, job: dict, base: dict, info) -> None:
        folder = self._pipeline(base)
        if not folder: raise FileNotFoundError(f"The {base['st']['folder']} folder is not installed.")
        run = Path(job["run_dir"]); (run / "config" / "run").mkdir(parents=True, exist_ok=True)
        cfg, data = self._config(job, base, job["settings"], str(folder), str(run), job["trigger"], job["sample_prompt"])
        (run / "config" / "run" / "config.json").write_text(json.dumps(cfg, indent=1))
        (run / "config" / "run" / "multidatabackend.json").write_text(json.dumps(data, indent=1))
        for f in (run / "dataset").glob("*.txt"):
            lyrics = f.with_suffix(".lyrics")
            if not lyrics.exists(): lyrics.write_text("[Instrumental]")

    def preview(self, base: dict, settings: dict) -> str:
        return json.dumps(self._config(None, base, settings, "(the model folder)", "(the run's folder)", "(your trigger)", "(your test prompt)")[0], indent=1)

    def command(self, job: dict, base: dict) -> list[str]:
        return [trainer_paths(self.name)["python"], "-m", "simpletuner.cli", "train", "env=run"]

    def spawn(self, job: dict, base: dict) -> None:
        self._cwd = job["run_dir"]
        super().spawn(job, base)

    def env(self, job: dict) -> dict:
        return {**super().env(job), "SIMPLETUNER_CONFIG_BACKEND": "json", "CONFIG_PATH": f"{job['run_dir']}/config/run/config.json", "SIMPLETUNER_WORKSPACE": job["run_dir"]}

    def parse_log(self, text: str) -> list:
        return parse_progress(text)

    def list_samples(self, job: dict) -> list[dict]:
        d = Path(job["run_dir"]) / "output" / "validation_images"
        rows = []
        if d.is_dir():
            for f in sorted(d.rglob("*"), key=lambda p: p.stat().st_mtime):
                if f.suffix.lower() in AUDIO:
                    m = SAMPLE_STEP.search(f.stem)
                    rows.append({"name": f.name, "step": int(m.group(1)) if m else len(rows), "index": len(rows), "rel": str(f.relative_to(job["run_dir"])), "url": f"/api/train/jobs/{job['id']}/sample/{f.name}"})
        return rows

    def list_checkpoints(self, job: dict) -> list[str]:
        d = Path(job["run_dir"]) / "output"
        return sorted((c.name for c in d.glob("checkpoint-*") if c.is_dir()), key=lambda n: int(re.sub(r"\D", "", n) or 0)) if d.is_dir() else []

    def result(self, job: dict) -> Path | None:
        f = Path(job["run_dir"]) / "output" / "pytorch_lora_weights.safetensors"
        return f if f.is_file() else None
