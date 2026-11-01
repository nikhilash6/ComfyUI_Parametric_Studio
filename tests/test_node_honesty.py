"""Stops fabricated node output coming back (see the node audit of 2026-11-01: a node called PSN_LoRA_Train_HunYuan returned a made-up path and loss curve, and its tests passed).
Static scan of every node in psn_nodes/ and psn_nodes/gen/: starting from the method named by FUNCTION, it follows the helpers that method can reach in the same module and looks at what could end up in a result.
A hit that is honest goes in tests/node_honesty_allow.tsv (node, rule, token, reason). Every entry there must still match something, so the list cannot go stale. No node is imported or run."""
import ast, csv, glob, os, re
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOW = os.path.join(ROOT, "tests", "node_honesty_allow.tsv")
WORDS = re.compile(r"placeholder|synthetic|simulat|(?<![a-z])mock|(?<![a-z])stub|dummy|(?<![a-z])fake|not implemented|notimplemented|pseudo", re.I)
RANDOM_CALLS = {"random.random", "random.randint", "random.uniform", "random.choice", "random.gauss", "random.Random", "random.sample", "random.shuffle", "torch.rand", "torch.randn", "torch.randint", "torch.randperm", "torch.rand_like", "torch.randn_like", "np.random", "numpy.random"}
MEDIA = re.compile(r"\.(mp4|mov|webm|mkv|avi|gif|png|jpe?g|webp|wav|mp3|flac|ogg|safetensors|ckpt|pt|pth|gguf|glb|fbx|obj|ply)$", re.I)
WRITERS = {"open", "save", "write", "write_bytes", "write_text", "dump", "save_file", "makedirs", "mkdir", "copy", "copyfile", "urlopen", "request", "post", "put", "run", "Popen", "deliver"}


def dotted(node):
    parts = []
    while isinstance(node, ast.Attribute): parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name): parts.append(node.id)
    return ".".join(reversed(parts))


def is_docstring(parent):
    return isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and parent.body and isinstance(parent.body[0], ast.Expr) and isinstance(getattr(parent.body[0], "value", None), ast.Constant)


def body_without_doc(fn):
    return fn.body[1:] if is_docstring(fn) else fn.body


def reachable(entry, methods, functions):
    """The FUNCTION method plus every same-module helper it can call."""
    seen, stack, out = set(), [entry], []
    while stack:
        fn = stack.pop()
        if id(fn) in seen: continue
        seen.add(id(fn)); out.append(fn)
        for n in ast.walk(fn):
            name = n.id if isinstance(n, ast.Name) else n.attr if isinstance(n, ast.Attribute) else None
            if name in functions: stack.append(functions[name])
            if name in methods: stack.append(methods[name])
    return out


def writes_something(fns):
    return any(isinstance(n, ast.Call) and dotted(n.func).split(".")[-1] in WRITERS for fn in fns for n in ast.walk(fn))


def scan_function(fn, wrote=False):
    """(rule, token, line) hits in one function: words in strings and names, random used, media paths nobody writes. Docstrings, comments and raised error text do not count. `wrote` says whether anything reachable from the node writes or sends."""
    hits = []
    skip = set()
    if is_docstring(fn): skip.add(id(fn.body[0].value))
    for n in ast.walk(fn):
        if isinstance(n, ast.Raise):
            skip.update(id(x) for x in ast.walk(n))
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            name = dotted(n.func)
            if name in RANDOM_CALLS or any(name.startswith(p + ".") for p in ("np.random", "numpy.random")): hits.append(("random", name, n.lineno))
        if id(n) in skip: continue
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            m = WORDS.search(n.value)
            if m: hits.append(("word", m.group(0).lower(), n.lineno))
        elif isinstance(n, ast.Name) and WORDS.search(n.id): hits.append(("word", WORDS.search(n.id).group(0).lower(), n.lineno))
        elif isinstance(n, ast.Attribute) and WORDS.search(n.attr): hits.append(("word", WORDS.search(n.attr).group(0).lower(), n.lineno))
    if not wrote:      # a media file name built in a function that writes nothing, like f"{name}.mp4" or "/out/lora.safetensors". A bare ".mp4" in an allow-list of extensions is not one.
        joined = {id(v) for n in ast.walk(fn) if isinstance(n, ast.JoinedStr) for v in n.values}
        for n in ast.walk(fn):
            if id(n) in skip or not isinstance(n, ast.Constant) or not isinstance(n.value, str): continue
            s = n.value.strip()
            if MEDIA.search(s) and not re.search(r"\s", s) and (id(n) in joined or MEDIA.sub("", s)): hits.append(("path", s[-40:], n.lineno))
    return hits


