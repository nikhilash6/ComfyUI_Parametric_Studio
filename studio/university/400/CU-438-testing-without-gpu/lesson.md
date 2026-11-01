# CU-438 - Testing your node without a GPU

**Objective.** Catch most node bugs with no card and no model, at three levels of test. Taught by Captain Graph.

## The idea

A node is a Python class. Most of what goes wrong with one is in the Python: a bad schema, a wrong return, a changed input, a hook that lies. None of that needs a graphics card, and none of it needs a real model. A tensor of zeros will do.

There are three levels. Each costs more and catches more.

| Level | What you run | What it catches | Time |
|---|---|---|---|
| 1 | The function directly | Wrong maths, changed inputs, wrong shape | Under a second |
| 2 | `GET_SCHEMA` and `validate_prompt` | Bad schema, wrong types, ranges | A few seconds |
| 3 | The real engine, in one process | Return shapes, caching, lazy, lists, expansion | A few seconds |

Which test catches which bug?

{{play:f_tests}}

## Level 1: call it

A V3 `execute` is a classmethod, so you can just call it. We ran this with no engine loaded beyond the import. In V1, make an instance and call its function.

```python
def test_brighten_doubles():
    x = torch.full((1, 2, 2, 3), 0.25)
    r = Brighten.execute(image=x, amount=2.0)
    assert torch.allclose(r[0], torch.full_like(x, 0.5))

def test_does_not_change_input():
    x = torch.full((1, 2, 2, 3), 0.25)
    y = x.clone()
    Brighten.execute(image=x, amount=2.0)
    assert torch.equal(x, y)
```

Five tests are worth writing for almost any image node: the schema is sound, the input is untouched, the output stays in range, the shape is right, and the same input gives the same answer. Build the test inputs by hand with the right axes (CU-103).

If your node reads `cls.hidden`, a direct call won't work: `hidden` is `None` outside the engine. Use level 3 for that.

## Level 2: the schema and the validator

`GET_SCHEMA` runs the schema's own checks. It told us:

```
ValueError: Input ids must be unique, but ['a'] are not.
Exception: No execute function was defined for node class NoExec.
```

Then the validator. Add your class to the node table in the test, build a graph as a dict, and call `validate_prompt`. It returns the same errors a user would see (CU-290).

## Level 3: the real engine, in one process

This is the one most people don't know about. You don't need a server. The script that checks this university's graphs does it this way, and so did the runs in these lessons.

```python
import os, sys, asyncio, json, tempfile
os.environ["CUDA_VISIBLE_DEVICES"] = ""          # hide the card
sys.path.insert(0, COMFY); os.chdir(COMFY); sys.argv = ["test"]

from comfy.cli_args import args
args.cpu = True
args.disable_all_custom_nodes = True             # only what you add

import folder_paths
tmp = tempfile.mkdtemp()
folder_paths.set_output_directory(tmp)           # keep test files out of your real folder
folder_paths.set_temp_directory(tmp)

import nodes, execution
asyncio.run(nodes.init_extra_nodes(init_custom_nodes=False, init_api_nodes=False))

class FakeServer:
    client_id = None; last_node_id = None; last_prompt_id = None
    def send_sync(self, *a, **k): pass
    def queue_updated(self): pass

nodes.NODE_CLASS_MAPPINGS["Brighten"] = Brighten  # your class under test

def run(ex, graph):
    ok, err, outs, node_errors = asyncio.run(
        execution.validate_prompt("test", graph, None))
    assert ok, node_errors
    ex.execute(graph, "test", {}, sorted(outs))
    return ex.success

ex = execution.PromptExecutor(FakeServer(), cache_type=execution.CacheType.CLASSIC,
                              cache_args={"lru": 0, "ram": 0.0, "ram_inactive": 0.0})
```

On our test machine the setup took about 8 seconds, once, and each graph then took a fraction of a second. Use core nodes such as `EmptyImage` for inputs, and this graph is the shape to copy.

{{graph:nm_first}}

Now you can test behaviour that needs the engine. Count calls in a list your node appends to:

- **Caching:** run the same graph twice in one executor. Your node should run once. Change one value, and it should run again.
- **A fingerprint:** change what the hook returns, and queue again.
- **Lazy:** add a counting node on each branch, and check which ran.
- **Lists:** check the number of calls.
- **Expansion:** check your new class names exist.

Here's what level 3 caught that level 1 could not, from real runs:

```
return x, not (x,)     TypeError: object of type 'int' has no len()
two outputs, returns 1 IndexError: list index out of range
wrong argument name    TypeError: WrongArg.r() got an unexpected keyword argument 'x'
expand with no flag    Node ExpNoClone is not expandable, but expand included in NodeOutput
```

Errors in a run don't raise. They arrive as a message, so read them: look in `ex.status_messages` for `execution_error`, which holds `exception_type` and `exception_message`. And check `ex.success`.

## What you still need a card for

Speed, memory use, and whether real weights give a good picture. Run those by hand before a release. For everything else, a CPU is enough, and that means your tests can run on a free build server.

ComfyUI's own suite is a good model. `tests/execution/test_execution.py` starts a real server and drives it with a builder, and `tests/execution/testing_nodes` holds small nodes made for testing. Its flags are worth knowing too: `--cpu` and `--quick-test-for-ci` exist for this, and `--whitelist-custom-nodes` lets you load only your pack.

## What goes wrong

- **Tests write to your real output folder.** Set the folders first, as above. Never point tests at live accounts or a server you use.
- **A test passes alone and fails in a group.** `_io` caches schema values on the class, and your test may add to a shared table. Use unique node names per test.
- **`type object 'PromptServer' has no attribute 'instance'`.** Some core nodes call the server directly, and there's no server here. `GetImageSize` and Start Loop do this. Give `server.PromptServer.instance` a small stub, or avoid them.
- **`'_loop_body'` KeyError.** Validation annotates the prompt, so run the same object you validated, not a fresh copy. The same goes for value conversions: `3.7` becomes `3` in the object you validated.
- **Your test checks nothing.** Break the node on purpose once. If the test still passes, it's not a test. The lab does that.
- **A real run fails with no exception in your test.** You didn't look at `ex.success`.

## Lab

The lab runs five plain tests against one good node and five broken ones. It uses a tiny stand-in for the base class, because labs can't import ComfyUI. Every broken node must fail at least one test.

```text
node      schema           input_untouched  range            shape            same_twice
Good      pass             pass             pass             pass             pass
InPlace   pass             FAIL             FAIL             pass             pass
NoClamp   pass             pass             FAIL             pass             pass
Swapped   FAIL             pass             pass             pass             pass
DupId     FAIL             pass             pass             pass             pass
Stateful  pass             pass             pass             pass             FAIL
```

Read down the columns. Each test earns its place by catching something the others miss.

## Sources

- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_api/latest/_io.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_io.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, tests/execution/test_execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/tests/execution/test_execution.py)
