# CU-100 lab: the nodes of the first graph, with the same formulas as nodes.py, and the rule that decides what runs.
import torch
torch.manual_seed(0)

def empty_image(width, height, batch_size=1, color=0):
    r = torch.full([batch_size, height, width, 1], ((color >> 16) & 0xFF) / 0xFF)
    g = torch.full([batch_size, height, width, 1], ((color >> 8) & 0xFF) / 0xFF)
    b = torch.full([batch_size, height, width, 1], (color & 0xFF) / 0xFF)
    return torch.cat((r, g, b), dim=-1)

def image_invert(image): return 1.0 - image

a = empty_image(4, 4, color=0xF5C518); b = image_invert(a)
fmt = lambda t: " ".join(f"{v:.4f}" for v in t[0, 0, 0].tolist())
print(f"EmptyImage 0xF5C518 -> shape {tuple(a.shape)}  values {fmt(a)}")
print(f"ImageInvert         -> values {fmt(b)}")
again = image_invert(empty_image(4, 4, color=0xF5C518))
print("run twice: same numbers:", bool(torch.equal(b, again)))
assert abs(a[0, 0, 0, 0].item() - 245 / 255) < 1e-6 and abs(b[0, 0, 0, 2].item() - (1 - 24 / 255)) < 1e-6

# The rule: start from output nodes and pull backwards along the wires.
graph = {"1": ("EmptyImage", []), "2": ("ImageBlur", ["1"]), "3": ("PreviewImage", ["2"]), "4": ("ImageInvert", ["1"])}
OUTPUTS = {"PreviewImage", "SaveImage"}
def will_run(g):
    todo = [k for k, (c, _) in g.items() if c in OUTPUTS]; seen = set()
    while todo:
        k = todo.pop()
        if k not in seen: seen.add(k); todo += g[k][1]
    return seen
ran = will_run(graph); idle = [graph[k][0] for k in graph if k not in ran]
print(f"\nnodes on the canvas: {len(graph)}   nodes that ran: {len(ran)}   left idle: {idle}")
assert len(ran) == 3 and idle == ["ImageInvert"]
none = {k: v for k, v in graph.items() if v[0] not in OUTPUTS}
assert will_run(none) == set()
print("without an output node: nothing runs, the server says prompt_no_outputs")
