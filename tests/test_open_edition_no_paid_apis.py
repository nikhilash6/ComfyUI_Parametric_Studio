import os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAID = ["api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com", "api.x.ai", "api.deepseek.com", "api.groq.com", "openrouter.ai", "api.mistral.ai", "api.cohere", "api.klingai.com", "klingai.com", "api.runwayml.com", "runwayml.com",
        "higgsfield", "api.lumalabs.ai", "api.bfl.ai", "fal.run", "api.replicate.com", "api.stability.ai", "api.ideogram.ai", "api.recraft.ai", "api.heygen.com", "api.elevenlabs.io", "api.together.xyz", "api.fireworks.ai", "bedrock", "azure.com/openai"]
PAID_IMPORTS = re.compile(r"^\s*(?:import|from)\s+(openai|anthropic|google\.generativeai|replicate|fal_client|elevenlabs|runwayml|cohere|groq)\b", re.M)
def test_no_paid_api_hosts_or_sdks_in_source():
    hits = []
    for base in ("psn", "psn_nodes"):
        for dp, _, fs in os.walk(os.path.join(ROOT, base)):
            for f in fs:
                if not f.endswith(".py"): continue
                t = open(os.path.join(dp, f), errors="replace").read(); p = os.path.relpath(os.path.join(dp, f), ROOT)
                hits += [f"{p}: host {h}" for h in PAID if h in t.lower()]; hits += [f"{p}: import {m.group(1)}" for m in PAID_IMPORTS.finditer(t)]
    assert not hits, hits

def test_no_studio_graph_uses_a_partner_node():
    import glob, json
    ids = {l.strip() for l in open(os.path.join(ROOT, "tests", "partner_node_ids.txt")) if l.strip() and not l.startswith("#")}; assert len(ids) > 300
    graphs = glob.glob(os.path.join(ROOT, "workflows", "*.json")) + glob.glob(os.path.join(ROOT, "studio", "family_templates", "*.json")); assert len(graphs) > 30
    hits = []
    for f in graphs:
        g = json.load(open(f)); nodes = g.values() if isinstance(g, dict) else []
        hits += [f"{os.path.relpath(f, ROOT)}: {n.get('class_type')}" for n in nodes if isinstance(n, dict) and n.get("class_type") in ids]
    assert not hits, hits
