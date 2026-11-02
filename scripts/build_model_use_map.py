"""Every file downloaded on 2026-11-01 against what uses it. Reads the fetch plans, the disk, ComfyUI's model folders and every graph the studio can reach, and writes one row per file.
A file's status is earned: rendered (a graph naming it finished on this box), graph (a graph names it, not run), reachable (a loader can see it, nothing uses it), unreachable (nothing can see it), not_on_disk.
What a model does comes from its model card when the card was read (--cards), and says so when it was not. Run: python scripts/build_model_use_map.py --out worker/MODEL_USE_MAP_2026-11-01.tsv"""
import argparse, csv, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PLANS = ("3d_models", "three", "3d2", "small", "families", "fibo", "hyenc", "ming", "layout", "prio")
LATER_PLANS = ("planned", "media_models", "support")
COLUMNS = ["file", "gb", "repo", "path_in_repo", "on_disk", "disk_path", "function", "family", "does", "does_source", "status", "used_by", "proof", "next_step", "sha"]
#: Non-ComfyUI runners that read a model folder directly: what the file is read by, from each tool's own launcher.
RUNNERS = [("_complete_pipelines/SAM-3D-Objects/", "tool sam3d-objects, World Kit prop route (worldkit/tools.py sam3d_objects)"),
           ("3d/sam-3d-objects/", "tool sam3d-objects, World Kit prop route (worldkit/tools.py sam3d_objects)"),
           ("3d/SkinTokens/", "tool skintokens, World Kit rig step (worldkit/tools.py skintokens)"),
           ("UniRig/checkpoints/", "tool unirig, the 3D page rig route (worldkit/tools.py unirig)"),
           ("motion/kimodo/", "tool kimodo, World Kit motion step (worldkit/tools.py kimodo)"),
           ("motion/text-encoders/", "tool kimodo text encoder, World Kit motion step (worldkit/tools.py kimodo)"),
           ("_complete_pipelines/TripoSR/", "runner triposr_image.py, 3D page and World Kit prop route"),
           ("3d/shap-e/", "runner shap_e_text.py, 3D page and World Kit prop route"),
           ("AniGen/ckpts/anigen/ss_flow_solo", "tool anigen, 3D page"), ("AniGen/ckpts/anigen/slat_flow_auto", "tool anigen, 3D page"), ("AniGen/ckpts/anigen/ss_dae", "tool anigen, 3D page"), ("AniGen/ckpts/anigen/slat_dae", "tool anigen, 3D page"), ("AniGen/ckpts/dsine/", "tool anigen, 3D page"), ("AniGen/ckpts/vgg/", "tool anigen, 3D page"),
           ("3d/moge-vitl/", "tool sam3d-objects (reads MoGe for its depth), World Kit prop route"),
           ("AniGen/ckpts/dinov2/", "tool sam3d-objects (reads this DINOv2), World Kit prop route")]
