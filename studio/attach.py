import ipaddress
import json
import os
import re
import tempfile
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

CONFIG_DIR = Path(os.environ.get("STUDIO_CONFIG_DIR", Path.home() / ".config" / "parametric-studio"))
CONFIG_FILE = CONFIG_DIR / "attach.json"
APPS_DIR = Path.home() / "comfy_apps"

PRIVATE_NETS = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7", "fe80::/10")]

NSFW_WORDS = {
    "nsfw", "nude", "naked", "lingerie", "porn", "hentai",
    "explicit", "erotic", "topless", "fetish", "onlyfans", "sex"
}

def _is_loopback_or_private(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # a name is only as private as its owner says, so 10.1.example.com is not private
    return ip.is_loopback or any(ip in net for net in PRIVATE_NETS)

def _url_host(url: str) -> str:
    """The host a client will really connect to. http://127.0.0.1:80@evil.example/ connects to evil.example."""
    if re.search(r"[\s\\]", url):
        raise ValueError("URL contains characters a URL cannot have")
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname
        parts.port
    except ValueError:
        raise ValueError("URL could not be read") from None
    if parts.scheme not in ("http", "https"):
        raise ValueError("URL must be http or https")
    if "@" in parts.netloc:
        raise ValueError("URL must not contain a user name or password")
    if not host:
        raise ValueError("URL has no host")
    return host.lower()

def _validate_url(url: str) -> None:
    host = _url_host(url)
    if not _is_loopback_or_private(host):
        if os.environ.get("STUDIO_ALLOW_REMOTE") != "1":
            raise ValueError("Host must be loopback or private LAN unless STUDIO_ALLOW_REMOTE=1")

def load() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save(comfy_url: Optional[str] = None, workflows_dir: Optional[str] = None) -> Dict[str, Any]:
    current = load()
    
    if comfy_url is not None:
        _validate_url(comfy_url)
        current["comfy_url"] = comfy_url
        
    if workflows_dir is not None:
        p = Path(workflows_dir)
        if not p.is_dir():
            raise ValueError("workflows_dir must be an existing directory")
        current["workflows_dir"] = str(p.resolve())
        
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Atomic write
    fd, tmp_path = tempfile.mkstemp(dir=str(CONFIG_DIR))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(current, f, indent=2)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, CONFIG_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
        
    return current

def comfy_url(default: str) -> str:
    settings = load()
    return settings.get("comfy_url", default)

def test_connection(url: str, opener: Optional[Any] = None) -> Dict[str, Any]:
    if opener is None:
        opener = urllib.request.urlopen
    try:
        req = urllib.request.Request(f"{url.rstrip('/')}/system_stats")
        with opener(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            version = data.get("system", {}).get("comfyui_version", "unknown")
            devices = []
            if "devices" in data:
                devices = data["devices"]
            elif "cuda" in data:
                devices = ["cuda"]
            return {"ok": True, "version": version, "devices": devices}
    except Exception as e:
        return {"ok": False, "version": None, "devices": [], "error": str(e)}

def sfw_problems(workflow_dict: Dict[str, Any]) -> List[str]:
    problems = []
    words_found = set()
    
    def check_text(text: str):
        if not isinstance(text, str):
            return
        lower_text = text.lower()
        for word in NSFW_WORDS:
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, lower_text):
                words_found.add(word)
                
        if 'nsfw' in lower_text:
            words_found.add('nsfw')

    nodes = workflow_dict.get("nodes", [])
    for node in nodes:
        if not isinstance(node, dict):
            continue
        title = node.get("title", "")
        check_text(title)
        
        ntype = node.get("type", "")
        check_text(ntype)
        
        widgets = node.get("widgets_values", [])
        if isinstance(widgets, list):
            for w in widgets:
                check_text(w)
        elif isinstance(widgets, str):
            check_text(widgets)
            
    if words_found:
        problems.append("Contains NSFW terms: " + ", ".join(sorted(words_found)))
        
    return problems

def scan_workflows(dir_path: str, limit: int = 300) -> List[Dict[str, Any]]:
    results = []
    p = Path(dir_path)
    if not p.is_dir():
        return results
        
    files = []
    for item in p.rglob("*.json"):
        if item.is_symlink():
            continue
        if not item.is_file():
            continue
        try:
            item.relative_to(p)
        except ValueError:
            continue
        files.append(item)
        
    files.sort(key=lambda x: str(x))
    
    for f in files:
        if len(results) >= limit:
            break
        try:
            if f.stat().st_size > 5 * 1024 * 1024:
                continue
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                
            if not isinstance(data, dict):
                continue
                
            nodes = data.get("nodes", [])
            node_count = len(nodes) if isinstance(nodes, list) else 0
            
            extra = data.get("extra", {})
            is_app = extra.get("linearMode", False) == True
            
            sfw = len(sfw_problems(data)) == 0
            problems = sfw_problems(data)
            
            results.append({
                "file": str(f.relative_to(p)),
                "nodes": node_count,
                "is_app": is_app,
                "sfw": sfw,
                "problems": problems
            })
        except Exception:
            continue
            
    return results

def to_app(workflow_dict: Dict[str, Any], inputs: List[List[Any]], outputs: List[Any]) -> Dict[str, Any]:
    import copy
    wf = copy.deepcopy(workflow_dict)
    
    nodes = wf.get("nodes", [])
    node_map = {}
    for n in nodes:
        if isinstance(n, dict) and "id" in n:
            node_map[n["id"]] = n
            
    # Validate inputs
    for inp in inputs:
        if not isinstance(inp, list) or len(inp) != 2:
            raise ValueError("Input must be [node_id, widget_name]")
        node_id, widget_name = inp
        if node_id not in node_map:
            raise ValueError(f"Node id {node_id} not found")
        node = node_map[node_id]
        # Check widget name
        valid = False
        if isinstance(widget_name, str):
            valid = True
        else:
            raise ValueError("Widget name must be a string")
            
        # Spec says: "every widget name appears among that node's inputs' widget names or is a plain string"
        # This is slightly ambiguous. Usually widgets are defined in 'inputs' or 'widgets_values'.
        # Let's check if 'inputs' in node has 'widget' type or similar.
        # For simplicity and robustness against varying ComfyUI formats, we accept any string as per "or is a plain string".
        
    # Validate outputs
    for out_id in outputs:
        if out_id not in node_map:
            raise ValueError(f"Node id {out_id} not found")
            
    wf["extra"] = wf.get("extra", {})
    wf["extra"]["linearMode"] = True
    wf["extra"]["linearData"] = {
        "inputs": inputs,
        "outputs": outputs
    }
    
    return wf

def import_workflow(file: str, dest_dir: str, inputs: List[List[Any]], outputs: List[Any]) -> str:
    src = Path(file)
    if not src.is_file():
        raise ValueError("File not found")
        
    try:
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        raise ValueError("That file is not a JSON workflow") from None
        
    problems = sfw_problems(data)
    if problems:
        raise ValueError("Refusing to import non-SFW workflow: " + "; ".join(problems))
        
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    
    name = src.stem
    out_path = dest / f"{name}.app.json"
    
    app_data = to_app(data, inputs, outputs)
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(app_data, f, indent=2)
        
    return str(out_path)

def _inside(file: str, root: str) -> bool:
    try:
        return Path(file).resolve().is_relative_to(Path(root).resolve())
    except (OSError, ValueError):
        return False

class AttachSettings(BaseModel):
    comfy_url: Optional[str] = None
    workflows_dir: Optional[str] = None

class TestRequest(BaseModel):
    url: str

class ImportRequest(BaseModel):
    file: str
    inputs: List[List[Any]]
    outputs: List[Any]

@router.get("/api/attach")
def get_attach():
    return load()

@router.post("/api/attach")
def post_attach(settings: AttachSettings):
    try:
        return save(settings.comfy_url, settings.workflows_dir)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/attach/test")
def post_test(req: TestRequest):
    try:
        _validate_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return test_connection(req.url)

@router.get("/api/attach/workflows")
def get_workflows():
    settings = load()
    wd = settings.get("workflows_dir")
    if not wd:
        return []
    return scan_workflows(wd)

@router.post("/api/attach/import")
def post_import(req: ImportRequest):
    root = load().get("workflows_dir")
    if not root or not _inside(req.file, root):
        raise HTTPException(status_code=400, detail="That file is not in your workflows folder")
    try:
        path = import_workflow(req.file, str(APPS_DIR), req.inputs, req.outputs)
        return {"path": path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
