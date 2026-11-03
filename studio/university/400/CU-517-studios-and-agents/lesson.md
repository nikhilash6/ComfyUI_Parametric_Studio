# CU-517 - History 17: Studios and agents: when models became pipelines

**Objective.** See how work moved from one model call to pipelines of graphs driven by programs, and build the bookkeeping that keeps a pipeline honest. Taught by Captain Graph.

## The idea

Open a recent ComfyUI and three things stand out in its code, compared with one checkpoint and one sampler.

- **Several models in one job.** A graph may hold a text encoder, a video model, an audio model and an upscaler.
- **Outside services as nodes.** `comfy_api_nodes` holds nodes that send your data to another company's server, and wait.
- **Programs driving it.** There's an API (CU-224), app mode (CU-223) and, in `app/agent_host.py`, a loader for an optional agent package.

Here "studio" means a program on top of ComfyUI that keeps several graphs, runs them in order, and hands one's files to the next. We don't attempt to date this shift, or name who was first. We can only show what's in the code at v0.43.0.

## One graph or several

Often a pipeline can live in one graph. A draft and a refine pass on the same canvas share the engine's cache (CU-102), so changing the last step re-runs only that.

{{graph:sd15_hires}}

Try predicting it.

{{play:cache}}

Several graphs earn their keep when:

- A step needs a different machine, or a person's choice.
- A graph would hold too many models at once for your memory.
- You want to stop, look, and go on tomorrow, since the cache is lost on restart.

Hand-off is by file. `/history` names the output, `/view` fetches it, and `/upload/image` makes it an input for the next graph.

{{video:showcase/music_video.mp4|Our Music Video Maker recipe, a pipeline of separate graphs: Music 3 writes the song first, FLUX.2 Klein draws one character into each keyframe, H3 moves each keyframe with its own camera move, and the edit is cut to the song. This file is 24.9 s, 598 frames, with the song. Recorded: 781.4 s for the whole recipe, peak 68.6 GiB, so don't read that peak as one model's.|showcase/music_video.webp}}

## The ledger

A script calling several graphs needs what the engine gave you free: "did I already do this?" So store, per step, a hash of its graph and inputs, and its output file. If a step fails, re-running the pipeline repeats only what's missing.

## Waiting for the outside

An API node sends a request and polls until the far side finishes. `poll_op` in `comfy_api_nodes/util/client.py` is that loop. The local server is waiting on someone else's queue. It has a price, and your inputs leave your machine.

## What an agent adds

An agent picks which graph to run and sets its values. CU-405 covers the checks. The pipeline's ledger is what lets an agent retry without paying twice.

{{graph:sd15_two_stage}}

## What goes wrong

- **Reused file names.** If a key is built from a file name that repeats, a new input can look like an old one. The stub's counter avoids that here, and `SaveImage`'s counter does the same. Hash the content for real work.
- **The ledger outlives the files.** A file you deleted is still in your ledger. Check it exists before you skip a step.
- **Each step re-loads the models.** Separate graphs on one server still share the loaded-model cache, until memory runs short or a different model is needed. Order steps to reduce swaps.
- **Calling a remote node "free".** It's a real charge and an upload. Count it, and ask first.
- **Partial failures reported as success.** Check each step's status (CU-461). A pipeline's status is its worst step's.

## Lab

A stub server, three steps, and a ledger. The second step fails once.

```text
first try: stopped at refine  calls: ['draft', 'refine']
second try: upscale_00004_.png  calls: ['draft', 'refine', 'refine', 'upscale']
again, nothing changed: upscale_00004_.png  calls so far: 4
new prompt: upscale_00007_.png  calls so far: 7
```

The second try skipped the draft. The third ran nothing. A new prompt needed all three steps.

```text
split                  change the last step    why
one graph              it and what follows it  the engine's cache keeps earlier results, while they stay in memory
three graphs + ledger  1 graph runs            your ledger keeps file names, for as long as the files stay
```

And a poll that knows when to give up:

```text
poll: ('done', 3) ('failed', 2) ('gave up', 10)
```

## Sources

- [ComfyUI v0.43.0, app/agent_host.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/app/agent_host.py)
- [ComfyUI v0.43.0, comfy_api_nodes/util/client.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api_nodes/util/client.py)
- [ComfyUI v0.43.0, comfy_execution/caching.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/caching.py)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