#: Why a file is still not used, written after trying it. A pattern on the path decides the row's next step.
WHY_UNUSED = [("fiona-crapple", "HOLD: the name reads like a real singer (inference, no card read): not shown publicly until the founder has checked it"), ("ClipProj-celeb", "HOLD: named for celebrities: not shown publicly"),
              ("/TTS/", "owned by feat/voice"), ("TTS/", "owned by feat/voice"), ("speech_enhancement/", "owned by feat/voice"), ("/motion/", "owned by feat/motion"), ("liveportrait/", "owned by feat/motion"),
              ("AniGen/ckpts/anigen/ss_flow_duet", "AniGen duet variant: the runner uses ss_flow_solo, this one is not run."), ("AniGen/ckpts/anigen/ss_flow_epic", "AniGen epic variant: the runner uses ss_flow_solo, this one is not run."), ("AniGen/ckpts/anigen/slat_flow_control", "AniGen control variant: the runner uses slat_flow_auto, this one is not run."),
              ("Pixal3D/", "Pixal3D: the ComfyUI file pixal3d_int8_convrot is not on disk and the standalone tool lacks its shape and texture decoders. Needs a fetch."),
              ("TRELLIS-2-4B/", "TRELLIS.2 raw per-stage weights: ComfyUI uses its single file trellis_2_int8_convrot, which is proven. These are only for a standalone runner, none exists here."),
              ("microsoft/ckpts/", "TRELLIS v1 weights: no runner here."), ("TRELLIS-image-large/", "TRELLIS v1 weights: no runner here."),
              ("Matrix-3D/", "Matrix-3D: no runner for its panorama video and LRM checkpoints. Not run."),
              ("3d/instantmesh/", "InstantMesh: its code needs Zero123++ weights that are not on disk. Not run."),
              ("Stable-Fast-3D/", "Stable-Fast-3D: its sf3d code is not on this box. Not run."),
              ("PartCrafter/", "PartCrafter: its VAE weights did not land (config only) and torch_cluster is not in the venv. Not run."),
              ("MIDI-3D", "MIDI-3D: only the image encoders landed; transformer and VAE are markers. Needs a fetch."),
              ("UniRig/", "UniRig: no venv; spconv, torch_scatter, torch_cluster missing. Needs a pip into a new venv, founder's call."),
              ("veichta__zipsplat", "ZipSplat: a tar with no runner here. Not run."),
              ("FitDiT/", "FitDiT: virtual try-on code is not on this box. Not run."),
              ("ipadapter/", "IP-Adapter: needs a pack that is not on live ComfyUI (Pack Lab first)."), ("geometry_estimation/Fast3R", "Fast3R: no node or runner here. Not run."), ("geometry_estimation/VGGT", "VGGT: no node or runner here. Not run."), ("geometry_estimation/STream3R", "STream3R: no node or runner here. Not run."),
              ("hunyuan3d-paintpbr", "Hunyuan3D paint: no node or runner for the texture model here. Not run."), ("hunyuan3d-dit-v2-1", "Hunyuan3D 2.1 raw checkpoint: ComfyUI reads the converted repackaged files instead. Not run."), ("hunyuan3d-vae-v2-1", "Hunyuan3D 2.1 raw VAE: same."),
              ("LDM3D-4C/pipeline/unet", "LDM3D-4C: wrapped for its family instance; level render recorded earlier."),
              ("flownet", "Frame-interpolation weights for a pack not on live ComfyUI."), ("rife", "RIFE: the frame-interpolation template picks FILM, so these have no graph yet.")]


def read_plan(path):
    with open(path, newline="") as f: return list(csv.DictReader(f, delimiter="\t"))


def load_plans(workbench, names=PLANS):
    """One row per unique file (sha, else repo+path), keeping the first plan that named it."""
    seen, out = set(), []
    for n in names:
        p = Path(workbench) / f"fetch_{n}_now_plan.tsv"
        if not p.exists(): continue
        for r in read_plan(p):
            k = r.get("sha") or (r.get("repo"), r.get("path"))
            if k in seen: continue
            seen.add(k); out.append({**r, "plan": n})
    return out


def comfy_folders(yaml_path):
    """{relative folder: model type} that ComfyUI's extra_model_paths.yaml lists. Line-based so it needs no yaml module."""
    out, cur = {}, None
    for ln in open(yaml_path):
        m = re.match(r"^\s{4}([\w-]+):\s*(\|)?\s*(\S.*)?$", ln)
        if m and m.group(1) != "base_path":
            cur = m.group(1)
            if m.group(3): out[m.group(3).strip().rstrip("/")] = cur
            continue
        m = re.match(r"^\s{8}(\S.*)$", ln)
        if m and cur: out[m.group(1).strip().rstrip("/")] = cur
    return out


def reach(rel, folders):
    """The ComfyUI model type that can see this path, or ''."""
    d = os.path.dirname(rel)
    while d:
        if d in folders: return folders[d]
        d = os.path.dirname(d)
    return ""


def on_disk(models_root, row):
    """-> (exists at full size, its real path). A plan row may name a link; a size under 90% of the plan's is a partial, not a model."""
    p = Path(models_root) / row["rel"]
    try:
        if p.is_file():
            want = int(row.get("bytes") or 0)
            return (not want or p.stat().st_size >= want * 0.9), str(p)
    except (OSError, ValueError): pass
    return False, str(p)


def _walk_strings(x):
    if isinstance(x, str): yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from _walk_strings(v)
    elif isinstance(x, list):
        for v in x: yield from _walk_strings(v)


def graph_names(path):
    """The model-looking file names inside one graph file."""
    try: d = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError): return set()
    return {os.path.basename(s) for s in _walk_strings(d) if len(s) < 400 and re.search(r"\.(safetensors|ckpt|pt|pth|bin|gguf|sft|onnx)$", s, re.I)}


#: Weight files named the same in many repos. A graph or need naming one says nothing about this copy unless the whole path matches.
GENERIC = re.compile(r"^(model|diffusion_pytorch_model|pytorch_model|denoiser|encoder_final|decoder_final|last|ema|skin|skeleton|weights|ckpt|checkpoint)([.-]|$)", re.I)


