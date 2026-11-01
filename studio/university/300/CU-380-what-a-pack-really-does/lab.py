# CU-380 lab: sort the lines of a pack's entry file by when they would run. The file is text we wrote for this lab. It is read, never run.
import re, hashlib
FILE = "\n".join([
    "import os, json",
    "import subprocess, sys",
    "from .nodes import NODE_CLASS_MAPPINGS",
    "subprocess.check_call([sys.executable, \"-m\", \"pip\", \"install\", \"-q\", \"somepkg\"])",
    "CONFIG = json.load(open(os.path.join(os.path.dirname(__file__), \"config.json\")))",
    "def helper(path):",
    "    return open(path).read()",
    "class MyNode:",
    "    def run(self, text):",
    "        return (eval(text),)",
    "@PromptServer.instance.routes.get(\"/mypack/read\")",
    "async def read(request):",
    "    return web.FileResponse(request.query[\"path\"])",
    "if os.environ.get(\"MYPACK_UPDATE\"):",
    "    subprocess.run([\"git\", \"pull\"])",
    "WEB_DIRECTORY = \"./web\"",
]) + "\n"
PAT = {"install": r"\bpip\b|git\b.*\b(pull|clone)\b", "code from text": r"\b(eval|exec)\(", "file route": r"routes\.(get|post)|FileResponse", "process": r"subprocess\."}
def when(lines, i):
    """A very small reader: indentation and the line above tell you when a line runs."""
    l = lines[i]
    if not l.startswith((" ", "\t")): return "at start"
    j = i - 1
    while j >= 0 and lines[j].startswith((" ", "\t")): j -= 1
    head = lines[j]
    if head.startswith("if "): return "at start, if " + head[3:30]
    if head.startswith("async def") and i >= 2 and "routes" in lines[j - 1]: return "on a web request"
    if head.startswith("class "): return "when the node runs"
    if head.startswith(("def ", "async def")): return "when called"
    return "?"
lines = FILE.splitlines(); hits = []
for i, l in enumerate(lines):
    tags = [k for k, p in PAT.items() if re.search(p, l)]
    if tags: hits.append((i + 1, when(lines, i), tags)); print(f"line {i + 1:2d}  {when(lines, i):30s} {','.join(tags):24s} {l.strip()[:58]}")
assert any(h[1] == "at start" and "install" in h[2] for h in hits)
assert any(h[1] == "when the node runs" and "code from text" in h[2] for h in hits)
print(f"\n{len(lines)} lines, {sum(1 for l in lines if not l.startswith((' ', chr(9))) and l)} of them run as soon as ComfyUI imports this file")
print("worst first: runs at start and changes your environment, then reacts to outside input, then runs only when you ask")
tree = [".py 12", ".js 3", ".so 1", ".pkl 2", "requirements.txt", "prestartup_script.py"]
print("\nthings to look for in the file list before reading any line")
for t in tree:
    why = {".so 1": "compiled, you can't read it", ".pkl 2": "a pickle can run code when loaded", "prestartup_script.py": "main.py runs this before the rest of ComfyUI starts", "requirements.txt": "dry-run it against your constraints"}.get(t, "ordinary")
    print(f"  {t:22s} {why}")
print("\npin what you read. If one byte changes, so does the digest")
a = hashlib.sha256(FILE.encode()).hexdigest()[:16]; b = hashlib.sha256((FILE + " ").encode()).hexdigest()[:16]; print(f"  file as read {a}\n  one space more {b}")
assert a != b
