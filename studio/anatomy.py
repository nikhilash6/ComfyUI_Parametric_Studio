"""Model Anatomy: what a network is made of, read from the file's header alone. No GPU, no weights loaded.
safetensors: an 8-byte little-endian length, then that many bytes of JSON naming every tensor's dtype, shape and byte range. That is all this reads, plus the few-byte `comfy_quant` descriptors that ComfyUI's quantized files keep beside a layer to say its format.
GGUF: the magic, the key/value metadata and the tensor table, stopping where the tensor data starts.
Anything else (.pt, .pth, .ckpt, .bin are Python pickles; .onnx is a protobuf graph) is listed and not opened: listing a pickle's tensors means running its unpickler, which can run code.
Every number here is counted from the header. What a header can't say is written down in `cant_tell` rather than guessed."""
import hashlib, json, os, re, struct
from collections import Counter, defaultdict

ST_BYTES = {"F64": 8, "F32": 4, "F16": 2, "BF16": 2, "I64": 8, "I32": 4, "I16": 2, "I8": 1, "U8": 1, "U16": 2, "U32": 4, "U64": 8, "BOOL": 1, "F8_E4M3": 1, "F8_E5M2": 1, "F8_E8M0": 1, "F4": 0.5, "F6_E2M3": 0.75, "F6_E3M2": 0.75}
# GGML tensor types: id -> (name, elements per block, bytes per block), as gguf-py's GGML_QUANT_SIZES lists them
GGML = {0: ("F32", 1, 4), 1: ("F16", 1, 2), 2: ("Q4_0", 32, 18), 3: ("Q4_1", 32, 20), 6: ("Q5_0", 32, 22), 7: ("Q5_1", 32, 24), 8: ("Q8_0", 32, 34), 9: ("Q8_1", 32, 40), 10: ("Q2_K", 256, 84), 11: ("Q3_K", 256, 110), 12: ("Q4_K", 256, 144), 13: ("Q5_K", 256, 176), 14: ("Q6_K", 256, 210), 15: ("Q8_K", 256, 292), 16: ("IQ2_XXS", 256, 66), 17: ("IQ2_XS", 256, 74), 18: ("IQ3_XXS", 256, 98), 19: ("IQ1_S", 256, 50), 20: ("IQ4_NL", 32, 18), 21: ("IQ3_S", 256, 110), 22: ("IQ2_S", 256, 82), 23: ("IQ4_XS", 256, 136), 24: ("I8", 1, 1), 25: ("I16", 1, 2), 26: ("I32", 1, 4), 27: ("I64", 1, 8), 28: ("F64", 1, 8), 29: ("IQ1_M", 256, 56), 30: ("BF16", 1, 2), 34: ("TQ1_0", 256, 54), 35: ("TQ2_0", 256, 66), 39: ("MXFP4", 32, 17), 40: ("NVFP4", 64, 36), 41: ("Q1_0", 128, 18)}
MAX_HEADER = 256 << 20
PICKLE_EXT = (".pt", ".pth", ".ckpt", ".bin", ".pkl", ".tar", ".nemo", ".npz")
READ_EXT = (".safetensors", ".sft", ".gguf")
# Metadata worth showing. A whitelist: LoRA metadata can carry training folders, tags and comments, and none of that belongs on a page.
META_KEEP = ("modelspec.architecture", "modelspec.implementation", "modelspec.resolution", "modelspec.prediction_type", "model_type", "model_version", "format", "ss_network_module", "ss_network_dim", "ss_network_alpha", "ss_base_model_version", "ss_v2", "lora_rank", "lora_alpha", "rank", "alpha", "general.architecture", "general.name", "general.file_type", "general.quantization_version", "general.basename", "general.size_label")
KIND_ORDER = ("attention", "mlp", "modulation", "norm", "embedding", "conv", "unclassified", "quant_aux")
LORA_RX = re.compile(r"(?:^|[._])(lora_a|lora_b|lora_down|lora_up|lora_mid|lora\.down|lora\.up|lora_linear_layer\.down|lora_linear_layer\.up)(?:\.weight|\.bias)?$|lora\w*\.(?:down|up)(?:\.weight)?$|\.alpha$|(?:^|[._])(hada_w[12]_[ab]|hada_t[12]|lokr_w[12](?:_[ab])?|lokr_t2)$|\.diff(?:_b)?$|\.dora_scale$", re.I)
AUX_RX = re.compile(r"(?:^|\.)(weight_scale(?:_2)?|input_scale|scale_weight|scale_input|comfy_quant|absmax|quant_map|nested_absmax|nested_quant_map|qzeros|g_idx|wscales|wzeros|smooth_factor(?:_orig)?|wcscales|proj_down|proj_up)$|quant_state\.|\.weight_global_scale$", re.I)
NORM_RX = re.compile(r"(^|_)(norm|ln|layernorm|layer_norm|rmsnorm|group_norm|groupnorm)(\d*|_\w+)?$|norm\d*$|^ln_\w+$|^ln\d*$|^(q|k|query|key|added_q|added_k)_norm$", re.I)
ATTN_PARTS = {"to_q", "to_k", "to_v", "to_out", "to_qkv", "qkv", "q_proj", "k_proj", "v_proj", "o_proj", "out_proj", "qkv_proj", "wq", "wk", "wv", "wo", "query", "key", "value", "add_q_proj", "add_k_proj", "add_v_proj", "to_add_out", "in_proj", "q", "k", "v", "o", "c_attn", "kv", "to_kv", "attn_q", "attn_k", "attn_v", "attn_output", "attn_qkv"}
MLP_PARTS = {"mlp", "ffn", "ff", "feed_forward", "feedforward", "fc1", "fc2", "gate_proj", "up_proj", "down_proj", "w1", "w2", "w3", "ffn_up", "ffn_down", "ffn_gate", "ff_context", "c_fc", "dense_h_to_4h", "dense_4h_to_h", "experts", "ffn_up_exps", "ffn_down_exps", "ffn_gate_exps", "shared_experts", "img_mlp", "txt_mlp", "wi", "wi_0", "wi_1"}
MOD_RX = re.compile(r"modulation|adaln|ada_ln|adanorm|scale_shift|_mod$|^mod$", re.I)
EMB_RX = re.compile(r"embed|embd|embedding|^wte$|^wpe$|^tok_|^token_|shared$", re.I)
KNOWN_TOP = {"model.diffusion_model": "denoiser", "first_stage_model": "VAE", "cond_stage_model": "text encoder", "conditioner": "text encoders", "text_encoders": "text encoders", "vae": "VAE", "model_ema": "EMA copy"}


