# CU-516 lab: four separate questions hide inside the word open. A table of what you can do with what you were given.
# The licence facts below were read from the licence texts. The table logic is ours. Not legal advice.
HAVE = {  # what you get, per release style
    "closed API":                      {"code": 0, "weights": 0, "data_info": 0},
    "weights only, in a binary runner": {"code": 0, "weights": 1, "data_info": 0},
    "weights and code":                {"code": 1, "weights": 1, "data_info": 0},
    "weights, code and data details":  {"code": 1, "weights": 1, "data_info": 1},
}
CAN = {  # the question, and what it takes
    "run it on your own machine":      lambda h: h["weights"],
    "read how it works":               lambda h: h["code"],
    "fine-tune it, a LoRA for example": lambda h: h["code"] and h["weights"],
    "rebuild something equivalent":    lambda h: h["code"] and h["data_info"],
}
print(f"{'':36s}" + "  ".join(f"{k[:16]:16s}" for k in CAN))
tab = {}
for name, h in HAVE.items():
    row = [bool(f(h)) for f in CAN.values()]; tab[name] = row
    print(f"{name:36s}" + "  ".join(f"{'yes' if v else 'no':16s}" for v in row))
assert tab["weights and code"] == [True, True, True, False] and tab["closed API"] == [False] * 4
print("\nand separately, what the licence lets you do. Dates and rules from the texts we fetched")
LIC = [("GNU GPL 3", "29 June 2007", "source duty when you convey; remote use alone is not conveying"),
       ("GNU AGPL 3", "19 November 2007", "adds an offer of source to remote users of a modified version"),
       ("CreativeML Open RAIL-M", "August 22, 2022", "free use, with a list of banned uses that you must pass on"),
       ("MIT", "no version date", "keep the notice")]
for n, d, r in LIC: print(f"  {n:24s} {d:18s} {r}")
print("\none graph can carry several of these at once")
STACK = {"ComfyUI itself": "GPL 3", "a checkpoint": "CreativeML Open RAIL-M", "a LoRA from someone else": "its own terms: read them", "a node pack": "its own LICENSE file", "your pictures": "the Open RAIL-M says the licensor claims no rights in the output, with limits on use"}
for k, v in STACK.items(): print(f"  {k:26s} {v}")
assert len(set(STACK.values())) == len(STACK)
