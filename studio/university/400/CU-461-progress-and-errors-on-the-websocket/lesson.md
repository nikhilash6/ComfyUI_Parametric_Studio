# CU-461 - Progress and errors over the websocket

**Objective.** Say which messages the websocket sends and who receives them, then write a watcher that reports progress and tells success from failure. Taught by Captain Graph.

## The idea

`/history` tells you how a job ended. The websocket tells you what it's doing now. Connect to `/ws?clientId=<your id>`, send the same id as `client_id` when you post, and JSON messages arrive, each shaped as `{"type": ..., "data": ...}`. Previews arrive as binary frames.

## Which messages exist

The docs list nine types. The source has more. Each message about a job carries its `prompt_id`.

| Message | Sent when | Who gets it |
|---|---|---|
| `status` | On connecting (with your `sid`) and whenever the queue changes | Everyone, except the first one |
| `execution_start` | A job is about to run | The job's client |
| `execution_cached` | Start of a job. `nodes` lists what is already stored | The job's client |
| `executing` | A node is about to run. `node: null` means the job is over | The job's client |
| `progress` | A node with a progress bar moves. `value` and `max` | The job's client, or everyone if it has none |
| `progress_state` | Around each node, the state of all active nodes. It's not in the docs table | The same |
| `executed` | A node returned something for the page, such as files | The job's client |
| `execution_success` | Every node finished | The job's client |
| `execution_error` | A node raised. Has `node_id`, `node_type`, `exception_type`, `exception_message`, `traceback` | The job's client |
| `execution_interrupted` | Someone stopped it | The job's client, or everyone if it has none |

`executed` is not "a node finished". A node that returns nothing for the page sends none. Use `progress_state` or the next `executing` for that.

The docs table and the source agree on the nine types it names, and the source sends others that aren't in it, such as `logs` when you subscribe to them, `agent_status` and `feature_flags`.

## What a real job sends

Here are real captures. We ran ComfyUI's own `PromptExecutor` on a CPU with a stand-in server that records each `send_sync` call. Test nodes raised an error or an interrupt on purpose, and one had a progress bar.

{{graph:sd15_txt2img}}

The `KSampler` in that graph gets its progress bar from `prepare_callback` in `latent_preview.py`. We did not run that graph with a model here. Now find the message your script should stop on.

{{play:wsorder}}

## Lab

The lab replays those lists through a small watcher. The last message of each, `executing` with a null node, comes from reading `prompt_worker` in `main.py`, because the executor doesn't send it. We removed `progress_state` to keep the lists short.

```text
job             nodes run  cached  progress  files  result       why
first run               3       0         2      1  success      
same again              0       3         0      1  success      
a node raises           1       1         0      0  error        Boom ValueError: boom on purpose
interrupted             1       1         0      0  interrupted  stopped in Stop
```

Read the second row. The job ran no nodes and still delivered a file. A watcher that waits for progress would wait forever here.

The routing rule is short. In `send_json`, no id means everyone, a known id means one socket, and an unknown id means nobody.

```text
sent to me:           ['me']
sent to everyone:     ['me', 'other']
sent while I am away: []
```

There is no replay. If your connection drops during `execution_success`, that message is gone. So on reconnecting, ask `/history`. Reconnect with the same `clientId` and the server does send you the node it's on, if your job is running.

Now a job with no `client_id`. In a real run on the CPU, only `progress` and `progress_state` went out, with no target, and so to everyone. The lab writes down the rule from the source:

```text
a job queued with no client_id can still send: ['progress', 'progress_state', 'execution_interrupted']
```

So on a shared server you can see progress from other people's jobs. Compare `prompt_id` and ignore what isn't yours.

## Binary frames

A binary frame starts with 4 bytes, big-endian, giving its type. `BinaryEventTypes` in `protocol.py` names them: 1 is a preview, 3 is text, 4 is a preview with metadata. Type 2 exists in the table, but it's the internal one that `send_image` turns into type 1 frames. A type 1 frame has 4 more bytes for the format, which is why the official example skips `out[8:]`.

```text
('preview', 'JPEG', b'\xff\xd8..')
('preview+meta', {'node_id': '5', 'image_type': 'image/jpeg'}, b'\xff\xd8..')
('text', '5', 'loading')
```

Those frames were built by the lab, with the same layout as `send_image_with_metadata` and `send_progress_text`. You get type 4 only if your first message on the socket says you support it: `{"type": "feature_flags", "data": {"supports_preview_metadata": true}}`. Previews are off by default, because `--preview-method` defaults to none. A client can ask for one by setting `preview_method` in `extra_data` when it posts.

## What goes wrong

- **Your watcher hangs on a cached job.** You waited for `progress` or for `executing` on the output node. Stop only on `executing` with a null node and your `prompt_id`.
- **You report success too early.** `executing` with a null node also ends failed jobs. Watch for `execution_success`, or read `status.status_str` in the history.
- **The script crashes on a preview.** `json.loads` on a binary frame fails. Check whether the frame is text first, as the official example does.
- **Nothing arrives.** `client_id` and `clientId` differ, or you connected after the job ended.
- **Two scripts, one id.** A new socket with the same `clientId` replaces the old one, with no warning. The old script hears nothing more. Give each script its own id.
- **An error with no useful text.** Use `traceback` and `current_inputs` in `execution_error`. The same message is kept in `status.messages` in the history, so you can read it after a disconnect.

## Sources

- [ComfyUI docs: Messages](https://docs.comfy.org/development/comfyui-server/comms_messages)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, protocol.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/protocol.py)
- [ComfyUI v0.43.0, comfy_execution/progress.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/progress.py)
- [ComfyUI v0.43.0, script_examples/websockets_api_example.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/script_examples/websockets_api_example.py)
