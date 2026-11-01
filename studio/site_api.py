import html
import os
import re
import urllib.parse
import secrets
import mimetypes
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from psn.sitebuilder import style
from psn.sitebuilder.build import brief_problems, build_site, css as site_css, placeholder_svg

router = APIRouter()

SITE_ID_RE = re.compile(r"^[0-9a-f]{12}$")


def _sites_root() -> Path:
    root = os.environ.get("STUDIO_SITES", os.path.expanduser("~/studio_sites"))
    p = Path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _site_dir(site_id: str) -> Path:
    return _sites_root() / site_id


def _safe_resolve(site_id: str, rel_path: str) -> Path | None:
    """Resolve a relative path within the site directory, rejecting traversal."""
    if not SITE_ID_RE.match(site_id):
        return None
    site_dir = _site_dir(site_id)
    if not site_dir.is_dir():
        return None
    # Reject absolute paths
    if rel_path.startswith("/"):
        return None
    # Reject null bytes
    if "\0" in rel_path:
        return None
    # Resolve the path
    target = (site_dir / rel_path).resolve()
    # Ensure it's inside the site directory
    try:
        target.relative_to(site_dir.resolve())
    except ValueError:
        return None
    return target


class BuildRequest(BaseModel):
    brief: Dict[str, Any]


def preview_html(brief: Dict[str, Any]) -> str:
    """The page as it stands while the brief is being typed: the real stylesheet and colour rules, the brief's own name, pages and facts, no written copy. No model runs."""
    e = html.escape
    colour = brief.get("brand") if re.fullmatch(r"#[0-9a-fA-F]{6}", str(brief.get("brand") or "")) else "#3b6ea5"
    tokens = style.make_tokens(colour)
    name = str(brief.get("name") or "").strip() or "Your site"
    pages = [str(x).strip() for x in (brief.get("pages") or []) if str(x).strip()][:6] or ["Home"]
    facts = [(str(k).strip(), str(v).strip()) for k, v in (brief.get("facts") or {}).items() if str(k).strip() and str(v).strip()]
    voice = str(brief.get("voice") or "").strip()
    pic = "data:image/svg+xml," + urllib.parse.quote(placeholder_svg(tokens, name, "Picture to come"))
    nav = "".join(f"<a{' aria-current=page' if i == 0 else ''}>{e(x.title())}</a>" for i, x in enumerate(pages))
    fact_html = "".join(f"<p><b>{e(k)}.</b> {e(v)}</p>" for k, v in facts) or "<p>Your facts appear here as you add them.</p>"
    rest = "".join(f'<section><div><h2>{e(x.title())}</h2><p>The words for this page are written when you press Build.</p></div><img src="{pic}" alt=""></section>' for x in pages[1:])
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(name)}</title><style>{site_css(tokens)}</style></head><body>'
            f'<header><a class="brand">{e(name)}</a><nav aria-label="Main">{nav}</nav></header><main><section><div><h2>{e(name)}</h2><p>{e(voice) or "Add a brand voice and it shapes the words."}</p>{fact_html}</div><img src="{pic}" alt=""></section>{rest}</main><footer><p>{e(name)}</p></footer></body></html>')


@router.post("/api/site/preview")
def site_preview(req: BuildRequest):
    problems = brief_problems({**req.brief, "name": req.brief.get("name") or "x"})
    if problems:
        return JSONResponse(status_code=400, content={"problems": problems})
    return {"html": preview_html(req.brief)}


@router.post("/api/site/build")
def build_site_endpoint(req: BuildRequest):
    brief = req.brief
    problems = brief_problems(brief)
    if problems:
        return JSONResponse(status_code=400, content={"problems": problems})

    site_id = secrets.token_hex(6)
    out_dir = _site_dir(site_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = build_site(brief, str(out_dir))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    files = []
    problems_out = []

    if isinstance(result, dict):
        if 'files' in result:
            files = result['files']
        elif 'file_list' in result:
            files = result['file_list']
        else:
            for item in out_dir.rglob('*'):
                if item.is_file():
                    files.append(str(item.relative_to(out_dir)))

        if 'problems' in result:
            problems_out = result['problems']
        elif 'errors' in result:
            problems_out = result['errors']

    elif isinstance(result, list):
        files = result

    rel_files = []
    for f in files:
        if isinstance(f, str):
            rel_files.append(f.replace(os.sep, '/'))
        else:
            rel_files.append(str(Path(f).relative_to(out_dir)).replace(os.sep, '/'))

    return {
        "site_id": site_id,
        "files": rel_files,
        "problems": problems_out
    }


@router.get("/api/site/{site_id}")
async def list_site_files(site_id: str):
    if not SITE_ID_RE.match(site_id):
        raise HTTPException(status_code=404, detail="Not found")

    site_dir = _site_dir(site_id)
    if not site_dir.is_dir():
        raise HTTPException(status_code=404, detail="Not found")

    files = []
    for item in site_dir.rglob('*'):
        if item.is_file():
            files.append(str(item.relative_to(site_dir)).replace(os.sep, '/'))

    return {"files": files}


@router.get("/api/site/{site_id}/{path:path}")
async def serve_site_file(site_id: str, path: str):
    if not SITE_ID_RE.match(site_id):
        raise HTTPException(status_code=404, detail="Not found")

    target = _safe_resolve(site_id, path)
    if target is None or not target.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    media_type, _ = mimetypes.guess_type(str(target))
    if media_type is None:
        media_type = "application/octet-stream"

    return FileResponse(target, media_type=media_type)
