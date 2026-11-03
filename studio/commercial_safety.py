"""The Commercials page's hard rules, in code: invented brands, products and people only; no real brands, logos, trademarks, celebrities, politicians or parties; pharma-style spots name an invented drug for an invented condition and claim nothing; adults only, clothed, nothing sexual, no alcohol or tobacco.
problems() turns text into plain sentences saying what is wrong; check() refuses with them. The same check runs on the brief, on the script built from a template, and on anything a language model rewrote, so a rewrite can't slip a real name in.
The names live in commercial_names.json: a reasonable list, plus a near-miss check on invented names (one letter off a real brand is still that brand)."""
import json, re, unicodedata
from functools import lru_cache
from pathlib import Path
from fastapi import HTTPException
from studio import sfw

DATA = Path(__file__).resolve().parent / "commercial_names.json"
#: Fields that are names the brief invents: these get the strict and near-miss checks.
NAME_FIELDS = ("brand", "product", "candidate")
CHILDREN = re.compile(r"\b(child|children|kids?|kiddos?|bab(y|ies)|toddlers?|infants?|newborns?|boys?|girls?|teens?|teenagers?|teenaged|tweens?|pre-?teens?|schoolboys?|schoolgirls?|minors?|juveniles?|youngsters?|underage|kindergarten|little ones?)\b", re.I)
CHILDREN_OK = re.compile(r"\bbaby (blue|pink|spinach|carrots?|steps?|grand)\b|\bkid gloves\b", re.I)
SEXUAL = re.compile(r"\b(sexy|seductive|seduc\w*|sensual|sultry|steamy|provocative|aroused|bikinis?|underwear|swimsuits?|swimwear|cleavage|shirtless|bare-?chested|topless|lingerie|nude|naked|undress\w*|strip(per|tease)\w*|bedroom eyes)\b", re.I)
ALCOHOL = re.compile(r"\b(beers?|lagers?|ales?|ipa|stouts|wines?|champagne|prosecco|vodka|whiske?y|bourbon|scotch|rum|gin|tequila|mezcal|brandy|cognac|liqueurs?|liquor|cocktails?|margaritas?|mojitos?|sangria|hard seltzer|booze|boozy|drunk|tipsy|hangover|alcohol|alcoholic|brewery|breweries|pub crawl|bar crawl|happy hour|shots of)\b", re.I)
ALCOHOL_OK = re.compile(r"\b(non-?alcoholic|alcohol-?free|no alcohol|zero alcohol|ginger ales?|root beers?)\b", re.I)
TOBACCO = re.compile(r"\b(cigarettes?|cigars?|cigarillos?|tobacco|vapes?|vaping|vaper|e-?cigs?|nicotine|smoking|smokers?|hookah|shisha|cannabis|marijuana|cocaine|heroin)\b", re.I)
CLAIMS = re.compile(r"\b(cures?|cured|curing|treats?|treatment|treated|heals?|healed|healing|prevents?|prevention|clinically|proven|fda|ema|mhra|approved|prescription|prescribed|doctor[- ]recommended|guaranteed|medically)\b", re.I)
MARKS = re.compile(r"[™®℠©]|\(tm\)|\(r\)", re.I)


def fold(text):
    """Lower case, accents and apostrophes gone (so McDonald's matches McDonalds): for matching only."""
    t = unicodedata.normalize("NFKD", str(text or "")); t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"['‘’]", "", t).lower()


def letters(text): return re.sub(r"[^a-z0-9]", "", fold(text))


def skeleton(word):
    """How a name sounds, roughly: c/k/q alike, ph is f, z is s, y is i, doubled letters once. Catches 'Koka-Kola' and 'Nykee'."""
    w = letters(word).replace("ph", "f").replace("ck", "c").replace("x", "cs")
    w = w.translate(str.maketrans("kqzy", "ccsi")); return re.sub(r"(.)\1+", r"\1", w)


def _phrase(name):
    """A name as a pattern over folded text: words may be split by a space, a hyphen, a dot or nothing, and a plural or possessive s is allowed."""
    words = [re.escape(w) for w in re.split(r"[\s\-.]+", fold(name).replace("&", " & ")) if w]
    return r"(?<![a-z0-9])" + r"[\s\-.]*".join(words) + r"s?(?![a-z0-9])"