def need_paths(repo_root):
    """{path under the models folder: where it is used} for World Kit's needs, which name whole paths."""
    src = (Path(repo_root) / "studio" / "worldkit" / "capabilities.py")
    if not src.exists(): return {}
    return {path: f"World Kit need {key}" for key, path in re.findall(r'"(\w+)": \{"label"[^\n]*?\("([^"]+\.(?:safetensors|ckpt|pt|pth|bin))"', src.read_text())} | {path: "World Kit capabilities" for path in re.findall(r'\("([^"]+\.(?:safetensors|ckpt|pt|pth|bin))", ', src.read_text()) if "/" in path}


def index_uses(repo_root, template_dir=None):
    """{file name: [where it is used]} from the studio's graphs, family metadata, World Kit's needs and the shipped ComfyUI templates."""
    uses = {}
    def add(name, where):
        uses.setdefault(os.path.basename(name), [])
        if where not in uses[os.path.basename(name)]: uses[os.path.basename(name)].append(where)
    studio = Path(repo_root) / "studio"
    st = json.load(open(studio / "family_status.json"))["families"]
    for fam, r in st.items():
        for t in r.get("templates") or []:
            for m in t.get("models") or []: add(m["name"], f"family {fam} / {t['name']}")
    try:
        for t in json.load(open(studio / "family_templates" / "index.json"))["templates"]:
            for m in t.get("models") or []: add(m["name"], f"family {t['family']} / {t['name']}")
    except (OSError, ValueError, KeyError): pass
    for p in sorted((studio / "family_templates").glob("*.json")):
        if p.name != "index.json":
            for n in graph_names(p): add(n, f"studio template {p.stem}")
    for p in sorted((Path(repo_root) / "workflows").glob("*.json")):
        for n in graph_names(p): add(n, f"workflow {p.stem}")
    try:
        man = json.load(open(studio / "models_manifest.json"))["goals"]
        for g, r in man.items():
            for f in r.get("files") or []: add(f.get("dest") or f.get("name") or "", f"goal {g}")
    except (OSError, ValueError, KeyError): pass
    for row in json.load(open(studio / "lora_recipes.json"))["loras"]: add(row["path"], f"LoRA recipe {row['id']}")
    for p in sorted((studio / "recipe_library").glob("*.json")):
        for n in graph_names(p): add(n, f"recipe list {p.stem}")
    try:
        for n in graph_names(studio / "recipes.json"): add(n, "recipes.json")
    except OSError: pass
    src = (studio / "worldkit" / "capabilities.py").read_text() if (studio / "worldkit" / "capabilities.py").exists() else ""
    for key, path in re.findall(r'"(\w+)": \{"label"[^\n]*?\("([^"]+\.(?:safetensors|ckpt|pt|pth|bin))"', src): add(path, f"World Kit need {key}")
    for path in re.findall(r'\("([^"]+\.(?:safetensors|ckpt|pt|pth|bin))", ', src): add(path, "World Kit capabilities")
    if template_dir and os.path.isdir(template_dir):
        for p in sorted(Path(template_dir).glob("*.json")):
            if p.name.startswith("api_"): continue
            for n in graph_names(p): add(n, f"ComfyUI template {p.stem}")
    return uses


def proof_index(all_json, status):
    """{template name: 'proof text'} for templates that finished on this box, from the watcher's results and the recorded media."""
    out = {}
    for slug, rec in (all_json.get("families") or {}).items():
        for t in rec.get("tries") or []:
            if t.get("status") == "done" and t.get("files"): out[t["template"]] = f"rendered {slug}/{t['template']} ({t.get('wall_s')} s)"
    for fam, r in status.items():
        for m in r.get("media") or []:
            if m.get("tpl") and m.get("own") and not m.get("library"): out.setdefault(m["tpl"], f"rendered {fam}/{m['tpl']} ({m.get('src')})")
    return out


#: A tool run proves the files that tool loaded, not every file in its folder. {runner label's start: (id in model3d_proof.json, path parts of what it loaded)}
TOOL_PROOF = {"tool sam3d-objects": ("sam3d_objects", ("ss_generator", "slat_generator", "slat_decoder_mesh", "slat_decoder_gs", "ss_decoder", "ss_encoder")),
              "tool skintokens": ("skintokens", ("grpo_1400.ckpt", "skin_vae_2_10_32768/last.ckpt")),
              "tool unirig": ("unirig", ("skeleton_model.ckpt", "skin_model.ckpt")),
              "tool anigen": ("anigen", ("ss_flow_solo/", "slat_flow_auto/", "slat_dae/ckpts/decoder_final", "ss_dae/ckpts/decoder_final", "dinov2_vitl14_reg4", "dsine.pt")),
              "runner triposr_image": ("triposr", ("TripoSR/model.ckpt",)),
              "runner shap_e_text": ("shap_e", ("shap-e/",))}


