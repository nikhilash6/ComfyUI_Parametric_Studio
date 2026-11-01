# CU-221 - Caching: why changing the seed does not reload the model

**Objective.** Work out which nodes re-run after any edit, and choose a cache policy knowing what it trades. Taught by Captain Graph.

## The idea

Each node gets a key made from its class, its constant inputs and, recursively, the same data for all its ancestors. If a key was seen and its result is still held, the node doesn't run. The key depends on what would be computed, not on where the node sits on the canvas.

That is why changing the seed doesn't reload your model. The loader's key has no seed in it, so its result is still good. Predict it yourself:

{{play:cache}}

## The mechanism

`CacheKeySetInputSignature` in `comfy_execution/caching.py` builds the signature. For the node and each ancestor it records:

- the class type, and the value from `fingerprint_inputs` (V3) or `IS_CHANGED` (older nodes), held in `IsChangedCache`
- each input in sorted order: a constant as itself, a link as ("ANCESTOR", ancestor index, output slot)
- the node id too, but only for `NOT_IDEMPOTENT` nodes and nodes taking `UNIQUE_ID`

Since links are numbered by position in the ancestry, renaming every node changes nothing. And two identical ordinary nodes have the same key, so they share a result. We ran that: two copies ran once.

A new `float("NaN")` as a fingerprint means "always run", because NaN never equals itself. Take care, because `math.nan` doesn't do the same: it's one shared object, and in a real run it stayed cached. CU-433 has the full table. `to_hashable` also turns anything it can't hash into an `Unhashable` object, which never matches either. Note that `IsChangedCache` passes `execution_list=None`, so a fingerprint function sees constants and not linked values.

Results are cached per node, as each one finishes. So if a run fails halfway, the finished nodes are saved, and the next queue starts from where it stopped. You fix a bad VAE setting and don't wait for the sampler again.

## Choosing a policy

`main.py` chooses the policy, and `CacheSet` builds it:

| Flag | Class | Behaviour |
|---|---|---|
| none (default) | `RAMPressureCache` | Keeps results, evicting by age and size when free RAM runs low |
| `--cache-classic`, or `--high-ram`, which sets it | `HierarchicalCache` | Drops anything the current prompt doesn't use |
| `--cache-lru N` | `LRUCache` | Evicts the least recently used generations above N results |
| `--cache-none` | `NullCache` | Runs every node every time |

The trade is memory against time. `--cache-none` holds nothing, and it means every node runs every time, with your models loading again too. A long video chain can hold many large tensors, so the policy matters there.

## See it

This small graph needs no model. Queue it twice and watch the second run do nothing. Then change the colour on `EmptyImage` and everything re-runs. With a real model, the same thing means seconds or minutes:

{{graph:nm_first}}

{{graph:sd15_txt2img}}

Set the seed to fixed, and change only the seed by hand. `CLIPTextEncode` and the loader don't run. Change the prompt, and the encoder for that prompt runs, along with the sampler and all that follows it. The other encoder and the loader still don't.

## What goes wrong

- **A node with hidden state returns a stale result.** Reading a clock or a file with no fingerprint: the key can't see that state. See CU-433.
- **You replaced a file under the same name, and got the old result.** `CheckpointLoaderSimple` has no change hook. Restart, or clear the cache. `LoadImage` does hash its file, so it notices.
- **"Nothing happened" when you queued.** Nothing changed, so everything came from the cache. That's right. Change the seed if you want a new picture.
- **Everything re-runs each queue.** Something early has a new key each time: a random seed on `control_after_generate`, or a node whose fingerprint returns NaN. Find the first node that runs, using the `execution_cached` message or by watching the graph.
- **Everything re-runs when you switch between two graphs.** With `--cache-classic` a prompt drops what it doesn't use. The lab shows the count. The default keeps results until RAM runs low.
- **RAM climbs until something gives.** The default holds results in RAM until there's pressure. A machine with little RAM may prefer `--cache-classic` or a small `--cache-lru`.
- **A flag or a pack update changes nothing.** Flags and code aren't in the key, only the class name and inputs. Change an input, or restart so the cache is empty.
- **You changed a node's code, and its result is old.** The same reason. After a restart the cache is empty.

## Lab

```text
first run          ran: ['ckpt', 'pos', 'neg', 'lat', 'smp', 'dec', 'out']
same graph again   ran: []
seed changed       ran: ['smp', 'dec', 'out']
prompt changed     ran: ['pos', 'smp', 'dec', 'out']
all ids renamed    ran: []
```

The seed row is the title of this lesson: the sampler and all that follows it run again, and the loader doesn't.

```text
file unchanged     ran: []
file edited on disk ran: ['f', 'out']
same inputs, not_idempotent, two nodes: keys equal? False
same inputs, ordinary node, two nodes: keys equal? True
```

The last line is a real effect: two identical ordinary nodes share one result.

```text
policy         nodes run over A B A B   (7 per full run)
classic        16
lru 100        10
lru 4          16
none           28
```

Alternating between two prompts is where policy matters. Classic forgets the other prompt each time, and a large LRU remembers both. The lab's LRU counts single results, while the real one evicts by generation, so read this for the direction. RAM pressure, the default, isn't simulated, because its behaviour depends on free RAM on the machine.

## Sources

- [ComfyUI v0.43.0, comfy_execution/caching.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/caching.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
