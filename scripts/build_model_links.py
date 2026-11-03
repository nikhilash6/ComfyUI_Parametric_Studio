#!/usr/bin/env python3
"""Find the official download for every model file the repository uses, and write it into studio/models_manifest.json ("files") and MODELS.md.

The list of files comes from studio/model_inventory.py (graphs, family templates, goals, recipes, pipelines, music, voices, feature code). For each file it
collects candidate sources: the links already in the repository (the goal manifest, the family templates, ComfyUI's own template metadata), any download
plans or catalogues passed with --plans and --catalog, the model cards a source points at, and a Hugging Face search for a LoRA's folder name. Every candidate
is checked against the Hugging Face API (model_info with blobs: the file must be listed; its size and LFS SHA-256 come from that listing, which also gives
the licence and gated flag). Comfy-Org repackages and the publisher's own repository win over re-uploads. A file with no candidate that checks out is written
with source "none" and said so in MODELS.md. Metadata only: nothing is downloaded. Responses are cached in --cache so a re-run is quick.

Usage: python3 scripts/build_model_links.py [--plans PLAN.tsv ...] [--catalog DIR_OR_JSON ...] [--cache DIR] [--offline] [--check]"""
import argparse
import concurrent.futures as cf
import csv
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from studio import model_inventory as mi  # noqa: E402

API = "https://huggingface.co/api"
UA = {"User-Agent": "parametric-studio-model-links"}
#: Publishers whose own repositories count as official, ahead of re-uploads. Comfy-Org repackages rank first of all.
OFFICIAL = {"comfy-org", "black-forest-labs", "lightricks", "minimaxai", "wan-ai", "qwen", "stabilityai", "stable-diffusion-v1-5", "tencent", "tencent-hunyuan",
            "nvidia", "facebook", "microsoft", "google", "openai", "meta-llama", "lodestones", "circlestone-labs", "ace-step", "tongyi-mai", "hidream-ai",
            "kwai-kolors", "kwaivgi", "rhymes-ai", "zai-org", "thudm", "genmo", "vast-ai", "bytedance", "bytedance-seed", "alibaba-pai", "briaai",
            "ideogram-ai", "krea", "meituan-longcat", "efficient-large-model", "pixart-alpha", "h94", "guoyww", "bytedance", "intel", "skywork", "m-a-p",
            "hexgrad", "resembleai", "fireredteam", "openbmb", "suno", "swivid", "zyphra", "coqui", "indexteam", "stepfun-ai", "k2-fsa", "kijai",
            "xinsir", "lllyasviel", "yzd-v", "depth-anything", "jingheya", "ruicheng", "tencentarc", "deepseek-ai", "mistralai", "allenai", "apple",
            "laion", "timbrooks", "runwayml", "sayakpaul", "alibabasglab", "systran", "drbaph", "gradium", "supertone", "neuphonic", "maya-research",
            "ibm-granite", "soul-ailab", "declare-lab", "heartmula", "diffsynth-studio", "aidc-ai", "omnigen2", "speridlabs", "jdopensource",
            "kandinskylab", "t8star", "firered", "openmoss-team", "wgsxm", "turbodiffusion", "sefi-image", "boyuanjiang", "junhaozhuang",
            "lightx2v", "ostris", "unsloth", "lykon", "instantx", "latent-consistency", "klingteam", "resembleai", "pablodawson", "akatz-ai", "playgroundai", "segmind", "madebyollin", "comfyanonymous"}
NC_IDS = re.compile(r"(^|-)nc(-|$)|non-commercial|noncommercial|research|cc-by-nc|flux-1-dev|flux-dev|stable-cascade", re.I)


def log(*a):
    print(*a, file=sys.stderr)


class HF:
    """A cached, polite reader of the Hugging Face API. None means the repo is not there or not readable."""

    def __init__(self, cache, offline=False):
        self.dir = Path(cache)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.offline = offline

    def _get(self, url, tries=4):
        for i in range(tries):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404): return None
                if e.code == 429: time.sleep(30 * (i + 1)); continue
                time.sleep(3 * (i + 1))
            except (OSError, ValueError):
                time.sleep(3 * (i + 1))
        return None

    def _cached(self, key, url):
        f = self.dir / (re.sub(r"[^\w.-]+", "_", key)[:180] + ".json")
        if f.exists():
            return json.loads(f.read_text())["data"]
        if self.offline: return None
        data = self._get(url)
        f.write_text(json.dumps({"url": url, "fetched": time.strftime("%Y-%m-%d"), "data": data}))
        return data

    def info(self, repo):
        return self._cached(f"info_{repo}", f"{API}/models/{repo}?blobs=true")

    def search(self, term):
        return self._cached(f"search_{term}", f"{API}/models?search={urllib.parse.quote(term)}&limit=30") or []


def head_size(url, hf):
    """Content length of a release asset, from a HEAD request (cached; nothing is downloaded)."""
    f = hf.dir / ("head_" + re.sub(r"[^\w.-]+", "_", url)[-150:] + ".json")
    if f.exists(): return json.loads(f.read_text())["size"]
    if hf.offline: return None
    size = None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD", headers=UA), timeout=60) as r:
            size = int(r.headers.get("Content-Length") or 0) or None
    except (OSError, ValueError): pass
    f.write_text(json.dumps({"url": url, "size": size}))
    return size


def gh_licence(url, hf):
    """(SPDX id plus where it was read, licence page) for a GitHub project, from the GitHub API (cached)."""
    m = re.match(r"https://github\.com/([\w.-]+/[\w.-]+)/", url)
    if not m: return None
    data = hf._cached(f"gh_{m.group(1)}", f"https://api.github.com/repos/{m.group(1)}")
    spdx = ((data or {}).get("license") or {}).get("spdx_id")
    return (f"{spdx} (the project's code repository)", f"https://github.com/{m.group(1)}") if spdx and spdx != "NOASSERTION" else None


def parse_hf_url(url):
    """-> (repo, path) for a huggingface.co resolve or blob link, else None."""
    m = re.match(r"https?://huggingface\.co/(?!datasets/|spaces/)([\w.-]+/[\w.-]+)/(?:resolve|blob)/[^/]+/(.+?)(?:\?.*)?$", str(url or ""))
    return (m.group(1), urllib.parse.unquote(m.group(2))) if m else None


