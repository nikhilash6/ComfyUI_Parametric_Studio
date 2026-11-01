import json
import os
import re
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from psn import paths
from studio import sfw

router = APIRouter()

# Cache state
_cache = {
    "timestamp": 0,
    "data": None
}
CACHE_TTL = 60
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lora_recipes.json")
_curated = {}

def curated() -> List[Dict[str, Any]]:
    """The tuned LoRA recipes this edition carries: safe for work, no real people, each with its licence and its proof level as recorded."""
    m = os.path.getmtime(DATA)
    if _curated.get("m") != m: _curated.update(m=m, rows=json.load(open(DATA))["loras"])
    return _curated["rows"]

def by_id(rid: str) -> Optional[Dict[str, Any]]:
    return next((r for r in curated() if r["id"] == rid), None)

def apply_to_graph(graph: Dict[str, Any], ask: Dict[str, Any]) -> Dict[str, Any]:
    """Put one curated LoRA into an H3 graph with its tuned settings: its loader right after the model, the base, steps, sampler, scheduler and size its recipe names. Only a LoRA from the curated list can be asked for, by id."""
    row = by_id(str((ask or {}).get("id") or ""))
    if not row or not row.get("run"): raise HTTPException(400, "this LoRA is not one this studio can run")
    run = row["run"]
    try: strength = float(ask.get("strength", run["strength"]))
    except (TypeError, ValueError): raise HTTPException(400, "the LoRA strength must be a number") from None
    strength = max(-10.0, min(10.0, strength))
    unet = next((k for k, n in graph.items() if n["class_type"] == "UNETLoader"), None)
    if not unet: raise HTTPException(400, "this graph has no model to put a LoRA on")
    graph[unet]["inputs"]["unet_name"] = run["base"]; nid = "lora_recipe"
    for k, n in graph.items():
        for key, v in n["inputs"].items():
            if v == [unet, 0]: n["inputs"][key] = [nid, 0]
    graph[nid] = {"class_type": run["loader"], "inputs": {"model": [unet, 0], "lora_name": row["path"], "strength_model": strength}}
    for n in graph.values():
        i = n["inputs"]
        if n["class_type"] == "KSamplerSelect": i["sampler_name"] = run["sampler"]
        elif n["class_type"] == "ResolutionSelector" and run.get("megapixels"): i["megapixels"] = run["megapixels"]
        elif n["class_type"] == "BasicScheduler":
            i["scheduler"] = run["scheduler"]; st = i.get("steps")
            if isinstance(st, list) and graph.get(st[0], {}).get("class_type") == "ComfySwitchNode": st = graph[st[0]]["inputs"].get("on_false")          # the quality side of the speed switch
            if isinstance(st, list) and graph.get(st[0], {}).get("class_type") == "PrimitiveInt": graph[st[0]]["inputs"]["value"] = int(run["steps"])
            elif not isinstance(st, list): i["steps"] = int(run["steps"])
    return graph

def _get_models_root() -> str:
    return paths.models_root(True)

def _is_sfw(name: str) -> bool:
    """
    Returns False if the name contains SFW-violating keywords.
    Word-boundary aware for short keywords like 'sex'.
    """
    lower_name = name.lower()
    
    # Keywords that require word boundaries to avoid false positives (e.g., 'sex' in 'essex')
    boundary_keywords = [
        "sex", "18+"
    ]
    
    if sfw.flagged(name.replace("_", " ").replace("-", " ")):
        return False

    # Keywords that can be substring matches
    substring_keywords = [
        "nsfw", "eros", "nude", "naked", "lingerie", "porn", "hentai", 
        "explicit", "erotic", "onlyfans", "topless"
    ]
    
    # Check substring keywords
    for kw in substring_keywords:
        if kw in lower_name:
            return False
            
    # Check boundary keywords
    for kw in boundary_keywords:
        # Use regex with word boundaries. 
        # Note: '18+' contains '+', which is not a word char, so we need to be careful.
        # \b works around word chars. '18+' -> \b18\+
        # 'sex' -> \bsex\b
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, lower_name):
            return False
            
    return True

