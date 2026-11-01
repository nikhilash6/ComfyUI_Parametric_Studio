# CU-460 - Queue a graph from a script

**Objective.** Write a client that sets values on a graph, queues it, waits for the end, tells success from failure, and downloads the right file. Taught by Captain Graph.

## The idea

CU-224 listed the calls. This lesson joins them into a job loop you can trust, which is a short program with five steps:

1. Load an API-format graph and copy it.
2. Set your values.
3. `POST /prompt`, and handle a refusal.
4. Wait for the job to end.
5. Read `/history/{prompt_id}`, check the status, then fetch files with `/view`.

Start with a graph that needs no model. Anything you learn here works the same with a real one.

{{graph:a_save_preview}}

Try the request, and notice what stays the same when the seed changes.

{{play:api}}

## The script

This uses only the Python standard library and waits by asking the history. We checked each call shape against `server.py`. We did not run this listing against a live server, so run it on your own and read what it prints.

```
import copy, json, time, urllib.parse, urllib.request, uuid

SERVER = "http://127.0.0.1:8188"

def post_prompt(graph, client_id):
    body = json.dumps({"prompt": graph, "client_id": client_id}).encode()
    req = urllib.request.Request(SERVER + "/prompt", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:      # a 400 carries the reasons as JSON
        raise SystemExit(json.dumps(json.load(e), indent=1))

def wait_for(prompt_id, timeout=600, every=1.0):
    end = time.time() + timeout
    while time.time() < end:
        with urllib.request.urlopen(f"{SERVER}/history/{prompt_id}") as r:
            h = json.load(r)
        if prompt_id in h:
            return h[prompt_id]
        time.sleep(every)
    raise TimeoutError(prompt_id)

def fetch(f):
    q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f["subfolder"], "type": f["type"]})
    with urllib.request.urlopen(f"{SERVER}/view?{q}") as r:
        return r.read()

graph = copy.deepcopy(json.load(open("graph_api.json")))
graph["1"]["inputs"]["color"] = 0xF5C518

reply = post_prompt(graph, str(uuid.uuid4()))
if reply["node_errors"]:
    print("some outputs were dropped:", reply["node_errors"])
job = wait_for(reply["prompt_id"])
if job["status"]["status_str"] != "success":
    raise SystemExit(job["status"]["messages"])
for node_id, out in job["outputs"].items():
    for f in out.get("images", []):
        if f["type"] == "output":
            open(f["filename"], "wb").write(fetch(f))
```

Asking the history once a second is simple and survives a dropped connection. Its one cost is that you see nothing until the end. For live progress, add the websocket from CU-461. The official example does it with the third-party `websocket-client` package.

## Why each step is there

**Copy before you edit.** A loop that edits the same dict carries the last job's values into the next one.

**Open the socket before you post.** If you use the websocket, connect first. Messages to a client that has no socket yet are dropped: `send_json` only sends when the id is in `self.sockets`. A job that finishes first looks like one that never ended. This is why the official example makes its socket before it queues.

**You may choose the id.** Send your own `prompt_id` and you know it before the reply arrives, which helps you log it or match socket messages. It must be a UUID in lowercase hyphenated form. `validate_job_id` refuses other spellings, on purpose, since the id gets compared exactly everywhere.

**Filter by `type`.** History lists every node that returned files. A preview node's file has `type` of `temp`. The folder for `temp` is not for keeping, so take what you want to keep from `output`.

**Uploads go first.** A `LoadImage` needs its file on the server. `POST /upload/image` takes a multipart form with `image`, and optionally `subfolder`, `type` and `overwrite`. Without `overwrite`, a clash with a different file gets a new name such as `photo (1).png`, and the reply tells you the name it used. Put that name into the graph, not the one you started with.

## Lab

The lab runs the same logic against an in-memory stub, with no network. It shows the protocol and not a real server's timing.

```text
finished after polls: 2  status: success True
  node 2: output  subfolder 'university'  filename first_00001_.png
  node 3: temp    subfolder ''            filename ComfyUI_temp_abc_00001_.png
downloaded: b'\x89PNG'
```

The stub makes the history empty on the first ask, as the real one is until a job ends. The temp file's name is made up, but its `type` is what matters. A `filename_prefix` of `university/first` comes back split in two, as the real `SaveImage` did when we ran it, which is why `/view` needs `subfolder` as well as `filename`.

A refused graph, then a bad and a good id:

```text
too wide: None
prompt_outputs_failed_validation
  node 1 EmptyImage: value_bigger_than_max (width)
```

```text
my own id MY-JOB-1: ['invalid_prompt_id']
my own id, a real UUID: 12345678-1234-4234-8234-1234567890ab
```

## What goes wrong

- **You posted the save format.** The file from File, Save has `nodes` and `links`. The server wants the API dictionary. See CU-462.
- **Your job "never ends".** It may have failed with no end message reaching you, or you connected after it ended. Set a timeout and check the history.
- **Every picture is the same, and quick.** The seed never changed. The API format has only a number, and "randomize" is not applied for you. Set a new seed yourself.
- **The history is gone.** It holds at most 10,000 jobs and lives in memory, so a restart empties it. Copy files and status while you can.
- **A second script interferes.** There is one queue. `POST /queue` with `clear` and `POST /interrupt` with no id act on everybody's work. Pass your `prompt_id` to `/interrupt`.
- **`/view` says 400 or 403.** A filename that starts with a slash or contains `..` gets 400. A subfolder that leaves the folder gets 403. Use the three values history gave you, unchanged.

## Sources

- [ComfyUI docs: ComfyUI Server Routes (HTTP and WebSocket API)](https://docs.comfy.org/development/comfyui-server/comms_routes)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/jobs.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/jobs.py)
- [ComfyUI v0.43.0, script_examples/websockets_api_example.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/script_examples/websockets_api_example.py)
- [ComfyUI v0.43.0, script_examples/basic_api_example.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/script_examples/basic_api_example.py)