def read_tsv(path):
    with open(path, newline="", encoding="utf-8") as f:
        first = f.readline()
        if "repo" not in first.split("\t"): return []
        f.seek(0)
        return list(csv.DictReader(f, delimiter="\t"))


def candidates_from_repo(root):
    """{basename: [(repo, path, sha, origin)]} and {url: origin} from the links the repository already carries."""
    by_name, other = {}, {}
    def add(name, url, sha=None, origin="repo"):
        hp = parse_hf_url(url)
        if hp: by_name.setdefault(Path(name).name, []).append((hp[0], hp[1], sha, origin))
        elif url: other.setdefault(Path(name).name, []).append((url, origin))
    goals = json.loads((root / "studio/models_manifest.json").read_text()).get("goals") or {}
    for g in goals.values():
        for f in g.get("files") or []:
            by_name.setdefault(Path(f["path"]).name, []).append((f["repo"], f["path"], f.get("sha256") or None, "goal manifest"))
    idx = json.loads((root / "studio/family_templates/index.json").read_text())
    for t in idx.get("templates") or []:
        for m in t.get("models") or []: add(m.get("name", ""), m.get("url"), origin="studio template")
    st = json.loads((root / "studio/family_status.json").read_text()).get("families") or {}
    for row in st.values():
        for t in row.get("templates") or []:
            for m in (t.get("models") or []) if isinstance(t, dict) else []: add(m.get("name", ""), m.get("url"), origin="ComfyUI template")
    for p in mi.graph_files(root):
        try: doc = json.loads((root / p).read_text())
        except ValueError: continue
        for m in _template_models(doc): add(m["name"], m["url"], origin="graph metadata")
    return by_name, other


def _template_models(doc):
    if isinstance(doc, dict):
        if isinstance(doc.get("models"), list):
            for m in doc["models"]:
                if isinstance(m, dict) and m.get("name") and m.get("url"): yield m
        for v in doc.values(): yield from _template_models(v)
    elif isinstance(doc, list):
        for v in doc: yield from _template_models(v)


def candidates_from_catalogs(paths):
    """ComfyUI's template packages or any JSON with {"models": [{name, url}]}: {basename: [(repo, path, None, origin)]}."""
    by_name = {}
    files = []
    for p in paths:
        p = Path(p)
        files += sorted(p.rglob("*.json")) if p.is_dir() else [p]
    for f in files:
        try: doc = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError): continue
        for m in _template_models(doc):
            hp = parse_hf_url(m["url"])
            if hp: by_name.setdefault(Path(m["name"]).name, []).append((hp[0], hp[1], None, "ComfyUI template"))
    return by_name


def candidates_from_plans(paths):
    """Download plans (rel, repo, path, sha): {basename: [...]}, {rel path: (repo, path, sha)}."""
    by_name, by_rel = {}, {}
    for p in paths:
        for r in read_tsv(p):
            repo, path = (r.get("repo") or "").strip(), (r.get("path") or r.get("path_in_repo") or "").strip()
            if not re.match(r"^[\w.-]+/[\w.-]+$", repo) or not path: continue
            sha = (r.get("sha") or "").strip() or None
            by_name.setdefault(Path(path).name, []).append((repo, path, sha, "plan"))
            if r.get("file") and Path(r["file"]).name != Path(path).name:
                by_name.setdefault(Path(r["file"]).name, []).append((repo, path, sha, "plan"))
            for relkey in ("rel", "disk_path"):
                rel = (r.get(relkey) or "").strip()
                if rel:
                    rel = re.sub(r"^.*?/comfyui_models/", "", rel)
                    by_rel[rel] = (repo, path, sha)
                    if Path(rel).name != Path(path).name:          # saved under another name: the plan is the only link between the two
                        by_name.setdefault(Path(rel).name, []).append((repo, path, sha, "plan"))
    return by_name, by_rel


def author_repos(hf, authors):
    out = []
    for a in authors:
        out += [m["id"] for m in hf._cached(f"author_{a}", f"{API}/models?author={urllib.parse.quote(a)}&limit=1000") or []]
    return out


SEARCH_STOP = {"minimax", "safetensors", "comfyui", "comfy", "lora", "loras", "high", "noise", "steps", "pruned", "model", "style", "slider", "rank",
               "final", "epoch", "wan2.2", "wan22", "i2v", "t2v", "bf16", "fp16", "fp8", "16-sel", "video", "transformer", "encoder", "single", "music3"}
_PREFIX = re.compile(r"^(minimax[_-]?h3[_-]?|mmh3[_-]|h3[_-]|wan[_-]?2\.?2[_-]?|wan22[_-]|\[wan2\.2-i2v\])", re.I)
_NOISE = re.compile(r"^(v?\d+(\.\d+)*|step-?\d+|s\d+|ep\d+|cp\d+|rank\d+|r\d+|\d+|high|low|noise|comfyui|comfy|bf16|fp16|pruned|lora|v\d\w*)$", re.I)


def search_terms(key, row):
    """Hugging Face search strings for a file no source links: the folder's author (alvdansen_keyframe -> alvdansen), the name without its
    family prefix and trailing version words, and its longest distinctive word."""
    stem = re.sub(r"\.\w+$", "", key.rsplit("/", 1)[-1])
    out = []
    for n in row["names"]:
        for seg in mi.split_path(n)[0].split("/")[:-1]:
            m = re.match(r"^([A-Za-z][A-Za-z0-9]{4,})_", seg)
            if m and not seg.lower().startswith(("minimax", "civitai", "wan", "ltx")): out.append(m.group(1))
    core = _PREFIX.sub("", stem)
    toks = [t for t in re.split(r"[_\-.\s]+", core) if t]
    while toks and _NOISE.match(toks[-1]): toks.pop()
    if toks:
        phrase = "-".join(toks[:3])
        if len(phrase) >= 6: out.append(phrase)
    words = sorted({w for w in re.split(r"[_\-.\s\[\]]+", core) if len(w) >= 6 and w.lower() not in SEARCH_STOP and not _NOISE.match(w)}, key=len, reverse=True)
    out += words[:1]
    return list(dict.fromkeys(out))[:3]


