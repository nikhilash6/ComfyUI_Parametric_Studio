# CU-112 - What Queue really does, and where your picture went

**Objective.** Trace one press of Queue from the editor to a file on disk, and say what is sent, what waits, what history remembers and how the file gets its name. Taught by Captain Graph.

## The idea

Queue does not run anything in your browser. The editor writes the graph down, sends it to a server, and the server does the work when its turn comes. Nearly every "where did my picture go?" is answered by following that trip, so let's follow it.

Load this graph. It needs no model. It makes one picture and sends it two ways.

{{graph:a_save_preview}}

## The trip, stop by stop

**1. The editor writes the graph down.** It turns the canvas into the API format of CU-110 and posts it to `/prompt`. The body holds `prompt`, the graph, a `client_id`, and `extra_data`, which carries the save-format workflow under `extra_pnginfo`. That second copy is how the workflow ends up inside your PNG (CU-111).

**2. The server checks it.** `validate_prompt` runs before anything else (CU-102). If it fails you get a 400 with the errors for each node, and nothing is queued. If it passes you get a `prompt_id` and a `number` back straight away, long before any image exists.

**3. It waits in line.** The queue is a heap, so the smallest number goes first. Numbers count up, and asking for the front of the line makes your number negative.

**4. One worker takes one job.** A single thread runs `prompt_worker`, which pulls the next item and runs it. A job already running is not pushed aside by a job sent to the front. While it runs, the server sends messages over a WebSocket: `execution_start`, `execution_cached` naming the nodes it can skip, `executing` for the current node, `progress`, `executed` when a node has something to show, and `execution_success` or `execution_error` at the end.

**5. Output nodes write files.** `SaveImage` writes into the output folder. `PreviewImage` is the same code pointed at the temp folder. Each returns a small record: file name, subfolder, type.

**6. History is written.** When the job ends, the worker stores the prompt, the output records and a status. The page gets its picture by asking `/view` with that record.

## Where the files live

| Folder | What goes there | How long |
|---|---|---|
| output | `SaveImage` and the other save nodes | Until you delete it |
| temp | `PreviewImage`, named with `_temp_` and five random letters | Removed at the next start, when the assets system is off, which is the default |
| input | Pictures you upload, read by `LoadImage` (CU-116) | Until you delete it |

By default all three sit inside the ComfyUI folder. `--output-directory`, `--temp-directory`, `--input-directory` and `--base-directory` move them, so if your output folder looks empty, check how the server was started.

## How a file gets its name

`filename_prefix` is split into a subfolder and a name. The name gets a five-digit counter and a trailing underscore. The counter is the largest number already there for that name, plus one, so gaps stay gaps. A batch takes one number per picture.

The server fills in `%year%`, `%month%`, `%day%`, `%hour%`, `%minute%`, `%second%`, `%width%` and `%height%`, plus `%batch_num%` in the name. The editor separately turns `%date:yyyy-MM-dd%` into text before sending. Anything that would land outside the output folder is refused while the job runs.

{{play:savepath}}

## What history is, and isn't

History is a dictionary in the server's memory. It holds the graph, the extra data and the output records, up to about 10,000 jobs, and then the oldest goes first. Your account keys, if the job carried any, are stripped first. It does not hold the pictures, only their names. So after a restart the list is gone and the files in output are still there. To get an old graph back, drag its PNG onto the canvas (CU-110). That works because the workflow is inside the file, not because of history.

## What goes wrong

- **Queue twice, one file.** Nothing changed, so the second run came entirely from the cache, `SaveImage` included. In our run the folder held one file and the second history entry repeated the first record. Change a value, or set the seed to change after each run.
- **"My picture isn't in output."** Check whether the graph ends in `PreviewImage`. That file went to temp and goes away at the next start.
- **Nothing happens when you press Queue.** Validation refused the graph, so no job exists. Look for the red node and read the message.
- **`Saving image outside the output folder is not allowed.`** The prefix has `../` or an absolute path. Note that this is raised during the run, after the nodes before it have done their work.
- **A folder literally called `%date:yyyy-MM-dd%`.** A script sent the prefix straight to the server, and only the editor expands that form. Use `%year%-%month%-%day%`.
- **A prefix ending in `/`.** `portraits/` does not mean "the portraits folder". The path is normalised first, so it gives a file named `portraits_00001_.png` in the top folder. Write `portraits/fox`.
- **Numbers jump.** Deleting the highest file frees its number, and deleting a middle one does not.
- **`%batch_num%` overwrites the last run.** The counter looks for the name with the token still in it, and the files on disk have a number there, so it finds none and starts from 1 again. In our run a second batch reused the same two file names. Change the prefix each run, or leave the token out.

## Lab

The lab rebuilds the parts of this trip that can be checked without a server. First the line. Job D arrives last and asks for the front.

```text
sent:  job A, job B, job C, job D (front)
runs:  job D (front), job A, job B, job C
```

Then what a queued item holds, and what reaches history.

```text
queued item:   number, prompt_id, prompt, extra_data, outputs_to_execute, sensitive
in history:    number, prompt_id, prompt, extra_data, outputs_to_execute
```

Then the file names, with an output folder that already holds ComfyUI numbers 1, 2 and 9, and Other number 50.

```text
filename_prefix         subfolder   name        counter  file
ComfyUI                 (none)      ComfyUI     10       ComfyUI_00010_.png
Other                   (none)      Other       51       Other_00051_.png
portraits/fox           portraits   fox         1        portraits/fox_00001_.png
a/b/../c/x              a/c         x           1        a/c/x_00001_.png
%width%x%height%/img    512x512     img         1        512x512/img_00001_.png
portraits/              (none)      portraits   1        portraits_00001_.png
../escape               refused: Saving image outside the output folder is not allowed.
/tmp/x                  refused: Saving image outside the output folder is not allowed.
a/../../b               refused: Saving image outside the output folder is not allowed.
```

We also ran ComfyUI's real function on these prefixes in a throw-away folder, and it gave the same answers.

```text
files 1, 2, 9 present: next is 10.   file 9 deleted: next is 3
batch of 3, prefix run_%batch_num%: run_0_00001_.png, run_1_00002_.png, run_2_00003_.png
record: {'filename': 'fox_00001_.png', 'subfolder': 'portraits', 'type': 'output'}
fetched with: /view?filename=fox_00001_.png&subfolder=portraits&type=output
```

## What the lab leaves out

The lab has no server and no WebSocket. It does not cover partial runs from one chosen output, or stopping a job. For stopping: `/interrupt` asks the running job to stop, and a post to `/queue` can delete or clear jobs still waiting. CU-224 does all of this from a script. The caching in step 4 is CU-102 and CU-221.

## Sources

- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, folder_paths.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/folder_paths.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, app/assets/lifecycle.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/app/assets/lifecycle.py)
- [ComfyUI front end, packages/api-client/src/ComfyApi.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/packages/api-client/src/ComfyApi.ts)
- [ComfyUI front end, src/extensions/core/saveImageExtraOutput.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/extensions/core/saveImageExtraOutput.ts)
- [ComfyUI front end, src/utils/searchAndReplace.ts](https://github.com/Comfy-Org/ComfyUI_frontend/blob/main/src/utils/searchAndReplace.ts)
