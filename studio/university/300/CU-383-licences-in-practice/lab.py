# CU-383 lab: decide common cases from clauses we read in the licence texts. The clauses are short quotes. The table is our reading. Not legal advice.
CLAUSES = {
 "GPL-3.0 s0": "Mere interaction with a user through a computer network, with no transfer of a copy, is not conveying.",
 "AGPL-3.0 s13": "your modified version must prominently offer all users interacting with it remotely through a computer network ... an opportunity to receive the Corresponding Source",
 "MIT": "The above copyright notice and this permission notice shall be included in all copies or substantial portions",
 "OpenRAIL-M 5": "You cannot use the Model and the Derivatives of the Model for the specified restricted uses.",
}
for k, v in CLAUSES.items(): print(f"{k:14s} {v[:96]}")
def duty(lic, modified, gave_copy, served_remotely):
    """-> what the text asks in this case, in short."""
    out = []
    if lic in ("GPL-3.0", "AGPL-3.0"):
        if gave_copy: out.append("give source, keep licence" + (", mark changes" if modified else ""))
        if lic == "AGPL-3.0" and modified and served_remotely: out.append("offer source to remote users")
    if lic == "MIT" and gave_copy: out.append("keep notice")
    if lic == "OpenRAIL-M":
        out.append("no banned uses")
        if gave_copy or served_remotely: out.append("pass the use limits on")
    return "; ".join(out) or "nothing triggered"
CASES = [("use as is, at home", False, False, False), ("change it, at home", True, False, False), ("change it, give a friend a copy", True, True, False), ("change it, run a site for strangers", True, False, True), ("as is, run a site for strangers", False, False, True)]
for lic in ("MIT", "GPL-3.0", "AGPL-3.0", "OpenRAIL-M"):
    print(f"\n{lic}")
    for name, *c in CASES: print(f"  {name:38s} {duty(lic, *c)}")
assert duty("GPL-3.0", True, False, True) == "nothing triggered"
assert "offer source" in duty("AGPL-3.0", True, False, True)
assert duty("AGPL-3.0", False, False, True) == "nothing triggered"
assert duty("OpenRAIL-M", False, False, False) == "no banned uses"
print("\ncopying a piece of a pack into your own project, by the pack's licence")
for lic, r in (("MIT", "allowed, keep the notice"), ("Apache-2.0", "allowed, keep notices and state changes"), ("GPL-3.0", "your work that contains it, if you convey it, comes under GPL-3.0"), ("AGPL-3.0", "as GPL, plus the remote-users offer if modified"), ("no licence file", "no permission has been given: write your own")):
    print(f"  {lic:18s} {r}")
print("\nan idea or a published formula, written in your own code, is a different question from copying the code. Ask someone qualified if it matters.")