def rank(repo, origin, family_repos):
    """(0 official or 1 community, how directly a source links it, publisher order). An official publisher beats a re-upload; among official
    copies the one a goal or template links wins, because two repos can hold different bytes under one name; Comfy-Org breaks the remaining ties."""
    owner = repo.split("/")[0].lower()
    if owner == "comfy-org": r = 0
    elif repo in family_repos: r = 1
    elif owner in OFFICIAL: r = 2
    else: r = 4
    o = {"goal manifest": 0, "studio template": 1, "ComfyUI template": 2, "graph metadata": 2, "plan": 3, "card": 3, "folder name": 3,
         "author index": 4, "same SHA-256": 4, "search": 5, "lead": 5}.get(origin, 6)
    return (0 if r <= 2 else 1, o, r)


def licence_of(info):
    card = info.get("cardData") or {}
    lid = card.get("license") or next((t.split(":", 1)[1] for t in info.get("tags") or [] if t.startswith("license:")), None)
    if isinstance(lid, list): lid = lid[0] if lid else None
    name = card.get("license_name")
    link = card.get("license_link")
    label = name if (lid in (None, "other") and name) else (lid or name or "not stated on the card")
    if link and not re.match(r"https?://", str(link)): link = f"https://huggingface.co/{info['id']}/blob/main/{str(link).lstrip('./')}"
    nc = bool(NC_IDS.search(f"{lid or ''} {name or ''}"))
    return label, link, nc


def pick_in_repo(info, key, names):
    """The file in this repo's listing that is the one a source names: exact path first, then the same path tail, then the same file name."""
    sib = {s["rfilename"]: s for s in info.get("siblings") or []}
    base = key.rsplit("/", 1)[-1]
    tails = sorted({mi.split_path(n)[0] for n in names} | {key}, key=len, reverse=True)
    if mi.GENERIC.match(base): tails = [t for t in tails if "/" in t]
    for t in tails:
        if t in sib: return sib[t]
    for t in tails:
        if "/" in t:
            hit = [s for p, s in sib.items() if p.endswith("/" + t)]
            if len(hit) == 1: return hit[0]
    if mi.GENERIC.match(base):
        # model.safetensors means nothing alone, unless the path names this repo: .../whisper-tiny/model.safetensors in openai/whisper-tiny
        rid = info.get("id", "")
        for n in names:
            segs = mi._LAYOUT_PREFIX.sub("", n.replace("\\", "/")).split("/")
            low = [x.lower() for x in segs]
            for want in (rid.replace("/", "__").lower(), rid.split("/")[-1].lower()):
                if want in low[:-1]:
                    rest = "/".join(segs[low.index(want) + 1:])
                    if rest in sib: return sib[rest]
        return None
    hit = [s for p, s in sib.items() if p.rsplit("/", 1)[-1] == base]
    return hit[0] if len(hit) == 1 else (sorted(hit, key=lambda s: len(s["rfilename"]))[0] if hit else None)


def folder_from_repo_path(path, key):
    for seg in path.split("/")[:-1]:
        if seg in mi.LOADER_FOLDERS.values() or seg in mi.KNOWN_FOLDERS: return seg
    low = (path + key).lower()
    if "lora" in low: return "loras"
    if key.endswith(".gguf"): return "LLM"
    return None


#: Publishers' own repositories that no source in the repository links but that hold files the graphs name (often under the name a re-upload copied).
EXTRA_REPOS = ["h94/IP-Adapter", "guoyww/animatediff", "timbrooks/instruct-pix2pix", "meta-llama/Meta-Llama-3-8B-Instruct", "laion/CLIP-ViT-H-14-laion2B-s32B-b79K",
               "openai/clip-vit-large-patch14", "xinsir/controlnet-depth-sdxl-1.0", "xinsir/controlnet-openpose-sdxl-1.0", "xinsir/controlnet-scribble-sdxl-1.0",
               "xinsir/controlnet-tile-sdxl-1.0", "madebyollin/sdxl-vae-fp16-fix", "lllyasviel/ic-light", "Intel/ldm3d-4c", "KlingTeam/LivePortrait",
               "tencent/HY-Motion-1.0", "latent-consistency/lcm-lora-sdv1-5", "Lykon/DreamShaper", "stable-diffusion-v1-5/stable-diffusion-v1-5",
               "lllyasviel/ControlNet-v1-1", "comfyanonymous/flux_text_encoders", "ByteDance/LatentSync-1.6", "ResembleAI/chatterbox"]


_SHA_CACHE = {"file": None, "data": {}}


def sha256_file(path, chunk=1 << 22):
    """SHA-256 of a local file, remembered by path, size and time in the cache folder so a re-run does not read it again."""
    import hashlib
    st = Path(path).stat()
    key = f"{path}|{st.st_size}|{int(st.st_mtime)}"
    if key in _SHA_CACHE["data"]: return _SHA_CACHE["data"][key]
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while b := fh.read(chunk): h.update(b)
    _SHA_CACHE["data"][key] = h.hexdigest()
    if _SHA_CACHE["file"]: Path(_SHA_CACHE["file"]).write_text(json.dumps(_SHA_CACHE["data"]))
    return h.hexdigest()


def read_sizes(paths):
    """{file name: bytes} from inventory tables: any row with a cell naming a model file and a cell that is a byte count."""
    out = {}
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                cells = line.rstrip("\n").split("\t")
                name = next((c for c in cells if c.strip().endswith(mi.MODEL_EXT)), None)
                size = next((int(c) for c in cells if c.isdigit() and int(c) > 4096), None)
                if name and size: out.setdefault(Path(name.strip()).name, size)
    return out


def civitai_queries(key, row):
    """Civitai search words for a file: its search terms with the dashes as spaces, then the bare stem."""
    stem = re.sub(r"\.\w+$", "", key.rsplit("/", 1)[-1])
    terms = [t.replace("-", " ") for t in search_terms(key, row)]
    qs = terms + [re.sub(r"v\d+$", "", t) for t in terms] + [re.sub(r"[_\-]+", " ", stem)]
    return list(dict.fromkeys(q.strip() for q in qs if len(q.strip()) >= 4))[:4]


