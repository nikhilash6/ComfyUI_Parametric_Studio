"""Swap on any model: every graph in this repo that swaps a person (a whole character, a performer, or an outfit), side by side, each with its core model, a render made here and its licence.
The rows live in studio/swap_showcase.json; the README's table is written from the same file by scripts/build_swap_table.py, so the two cannot drift. A row is offered as done only when its graph and its render are both in the repo;
a graph whose proof is still being rendered is listed as coming, with no picture. Nothing here runs a model: each row opens the page that does (Create, Motion or Try-on).
GET /api/swap (the rows) and /api/swap/graph/{id} (the row's graph, as ComfyUI API JSON)."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/swap")
PAGE = {"tab": "swap", "label": "Swap", "title": ["Swap on any model", "Swap the person. Pick the model.", "Every graph here that swaps a character, a performer or an outfit, each with a render made on our card, its time, its peak memory and its licence. Invented adults only."], "module": "swap.js", "export": "Swap", "css": "swap.css"}
ROOT = Path(__file__).resolve().parent; REPO = ROOT.parent; DATA = ROOT / "swap_showcase.json"; WEB = ROOT / "web"


def rows():
    """The rows, each told whether its graph and render are really here. A rendered row missing either is shown as coming instead of as done."""
    d = json.loads(DATA.read_text(encoding="utf-8")); out = []
    for r in d["rows"]:
        r = dict(r); graph_here = (REPO / r["graph"]).is_file()
        proof = r.get("proof") or {}; proof_here = bool(proof) and (WEB / proof["src"]).is_file() and (WEB / proof.get("poster", proof["src"])).is_file()
        if r["status"] == "rendered" and not (graph_here and proof_here): r["status"] = "coming"
        if r["status"] != "rendered": r.pop("proof", None); r.pop("looked", None); r.pop("flaw", None)
        r["graph_here"] = graph_here; out.append(r)
    return {"about": d["about"], "checked": d["checked"], "rows": out}


@router.get("")
def swap_rows(): return rows()


@router.get("/graph/{rid}")
def swap_graph(rid: str):
    r = next((x for x in rows()["rows"] if x["id"] == rid), None)
    if not r or not r["graph_here"]: raise HTTPException(404, "No graph with that id is in this copy of the studio.")
    return json.loads((REPO / r["graph"]).read_text(encoding="utf-8"))
