"""Every model file the shipped graphs, templates, recipes, pipelines, families and features name, with the ComfyUI models folder its loader reads and what uses it.

Standard library only: scripts/get_models.py and the tests use it without any package installed.
A graph names a file in a loader input (CheckpointLoaderSimple.ckpt_name, UNETLoader.unet_name...); LOADER_FOLDERS maps that input to the folder under
ComfyUI/models that the loader lists, read from each node's own source. Values that are placeholders (``${unet}``) or that a node demo filled with whatever
the first file in its list happened to be (IGNORED_INPUTS) are not model uses. The key is the file name without any sub-folder a graph put in front of it,
because the studio resolves names by file name (studio/names.py); generic names such as model.safetensors keep their whole path."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_EXT = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".sft", ".onnx")
_EXT_RX = re.compile(r"\.(safetensors|ckpt|pt|pth|bin|gguf|sft|onnx)$", re.I)

#: (node class, input) -> ComfyUI models folder. From each loader's folder_paths call in ComfyUI 0.43 core and the packs the graphs use.
LOADER_FOLDERS = {
    ("CheckpointLoaderSimple", "ckpt_name"): "checkpoints", ("ImageOnlyCheckpointLoader", "ckpt_name"): "checkpoints",
    ("unCLIPCheckpointLoader", "ckpt_name"): "checkpoints", ("CCSR_Model_Select", "ckpt_name"): "checkpoints",
    ("UNETLoader", "unet_name"): "diffusion_models", ("VAELoader", "vae_name"): "vae", ("PSN_VAELoaderChannels", "vae_name"): "vae",
    ("CLIPLoader", "clip_name"): "text_encoders", ("DualCLIPLoader", "clip_name1"): "text_encoders", ("DualCLIPLoader", "clip_name2"): "text_encoders",
    ("TripleCLIPLoader", "clip_name1"): "text_encoders", ("TripleCLIPLoader", "clip_name2"): "text_encoders", ("TripleCLIPLoader", "clip_name3"): "text_encoders",
    ("HYMotionTextEncoderLoader", "clip_name"): "text_encoders", ("HYMotionTextEncoderLoader", "llm_name"): "text_encoders",
    ("UltraSharkSampler Tiled", "clip_name"): "text_encoders",
    ("CLIPVisionLoader", "clip_name"): "clip_vision", ("StyleModelLoader", "style_model_name"): "style_models",
    ("LoraLoader", "lora_name"): "loras", ("LoraLoaderModelOnly", "lora_name"): "loras", ("LoraLoaderBypassModelOnly", "lora_name"): "loras",
    ("LTXICLoRALoaderModelOnly", "lora_name"): "loras",
    ("ControlNetLoader", "control_net_name"): "controlnet", ("MiniMaxH3FunUnion2LoaderEXPT8", "control_net_name"): "controlnet",
    ("ModelPatchLoader", "name"): "model_patches", ("LatentUpscaleModelLoader", "model_name"): "latent_upscale_models",
    ("UpscaleModelLoader", "model_name"): "upscale_models", ("AudioEncoderLoader", "audio_encoder_name"): "audio_encoders",
    ("FrameInterpolationModelLoader", "model_name"): "frame_interpolation", ("LoadBackgroundRemovalModel", "bg_removal_name"): "background_removal",
    ("LoadMoGeModel", "model_name"): "geometry_estimation", ("SAM3DBody_Loader", "model_file"): "detection",
    ("IPAdapterModelLoader", "ipadapter_file"): "ipadapter", ("IPAdapterSD3Loader", "ipadapter"): "ipadapter",
    ("ADE_AnimateDiffLoaderGen1", "model_name"): "animatediff_models", ("GFPGANRestorer", "model_name"): "face_restoration",
    ("IrisModelLoader", "model_name"): "diffusion_models", ("LoadAndApplyICLightUnet", "model_path"): "unet",
}
#: Inputs a node demo filled with the first entry of its file list, not a model the graph is about.
IGNORED_INPUTS = {("LayerPatcher", "embedder"), ("LayerPatcher", "gates"), ("LayerPatcher", "last_layer")}
#: Names many repositories share; a use of one of these is keyed by its whole path.
GENERIC = re.compile(r"^(model|adapter_model|diffusion_pytorch_model|pytorch_model|denoiser|encoder|decoder|config|last|latest|ema|weights|ckpt|checkpoint|tokenizer|conds|ve|t3_cfg|s3gen)([.-]|$)", re.I)
#: Box-only prefixes some feature code puts in front of a standard folder; the folder after them is where the file goes on any machine.
_LAYOUT_PREFIX = re.compile(r"^(_by_repo/[^/]+/|_complete_pipelines/[^/]+/|_libraries/[^/]+/)")
#: The folders ComfyUI and the studio's tools read, used to tell a folder from a sub-folder in a path.
KNOWN_FOLDERS = {"checkpoints", "diffusion_models", "unet", "vae", "text_encoders", "clip", "clip_vision", "loras", "controlnet", "model_patches",
                 "latent_upscale_models", "upscale_models", "audio_encoders", "frame_interpolation", "background_removal", "geometry_estimation",
                 "detection", "ipadapter", "animatediff_models", "face_restoration", "style_models", "hymotion", "sam3", "TTS", "3d", "motion",
                 "diffusers", "LLM", "embeddings", "face_detection", "face_parsing", "facerestore_models", "liveportrait", "vae_approx", "photomaker", "gligen", "hypernetworks", "audio", "face", "ext_weights"}
#: Python modules whose string literals name the files a studio feature loads (graphs built in code, standalone tools, training bases).
FEATURE_MODULES = ("studio/goals.py", "studio/feature_doctor.py", "studio/feature_dub.py", "studio/feature_finish.py", "studio/feature_motion.py",
                   "studio/feature_oneclick.py", "studio/commercials.py", "studio/words_graph.py", "studio/sampling_graph.py", "studio/recipes_family.py",
                   "studio/gamebuilder/models.py", "studio/foley.py", "studio/train_bases.py", "studio/worldkit/capabilities.py", "studio/llm_tiers.py")
_LITERAL = re.compile(r"[\"']([^\"'\s*{}\[\]]+\.(?:safetensors|ckpt|pth|pt|gguf|sft|onnx|bin))[\"']")
#: Graph folders that are test data, not shipped graphs.
_SKIP_DIRS = ("tests/", ".git/", "node_modules/")


def is_model_name(s):
    if not isinstance(s, str) or not 0 < len(s) < 300 or "${" in s or "\n" in s or not _EXT_RX.search(s): return False
    return not re.search(r"\s", s.replace("\\", "/").rsplit("/", 1)[-1])


_OWNER_REPO = re.compile(r"^([A-Za-z0-9][\w.-]*)__([\w.-]+)$")


def split_path(path):
    """-> (path under the models folder with box-only prefixes removed, Hugging Face repo hinted by an owner__repo folder or None)."""
    raw = str(path).replace("\\", "/").lstrip("./")
    hint = next((f"{m.group(1)}/{m.group(2)}" for seg in raw.split("/")[:-1] if (m := _OWNER_REPO.match(seg))), None)
    p = _LAYOUT_PREFIX.sub("", raw)
    p = re.sub(r"^[A-Za-z0-9][\w.-]*__[\w.-]+/", "", p)
    return p, hint


def key_for(path, hint=None):
    """The manifest key for a file a source names: its file name, or, when the name is generic, its path (or the hinted repo's name and the file name)."""
    p, h = split_path(path)
    hint = h or hint                  # the owner__repo folder in the path is about this file; a card hint is about the whole entry
    name = p.rsplit("/", 1)[-1]
    if not GENERIC.match(name): return name
    if "/" in p: return p
    return f"{hint.split('/')[-1]}/{name}" if hint else name


def folder_of(path, default=None):
    """The models folder a path names (its first known folder segment), else default."""
    p, _ = split_path(path)
    return next((seg for seg in p.split("/")[:-1] if seg in KNOWN_FOLDERS), default)


def api_graphs(obj):
    """Yield every API-format graph ({id: {class_type, inputs}}) inside a JSON document, however it is wrapped."""
    if isinstance(obj, dict):
        vals = [v for v in obj.values() if isinstance(v, dict)]
        if vals and len(vals) == len(obj) and all("class_type" in v for v in vals):
            yield obj
            return
        for v in obj.values(): yield from api_graphs(v)
    elif isinstance(obj, list):
        for v in obj: yield from api_graphs(v)


def graph_files(root=ROOT):
    """Every shipped JSON file that holds at least one API graph, as repo-relative paths."""
    out = []
    for p in sorted(Path(root).rglob("*.json")):
        rel = p.relative_to(root).as_posix()
        if rel.startswith(_SKIP_DIRS) or "/." in rel: continue
        try: doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError): continue
        if next(api_graphs(doc), None) is not None: out.append(rel)
    return out


