# CU-381 lab: a small text scanner on sample lines we wrote. It shows both kinds of mistake: alarms on harmless lines, and silence on harmful ones.
import re
PATS = {"dynamic code": r"\b(eval|exec)\(|b64decode|marshal\.loads", "install": r"\bpip\b|git clone|npm install", "network": r"\brequests\.|urllib|socket\.", "paid": r"api_key|openai|replicate", "credentials": r"\.ssh/|\.aws/|os\.environ\)"}
SAMPLES = [
 (False, "image = base64.b64decode(field)"),
 (False, 'raise ImportError("run pip install onnx")'),
 (False, 'x = pad(x, (1, 1), mode="replicate")'),
 (False, "# do not use eval( here"),
 (False, 'requests.get("http://127.0.0.1:8188/object_info")'),
 (False, "env = dict(os.environ)"),
 (True, "exec(zlib.decompress(base64.b64decode(BLOB)))"),
 (True, 'subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "torch"])'),
 (True, "return (eval(text_widget),)"),
 (True, 'f = getattr(__builtins__, "ev" + "al"); f(user_text)'),
 (True, 'import importlib; importlib.import_module("sub" + "process").run(cmd)'),
 (True, "state = pickle.load(open(path, 'rb'))"),
 (True, "torch.load(path, weights_only=False)"),
 (True, 'open(request.query["path"]).read()'),
]
def scan(l): return [k for k, p in PATS.items() if re.search(p, l)]
tp = fp = fn = tn = 0
print("truth    scan     line")
for bad, l in SAMPLES:
    h = scan(l); tp += bad and bool(h); fp += (not bad) and bool(h); fn += bad and not h; tn += (not bad) and not h
    print(f"{'bad' if bad else 'fine':8s} {'hit' if h else 'clean':8s} {l[:66]}")
print(f"\nhit on a bad line {tp}, hit on a fine line {fp}, clean on a bad line {fn}, clean on a fine line {tn}")
assert fp >= 5 and fn >= 4
print(f"of {tp + fp} hits, {fp} were false alarms. of {fn + tn} clean lines, {fn} were bad")
print("these are our own samples, picked to show both mistakes. The counts say nothing about real packs.")
print("\nadding patterns moves the mistakes, it does not end them")
PATS["loaders"] = r"pickle\.load|weights_only=False|query\["
fn2 = sum(1 for b, l in SAMPLES if b and not scan(l)); fp2 = sum(1 for b, l in SAMPLES if not b and scan(l))
print(f"with a loaders pattern: clean on a bad line {fn2}, hit on a fine line {fp2}")
assert fn2 < fn
print("same line, different place. The text is equal, the risk is not")
for where, risk in (("tests/test_nodes.py, never imported", "low"), ("docs/build.py, a script nobody runs at start", "low"), ("a node's run method, on a text widget", "high"), ("__init__.py at top level", "high")):
    print(f"  {where:46s} {risk}")
