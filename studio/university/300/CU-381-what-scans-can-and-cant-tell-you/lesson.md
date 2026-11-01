# CU-381 - What scans can and can't tell you

**Objective.** Read a scan result properly: follow a hit to a decision, know what silence can't tell you, and say what a clean scan means. Taught by Captain Graph.

## What a scan is

A scanner is usually pattern matching over text, sometimes over a parsed tree. It's fast, it never gets bored, and it knows nothing about intent. It looks for words such as `eval(`, `pip` or `b64decode`. So it makes two kinds of mistake, and you need to expect both.

- **False alarm.** A hit on harmless text.
- **Miss.** Silence on harmful code.

## Common false alarms

These patterns show up again and again. Each one looks alarming and usually isn't. Still follow each to the line, since sometimes it's real.

- `base64.b64decode` on an image field. Decoding a picture isn't running code.
- `pip install` inside an error message telling a human what to do.
- `replicate` as a padding mode, which trips a search for a paid service with that name.
- `eval(` in a comment, or `.eval()`, the PyTorch call that puts a model in evaluation mode.
- `requests.get` to your own machine: a pack talking to ComfyUI's own API.
- `dict(os.environ)` copied to pass to a subprocess, which looks like harvesting credentials.
- A code hit in `tests/` or `docs/`, which never runs at start.

## What misses look like

- **A name built at run time.** `"ev" + "al"` has no `eval(` in it.
- **Things you can't read.** Compiled binaries, or a long string blob that gets decoded later.
- **Code fetched later.** Nothing bad in the pack today, then a download at run time.
- **Harm with ordinary words.** Opening a file named in a web request needs no scary word. It only needs a missing check.
- **Patterns no one thought to add.** Each new pattern catches more, and it can add new false alarms as well.

## Where a hit is matters more than what it is

The same line has very different meaning in different places. A `pip install` in a script nobody runs is a note. The same call at the top of `__init__.py` runs at every start, and can move versions other packs rely on. So for each hit, ask three things:

1. **When does this line run?** At start, on a request, in a node, or never?
2. **What decides its inputs?** A constant, or text from a workflow or a web request?
3. **What can it reach?** Your files, your network, your other packs?

Now judge some yourself.

{{play:scan}}

Then look at a graph with the same eyes. A workflow can carry text into a node:

{{graph:a_read_before_run}}

## What to say about a scan

Say "the scan found X at file and line, and I read it and it does Y". Say "the scan found nothing, and it can't see compiled files, so I also checked the file list". Don't say "it passed". A scan is a pointer that shows you where to read. It isn't a verdict.

ComfyUI's own security policy puts issues that need a specific custom node out of its scope and sends them to the node's maintainer. So nobody else is checking this for you by default.

## What goes wrong

- **Dropping a pack on one hit.** You may lose a good pack to a padding mode. Read the line first.
- **Installing a pack on a clean scan.** Silence is not evidence of good intent. It's only evidence that no pattern matched.
- **Adding patterns until it feels safe.** In the lab a new pattern catches some misses, leaves two, and fixes no false alarm. It doesn't end the mistakes.
- **Treating a scan count as a score.** Fifty hits in a big toolkit can all be harmless, and one in a small pack can be the whole problem.
- **Quoting a scan as if you'd read the code.** Say which of the two you did.

## Lab

A small scanner over sample lines. We wrote these lines and picked them to show both mistakes, so the counts tell you nothing about real packs.

```text
truth    scan     line
fine     hit      image = base64.b64decode(field)
fine     hit      raise ImportError("run pip install onnx")
fine     hit      x = pad(x, (1, 1), mode="replicate")
fine     hit      # do not use eval( here
fine     hit      requests.get("http://127.0.0.1:8188/object_info")
fine     hit      env = dict(os.environ)
bad      hit      exec(zlib.decompress(base64.b64decode(BLOB)))
bad      hit      subprocess.check_call([sys.executable, "-m", "pip", "install", "-U
bad      hit      return (eval(text_widget),)
bad      clean    f = getattr(__builtins__, "ev" + "al"); f(user_text)
bad      clean    import importlib; importlib.import_module("sub" + "process").run(c
bad      clean    state = pickle.load(open(path, 'rb'))
bad      clean    torch.load(path, weights_only=False)
bad      clean    open(request.query["path"]).read()
```

```text
hit on a bad line 3, hit on a fine line 6, clean on a bad line 5, clean on a fine line 0
of 9 hits, 6 were false alarms. of 5 clean lines, 5 were bad
these are our own samples, picked to show both mistakes. The counts say nothing about real packs.
```

Adding a pattern for loaders catches some misses and fixes no false alarms:

```text
adding a pattern catches some misses, it does not end the mistakes
with a loaders pattern: clean on a bad line 2, hit on a fine line 6
```

And the same text in different places:

```text
same line, different place. The text is equal, the risk is not
  tests/test_nodes.py, never imported            low
  docs/build.py, a script nobody runs at start   low
  a node's run method, on a text widget          high
  __init__.py at top level                       high
```

## Sources

- [ComfyUI v0.43.0, SECURITY.md](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/SECURITY.md)
- [PyTorch 2.15, torch.load](https://docs.pytorch.org/docs/2.15/generated/torch.load.html)
