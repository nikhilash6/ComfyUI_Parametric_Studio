"""Portable model names: a workflow written on one box names its model files the way that box lays them out; on another box the same files sit in different sub-folders or carry a slightly different name.
resolve_names() rewrites each combo value that is not installed to an installed file of the same model. A file whose name is merely close is another model (4B or 9B, high or low noise, clip_vision_g or _h), so it is reported as missing, never guessed. Works on API-format graphs with object_info."""
import difflib, functools, re
SUBSTITUTE = {"minimax_h3_video_vae_int8_convrot.safetensors": "minimax_h3_video_vae_fp16.safetensors", "minimax_music3_text_encoder_pruned_int8_convrot.safetensors": "minimax_music3_text_encoder_pruned_bf16.safetensors", "minimax_music3_text_encoder_pruned_bf16.safetensors": "minimax_music3_text_encoder_pruned_int8_convrot.safetensors"}
MODEL_FILE = re.compile(r"\.(safetensors|sft|ckpt|pt|pth|gguf|bin|onnx|pkl)$")
QUANTIZED = {"int8", "convrot", "nvfp4", "awq"}                                                                  # the file needs ops of its own: not every loader reads these
PRECISION = QUANTIZED | {"fp8", "fp16", "fp32", "bf16", "scaled", "e4m3fn", "e5m2", "fp8mixed", "pruned", "ema", "emaonly"}
PACKAGING = {"comfyui", "comfy"}
RESOLUTION = re.compile(r"^\d{3,4}p$")
CORE_LOADERS = {"UNETLoader", "CheckpointLoaderSimple", "CLIPLoader", "DualCLIPLoader", "TripleCLIPLoader", "QuadrupleCLIPLoader", "VAELoader", "CLIPVisionLoader", "LoraLoader", "LoraLoaderModelOnly", "LoraLoaderBypassModelOnly"}      # read the dtype from the file, so any float precision of a model loads
QUANT_LOADERS = {"UNETLoader", "CheckpointLoaderSimple"}                                                         # also read quantization metadata for any model; CLIP and VAE loaders do it only for named models, which SUBSTITUTE lists
DIR_LOADER = {"diffusion_models": "UNETLoader", "unet": "UNETLoader", "checkpoints": "CheckpointLoaderSimple", "text_encoders": "CLIPLoader", "clip": "CLIPLoader", "vae": "VAELoader", "clip_vision": "CLIPVisionLoader", "loras": "LoraLoader"}
def norm(s): return re.sub(r"[^a-z0-9.]+", "_", str(s).lower().split("/")[-1])
@functools.lru_cache(maxsize=8192)
def _tokens(name):
    return [t for t in re.split(r"[^a-z0-9.]+|(?<!\d)\.|\.(?!\d)", MODEL_FILE.sub("", norm(name))) if t]
def _precision(name): return {t for t in _tokens(name) if t in PRECISION}
def _closest(was, fit):
    """Of several files of one model: the same precision, else a plain float build over another quantization, else the nearest name."""
    return max(fit, key=lambda o: (_precision(o) == _precision(was), not _precision(o) & QUANTIZED, difflib.SequenceMatcher(None, norm(was), norm(o)).ratio()))
def model_key(name):
    """A file name without its precision, packaging and resolution tags or its separators, so flux3-klein_bf16 and flux3_klein_fp8 share a key and 4b and 9b do not."""
    return "".join(t for t in _tokens(name) if t not in PRECISION and t not in PACKAGING and not RESOLUTION.match(t))
def _format(name):
    m = MODEL_FILE.search(norm(name)); ext = m.group(1) if m else ""
    return ext if ext in ("gguf", "onnx") else "torch"
def same_model(a, b):
    """True when two file names are one model: same key, same file format family, and no two different resolutions (480p and 720p are trained apart)."""
    ra, rb = {t for t in _tokens(a) if RESOLUTION.match(t)}, {t for t in _tokens(b) if RESOLUTION.match(t)}
    return model_key(a) == model_key(b) and _format(a) == _format(b) and (not ra or not rb or ra == rb)
def swap_ok(cls, was, now, weight_dtype=None):
    """Whether this loader loads `now` correctly in place of `was`, the same model in another precision. A pack's loader takes the precision as a setting of its own, so it gets no swap."""
    new = _precision(now)
    if new == _precision(was): return True
    if cls not in CORE_LOADERS: return False
    return not (new & QUANTIZED) or (cls in QUANT_LOADERS and weight_dtype in (None, "default"))
def resolve_names(graph, oi, threshold=0.0):
    """-> (graph, report) where report = [{node, input, was, now, score}] for changes and [{... 'now': None}] for values with no installed file of the same model. A caller's threshold can ask for a closer name as well; it never lets in another model. The graph is modified in place."""
    report = []
    for nid, n in graph.items():
        info = oi.get(n["class_type"], {}).get("input", {}); req = {**(info.get("required") or {}), **(info.get("optional") or {})}
        for k, v in list(n["inputs"].items()):
            spec = req.get(k)
            if not spec or not isinstance(v, str) or "${" in v: continue
            opts = spec[0] if isinstance(spec[0], list) else (spec[1].get("options") if len(spec) > 1 and isinstance(spec[1], dict) else None)
            if opts is None or v in opts: continue                                   # an empty list means nothing is installed for this loader: still missing
            if not MODEL_FILE.search(v): continue
            if SUBSTITUTE.get(v) in opts: n["inputs"][k] = SUBSTITUTE[v]; report.append({"node": nid, "input": k, "was": v, "now": SUBSTITUTE[v], "score": 1.0}); continue
            ratio = lambda o: difflib.SequenceMatcher(None, norm(v), norm(o)).ratio()
            fit = [o for o in opts if isinstance(o, str) and same_model(v, o) and swap_ok(n["class_type"], v, o, n["inputs"].get("weight_dtype")) and ratio(o) >= threshold]
            if fit: best = _closest(v, fit); n["inputs"][k] = best; report.append({"node": nid, "input": k, "was": v, "now": best, "score": round(ratio(best), 2)})
            else: report.append({"node": nid, "input": k, "was": v, "now": None, "score": round(max(map(ratio, opts), default=0), 2)})
    return graph, report
def have(files, name, folder=None):
    """The installed file that answers for a model name: that name, or the same model in a precision the loader for `folder` handles. Readiness and resolve_names answer the same way. -> a name in files, or None."""
    b = name.split("/")[-1]
    if b in files: return b
    if SUBSTITUTE.get(b) in files: return SUBSTITUTE[b]
    fit = [x for x in files if same_model(b, x) and swap_ok(DIR_LOADER.get(folder), b, x)]
    return _closest(b, fit) if fit else None