def read_leads(paths, wanted):
    """Repos a research table says a file came from: Hugging Face and ModelScope rows that were on the box or that list one of the wanted file
    names. Columns used: source, repo, status, take_files (the camp-b wide-search table has them)."""
    hf_repos, ms_repos = set(), set()
    for p in paths:
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                repo, src = (r.get("repo") or "").strip(), (r.get("source") or "").strip()
                if not re.match(r"^[\w.-]+/[\w.-]+$", repo): continue
                hit = (r.get("status") or "").startswith("ON BOX") or any(w in (r.get("take_files") or "") for w in wanted)
                if src == "HF" and hit: hf_repos.add(repo)
                elif src == "ModelScope": ms_repos.add(repo)          # few rows, and their files are often renamed: all are compared by SHA-256
    return sorted(hf_repos), sorted(ms_repos)


_LOCAL = {}


def local_index(local_root):
    """{file name: [paths]} for every model file under local_root (walked once)."""
    if local_root not in _LOCAL:
        idx = {}
        for d, _dirs, names in os.walk(local_root, followlinks=False):
            for n in names:
                if n.endswith(mi.MODEL_EXT): idx.setdefault(n, []).append(Path(d) / n)
        _LOCAL[local_root] = idx
    return _LOCAL[local_root]


def local_copies(local_root, use_map, key, row):
    """Paths of this file on the machine that built the plans: under local_root by its names or file name, or by the use map's disk paths."""
    out = []
    base = key.rsplit("/", 1)[-1]
    for lr in ([local_root] if isinstance(local_root, (str, Path)) else list(local_root or [])):
        root = Path(lr)
        for n in row["names"]:
            for cand in (root / n, root / mi.split_path(n)[0]):
                if cand.is_file(): out.append(cand)
        if not mi.GENERIC.match(base): out += [p for p in local_index(str(lr)).get(base, []) if p.is_file()]
    if not mi.GENERIC.match(base): out += [Path(p) for p in use_map.get(base, []) if Path(p).is_file()]
    return list(dict.fromkeys(out))[:6]


