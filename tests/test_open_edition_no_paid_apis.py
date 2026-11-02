"""Open Weights Only: "No partner nodes or closed-source APIs, open-weights models only" (the contest page). The open edition must keep to it, and this file is the proof.
It checks the code for paid model hosts and SDKs, every graph in the repo against ComfyUI's own list of partner nodes, the Atlas's closed models, and the default path a
person meets first: the default goal, the backend and the crew's language model. No live ports: the partner list is a fixture read from ComfyUI 0.43.0."""
import json, os, re, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAID = ["api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com", "aiplatform.googleapis.com", "api.x.ai", "api.deepseek.com", "api.groq.com", "openrouter.ai", "api.mistral.ai", "api.cohere", "api.klingai.com", "klingai.com", "api.runwayml.com", "runwayml.com",
        "higgsfield.ai", "api.lumalabs.ai", "api.bfl.ai", "api.bfl.ml", "fal.run", "api.replicate.com", "api.stability.ai", "api.ideogram.ai", "api.recraft.ai", "api.heygen.com", "api.elevenlabs.io", "api.together.xyz", "api.fireworks.ai", "bedrock-runtime", "azure.com/openai",
        "api.minimax.io", "api.minimaxi.com", "api.krea.ai", "api.vidu.com", "api.pixverse.ai", "api.tripo3d.ai", "api.meshy.ai", "api.topazlabs.com", "api.wavespeed.ai", "api.hailuoai", "api.comfy.org"]
PAID_IMPORTS = re.compile(r"^\s*(?:import|from)\s+(openai|anthropic|google\.generativeai|google\.genai|replicate|fal_client|elevenlabs|runwayml|cohere|groq|lumaai|comfy_api_nodes|comfy_sdk)\b", re.M)
#: not in the public tree (scripts/assemble_public.py drops it); reserved for the Extended edition (EDITIONS.md)
NOT_OPEN_EDITION = {"studio/printify.py"}
#: Comfy Cloud runs the same open-weights graphs on Comfy's GPUs and spends the user's credits. Off unless STUDIO_BACKEND=sdk; test_default_path_is_local_and_open holds that.
OPT_IN_BACKEND = {"studio/backends.py"}


def _tracked():
    try: return subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    except Exception: return [os.path.relpath(os.path.join(dp, f), ROOT) for dp, _, fs in os.walk(ROOT) if ".git" not in dp.split(os.sep) for f in fs]


def _code():
    for p in _tracked():
        if (p.startswith(("psn/", "psn_nodes/", "studio/")) and p.endswith((".py", ".js", ".mjs")) or p == "install.py") and p not in NOT_OPEN_EDITION and os.path.exists(os.path.join(ROOT, p)):
            yield p


def test_no_paid_api_hosts_or_sdks_in_source():
    hits = []
    for p in _code():
        t = open(os.path.join(ROOT, p), errors="replace").read()
        hits += [f"{p}: host {h}" for h in PAID if h in t.lower()]
        hits += [f"{p}: import {m.group(1)}" for m in PAID_IMPORTS.finditer(t) if p not in OPT_IN_BACKEND]
    assert not hits, hits


def test_the_scan_reads_the_whole_app():
    """The first version read psn/ and psn_nodes/ only; most of the app is in studio/."""
    seen = set(_code())
    assert {"studio/server.py", "studio/goals.py", "studio/web/app.js", "psn/instances.py", "install.py"} <= seen and "studio/printify.py" not in seen


def _graphs():
    for p in _tracked():
        if not p.endswith(".json") or not os.path.exists(os.path.join(ROOT, p)): continue
        try: d = json.load(open(os.path.join(ROOT, p), encoding="utf-8"))
        except Exception: continue
        types = set()
        def walk(o):
            if isinstance(o, dict):
                if isinstance(o.get("class_type"), str): types.add(o["class_type"])
                if isinstance(o.get("type"), str) and ("widgets_values" in o or ("inputs" in o and "id" in o)): types.add(o["type"])      # UI-format nodes
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(d)
        if types: yield p, types


