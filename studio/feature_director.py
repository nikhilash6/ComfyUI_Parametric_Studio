"""Live Director: talk to or type at Comfy Prime, and the Shot Board fills in as you speak.
The language model only proposes changes to the board, and every one is checked against the Shot Board's real jobs and cameras. When it is off, plain keyword rules still build the board, and the page says which of the two answered. Nothing here can start a render: there is no call to /prompt or /api/generate in this file, and the render button is on the Shot Board, behind your click."""
import json, re
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from studio import sfw

router = APIRouter(prefix="/api/director")
PAGE = {"tab": "director", "label": "Live Director", "title": ["Live Director", "Say the shoot. Watch the board fill.", "Talk or type to Comfy Prime and the Shot Board builds as you go. Nothing renders until you press the button yourself."], "module": "director.js", "export": "LiveDirector", "css": "director.css"}
TRANSFORMS = {"reshoot": "Reshoot", "orbit": "Orbit 360", "recast": "Recast", "water": "VFX: water", "plate": "VFX: clean plate", "night": "VFX: day to night", "transition": "Transition", "matte": "VFX: matte"}
CAMERAS = ["orbit_right", "orbit_left", "dolly_in", "dolly_out", "crane_up", "crane_down", "pan_left", "pan_right", "tilt_up", "tracking", "handheld"]
MAX_TEXT = 800; MAX_SCENE = 400
OFFLINE = "Comfy Prime's language model is not running, so plain keyword rules are building your board. They know the job and camera names, not your meaning."
SYSTEM = """You are Comfy Prime, helping someone plan a Shot Board by voice. Reply with ONE JSON object: {"say": str under 30 words, "ops": [...]}.
Allowed ops: {"op":"add","job": one of %s}  {"op":"remove","job": same list}  {"op":"camera","camera": one of %s}  {"op":"scene","text": str}  {"op":"clear"}
Jobs: reshoot is a new camera move on the same scene; orbit is a frozen-time turn; recast swaps in a character; water, night (day to night), plate (paint people out) and matte are VFX; transition bridges the clip into a second clip the person adds. "scene" describes the clip for the VFX jobs.
You cannot start a render, so never say one has started. Use only what the person asked for."""
KEYWORDS = [(r"\b(transition|bridge (the|two) (clips|shots))\b", "transition"), (r"\b(day to night|day-to-night|night ?time|at night|make it night|night)\b", "night"), (r"\b(water|flood|rain ?water)\b", "water"), (r"\b(clean plate|remove (the )?(people|person)|paint (them|people|everyone) out|empty (the )?(street|scene))\b", "plate"), (r"\b(matte|mask|cut ?out)\b", "matte"), (r"\b(recast|swap (the )?(actor|character|lead)|my character)\b", "recast"), (r"\b(orbit|frozen time|bullet time|360)\b", "orbit"), (r"\b(reshoot|new angle|another angle|different angle|camera move)\b", "reshoot")]
CAMERA_WORDS = [(r"\bdolly (in|forward)|push in\b", "dolly_in"), (r"\bdolly (out|back)|pull (out|back)\b", "dolly_out"), (r"\bcrane up\b", "crane_up"), (r"\bcrane down\b", "crane_down"), (r"\bpan (to the )?left\b", "pan_left"), (r"\bpan (to the )?right\b", "pan_right"), (r"\btilt up\b", "tilt_up"), (r"\btracking\b", "tracking"), (r"\bhand ?held\b", "handheld"), (r"\borbit (to the )?left\b", "orbit_left"), (r"\borbit (to the )?right\b", "orbit_right")]
NEGATE = re.compile(r"\b(no|not|without|remove|drop|skip|don'?t)\b[^,.;]*$")