def build(root, plans, catalogs, cache, offline=False, workers=6, authors=(), extra_repos=EXTRA_REPOS, local_root=None, leads=(), sizes=()):
    inv = mi.inventory(root)
    st = json.loads((root / "studio/family_status.json").read_text()).get("families") or {}
    fam_repos = {r for row in st.values() for r in row.get("repos") or []}
    repo_names, repo_other = candidates_from_repo(root)
    cat = candidates_from_catalogs(catalogs)
    plan_names, plan_rel = candidates_from_plans(plans)
    hf = HF(cache, offline)
    known_sizes = read_sizes(sizes)
    _SHA_CACHE["file"] = hf.dir / "local_sha256.json"
    if _SHA_CACHE["file"].exists(): _SHA_CACHE["data"] = json.loads(_SHA_CACHE["file"].read_text())

    # The big repackagers' whole listings: a file no source links may still be one of theirs, under the same name.
    indexed = author_repos(hf, authors) + [r for r in extra_repos]
    with cf.ThreadPoolExecutor(workers) as ex:
        idx_infos = dict(zip(indexed, ex.map(hf.info, indexed)))
    idx_names = {}
    for repo, info in idx_infos.items():
        for sib in (info or {}).get("siblings") or []:
            if sib["rfilename"].endswith(mi.MODEL_EXT): idx_names.setdefault(sib["rfilename"].rsplit("/", 1)[-1], []).append((repo, sib["rfilename"], None, "author index"))
    log(f"indexed {len(idx_infos)} repos of {', '.join(authors) or 'no authors'}")

    known_by_name = {}
    for r in set(idx_infos) | {c[0] for cs in repo_names.values() for c in cs} | {c[0] for cs in plan_names.values() for c in cs} | set(EXTRA_REPOS):
        known_by_name.setdefault(r.split("/")[-1].lower(), []).append(r)
    cands = {}
    for key, row in inv.items():
        base = key.rsplit("/", 1)[-1]
        c = []
        generic = bool(mi.GENERIC.match(base))
        hints = {h for h in row["hints"] if not h.startswith("*/")}
        for n in sorted(row["names"]):
            rel = n.replace("\\", "/")
            tail = mi._LAYOUT_PREFIX.sub("", rel)          # keeps an owner__repo folder, which tells generic names apart
            for r in (rel, tail):
                if r in plan_rel: c.append((*plan_rel[r], "plan"))
            if tail.count("/") >= (2 if generic else 1):
                for r, v in plan_rel.items():
                    if r.endswith("/" + tail) and (not generic or not hints or v[0] in hints): c.append((*v, "plan"))
        if generic and "/" not in key and len({x[0] for x in repo_names.get(base, [])}) == 1:
            c += repo_names[base]                         # one template links this generic name: that link is the file
        if not generic:
            c += repo_names.get(base, []) + cat.get(base, []) + plan_names.get(base, []) + idx_names.get(base, [])
        for h in sorted(row["hints"]):
            if not h.startswith("*/"): c.append((h, None, None, "card"))
        if generic:
            for n in row["names"]:
                for seg in mi.split_path(n)[0].split("/")[:-1]:
                    c += [(r, None, None, "folder name") for r in known_by_name.get(seg.lower(), [])]
        cands[key] = c

    # LoRA folders named like a repo: find the repo by search.
    searches = sorted({h[2:] for row in inv.values() for h in row["hints"] if h.startswith("*/") and len(h) > 6})
    with cf.ThreadPoolExecutor(workers) as ex:
        found = dict(zip(searches, ex.map(hf.search, searches)))
    for key, row in inv.items():
        for h in row["hints"]:
            if h.startswith("*/"):
                for m in found.get(h[2:]) or []:
                    if m.get("id", "").split("/")[-1].lower() == h[2:].lower(): cands[key].append((m["id"], None, None, "search"))

    repos = sorted({c[0] for cs in cands.values() for c in cs} - set(idx_infos))
    log(f"{len(inv)} files, {len(repos)} more candidate repos")
    with cf.ThreadPoolExecutor(workers) as ex:
        infos = dict(zip(repos, ex.map(hf.info, repos)))
    infos.update(idx_infos)

    # A local copy saved under another name: match it by size against every listing read, then confirm by SHA-256.
    by_size = {}
    for info in infos.values():
        for sib in (info or {}).get("siblings") or []:
            sz = sib.get("size") or (sib.get("lfs") or {}).get("size")
            if sz and sz > 1 << 20 and (sib.get("lfs") or {}).get("sha256"): by_size.setdefault(sz, []).append((info, sib))
    use_map = {}
    for p in plans:
        for r in read_tsv(p):
            if r.get("disk_path") and r.get("file"): use_map.setdefault(r["file"], []).append(r["disk_path"])

    def choose(key, row):
        best = None
        for repo, path, sha, origin in cands[key]:
            info = infos.get(repo)
            if not info: continue
            sib = None
            if path:
                sib = next((s for s in info.get("siblings") or [] if s["rfilename"] == path), None)
            if sib is None:
                sib = pick_in_repo(info, key, row["names"])
            if sib is None: continue
            score = (*rank(info.get("id", repo), origin, fam_repos), info.get("createdAt") or "9999", len(sib["rfilename"]))
            if best is None or score < best[0]: best = (score, info, sib, origin, sha)
        return best

    # Files nothing links yet: search Hugging Face by the folder's author and the name's distinctive words, keep repos that list the exact file name.
    open_keys = [k for k, row in inv.items() if choose(k, row) is None and not mi.GENERIC.match(k.rsplit("/", 1)[-1])]
    terms = {k: search_terms(k, inv[k]) for k in open_keys}
    queries = sorted({t for ts in terms.values() for t in ts})
    with cf.ThreadPoolExecutor(workers) as ex:
        results = dict(zip(queries, ex.map(hf.search, queries)))
    found_repos = sorted({m["id"] for q in queries for m in (results.get(q) or [])[:8]} - set(infos))
    log(f"{len(open_keys)} files with no link yet: {len(queries)} searches, {len(found_repos)} repos to read")
    with cf.ThreadPoolExecutor(workers) as ex:
        infos.update(dict(zip(found_repos, ex.map(hf.info, found_repos))))
    for k in open_keys:
        for q in terms[k]:
            for m in (results.get(q) or [])[:8]: cands[k].append((m["id"], None, None, "search"))
    for info in (infos[r] for r in found_repos):
        for sib in (info or {}).get("siblings") or []:
            sz = sib.get("size") or (sib.get("lfs") or {}).get("size")
            if sz and sz > 1 << 20 and (sib.get("lfs") or {}).get("sha256"): by_size.setdefault(sz, []).append((info, sib))

    # Research tables (--leads): the repos earlier work found these files in. Kept only where the exact file name is listed, as with search.
    still = [k for k in open_keys if choose(k, inv[k]) is None]
    lead_hf, lead_ms = read_leads(leads, {k.rsplit("/", 1)[-1] for k in still}) if leads else ([], [])
    new_leads = sorted(set(lead_hf) - set(infos))
    log(f"{len(still)} still open: {len(lead_hf)} Hugging Face and {len(lead_ms)} ModelScope repos from the research tables")
    with cf.ThreadPoolExecutor(workers) as ex:
        infos.update(dict(zip(new_leads, ex.map(hf.info, new_leads))))
    for k in still:
        cands[k] += [(r, None, None, "lead") for r in lead_hf]
    for info in (infos[r] for r in new_leads):
        for sib in (info or {}).get("siblings") or []:
            sz = sib.get("size") or (sib.get("lfs") or {}).get("size")
            if sz and sz > 1 << 20 and (sib.get("lfs") or {}).get("sha256"): by_size.setdefault(sz, []).append((info, sib))
    ms_by_sha = {}
    for repo in lead_ms:
        data = hf._cached(f"ms_{repo}", f"https://modelscope.cn/api/v1/models/{repo}/repo/files?Recursive=true") or {}
        for f in (data.get("Data") or {}).get("Files") or []:
            if f.get("Sha256") and str(f.get("Path", "")).endswith(mi.MODEL_EXT): ms_by_sha[f["Sha256"]] = (repo, f["Path"], f.get("Size"))

    files = []
    for key, row in sorted(inv.items()):
        best = choose(key, row)
        checked = None
        alt_gh = any(re.match(r"https://github\.com/[\w.-]+/[\w.-]+/releases/download/", u) for u, _ in repo_other.get(key.rsplit("/", 1)[-1], []))
        if best and alt_gh and best[0][0] >= 1: best = None        # the project's own GitHub release beats a stranger's upload
        if best and best[3] in ("search", "lead"):
            copies = local_copies(local_root, use_map, key, row) if (local_root or use_map) else []
            want = (best[2].get("lfs") or {}).get("sha256")
            if copies and want:
                checked = "same SHA-256 as the studio's copy" if sha256_file(copies[0]) == want else "differs"
                if checked == "differs": best = None
            else:
                checked = "same file name only; not compared byte for byte"
        if best is None and (local_root or use_map) and not alt_gh:
            for path in local_copies(local_root, use_map, key, row):
                same = by_size.get(path.stat().st_size) or []
                if not same or path.stat().st_size > 40 * 2**30: continue
                digest = sha256_file(path)
                hits = sorted((rank(i["id"], "same SHA-256", fam_repos), i.get("createdAt") or "9999", i["id"], i, sb) for i, sb in same if sb["lfs"]["sha256"] == digest)
                if hits:
                    best = (hits[0][0], hits[0][3], hits[0][4], "same SHA-256", digest)
                    break
        dest = mi.dest_of(key, row)
        fams = sorted(row["families"])
        entry = {"filename": key, "folder": row["folder"], "dest": dest, "used_by": sorted(row["used_by"]), "family": family_label(key, row, st)}
        if best:
            _, info, sib, origin, plan_sha = best
            repo = info["id"]
            lfs = sib.get("lfs") or {}
            label, link, nc = licence_of(info)
            gated = info.get("gated") or False
            folder = row["folder"] or folder_from_repo_path(sib["rfilename"], key)
            entry.update({
                "folder": folder, "dest": dest or (f"{folder}/{key.rsplit('/', 1)[-1]}" if folder else None),
                "url": f"https://huggingface.co/{repo}/resolve/main/{urllib.parse.quote(sib['rfilename'])}",
                "repo": repo, "path": sib["rfilename"], "size": sib.get("size") or lfs.get("size"),
                "sha256": lfs.get("sha256") or None, "licence": label, "licence_url": link or f"https://huggingface.co/{repo}",
                "noncommercial": nc, "gated": bool(gated), "source": "huggingface", "found_by": origin,
                "publisher": "official" if rank(repo, origin, fam_repos)[0] == 0 else "community",
            })
            if checked: entry["checked"] = checked
            others = {}
            for r2, p2, _s, o2 in cands[key]:
                if o2 not in ("goal manifest", "studio template", "ComfyUI template", "graph metadata") or not p2: continue
                s2 = next((x for x in (infos.get(r2) or {}).get("siblings") or [] if x["rfilename"] == p2), None)
                sha2 = ((s2 or {}).get("lfs") or {}).get("sha256")
                if sha2 and sha2 != entry["sha256"] and Path(p2).name == Path(sib["rfilename"]).name:
                    others.setdefault(sha2, {"url": f"https://huggingface.co/{r2}/resolve/main/{urllib.parse.quote(p2)}", "sha256": sha2, "size": s2.get("size"), "linked_by": o2})
            if others: entry["also_linked"] = list(others.values())   # another template links a different file under the same name
            if not entry["dest"]:
                entry["where"] = "read by " + ", ".join(sorted({u.split(":", 1)[1] for u in row["used_by"] if ":" in u})) + " from that tool's own folder; see its code"
            if gated: entry["gate"] = "accept the licence on the model page, then set HF_TOKEN"
            if Path(sib["rfilename"]).name != key.rsplit("/", 1)[-1]:
                entry["saved_as"] = f"published as {Path(sib['rfilename']).name}; save it under the name the graphs use"
        else:
            alt = repo_other.get(key.rsplit("/", 1)[-1])
            names = " ".join(row["names"]).lower()
            size = None
            digest = None
            copies = local_copies(local_root, use_map, key, row) if (local_root or use_map) and not alt else []
            if copies and copies[0].stat().st_size <= 40 * 2**30: digest = sha256_file(copies[0])
            ms_hit = ms_by_sha.get(digest) if digest else None
            civ, civ_check = None, None
            if digest and not ms_hit and "parametric_trained/" not in names:
                d = hf._cached(f"civitai_{digest}", f"https://civitai.com/api/v1/model-versions/by-hash/{digest}")
                if d and d.get("modelId"): civ, civ_check = d, "SHA-256"
            base_name = key.rsplit("/", 1)[-1]
            if not civ and not digest and not ms_hit and not alt and "parametric_trained/" not in names and known_sizes.get(base_name):
                # No copy left to hash: look the name up on Civitai and accept it only if the listed size matches the size recorded when it was on the box.
                for q in civitai_queries(key, row):
                    res = hf._cached(f"civq_{q}", f"https://civitai.com/api/v1/models?query={urllib.parse.quote(q)}&limit=20") or {}
                    for m in res.get("items") or []:
                        for v in m.get("modelVersions") or []:
                            for f in v.get("files") or []:
                                if f.get("name") == base_name and f.get("sizeKB") and abs(f["sizeKB"] * 1024 - known_sizes[base_name]) < 2048:
                                    civ, civ_check = {"modelId": m["id"], "id": v["id"], "model": {"name": m.get("name")}, "files": [f]}, "file name and size"
                                    break
                            if civ: break
                        if civ: break
                    if civ: break
            if alt and re.match(r"https://huggingface\.co/[\w.-]+/[\w.-]+/?$", alt[0][0]):
                src, note = "none", f"a template links the model page {alt[0][0]}, but no single file of this name is published there"
                alt = None
            elif alt and re.match(r"https://github\.com/[\w.-]+/[\w.-]+/releases/download/", alt[0][0]):
                size = head_size(alt[0][0], hf)
                src, note = ("github", "a GitHub release asset of the project; no SHA-256 is published") if size else ("other", "a GitHub release link that did not answer")
            elif alt: src, note = "other", "only a non-Hugging Face link is recorded; not checked"
            elif ms_hit: src, note = "modelscope", "on ModelScope, the same SHA-256 as the studio's copy" + (f" (published as {Path(ms_hit[1]).name})" if Path(ms_hit[1]).name != key.rsplit("/", 1)[-1] else "")
            elif civ: src, note = "civitai", f"on Civitai only (matched by {civ_check}); Civitai downloads can need an account, so get_models.py does not fetch it"
            elif "civitai" in names: src, note = "civitai", "from Civitai; no Hugging Face copy found, and its Civitai page could not be confirmed by SHA-256. Civitai needs an account, so get_models.py does not fetch it"
            elif "parametric_trained/" in names: src, note = "trained here", "trained with the studio's Train page; not published"
            else: src, note = "none", "no public source found"
            lic = gh_licence(alt[0][0], hf) if src == "github" else None
            entry.update({"url": alt[0][0] if alt else None, "repo": None, "path": None, "size": size, "sha256": None,
                          "licence": lic[0] if lic else None, "licence_url": lic[1] if lic else None, "noncommercial": False if lic else None,
                          "gated": False if src == "github" else None, "source": src, "note": note})
            if ms_hit:
                entry.update({"url": f"https://modelscope.cn/models/{ms_hit[0]}/resolve/master/{urllib.parse.quote(ms_hit[1])}", "repo": ms_hit[0],
                              "path": ms_hit[1], "size": ms_hit[2], "sha256": digest, "licence_url": f"https://modelscope.cn/models/{ms_hit[0]}", "gated": False})
            if civ:
                f0 = next((f for f in civ.get("files") or [] if digest and ((f.get("hashes") or {}).get("SHA256") or "").lower() == digest), None) or (civ.get("files") or [{}])[0]
                sha_c = digest or ((f0.get("hashes") or {}).get("SHA256") or "").lower() or None
                entry.update({"civitai_url": f"https://civitai.com/models/{civ['modelId']}?modelVersionId={civ['id']}", "civitai_name": (civ.get("model") or {}).get("name"),
                              "civitai_checked": civ_check, "size": known_sizes.get(base_name) or (int(f0["sizeKB"] * 1024) if f0.get("sizeKB") else None), "sha256": sha_c,
                              "published_as": f0.get("name") if f0.get("name") and f0.get("name") != key.rsplit("/", 1)[-1] else None})
                if not entry["published_as"]: entry.pop("published_as")
        files.append(entry)
    return files


