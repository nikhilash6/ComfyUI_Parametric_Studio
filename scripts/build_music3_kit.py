#!/usr/bin/env python3
"""Builds the Music 3 style kit: workflows/music_music3_kit_api.json (Music 3 with one ntc-ai slider LoRA on the text encoder and
the guillaume127 turbo LoRA on the DiT behind a switch) and studio/music3_kit.json (what the Music page offers, with sources
and honest labels). The slider files are read from the models folder so the sizes and hashes are this box's.
Usage: python3 scripts/build_music3_kit.py [--models MODELS_ROOT]   (default: the studio's models root)   (the proof block of an existing kit is kept)"""
import argparse, copy, hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUB = "minimax/music3"
TURBO = "minimax_music3_turbo_lora_8step.safetensors"
LABELS = {"acoustic-folk": "Acoustic folk", "afrobeats": "Afrobeats", "country": "Country", "disco-funk": "Disco funk", "female": "Female voice", "hiphop": "Hip-hop",
          "house": "House", "indie-rock": "Indie rock", "kpop": "K-pop", "lofi": "Lo-fi", "male": "Male voice", "metal": "Metal", "pop-punk": "Pop punk", "pop": "Pop",
          "reggaeton": "Reggaeton", "rnb": "R&B"}
VOICE = {"female", "male"}
HONEST = [
    "A slider nudges the song toward its name; it does not switch genre or voice on its own. Write the style in the caption as well.",
    "Strength runs from 0 (off) to 1.5. The author's advice is to start at 1 and compare with 0 using the same caption, lyrics and seed. Negative strength is not a trained opposite, so the studio doesn't offer it.",
    "One slider at a time: the author did not test stacking them.",
    "The sliders were converted on this box to the fused q/k/v layout of the text encoder the studio uses; the conversion binds every key (checked on the CPU, 2026-10-10).",
    "Turbo speeds up only the DiT's sampling (8 steps instead of 30). The text encoder's planning and the audio decode take as long as before, so a whole song is faster, not 4x faster.",
    "Nobody has listened to any render made with the kit. Proof below is measured by programs only.",
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def graph(base):
    """music3_api.json plus: slider LoraLoader on the CLIP (strength_model 0), turbo LoraLoaderModelOnly behind a lazy switch, 30/8 steps and TE cfg 1.7/1.5 behind the same switch."""
    g = copy.deepcopy(base)
    te = next(k for k, v in g.items() if v["class_type"] == "MiniMaxMusic3TextEncode"); ks = next(k for k, v in g.items() if v["class_type"] == "KSampler")
    unet = next(k for k, v in g.items() if v["class_type"] == "UNETLoader"); clip = next(k for k, v in g.items() if v["class_type"] == "CLIPLoader")
    g["kit:slider"] = {"class_type": "LoraLoader", "inputs": {"model": [unet, 0], "clip": [clip, 0], "lora_name": "${slider}", "strength_model": 0.0, "strength_clip": "${slider_strength}"}}
    g["kit:turbo_on"] = {"class_type": "PrimitiveBoolean", "inputs": {"value": "${turbo}"}}
    g["kit:turbo"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": [unet, 0], "lora_name": f"{SUB}/{TURBO}", "strength_model": 1.0}}
    g["kit:model"] = {"class_type": "ComfySwitchNode", "inputs": {"switch": ["kit:turbo_on", 0], "on_false": [unet, 0], "on_true": ["kit:turbo", 0]}}
    g["kit:steps30"] = {"class_type": "PrimitiveInt", "inputs": {"value": 30}}; g["kit:steps8"] = {"class_type": "PrimitiveInt", "inputs": {"value": 8}}
    g["kit:steps"] = {"class_type": "ComfySwitchNode", "inputs": {"switch": ["kit:turbo_on", 0], "on_false": ["kit:steps30", 0], "on_true": ["kit:steps8", 0]}}
    g["kit:te_cfg_full"] = {"class_type": "PrimitiveFloat", "inputs": {"value": 1.7}}; g["kit:te_cfg_turbo"] = {"class_type": "PrimitiveFloat", "inputs": {"value": 1.5}}
    g["kit:te_cfg"] = {"class_type": "ComfySwitchNode", "inputs": {"switch": ["kit:turbo_on", 0], "on_false": ["kit:te_cfg_full", 0], "on_true": ["kit:te_cfg_turbo", 0]}}
    g[te]["inputs"]["clip"] = ["kit:slider", 1]; g[te]["inputs"]["cfg_scale"] = ["kit:te_cfg", 0]
    g[ks]["inputs"]["model"] = ["kit:model", 0]; g[ks]["inputs"]["steps"] = ["kit:steps", 0]
    for v in g.values():
        if v["class_type"] == "SaveAudioAdvanced": v["inputs"]["filename_prefix"] = "audio/music3_kit"
    return g


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--models", default=""); a = ap.parse_args()
    if not a.models:
        sys.path.insert(0, str(ROOT)); from psn import paths
        a.models = paths.models_root() or sys.exit("no models root: pass --models")
    d = Path(a.models) / "loras" / SUB; sliders = []
    for p in sorted(d.glob("ntc_*_fusedqkv.safetensors")):
        m = re.fullmatch(r"ntc_(.+)_step(\d+)_fusedqkv\.safetensors", p.name)
        if not m or m.group(1) not in LABELS: print("skipped", p.name); continue
        sliders.append({"id": m.group(1), "label": LABELS[m.group(1)], "group": "voice" if m.group(1) in VOICE else "genre", "file": f"{SUB}/{p.name}", "step": int(m.group(2)),
                        "bytes": p.stat().st_size, "sha256": sha(p)})
    t = d / TURBO
    if len(sliders) != 16 or not t.is_file(): sys.exit(f"expected 16 sliders and the turbo LoRA in {d}, found {len(sliders)} sliders")
    out = ROOT / "studio" / "music3_kit.json"; old = json.loads(out.read_text()) if out.is_file() else {}
    kit = {"schema": 1, "about": "The Music 3 style kit on the Music page. Generated by scripts/build_music3_kit.py; edit the script, not this file.",
           "graph": "music_music3_kit_api.json", "strength": {"min": 0.0, "max": 1.5, "default": 1.0},
           "sliders": sliders,
           "turbo": {"file": f"{SUB}/{TURBO}", "bytes": t.stat().st_size, "sha256": sha(t), "steps": 8, "te_cfg": 1.5, "full_steps": 30, "full_te_cfg": 1.7},
           "sources": {
               "sliders": {"by": "ntc-ai", "url": "https://huggingface.co/ntc-ai/minimax-music3-particle-sliders", "licence": "MIT", "checked": "2026-11-02",
                           "card_says": "Text-encoder LoRAs for MiniMax Music 3, 16 sliders. Start at strength 1 and compare with 0 on the same caption, lyrics and seed. Negative strength is not a trained opposite. Selection used four short clips per checkpoint."},
               "turbo": {"by": "guillaume127", "url": "https://huggingface.co/guillaume127/MiniMax-Music-3-Turbo-FP8", "licence": "Apache-2.0", "checked": "2026-11-02",
                         "card_says": "LoraLoaderModelOnly 1.0, KSampler 8 steps euler/simple, CFG 1.5-1.7, text encoder cfg_scale 1.5."},
               "base": "MiniMax-Music3 Community License still applies to everything Music 3 makes: commercial use shows the name MiniMax-Music3."},
           "left_out": [{"file": f"{SUB}/fiona-crapple_ck250_fused.safetensors", "why": "named after a real singer and made to imitate her; the studio makes no real singers' voices"},
                        {"file": f"{SUB}/fiona-crapple_reg_ck750_fused.safetensors", "why": "the same LoRA, another checkpoint"}],
           "honest": HONEST, "proof": old.get("proof") or {}}
    out.write_text(json.dumps(kit, indent=1, ensure_ascii=False) + "\n")
    base = json.loads((ROOT / "workflows" / "music3_api.json").read_text())
    (ROOT / "workflows" / "music_music3_kit_api.json").write_text(json.dumps(graph(base), indent=1) + "\n")
    print(f"{len(sliders)} sliders, turbo {kit['turbo']['bytes']} bytes -> {out.relative_to(ROOT)}, workflows/music_music3_kit_api.json")


if __name__ == "__main__": main()
