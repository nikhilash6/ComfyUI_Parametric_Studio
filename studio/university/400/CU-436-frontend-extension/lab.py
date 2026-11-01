# CU-436 lab: how a pack's WEB_DIRECTORY turns into URLs. A port of the listing in server.py ("/extensions") and the name rule in nodes.py, on an in-memory file tree. It serves nothing, and does no browser work. The real listing is described in the lesson.
import re
TREE = ["my_pack/__init__.py", "my_pack/nodes.py", "my_pack/js/brighten.js", "my_pack/js/sub/more.js", "my_pack/js/style.css", "my_pack/js/docs/Brighten.md", "my_pack/README.md"]
def listing(tree, pack, web_dir):
    web_dir = web_dir.lstrip("./").rstrip("/"); root = f"{pack}/{web_dir}/"
    return ["/extensions/" + pack + "/" + f[len(root):] for f in tree if f.startswith(root) and f.endswith(".js")]
def served(path, pack, web_dir):
    web_dir = web_dir.lstrip("./").rstrip("/"); root = f"{pack}/{web_dir}/"
    return "/extensions/" + pack + "/" + path[len(root):] if path.startswith(root) else None
L = listing(TREE, "my_pack", "./js")
print("the page loads these as modules:"); [print(" ", u) for u in L]
assert L == ["/extensions/my_pack/brighten.js", "/extensions/my_pack/sub/more.js"]
print("served, but not loaded by itself:", served("my_pack/js/style.css", "my_pack", "./js"))
print("not served at all:", served("my_pack/README.md", "my_pack", "./js"))
assert served("my_pack/README.md", "my_pack", "./js") is None
# The browser resolves a relative import against the file's URL.
def resolve(base, rel):
    parts = base.split("/")[:-1]
    for p in rel.split("/"):
        if p == "..": parts.pop()
        elif p != ".": parts.append(p)
    return "/".join(parts)
for f in L: 
    print(f"{f}: ../../scripts/app.js -> {resolve(f, '../../scripts/app.js')}")
assert resolve(L[0], "../../scripts/app.js") == "/scripts/app.js" and resolve(L[1], "../../scripts/app.js") != "/scripts/app.js"
print("so a file in a subfolder needs:", resolve(L[1], "../../../scripts/app.js"), "from ../../../scripts/app.js")
# The order the docs give when the page loads.
ORDER = ["init", "addCustomNodeDefs", "getCustomWidgets", "beforeRegisterNodeDef", "registerCustomNodes", "beforeConfigureGraph", "nodeCreated", "loadedGraphNode", "afterConfigureGraph", "setup"]
print("\nhook order on page load:", " > ".join(ORDER))
assert ORDER.index("beforeRegisterNodeDef") < ORDER.index("nodeCreated") < ORDER.index("setup")
# Patch and keep the old one, or you remove what another extension added.
log = []
class Proto: pass
Proto.onExecuted = None
def install(name, chain):
    old = Proto.onExecuted
    def patched(msg):
        if chain and old: old(msg)
        log.append(name)
    Proto.onExecuted = patched
install("first", True); install("second", True); Proto.onExecuted("m"); print("both chain:", log); assert log == ["first", "second"]
log.clear(); Proto.onExecuted = None; install("first", True); install("rude", False); Proto.onExecuted("m"); print("second does not chain:", log); assert log == ["rude"]