def _guess_family(name: str) -> str:
    """
    Guesses the family from path/name keywords.
    """
    lower_name = name.lower()
    
    # Order matters: more specific first? 
    # Spec: h3/minimax-h3 -> 'MiniMax H3', music3 -> 'MiniMax Music 3', ltx -> 'LTX', 
    # flux -> 'FLUX', wan -> 'Wan', anima -> 'Anima', qwen -> 'Qwen-Image', 
    # sdxl/pony/illustrious -> 'SDXL', else 'Other'
    
    if "h3" in lower_name or "minimax-h3" in lower_name:
        return "MiniMax H3"
    if "music3" in lower_name:
        return "MiniMax Music 3"
    if "ltx" in lower_name:
        return "LTX"
    if "flux" in lower_name:
        return "FLUX"
    if "wan" in lower_name:
        return "Wan"
    if "anima" in lower_name:
        return "Anima"
    if "qwen" in lower_name:
        return "Qwen-Image"
    if "sdxl" in lower_name or "pony" in lower_name or "illustrious" in lower_name:
        return "SDXL"
    if "sd15" in lower_name or "sd1.5" in lower_name:
        return "SD 1.5"
        
    return "Other"

def _guess_kind(name: str) -> str:
    """
    Guesses the kind from path/name keywords.
    """
    lower_name = name.lower()
    
    # Spec: 
    # 'camera' for dolly/zoom/handheld/orbit/pan/fpv
    # 'style' for style/anime/cel/toon/retro/film/cinematic
    # 'character' for character/swap/identity
    # 'speed' for turbo/8step/4step/acc/hyperflow/distill
    # 'music' for genres in the music3 folder
    # else 'other'
    
    camera_keywords = ["dolly", "zoom", "handheld", "orbit", "pan", "fpv"]
    style_keywords = ["style", "anime", "cel", "toon", "retro", "film", "cinematic"]
    character_keywords = ["character", "swap", "identity"]
    speed_keywords = ["turbo", "8step", "4step", "acc", "hyperflow", "distill"]
    
    # Check music first? Spec says "music for genres in the music3 folder".
    # This implies if it's in the music3 folder, it's music.
    # Let's check if 'music3' is in the path.
    if "music3" in lower_name:
        return "music"
        
    for kw in camera_keywords:
        if kw in lower_name:
            return "camera"
            
    for kw in style_keywords:
        if kw in lower_name:
            return "style"
            
    for kw in character_keywords:
        if kw in lower_name:
            return "character"
            
    for kw in speed_keywords:
        if kw in lower_name:
            return "speed"
            
    return "other"

def scan(root: str, limit: int = 5000) -> List[Dict[str, Any]]:
    """
    Scans the models root for LoRA files.
    """
    loras_dir = os.path.join(root, "loras")
    if not os.path.exists(loras_dir):
        return []
        
    items = []
    count = 0
    
    for dirpath, dirnames, filenames in os.walk(loras_dir, followlinks=False):
        # Prune directories if we've hit the limit? 
        # The limit is on the number of items returned.
        # We should still walk to find all, but stop adding if limit reached.
        
        for filename in filenames:
            if count >= limit:
                return items
                
            # Check extension
            if not filename.endswith(".safetensors"):
                continue
                
            # Construct relative path from loras_dir
            full_path = os.path.join(dirpath, filename)
            
            # Check if it's a symlink pointing outside root
            # os.path.realpath resolves symlinks. 
            # We need to ensure the real path is within the real loras_dir.
            real_loras_dir = os.path.realpath(loras_dir)
            real_file_path = os.path.realpath(full_path)
            
            # Check if real_file_path starts with real_loras_dir
            # Use os.path.commonpath or startswith with separator
            if not real_file_path.startswith(real_loras_dir + os.sep) and real_file_path != real_loras_dir:
                continue
                
            # Calculate relative path
            rel_path = os.path.relpath(full_path, loras_dir)
            
            # SFW check
            if not _is_sfw(rel_path):
                continue
                
            # Get size
            try:
                size_bytes = os.path.getsize(full_path)
                size_mb = size_bytes / (1024 * 1024)
            except OSError:
                continue
                
            item = {
                "name": rel_path,
                "file": filename,
                "family": _guess_family(rel_path),
                "kind": _guess_kind(rel_path),
                "size_mb": round(size_mb, 2)
            }
            items.append(item)
            count += 1
            
    return items