#: Family guesses by file name for files no source tags with a family.
NAME_FAMILIES = [(r"minimax_h3|h3_|_h3|mmh3|minimaxh3", "MiniMax-H3"), (r"minimax_music3", "Mini-Max-Music3"), (r"^ltx|ltx-2|ltx2", "LTX-2.5"),
                 (r"flux-2|flux2", "Flux.2"), (r"flux3", "Flux.3-Klein"), (r"flux1|flux-1|ae\.safetensors", "Flux.1"), (r"wan2\.2|wan_2\.2|wan22", "Wan2.2"),
                 (r"wan2\.1|wan_2\.1|wan21|infinitetalk|scail", "Wan2.1"), (r"qwen_image|qwen-image", "Qwen-Image-2.1"), (r"anima", "Anima"),
                 (r"acestep|ace_1\.5|ace15", "ACE-Step-1.5"), (r"yue2", "yue2"), (r"krea2", "Krea2"), (r"sd_xl|sdxl", "SDXL"), (r"sd3|clip_g", "SD3-SD3.5"),
                 (r"v1-5|sd15|dreamshaper", "SD15"), (r"z_image|z-image", "Z-Image"), (r"hunyuan", "HunyuanVideo"), (r"trellis", "TRELLIS-2-4B"),
                 (r"sam3|sam_3d", "sam3"), (r"birefnet", "upscale_models"), (r"esrgan|nomos|4x|2x", "upscale_models"), (r"qwen3\.5|\.gguf$", "Crew language models"),
                 (r"stable_audio|stable-audio", "Music (other)"), (r"umt5|t5xxl|clip_l|t5-base", "Shared text encoders")]