def graph_uses(doc):
    """[(name as the graph writes it, folder or None)] for one graph document."""
    out = []
    for g in api_graphs(doc):
        for node in g.values():
            cls = node.get("class_type")
            for k, v in (node.get("inputs") or {}).items():
                if not is_model_name(v) or (cls, k) in IGNORED_INPUTS: continue
                out.append((v.replace("\\", "/"), LOADER_FOLDERS.get((cls, k))))
    return out


class Inventory(dict):
    """{key: {"folder", "names", "used_by", "families", "hints"}}. "names" keeps every spelling a source used, box prefixes included, so a
    builder can match it against a download plan; "hints" are Hugging Face repos a source points at (a model card, an owner__repo folder)."""

    def add(self, path, folder, user, family=None, hint=None):
        if not is_model_name(path): return
        p, h = split_path(path)
        k = key_for(path, hint if isinstance(hint, str) else next(iter(hint or []), None))
        row = self.setdefault(k, {"folder": None, "names": set(), "used_by": set(), "families": set(), "hints": set()})
        row["names"].add(str(path).replace("\\", "/"))
        row["used_by"].add(user)
        if family: row["families"].add(family)
        for x in ([hint] if isinstance(hint, str) else list(hint or [])) + [h]:
            if x: row["hints"].add(x)
        folder = folder or next((seg for seg in p.split("/")[:-1] if seg in KNOWN_FOLDERS), None)
        if folder and not row["folder"]: row["folder"] = folder