def test_no_graph_in_the_repo_uses_a_partner_node():
    partner = set(json.load(open(os.path.join(ROOT, "tests", "fixtures", "partner_nodes.json")))["api_nodes"])
    partner |= {l.strip() for l in open(os.path.join(ROOT, "tests", "partner_node_ids.txt")) if l.strip() and not l.startswith("#")}      # the /object_info list and the comfy_api_nodes source list differ by a few ids; use both
    assert len(partner) > 300 and {"BriaRemoveVideoBackground", "KlingFirstLastFrameNode", "GeminiImage2Node"} <= partner
    graphs = dict(_graphs())
    assert len(graphs) > 400 and {"workflows/ltx25_vfx_api.json", "workflows/h3_recast_api.json", "studio/family_templates/krea2_turbo_t2i.json"} <= set(graphs)
    hits = {p: sorted(t & partner) for p, t in graphs.items() if t & partner}
    assert not hits, hits


def test_closed_models_in_the_atlas_cannot_be_run_here():
    models = json.load(open(os.path.join(ROOT, "studio", "atlas_models.json")))["models"]
    closed = [m for m in models if m["licence_class"] == "proprietary"]
    assert closed and all(not m["run"]["goals"] and not m["family"] for m in closed), [m["name"] for m in closed]


def test_every_goal_names_open_weights_with_their_licence():
    from studio import goals, licences
    for gid, g in goals.GOALS.items():
        assert g["family"] in licences.GOAL_FAMILIES, f"{gid}: {g['family']} has no licence entry in studio/licences.py"
        assert g["license_url"].startswith("https://"), gid
        if g["license_class"] == "open": assert not g["license_limits"], gid
        else: assert g["license_limits"] and g["license_badge"], f"{gid}: a community licence must say what it limits"


def test_default_path_is_local_and_open(monkeypatch):
    """What a judge meets first: Create opens on the Image goal (FLUX.2 Klein 4B, Apache-2.0), graphs go to the local ComfyUI, the crew's models are Apache-2.0 open weights."""
    from studio import backends, goals, llm_tiers
    app = open(os.path.join(ROOT, "studio", "web", "app.js")).read()
    assert 'const [goal, setGoal] = useState("image")' in app
    g = goals.GOALS["image"]; assert g["license"] == "Apache-2.0" and g["license_class"] == "open" and not g["license_limits"]
    monkeypatch.delenv("STUDIO_BACKEND", raising=False); assert not backends.use_sdk()
    assert all(t["gguf"]["repo"].startswith("unsloth/Qwen3.5-") for t in llm_tiers.TIERS[:-1]) and llm_tiers.TIERS[-1]["model"].startswith("Qwen/")
    models = open(os.path.join(ROOT, "MODELS.md")).read()
    assert all(f"| Apache-2.0 | No | [{t['gguf']['repo']}]" in models for t in llm_tiers.TIERS[:-1])


def test_partner_apps_and_tools_stay_hidden_in_the_open_edition(monkeypatch):
    from studio import apps, edits
    monkeypatch.delenv("PSN_EDITION", raising=False)
    assert apps.open_edition() and "bgremove" in edits.PARTNER_TOOLS


def test_no_studio_graph_uses_a_partner_node():
    import glob, json
    ids = {l.strip() for l in open(os.path.join(ROOT, "tests", "partner_node_ids.txt")) if l.strip() and not l.startswith("#")}; assert len(ids) > 300
    graphs = glob.glob(os.path.join(ROOT, "workflows", "*.json")) + glob.glob(os.path.join(ROOT, "studio", "family_templates", "*.json")); assert len(graphs) > 30
    hits = []
    for f in graphs:
        g = json.load(open(f)); nodes = g.values() if isinstance(g, dict) else []
        hits += [f"{os.path.relpath(f, ROOT)}: {n.get('class_type')}" for n in nodes if isinstance(n, dict) and n.get("class_type") in ids]
    assert not hits, hits
