"""What World Kit refuses, and what it cannot see.

Text: every name, tag, brief, prompt, clip description and saved character description goes through studio/sfw.py, plus MINOR_RULE below: words for a
child together with words for undress or a body on show, which the studio-wide list does not catch on their own. A character description that names a child
at all is refused.

Pictures and meshes: a saved character's sheet goes through picturecheck.py (a readable adult face, nothing undressed); that file says what it does not catch. A picture a person adds for a prop, a generated prop picture and a finished
mesh are NOT checked by content. The character maker stays off (character_problem) until the founders decide otherwise: turning it on with STUDIO_WORLDKIT_CHARACTERS=1 is their decision, and this text says what it does not cover.

Characters come only from saved characters, made here from words, never an upload. Words that ask for a real person's likeness are refused, but nothing here can tell whether a finished sheet looks like a real person."""
from __future__ import annotations

import re

from psn import paths
from studio import sfw

CHILD = r"(?:child|children|childlike|kid|kids|minor|minors|underage|under-age|teen\w*|preteen\w*|schoolgirl\w*|schoolboy\w*|toddler\w*|infant\w*|baby|babies|loli\w*|shota\w*|boy|girl|\d{1,2}[- ]?(?:yo|y/o|years?[- ]old))"
ON_SHOW = r"(?:bikini\w*|swimsuit\w*|swimwear|underwear|undress\w*|panties|bra|lingerie|bare|shirtless|nudity|seductive\w*|sensual\w*|busty|cleavage|breasts?|provocative\w*|revealing)"
MINOR_RULE = re.compile(rf"\b{CHILD}\b.*\b{ON_SHOW}\b|\b{ON_SHOW}\b.*\b{CHILD}\b", re.I | re.S)
CHILD_WORD = re.compile(rf"\b{CHILD}\b", re.I)
LIKENESS = re.compile(r"\b(?:looks? like|look-?alike|resembl\w*|likeness|celebrit\w*|famous|real person|real people|actor|actress|politician|president|influencer|singer|footballer|portrait of|based on|my (?:wife|husband|girlfriend|boyfriend|friend|neighbou?r|ex|boss|colleague|daughter|son|sister|brother|mother|father))\b", re.I)
REFUSED = "World Kit makes safe-for-work assets only, and something in your text is outside that. Please reword it and try again."
CHARACTER_OFF = ("The character maker is off: this studio cannot yet check what a character mesh shows, only the words around it. "
                 "Places, props and looks work without it.")


def _texts(v):
    return list(sfw._texts(v))


def text_problem(*values) -> str:
    """"" or the refusal, for any nesting of strings."""
    texts = _texts(values)
    if sfw.flagged(*texts) or any(MINOR_RULE.search(t) for t in texts) or MINOR_RULE.search(" ".join(texts)):
        return REFUSED
    return ""


def character_text_problem(*values) -> str:
    """Stricter, for a saved character's own words: any word for a child refuses."""
    bad = text_problem(*values)
    if bad:
        return bad
    return "This saved character's description names a child, so it cannot become a 3D character." if any(CHILD_WORD.search(t) for t in _texts(values)) else ""


def likeness_problem(*values) -> str:
    """Words only, and only the plain ways of asking. A plain name cannot be told from an invented one."""
    return "A saved character must be invented: this description asks for the likeness of a real person." if any(LIKENESS.search(t) for t in _texts(values)) else ""


def characters_enabled() -> bool:
    return paths.setting("STUDIO_WORLDKIT_CHARACTERS") == "1"


def character_problem() -> str:
    return "" if characters_enabled() else CHARACTER_OFF
