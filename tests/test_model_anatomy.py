"""Model Anatomy reads headers only, counts only what they hold, and says what they can't. Files here are made in a temp folder; no test reads a real model or a live port."""
import gzip, json, os, shutil, struct, subprocess, sys, tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from studio import anatomy as A, feature_anatomy as F

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "studio" / "web"
BOX = ["/" + "mnt/", "/" + "home/"]


def st_file(path, tensors, meta=None, blobs=None):
    """A real safetensors file: header, then data. Data is zeros except the named blobs (the comfy_quant descriptors)."""
    blobs = blobs or {}; h, off, data = {}, 0, b""
    for name, (dt, shape) in tensors.items():
        n = int(A.ST_BYTES[dt] * max(1, __import__("math").prod(shape)) if shape else A.ST_BYTES[dt])
        raw = blobs.get(name, b"\0" * n); h[name] = {"dtype": dt, "shape": shape, "data_offsets": [off, off + len(raw)]}; off += len(raw); data += raw
    if meta: h["__metadata__"] = meta
    j = json.dumps(h).encode()
    Path(path).write_bytes(struct.pack("<Q", len(j)) + j + data)
    return path


def gguf_file(path):
    s = lambda t: struct.pack("<Q", len(t)) + t.encode()
    kv = s("general.architecture") + struct.pack("<I", 8) + s("toy") + s("toy.vocab") + struct.pack("<I", 9) + struct.pack("<IQ", 6, 3) + struct.pack("<3f", 1, 2, 3)
    t1 = s("blk.0.attn_q.weight") + struct.pack("<I", 2) + struct.pack("<QQ", 64, 32) + struct.pack("<I", 8) + struct.pack("<Q", 0)       # Q8_0, 64 wide, 32 rows
    t2 = s("blk.0.ffn_up.weight") + struct.pack("<I", 2) + struct.pack("<QQ", 64, 128) + struct.pack("<I", 1) + struct.pack("<Q", 4096)     # F16
    Path(path).write_bytes(b"GGUF" + struct.pack("<IQQ", 3, 2, 2) + kv + t1 + t2 + b"\0" * 64)
    return path


def test_a_transformer_header_is_counted_and_split(tmp_path):
    t = {}
    for i in range(3):
        t |= {f"model.diffusion_model.blocks.{i}.attn.qkv.weight": ("BF16", [96, 32]), f"model.diffusion_model.blocks.{i}.mlp.fc1.weight": ("BF16", [128, 32]), f"model.diffusion_model.blocks.{i}.norm1.weight": ("F32", [32])}
    t["model.diffusion_model.blocks.2.extra.weight"] = ("BF16", [4, 4])          # block 2 is built differently
    t["model.diffusion_model.final.linear1.weight"] = ("BF16", [256, 32])
    a = A.analyse(st_file(tmp_path / "toy.safetensors", t, {"modelspec.architecture": "toy-dit", "ss_dataset_dirs": "/private/place"}), "diffusion_models/toy.safetensors")
    assert a["read"] and a["tensors"] == 11 and a["weights"] == 3 * (96 * 32 + 128 * 32 + 32) + 16 + 256 * 32
    assert a["prefix"] == "model.diffusion_model" and a["arch"] == "toy-dit"
    assert a["kinds"]["attention"][0] == 3 * 96 * 32 and a["kinds"]["mlp"][0] == 3 * 128 * 32 and a["kinds"]["norm"][0] == 96
    assert dict((d[0], d[3]) for d in a["dtypes"]) == {"BF16": 2 * (3 * (96 * 32 + 128 * 32) + 16 + 256 * 32), "F32": 3 * 32 * 4}
    blocks = next(c for c in a["tree"]["c"] if c["n"] == "blocks")
    assert blocks["r"] == 3 and blocks["u"] == 2 and blocks["c"][1].get("s") == "0" and "c" not in blocks["c"][1] and "c" in blocks["c"][2]
    assert "ss_dataset_dirs" not in a["meta"] and a["meta"] == {"modelspec.architecture": "toy-dit"}       # metadata is a whitelist
    assert any("left unsplit" in c for c in a["cant_tell"]) and a["lora"] is None


def test_quantized_layers_count_the_weights_they_stand_for(tmp_path):
    q = json.dumps({"format": "nvfp4"}).encode()
    t = {"blocks.0.attn.qkv.weight": ("U8", [64, 16]), "blocks.0.attn.qkv.weight_scale": ("F8_E4M3", [64, 2]), "blocks.0.attn.qkv.comfy_quant": ("U8", [len(q)]),
         "blocks.1.mlp.fc1.weight": ("U8", [64, 16]), "blocks.1.mlp.fc1.weight_scale": ("F8_E4M3", [64, 2])}
    a = A.analyse(st_file(tmp_path / "q.safetensors", t, blobs={"blocks.0.attn.qkv.comfy_quant": q}))
    assert a["weights"] == 2 * (64 * 32)                          # two weights per stored byte, scales not counted as weights
    notes = dict(a["quant_notes"]); assert notes["nvfp4, from the layer's comfy_quant descriptor"] == 1 and any("inferred" in k for k in notes)
    assert a["kinds"]["quant_aux"][0] == 0 and a["kinds"]["quant_aux"][1] > 0


