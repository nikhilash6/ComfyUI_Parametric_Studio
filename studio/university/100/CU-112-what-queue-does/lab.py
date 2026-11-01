# CU-112 lab: what happens to a job after you press Queue, from the queue's order to the name of the file. Standard library only.
# The order follows post_prompt in server.py and PromptQueue in execution.py. The file names follow get_save_image_path in folder_paths.py.
# A run of the real function in a throw-away folder gave the same answers for these prefixes.
import heapq

# 1. The queue is a heap of tuples, smallest number first. Sending front=true makes the number negative.
heap = []; number = 0
def post(name, front=False):
    global number
    n = -number if front else number
    number += 1
    heapq.heappush(heap, (n, name))
post("job A"); post("job B"); post("job C"); post("job D (front)", front=True)
order = []
while heap: order.append(heapq.heappop(heap)[1])
print("sent:  job A, job B, job C, job D (front)")
print("runs: ", ", ".join(order))
assert order[0] == "job D (front)" and order[1:] == ["job A", "job B", "job C"]

# 2. What a queued item holds, and what history keeps. main.py removes item 5 before it reaches history.
item = (0, "the prompt id", {"the": "API graph"}, {"extra_pnginfo": {"workflow": "the save format"}}, ["the output node ids"], {"api_key_comfy_org": "secret"})
names = ["number", "prompt_id", "prompt", "extra_data", "outputs_to_execute", "sensitive"]
remove_sensitive = lambda prompt: prompt[:5] + prompt[6:]
kept = remove_sensitive(item)
print("\nqueued item:  ", ", ".join(names))
print("in history:   ", ", ".join(names[:len(kept)]))
assert len(kept) == 5 and all("secret" not in str(x) for x in kept)

# 3. A small os.path.normpath, enough for the prefixes below.
def normpath(p):
    absolute = p.startswith("/"); out = []
    for s in p.split("/"):
        if s in ("", "."): continue
        if s == ".." and out and out[-1] != "..": out.pop()
        elif s == ".." and absolute: continue
        else: out.append(s)
    return ("/" if absolute else "") + "/".join(out) or "."

def save_path(prefix, files, width=512, height=512):
    """-> (subfolder, name, counter) or None when the path would leave the output folder. files maps a subfolder to the names in it."""
    p = prefix.replace("%width%", str(width)).replace("%height%", str(height))
    p = normpath(p); sub, _, name = p.rpartition("/")
    if sub.startswith("/") or sub == ".." or sub.startswith("../") or p.startswith("/"): return None
    def map_filename(f):
        n = len(name); head = f[:n + 1]
        try: digits = int(f[n + 1:].split(".")[0].split("_")[0])
        except ValueError: digits = 0
        return digits, head
    found = [m for m in map(map_filename, files.get(sub, [])) if m[1][:-1].lower() == name.lower() and m[1][-1] == "_"]
    return sub, name, max(found)[0] + 1 if found else 1

files = {"": ["ComfyUI_00001_.png", "ComfyUI_00002_.png", "ComfyUI_00009_.png", "ComfyUI_notes.txt", "Other_00050_.png"]}
print(f"\n{'filename_prefix':<24}{'subfolder':<12}{'name':<12}{'counter':<9}file")
expect = {"ComfyUI": 10, "Other": 51, "portraits/fox": 1, "a/b/../c/x": 1, "%width%x%height%/img": 1, "portraits/": 1}
for p, c in expect.items():
    sub, name, n = save_path(p, files)
    print(f"{p:<24}{sub or '(none)':<12}{name:<12}{n:<9}{(sub + '/' if sub else '') + f'{name}_{n:05}_.png'}")
    assert n == c
for p in ("../escape", "/tmp/x", "a/../../b"):
    assert save_path(p, files) is None
    print(f"{p:<24}refused: Saving image outside the output folder is not allowed.")

# 4. The number is the largest one found, plus one. A gap is never filled, and removing the last file frees its number.
gone = {"": [f for f in files[""] if "00009" not in f]}
print(f"\nfiles 1, 2, 9 present: next is {save_path('ComfyUI', files)[2]}.   file 9 deleted: next is {save_path('ComfyUI', gone)[2]}")
assert save_path("ComfyUI", files)[2] == 10 and save_path("ComfyUI", gone)[2] == 3

# 5. A batch takes one number per picture, from the same counter.
batch = [f"run_{i}_{1 + i:05}_.png" for i in range(3)]
print("batch of 3, prefix run_%batch_num%:", ", ".join(batch))

# 6. What the page asks the server for, from the record the node returned.
rec = {"filename": "fox_00001_.png", "subfolder": "portraits", "type": "output"}
print("record:", rec)
print("fetched with: /view?filename=" + rec["filename"] + "&subfolder=" + rec["subfolder"] + "&type=" + rec["type"])
