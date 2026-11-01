# CU-405 - Agents on ComfyUI: tools, verification, side-effect safety

**Objective.** Give a model tools to queue graphs, with checks before and after each run and limits it can't talk its way past. Taught by Captain Graph.

## The idea

An agent is a program that asks a language model what to do next, runs a tool it picks, and shows the result to the model. On ComfyUI, the tools are HTTP calls from CU-224. The model is good at guessing node names, and it guesses wrong often. A graph it wrote may invent a node, skip an input, or quietly ask for something huge.

So the rule on the bridge is simple: **the model proposes, plain code checks, and limits live outside the model.**

Three layers.

1. **Before the run.** Check the graph against facts from `/object_info`, not from the model's memory.
2. **The gate.** Decide which actions may run with no person involved.
3. **After the run.** Read what really happened. "I queued it" isn't "it worked".

## Before the run

`POST /prompt` calls `validate_prompt`, so the server gives you most of a verifier free. It reports `missing_node_type`, `required_input_missing`, `return_type_mismatch`, `value_not_in_list`, `prompt_no_outputs` and more. Pass those messages back to the model and let it fix the graph.

Practise reading them.

{{play:graphfix}}

A cheap first check on your own side still pays. It catches invented nodes before they use up a turn, and it can apply rules the server doesn't have, such as a size limit.

{{graph:f_validation_base}}

## The gate

Decide for each action, in code. Here's one policy.

{{play:agentgate}}

Things to know when you write yours:

- ComfyUI's routes don't ask who's calling (CU-463). Your gate is the only one there is.
- Nodes marked as API nodes spend credits on outside services. `/object_info` reports `api_node` for them, so a checker can see one before the run. Treat them as asking a person.
- A file an agent reads, or a pack's README, can hold instructions aimed at the model. Treat tool output as data. Don't widen permissions because some text asks you to.
- Limit the jobs per task, the sizes and the step counts. A loop that re-queues forever is the classic failure.

## After the run

Read `/history/<id>`. Check `status`, then check `outputs`, then fetch the file. A model can only report what your tool returns, so return the real facts. Showing the picture to a person, or to a vision model, is the only check of whether it's the right picture.

## In ComfyUI

`app/agent_host.py` loads an optional package through the `comfyui.agent` entry point, and leaves the agent process, its storage and its trust boundary to that package. We read that loader, not the package. So this lesson teaches the rules for any agent, not that one.

## What goes wrong

- **Invented nodes.** The model names a node that sounds right. Fix: send it a short list of real ones from `/object_info`, and check with code.
- **It passes, and it's wrong.** Validation sees types. A swapped positive and negative prompt passes, and so does 8192 wide in the lab. Add your own limits.
- **Reporting success without looking.** A job can finish with no file, as the lab's third case shows. Require a fetched file.
- **The model is told to be careful.** Instructions aren't limits. A rule in a prompt can be ignored or argued with. Code can't.
- **Stale facts.** Node lists change as packs change. Fetch `/object_info` per session and don't bake it into a prompt.
- **The agent stops others' jobs.** `/interrupt`, `/free` and clearing the queue touch everyone on that server. Keep them behind a person.

## Lab

The verifier is a plain-code copy of a few rules. The names are the server's. The real server stops at the first unknown node, and this copy carries on.

```text
graph                  problems
good                   []
invented node          [('2', 'missing_node_type'), ('3', 'exception_during_inner_validation:images')]
forgot an input        [('1', 'required_input_missing:height')]
wire to nothing        [('2', 'exception_during_inner_validation:image')]
output slot too big    [('2', 'exception_during_inner_validation:image')]
wrong type on a wire   [('2', 'return_type_mismatch:image')]
no output node         [('-', 'prompt_no_outputs')]
```

```text
8192 wide passes these checks: True  so a size limit is your job, or the agent queues a huge job
```

The gate is plain code too, so a model can't talk it round.

```text
action                 allowed?
GET /object_info       yes
POST /prompt           yes
POST /queue clear      ask a person
POST /free             ask a person
API node in graph      ask a person
shell command          no
fourth POST /prompt with a limit of 3: ask a person
```

And what to do with a result:

```text
run              what the agent should do
ok               1 file: fetch it and look before reporting
failed           failed: read status messages
ran, no images   no files: don't report success
```

## Sources

- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, app/agent_host.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/app/agent_host.py)