def test_a_lora_says_its_rank_and_targets(tmp_path):
    t = {}
    for i in range(4):
        for p in ("attn.qkv_proj", "attn.out_proj"): t |= {f"diffusion_model.blocks.{i}.{p}.lora_A.weight": ("BF16", [16, 64]), f"diffusion_model.blocks.{i}.{p}.lora_B.weight": ("BF16", [64, 16])}
    a = A.analyse(st_file(tmp_path / "l.safetensors", t))
    l = a["lora"]; assert l["ranks"] == [[16, 8]] and dict(map(tuple, l["targets"])) == {"attn.qkv_proj": 4, "attn.out_proj": 4} and l["alpha_tensors"] == 0
    assert any("alpha" in c for c in a["cant_tell"])
    k = A.analyse(st_file(tmp_path / "k.safetensors", {"lora_unet_down_blocks_0_attentions_0_transformer_blocks_0_attn1_to_q.lora_down.weight": ("F16", [8, 320]), "lora_unet_down_blocks_0_attentions_0_transformer_blocks_0_attn1_to_q.lora_up.weight": ("F16", [320, 8]), "lora_unet_down_blocks_0_attentions_0_transformer_blocks_0_attn1_to_q.alpha": ("F16", [])}))
    assert k["lora"]["ranks"] == [[8, 1]] and k["lora"]["targets"] == [["attn1_to_q", 1]] and k["lora"]["alpha_tensors"] == 1


