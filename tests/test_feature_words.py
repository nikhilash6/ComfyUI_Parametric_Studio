"""Which word painted what: the page's routes build only our attention graph, refuse what they can't run, and read maps back from history; the proof data is
honest, its files exist, and the page's maths (studio/web/words_logic.js) runs under node. ComfyUI is stubbed: no GPU, no real queue."""
import base64, json, shutil, subprocess, tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import studio.server as S
from studio import feature_words as W, words_graph as G

ROOT = Path(__file__).parent.parent; WEB = ROOT / "studio" / "web"
node = pytest.mark.skipif(not shutil.which("node"), reason="node not installed")


@pytest.fixture
def client(monkeypatch):
    calls = []; state = {"nodes": True, "history": {}}
    def comfy(path, payload=None, timeout=30, raw=False):
        calls.append((path, payload))
        if path == "/object_info/PSN_AttentionRecord": return {"PSN_AttentionRecord": {}} if state["nodes"] else {}
        if path.startswith("/object_info"): return {"CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [["v1-5-pruned-emaonly.safetensors"]]}}}}
        if path == "/prompt": return {"prompt_id": "wjob1"}
        if path.startswith("/history/"): return state["history"]
        return {}
    monkeypatch.setattr(S, "comfy", comfy); monkeypatch.setattr(S, "comfy_up", lambda: True); monkeypatch.setattr(W, "_srv", lambda: S); S.JOBS.pop("wjob1", None)
    c = TestClient(S.app); c.calls = calls; c.state = state; return c


def test_the_page_is_one_feature_file():
    assert W.PAGE["tab"] == "words" and (WEB / W.PAGE["module"]).exists() and (WEB / W.PAGE["css"]).exists()
    assert f'export function {W.PAGE["export"]}' in (WEB / W.PAGE["module"]).read_text()
    js = (WEB / "words.js").read_text(); assert "http://" not in js and "fetch(" not in js and [u for u in __import__("re").findall(r"https://[^\"' ]+", js)] == ["https://arxiv.org/abs/2210.04885"]     # one credit link, nothing fetched from outside


def test_graph_is_ours_and_the_plain_twin_differs_only_by_the_recorder():
    p = {"model": "sdxl", "prompt": "a red hat", "seed": 1, "id": "t"}; g = G.build(p); plain = G.build(p, record=False)
    assert g["6"]["inputs"]["model"] == ["2", 0] and g["2"]["class_type"] == "PSN_AttentionRecord" and g[G.MAPS]["inputs"]["attention"] == ["2", 1] and g[G.MAPS]["inputs"]["text"] == "a red hat"
    assert plain["6"]["inputs"]["model"] == ["1", 0] and "2" not in plain and G.MAPS not in plain and G.SHEET not in plain
    assert {k: v for k, v in plain["6"]["inputs"].items() if k != "model"} == {k: v for k, v in g["6"]["inputs"].items() if k != "model"}
    assert {n["class_type"] for n in g.values()} == {"CheckpointLoaderSimple", "PSN_AttentionRecord", "CLIPTextEncode", "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage", "PSN_AttentionMaps"}


def test_routes_check_their_input(client):
    assert client.get("/api/words/graph?model=flux&prompt=x").status_code == 400
    assert client.get("/api/words/graph?model=sd15&prompt=" + "x" * 301).status_code == 400
    assert client.get("/api/words/graph?model=sd15&prompt=hat&steps=99").status_code == 400
    r = client.get("/api/words/graph?model=sd15&prompt=a%20blue%20teacup&seed=7").json(); assert r["params"]["seed"] == 7 and r["graph"]["3"]["inputs"]["text"] == "a blue teacup"
    assert client.get("/api/words").json()["renders"] is not None


def test_run_queues_our_graph_and_refuses_without_the_nodes_or_the_model(client):
    r = client.post("/api/words/run", json={"model": "sd15", "prompt": "a red hat"}); assert r.status_code == 200 and r.json()["job"] == "wjob1"
    sent = [p for path, p in client.calls if path == "/prompt"][0]["prompt"]; assert sent["2"]["class_type"] == "PSN_AttentionRecord" and S.JOBS["wjob1"]["goal"] == "words"
    assert client.post("/api/words/run", json={"model": "sdxl", "prompt": "a red hat"}).status_code == 400          # SDXL is not on this stub's disk; nothing is swapped in
    client.state["nodes"] = False; r = client.post("/api/words/run", json={"model": "sd15", "prompt": "a red hat"}); assert r.status_code == 400 and "PSN attention nodes" in r.json()["detail"]
    assert client.post("/api/words/run", content=b"nope").status_code == 400


def test_result_reads_the_maps_back_from_history(client):
    assert client.get("/api/words/result/wjob1").json() == {"status": "running"}
    maps = {"map_size": [2, 2], "words": [{"word": "hat", "share": 0.01, "peak": 0.1, "map": base64.b64encode(bytes([0, 255, 9, 9])).decode(), "phases": [None, None, None], "punct": False}], "start_share": 0.9}
    client.state["history"] = {"wjob1": {"status": {"completed": True, "status_str": "success"}, "outputs": {G.MAPS: {"psn_attention": [maps]}, G.PICTURE: {"images": [{"filename": "a.png", "subfolder": "words", "type": "output"}]}}}}
    r = client.get("/api/words/result/wjob1").json(); assert r["status"] == "done" and r["maps"]["words"][0]["word"] == "hat" and r["image"].startswith("/api/view?") and "words" in r["image"]
    client.state["history"] = {"wjob1": {"status": {"status_str": "error", "messages": [["execution_error", {"exception_message": "Attention maps need a UNet"}]]}}}
    assert client.get("/api/words/result/wjob1").json() == {"status": "error", "error": "Attention maps need a UNet"}
    assert client.get("/api/words/result/..%2Fx").status_code in (400, 404)


DOC = json.loads((ROOT / "studio" / "sampling_lab" / "attention.json").read_text())
def test_proof_data_is_complete_and_honest():
    assert DOC["renders"], "no proof renders"
    for r in DOC["renders"]:
        assert (WEB / r["image"]).exists() and (WEB / r["maps"]).exists() and r["model"] in G.MODELS and r["ckpt"] == G.MODELS[r["model"]]["ckpt"]
        assert r["peak_vram_gib"] > 0 and r["ran_on"] and r["steps_recorded"] == r["steps"] and r["layers"] > 0 and r["words"]
        from PIL import Image
        im = Image.open(WEB / r["maps"]); assert im.size == (r["map_size"][1] * 4, r["map_size"][0] * len(r["words"]))
        judge = lambda c, lift: c["picture_share"] > 0.005 and (lift >= DOC["high"] if c["expect"] == "high" else lift < DOC["low"])
        for c in r["checks"]:                                     # a check's verdicts follow from its own numbers and the thresholds the file states
            if "lift" in c: assert c["ok"] == judge(c, c["lift"]) and c["ok_above_floor"] == judge(c, c["lift_above_floor"])
        assert all(0 <= w["floor"] <= w["peak"] for w in r["words"])
        assert 0 < r["start_share"] < 1 and all(0 <= w["share"] < 1 for w in r["words"])
    proofs = [r for r in DOC["renders"] if r.get("proof")]
    assert {r["model"] for r in proofs} == {"sd15", "sdxl"} and all(r["proof"]["same_picture_mean_abs"] < 2 for r in proofs)     # recording does not change the picture beyond rounding
    assert DOC["sheet"] is None or (WEB / DOC["sheet"]).exists()


@node
def test_page_maths_under_node():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); shutil.copy(WEB / "words_logic.js", d / "words_logic.js")
        (d / "x.mjs").write_text('''import * as L from "./words_logic.js";
const o = {};
o.ramp = [L.ramp(0), L.ramp(1), L.ramp(0.6), L.ramp(-3)];
const m = new Float32Array([0, 1, 0, 0]);                          // 2 x 2, bright top right
o.corner = L.sample(m, 2, 2, 0.9, 0.1); o.centre = L.sample(m, 2, 2, 0.5, 0.5); o.cell = L.cellAt(511, 0, 512, 512, 2, 2);
const words = [{ word: "hat", floor: 0.02, peak: 0.2, maps: [m] }, { word: "table", floor: 0.05, peak: 0.05, maps: [new Float32Array([1, 1, 1, 1])] }];
o.rank = L.ranked(words, [0, 1], 2).map((r) => [r.i, +r.v.toFixed(4)]); o.rank2 = L.ranked(words, [1, 0], 2).map((r) => [r.i, +r.v.toFixed(4)]);
const base = new Uint8ClampedArray(4 * 4 * 4).fill(200), out = new Uint8ClampedArray(base.length);
L.paint(base, out, 4, 4, null, 2, 2); o.plain = Array.from(out.slice(0, 4)); L.paint(base, out, 4, 4, new Float32Array(4), 2, 2); o.dark = Array.from(out.slice(0, 4));
const rgba = new Uint8ClampedArray(4 * 8 * 2 * 2); for (let i = 0; i < 8 * 2 * 2; i++) rgba[4 * i] = i * 7;
const rows = L.fromSprite(rgba, 8, 2, 1, 2); o.sprite = rows.map((r) => r.map((x) => Array.from(x).map((v) => Math.round(v * 255))));
o.b64 = Array.from(L.fromB64(Buffer.from([0, 255, 51]).toString("base64"))).map((v) => +v.toFixed(3)); o.none = L.fromB64(null);
o.live = L.liveWords({ words: [{ word: ",", punct: true, map: "AA==", phases: [] }, { word: "hat", share: 0.1, floor: 0.3, peak: 1, map: "/w==", phases: ["AA==", null] }] }).map((w) => [w.word, w.maps.length, w.maps[2], w.floor]);
o.line = L.checkLine({ word: "hat", region: "red", expect: "high", attention_inside: 0.5, picture_share: 0.2, lift: 2.5 }, 1.5, 1);
o.pct = [L.pct(0.0123), L.pct(0.5), L.pct(null)]; o.phase = [L.phaseIndex("late"), L.phaseIndex("nope")];
console.log(JSON.stringify(o));''')
        p = subprocess.run(["node", str(d / "x.mjs")], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-800:]
    o = json.loads(p.stdout)
    assert o["ramp"][0] == [0.02, 0.02, 0.1] and o["ramp"][1] == [1, 0.98, 0.75] and o["ramp"][3] == o["ramp"][0] and o["ramp"][2] == [0.85, 0.25, 0.2]
    assert o["corner"] == 1 and o["centre"] == 0.25 and o["cell"] == [0, 1]
    assert o["rank"] == [[0, 0.2], [1, 0.05]] and o["rank2"] == [[1, 0.05], [0, 0.02]]                 # off the hat, hat falls to its floor
    assert o["plain"] == [200, 200, 200, 255] and o["dark"] == [60, 60, 60, 255]                # where the word did not look, the picture is dimmed to 30%, as the node does
    assert o["sprite"] == [[[0, 7], [14, 21], [28, 35], [42, 49]], [[56, 63], [70, 77], [84, 91], [98, 105]]]
    assert o["b64"] == [0, 1, 0.2] and o["none"] is None and o["live"] == [["hat", 3, None, 0.3]]
    assert "50% of “hat” falls on red pixels, which cover 20% of the picture: 2.5× as dense" in o["line"]
    assert o["pct"] == ["1.2%", "50%", ""] and o["phase"] == [3, 0]