def search(items: List[Dict[str, Any]], q: str = '', family: Optional[str] = None, kind: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Filters and sorts items.
    """
    results = []
    q_lower = q.lower()
    q_words = q_lower.split() if q_lower else []
    
    for item in items:
        # Filter by family
        if family and item["family"] != family:
            continue
            
        # Filter by kind
        if kind and item["kind"] != kind:
            continue
            
        # Filter by search query
        if q_words:
            name_lower = item["name"].lower()
            # All words must be present
            if not all(word in name_lower for word in q_words):
                continue
                
        results.append(item)
        
    # Sort: exact-family matches first, then by name
    # "exact-family matches" likely means if a family filter was applied, those are the only ones, 
    # but the spec says "sorted with exact-family matches first then by name".
    # This phrasing is slightly ambiguous. 
    # Interpretation 1: If family filter is active, all are exact. 
    # Interpretation 2: Maybe it means items where the family keyword is explicitly in the name?
    # Let's re-read: "sorted with exact-family matches first then by name".
    # Given the context of a library, it probably means: 
    # If you search for "flux", items with family "FLUX" come first? 
    # Or maybe it's just a stable sort by name, but prioritizing items that match the family filter?
    # Actually, looking at the spec again: `search(items, q='', family=None, kind=None, limit=50)`.
    # If family is provided, we already filtered. 
    # Perhaps it means: sort by (family != 'Other' ? 0 : 1, name)? No.
    # Let's assume it means: sort by name, but if a family filter is active, 
    # maybe it implies a specific ordering?
    # Let's look at the "exact-family matches" phrase. 
    # Maybe it means: if the query matches the family name exactly?
    # Let's stick to a simple interpretation: Sort by name. 
    # But wait, "exact-family matches first". 
    # If I search for "flux", and I have "flux-lora" (family FLUX) and "my-flux-style" (family Other, but contains flux), 
    # the FLUX one should come first?
    # Let's implement: 
    # 1. If family filter is active, all items have that family. 
    # 2. If no family filter, maybe items whose family matches a word in q come first?
    # Let's try: 
    # Primary sort key: 0 if (family and item['family'] == family) or (q and item['family'].lower() in q_lower) else 1
    # Secondary sort key: name
    
    def sort_key(item):
        # If family filter is active, all are "exact"
        if family:
            family_priority = 0
        else:
            # If q is active, check if family name is in q
            if q_lower and item["family"].lower() in q_lower:
                family_priority = 0
            else:
                family_priority = 1
                
        return (family_priority, item["name"])
        
    results.sort(key=sort_key)
    
    return results[:limit]

@router.get("/api/loras")
def get_loras(
    q: str = Query(""),
    family: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=5000)
):
    """The LoRA files on disk that this edition has a curated recipe for. A file's name alone cannot show it is safe for work, so anything else is counted, never listed."""
    now = time.time()
    if _cache["data"] is None or (now - _cache["timestamp"]) > CACHE_TTL:
        root = _get_models_root()
        all_items = scan(root)
        _cache["data"] = all_items
        _cache["timestamp"] = now

    known = {r["path"]: r for r in curated()}
    on_disk = _cache["data"]
    all_items = [{**i, "recipe": known[i["name"]]["id"], "proof": known[i["name"]]["proof"]["level"], "licence": known[i["name"]]["licence"]} for i in on_disk if i["name"] in known]
    
    # Calculate families and kinds counts from ALL items (unfiltered)
    families = {}
    kinds = {}
    for item in all_items:
        fam = item["family"]
        kin = item["kind"]
        families[fam] = families.get(fam, 0) + 1
        kinds[kin] = kinds.get(kin, 0) + 1
        
    # Search
    filtered = search(all_items, q=q, family=family, kind=kind, limit=limit)
    
    return {
        "items": filtered,
        "families": families,
        "kinds": kinds,
        "other_files": len(on_disk) - len(all_items),
    }
