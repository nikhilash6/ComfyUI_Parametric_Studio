# CU-436 - A front-end extension: WEB_DIRECTORY and registerExtension

**Objective.** Ship a JavaScript file with a pack, know how it reaches the page, and pick the right hook. Taught by Captain Graph.

## The idea

A pack can change the editor as well as the engine. It can add a button, draw on a node, or show a result when a node finishes. Python never runs this code. It tells the server where a folder of JavaScript is, and the page does the rest.

## The two parts

In your pack's `__init__.py`:

```python
WEB_DIRECTORY = "./js"
```

And in `js/brighten.js`:

```js
import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "university.brighten",        // must be unique
  async setup() {
    console.log("loaded");
  },
});
```

Restart the server, because the loader reads `WEB_DIRECTORY` at startup. Open the page and look at the browser console.

## What happens

1. At startup, `load_custom_node` turns `WEB_DIRECTORY` into a real path and stores it in `EXTENSION_WEB_DIRS`, under your pack's folder name.
2. The server adds a static route for it: `/extensions/<folder>/...`.
3. The page asks `/extensions` for a list. That route returns every `.js` file found under each folder, subfolders included.
4. The page imports each one as a module. Your file runs, and `registerExtension` adds your object to the list of extensions.
5. As the page starts, it calls the hooks on every extension.

Look at what this means for your files:

- **Every `.js` is loaded, wanted or not.** A helper library in that folder runs as a module too.
- **Other files are served, but nothing loads them.** A CSS file has to be added by your own code, using its URL.
- **The URL leaves out `js`.** `js/brighten.js` is at `/extensions/my_pack/brighten.js`.
- **A file outside the folder isn't served at all.**

## Imports depend on depth

`../../scripts/app.js` is relative to your file's URL. It works for a file directly in `js`. One subfolder down, you need one more `../`. The lab works this out.

## Which hook

The docs give this order when the page loads. Put them in order yourself.

{{play:f_hooks}}

Most extensions need only three:

- **`setup`** runs at the end of startup. Use it for something global, such as listening for an event from the server.
- **`beforeRegisterNodeDef(nodeType, nodeData, app)`** runs once per node type. Use it to change what every node of your class does.
- **`nodeCreated(node)`** runs for each new node on the canvas. `loadedGraphNode` runs for each node restored from a saved graph.

Here is the usual pattern. It runs code when your node finishes, using what the Python side sent as `ui`:

```js
app.registerExtension({
  name: "university.brighten",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "Brighten") return;
    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      onExecuted?.apply(this, arguments);       // keep what others added
      console.log(message);
    };
  },
});
```

And the Python side of that message, from a V3 node:

```python
return io.NodeOutput(result, ui={"text": ["hello"]})
```

## Test it on a small graph

Everything front-end can be tried without a model. Open this and add your node to it.

{{graph:nm_first}}

## What goes wrong

- **Nothing happens.** Check the list: open `/extensions` on your server and look for your file. If it isn't there, either the path in `WEB_DIRECTORY` is wrong or the pack failed to import. An import failure in Python stops the JavaScript too, because the line that sets `WEB_DIRECTORY` never takes effect.
- **A 404 in the console for `app.js`.** Your import has the wrong number of `../`. See the lab.
- **Another pack's button vanished.** You replaced a prototype function without calling the old one. Always chain, as above. The lab shows what the other extension loses.
- **`name` clashes.** Two extensions with one name is asking for trouble. Prefix yours with your pack's name.
- **Help files in the wrong place.** They have to be inside `WEB_DIRECTORY` to be served.
- **A `web` setting in `pyproject.toml` instead.** That registers the folder under your project name, not your folder name, so URLs built from the folder name break. `WEB_DIRECTORY` is the simple route.
- **Code taken from a guide about a newer API.** You may meet `@comfyorg/extension-api` and `defineNode`. When we checked on 2026-10-31, the front end on our test machine had no such API, and npm had no such package. Check before you build on it.

## Lab

The lab models the server's listing on an in-memory set of files. It doesn't serve anything or touch a browser.

```text
the page loads these as modules:
  /extensions/my_pack/brighten.js
  /extensions/my_pack/sub/more.js
served, but not loaded by itself: /extensions/my_pack/style.css
not served at all: None
```

Imports, resolved the way a browser does:

```text
/extensions/my_pack/brighten.js: ../../scripts/app.js -> /scripts/app.js
/extensions/my_pack/sub/more.js: ../../scripts/app.js -> /extensions/scripts/app.js
so a file in a subfolder needs: /scripts/app.js from ../../../scripts/app.js
```

And what chaining saves:

```text
both chain: ['first', 'second']
second does not chain: ['rude']
```

## Sources

- [Javascript Extensions, ComfyUI docs](https://docs.comfy.org/custom-nodes/js/javascript_overview)
- [Comfy Hooks, ComfyUI docs](https://docs.comfy.org/custom-nodes/js/javascript_hooks)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
