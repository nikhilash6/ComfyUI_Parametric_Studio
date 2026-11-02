"""ostris ai-toolkit (MIT): run.py and a YAML job. We write the YAML from studio/train_configs, in our own words; the trainer stays where you installed it.

Read from its source (v0.13.24): tqdm postfix 'lr: 1.0e-04 loss: 3.210e-01'; checkpoints <name>_000000250.safetensors in training_folder/<name> with optimizer.pt beside them; an unsuffixed <name>.safetensors at the end; samples/<ms>__000000250_0.jpg; on restart it finds the newest checkpoint and continues, optimizer included. SIGINT stops it with no save, so a cancel goes back to the last periodic save."""
from __future__ import annotations

import re
import time
from pathlib import Path

import yaml

from studio.trainers.base import ExternalTrainer, trainer_paths

CONFIGS = Path(__file__).resolve().parent.parent / "train_configs" / "ai_toolkit"
PROGRESS = re.compile(r"(\d+)/(\d+)\s*\[[^\]]*?loss:\s*([-+0-9.eE]+|nan|inf)")
SAMPLE = re.compile(r"__(\d+)_(\d+)\.(jpg|jpeg|png|webp|mp4)$")


def parse_progress(text: str) -> list:
    """[step, total, loss] from each tqdm redraw, in order. tqdm redraws with a carriage return, so the log is one long line."""
    out = []
    for m in PROGRESS.finditer(text.replace("\r", "\n")):
        raw = m.group(3)
        try: out.append([int(m.group(1)), int(m.group(2)), float(raw)])
        except ValueError: pass
    return out


_found: dict = {}


def _search(roots: list[Path], rel: str) -> str | None:
    """The file directly in a models folder, or anywhere under it. The page asks often and a deep search is slow, so an answer is kept for a minute."""
    key = (tuple(map(str, roots)), rel)
    when, hit = _found.get(key, (0, None))
    if time.time() - when < 60: return hit
    hit = next((str(r / rel) for r in roots if (r / rel).exists()), None)
    if not hit:
        for r in roots:
            if r.is_dir():
                hit = next((str(p) for p in r.rglob(rel)), None)
                if hit: break
    _found[key] = (time.time(), hit)
    return hit


