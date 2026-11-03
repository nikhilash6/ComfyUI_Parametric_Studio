"""Parametric Studio: Camera moves and looks preset library.
The 24 starter looks below stay as they were. look_library.json adds the grouped library behind the Create page's look picker: lighting, colour, framing, camera, motion and styles, one fragment per group."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Union
from psn.camera import camera_moves, one_move_problems
from studio import sfw

router = APIRouter()

# 8 Camera Presets
# Each phrase must classify as exactly [key] via camera_moves()
CAMERA = {
    "push_in": {
        "label": "Push In",
        "phrase": "slow dolly push in toward the subject",
        "blurb": "Gradually move closer to the subject for emphasis."
    },
    "pull_out": {
        "label": "Pull Out",
        "phrase": "smooth dolly pull out from the subject",
        "blurb": "Gradually move away from the subject to reveal context."
    },
    "pan": {
        "label": "Pan",
        "phrase": "steady horizontal pan across the scene",
        "blurb": "Rotate the camera horizontally to show a wider area."
    },
    "tilt": {
        "label": "Tilt",
        "phrase": "gentle vertical tilt up from the base",
        "blurb": "Rotate the camera vertically to reveal height or detail."
    },
    "orbit": {
        "label": "Orbit",
        "phrase": "smooth orbit around the central figure",
        "blurb": "Circle the subject to create a dynamic 360-degree view."
    },
    "track": {
        "label": "Track",
        "phrase": "tracking shot following the moving subject",
        "blurb": "Move the camera alongside the subject to maintain relative position."
    },
    "crane": {
        "label": "Crane",
        "phrase": "crane shot rising above the crowd",
        "blurb": "Vertical movement using a crane or jib for a sweeping view."
    },
    "handheld": {
        "label": "Handheld",
        "phrase": "handheld camera with natural subtle shake",
        "blurb": "Simulate the organic, slightly shaky feel of a hand-held camera."
    }
}

# 24 Look Presets
# Phrases must NOT contain camera move words (camera_moves(phrase) == [])
LOOKS = [
    {"id": "cinematic-4k", "label": "Cinematic 4K", "group": "cinematic", "phrase": "cinematic 4k, shallow depth of field, film grain", "blurb": "High-quality film look with realistic grain and focus."},
    {"id": "anamorphic", "label": "Anamorphic", "group": "cinematic", "phrase": "anamorphic lens flare, widescreen aspect ratio, teal and orange", "blurb": "Classic movie look with horizontal flares and color grading."},
    {"id": "noir", "label": "Film Noir", "group": "moody", "phrase": "black and white, high contrast, dramatic shadows", "blurb": "Moody, high-contrast monochrome style reminiscent of classic noir."},
    {"id": "neon-noir", "label": "Neon Noir", "group": "moody", "phrase": "neon lights, rain-slicked streets, cyberpunk atmosphere", "blurb": "Dark, futuristic city vibe with vibrant neon accents."},
    {"id": "watercolor", "label": "Watercolor", "group": "illustration", "phrase": "soft watercolor painting, pastel colors, textured paper", "blurb": "Gentle, artistic style with soft edges and paper texture."},
    {"id": "oil-painting", "label": "Oil Painting", "group": "illustration", "phrase": "thick oil paint strokes, canvas texture, classical style", "blurb": "Rich, textured look mimicking traditional oil paintings."},
    {"id": "pencil-sketch", "label": "Pencil Sketch", "group": "illustration", "phrase": "black and white pencil sketch, cross-hatching, rough lines", "blurb": "Monochrome drawing style with visible pencil strokes."},
    {"id": "comic-book", "label": "Comic Book", "group": "illustration", "phrase": "bold comic book style, halftone dots, vibrant colors", "blurb": "Punchy, graphic style with strong outlines and colors."},
    {"id": "pixel-art", "label": "Pixel Art", "group": "retro", "phrase": "8-bit pixel art, retro video game style, limited palette", "blurb": "Nostalgic, blocky aesthetic from early video games."},
    {"id": "vhs", "label": "VHS", "group": "retro", "phrase": "vhs tape aesthetic, tracking lines, 1990s color cast", "blurb": "Grainy, distorted look of old VHS recordings."},
    {"id": "polaroid", "label": "Polaroid", "group": "retro", "phrase": "instant photo, white border, faded colors, nostalgic", "blurb": "Casual, snapshot feel with a white frame and soft colors."},
    {"id": "sepia", "label": "Sepia", "group": "retro", "phrase": "sepia tone, vintage photograph, aged paper texture", "blurb": "Warm, brownish tint evoking old photographs."},
    {"id": "portrait", "label": "Portrait", "group": "photo", "phrase": "professional portrait, soft studio lighting, sharp focus", "blurb": "Clean, well-lit photography style ideal for people."},
    {"id": "landscape", "label": "Landscape", "group": "photo", "phrase": "wide angle landscape, natural lighting, high dynamic range", "blurb": "Vivid, detailed outdoor photography with balanced exposure."},
    {"id": "macro", "label": "Macro", "group": "photo", "phrase": "extreme close-up macro, intricate details, shallow focus", "blurb": "Very close photography highlighting fine textures and details."},
    {"id": "street", "label": "Street", "group": "photo", "phrase": "candid street photography, urban environment, natural light", "blurb": "Spontaneous, real-life urban moments captured naturally."},
    {"id": "documentary", "label": "Documentary", "group": "photo", "phrase": "documentary style, realistic, unposed, natural colors", "blurb": "Authentic, unglamorous look focusing on reality."},
    {"id": "fantasy", "label": "Fantasy", "group": "bright", "phrase": "fantasy art, magical lighting, ethereal glow, vibrant", "blurb": "Whimsical, otherworldly style with magical elements."},
    {"id": "scifi", "label": "Sci-Fi", "group": "bright", "phrase": "futuristic sci-fi, sleek technology, blue and white light", "blurb": "Clean, advanced technological aesthetic with cool tones."},
    {"id": "pastel", "label": "Pastel", "group": "bright", "phrase": "soft pastel colors, dreamy atmosphere, gentle lighting", "blurb": "Light, airy, and colorful with a soft focus."},
    {"id": "golden-hour", "label": "Golden Hour", "group": "bright", "phrase": "warm golden hour light, long shadows, soft glow", "blurb": "Warm, natural lighting typical of sunset or sunrise."},
    {"id": "high-key", "label": "High Key", "group": "bright", "phrase": "high key lighting, bright and airy, minimal shadows", "blurb": "Bright, evenly lit style with very few shadows."},
    {"id": "low-key", "label": "Low Key", "group": "moody", "phrase": "low key lighting, deep shadows, dramatic mood", "blurb": "Dark, moody style with strong contrast and shadows."},
    {"id": "vintage-film", "label": "Vintage Film", "group": "retro", "phrase": "vintage film look, light leaks, faded colors, grain", "blurb": "Aesthetic of old film cameras with light leaks and grain."}
]

LIBRARY = json.loads((Path(__file__).resolve().parent / "look_library.json").read_text(encoding="utf-8"))
LIB_BY_ID = {e["id"]: e for e in LIBRARY["looks"]}
GROUP_LABEL = {g["id"]: g["label"] for g in LIBRARY["groups"]}


def library():
    """The grouped look library, each group with its count, for the picker."""
    counts = {}
    for e in LIBRARY["looks"]: counts[e["group"]] = counts.get(e["group"], 0) + 1
    return {"about": LIBRARY["about"], "sections": LIBRARY["sections"], "groups": [{**g, "count": counts.get(g["id"], 0)} for g in LIBRARY["groups"]], "looks": LIBRARY["looks"], "total": len(LIBRARY["looks"])}


def pick_library(prompt, adds, kind="video", camera_taken=False):
    """Library fragments to add, in order: one per group (a later pick in the same group replaces an earlier one), video-only ones only on video,
    and at most one camera move, which also gives way to a move already in the prompt or a camera preset. -> (phrases, notes)."""
    notes, chosen = [], {}
    for lid in adds or []:
        e = LIB_BY_ID.get(lid)
        if not e: notes.append(f"Unknown look: {lid}"); continue
        if e["kind"] == "video" and kind != "video": notes.append(f"'{e['label']}' is for video only; skipped"); continue
        if e["group"] in chosen: notes.append(f"Only one {GROUP_LABEL[e['group']].lower()} at a time: '{e['label']}' replaces '{chosen[e['group']]['label']}'")
        chosen[e["group"]] = e
    out, move = [], None
    existing = camera_moves(prompt or "")
    for e in chosen.values():
        if e.get("move") and kind == "video":
            if existing: notes.append(f"Camera move already present in prompt ({', '.join(existing)}); skipping '{e['label']}'"); continue
            if camera_taken: notes.append(f"A camera preset is already set; skipping the camera move '{e['label']}'"); continue
            if move: notes.append(f"One camera move per clip: skipping '{e['label']}' because '{move['label']}' is set"); continue
            move = e
        if e["phrase"].lower() not in (prompt or "").lower(): out.append(e["phrase"])
    return out, notes


def apply(prompt, camera=None, look=None, kind='video', adds=None):
    """
    Appends look phrase, library fragments (adds) and (video only) camera phrase to the prompt.
    Returns str if no notes, or tuple (str, list[str]) if notes exist.
    """
    notes = []
    parts = [prompt.strip()] if prompt and prompt.strip() else []
    if look and look in LIB_BY_ID and not any(l['id'] == look for l in LOOKS):
        adds, look = [look] + list(adds or []), None
    lib_phrases, lib_notes = pick_library(prompt, adds, kind, camera_taken=bool(kind == 'video' and camera and camera in CAMERA))
    notes += lib_notes

    # Add look
    if look:
        look_obj = next((l for l in LOOKS if l['id'] == look), None)
        if look_obj:
            phrase = look_obj['phrase']
            # Check if already in prompt (simple substring check for phrase or key parts)
            # Spec says "avoiding duplicates". We check if the phrase is already present.
            if phrase.lower() not in prompt.lower():
                parts.append(phrase)
        else:
            notes.append(f"Unknown look: {look}")

    parts += lib_phrases

    # Add camera (video only)
    if kind == 'video' and camera:
        cam_obj = CAMERA.get(camera)
        if cam_obj:
            phrase = cam_obj['phrase']
            # Check if user's prompt already names a camera move
            existing_moves = camera_moves(prompt)
            if existing_moves:
                notes.append(f"Camera move already present in prompt ({', '.join(existing_moves)}); skipping preset '{camera}'")
            else:
                # Check if this specific phrase is already there
                if phrase.lower() not in prompt.lower():
                    parts.append(phrase)
        else:
            notes.append(f"Unknown camera: {camera}")

    # Collapse spaces
    final_text = " ".join(parts)
    final_text = " ".join(final_text.split())
    
    if notes:
        return final_text, notes
    return final_text

class ApplyRequest(BaseModel):
    prompt: str
    camera: Optional[str] = None
    look: Optional[str] = None
    kind: Optional[str] = 'video'
    adds: Optional[List[str]] = None

@router.get("/api/presets")
def get_presets():
    return {"camera": CAMERA, "looks": LOOKS}

@router.get("/api/presets/library")
def get_library():
    return library()

@router.post("/api/presets/apply")
def apply_presets(req: ApplyRequest):
    sfw.check(req.prompt)
    result = apply(req.prompt, req.camera, req.look, req.kind or 'video', (req.adds or [])[:40])
    if isinstance(result, tuple):
        text, notes = result
    else:
        text, notes = result, []
    return {"prompt": text, "notes": notes}