def _known(name):
    """A label for a top-level group, only where the key prefix is a checkpoint-format convention."""
    for k, v in KNOWN_TOP.items():
        if name == k or name.startswith(k + "."): return v
    return None


def sid(rel: str) -> str: return hashlib.sha1(rel.encode()).hexdigest()[:12]


# ---------- readers
def read_safetensors(path):
    """-> (tensors {name: (dtype, shape, nbytes, start)}, metadata, header length, comfy_quant {layer: format}). Reads the header and the few-byte comfy_quant descriptors only."""
    with open(path, "rb") as f:
        raw = f.read(8)
        if len(raw) < 8: raise ValueError("shorter than a safetensors header")
        n = struct.unpack("<Q", raw)[0]
        if not 2 <= n <= MAX_HEADER: raise ValueError(f"header length {n} is not plausible, so this is not a safetensors file")
        h = json.loads(f.read(n))
        meta = h.pop("__metadata__", None) or {}
        tensors = {}
        for k, v in h.items():
            a, b = v["data_offsets"]; tensors[k] = (v["dtype"], list(v["shape"]), b - a, a)
        cq = {}
        for k, (dt, shape, nb, a) in tensors.items():
            if k.endswith(".comfy_quant") and dt == "U8" and nb <= 1024:
                f.seek(8 + n + a)
                try: cq[k[: -len(".comfy_quant")]] = json.loads(f.read(nb).decode("utf8", "replace"))
                except ValueError: cq[k[: -len(".comfy_quant")]] = {"format": "unreadable"}
    return tensors, meta, n, cq


