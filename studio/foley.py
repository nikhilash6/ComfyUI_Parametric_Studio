"""Add sound to a silent clip with ControlFoley (Xiaomi Research): the rules, kept apart from the routes so they can be tested without ComfyUI.
The model's weights are CC BY-NC 4.0 and the image encoder it loads (Apple's DFN5B-CLIP) is for research only, so nothing here is a default:
a run needs the person to say, every time, that the result is for non-commercial use. The picture is never re-encoded: ffmpeg copies the video
stream and adds the new sound beside it. Loudness is measured by ffmpeg's EBU R128 filter; nobody listens."""
import json, os, re
from pathlib import Path
from psn import paths

GRAPH = "clipsound_foley_api.json"
MAX_SECONDS = 30.0      # LoadControlFoleyVideo's own limit
MIN_SECONDS = 0.7
STEPS = (10, 25, 40)    # 25 is the pack's fixed default

#: The weights and code a run uses, each with its own terms. The strictest decides what you may do with the result.
LICENCES = [
    {"what": "ControlFoley weights (Xiaomi Research)", "name": "CC BY-NC 4.0", "url": "https://creativecommons.org/licenses/by-nc/4.0/", "card": "https://huggingface.co/YJX-Xiaomi/ControlFoley", "commercial": False,
     "quote": "the model weights are licensed under the CC BY-NC 4.0"},
    {"what": "DFN5B-CLIP image encoder (Apple), which ControlFoley loads to see the clip", "name": "Apple Machine Learning Research Model License", "url": "https://huggingface.co/apple/DFN5B-CLIP-ViT-H-14-384/blob/main/LICENSE", "card": "https://huggingface.co/apple/DFN5B-CLIP-ViT-H-14-384", "commercial": False, "research_only": True,
     "quote": "\u201cResearch Purposes\u201d does not include any commercial exploitation, product development or use in any commercial product or service."},
    {"what": "MusicGen-style and MERT-v1-95M (Meta, m-a-p), loaded for sound references", "name": "CC BY-NC 4.0", "url": "https://creativecommons.org/licenses/by-nc/4.0/", "card": "https://huggingface.co/facebook/musicgen-style", "commercial": False},
    {"what": "BigVGAN v2 44 kHz vocoder (NVIDIA), which turns ControlFoley's output into a waveform", "name": "MIT", "url": "https://huggingface.co/nvidia/bigvgan_v2_44khz_128band_512x", "card": "https://huggingface.co/nvidia/bigvgan_v2_44khz_128band_512x", "commercial": True},
    {"what": "Text encoders it loads: T5-base and BERT-base (Google), BART-base (Meta) under Apache-2.0; RoBERTa-base (Meta) under MIT", "name": "Apache-2.0 and MIT", "url": "https://huggingface.co/google-t5/t5-base", "card": "https://huggingface.co/google-t5/t5-base", "commercial": True},
    {"what": "ControlFoley code and the ComfyUI nodes", "name": "Apache-2.0", "url": "https://github.com/xiaomi-research/controlfoley/blob/main/LICENSE", "card": "https://github.com/xiaomi-research/controlfoley", "commercial": True},
]
LABEL = "Non-commercial (CC BY-NC 4.0)"
HONEST = "Generated ambience for the whole clip. It doesn't place sounds on visible events (measured: no better than chance)."
STRICTEST = "Research and other non-commercial use only. Apple's DFN5B licence, which ControlFoley needs, also rules out product development and any commercial product or service."

MODELS = [{"id": "controlfoley", "label": "ControlFoley large 44 kHz", "maker": "Xiaomi Research", "card": "https://huggingface.co/YJX-Xiaomi/ControlFoley", "code": "https://github.com/xiaomi-research/controlfoley",
           "label_short": LABEL, "strictest": STRICTEST, "honest": HONEST, "licences": LICENCES, "commercial": False, "default": False,
           "does": "Listens to nothing: it watches the clip and makes sound that fits what it sees, timed to the picture. A few words can steer it."}]

