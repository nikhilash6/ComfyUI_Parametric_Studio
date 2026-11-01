# CU-434 lab: a port of the list rules in execution.py (_async_map_node_over_list and merge_result_data), on made-up node functions. The results match a real run in the lesson.
import torch
def slice_dict(d, i): return {k: v[i if len(v) > i else -1] for k, v in d.items()}
def call(fn, data, input_is_list=False):
    if input_is_list: return [fn(**data)]
    n = max(len(x) for x in data.values())
    return [fn(**slice_dict(data, i)) for i in range(n)]
def merge(results, output_is_list):
    out = []
    for i, il in enumerate(output_is_list):
        if il: v = []; [v.extend(o[i]) for o in results]; out.append(v)
        else: out.append([o[i] for o in results])
    return out
LOG = []
def make(n): LOG.append(("make", n)); return (list(range(n)), "s")
def each(v, k, s): LOG.append(("each", v, k, s)); return (v * k,)
def whole(v, k): LOG.append(("whole", v, k)); return (sum(v),)
a = merge(call(make, {"n": [3]}), (True, False)); print("make(3) outputs:", a)
b = merge(call(each, {"v": a[0], "k": [10], "s": a[1]}), (False,)); print("each outputs:", b)
c = merge(call(whole, {"v": b[0], "k": [1]}, input_is_list=True), (False,)); print("whole outputs:", c)
for l in LOG: print("  call", l)
assert LOG == [("make", 3), ("each", 0, 10, "s"), ("each", 1, 10, "s"), ("each", 2, 10, "s"), ("whole", [0, 10, 20], [1])]
LOG.clear(); 
def pair(a, b): LOG.append((a, b)); return (a + b,)
call(pair, {"a": [1, 2, 3], "b": [1]}); print("\nlists of 3 and 1:", LOG); assert LOG == [(1, 1), (2, 1), (3, 1)]
LOG.clear(); call(pair, {"a": [1, 2, 3], "b": [10, 20]}); print("lists of 3 and 2:", LOG); assert LOG == [(1, 10), (2, 20), (3, 20)]
# OUTPUT_IS_LIST flag forgotten: the node returns a list, and the engine treats it as one item.
print("\nreturn a list with OUTPUT_IS_LIST:", merge([([1, 2, 3],)], (True,)), " 3 items")
print("return a list without the flag:   ", merge([([1, 2, 3],)], (False,)), " 1 item, which is a list")
assert len(merge([([1, 2, 3],)], (True,))[0]) == 3 and len(merge([([1, 2, 3],)], (False,))[0]) == 1
# A batch is one item. A list is many items.
batch = torch.zeros(4, 8, 8, 3); items = [torch.zeros(1, 8, 8, 3) for _ in range(4)]
print(f"\nbatch: 1 list item, shape {tuple(batch.shape)}: a node is called {len(call(lambda x: 0, {'x': [batch]}))} time")
print(f"list:  {len(items)} list items, each shape {tuple(items[0].shape)}: a node is called {len(call(lambda x: 0, {'x': items}))} times")
mixed = [torch.zeros(1, 8, 8, 3), torch.zeros(1, 16, 16, 3)]; print("a list may hold different sizes:", [tuple(x.shape) for x in mixed])
try: torch.cat(mixed)
except RuntimeError as e: print("a batch may not:", str(e).split(".")[0]); assert "Sizes of tensors must match" in str(e)