def node_classes(tree):
    """Each class with a FUNCTION string attribute, or a V3 `execute` classmethod plus define_schema."""
    for c in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        methods = {f.name: f for f in c.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
        fn = None
        for st in c.body:
            if isinstance(st, ast.Assign) and any(getattr(t, "id", "") == "FUNCTION" for t in st.targets) and isinstance(st.value, ast.Constant): fn = st.value.value
        if fn is None and "define_schema" in methods and "execute" in methods: fn = "execute"
        if fn and fn in methods: yield c, methods, methods[fn]


def scan_source(src):
    """{class name: [(rule, token, line)]} for a module's source. Also: a FUNCTION body that is only `pass`, and marker words in the description the user sees."""
    tree = ast.parse(src); functions = {f.name: f for f in tree.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}; out = {}
    for cls, methods, entry in node_classes(tree):
        hits = []
        body = body_without_doc(entry)
        if all(isinstance(b, ast.Pass) for b in body): hits.append(("empty", entry.name, entry.lineno))
        fns = reachable(entry, {k: v for k, v in methods.items() if k not in ("INPUT_TYPES", "define_schema", "IS_CHANGED", "VALIDATE_INPUTS")}, functions); wrote = writes_something(fns)
        for fn in fns: hits += scan_function(fn, wrote)
        text = ast.get_docstring(cls) or ""
        for st in cls.body:
            if isinstance(st, ast.Assign) and any(getattr(t, "id", "") == "DESCRIPTION" for t in st.targets) and isinstance(st.value, ast.Constant): text += " " + str(st.value.value)
        m = WORDS.search(text.split("\n\n")[0])
        if m: hits.append(("description", m.group(0).lower(), cls.lineno))
        for st in cls.body:      # an output named like a result of work that the module admits it fakes
            if isinstance(st, ast.Assign) and any(getattr(t, "id", "") == "RETURN_NAMES" for t in st.targets):
                for v in ast.walk(st.value):
                    if isinstance(v, ast.Constant) and isinstance(v.value, str) and WORDS.search(v.value): hits.append(("output", v.value, st.lineno))
        if hits: out[cls.name] = sorted(set(hits), key=lambda h: (h[2], h[0], h[1]))
    return out


def modules():
    return sorted(p for p in glob.glob(os.path.join(ROOT, "psn_nodes", "*.py")) + glob.glob(os.path.join(ROOT, "psn_nodes", "gen", "*.py")) if not os.path.basename(p).startswith("_") and os.path.basename(p) != "tidy.py")


def load_allow():
    with open(ALLOW, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader((ln for ln in f if not ln.startswith("#")), delimiter="\t")]
    return rows


def all_hits():
    out = []
    for p in modules():
        with open(p, encoding="utf-8") as f: found = scan_source(f.read())
        for cls, hits in found.items():
            for rule, token, line in hits: out.append((cls, rule, token, f"{os.path.relpath(p, ROOT)}:{line}"))
    return out


def test_no_node_result_path_carries_a_fabrication_marker():
    allow = {(r["node"], r["rule"], r["token"]) for r in load_allow()}
    bad = sorted({h for h in all_hits() if (h[0], h[1], h[2]) not in allow})
    assert not bad, f"{len(bad)} unexplained marker(s). Fix the node, or add it to tests/node_honesty_allow.tsv with a reason: " + "; ".join(f"{c} {r} {t!r} at {w}" for c, r, t, w in bad[:25])


def test_every_allowlist_entry_has_a_reason_and_still_matches():
    hits = {(h[0], h[1], h[2]) for h in all_hits()}
    stale = [(r["node"], r["rule"], r["token"]) for r in load_allow() if (r["node"], r["rule"], r["token"]) not in hits]
    assert not stale, f"stale allowlist entries: {stale[:20]}"
    assert all((r["reason"] or "").strip() for r in load_allow())


def shape_only(src):
    """True when every assert in a test file only checks type, presence, length or shape: the kind of test that let the fake trainer pass. None when it has no assert at all."""
    asserts = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Assert)]
    if not asserts: return None
    def shapey(e):
        if isinstance(e, ast.Call): return getattr(e.func, "id", "") in ("isinstance", "hasattr", "callable")
        if isinstance(e, ast.Compare):
            if all(isinstance(o, (ast.In, ast.NotIn, ast.IsNot)) for o in e.ops): return True
            left = e.left
            return (isinstance(left, ast.Call) and getattr(left.func, "id", "") == "len") or (isinstance(left, ast.Attribute) and left.attr in ("shape", "ndim", "dtype"))
        return isinstance(e, (ast.Name, ast.Attribute, ast.Subscript))
    return all(shapey(a.test) for a in asserts)