WEIGHTS = ("weights/controlfoley.pth", "ext_weights/v1-44.pth", "ext_weights/synchformer_state_dict.pth", "ext_weights/cav_mae_st.pth", "ext_weights/music_speech_audioset_epoch_15_esc_89.98.pt", "ext_weights/empty_string.pth")
#: Hugging Face repos the node loads with low_vram off (the only mode the pack supports for video). The node downloads any it cannot find, so the studio refuses first.
HF_REPOS = ("apple/DFN5B-CLIP-ViT-H-14-384", "nvidia/bigvgan_v2_44khz_128band_512x", "facebook/musicgen-style", "roberta-base", "facebook/bart-base", "bert-base-uncased", "m-a-p/MERT-v1-95M", "t5-base")


def comfy_dir(): return Path(paths.setting("PSN_COMFY_DIR", default=paths.home("ComfyUI")))
def weights_dir(root=None): return Path(root or paths.models_root()) / "controlfoley" / "model_weights"
def hf_hub(): return Path(paths.setting("HF_HUB_CACHE") or Path(paths.setting("HF_HOME", default=paths.home(".cache", "huggingface"))) / "hub")


WEIGHT_EXT = (".bin", ".safetensors", ".pt", ".pth")
def _has_weights(snap): return any(f.suffix in WEIGHT_EXT and f.is_file() for f in Path(snap).rglob("*"))


def _cached(repo, hub):
    """Ask huggingface_hub the same question the node asks before it downloads: is a complete snapshot of this repo in the cache, offline?
    A snapshot missing any file counts as absent, because the node would then fetch the rest. Without huggingface_hub, a snapshot folder holding files is enough."""
    try: from huggingface_hub import snapshot_download
    except ImportError: snapshot_download = None
    if snapshot_download is not None:
        try: snap = Path(snapshot_download(repo_id=repo, cache_dir=str(hub), local_files_only=True))
        except Exception: return False
        return _has_weights(snap)      # a cache with only a tokenizer passes the probe, then fails when the model loads
    snaps = hub / ("models--" + repo.replace("/", "--")) / "snapshots"
    return snaps.is_dir() and any(_has_weights(s) for s in snaps.iterdir())


def missing(root=None, comfy=None, hub=None):
    """What this machine lacks to run ControlFoley without downloading anything. [] means ready."""
    out = []; src = Path(comfy or comfy_dir()) / "controlfoley"
    if not ((src / "demo.py").is_file() and (src / "controlfoley" / "inference_utils.py").is_file()): out.append("ControlFoley source code (github.com/xiaomi-research/controlfoley) next to ComfyUI")
    w = weights_dir(root); out += [f"controlfoley/model_weights/{f}" for f in WEIGHTS if not (w / f).is_file()]
    h = Path(hub or hf_hub()); out += [f"Hugging Face cache: {r}" for r in HF_REPOS if not _cached(r, h)]
    return out


def clean_words(s, n=200):
    """A prompt for the model: printable, one line, no braces that a template might read."""
    return re.sub(r"[{}$\\]", "", " ".join("".join(c for c in str(s or "") if c.isprintable()).split()))[:n]


def options(b):
    """The request, checked. -> dict. Raises ValueError with a sentence a person can act on."""
    if b.get("model", "controlfoley") != "controlfoley": raise ValueError("pick the model listed")
    if b.get("noncommercial") is not True: raise ValueError("ControlFoley's weights are CC BY-NC 4.0 and Apple's DFN5B encoder is for research only. Tick the box to say this sound is for non-commercial use.")
    try: seed = int(b.get("seed") if b.get("seed") not in (None, "") else 42)
    except (TypeError, ValueError): raise ValueError("seed must be a whole number") from None
    if not 0 <= seed <= 4294967295: raise ValueError("seed must be between 0 and 4294967295")
    steps = int(b.get("steps") or 25)
    if steps not in STEPS: raise ValueError(f"steps must be one of {', '.join(map(str, STEPS))}")
    try: cfg = float(b.get("cfg") if b.get("cfg") not in (None, "") else 4.5)
    except (TypeError, ValueError): raise ValueError("guidance must be a number") from None
    if not 1.0 <= cfg <= 10.0: raise ValueError("guidance must be between 1 and 10")
    return {"model": "controlfoley", "prompt": clean_words(b.get("prompt")), "negative": clean_words(b.get("negative")), "seed": seed, "steps": steps, "cfg": round(cfg, 2), "noncommercial": True}


