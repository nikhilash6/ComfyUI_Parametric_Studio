# CU-224 - The API: queue, watch, fetch

**Objective.** Name the calls a script needs to queue a prompt, follow it to the end and download the result, and say which one tells you a job failed. Taught by Captain Graph.

## The idea

The web page is one client among others. Anything it does goes over HTTP and a websocket, and your script can use the same calls. There is no separate "API mode". The server you already run is the API.

Three things to hold on to:

- `POST /prompt` checks the graph and puts it in the queue. It does not wait for the picture.
- The websocket tells you what is happening.
- `/history` tells you what happened, and `/view` hands you the file.

This graph needs no model, so it is a good first thing to queue. It saves one file and previews another.

{{graph:a_save_preview}}

Build the request here. It sends nothing, it just shows you the body.

{{play:api}}

## The calls

From `server.py` and `execution.py` at v0.43.0. These routes also exist with `/api` in front, so `/api/prompt` and `/prompt` are the same thing.

| Call | What it does |
|---|---|
| `POST /prompt` | Validates and queues. 200 gives `prompt_id`, `number`, `node_errors`. 400 gives `error` and `node_errors` |
| `GET /ws?clientId=...` | The websocket. Events for that client |
| `GET /history/{prompt_id}` | Outputs and status when finished. An empty `{}` until then |
| `GET /view?filename=&subfolder=&type=` | Fetches a file. `type` is `output`, `input` or `temp` |
| `GET /queue` | What is running and what is waiting |
| `POST /queue` | `{"clear": true}` empties the waiting list, `{"delete": [ids]}` removes jobs |
| `POST /interrupt` | Stops the running job. Pass `prompt_id` to stop it only if that job is the one running |
| `POST /free` | `{"unload_models": true, "free_memory": true}` asks for memory back |
| `GET /object_info` | Every node's inputs and outputs |
| `POST /upload/image` | Puts an input file on the server |
| `GET /system_stats` | Versions and memory |

The body of `POST /prompt` is `{"prompt": <API format graph>, "client_id": "..."}` (CU-110 covers the format). `prompt_id` is optional, and if you send one it must be a UUID in lowercase hyphenated form, or you get a 400 `invalid_prompt_id`. Validation runs inside this call, so a bad graph fails right there, without being queued.

## The order of events

We ran ComfyUI's real `PromptExecutor` on a CPU with a test server that records what it is told to send. A first run of a three-node graph with a progress bar sent this, leaving out the `progress_state` messages it sends around each node:

```
execution_start
execution_cached (the list of nodes already stored)
executing node 1
executing node 2, progress, progress
executing node 3, executed (it saved a file)
execution_success
executing with node = null
```

That last line is not from the executor. `prompt_worker` in `main.py` sends it after every job, whether the job worked or not. The official example `script_examples/websockets_api_example.py` treats `executing` with a null node and its own `prompt_id` as the end of the job. CU-461 goes through every message.

## Lab

This runs against an in-memory stub that follows the code above. It has no network and it never touches a real server, so it shows the protocol, not the real server's timing.

```text
POST /prompt, unknown node -> 400 missing_node_type
POST /prompt, no output    -> 400 prompt_no_outputs
POST /prompt, good         -> 200 {'number': 0, 'node_errors': {}}
```

```text
  execution_start {}
  execution_cached {'nodes': []}
  executing {'node': '3'}
  executing {'node': None}
```

Those four lines are from the full list the lab prints, with the sampler's progress and the save node's `executed` event in between.

```text
GET /view?filename=app_00001_.png&subfolder=&type=output -> b'\x89PNG'
same prompt again: ['execution_start', 'execution_cached', 'executed', 'execution_success', 'executing']  cached: ['3', '9']
```

The second line shows a trap avoided. Queue the same prompt again and no node function runs, yet `emit_cached_output` still sends `executed` for the output node, and history still lists the file. So do not wait for a progress event, because a cached job has none.

```text
partly valid -> 200 node_errors for: ['10'] required_input_missing
failing job: ['execution_start', 'execution_cached', 'executing', 'execution_error', 'executing']
its history status: error
history of a job that has not finished: {}
```

A failed job also ends with `executing` and a null node. So that message means "stop waiting", not "it worked". The status in the history tells you which.

## What goes wrong

- **A 200 that hid a problem.** `validate_prompt` drops the outputs that fail and runs the rest. You get 200 with `node_errors` filled in. If one of two save nodes was broken, one file arrives and nothing else complains. Read `node_errors` every time.
- **Treating the end message as success.** Read `status.status_str` in `/history/{prompt_id}`. It is `success` or `error`, and `status.messages` carries the error.
- **No events arrive.** You left out `client_id`, or it doesn't match the `clientId` on your socket. Events are routed by that id.
- **Waiting for a progress bar on a cached job.** A job where everything is cached sends none.
- **The same file comes back.** Nothing changed, so nothing ran. Change the seed.
- **Binding to the network.** The default is 127.0.0.1, and `--listen` changes it. ComfyUI has no login. Read CU-463 first.

## Sources

- [ComfyUI docs: ComfyUI Server Routes (HTTP and WebSocket API)](https://docs.comfy.org/development/comfyui-server/comms_routes)
- [ComfyUI docs: Messages](https://docs.comfy.org/development/comfyui-server/comms_messages)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, comfy_execution/asset_enrichment.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/asset_enrichment.py)
- [ComfyUI v0.43.0, comfy_execution/jobs.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/jobs.py)
- [ComfyUI v0.43.0, script_examples/websockets_api_example.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/script_examples/websockets_api_example.py)
