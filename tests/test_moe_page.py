"""Inside a mixture of experts: the routing record is checked when packed, served as static files, and read by the page with no model.
Records here are tiny and made in memory; no test loads a model, opens a GPU or touches a live port."""
import gzip, importlib.util, json, shutil, subprocess, tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from studio import feature_moe as F

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "studio" / "web"
DATA = ROOT / "studio" / "moe"
BOX = ["/" + "mnt/", "/" + "home/", "/" + "tmp/"]
spec = importlib.util.spec_from_file_location("pack_moe_routing", ROOT / "scripts" / "pack_moe_routing.py"); P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)

L, E, K = 2, 8, 2
META = {"model": "toy", "license": "apache-2.0", "layers": L, "experts": E, "top_k": K, "norm_topk_prob": True, "hidden": 4, "moe_intermediate": 2, "recorded": "2026-11-02", "secret_path": "/" + "home/x"}


def toy(tokens=("a", "b", "c")):
    T = len(tokens)
    prompt = {"id": "p1", "label": "Toy", "text": "".join(tokens), "tokens": list(tokens), "token_ids": list(range(T)),
              "experts": [[[t % E, (t + 1) % E] for _ in range(L)] for t in range(T)], "weights": [[[700, 300] for _ in range(L)] for _ in range(T)], "entropy": [[1.0] * L for _ in range(T)]}
    count = [[0] * E for _ in range(L)]
    for l in range(L): count[l][0] += 3; count[l][1] += 3
    load = {"meta": {**META, "corpus_tokens": 3}, "categories": {"Prose": {"tokens": 3, "texts": 1, "count": count, "weight": count}}, "top_tokens": [[[["a", 2]] if e < 2 else [] for e in range(E)] for _ in range(L)]}
    return {"meta": META, "prompts": [prompt]}, load


def test_pack_keeps_what_the_page_reads_and_drops_the_rest():
    r, l = toy(); out = P.pack(r, l)
    idx = json.loads(out["index.json"]); prompts = json.loads(out["prompts.json.gz"]); load = json.loads(out["load.json.gz"])
    assert idx["meta"]["license"] == "apache-2.0" and "secret_path" not in idx["meta"] and idx["meta"]["corpus_tokens"] == 3
    assert idx["prompts"] == [{"id": "p1", "label": "Toy", "tokens": 3}] and "token_ids" not in prompts["p1"]
    assert load["categories"][0]["name"] == "Prose" and "weight" not in load["categories"][0]


@pytest.mark.parametrize("bad", ["dup", "range", "sum", "order", "short", "count"])
def test_pack_refuses_a_record_that_is_not_top_k_routing(bad):
    r, l = toy(); p = r["prompts"][0]
    if bad == "dup": p["experts"][0][0] = [3, 3]
    if bad == "range": p["experts"][0][0] = [0, E]
    if bad == "sum": p["weights"][0][0] = [500, 300]
    if bad == "order": p["weights"][0][0] = [300, 700]
    if bad == "short": p["experts"][1] = p["experts"][1][:1]
    if bad == "count": l["categories"]["Prose"]["count"][0][0] += 1
    with pytest.raises(AssertionError): P.pack(r, l)


def test_pack_refuses_a_path_from_the_recording_machine():
    r, l = toy(("a", "/" + "home/someone/x", "c"))
    with pytest.raises(SystemExit): P.pack(r, l)


def test_the_endpoints_serve_the_packed_files(tmp_path, monkeypatch):
    from studio import server as S
    r, l = toy(); out = P.pack(r, l)
    for name, text in out.items(): (tmp_path / name).write_bytes(gzip.compress(text.encode()) if name.endswith(".gz") else text.encode())
    monkeypatch.setattr(F, "DATA", tmp_path); F._cache.clear(); c = TestClient(S.app)
    assert c.get("/api/moe").json()["meta"]["experts"] == E
    assert c.get("/api/moe/prompt/p1").json()["tokens"] == ["a", "b", "c"] and c.get("/api/moe/prompt/nope").status_code == 404
    assert c.get("/api/moe/load").json()["categories"][0]["tokens"] == 3
    monkeypatch.setattr(F, "DATA", tmp_path / "none"); F._cache.clear()
    assert c.get("/api/moe").status_code == 404 and c.get("/api/moe/load").status_code == 404
    F._cache.clear()


