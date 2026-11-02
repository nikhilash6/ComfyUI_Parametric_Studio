"""The picture check for a saved character's sheet. It is deliberately a blunt rule: a sheet passes only if it shows a readable face that reads as an adult, and nothing undressed. Whatever would be
sexual content involving a minor has to get past both halves, and a sheet that cannot be read, or a check that cannot run, does not pass. It runs on every sheet; without it no sheet passes and no character is built.

What runs: run_picturecheck.sh in the tool's folder (STUDIO_TOOL_PICTURECHECK), on the CPU: InsightFace buffalo_l for faces and apparent age, NudeNet 320n for exposed parts. An optional second opinion from a local vision model
(STUDIO_WORLDKIT_VISION_CHECK=1, an OpenAI-style server at STUDIO_WORLDKIT_VISION_URL) is off by default; when on, its failure or its doubt refuses.

What it does NOT do: it cannot tell a real person from an invented one. Apparent age is an estimate with an error of years and it is trained on photographs, so a young adult can be refused and a stylised, drawn or anime face, or a
youthful face the model reads as older, can pass. NudeNet sees exposed parts, not a pose, a suggestive framing or sheer clothes. It looks at the sheet only, not at the mesh or at any later frame. How often it catches what it should has
never been measured, by design: no such picture is ever made or sought to test it. Only its rate of refusing harmless pictures is measured."""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path

from psn import paths

VERSION = 1
MIN_AGE = 20.0                # as the earlier studio: a reading error of a couple of years must not let a teenager through
MIN_FACE_SCORE = 0.5
TIMEOUT_S = 300
TAG = "PICTURECHECK "
#: The class and the score from which it refuses. A sheet is asked for fully clothed, so even a bare chest or belly fails it.
REFUSE_AT = {"FEMALE_GENITALIA_EXPOSED": 0.2, "MALE_GENITALIA_EXPOSED": 0.2, "ANUS_EXPOSED": 0.2, "FEMALE_BREAST_EXPOSED": 0.2, "BUTTOCKS_EXPOSED": 0.25, "MALE_BREAST_EXPOSED": 0.4, "BELLY_EXPOSED": 0.5}
VISION_PROMPT = ("Look at this picture of a character. Answer with JSON only, no other words: {\"child_or_teen\": true or false, \"undressed_or_sexual\": true or false, \"real_famous_person\": true or false}. "
                 "If you are unsure of any answer, answer true.")


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(2 ** 20), b""):
            h.update(chunk)
    return h.hexdigest()


def judge(facts: dict) -> list[str]:
    """Why these facts do not pass; [] when they pass."""
    why = []
    faces = [f for f in facts.get("faces") or [] if float(f.get("score", 0)) >= MIN_FACE_SCORE]
    if not faces:
        why.append("no face it can read, so it cannot say the character is an adult")
    young = [f for f in faces if float(f.get("age", 0)) < MIN_AGE]
    if young:
        why.append(f"a face reads as under {MIN_AGE:.0f}")
    for d in facts.get("exposed") or []:
        at = REFUSE_AT.get(d.get("class"))
        if at is not None and float(d.get("score", 0)) >= at:
            why.append(f"{str(d['class']).replace('_', ' ').lower()}")
    return why


def _tool(path, *, run=None, home=None) -> dict:
    from studio.worldkit import capabilities as C
    runner = Path(home or C.tool_home("picturecheck")) / "run_picturecheck.sh"
    p = (run or subprocess.run)([str(runner), str(path)], capture_output=True, text=True, timeout=TIMEOUT_S)
    if p.returncode != 0:
        raise RuntimeError(f"the picture check exited {p.returncode}: {(p.stderr or '').strip()[-300:]}")
    lines = [ln for ln in (p.stdout or "").splitlines() if ln.startswith(TAG)]
    if len(lines) != 1:
        raise RuntimeError("the picture check gave no result")
    return json.loads(lines[0][len(TAG):])


def vision_on() -> bool:
    return paths.setting("STUDIO_WORLDKIT_VISION_CHECK") == "1"


def _vision(path, *, post=None) -> list[str]:
    """The second opinion, when it is on. No answer or an unclear answer refuses."""
    url, model = paths.setting("STUDIO_WORLDKIT_VISION_URL"), paths.setting("STUDIO_WORLDKIT_VISION_MODEL")
    if not url or not model:
        return ["the vision check is on, but STUDIO_WORLDKIT_VISION_URL or STUDIO_WORLDKIT_VISION_MODEL is not set"]
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    body = {"model": model, "temperature": 0, "max_tokens": 80, "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}, {"type": "text", "text": VISION_PROMPT}]}]}
    try:
        if post is None:
            import urllib.request
            req = urllib.request.Request(url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                reply = json.loads(r.read())
        else:
            reply = post(body)
        text = reply["choices"][0]["message"]["content"]
        got = json.loads(text[text.index("{"): text.rindex("}") + 1])
    except Exception as exc:          # fail closed
        return [f"the vision check could not answer ({type(exc).__name__})"]
    words = {"child_or_teen": "the vision check reads a child or teenager", "undressed_or_sexual": "the vision check reads it as undressed or sexual", "real_famous_person": "the vision check reads a real, famous person"}
    return [w for k, w in words.items() if got.get(k) is not False]


def check(path, *, run=None, home=None, post=None) -> dict:
    """{"ok", "why": [...], "sha256", "version", "facts", "vision"}. Any failure to run is ok: False."""
    rec = {"ok": False, "why": [], "sha256": "", "version": VERSION, "facts": {}, "vision": vision_on()}
    try:
        rec["sha256"] = sha256(path)
        rec["facts"] = {k: v for k, v in _tool(path, run=run, home=home).items() if k != "path"}
        rec["why"] = judge(rec["facts"])
        if vision_on():
            rec["why"] += _vision(path, post=post)
    except Exception as exc:
        rec["why"] = [f"the picture check could not run: {type(exc).__name__}: {exc}"[:400]]
    rec["ok"] = not rec["why"]
    return rec


def passed(record, path) -> bool:
    """A stored result counts only for this exact file, this version of the rule and a pass."""
    try:
        return bool(isinstance(record, dict) and record.get("ok") and record.get("version") == VERSION and record.get("sha256") == sha256(path))
    except OSError:
        return False