def graph_values(clip, seconds, opts, prefix, root=None):
    """Values for the ${...} slots in the graph. The clip goes in by absolute path; the duration is the clip's own, within the node's limits."""
    return {"weights_dir": str(weights_dir(root)), "video_path": str(clip), "duration": round(min(MAX_SECONDS, max(MIN_SECONDS, float(seconds))), 3), "prompt": opts["prompt"], "negative": opts["negative"],
            "seed": opts["seed"], "steps": str(opts["steps"]), "cfg": opts["cfg"], "prefix": prefix}


TARGET_LUFS, TARGET_TP, TARGET_LRA = -16.0, -1.5, 11.0


def level_measure_command(ffmpeg, wav, seconds):
    """Pass one of ffmpeg loudnorm: measure the raw sound (trimmed to the picture) so pass two can level it exactly."""
    return [ffmpeg, "-hide_banner", "-nostats", "-i", str(wav), "-af", f"atrim=end={float(seconds):.3f},loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json", "-f", "null", "-"]


def parse_level(stderr):
    """loudnorm's JSON block -> the measured_* values pass two needs, or None when it could not measure (silence)."""
    i = stderr.rfind("{"); j = stderr.rfind("}")
    try: d = json.loads(stderr[i:j + 1])
    except ValueError: return None
    try: vals = {k: float(d[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    except (KeyError, ValueError): return None
    return vals if all(v == v and abs(v) != float("inf") for v in vals.values()) else None


def mux_command(ffmpeg, clip, wav, dest, seconds, level=None):
    """The clip's picture, copied packet for packet, with the new sound as its only audio track (AAC 192k).
    The sound is trimmed to the picture's length (-shortest is not used: with a copied picture it drops the last frames), then levelled by loudnorm's second pass
    to -16 LUFS with a true-peak ceiling of -1.5 dBTP, so a hot take no longer clips. Without a measurement, loudnorm runs in one pass."""
    norm = f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}"
    if level: norm += f":measured_I={level['input_i']}:measured_TP={level['input_tp']}:measured_LRA={level['input_lra']}:measured_thresh={level['input_thresh']}:offset={level['target_offset']}:linear=true"
    return [ffmpeg, "-y", "-v", "error", "-i", str(clip), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-af", f"atrim=end={float(seconds):.3f},{norm},aresample=44100,atrim=end={float(seconds):.3f}",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dest)]


def loudness_command(ffmpeg, wav): return [ffmpeg, "-hide_banner", "-nostats", "-i", str(wav), "-af", "ebur128=peak=true", "-f", "null", "-"]


def parse_loudness(stderr):
    """ffmpeg ebur128's summary -> {lufs, lra, true_peak_db}. Missing numbers are None."""
    tail = stderr[stderr.rfind("Summary:"):] if "Summary:" in stderr else stderr
    def num(pat):
        m = re.search(pat, tail)
        return float(m.group(1)) if m else None
    return {"lufs": num(r"I:\s+(-?[\d.]+|-inf)\s+LUFS"), "lra": num(r"LRA:\s+(-?[\d.]+)\s+LU"), "true_peak_db": num(r"Peak:\s+(-?[\d.]+|-inf)\s+dBFS")}


def receipt(path, clip, opts, model=MODELS[0]):
    """A JSON file beside the result that says what made it and under which terms, so the licence travels with the sound."""
    Path(path).write_text(json.dumps({"model": model["label"], "maker": model["maker"], "card": model["card"], "label": LABEL, "terms": STRICTEST, "licences": [{k: l[k] for k in ("what", "name", "url")} for l in LICENCES],
                                      "clip": Path(clip).name, "prompt": opts["prompt"], "negative": opts["negative"], "seed": opts["seed"], "steps": opts["steps"], "cfg": opts["cfg"],
                                      "noncommercial_confirmed": True, "listened": False}, indent=1), encoding="utf-8")