class AiToolkit(ExternalTrainer):
    name = "ai-toolkit"

    def missing_install(self) -> list[str]:
        p = trainer_paths(self.name)
        miss = []
        if not p.get("dir") or not (Path(p["dir"]) / "run.py").is_file() or not (Path(p["dir"]) / "jobs").is_dir(): miss.append("ai-toolkit checkout (git clone https://github.com/ostris/ai-toolkit), set in STUDIO_TRAINER_AI_TOOLKIT_DIR.")
        if not p.get("python") or not Path(p["python"]).is_file(): miss.append("A Python for it with its requirements installed, set in STUDIO_TRAINER_AI_TOOLKIT_PYTHON.")
        return miss

    def _weight_paths(self, base: dict) -> tuple[dict, list[str]]:
        """Each file or folder the config names, found through the folders ComfyUI lists. Returns name to full path, and what is not there."""
        from studio import train as T
        found, missing = {}, []
        own = trainer_paths(self.name).get("files") or {}          # trainers.json can say where a file or folder lives on this machine
        for key, (folder, rel) in (base.get("aitk") or {}).get("files", {}).items():
            if own.get(rel) and Path(own[rel]).exists():
                found[key] = own[rel]
                continue
            roots = [Path(r) for r in T._comfy_folder(folder)] + [Path(T.paths.models_root(True)) / folder]
            hit = _search(roots, rel)
            if hit: found[key] = hit
            else: missing.append(f"{rel} is not installed (models folder {folder}).")
        return found, missing

    def _link_farm(self, run: Path, found: dict, base: dict) -> dict:
        """The trainer writes beside its inputs (a tokenizer folder next to the text encoder) and downloads what it cannot find into MODELS_PATH, so it gets a folder of links in the run's own space, laid out as the models folders are, never the real model store."""
        farm = run / "models_path"
        out = {}
        files = base["aitk"]["files"]
        for key, target in found.items():
            sub = farm / files[key][0]
            sub.mkdir(parents=True, exist_ok=True)
            link = sub / Path(target).name
            if not link.is_symlink(): link.symlink_to(target)
            out[key] = str(link)
        return out

    def check(self, base: dict, info):
        missing = self.missing_install()
        found, gone = self._weight_paths(base)
        missing += gone
        for key, subs in (base.get("aitk") or {}).get("folder_needs", {}).items():
            if key not in found: continue
            for sub in subs:
                d = Path(found[key]) / sub
                if not d.is_dir() or not any(d.glob("*.safetensors")): missing.append(f"{Path(found[key]).name}/{sub} has no weights in it. Download the full folder from {base.get('repo')}.")
        if missing: return " ".join(missing), missing
        return None, []

    def _render(self, job: dict | None, base: dict, s: dict, found: dict, run: str, trigger: str, prompt: str) -> str:
        spec = base["aitk"]
        text = (CONFIGS / spec["template"]).read_text()
        rep = {"name": (job or {}).get("id", "preview"), "run_dir": run, "dataset": f"{run}/dataset", "trigger": trigger, "steps": s["steps"], "rank": s["rank"], "batch": s["batch"], "lr": s["learning_rate"], "size": s["size"], "seed": s["seed"], "prompt": prompt,
               "save_every": max(25, s["steps"] // 4), "sample_every": max(25, s["steps"] // 4), "sample_steps": spec.get("sample_steps", 20), "guidance": spec.get("guidance", 4.0), "arch": spec["arch"], "num_frames": spec.get("num_frames", 1), **found}
        for k, v in rep.items(): text = text.replace("{{" + k + "}}", str(v))
        return text

    def write_config(self, job: dict, base: dict, info) -> None:
        found, missing = self._weight_paths(base)
        if missing: raise FileNotFoundError(" ".join(missing))
        run = Path(job["run_dir"]); run.mkdir(parents=True, exist_ok=True)
        found = self._link_farm(run, found, base)
        text = self._render(job, base, job["settings"], found, str(run), job["trigger"], job["sample_prompt"])
        yaml.safe_load(text)         # a broken template fails here, not inside the trainer
        (run / "config.yaml").write_text(text)

    def preview(self, base: dict, settings: dict) -> str:
        found, _ = self._weight_paths(base)
        return self._render(None, base, settings, found, "(the run's folder)", "(your trigger)", "(your test prompt)")

    def command(self, job: dict, base: dict) -> list[str]:
        return [trainer_paths(self.name)["python"], "run.py", str(Path(job["run_dir"]) / "config.yaml")]

    def env(self, job: dict) -> dict:
        return {**super().env(job), "MODELS_PATH": str(Path(job["run_dir"]) / "models_path")}

    def parse_log(self, text: str) -> list:
        return parse_progress(text)

    def _out(self, job: dict) -> Path:
        return Path(job["run_dir"]) / job["id"]

    def list_samples(self, job: dict) -> list[dict]:
        d = self._out(job) / "samples"
        rows = []
        if d.is_dir():
            for f in d.iterdir():
                m = SAMPLE.search(f.name)
                if m: rows.append({"name": f.name, "step": int(m.group(1)), "index": int(m.group(2)), "rel": str(f.relative_to(job["run_dir"])), "url": f"/api/train/jobs/{job['id']}/sample/{f.name}"})
        return sorted(rows, key=lambda r: (r["step"], r["index"], r["name"]))

    def list_checkpoints(self, job: dict) -> list[str]:
        d = self._out(job)
        return sorted(f.name for f in d.glob(f"{job['id']}_*.safetensors")) if d.is_dir() else []

    def result(self, job: dict) -> Path | None:
        final = self._out(job) / f"{job['id']}.safetensors"
        if final.is_file(): return final
        steps = self.list_checkpoints(job)
        return (self._out(job) / steps[-1]) if steps else None
