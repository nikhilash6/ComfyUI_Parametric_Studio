# CU-380 - Finding out what a pack really does before you install it

**Objective.** Read a node pack as text and say when each part of it runs, what it can reach, and what you didn't read. Taught by Captain Graph.

## What you're agreeing to

Installing a pack isn't like opening a picture. ComfyUI's own `SECURITY.md` is direct: custom nodes "are arbitrary Python code and are trusted as much as any other software the user chooses to install". A pack runs as you, with your files, your keys and your network.

So the question isn't "is this pack good?". You can't answer that. The question you can answer is **"what did I read, what did I find, and what didn't I read?"** An answer of "safe" is one you can't honestly give. Say what you read.

## When does the code run?

Most of the skill is this one question. A scary line that runs only if you press a button is different from a dull line that runs at every start.

- **Before ComfyUI starts.** `main.py` runs each pack's `prestartup_script.py` if it has one. That's the earliest there is.
- **At import.** `load_custom_node` in `nodes.py` executes the pack's module. Everything at the top level of `__init__.py`, and anything it imports, runs at every start, whether or not you ever use a node.
- **In your browser.** Files under `WEB_DIRECTORY` are served to the page, and run there with what the page can see.
- **On a web request.** A route added to the server can be called by anything that can reach it.
- **When a node runs.** Only then, and with whatever inputs the graph gives it. A shared workflow can fill these in.

## A reading order

Don't read top to bottom. Read in order of when it runs and what it can reach.

1. **List the files first.** Look for compiled files such as `.so`, `.pyd` and `.pyc`, for pickles, and for huge single files. You can't read those, so write that down.
2. **`prestartup_script.py` and `__init__.py`.** Everything at top level. Follow what they import.
3. **`requirements.txt` and any install script.** Which versions would move? CU-450 has the dry run.
4. **Search the rest as text.** Patterns worth searching are `subprocess`, `pip`, `eval(`, `exec(`, `b64decode`, `torch.load(`, `pickle`, `requests.`, `urllib`, `routes.`, `os.environ`, `trust_remote_code`.
5. **Follow each hit to its line.** Decide what it does and when it runs. CU-381 is about the false alarms.
6. **The JavaScript, and any route handler.** Does a request's text reach a file path? Is anything sent out?
7. **Write it down.** Which version, what you read, what you found with file and line, what you didn't read.

Do this with the pack's files as text. Never import a pack to inspect it, and don't run Python from inside its folder: a pack can plant a file that shadows a standard module. A reader that parses without running is fine.

Practise now. These files are ours, written for this lab.

{{play:risk}}

Reading is a habit worth having for graphs too. A graph can be read before it's run:

{{graph:a_read_before_run}}

## Finding the right pack in the first place

Before any of this, check you need one (CU-385). Then check the name's owner: forks and same-named packs are common, and a name tells you nothing about the code (CU-382). Prefer the original of a fork unless the copy has a fix you can name. Stars tell you about attention, not about code, and new packs for new models have few.

## What goes wrong

- **Trusting a README.** It's the author's account of the pack, and what you need is the pack. "No telemetry" is a claim to check.
- **Reading only `nodes.py`.** The dangerous part, if there is one, is usually at import or in a helper. Start at the entry point.
- **A clean search means safe.** It means no pattern matched. Text can be built at run time, and compiled files can't be searched at all.
- **Reading once, then updating forever.** A new commit is new code. Pin what you read, and read the difference when you update.
- **Installing to find out.** That's what you were trying to avoid. Use a sandbox if you need to see it run (CU-450).

## Lab

The lab reads a file we wrote, as text, and sorts hits by when they run. Nothing is executed.

```text
line  4  at start                       install,process          subprocess.check_call([sys.executable, "-m", "pip", "insta
line 10  when the node runs             code from text           return (eval(text),)
line 11  at start                       file route               @PromptServer.instance.routes.get("/mypack/read")
line 13  on a web request               file route               return web.FileResponse(request.query["path"])
line 15  at start, if os.environ.get("MYPACK_UPDA install,process          subprocess.run(["git", "pull"])
```

Line 4 is the worst here: it changes your environment at every start. Line 10 runs on whatever text a graph gives it. Line 13 hands any file named in a web request to whoever asked. Note also line 15, hidden behind an environment variable.

```text
16 lines, 11 of them run as soon as ComfyUI imports this file
worst first: runs at start and changes your environment, then reacts to outside input, then runs only when you ask
```

Before reading a line, read the file list:

```text
things to look for in the file list before reading any line
  .py 12                 ordinary
  .js 3                  ordinary
  .so 1                  compiled, you can't read it
  .pkl 2                 a pickle can run code when loaded
  requirements.txt       dry-run it against your constraints
  prestartup_script.py   main.py runs this before the rest of ComfyUI starts
```

And pin what you read:

```text
pin what you read. If one byte changes, so does the digest
  file as read 749b67869d8eda0c
  one space more 3c5672760453e26e
```

## Sources

- [ComfyUI v0.43.0, SECURITY.md](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/SECURITY.md)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