def test_the_page_is_wired_and_the_demo_saves_it():
    assert F.PAGE["tab"] == "moe" and (WEB / F.PAGE["module"]).exists() and (WEB / F.PAGE["css"]).exists()
    src = (ROOT / "scripts" / "build_pages.py").read_text(); assert '"moe/load"' in src and 'save("moe")' in src and '"moe/prompt/"' in src
    page = (WEB / "moe.js").read_text(); assert "Apache-2.0" in page and "huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Captioner" in page


def test_the_record_on_disk_is_real_routing_and_clean():
    idx = json.loads((DATA / "index.json").read_text(encoding="utf8"))
    raw_p = gzip.decompress((DATA / "prompts.json.gz").read_bytes()).decode("utf8"); raw_l = gzip.decompress((DATA / "load.json.gz").read_bytes()).decode("utf8")
    assert not any(x in json.dumps(idx) + raw_p + raw_l for x in BOX)
    m = idx["meta"]; assert (m["layers"], m["experts"], m["top_k"], m["license"]) == (48, 128, 8, "apache-2.0") and m["path"].startswith("text only")
    prompts = json.loads(raw_p); assert [p["id"] for p in idx["prompts"]] == list(prompts) and len(prompts) >= 6
    for p in prompts.values(): P.check_prompt(p, 48, 128, 8)
    load = json.loads(raw_l); assert len(load["categories"]) == len(idx["categories"]) >= 6
    for c in load["categories"]: assert all(sum(row) == c["tokens"] * 8 for row in c["count"])
    used = sum(1 for e in range(128) if any(c["count"][24][e] for c in load["categories"])); assert used > 100      # a real router spreads its work


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_the_page_logic():
    code = r'''
import * as M from "./moe_logic.js"; import assert from "node:assert";
assert.deepEqual(M.parseRoute("moe"), { prompt: null }); assert.deepEqual(M.parseRoute("moe/code"), { prompt: "code" });
assert.equal(M.showPiece(" total"), "␣total"); assert.equal(M.showPiece("):\n"), "):↵"); assert.equal(M.showPiece(""), "↳");
const p = { experts: [[[1, 2], [3, 4]], [[2, 5], [3, 4]]], weights: [[[600, 400], [500, 500]], [[900, 100], [700, 300]]] };
assert.deepEqual(M.pick(p, 0, 0), [{ e: 1, w: 0.6 }, { e: 2, w: 0.4 }]); assert.equal(M.overlap(p, 0, 1, 0), 1); assert.equal(M.overlap(p, 0, 1, 1), 2); assert.equal(M.meanOverlap(p, 0, 1), 1.5);
const cats = [{ name: "A", tokens: 2, count: [[4, 0, 0, 0]] }, { name: "B", tokens: 2, count: [[0, 2, 2, 0]] }];
const all = M.combine(cats, []); assert.equal(all.tokens, 4); assert.deepEqual(all.count, [[4, 2, 2, 0]]); assert.deepEqual(M.combine(cats, ["B"]).count, [[0, 2, 2, 0]]);
assert.deepEqual(M.shares(all, 2), [[0.5, 0.25, 0.25, 0]]);
assert.ok(Math.abs(M.balance([1, 1, 1, 1]) - 1) < 1e-9); assert.equal(M.balance([5, 0, 0, 0]), 0); assert.equal(M.balance([0, 0]), null);
assert.equal(M.heat(1 / 128, 128), 0.5); assert.equal(M.heat(0, 128), 0); assert.equal(M.heat(4 / 128, 128), 1); assert.equal(M.heat(1 / 512, 128), 0);
assert.deepEqual(M.heatRGB(0), [11, 16, 13]); assert.deepEqual(M.heatRGB(1), [255, 236, 170]);
const sp = M.specialists(cats, 0, 2, 6, 1); assert.equal(sp[0].e, 0); assert.equal(sp[0].cat, "A"); assert.equal(sp[0].ratio, 2); assert.equal(new Set(sp.map((r) => r.e)).size, sp.length);
assert.deepEqual(M.cellAt(10, 5, 100, 48, 48, 128), { l: 5, e: 12 }); assert.equal(M.cellAt(-1, 0, 100, 48, 48, 128), null);
const ep = M.expertParams({ hidden: 2048, moe_intermediate: 768, experts: 128, top_k: 8, layers: 48 }); assert.equal(ep.perExpert, 4718592); assert.equal(ep.activeLayers, 4718592 * 8 * 48);
console.log("ok");
'''
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(WEB / "moe_logic.js", t); (Path(t) / "x.mjs").write_text(code)
        p = subprocess.run(["node", str(Path(t) / "x.mjs")], cwd=t, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and "ok" in p.stdout, p.stderr