#: Short family names other lists use (LoRA recipes, the Music page), mapped to the Families page's names.
FAMILY_ALIASES = {"h3": "MiniMax-H3", "wan22": "Wan2.2", "wan21": "Wan2.1", "qwen": "Qwen-Image-2.1", "ltx": "LTX-2.5", "flux1": "Flux.1", "flux2": "Flux.2",
                  "krea2": "Krea2", "moss": "Moss-Image", "anima": "Anima", "z-image": "Z-Image", "ace-step-1-5": "ACE-Step-1.5", "mini-max-music3": "Mini-Max-Music3"}


def family_label(key, row, st):
    fams = sorted(row["families"])
    if "voices" in fams: return "Voices"
    users = row["used_by"]
    slug = {re.sub(r"[^a-z0-9]", "", k.lower()): k for k in st}
    fam_names = sorted({FAMILY_ALIASES.get(f) or slug.get(re.sub(r"[^a-z0-9]", "", f.lower())) or "" for f in fams} - {""})
    if fam_names: return fam_names[0]
    low = key.lower()
    for rx, fam in NAME_FAMILIES:
        if re.search(rx, low): return fam
    if any(u.startswith("music:") for u in users): return "Music (other)"
    if any(u.startswith("feature:studio/worldkit") for u in users): return "World Kit tools"
    if any(u.startswith("feature:studio/feature_motion") for u in users): return "Motion"
    return fams[0] if fams else "Other"


def used_by_line(users):
    """One plain line for a group's users."""
    kinds = {}
    for u in users:
        if u.startswith("goal:"): kinds.setdefault("goals", set()).add(u[5:])
        elif u.startswith("family:"): kinds.setdefault("family templates", set()).add(u.split("/", 1)[-1])
        elif u.startswith("lora-recipe:"): kinds.setdefault("LoRA recipes", set()).add(u.split(":", 1)[1])
        elif u.startswith(("recipe:", "pipeline:")): kinds.setdefault("recipes and pipelines", set()).add(u.split(":", 1)[1])
        elif u.startswith("music:"): kinds.setdefault("Music page", set()).add(u[6:])
        elif u.startswith("voice:"): kinds.setdefault("Voices page", set()).add(u[6:])
        elif u.startswith("feature:"): kinds.setdefault("features", set()).add(u[8:].removeprefix("studio/").removesuffix(".py"))
        elif u.startswith("studio/university/"): kinds.setdefault("University graphs", set()).add(u)
        elif "/pipelines/" in u: kinds.setdefault("pipeline graphs", set()).add(u)
        elif u.startswith("studio/family_templates/"): kinds.setdefault("studio templates", set()).add(Path(u).name)
        elif u.startswith("workflows/"): kinds.setdefault("workflows", set()).add(Path(u).name)
        else: kinds.setdefault("other graphs", set()).add(u)
    parts = []
    for k in ("goals", "workflows", "studio templates", "family templates", "recipes and pipelines", "pipeline graphs", "University graphs", "other graphs",
              "LoRA recipes", "Music page", "Voices page", "features"):
        v = kinds.get(k)
        if not v: continue
        if k in ("goals", "workflows", "features", "Music page") or len(v) <= 3: parts.append(f"{k} " + ", ".join(f"`{x}`" for x in sorted(v)[:8]) + (" ..." if len(v) > 8 else ""))
        else: parts.append(f"{len(v)} {k}")
    return "; ".join(parts)


def gib(n): return f"{n / 2**30:.2f}" if n else "?"


MD_START, MD_END = "<!-- model-files:start (scripts/build_model_links.py writes this part) -->", "<!-- model-files:end -->"