class _R:
    def __init__(self, f): self.f = f
    def take(self, n):
        b = self.f.read(n)
        if len(b) != n: raise ValueError("GGUF header ends early")
        return b
    def u32(self): return struct.unpack("<I", self.take(4))[0]
    def u64(self): return struct.unpack("<Q", self.take(8))[0]
    def s(self):
        n = self.u64()
        if n > 1 << 24: raise ValueError("GGUF string length is not plausible")
        return self.take(n).decode("utf8", "replace")
    SCALAR = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
    def value(self, t, keep=True):
        if t in self.SCALAR: fmt = self.SCALAR[t]; return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]
        if t == 8: return self.s()
        if t == 9:
            it, n = self.u32(), self.u64()
            if it in self.SCALAR: self.take(struct.calcsize(self.SCALAR[it]) * n); return f"[{n} values]"
            for _ in range(n): self.value(it, False)
            return f"[{n} values]"
        raise ValueError(f"unknown GGUF value type {t}")


def read_gguf(path):
    """-> (tensors {name: (type name, shape, nbytes, offset)}, metadata, bytes read). Stops at the end of the tensor table."""
    with open(path, "rb") as f:
        r = _R(f)
        if r.take(4) != b"GGUF": raise ValueError("no GGUF magic")
        ver = r.u32()
        if ver < 2: raise ValueError(f"GGUF version {ver} is too old to read here")
        nt, nkv = r.u64(), r.u64(); meta = {"gguf.version": ver}
        for _ in range(nkv):
            k = r.s(); t = r.u32(); v = r.value(t); meta[k] = v
        tensors = {}
        for _ in range(nt):
            name = r.s(); nd = r.u32(); dims = [r.u64() for _ in range(nd)]; t = r.u32(); off = r.u64()
            tname, blk, bb = GGML.get(t, (f"type{t}", 0, 0)); el = 1
            for d in dims: el *= d
            tensors[name] = (tname, list(reversed(dims)), (el // blk) * bb if blk else 0, off)
        return tensors, meta, f.tell()


# ---------- what a tensor is
ATTN_SURE = {"to_q", "to_k", "to_v", "to_out", "to_qkv", "qkv", "q_proj", "k_proj", "v_proj", "o_proj", "qkv_proj", "add_q_proj", "add_k_proj", "add_v_proj", "to_add_out", "in_proj", "c_attn", "to_kv", "kv_proj"}
MLP_SURE = {"fc1", "fc2", "gate_proj", "up_proj", "down_proj", "c_fc", "dense_h_to_4h", "dense_4h_to_h", "experts", "shared_experts", "ffn_up", "ffn_down", "ffn_gate", "ffn_up_exps", "ffn_down_exps", "ffn_gate_exps", "gate_up_proj"}
ATTN_MAYBE = {"q", "k", "v", "o", "wq", "wk", "wv", "wo", "query", "key", "value", "out_proj", "kv", "proj_q", "proj_k", "proj_v"}
MLP_MAYBE = {"w1", "w2", "w3", "wi", "wi_0", "wi_1", "ff", "ff_context"}
STRIP = ("weight", "bias", "scale", "gamma", "beta", "weight_g", "weight_v", "alpha")


def kind_of(name, shape):
    """Attention, MLP, modulation, norm, embedding or conv, by the layer's own name. The innermost name that says for sure wins; q, k, wo and the like only count when nothing around them says otherwise."""
    if AUX_RX.search(name): return "quant_aux"
    mods = [p for p in name.lower().split(".") if p not in STRIP]
    last = mods[-1] if mods else ""
    if any(EMB_RX.search(p) for p in mods[-2:]) or name.lower().startswith(("token_embd", "tok_embeddings", "wte", "wpe")): return "embedding"
    if any(MOD_RX.search(p) for p in mods) or (len(mods) > 1 and NORM_RX.search(mods[-2]) and last == "linear"): return "modulation"
    if NORM_RX.search(last) or (len(mods) > 1 and NORM_RX.search(mods[-2]) and last in ("key_norm", "query_norm")): return "norm"
    for p in reversed(mods):
        if "attn" in p or "attention" in p or p in ATTN_SURE: return "attention"
        if p in MLP_SURE or "mlp" in p or "ffn" in p or "feed_forward" in p or "feedforward" in p or "densereludense" in p: return "mlp"
    for p in reversed(mods):
        if p in ATTN_MAYBE: return "attention"
        if p in MLP_MAYBE: return "mlp"
    if len(shape) >= 4 or (len(shape) == 3 and any("conv" in p for p in mods)): return "conv"
    return "unclassified"


def _quant_factor(name, dt, shape, tensors, cq):
    """How many weights one stored element holds, and where that number came from."""
    if dt not in ("U8", "I8", "I32"): return 1, None
    layer = name[: -len(".weight")] if name.endswith(".weight") else None
    fmt = ((cq.get(layer) or {}).get("format") or "") if layer else ""
    if fmt:
        f = fmt.lower()
        if "fp4" in f or "int4" in f or f in ("mxfp4", "nvfp4"): return 2, f"{fmt}, from the layer's comfy_quant descriptor"
        return 1, f"{fmt}, from the layer's comfy_quant descriptor"
    if layer and dt == "U8":
        sc = tensors.get(layer + ".weight_scale")
        if sc and sc[1] and shape and sc[0].startswith("F8") and sc[1][-1] * 8 == shape[-1]: return 2, "two 4-bit weights per byte, inferred from the 16-weight block scales beside it"
        if name + ".quant_state.bitsandbytes__nf4" in tensors or name + ".quant_state.bitsandbytes__fp4" in tensors: return 2, "bitsandbytes 4-bit, two weights per byte, from its quant_state key"
    if name.endswith(".qweight") and dt in ("I8", "U8") and name[: -len("qweight")] + "wscales" in tensors: return 2, "two 4-bit weights per byte, inferred from the wscales beside it"
    return 1, None


def _numel(shape):
    n = 1
    for d in shape: n *= int(d)
    return n


# ---------- the tree
def _strip_common(names):
    """Key components every name starts with, such as model.diffusion_model."""
    if not names: return []
    split = [n.split(".") for n in names]; common = []
    for parts in zip(*split):
        if all(p == parts[0] for p in parts) and not parts[0].isdigit(): common.append(parts[0])
        else: break
    if any(len(s) <= len(common) for s in split): common = common[: max(0, min(len(s) for s in split) - 1)]
    return common


def _node(): return {"w": 0, "b": 0, "t": 0, "c": {}, "k": Counter(), "leaf": None}


def build_tree(rows, skip):
    root = _node()
    for name, shape, dt, w, b, kind in rows:
        parts = name.split(".")[skip:] or [name]; n = root
        n["w"] += w; n["b"] += b; n["t"] += 1; n["k"][kind] += w
        for i, p in enumerate(parts):
            n = n["c"].setdefault(p, _node()); n["w"] += w; n["b"] += b; n["t"] += 1; n["k"][kind] += w
            if i == len(parts) - 1: n["leaf"] = (shape, dt, kind)
    return root


def _sig(n):
    """The structure under a node: names, shapes and dtypes, so identical blocks are stored once."""
    if not n["c"]: return ("L",) + (tuple(n["leaf"][0]), n["leaf"][1]) if n["leaf"] else ("L",)
    return tuple((k, _sig(v)) for k, v in sorted(n["c"].items()))


def _order(keys):
    return sorted(keys, key=lambda k: (0, int(k)) if k.isdigit() else (1, k))


def pack(n, name="", depth=0, budget=None):
    """The node as the page wants it: n name, w weights, b bytes, t tensors, k kinds (groups only), c children, s 'same as' for repeated blocks, r repeat count, x [shape, dtype] for a tensor."""
    budget = budget if budget is not None else [4000]
    # a chain of single children collapses into one label: model.diffusion_model.x -> one node
    while len(n["c"]) == 1 and not n["leaf"]:
        (k, v), = n["c"].items(); name = f"{name}.{k}" if name else k; n = v
    out = {"n": name, "w": n["w"], "b": n["b"], "t": n["t"]}
    if depth <= 2: out["k"] = {k: v for k, v in n["k"].items() if v}
    if n["leaf"] and not n["c"]: out["x"] = [n["leaf"][0], n["leaf"][1]]; out["kind"] = n["leaf"][2]; return out
    keys = _order(n["c"]); numeric = [k for k in keys if k.isdigit()]
    kids, seen = [], {}
    if len(numeric) >= 2: out["r"] = len(numeric)
    for k in keys:
        v = n["c"][k]
        if budget[0] <= 0: out["more"] = out.get("more", 0) + 1; continue
        if k.isdigit() and len(numeric) >= 2:
            s = _sig(v)
            if s in seen:
                kids.append({"n": k, "w": v["w"], "b": v["b"], "t": v["t"], "s": seen[s]}); budget[0] -= 1; continue
            seen[s] = k
        budget[0] -= 1; kids.append(pack(v, k, depth + 1, budget))
    if len(numeric) >= 2: out["u"] = len(seen)
    out["c"] = kids
    return out


# ---------- LoRA
def _lora_module(name):
    m = re.match(r"(.*?)[._](lora_A|lora_B|lora_down|lora_up|lora_mid|lora\.down|lora\.up|lora_linear_layer\.down|lora_linear_layer\.up)(?:\.weight|\.bias)?$", name, re.I)
    if m: return m.group(1), m.group(2).lower().replace(".", "_")
    m = re.match(r"(.*lora\w*)\.(down|up)(?:\.weight)?$", name, re.I)
    if m: return m.group(1), "lora_" + m.group(2).lower()
    m = re.match(r"(.*)\.(alpha|diff|diff_b|dora_scale|hada_w[12]_[ab]|hada_t[12]|lokr_w[12](?:_[ab])?|lokr_t2)$", name, re.I)
    if m: return m.group(1), m.group(2).lower()
    return None, None


def _target(module):
    """The layer a LoRA module adapts, without its block number: blocks.12.attn.qkv -> attn.qkv; kohya's lora_unet_..._0_attn1_to_q -> attn1_to_q."""
    if "." in module:
        parts = module.split("."); idx = [i for i, p in enumerate(parts) if p.isdigit()]
        return ".".join(parts[idx[-1] + 1:]) if idx and idx[-1] < len(parts) - 1 else ".".join(parts[-2:])
    m = re.search(r".*_\d+_([a-z][a-z0-9_]*)$", module)
    return m.group(1) if m else module.split("_", 2)[-1]


def lora_facts(tensors):
    mods = defaultdict(dict)
    for name, (dt, shape, nb, _) in tensors.items():
        mod, part = _lora_module(name)
        if mod: mods[mod][part] = shape
    ranks, targets, kinds, layouts = Counter(), Counter(), Counter(), Counter()
    for mod, parts in mods.items():
        down = parts.get("lora_a") or parts.get("lora_down") or parts.get("lora_linear_layer_down")
        if down: ranks[int(down[0])] += 1; layouts["LoRA (down and up matrices)"] += 1
        elif any(p.startswith("hada") for p in parts): layouts["LoHa"] += 1
        elif any(p.startswith("lokr") for p in parts): layouts["LoKr"] += 1
        elif "diff" in parts: layouts["full weight difference"] += 1
        targets[_target(mod)] += 1; kinds[kind_of(mod + ".weight", [])] += 1
    alpha_tensors = sum(1 for p in mods.values() if "alpha" in p)
    return {"modules": len(mods), "ranks": sorted(([r, c] for r, c in ranks.items()), key=lambda x: -x[1]), "targets": [[t, c] for t, c in targets.most_common(40)], "more_targets": max(0, len(targets) - 40), "kinds": {k: v for k, v in kinds.items()}, "layouts": dict(layouts), "alpha_tensors": alpha_tensors}


# ---------- one file
def _meta_shown(meta):
    out = {}
    for k in META_KEEP:
        v = meta.get(k)
        if v is not None and len(str(v)) <= 120: out[k] = v
    cfg = meta.get("config")
    if isinstance(cfg, str) and len(cfg) < 400000:
        try: c = json.loads(cfg)
        except ValueError: c = None
        names = []
        def walk(o):
            if isinstance(o, dict):
                if isinstance(o.get("_class_name"), str): names.append(o["_class_name"])
                for v in o.values(): walk(v)
        walk(c)
        if names: out["config._class_name"] = ", ".join(dict.fromkeys(names))
    return out


def analyse(path, rel=None):
    """Everything this page says about one file, from its header."""
    ext = os.path.splitext(path)[1].lower(); size = os.path.getsize(path)
    base = {"file": os.path.basename(path), "rel": rel or os.path.basename(path), "size": size, "format": ext.lstrip(".")}
    if ext not in READ_EXT:
        why = "a Python pickle: listing its tensors means running its unpickler, which can run code, so this page doesn't open it" if ext in PICKLE_EXT else "not safetensors or GGUF, so there is no tensor header to read"
        return {**base, "read": False, "why": why}
    try:
        if ext == ".gguf": tensors, meta, hb = read_gguf(path); cq = {}; fmt = "gguf"
        else: tensors, meta, hb, cq = read_safetensors(path); fmt = "safetensors"
    except (OSError, ValueError, KeyError, struct.error) as e:
        return {**base, "read": False, "why": f"the header didn't read: {str(e)[:160]}"}
    rows, notes = [], Counter(); dtypes = defaultdict(lambda: [0, 0, 0])
    for name, (dt, shape, nb, _) in tensors.items():
        el = _numel(shape); f, why = _quant_factor(name, dt, shape, tensors, cq); kind = kind_of(name, shape)
        w = 0 if kind == "quant_aux" else el * f
        if why: notes[why] += 1
        d = dtypes[dt]; d[0] += 1; d[1] += w; d[2] += nb
        rows.append((name, shape, dt, w, nb, kind))
    names = [r[0] for r in rows]; common = _strip_common(names)
    tree = pack(build_tree(rows, len(common)))
    kinds = Counter(); kbytes = Counter()
    for r in rows: kinds[r[5]] += r[3]; kbytes[r[5]] += r[4]
    weights = sum(r[3] for r in rows); data = sum(r[4] for r in rows)
    is_lora = sum(1 for n in names if LORA_RX.search(n)) > 0.5 * max(1, len(names))
    shown = _meta_shown(meta)
    arch = shown.get("modelspec.architecture") or shown.get("general.architecture") or shown.get("config._class_name") or shown.get("model_type")
    groups = [{"n": c["n"], "w": c["w"], "b": c["b"], "t": c["t"], "k": c.get("k", {}), "r": c.get("r"), "label": _known(".".join(common + [c["n"]]))} for c in (tree.get("c") or [])]
    widths = Counter(r[1][-1] for r in rows if len(r[1]) == 2 and r[5] in ("attention", "mlp") and r[1][-1] > 1)
    cant = []
    if not arch: cant.append("The header names no architecture. The key names are all there is, so this page doesn't name one.")
    if kinds["unclassified"] > 0.05 * max(1, weights): cant.append(f"{kinds['unclassified'] / max(1, weights):.0%} of the weights sit in layers whose names don't say attention or MLP, such as fused or input layers, so they are left unsplit.")
    if any("comfy_quant" in k for k in notes) or notes: cant.append("Quantized layers: the weight count is worked out from the storage format named beside each layer; bytes are what the file stores.")
    if "U8" in dtypes and not notes: cant.append("Some tensors are raw bytes (U8) with no format descriptor, so whether they pack several weights per byte isn't stated; each byte is counted as one.")
    cant.append("How the width splits into attention heads isn't in the shapes. Only the metadata could say, and only when it does.")
    if is_lora: cant.append("A LoRA's alpha, and so its real strength, is stored as a number in the data, not in the header; this page doesn't read values.")
    out = {**base, "read": True, "format": fmt, "header_bytes": hb, "tensors": len(rows), "weights": weights, "data_bytes": data, "prefix": ".".join(common),
           "dtypes": sorted(([k, *v] for k, v in dtypes.items()), key=lambda x: -x[3]), "kinds": {k: [kinds[k], kbytes[k]] for k in KIND_ORDER if kinds[k] or kbytes[k]},
           "groups": groups, "tree": tree, "meta": shown, "arch": arch, "quant_notes": [[k, v] for k, v in notes.most_common()], "widths": [[w, c] for w, c in widths.most_common(3)], "cant_tell": cant, "lora": lora_facts(tensors) if is_lora else None}
    return out


def summary(a):
    """The row the list and the compare picker need, without the tree."""
    keys = ("id", "file", "rel", "size", "format", "read", "why", "tensors", "weights", "data_bytes", "arch", "family", "function", "gb", "also", "same_header_as")
    s = {k: a.get(k) for k in keys if a.get(k) is not None}
    if a.get("read"):
        s["dtype"] = a["dtypes"][0][0] if a["dtypes"] else None; s["kinds"] = {k: round(v[0] / a["weights"], 3) for k, v in a["kinds"].items() if a["weights"] and v[0] / a["weights"] >= 0.001}
        s["blocks"] = max([g.get("r") or 0 for g in a["groups"]] or [0])
        if a.get("lora"): s["lora_rank"] = a["lora"]["ranks"][0][0] if a["lora"]["ranks"] else None; s["lora"] = True
    return s