@lru_cache(maxsize=1)
def names():
    d = json.loads(DATA.read_text(encoding="utf-8")); out = {}
    for kind in ("brands", "people", "politicians", "parties", "medicines"):
        multi = [n for n in d[kind] if len(re.split(r"[\s\-]+", n)) > 1 or kind in ("brands", "medicines")]
        single = [n for n in d[kind] if n not in multi]
        out[kind] = {"any_case": [(n, re.compile(_phrase(n))) for n in multi], "capital": [(n, re.compile(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?:'?s)?(?![A-Za-z0-9])")) for n in single]}
    out["ambiguous"] = [(n, re.compile(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?:'?s)?(?![A-Za-z0-9])")) for n in d["ambiguous"]]
    out["ambiguous_fold"] = {letters(n): n for n in d["ambiguous"]}
    out["strict_letters"] = {letters(n): n for n in d["brands"] + d["medicines"] if len(letters(n)) >= 4}
    out["medicine_letters"] = {letters(n) for n in d["medicines"]}
    out["conditions"] = [(c, re.compile(_phrase(c))) for c in d["conditions"]]
    return out


def _sentence_start(text, i):
    j = i - 1
    while j >= 0 and text[j] in " \t\"'([":
        j -= 1
    return j < 0 or text[j] in ".!?:\n"


def _dist(a, b, cap=3):
    """Levenshtein distance, stopping early past cap."""
    if abs(len(a) - len(b)) > cap: return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1): cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        if min(cur) > cap: return cap + 1
        prev = cur
    return prev[-1]


WHAT = {"brands": "a real brand or trademark", "people": "a real person", "politicians": "a real politician", "parties": "a real political party", "medicines": "a real medicine"}


def found(text):
    """Every real name in one piece of running text, as (name, what it is)."""
    n = names(); low = fold(text); hits = []
    for kind in WHAT:
        hits += [(name, WHAT[kind]) for name, rx in n[kind]["any_case"] if rx.search(low)]
        hits += [(name, WHAT[kind]) for name, rx in n[kind]["capital"] if rx.search(str(text))]
    for name, rx in n["ambiguous"]:
        for m in rx.finditer(str(text)):
            if not _sentence_start(str(text), m.start()): hits.append((name, "a real brand or trademark")); break
    return hits


def name_problem(value):
    """An invented name must not be, contain, or nearly spell a real brand or medicine. '' when it's fine."""
    n = names(); v = letters(value); vs = skeleton(value)
    if not v: return ""
    for word in re.split(r"[\s\-./&]+", str(value)):
        if letters(word) in n["ambiguous_fold"]: return f"“{word}” is also a real brand name. Invent a name that isn't one."
        w = letters(word)
        if len(w) >= 5:
            for real_l, real in n["strict_letters"].items():
                if len(real_l) >= 5 and w != real_l and (_dist(w, real_l) <= 1 or skeleton(w) == skeleton(real_l)): return f"\u201c{word}\u201d is too close to the real name {real}. Invent something further away."
    for real_l, real in n["strict_letters"].items():
        if v == real_l or vs == skeleton(real_l): return f"“{value}” is {('a real medicine' if real in json.loads(DATA.read_text(encoding='utf-8'))['medicines'] else 'a real brand')}. Invent a name instead."
        if len(real_l) >= 5 and real_l in v: return f"“{value}” contains the real name {real}. Invent a name instead."
        if len(v) >= 5 and len(real_l) >= 5 and min(_dist(v, real_l), _dist(vs, skeleton(real_l))) <= (2 if len(real_l) >= 8 else 1): return f"“{value}” is too close to the real name {real}. Invent something further away."
    return ""


def problems(texts, genre=None, name_fields=None):
    """texts: {label: text}. -> sentences saying what breaks the rules, or [] when it is all fine."""
    out = []; parody_pharma = bool(genre and genre.get("id") == "pharma")
    seen = set()
    def add(msg):
        if msg not in seen: seen.add(msg); out.append(msg)
    for label, text in (texts or {}).items():
        t = str(text or "")
        if not t.strip(): continue
        if sfw.flagged(t): add(f"{label}: {sfw.MESSAGE}")
        if MARKS.search(t): add(f"{label}: leave out trademark symbols. Every brand here is invented.")
        for name, what in found(t): add(f"{label}: “{name}” is {what}. Use invented names only.")
        if CHILDREN.search(CHILDREN_OK.sub("", t)): add(f"{label}: commercials here show adults only. Describe grown-ups, for example “a woman in her thirties”.")
        if SEXUAL.search(t): add(f"{label}: nothing sexual or revealing. Keep everyone fully clothed and the tone clean.")
        if ALCOHOL.search(ALCOHOL_OK.sub("", t)): add(f"{label}: no alcohol. The beer-style genre sells a soda instead.")
        if TOBACCO.search(t): add(f"{label}: no tobacco, vaping or drugs.")
        if parody_pharma:
            for cond, rx in names()["conditions"]:
                if rx.search(fold(t)): add(f"{label}: “{cond}” is a real medical condition. Pharma-style parodies only treat invented ones, like “Chronic Sock Mismatch”."); break
            m = CLAIMS.search(t)
            if m: add(f"{label}: “{m.group(0)}” sounds like a medical claim. Pharma-style parodies make no claims.")
    for key in (name_fields or ()):
        v = (texts or {}).get(key)
        if v: (lambda p: p and add(f"{key}: {p}"))(name_problem(v))
    return out


def check(texts, genre=None, name_fields=None):
    bad = problems(texts, genre, name_fields)
    if bad: raise HTTPException(400, " ".join(bad[:6]))