def check_ops(raw) -> list:
    """Only the board's own jobs and cameras get through. Anything else, a render request above all, is dropped."""
    out = []
    for o in raw if isinstance(raw, list) else []:
        if not isinstance(o, dict): continue
        k = o.get("op")
        if k in ("add", "remove") and o.get("job") in TRANSFORMS: out.append({"op": k, "job": o["job"]})
        elif k == "camera" and o.get("camera") in CAMERAS: out.append({"op": k, "camera": o["camera"]})
        elif k == "scene" and isinstance(o.get("text"), str) and o["text"].strip() and not sfw.flagged(o["text"]): out.append({"op": k, "text": o["text"].strip()[:MAX_SCENE]})
        elif k == "clear": out.append({"op": k})
    return out[:12]


def by_keywords(text: str) -> list:
    """What plain words can say without a language model. A job named after no, skip or remove comes off."""
    t = text.lower(); ops = []
    for pat, job in KEYWORDS:
        for m in re.finditer(pat, t):
            ops.append({"op": "remove" if NEGATE.search(t[:m.start()]) else "add", "job": job}); break
    for pat, cam in CAMERA_WORDS:
        if re.search(pat, t): ops.append({"op": "camera", "camera": cam}); break
    if re.search(r"\b(start over|clear (the )?board|clear everything)\b", t): ops.append({"op": "clear"})
    m = re.search(r"\b(?:the scene is|scene:|it'?s a shot of|the clip (?:is|shows))\s+(.{3,300})", text, re.I)
    if m and not sfw.flagged(m.group(1)): ops.append({"op": "scene", "text": m.group(1).strip().rstrip(".")})
    return check_ops(ops)


def _say_keywords(ops) -> str:
    if not ops: return "I did not catch a job or a camera. Try: orbit, day to night, water, clean plate, matte, recast or reshoot."
    bits = [("added " if o["op"] == "add" else "took off ") + TRANSFORMS[o["job"]] for o in ops if o["op"] in ("add", "remove")] + [("camera " + o["camera"].replace("_", " ")) for o in ops if o["op"] == "camera"] + ["noted the scene" for o in ops if o["op"] == "scene"] + ["cleared the board" for o in ops if o["op"] == "clear"]
    said = ", ".join(bits); return said[0].upper() + said[1:] + "."


def _chat(messages):
    from studio import crew
    return crew.default_chat(messages)


def _available() -> bool:
    from studio import voice
    return voice.llm_state() == "awake"


def turn(text, history, chat=None, available=None) -> dict:
    """One thing said. -> {say, ops, by: 'model' or 'rules', offline}. Never a render."""
    avail = (available or _available)
    if avail():
        msgs = [{"role": "system", "content": SYSTEM % (json.dumps(list(TRANSFORMS)), json.dumps(CAMERAS))}] + [{"role": h["role"], "content": str(h.get("text"))[:400]} for h in (history or [])[-6:] if isinstance(h, dict) and h.get("role") in ("user", "assistant")] + [{"role": "user", "content": text}]
        try:
            raw = (chat or _chat)(msgs); m = re.search(r"\{.*\}", raw or "", re.S); obj = json.loads(m.group(0)) if m else None
            if isinstance(obj, dict): return {"say": str(obj.get("say") or "")[:300] or "Done.", "ops": check_ops(obj.get("ops")), "by": "model", "offline": False}
        except Exception: pass
    ops = by_keywords(text)
    return {"say": _say_keywords(ops), "ops": ops, "by": "rules", "offline": True, "offline_why": OFFLINE}


@router.get("/status")
def status():
    try: on = _available()
    except Exception: on = False
    return {"model": on, "why": "" if on else OFFLINE, "transforms": TRANSFORMS, "cameras": CAMERAS}


@router.post("/turn")
async def turn_route(req: Request):
    try: b = await req.json()
    except ValueError: raise HTTPException(400, "Send a JSON object.") from None
    text = b.get("text") if isinstance(b, dict) else None
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= MAX_TEXT: raise HTTPException(400, "Say something short.")
    sfw.check(text)
    return await run_in_threadpool(turn, text.strip(), b.get("history"))