def dest_of(key, row):
    """Where the file goes under ComfyUI/models: the path a source names when it starts with a known folder, else folder/name. None when no source says."""
    names = sorted((split_path(n)[0] for n in row["names"]), key=lambda n: (n.count("/"), n))
    for n in names:
        if n.split("/")[0] in KNOWN_FOLDERS: return n
    folder = row.get("folder")
    if not folder: return None
    if "/" in key: return f"{folder}/{key}"
    if key in names: return f"{folder}/{key}"           # a source names it bare: the plain folder works for every loader
    sub = [n for n in names if n.rsplit("/", 1)[-1] == key]
    return f"{folder}/{sub[0] if sub else key}"


def _load(root, rel):
    try: return json.loads((Path(root) / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError): return None


def _walk_keys(obj, keys):
    """Yield (key, value) for every dict entry whose key is in keys, anywhere in obj."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys: yield k, v
            yield from _walk_keys(v, keys)
    elif isinstance(obj, list):
        for v in obj: yield from _walk_keys(v, keys)


def _hf_repo(url):
    m = re.match(r"https?://huggingface\.co/(?!datasets/|spaces/)([\w.-]+/[\w.-]+)", str(url or ""))
    return m.group(1) if m else None


def inventory(root=ROOT, features=True):
    """Every model file used anywhere in the repository. Sources, in order: graphs, family templates (studio and ComfyUI's own, as the Families page
    lists them), goals, recipes and LoRA recipes, pipelines, music and voice models, and feature code."""
    root = Path(root)
    inv = Inventory()
    tpl_family = {}
    idx = _load(root, "studio/family_templates/index.json") or {}
    for t in idx.get("templates") or []:
        tpl_family[t.get("name")] = t.get("family")
        for m in t.get("models") or []:
            inv.add(m.get("name", ""), m.get("dir"), f"family:{t.get('family')}/{t.get('name')}", t.get("family"))
    for rel in graph_files(root):
        doc = _load(root, rel)
        stem = rel[:-5]
        fam = tpl_family.get(Path(rel).stem) if rel.startswith("studio/family_templates/") else None
        for name, folder in graph_uses(doc):
            inv.add(name, folder, stem, fam)
    st = (_load(root, "studio/family_status.json") or {}).get("families") or {}
    for fam, row in st.items():
        for t in row.get("templates") or []:
            if not isinstance(t, dict): continue
            for m in t.get("models") or []:
                inv.add(m.get("name", ""), m.get("dir"), f"family:{fam}/{t.get('name')}", fam, row.get("repos"))
    goals = (_load(root, "studio/models_manifest.json") or {}).get("goals") or {}
    for g, row in goals.items():
        for f in row.get("files") or []:
            inv.add(f.get("dest") or f.get("path", ""), (f.get("dest") or "").split("/")[0] or None, f"goal:{g}")
    lr = _load(root, "studio/lora_recipes.json") or {}
    for r in lr.get("loras") or []:
        d = str(r.get("path", "")).replace("\\", "/").rsplit("/", 1)
        inv.add(r.get("path", ""), "loras", f"lora-recipe:{r.get('id')}", r.get("family"), f"*/{d[0]}" if len(d) == 2 else None)
    for rel in ["studio/recipes.json"] + sorted(p.relative_to(root).as_posix() for p in (root / "studio" / "recipe_library").glob("*.json")) \
            + sorted(p.relative_to(root).as_posix() for p in (root / "studio" / "pipelines").glob("*.json")):
        doc = _load(root, rel)
        if doc is None: continue
        tag = "pipeline" if "/pipelines/" in rel else "recipe"
        items = doc.get("recipes") if isinstance(doc, dict) and isinstance(doc.get("recipes"), list) else [doc]
        for item in items:
            rid = (item.get("id") if isinstance(item, dict) else None) or Path(rel).stem
            for k, v in _walk_keys(item, {"lora", "lora_name", "unet", "unet_name", "ckpt", "ckpt_name", "swap", "need"}):
                vals = list(v.keys()) + list(v.values()) if isinstance(v, dict) else (v if isinstance(v, list) else [v])
                for s in vals:
                    folder = "loras" if k.startswith("lora") else ("diffusion_models" if k.startswith("unet") or k == "swap" else ("checkpoints" if k.startswith("ckpt") else None))
                    inv.add(s, folder, f"{tag}:{rid}")
    mm = _load(root, "studio/music_models.json") or {}
    for m in mm.get("models") or []:
        hints = [r for r in (_hf_repo(u) for _, u in (m.get("links") or [])) if r]
        for s in m.get("need") or []: inv.add(s, None, f"music:{m.get('id')}", m.get("family"), hints)
    vm = _load(root, "studio/voice_models.json") or {}
    for m in vm.get("models") or []:
        for s in m.get("files") or []: inv.add(s, folder_of(s, "TTS"), f"voice:{m.get('id')}", "voices", _hf_repo(m.get("card")))
    if features:
        llm = root / "studio" / "llm_tiers.py"
        if llm.exists():
            for repo, f in re.findall(r'"repo":\s*"([\w.-]+/[\w.-]+)",\s*"file":\s*"([^"]+)"', llm.read_text(encoding="utf-8")):
                inv.add(f, "LLM", "feature:studio/llm_tiers.py", "Crew language models", repo)
        for rel in FEATURE_MODULES:
            p = root / rel
            if not p.exists(): continue
            for s in sorted(set(_LITERAL.findall(p.read_text(encoding="utf-8")))):
                inv.add(s, folder_of(s), f"feature:{rel}")
    return inv


if __name__ == "__main__":
    inv = inventory()
    print(len(inv), "files;", sum(1 for r in inv.values() if not r["folder"]), "without a folder")
