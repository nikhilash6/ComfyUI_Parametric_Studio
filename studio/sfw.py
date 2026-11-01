"""One safe-for-work check for what people type into Create, recipes, apps and schedules. The word list is the one schedules already used. Negative prompts are not checked: they name what to keep out."""
import re
from fastapi import HTTPException
BAD = re.compile(r"\b(nsfw|nude|naked|lingerie|porn|hentai|explicit|erotic|topless|fetish|onlyfans|sex\w*|gore|butt|fuck\w*|schoolgirl)\b", re.I)
MESSAGE = "This studio makes safe-for-work pictures, video and music only, and something in your text is outside that. Please reword it and try again."
def _texts(v):
    """Every string inside a value, however it is nested: the goal code stringifies lists and dicts later, so they have to be read here too."""
    if isinstance(v, str): yield v
    elif isinstance(v, dict):
        for k, x in v.items(): yield from _texts(k); yield from _texts(x)
    elif isinstance(v, (list, tuple, set)):
        for x in v: yield from _texts(x)
def flagged(*texts): return any(BAD.search(t) for t in _texts(texts))
def check(*texts):
    if flagged(*texts): raise HTTPException(400, MESSAGE)