def tool_proof(rel, used, proofs3d):
    """'proof text' when a tool whose run was recorded and looked at loaded this file."""
    for label, (tid, parts) in TOOL_PROOF.items():
        if any(u.startswith(label) for u in used) and any(x in rel for x in parts) and tid in proofs3d:
            p = proofs3d[tid]; return f"tool run {tid} ({p.get('seconds')} s, {p.get('sheet') or 'no sheet'})"
    return ""


def load_viewed(path):
    """{template or tool id: what looking at the result showed} from the ledger. A run with no line here has not been looked at."""
    out = {}
    if path and os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            if ln.strip() and not ln.startswith("#"): k, _, v = ln.rstrip("\n").partition("\t"); out[k] = v
    return out


def family_of(row, status_families):
    m = re.match(r"_complete_pipelines/([^/]+)/", row.get("rel", ""))
    if m: return m.group(1)
    repo = row.get("repo", "").lower()
    for fam, r in status_families.items():
        if any(x.lower() == repo for x in r.get("repos") or []): return fam
    return ""


def first_paragraph(text):
    """The first plain sentence of a model card, with its front matter and markup removed."""
    t = re.sub(r"^---\n.*?\n---\n", "", text or "", flags=re.S)
    for p in re.split(r"\n\s*\n", t):
        p = re.sub(r"<[^>]+>|!\[[^\]]*\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)", r"\1", p).strip()
        if len(p) < 40 or p.startswith(("#", "|", "```", "<", ">", "*", "-", "Place the files", "Original model repository", "https://", "see github")) or p.endswith(":"): continue
        return " ".join(p.split())[:220]
    return ""


def fetch_card(repo, cache_dir):
    """A repo's model card, cached. -> (description, source)."""
    c = Path(cache_dir) / (repo.replace("/", "__") + ".md"); c.parent.mkdir(parents=True, exist_ok=True)
    if not c.exists():
        try:
            data = urllib.request.urlopen(f"https://huggingface.co/{urllib.parse.quote(repo)}/raw/main/README.md", timeout=30).read().decode("utf8", "replace")
        except Exception: data = ""
        c.write_text(data)
    text = c.read_text(); d = first_paragraph(text)
    return (d, f"model card of {repo}") if d else ("", "")


def decide(row, ok, reachable, used, proof):
    """-> (status, next step). Pure."""
    if not ok: return "not_on_disk", "not landed: check the fetch log before relying on it"
    if proof: return "rendered", ""
    if used: return "graph", "a graph names it: run it"
    if reachable: return "reachable", "a loader can see it but no graph uses it: add a graph or a LoRA recipe"
    return "unreachable", "no ComfyUI folder lists it and no runner reads it: wire a runner or map the folder"


def plans_landed(workbench, models_root, have, names=LATER_PLANS):
    """Rows of the later fetch plans that have landed: those plans list far more than has arrived, so only files on disk count."""
    return [r for r in load_plans(workbench, names) if r.get("sha") not in have and on_disk(models_root, r)[0]]


def link_uses(models_root, uses, roots=("_complete_pipelines", "controlnet", "checkpoints", "diffusion_models", "text_encoders", "loras", "vae")):
    """{real path: uses} for files a graph names through a link: the link's name is what the graph says, the file it points at is what gets proven."""
    out = {}
    for r in roots:
        for dp, dn, fs in os.walk(os.path.join(models_root, r)):
            for f in fs:
                p = os.path.join(dp, f)
                if os.path.islink(p) and f in uses: out.setdefault(os.path.realpath(p), []).extend(uses[f])
    return out


