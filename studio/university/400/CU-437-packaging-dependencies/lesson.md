# CU-437 - Packaging a pack without breaking anyone's install

**Objective.** Lay out a pack, declare what it needs, and avoid moving a library under someone else's feet. Taught by Captain Graph.

## The idea

Every pack runs in **one Python**, with one copy of each library. There is no wall between packs. If yours asks for `numpy==1.24.0` and a user installs it, every other pack gets that numpy too. Most broken installs start this way.

So packaging comes down to one question: what is the smallest thing you can ask of someone's machine?

## The layout

```
my_pack/
  __init__.py          what the loader imports
  nodes.py             your classes
  js/                  WEB_DIRECTORY, if you have one (CU-436)
  example_workflows/   graphs shown as templates
  pyproject.toml       name, version, what you need
  requirements.txt     only what ComfyUI doesn't already bring
  README.md            what it does, and what it needs
  LICENSE
```

The folder goes under `custom_nodes`. A pack can also be a single `.py` file.

## How it loads

From `load_custom_node` and `init_external_custom_nodes` in `nodes.py`:

1. Each folder in `custom_nodes` is imported in the order `os.listdir` gives. That order isn't sorted or promised.
2. Names ending in `.disabled` are skipped.
3. `NODE_CLASS_MAPPINGS` is read first. If it is absent, `comfy_entrypoint` is used. With neither, the pack is skipped with a warning.
4. An exception at import is caught and logged. Your pack shows `IMPORT FAILED` in the timing list, and the others carry on.

Two things follow.

**Names can clash.** A pack can't replace a core node: core names are passed in as `ignore`. But between two packs, the later one silently wins. So if you call your node `Blur`, you may lose to another pack on some machines and win on others. Prefix your ids: `MyPack_Blur`. The schema's docstring says the same.

**Importing should be cheap and safe.** Your module runs on every start for every user. Don't load a model, reach the network, or install anything at import. Import heavy libraries inside the function that needs them, and give a clear error if one is missing.

```python
@classmethod
def execute(cls, image):
    try:
        import cv2
    except ImportError:
        raise RuntimeError("MyPack_Edges needs opencv-python.")
```

That way one optional library doesn't cost a user the whole pack.

## Declaring what you need

ComfyUI doesn't install your requirements when it loads you. A person or a pack manager does. Your file is a request, and it may run on an install you have never seen.

- **List only what is new.** Don't list what ComfyUI's own `requirements.txt` already has, such as `torch`, `numpy`, `Pillow`, `safetensors`, `transformers`.
- **Never pin `torch`.** It has to match the user's card and drivers. Nobody can pick that for them from a text file.
- **Prefer a floor to an exact pin.** `opencv-python>=4.8` says what you need. `==` says what everyone else must have too.
- **Test with what you claim.** A floor you never tried is a guess.

Try it here. This is a small model of one idea, on a made-up install.

{{play:f_pins}}

Before anyone installs a pack on a machine they care about, there is a safe check. pip's `--dry-run` prints what would happen and installs nothing, and `-c` holds versions to a constraints file:

```
pip install --dry-run -c constraints.txt -r requirements.txt
```

Read the output. If it says `torch` or `numpy` would change, stop. Put that advice in your README. Better still, keep a virtual environment you can throw away for testing new packs.

## pyproject.toml

The Comfy Registry reads this file. The docs ask for at least a name and version, a repository URL, and a publisher id.

```toml
[project]
name = "my-pack"
version = "1.0.0"
description = "Edge tools."
license = { file = "LICENSE" }
dependencies = ["opencv-python>=4.8"]
requires-python = ">=3.10"

[project.urls]
Repository = "https://github.com/you/my-pack"

[tool.comfy]
PublisherId = "you"
DisplayName = "My Pack"
```

The docs' rules: a name under 100 characters, using letters, numbers, hyphens, underscores and periods, with no doubled special characters, and a three-part version.

## Ship a graph you can test

Put a small graph in `example_workflows`, and the server offers it as a template. The server also accepts `example`, `examples`, `workflow` and `workflows`, with a debug-level log line suggesting a rename. Any other folder name isn't served. If your pack can do anything with no model, ship a graph that runs in a second, like this one with your node swapped in. A user can then tell at once whether the install worked.

{{graph:nm_first}}

## And read before you run

The other side of all this: a pack is code that runs with your account's rights, at import. A `prestartup_script.py` in a pack runs before the rest of startup too. So read a pack before you run it, and write yours so others can read it. Here are made-up files to practise on.

{{play:risk}}

A build of ComfyUI can also refuse packs by policy: `app/governance.py` has a `pack_refusal` check that runs before a pack loads. In the v0.43.0 source it refuses nothing unless a policy has set a mode. We read that code, and did not run a build with a policy.

## What goes wrong

- **Other packs break after you install yours.** Something moved. Compare versions, and ask whether your exact pin is needed. Remember that uninstalling your pack doesn't put the old version back.
- **`IMPORT FAILED` beside your folder.** The traceback just above in the log says why, usually `No module named ...`.
- **Your node vanishes on one machine.** A name clash with another pack, or the listing order changed. Prefix your ids.
- **`Skip ... due to the lack of NODE_CLASS_MAPPINGS or comfy_entrypoint`.** Your `__init__.py` doesn't expose them. Re-export from `nodes.py`.
- **A 30 second start.** Your import loads something heavy. Move it into the function. The startup log prints import times per pack.
- **`from nodes import ...` picks up the wrong file.** Use relative imports in a pack: `from .nodes import MyNode`. A plain `nodes` means ComfyUI's own file.
- **Downloading at import, or installing with pip from your code.** Don't. It's surprising, it's slow, and it's the first thing a careful reader will flag.

## Lab

The first part is a teaching model of one idea, not pip's resolver. The rest ports the loader's rules from `nodes.py`.

```text
pins everything    would move: ['torch 2.6.0 (asked ==2.1.0)', 'numpy 1.26.4 (asked ==1.24.0)', 'pillow 10.4.0 (asked ==9.5.0)']
floors only        would move: nothing
only what is new   would move: nothing
```

Names, with two packs loading in turn:

```text
table: {'KSampler': 'core', 'Blur': 'pack_b'}
pack_a tried to replace core KSampler: ignored
```

A failed import costs one pack:

```text
pack_a loaded
pack_b IMPORT FAILED: ModuleNotFoundError: No module named 'cv2'
pack_c loaded
```

And which way of registering wins:

```text
both -> V1 table
v3 -> comfy_entrypoint
neither -> skipped: need one of them
```

## Sources

- [pyproject.toml, Comfy Registry docs](https://docs.comfy.org/registry/specifications)
- [pip install, pip docs](https://pip.pypa.io/en/stable/cli/pip_install/)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, requirements.txt](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/requirements.txt)
- [ComfyUI v0.43.0, app/custom_node_manager.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/app/custom_node_manager.py)
- [ComfyUI v0.43.0, app/governance.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/app/governance.py)