def models_md_section(files, built):
    groups = {}
    for f in files: groups.setdefault(f["family"], []).append(f)
    hf = sum(1 for f in files if f["source"] == "huggingface")
    gh = sum(1 for f in files if f["source"] == "github")
    ms = sum(1 for f in files if f["source"] == "modelscope")
    none = [f for f in files if f["source"] not in ("huggingface", "github", "modelscope")]
    civ = sum(1 for f in files if f["source"] == "civitai")
    civ_url = sum(1 for f in files if f.get("civitai_url"))
    gated = sum(1 for f in files if f.get("gated"))
    nc = sum(1 for f in files if f.get("noncommercial"))
    out = [MD_START, "", "## Every model file, with its download link", "",
           f"Every model file a shipped graph, template, recipe, pipeline, family or feature names: {len(files)} files. {hf} have an official download checked "
           f"against the Hugging Face API on {built} (the file is in the repository's listing; size and SHA-256 are from that listing); {gh} are release "
           f"assets of the project on GitHub (size checked, no published SHA-256); and {ms} is on ModelScope (SHA-256 matched). {gated} sit in gated "
           f"repositories (accept the licence on the model page and set `HF_TOKEN`), and {nc} are under a licence the card marks non-commercial or research-only. "
           f"{len(none)} have no download the helper can fetch: {civ} are on Civitai only ({civ_url} with their Civitai page, confirmed by SHA-256 or by file name and "
           f"size), {sum(1 for f in files if f['source'] == 'trained here')} were trained here, and {sum(1 for f in files if f['source'] == 'none')} have no public source we could find. They are listed at the end of "
           "their family's table. The same data is in "
           "[`studio/models_manifest.json`](studio/models_manifest.json) under `files`.", "",
           "**Get them:** `python3 scripts/get_models.py --for all --dry-run` lists what is missing; drop `--dry-run` to download. "
           "`--for image` (a goal), `--for family:Anima` (a family) or `--for flux-2-klein-4b.safetensors` (one file) narrow it. "
           "It resumes, checks SHA-256, skips files already in place, and reads `HF_TOKEN` only from the environment.", "",
           "Licence here is the Hugging Face card's own field. The family tables above say what each licence limits; read the licence before you rely on it.", ""]
    for fam in sorted(groups, key=lambda s: s.lower()):
        rows = sorted(groups[fam], key=lambda f: (f["source"] not in ("huggingface", "github", "modelscope"), f["filename"].lower()))
        users = sorted({u for f in rows for u in f["used_by"]})
        total = sum(f.get("size") or 0 for f in rows)
        out += [f"### {fam}", "", f"Used by: {used_by_line(users)}.", "", "| File | Put it in | GiB | Licence | Download |", "|---|---|---|---|---|"]
        for f in rows:
            if f["source"] == "github":
                lic, link = f.get("licence") or "unknown", f"[GitHub release]({f['url']})"
            elif f["source"] == "modelscope":
                lic, link = "not stated", f"[ModelScope {f['repo']}]({f['url']}), published as `{Path(f['path']).name}`"
            elif f["source"] == "civitai" and f.get("civitai_url"):
                lic = "see the Civitai page"
                link = f"Civitai only: [{(f.get('civitai_name') or 'model page').replace('|', '/')}]({f['civitai_url']}) (matched by {f.get('civitai_checked')})"
            elif f["source"] == "huggingface":
                lic = f["licence"] + (" (non-commercial)" if f.get("noncommercial") else "")
                link = f"[{f['repo']}]({f['url']})" + (" (gated)" if f.get("gated") else "") + (f", published as `{Path(f['path']).name}`" if f.get("saved_as") else "") \
                    + (" (community upload)" if f.get("publisher") == "community" else "") + (" (matched by file name only)" if (f.get("checked") or "").startswith("same file name") else "")
            else:
                lic = "unknown"
                link = {"other": f"[link, not checked]({f.get('url')})", "civitai": "Civitai only; no Hugging Face copy found",
                        "trained here": "Trained with the studio's Train page; not published"}.get(f["source"], "No public source found")
            out.append(f"| `{f['filename']}` | `{f.get('dest') or f.get('folder') or '?'}` | {gib(f.get('size'))} | {lic} | {link} |")
        out += ["", f"{len(rows)} files, {gib(total)} GiB with a known size.", ""]
    out.append(MD_END)
    return "\n".join(out)


def rewrite_md(root=ROOT):
    """Regenerate the MODELS.md section from the manifest as it is, without reading the network."""
    man = json.loads((root / "studio/models_manifest.json").read_text())
    write_outputs(root, man["files"], man["files_built"])


def write_outputs(root, files, built):
    man_path = root / "studio/models_manifest.json"
    man = json.loads(man_path.read_text())
    man["files_built"] = built
    man["files_source"] = "Hugging Face API model listings (studio/model_inventory.py names the files; scripts/build_model_links.py finds and checks the links)"
    man["files"] = files
    man_path.write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n")
    md_path = root / "MODELS.md"
    md = md_path.read_text()
    sec = models_md_section(files, built)
    if MD_START in md:
        md = md[:md.index(MD_START)] + sec + md[md.index(MD_END) + len(MD_END):]
    else:
        md = md.rstrip() + "\n\n" + sec + "\n"
    md_path.write_text(md)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plans", nargs="*", default=[], help="download plans (TSV with repo, path, sha and rel columns); globs allowed")
    ap.add_argument("--catalog", nargs="*", default=[], help="folders or JSON files with ComfyUI template model metadata")
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "parametric-studio" / "model-links"))
    ap.add_argument("--offline", action="store_true", help="use only the cache")
    ap.add_argument("--authors", nargs="*", default=["Comfy-Org", "Kijai", "lightx2v", "Lightricks", "MiniMaxAI", "black-forest-labs", "stabilityai"],
                    help="Hugging Face accounts whose whole listings are searched by file name")
    ap.add_argument("--report", help="also write the file list as TSV here")
    ap.add_argument("--leads", nargs="*", default=[], help="research tables (TSV: source, repo, status, take_files) naming repos files came from")
    ap.add_argument("--sizes", nargs="*", default=[], help="inventory tables recording each file's byte size, for files no longer on disk (Civitai name lookups must match it)")
    ap.add_argument("--md-only", action="store_true", help="only rewrite the MODELS.md section from the manifest as it stands")
    ap.add_argument("--local-root", nargs="*", default=[], help="a models folder holding copies of the files: a copy saved under another name is matched by size, then SHA-256")
    a = ap.parse_args(argv)
    if a.md_only:
        rewrite_md(); return
    plans = [p for g in a.plans for p in (sorted(glob.glob(g)) or [g])]
    files = build(ROOT, plans, a.catalog, a.cache, a.offline, authors=a.authors, local_root=a.local_root, leads=a.leads, sizes=a.sizes)
    built = time.strftime("%Y-%m-%d")
    write_outputs(ROOT, files, built)
    none = [f for f in files if f["source"] not in ("huggingface", "github", "modelscope")]
    print(f"{len(files)} files: {len(files) - len(none)} with a checked public download, {len(none)} without "
          f"({sum(1 for f in none if f['source'] == 'civitai')} Civitai, {sum(1 for f in none if f.get('civitai_url'))} of them with a page; "
          f"{sum(1 for f in none if f['source'] == 'none')} not found; {sum(1 for f in none if f['source'] == 'trained here')} trained here)")
    if a.report:
        with open(a.report, "w", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            w.writerow(["filename", "family", "source", "repo", "path", "size", "licence", "gated", "used_by"])
            for f in files: w.writerow([f["filename"], f["family"], f["source"], f.get("repo"), f.get("path"), f.get("size"), f.get("licence"), f.get("gated"), len(f["used_by"])])


if __name__ == "__main__":
    main()
