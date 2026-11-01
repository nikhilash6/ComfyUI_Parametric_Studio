# CU-431 - Node inputs: widgets, optional, hidden, force_input

**Objective.** Pick the right kind of input for each job, and know which promises the server really keeps. Taught by Captain Graph.

## The idea

An input is either a value typed into the node or a wire from another node. The same input can usually be either. What you declare in the schema does two jobs: it tells the editor what to draw, and it tells the server what to check. The server checks much less than you might guess, and that matters as soon as anyone calls your node from the API.

## The kinds of input

| You want | V3 | V1 |
|---|---|---|
| A number, text, switch or menu | `io.Int.Input`, `io.Float.Input`, `io.String.Input`, `io.Boolean.Input`, `io.Combo.Input` | `("INT", {...})`, `("FLOAT", {...})`, `("STRING", {...})`, `("BOOLEAN", {...})`, `(["a", "b"], {})` |
| A wire of data | `io.Image.Input`, `io.Latent.Input`, `io.Model.Input` and so on | `("IMAGE",)`, `("LATENT",)`, `("MODEL",)` |
| Allowed to be absent | `optional=True` | inside `"optional"`, not `"required"` |
| A socket, not a widget | `force_input=True` | `{"forceInput": True}` |
| Evaluate only if asked | `lazy=True` (CU-432) | `{"lazy": True}` |
| Engine facts, not user data | `hidden=[io.Hidden.unique_id]`, read `cls.hidden.unique_id` | `"hidden": {"uid": "UNIQUE_ID"}`, an argument `uid` |

A wire in the API format is a list of two: a node id and an output slot. This graph feeds `width` with a wire, and types `height` by hand. Both are the same kind of input.

{{graph:f_widget_wire}}

## What the server does to a value

Before anything runs, `validate_inputs` converts each constant, then checks its range. It uses Python's `int`, `float`, `str` and `bool`, and those are more forgiving than you may want. We sent these through the real `validate_prompt` and read what the node received.

- **3.7 for an INT becomes 3.** It truncates, and no error appears.
- **The string "3.7" for an INT fails**, with `invalid_input_type`. `int("3.7")` raises.
- **The string "false" for a BOOLEAN becomes True.** Any non-empty string is true in Python.
- **None for a STRING becomes the text "None".**
- **The string "nan" for a FLOAT passes a range of 0 to 1.** Comparing NaN with anything gives false, so neither range check fires. Your node gets NaN.
- **`step` is not checked.** It is a hint to the editor. A value of 3 passed with `step=2`.
- **A list as a value is read as a wire.** A two-item list is a link, and any other length gives `bad_linked_input`. To pass a list as a value, wrap it: `{"__value__": [...]}`.

So if your node can be reached from the API, don't lean on the schema for safety. Check in `validate_inputs` (CU-433) or at the top of `execute`.

## Defaults belong to the editor

A `default` is what the editor puts in the widget when you add the node. The server doesn't fill it in. So:

- A **required** input missing from the prompt gives `required_input_missing`, default or not.
- An **optional** input missing from the prompt isn't passed at all. In our run, an optional input with schema default 3 reached the function as its Python default, `None`.

Always give optional inputs a default in the function signature. A signature with no default gives you a `TypeError` as soon as someone leaves the input out.

## force_input and friends

`force_input` means "draw a socket, not a widget". It is for values you expect from another node. The server doesn't enforce it: in our run, an API call with a plain constant worked fine.

`raw_link` is different. It asks the engine to hand you the wire itself, as `[node_id, slot]`, rather than the value. Node expansion uses it (CU-435).

## Hidden inputs

Hidden inputs never appear on the node. They are facts from the engine.

- `UNIQUE_ID`: this node's id. Asking for it **changes caching**: `include_unique_id_in_input` puts the id in the key, so two identical copies stop sharing one result.
- `PROMPT`: the whole graph as sent.
- `EXTRA_PNGINFO`: what is written into saved PNGs, including the workflow.
- `DYNPROMPT`: the live graph, which grows during node expansion.

In V3 you read them from `cls.hidden`, and any you didn't ask for are `None`. A V3 output node gets `prompt` and `extra_pnginfo` added automatically.

## Test yourself

Each of these came from a real run.

{{play:f_inputs}}

## What goes wrong

- **A switch that is always on in API calls.** A client sent the string "false". Send a JSON `false`, and check the type if strangers can call you.
- **`TypeError: missing 1 required positional argument`.** An optional input has no default in your function. Add `=None`.
- **A wire left unconnected on a required input.** `required_input_missing`, named in the message. Connect it or make it optional.
- **Two copies of your node suddenly run separately.** You added `UNIQUE_ID`. That is the side effect above.
- **A menu value that worked last week fails.** `value_not_in_list`. Menus are checked against what the schema returns today, and file menus change when files move. CU-294 covers that.
- **An extra value in your API graph did nothing.** Inputs your node doesn't declare are dropped without a word. Check the spelling. V3 can opt in with `accept_all_inputs=True`.

## Lab

The lab ports the conversion and range branch of `validate_inputs`. It isn't ComfyUI, but each row matches what the real function did in our run.

```text
type    you sent  the node receives
INT     3.7       3
INT     '3.7'     'invalid_input_type: Failed to convert an input value to a INT value'
FLOAT   'nan'     nan
BOOLEAN 'false'   True
STRING  None      'None'
```

Optional and required, left out of the prompt:

```text
optional o, schema default 3, left out of the prompt: {'s': 'hi', 'o': None}
required s, left out of the prompt:                 required_input_missing: s
```

And what the engine treats as a wire:

```text
['1', 0]                 wire? True
['a']                    wire? False
```

## Sources

- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_api/latest/_io.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_io.py)
- [ComfyUI v0.43.0, comfy/comfy_types/node_typing.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/comfy_types/node_typing.py)
- [ComfyUI v0.43.0, comfy_execution/graph_utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph_utils.py)
- [ComfyUI v0.43.0, comfy_execution/caching.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/caching.py)