def build(repo_root, models_root, workbench, yaml_path, all_json, template_dir=None, cards=None, plans=PLANS, arrivals=(), viewed=None):
    status = json.load(open(Path(repo_root) / "studio" / "family_status.json"))["families"]
    from studio.names import model_key
    uses = index_uses(repo_root, template_dir); by_key = {}
    for n, w in uses.items(): by_key.setdefault(model_key(n), []).extend(w)
    folders = comfy_folders(yaml_path); proofs = proof_index(all_json, status); rows = []; needs = need_paths(repo_root); viewed = viewed or {}
    linked = link_uses(models_root, uses)
    try: proofs3d = json.load(open(Path(repo_root) / "studio" / "model3d_proof.json"))
    except (OSError, ValueError): proofs3d = {}
    planned = load_plans(workbench, plans); planned += plans_landed(workbench, models_root, {r.get("sha") for r in planned}); known = {os.path.normpath(os.path.join(models_root, r["rel"])) for r in planned}
    for path, size in arrivals:                                  # landed with no plan row naming it: all that is known is the file
        if os.path.normpath(path) not in known and not path.endswith(".sha256-ok"):
            planned.append({"sha": "", "bytes": size, "function": "arrived, no plan row", "repo": "", "path": "", "rel": os.path.relpath(path, models_root) if path.startswith(str(models_root)) else path})
    for r in planned:
        ok, path = on_disk(models_root, r); name = os.path.basename(r["rel"]); used = [] if GENERIC.match(name) else list(uses.get(name) or by_key.get(model_key(name)) or [])
        used += [w for pth, w in needs.items() if r["rel"].endswith(pth) and w not in used]
        used += [w for w in linked.get(os.path.realpath(path), []) if w not in used]
        for pre, label in RUNNERS:
            if pre in r["rel"] and label not in used: used.append(label)
        typ = reach(r["rel"], folders)
        rejected = ""; names = [u.rsplit(" / ", 1)[-1] for u in used]; hit = next((t for t in names if t in proofs), "")
        proof = proofs[hit] if hit else tool_proof(r["rel"], used, proofs3d)
        if proof:
            key = hit or next((tid for lb, (tid, _) in TOOL_PROOF.items() if any(u.startswith(lb) for u in used)), "")
            proof += "; looked at: " + viewed[key] if key in viewed else "; not looked at yet"
            if viewed.get(key, "").startswith("REJECTED"): rejected, proof = proof, ""                       # it finished, but looking at it showed it proves nothing
        st, nxt = decide(r, ok, bool(typ), used, proof)
        if rejected and st == "graph": nxt = "run again: " + rejected
        if st in ("reachable", "unreachable"):
            nxt = next((w for pat, w in WHY_UNUSED if pat in r["rel"]), nxt)
        does, src = (fetch_card(r["repo"], cards) if cards and r["repo"] else ("", ""))
        rows.append({"file": name, "gb": round(int(r.get("bytes") or 0) / 1e9, 2), "repo": r["repo"], "path_in_repo": r["path"], "on_disk": "yes" if ok else "no", "disk_path": path, "function": r.get("function", ""), "family": family_of(r, status),
                     "does": does or f"not read: plan says {r.get('function', '')}", "does_source": src or "plan function only, card not read", "status": st, "used_by": "; ".join(used[:6]) + (f"; +{len(used) - 6} more" if len(used) > 6 else ""), "proof": proof, "next_step": nxt, "sha": r.get("sha", "")})
    return rows


def voice_proof(rows):
    """Speech models run in their own process, so no graph names them. The Voices page's recorded proof moves their rows, here as well as by hand, so a rebuild keeps them."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("record_voice_renders", ROOT / "scripts" / "record_voice_renders.py"); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    try: good, low = mod.proofs()
    except (OSError, ValueError): return rows
    mod.apply(rows, good, low); return rows


def write_tsv(rows, out):
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, COLUMNS, delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(rows)


def main(argv=None):
    a = argparse.ArgumentParser(); a.add_argument("--out", required=True); a.add_argument("--models", required=True); a.add_argument("--yaml", required=True); a.add_argument("--all-json", required=True); a.add_argument("--cards"); a.add_argument("--arrivals", help="TSV of path and size from scan_new_models.py"); a.add_argument("--viewed", help="ledger: template or tool id, tab, what looking at the result showed"); a = a.parse_args(argv)
    try:
        import comfyui_workflow_templates_json as t; td = os.path.join(os.path.dirname(t.__file__), "templates")
    except ImportError: td = None
    rows = build(ROOT, a.models, os.path.join(a.models, "_workbench"), a.yaml, json.load(open(a.all_json)), td, a.cards, arrivals=[(l.split("\t")[0], int(l.split("\t")[1])) for l in open(a.arrivals)] if a.arrivals else (), viewed=load_viewed(a.viewed))
    rows = voice_proof(rows); write_tsv(rows, a.out)
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("build_future_numbers", ROOT / "scripts" / "build_future_numbers.py"); fn = module_from_spec(spec); spec.loader.exec_module(fn); fn.write(a.out)      # the Future page's totals follow the map
    n = {}
    for r in rows: n[r["status"]] = n.get(r["status"], 0) + 1
    print(len(rows), "files:", n, "rendered and looked at:", sum(r["status"] == "rendered" and "looked at:" in r["proof"] for r in rows), "of those weak:", sum(r["status"] == "rendered" and "looked at: WEAK" in r["proof"] for r in rows))


if __name__ == "__main__":
    main()