def test_gguf_tensor_table_and_block_sizes(tmp_path):
    a = A.analyse(gguf_file(tmp_path / "toy.gguf"))
    assert a["read"] and a["format"] == "gguf" and a["arch"] == "toy" and a["weights"] == 64 * 32 + 64 * 128
    d = {x[0]: x[3] for x in a["dtypes"]}; assert d == {"Q8_0": 64 * 32 // 32 * 34, "F16": 64 * 128 * 2}
    assert a["kinds"]["attention"][0] == 64 * 32 and a["kinds"]["mlp"][0] == 64 * 128


def test_pickles_and_broken_headers_are_not_opened(tmp_path):
    p = tmp_path / "m.ckpt"; p.write_bytes(b"\x80\x04")
    a = A.analyse(str(p)); assert not a["read"] and "pickle" in a["why"] and "run code" in a["why"]
    b = tmp_path / "bad.safetensors"; b.write_bytes(struct.pack("<Q", 1 << 40) + b"{}")
    r = A.analyse(str(b)); assert not r["read"] and "didn't read" in r["why"]
    assert A.kind_of("block.1.layer.1.DenseReluDense.wo.weight", [4, 4]) == "mlp" and A.kind_of("layers.0.self_attn.o_proj.weight", [4, 4]) == "attention"
    assert A.kind_of("double_blocks.0.img_mod.lin.weight", [4, 4]) == "modulation" and A.kind_of("decoder.up.0.block.1.conv1.weight", [4, 4, 3, 3]) == "conv"


def test_the_build_script_writes_paths_relative_to_the_models_folder(tmp_path):
    m = tmp_path / "models"; (m / "loras").mkdir(parents=True); (m / "checkpoints").mkdir()
    st_file(m / "checkpoints" / "a.safetensors", {"x.attn.q.weight": ("F16", [8, 8])}); os.symlink(m / "checkpoints" / "a.safetensors", m / "loras" / "same.safetensors")
    (m / "checkpoints" / "old.pt").write_bytes(b"\x80"); out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_model_anatomy.py"), "--models", str(m), "--out", str(out)], capture_output=True, text=True, timeout=120, env={**os.environ, "PSN_MODEL_USE_MAP": ""})
    assert r.returncode == 0, r.stderr
    idx = json.loads((out / "index.json").read_text()); full = json.loads(gzip.decompress((out / "models.json.gz").read_bytes()))
    assert idx["files"] == 2 and idx["read"] == 1 and idx["not_read"] == {"pickle": 1}
    a = next(x for x in full.values() if x.get("read")); assert a["also"] and a["folder"] in ("checkpoints", "loras")
    text = (out / "index.json").read_text() + json.dumps(full); assert str(tmp_path) not in text


def test_the_endpoints_serve_the_cache(tmp_path, monkeypatch):
    from studio import server as S
    d = tmp_path / "anatomy"; d.mkdir(); (d / "index.json").write_text(json.dumps({"files": 1, "models": [{"id": "abc"}]}))
    (d / "models.json.gz").write_bytes(gzip.compress(json.dumps({"abc": {"id": "abc", "read": True}}).encode())); monkeypatch.setattr(F, "DATA", d); F._cache.clear()
    c = TestClient(S.app)
    assert c.get("/api/anatomy").json()["files"] == 1 and c.get("/api/anatomy/model/abc").json()["id"] == "abc" and c.get("/api/anatomy/model/nope").status_code == 404
    monkeypatch.setattr(F, "DATA", tmp_path / "none"); F._cache.clear(); assert c.get("/api/anatomy").status_code == 404
    F._cache.clear()


def test_the_page_is_wired_and_the_demo_saves_it():
    assert F.PAGE["tab"] == "anatomy" and (WEB / F.PAGE["module"]).exists() and (WEB / F.PAGE["css"]).exists()
    src = (ROOT / "scripts" / "build_pages.py").read_text(); assert '"anatomy"' in src and '"anatomy/model/"' in src


def test_the_cache_on_disk_is_clean_and_has_the_comparison():
    idx = json.loads((ROOT / "studio" / "anatomy" / "index.json").read_text()); raw = gzip.decompress((ROOT / "studio" / "anatomy" / "models.json.gz").read_bytes()).decode()
    assert not any(x in json.dumps(idx) + raw for x in BOX)
    full = json.loads(raw); main = next(p for p in idx["presets"] if p["id"] == "video-and-image")
    assert len(main["ids"]) == 4 and all(full[i]["read"] and full[i]["weights"] > 1e9 for i in main["ids"])
    for m in idx["models"]: assert m["id"] in full


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_the_page_logic():
    code = r'''
import * as L from "./anatomy_logic.js"; import assert from "node:assert";
assert.equal(L.fmtN(3875544576), "3.88 B"); assert.equal(L.fmtN(1.76e12), "1.76 T"); assert.equal(L.fmtBytes(7751089152), "7.75 GB");
assert.deepEqual(L.parseRoute("anatomy"), { view: "list" }); assert.deepEqual(L.parseRoute("anatomy/abc"), { view: "model", id: "abc" }); assert.deepEqual(L.parseRoute("anatomy/compare/a,b,c,d,e").ids, ["a", "b", "c", "d"]);
const t = L.squarify([{ w: 6 }, { w: 6 }, { w: 4 }, { w: 3 }, { w: 2 }, { w: 2 }, { w: 1 }], 0, 0, 600, 400);
assert.equal(t.length, 7); const area = t.reduce((s, r) => s + r.w * r.h, 0); assert.ok(Math.abs(area - 240000) < 1e-6);
for (const r of t) { assert.ok(r.x >= -1e-9 && r.y >= -1e-9 && r.x + r.w <= 600 + 1e-6 && r.y + r.h <= 400 + 1e-6); assert.ok(Math.abs(r.w * r.h - r.item.w * 10000) < 1e-6); }
assert.deepEqual(L.kindShares({ attention: [30, 60], mlp: [70, 140] }).map((s) => s.k), ["attention", "mlp"]); assert.equal(L.attnMlp({ attention: 0.3, mlp: 0.7 }).mlp, 0.7); assert.equal(L.attnMlp({ conv: 1 }), null);
const m = { read: true, weights: 100, data_bytes: 200, tensors: 3, dtypes: [["BF16", 3, 100, 200]], kinds: { attention: [40, 80], mlp: [60, 120] }, widths: [[64, 2]], tree: { c: [{ n: "blocks", w: 100, r: 4, u: 1, k: { attention: 40, mlp: 60 }, c: [] }] } };
const rows = L.compareRows([m, { read: false }]); assert.equal(rows.find((r) => r.label === "Bits per weight").cells[0], "16.0"); assert.equal(rows[0].cells[1], "not read");
assert.equal(rows.find((r) => r.label === "Repeated blocks").cells[0], "blocks x 4"); assert.equal(L.treemapItems(m)[0].kids.length, 2);
assert.equal(L.rankLine({ ranks: [[16, 104]] }), "rank 16 on all 104 modules");
const list = [{ file: "a.safetensors", read: true, weights: 5, folder: "loras", lora: true }, { file: "b.gguf", read: true, weights: 9, folder: "unet" }, { file: "c.pt", read: false, folder: "unet" }];
assert.deepEqual(L.filterModels(list, { read: "read", sort: "weights" }).map((x) => x.file), ["b.gguf", "a.safetensors"]); assert.equal(L.filterModels(list, { read: "all", lora: "lora" }).length, 1); assert.equal(L.filterModels(list, { read: "all", q: "gguf" }).length, 1);
console.log("ok");
'''
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(WEB / "anatomy_logic.js", t); (Path(t) / "x.mjs").write_text(code)
        p = subprocess.run(["node", str(Path(t) / "x.mjs")], cwd=t, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and "ok" in p.stdout, p.stderr