def test_no_generated_node_test_only_checks_shape():
    files = glob.glob(os.path.join(ROOT, "tests", "gen", "*.py")) + glob.glob(os.path.join(ROOT, "tests", "gen_built", "*", "test_*.py"))
    bad = []
    for p in files:
        with open(p, encoding="utf-8") as f:
            if shape_only(f.read()) is not False: bad.append(os.path.relpath(p, ROOT))
    assert files and not bad, f"tests that assert only a shape, or nothing: {bad[:20]}"


def test_shape_check_tells_the_two_kinds_apart():
    assert shape_only("def t():\n    r = f()\n    assert isinstance(r, dict)\n    assert 'a' in r\n    assert len(r) == 2\n") is True
    assert shape_only("def t():\n    r = f()\n    assert 'a' in r\n    assert r['a'] == 3\n") is False
    assert shape_only("def t():\n    f()\n") is None


# The scanner itself, on fixtures: it has to catch the pattern this check exists for.
FAKE_TRAINER = '''
class PSN_Train:
    """Formats a job."""
    RETURN_NAMES = ("lora_path", "loss_curve", "status")
    FUNCTION = "run"
    def run(self, config):
        curve = {"type": "synthetic", "note": "placeholder loss curve"}
        return ("/out/lora.safetensors", str(curve), "ok")
'''
def test_scanner_catches_a_made_up_loss_curve_and_path():
    rules = {(r, t) for r, t, _ in scan_source(FAKE_TRAINER)["PSN_Train"]}
    assert ("word", "synthetic") in rules and ("path", "/out/lora.safetensors") in rules

def test_scanner_follows_helpers_and_catches_random_as_data():
    src = '''
import random
def _score(x): return random.random()
class PSN_Score:
    FUNCTION = "go"
    def go(self, x): return (_score(x),)
'''
    assert ("random", "random.random") in {(r, t) for r, t, _ in scan_source(src)["PSN_Score"]}

def test_scanner_catches_an_empty_body_and_a_mocked_output_name():
    src = '''
class PSN_Empty:
    RETURN_NAMES = ("mock_result",)
    FUNCTION = "go"
    def go(self):
        """Does the thing."""
        pass
'''
    rules = {(r, t) for r, t, _ in scan_source(src)["PSN_Empty"]}
    assert ("empty", "go") in rules and ("output", "mock_result") in rules

def test_scanner_catches_a_file_name_built_in_an_f_string():
    src = '''
class PSN_Video:
    FUNCTION = "go"
    def go(self, n):
        path = f"video_{n}.mp4"
        return (path,)
'''
    assert ("path", ".mp4") in {(r, t) for r, t, _ in scan_source(src)["PSN_Video"]}

def test_scanner_passes_a_list_of_allowed_extensions():
    src = '''
class PSN_Check:
    FUNCTION = "go"
    def go(self, name): return (name.endswith((".mp4", ".png")),)
'''
    assert scan_source(src) == {}

def test_scanner_passes_a_real_node_and_a_written_path():
    src = '''
import os
class PSN_Save:
    """Writes the text to a file."""
    RETURN_NAMES = ("path",)
    FUNCTION = "go"
    def go(self, text):
        with open("/tmp/a.txt", "w") as f: f.write(text)
        return ("/tmp/a.png",)
'''
    assert scan_source(src) == {}

def test_scanner_ignores_docstrings_and_error_text():
    src = '''
class PSN_Honest:
    """Adds two numbers."""
    FUNCTION = "go"
    def go(self, a, b):
        """Not a simulation: see above."""
        if a is None: raise ValueError("placeholder not allowed")
        return (a + b,)
'''
    assert scan_source(src) == {}

@pytest.mark.parametrize("word", ["placeholder", "synthetic", "simulated", "mock", "stub", "dummy", "fake", "not implemented"])
def test_every_marker_in_the_brief_is_covered(word):
    assert WORDS.search(word)
