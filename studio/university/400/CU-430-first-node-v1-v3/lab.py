# CU-430 lab: the same node written twice, on a small stand-in for the engine. It is an emulation, not ComfyUI: labs here can only import the standard library and torch.
# The stand-in follows comfy_api/latest/_io.py (get_v1_info) and execution.py (merge_result_data). The numbers it prints match a real run in the lesson.
import torch
from dataclasses import dataclass, field

# ---- a stand-in for the small part of comfy_api.latest.io this node uses
class io:
    @dataclass
    class FloatIn:
        id: str; default: float = 0.0; min: float = None; max: float = None; step: float = None
        def spec(self): return ("FLOAT", {k: getattr(self, k) for k in ("default", "min", "max", "step") if getattr(self, k) is not None})
    @dataclass
    class ImageIn:
        id: str
        def spec(self): return ("IMAGE", {})
    @dataclass
    class Schema:
        node_id: str; category: str; inputs: list = field(default_factory=list); outputs: list = field(default_factory=list)
    class NodeOutput:
        def __init__(self, *args): self.args = args

# ---- V1: a plain class. The engine reads these attributes.
class BrightenV1:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE", {}), "amount": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 4.0, "step": 0.01})}}
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = "university"
    def run(self, image, amount):
        return (torch.clamp(image * amount, 0, 1),)

# ---- V3: a schema and a classmethod.
class BrightenV3:
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="BrightenV3", category="university",
                         inputs=[io.ImageIn("image"), io.FloatIn("amount", default=1.0, min=0.0, max=4.0, step=0.01)], outputs=["IMAGE"])
    @classmethod
    def execute(cls, image, amount):
        return io.NodeOutput(torch.clamp(image * amount, 0, 1))
    @classmethod
    def INPUT_TYPES(cls):                       # the real base class makes this for you, in get_v1_info
        return {"required": {i.id: i.spec() for i in cls.define_schema().inputs}}

print("V1 inputs:", BrightenV1.INPUT_TYPES())
print("V3 inputs:", BrightenV3.INPUT_TYPES())
print("the same to the validator:", BrightenV1.INPUT_TYPES() == BrightenV3.INPUT_TYPES())
assert BrightenV1.INPUT_TYPES() == BrightenV3.INPUT_TYPES()

img = torch.full((1, 8, 8, 3), 0x20 / 255)
a = BrightenV1().run(img, 2.0)[0]; b = BrightenV3.execute(image=img, amount=2.0).args[0]
print(f"\ninput mean {img.mean():.4f}   V1 output {a.mean():.4f}   V3 output {b.mean():.4f}")
assert torch.equal(a, b)

# ---- a mistake only the engine shows: V1 must return a tuple. merge_result_data calls len(results[0]).
def merge_result_data(results):
    return [[o[i] for o in results] for i in range(len(results[0]))]
print("\nreturn (x,) ->", merge_result_data([(7,)]))
try:
    merge_result_data([7])
except TypeError as e:
    print("return x    -> TypeError:", e); msg = str(e)
assert msg == "object of type 'int' has no len()"

# ---- why you must not change an input in place. The cached output of the node upstream is the same object.
class Cache: pass
def three_queues(node):
    cached = torch.full((1, 4, 4, 3), 0x20 / 255); seen = []            # EmptyImage stays cached between queues
    for _ in range(3): seen.append(round(node(cached).mean().item(), 4))
    return seen
def in_place(image): image += 0.25; return image
def new_tensor(image): return image + 0.25
print("\nthree queues, only a later setting changes")
x = three_queues(in_place); y = three_queues(new_tensor)
print("image += 0.25      ", x)
print("image + 0.25       ", y)
assert x == [0.3755, 0.6255, 0.8755] and y == [0.3755, 0.3755, 0.3755]
