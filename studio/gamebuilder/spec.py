"""The game spec: what prompts become. A kit is chosen from five; everything else is checked data, so a model's answer can only ever fill in words, colours and a choice from a list.
deterministic() makes a whole spec from the prompt's words with no model at all and is labelled source="words". from_model() asks Qwen for the words when it is running, checks the answer, and falls back to deterministic() when it is not there or its answer is no good."""
from __future__ import annotations

import hashlib
import json
import re

from studio.worldkit import safety

SCHEMA = "gamebuilder-spec/1"
KITS = {
    "platformer": {"label": "3D platformer", "pitch": "Run, jump and stomp across floating islands, collect every star, reach the goal.", "words": ("platform", "platformer", "jump", "jumping", "collect", "collectathon", "stars", "coins", "hop", "islands")},
    "quest": {"label": "Exploration quest", "pitch": "Talk to a guide, roam a big landscape, bring back what was lost.", "words": ("quest", "explore", "exploration", "adventure", "open", "world", "relic", "relics", "journey", "wander", "treasure")},
    "arena": {"label": "Arena survival", "pitch": "Top-down: move, dash and hold out through waves of cartoon foes.", "words": ("arena", "survive", "survival", "waves", "wave", "horde", "swarm", "top-down", "topdown", "defend", "shooter", "bullet")},
    "kart": {"label": "Kart time trial", "pitch": "Three laps against the clock and a ghost. Drift, boost, take the medal.", "words": ("kart", "karts", "race", "racing", "racer", "drive", "driving", "car", "cars", "buggy", "vehicle", "lap", "laps", "track", "speed", "go-kart", "time trial", "rally")},
    "mystery": {"label": "Walking mystery", "pitch": "No foes and no clock: question people, find clues, name who did it.", "words": ("mystery", "detective", "clue", "clues", "whodunit", "whodunnit", "investigate", "investigation", "suspect", "suspects", "sleuth", "missing", "stolen", "inspector")},
}
SIZES = ("small", "medium", "large")
DIFFICULTIES = ("easy", "normal", "hard")
TIMES = ("day", "golden", "night")
WEATHERS = ("clear", "overcast", "rain", "snow", "fog")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
LIMITS = {"title": 40, "tagline": 90, "name": 40, "description": 220, "line": 220, "mood": 160}
#: Not ours to make: third-party characters and brands. The list is short on purpose: the plain, well-known ways of asking; a page can't know every name.
THIRD_PARTY = re.compile(r"\b(?:mario|luigi|bowser|zelda|link from|pikachu|pok[eé]mon|sonic the|kirby|minecraft|fortnite|roblox|disney|pixar|mickey mouse|elsa|batman|superman|spider-?man|marvel|harry potter|hogwarts|star wars|darth|lego|nintendo|playstation|xbox|ferrari|lamborghini|porsche|red bull|coca[- ]cola|barbie)\b", re.I)
HARSH = re.compile(r"\b(?:blood\w*|gore\w*|gory|torture\w*|dismember\w*|behead\w*|decapitat\w*|massacre\w*|murder\w*|corpse\w*|slaughter\w*|suicide|mutilat\w*|execution|school shooting|war crime\w*)\b", re.I)
THIRD_PARTY_MSG = "A game here uses invented characters only: no brands, no characters from other games or films. Please describe your own and try again."
HARSH_MSG = "A game here keeps to cartoon-level violence: foes turn to confetti, and a mystery is about something missing. Please reword it and try again."


#: A setting: what it looks like and what is in it. The first whose words are in the prompt is used.
THEMES = {
    "forest": {"word": "Mossy", "words": ("forest", "woods", "woodland", "grove", "jungle", "mushroom", "moss", "fairy"), "name": "the Mossy Wilds", "time": "day", "weather": "clear", "palette": {"sky": "#4f8fd0", "horizon": "#cfe6e0", "ground": "#5e8f3e", "accent": "#f5c518", "accent2": "#7a6a55", "danger": "#d65a3c"},
               "ground": "lush mossy forest floor with small clover", "rock": "grey mossy rock face", "road": "packed dirt trail", "props": ["a giant red-capped toadstool", "a gnarled old tree stump", "a mossy boulder"], "item": ("golden acorn", "golden acorns"), "foe": "a grumpy walking pinecone creature", "mood": "playful woodland adventure, plucked strings, flute, bright marimba", "bpm": 112, "hero": "a cheerful adult forest ranger in a green jacket and boots"},
    "desert": {"word": "Sunbaked", "words": ("desert", "dune", "dunes", "canyon", "sand", "oasis", "wasteland", "mesa"), "name": "the Sunbaked Mesa", "time": "golden", "weather": "clear", "palette": {"sky": "#5f9fd6", "horizon": "#f6d7a6", "ground": "#d0a062", "accent": "#f5c518", "accent2": "#a0653f", "danger": "#c93f2f"},
               "ground": "fine rippled desert sand", "rock": "layered red sandstone rock", "road": "cracked dusty hardpan road", "props": ["a tall saguaro cactus", "a wind-carved sandstone pillar", "a weathered wooden water tower"], "item": ("sun coin", "sun coins"), "foe": "a round grumpy cactus creature", "mood": "dusty western surf guitar, hand claps, upbeat", "bpm": 118, "hero": "an adult desert courier in a sand-coloured coat and goggles"},
    "ice": {"word": "Frostbound", "words": ("ice", "icy", "snow", "snowy", "frozen", "arctic", "glacier", "winter", "tundra", "alpine"), "name": "the Frostbound Peaks", "time": "day", "weather": "snow", "palette": {"sky": "#7fb2dc", "horizon": "#e8f2f8", "ground": "#dfeaf2", "accent": "#ffcf33", "accent2": "#7f97ad", "danger": "#6d4fc7"},
            "ground": "packed clean snow surface", "rock": "blue glacial ice and grey rock", "road": "compacted snow track with tyre grooves", "props": ["a snow-covered pine tree", "a jagged blue ice crystal", "a small wooden ski hut"], "item": ("frost gem", "frost gems"), "foe": "a round snowball creature with stubby arms", "mood": "sparkling winter adventure, glockenspiel, soft synth pads", "bpm": 104, "hero": "an adult mountain guide in a red parka and woollen hat"},
    "beach": {"word": "Saltwind", "words": ("beach", "island", "islands", "tropical", "coast", "harbour", "harbor", "seaside", "pirate", "lagoon", "ocean", "sea", "boardwalk"), "name": "Saltwind Cove", "time": "day", "weather": "clear", "palette": {"sky": "#3fa0e0", "horizon": "#d8f2f2", "ground": "#e3cf94", "accent": "#ffb627", "accent2": "#8a7458", "danger": "#e0523f"},
              "ground": "pale beach sand with small shells", "rock": "wet dark coastal rock", "road": "weathered wooden boardwalk planks", "props": ["a leaning palm tree", "a stack of old wooden barrels", "a small striped beach hut"], "item": ("sea pearl", "sea pearls"), "foe": "a sulking orange crab creature", "mood": "sunny steel drums and ukulele, breezy and bright", "bpm": 116, "hero": "an adult lifeguard in a yellow windbreaker and shorts"},
    "city": {"word": "Neon", "words": ("city", "downtown", "street", "neon", "urban", "cyberpunk", "alley", "rooftop", "rooftops", "metro"), "name": "Neon Row", "time": "night", "weather": "rain", "palette": {"sky": "#141a3a", "horizon": "#6a3a78", "ground": "#3a3d48", "accent": "#ffd21f", "accent2": "#5a5e70", "danger": "#ff3f7f"},
             "ground": "wet dark city pavement slabs", "rock": "dark brick wall with old paint", "road": "wet asphalt road surface", "props": ["a glowing vending machine with no text", "a stack of steel shipping crates", "an old iron street lamp"], "item": ("data shard", "data shards"), "foe": "a boxy little security robot on wheels", "mood": "driving synthwave, analog bass, neon night drive", "bpm": 124, "hero": "an adult bike courier in a yellow rain jacket"},
    "space": {"word": "Kepler", "words": ("space", "moon", "lunar", "mars", "planet", "alien", "asteroid", "galaxy", "starship", "orbit", "station"), "name": "Outpost Kepler", "time": "night", "weather": "clear", "palette": {"sky": "#0b0f2a", "horizon": "#3a4a8c", "ground": "#8a8794", "accent": "#7cf0ff", "accent2": "#55586a", "danger": "#ff5a3c"},
              "ground": "fine grey lunar dust with small craters", "rock": "dark basalt moon rock", "road": "smooth metal landing strip plates", "props": ["a small white habitat dome", "a crooked radio antenna mast", "a cluster of glowing teal crystals"], "item": ("power cell", "power cells"), "foe": "a floating round maintenance drone", "mood": "cosmic synth arpeggios, warm pads, gentle pulse", "bpm": 108, "hero": "an adult astronaut in a white and orange suit, helmet visor up"},
    "volcano": {"word": "Cinder", "words": ("volcano", "lava", "magma", "fire", "ember", "ash"), "name": "Cinder Isle", "time": "golden", "weather": "fog", "palette": {"sky": "#5a3b4a", "horizon": "#f09a4a", "ground": "#4a4040", "accent": "#ffd21f", "accent2": "#2f2a2c", "danger": "#ff6a1f"},
                "ground": "dark volcanic gravel and ash", "rock": "black basalt rock with glowing orange cracks", "road": "cracked dark volcanic stone road", "props": ["a smoking black basalt spire", "a charred dead tree", "a pile of glowing orange rocks"], "item": ("ember stone", "ember stones"), "foe": "a little walking lava rock creature with a sulky face", "mood": "heroic drums and brass, tense but fun", "bpm": 128, "hero": "an adult geologist in a heat-proof silver coat"},
    "candy": {"word": "Sugar", "words": ("candy", "sweet", "sweets", "dessert", "chocolate", "cake", "toy", "toys"), "name": "Sugar Hollow", "time": "day", "weather": "clear", "palette": {"sky": "#8fd0f0", "horizon": "#ffe6f2", "ground": "#f7a8c8", "accent": "#fff06a", "accent2": "#b5654a", "danger": "#7a3fd0"},
              "ground": "pink frosting with tiny sprinkles", "rock": "layered sponge cake and chocolate", "road": "smooth dark chocolate slab", "props": ["a giant swirl lollipop", "a stack of round macarons", "a gingerbread cottage"], "item": ("sugar star", "sugar stars"), "foe": "a wobbling jelly cube with a grumpy face", "mood": "bouncy toy piano and pizzicato strings, silly and sweet", "bpm": 126, "hero": "an adult pastry chef in a white jacket and tall hat"},
    "castle": {"word": "Greywater", "words": ("castle", "medieval", "kingdom", "knight", "dungeon", "fantasy", "ruins", "ruin", "temple", "manor", "mansion", "village", "town"), "name": "Greywater Keep", "time": "golden", "weather": "overcast", "palette": {"sky": "#6d86a8", "horizon": "#e6d4b8", "ground": "#6d8a4f", "accent": "#f5c518", "accent2": "#7d7468", "danger": "#a03f6a"},
               "ground": "short meadow grass with small stones", "rock": "old grey castle stonework", "road": "worn cobblestone road", "props": ["a crumbling stone archway", "a wooden market stall with no writing", "a small round stone well"], "item": ("lost rune", "lost runes"), "foe": "a clanking empty suit of cartoon armour", "mood": "folk fantasy, lute, hand drum, wooden flute", "bpm": 100, "hero": "an adult traveller in a long green cloak and leather boots"},
}
THEME_DEFAULT = "forest"
#: Words that set the hour and the weather, whatever the place: "a harbour at dusk" is a harbour at dusk.
TIME_WORDS = (("night", ("night", "midnight", "nighttime", "moonlit", "after dark")), ("golden", ("dusk", "sunset", "sundown", "twilight", "evening", "dawn", "sunrise", "golden hour")), ("day", ("noon", "midday", "morning", "afternoon", "daytime", "sunny")))
WEATHER_WORDS = (("rain", ("rain", "rainy", "storm", "stormy", "drizzle")), ("snow", ("snow", "snowy", "blizzard", "snowfall")), ("fog", ("fog", "foggy", "mist", "misty", "haze")), ("overcast", ("overcast", "cloudy", "grey", "gray", "gloomy")))
FIRST = ("Mara", "Tobin", "Ines", "Bram", "Odile", "Kester", "Nadia", "Ruben", "Sable", "Corin", "Tamsin", "Joss")
LAST = ("Voss", "Hale", "Corbel", "Okoye", "Marsh", "Teller", "Quill", "Brandt", "Farrow", "Lund", "Ashby", "Reyes")
ROLES = ("the gardener", "the clockmaker", "the cook", "the night porter", "the bookkeeper", "the painter", "the ferry pilot", "the archivist")
TRAITS = [("I've been repainting the shutters green all week. Ask anyone.", "Green paint", "A smear of fresh green paint on the latch of the empty case."),
          ("I oil every hinge in this place, that's my trade.", "Oily thumbprint", "A clean thumbprint in machine oil on the glass."),
          ("I keep the ledgers, so there's always ink on my cuffs.", "Ink blot", "A blot of blue-black ink on the sill, still tacky."),
          ("I carry flour on my sleeves from dawn till noon.", "Dusting of flour", "A dusting of white flour on the floor by the case.")]
#: The same words give the same game: the seed comes from them unless one is asked for.
TITLE_NOUNS = {"platformer": ("Leap", "Bound", "Hop", "Skyward"), "quest": ("Wayfarer", "Trail", "Lost Road", "Long Walk"), "arena": ("Last Stand", "Holdout", "Swarm", "Ring"), "kart": ("Grand Prix", "Rally", "Circuit", "Dash"), "mystery": ("Affair", "Case", "Puzzle", "Riddle")}


def seed_of(prompts) -> int:
    return int(hashlib.sha256("\n".join(prompts).encode()).hexdigest()[:8], 16) % 2**31


def clean(prompts) -> list[str]:
    if isinstance(prompts, str):
        prompts = [prompts]
    if not isinstance(prompts, list):
        return []
    return [" ".join(str(p).split())[:600] for p in prompts if str(p or "").strip()][:6]


def text_problems(*values) -> str:
    """"" or the plain sentence refusing these words."""
    bad = safety.text_problem(*values)
    if bad:
        return bad
    joined = " ".join(safety._texts(values))
    if THIRD_PARTY.search(joined):
        return THIRD_PARTY_MSG
    if HARSH.search(joined):
        return HARSH_MSG
    if safety.LIKENESS.search(joined):
        return "A game here uses invented characters only: this asks for the likeness of a real person. Please describe someone invented."
    return ""


def _hits(text: str, words) -> int:
    return sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", text))


def choose_kit(text: str) -> tuple[str, str]:
    """-> (kit, how it was chosen)."""
    scores = {k: _hits(text, v["words"]) for k, v in KITS.items()}
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "platformer", "no genre word in the prompts, so the platformer kit"
    return best, f"from the words in the prompts ({best}: {scores[best]})"


def choose_theme(text: str) -> str:
    scores = {k: _hits(text, v["words"]) for k, v in THEMES.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] else THEME_DEFAULT


_STOP = r"(?=$|[.,;:!?]|\s*\b(?:and|who|that|while|in|on|at|across|through|from|with|for|to|by|or|but|then|before|after|collecting|gathering|avoiding|dodging|fighting|racing|driving|exploring|searching|finding|hunting|chasing|solving)\b)"
_STOPWORDS = r"(?:and|who|that|while|in|on|at|across|through|from|with|for|to|by|or|but|then|before|after|around|over|into|along)\b"
NOUN = r"((?!" + _STOPWORDS + r")(?:[a-zA-Z][a-zA-Z'-]*\s?){1,5}?)"
VEHICLE_WORD = re.compile(r"\b(kart|go-kart|car|buggy|truck|bike|hover\w*|vehicle|sled|boat|wagon|racer|rover|scooter)\b", re.I)


def _find(pattern: str, text: str) -> str:
    m = re.search(pattern + _STOP, text, re.I)
    return " ".join(m.group(1).split()) if m else ""


def _article(phrase: str) -> str:
    p = phrase.strip()
    if re.match(r"^(a|an|the|some)\b", p, re.I):
        return p
    return ("an " if p[:1].lower() in "aeiou" else "a ") + p


def _plural(word: str) -> str:
    w = word.strip()
    if w.endswith("s"):
        return w
    if re.search(r"(ch|sh|x)$", w):
        return w + "es"
    if re.search(r"[^aeiou]y$", w):
        return w[:-1] + "ies"
    return w + "s"


def _singular(word: str) -> str:
    w = word.strip()
    if re.search(r"(ches|shes|xes)$", w):
        return w[:-2]
    if re.search(r"ies$", w):
        return w[:-3] + "y"
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def words_found(text: str) -> dict:
    """What a sentence names outright: 'play as a tired mail carrier', 'collect glowing pearls', 'avoid angry crabs', 'called Foo Bar'."""
    title = ""
    m = re.search(r"""(?:called|titled|named|title[:\s])\s*["“']([^"”']{2,40})["”']""", text, re.I) or re.search(r"\b(?i:called|titled)\s+((?:[A-Z][\w'-]*\s?){1,5})", text)
    if m:
        title = " ".join(m.group(1).split())
    return {"title": title,
            "hero": _find(r"\b(?:play(?:ing)? as|you are|you play|hero is|main character is|starring)\s+" + NOUN, text),
            "item": _find(r"\b(?:collect(?:ing)?|gather(?:ing)?|find(?:ing)?|grab(?:bing)?|recover(?:ing)?|retrieve)\s+(?:all\s+|the\s+|every\s+|some\s+|\d+\s+)*" + NOUN, text),
            "foe": _find(r"\b(?:avoid(?:ing)?|dodge|dodging|fight(?:ing)?|against|chased by|enemies are|foes are|hordes? of|waves? of|swarms? of|attacked by)\s+(?:the\s+|some\s+)*" + NOUN, text),
            "setting": _find(r"\b(?:set in|takes place in|located in|inside|on the|in the|in an?|on an?)\s+" + NOUN, text),
            "vehicle": _vehicle(text)}


def _vehicle(text: str) -> str:
    """What the player drives: the first phrase after drive/race/ride that names a vehicle, or nothing."""
    for m in re.finditer(r"\b(?:drive|driving|drives|race|racing|ride|riding)\s+(?:an?\s+|the\s+|your\s+)?" + NOUN + _STOP, text, re.I):
        phrase = " ".join(m.group(1).split())
        if VEHICLE_WORD.search(phrase):
            return phrase


#: What things really measure, longest side in metres, so a tree towers and a crate doesn't.
REAL_SIZE = (("stump", 1.8), ("palm", 8.0), ("pine", 8.0), ("tree", 7.0), ("tower", 7.0), ("pillar", 6.0), ("spire", 7.0), ("mast", 6.0), ("antenna", 6.0), ("dome", 6.0), ("hut", 5.0), ("cottage", 5.0), ("arch", 5.5), ("toadstool", 3.2), ("mushroom", 3.0), ("cactus", 4.0), ("lollipop", 3.0), ("lamp", 4.0), ("stall", 3.5), ("boulder", 2.4), ("crystal", 2.4), ("machine", 2.2), ("well", 2.2), ("crate", 1.6), ("barrel", 1.3), ("macaron", 1.2), ("rock", 2.0))


def real_size(description: str, default: float = 2.5) -> float:
    low = str(description).lower()
    return next((v for w, v in REAL_SIZE if w in low), default)


def _pick(seq, seed: int, n: int = 1):
    return seq[seed % len(seq)] if n == 1 else [seq[(seed + i * 7) % len(seq)] for i in range(n)]


def deterministic(prompts, *, seed: int | None = None, kit: str | None = None, size: str = "medium", difficulty: str = "normal") -> dict:
    """A whole, valid spec from the words alone. No model: labelled source="words"."""
    prompts = clean(prompts)
    text = " ".join(prompts)
    low = text.lower()
    seed = seed_of(prompts) if seed is None else int(seed)
    chosen, why = (kit, "asked for") if kit in KITS else choose_kit(low)
    theme_id = choose_theme(low)
    th = THEMES[theme_id]
    f = words_found(text)
    item_word = _singular(f["item"].lower()) if f["item"] else th["item"][0]
    foe_word = f["foe"].lower() if f["foe"] else th["foe"]
    if f["foe"]:
        foe_word = _article(_singular(foe_word))
    setting_name = th["name"]
    if f["setting"] and len(f["setting"]) > 3:
        setting_name = "the " + f["setting"].removeprefix("the ").strip() if not f["setting"].lower().startswith("the ") else f["setting"]
    title = f["title"] or f"{th['word']} {_pick(TITLE_NOUNS[chosen], seed)}"
    hero_desc = f["hero"] or th["hero"]
    if f["hero"]:
        hero_desc = _article(hero_desc)
    if "adult" not in hero_desc:
        hero_desc = re.sub(r"^(a|an|the)\s+", "an adult ", hero_desc, count=1, flags=re.I) if re.match(r"^(a|an|the)\s", hero_desc, re.I) else "an adult " + hero_desc
    time = next((t for t, words in TIME_WORDS if any(re.search(rf"\b{w}\b", low) for w in words)), "golden" if chosen == "mystery" else th["time"])
    weather = next((w for w, words in WEATHER_WORDS if any(re.search(rf"\b{x}\b", low) for x in words)), "overcast" if chosen == "mystery" and th["weather"] == "clear" else th["weather"])
    names = [f"{_pick(FIRST, seed + i * 5)} {_pick(LAST, seed + i * 3 + 1)}" for i in range(4)]
    is_vehicle = chosen == "kart"
    vehicle = _article(f["vehicle"]) if f["vehicle"] else {"space": "a little white moon buggy with chunky wheels", "candy": "a round candy-coloured go-kart", "ice": "a stubby red snow kart", "city": "a low boxy electric kart with neon trim"}.get(theme_id, "a stubby go-kart with chunky wheels and a roll bar")
    spec = {
        "schema": SCHEMA, "kit": chosen, "source": "words", "kit_why": why, "theme": theme_id, "prompts": prompts, "seed": seed,
        "title": title[:LIMITS["title"]], "tagline": f"{KITS[chosen]['pitch']}"[:LIMITS["tagline"]],
        "setting": {"name": setting_name[:LIMITS["name"]], "description": (text[:200] or setting_name), "time": time, "weather": weather, "palette": dict(th["palette"]), "ground": th["ground"], "rock": th["rock"], "road": th["road"]},
        "player": {"name": "Rider" if is_vehicle else _pick(FIRST, seed + 2), "kind": "vehicle" if is_vehicle else "human", "description": vehicle if is_vehicle else hero_desc, "height_m": 1.8, "size_m": 3.0, "asset": ""},
        "enemies": [] if chosen in ("kart", "mystery") else [{"name": "Foe", "description": foe_word, "size_m": 1.3, "speed": 2.6, "asset": ""}],
        "items": [{"name": item_word.title(), "plural": _plural(item_word), "description": _article(item_word), "size_m": 0.9, "role": "goal", "asset": ""}],
        "props": [{"name": p.split(" ", 1)[-1][:LIMITS["name"]], "description": p, "size_m": real_size(p), "asset": ""} for p in th["props"]],
        "goals": {"text": "", "hearts": {"easy": 8, "normal": 5, "hard": 3}[difficulty if difficulty in DIFFICULTIES else "normal"]},
        "level": {"size": size if size in SIZES else "medium", "difficulty": difficulty if difficulty in DIFFICULTIES else "normal", "seed": seed},
        "music": {"mood": th["mood"], "bpm": th["bpm"], "key": "C major"},
        "story": _story(chosen, setting_name, item_word, names, seed),
    }
    if chosen == "mystery":
        spec["items"] = [{"name": c["name"], "plural": "clues", "description": _clue_object(c["name"]), "size_m": 0.8, "role": "clue", "asset": ""} for c in spec["story"]["clues"]]
    spec["goals"]["text"] = {"platformer": f"Collect every {item_word}, then reach the goal.", "quest": f"Find every {item_word} and bring them back.", "arena": "Hold out through every wave.", "kart": "Three laps. Beat the clock.", "mystery": "Find the clues and name who did it."}[chosen]
    return spec


def _clue_object(name: str) -> str:
    return {"Green paint": "an open tin of green paint with a brush", "Oily thumbprint": "a small brass oil can", "Ink blot": "an old glass bottle of ink", "Dusting of flour": "a small cloth sack of flour", "Ferry ticket": "a small wooden ticket box", "Lantern": "an old brass lantern", "Pocket watch": "an open brass pocket watch"}.get(name, "a small wooden box")


def _story(kit: str, setting: str, item: str, names: list, seed: int) -> dict:
    plural = _plural(item)
    if kit == "mystery":
        lost = _pick(("the harbour bell", "the founder's lantern", "the silver weather vane", "the old town map", "the clocktower key"), seed)
        trait_i = seed % len(TRAITS)
        culprit = seed % 3
        rows, others = [], [t for i, t in enumerate(TRAITS) if i != trait_i]
        roles = _pick(ROLES, seed, 3)
        for i in range(3):
            who = names[i]
            line = TRAITS[trait_i][0] if i == culprit else others[(i + seed) % len(others)][0]
            rows.append({"name": who, "role": roles[i], "description": f"an invented adult, {roles[i]}, in plain work clothes", "line": f"{line} I never touched {lost}.", "spot": [0, 0, 0], "height_m": 1.7, "asset": ""})
        a, b = [i for i in range(3) if i != culprit]
        return {"intro": [f"Someone has taken {lost} from {setting}.", "Nobody leaves until it's found. Three people were here. One of them is lying."],
                "lost": lost, "suspects": rows, "culprit": culprit,
                "clues": [{"name": TRAITS[trait_i][1], "text": TRAITS[trait_i][2] + " Whoever opened the case left that behind.", "spot": [0, 0, 0]},
                          {"name": "Ferry ticket", "text": f"A stamped ferry ticket with {names[a]}'s name on it. They were across the water all afternoon.", "spot": [0, 0, 0]},
                          {"name": "Lantern", "text": f"A signed lamp-room log: {names[b]} was up there until dark, with two witnesses.", "spot": [0, 0, 0]},
                          {"name": "Pocket watch", "text": "A pocket watch stopped at four o'clock, dropped when someone hurried out. So it happened at four.", "spot": [0, 0, 0]}],
                "confession": f"All right. I took {lost}. I only meant to borrow it, and then I couldn't put it back. It's safe.",
                "win": f"{lost.capitalize()} is back where it belongs. Case closed.", "lose": "The trail has gone cold. Someone in this place is smiling tonight."}
    if kit == "quest":
        guide = {"name": names[0], "description": "an invented adult village elder in a patched coat", "height_m": 1.7, "asset": "",
                 "lines": [f"You came. Good. The {plural} of {setting} have been scattered across the wilds.", "Each one lies under a beam of light. Their keepers are grumpy, but a good bonk turns them into confetti.", f"Bring every {item} back to me, and watch your hearts."]}
        return {"intro": [f"{setting.capitalize()} has lost its {plural}.", f"Find {guide['name']} in the middle of the valley."], "npcs": [guide], "turn_in": f"Every {item}. I knew you could. {setting.capitalize()} will sleep well tonight.", "win": f"The {plural} are home and {setting} is whole again.", "lose": "You wake back in the valley with a sore head. The wilds are still out there."}
    if kit == "arena":
        return {"intro": [f"They came out of nowhere and they won't stop coming.", f"Hold your ground in {setting} until the last wave breaks."], "win": f"The last of them turned to confetti. {setting.capitalize()} is quiet again.", "lose": "Too many, this time. Dust yourself off and go again."}
    if kit == "kart":
        return {"intro": [f"Welcome to the {setting.removeprefix('the ')} circuit.", "Three laps. One ghost. Whoever said slow and steady has never driven here."], "win": "Over the line and under the clock. Not bad at all.", "lose": "The clock beat you this time. Take the corners tighter."}
    return {"intro": [f"The {plural} of {setting} have floated off across the sky.", f"Hop the islands, stomp what grumbles at you, and gather every last {item}."], "win": f"Every {item} is safe. {setting.capitalize()} shines again.", "lose": "Out of hearts. The islands will wait for you."}


# ---------- checking
def _text(d: dict, key: str, limit: int, bad: list, where: str, required: bool = True) -> None:
    v = d.get(key)
    if not isinstance(v, str) or (required and not v.strip()):
        bad.append(f"{where}.{key} is required text")
        return
    d[key] = " ".join(v.split())[:limit]


def _num(d: dict, key: str, lo: float, hi: float, default: float) -> None:
    v = d.get(key, default)
    d[key] = default if isinstance(v, bool) or not isinstance(v, (int, float)) else max(lo, min(hi, float(v)))


def validate(spec) -> tuple[dict, list[str]]:
    """(the spec, cleaned and clamped; problems). A spec with problems is never built. Words go through the same refusals as prompts."""
    bad: list[str] = []
    if not isinstance(spec, dict):
        return {}, ["the spec is not an object"]
    s = json.loads(json.dumps(spec))
    if s.get("schema") != SCHEMA:
        bad.append(f"schema must be {SCHEMA}")
    if s.get("kit") not in KITS:
        bad.append(f"kit must be one of {', '.join(KITS)}")
    _text(s, "title", LIMITS["title"], bad, "spec")
    _text(s, "tagline", LIMITS["tagline"], bad, "spec", required=False)
    if not isinstance(s.get("seed"), int) or isinstance(s.get("seed"), bool):
        bad.append("seed is a whole number")
    st = s.get("setting")
    if not isinstance(st, dict):
        bad.append("setting is required")
        st = {}
    else:
        _text(st, "name", LIMITS["name"], bad, "setting")
        if st.get("time") not in TIMES:
            bad.append(f"setting.time is one of {', '.join(TIMES)}")
        if st.get("weather") not in WEATHERS:
            bad.append(f"setting.weather is one of {', '.join(WEATHERS)}")
        pal = st.get("palette")
        if not isinstance(pal, dict) or not pal or not all(isinstance(v, str) and HEX.match(v) for v in pal.values()):
            bad.append("setting.palette is colours like #f5c518")
    p = s.get("player")
    if not isinstance(p, dict):
        bad.append("player is required")
    else:
        _text(p, "name", LIMITS["name"], bad, "player")
        _text(p, "description", LIMITS["description"], bad, "player")
        _num(p, "height_m", 0.8, 2.4, 1.7)
        _num(p, "size_m", 1.5, 6.0, 3.0)
        if p.get("kind") == "human":
            why = safety.character_text_problem(p.get("name"), p.get("description")) or safety.likeness_problem(p.get("name"), p.get("description"))
            if why:
                bad.append(why)
    for key, cap in (("enemies", 4), ("items", 6), ("props", 6)):
        rows = s.get(key)
        if not isinstance(rows, list) or len(rows) > cap:
            bad.append(f"{key} is a list of up to {cap}")
            continue
        for i, r in enumerate(rows):
            if not isinstance(r, dict):
                bad.append(f"{key}[{i}] is an object")
                continue
            _text(r, "name", LIMITS["name"], bad, f"{key}[{i}]")
            _text(r, "description", LIMITS["description"], bad, f"{key}[{i}]")
            _num(r, "size_m", 0.2, 12.0, 1.0)
            if key == "enemies":
                _num(r, "speed", 0.5, 7.0, 2.6)
    if s.get("kit") in ("platformer", "quest", "arena") and not s.get("enemies"):
        bad.append("this kit needs at least one enemy")
    if s.get("kit") in ("platformer", "quest", "arena", "mystery") and not s.get("items"):
        bad.append("this kit needs at least one item")
    g = s.get("goals")
    if not isinstance(g, dict):
        bad.append("goals is required")
    else:
        _num(g, "hearts", 1, 9, 4)
        g["hearts"] = int(g["hearts"])
    lv = s.get("level")
    if not isinstance(lv, dict) or lv.get("size") not in SIZES or lv.get("difficulty") not in DIFFICULTIES:
        bad.append(f"level has size ({', '.join(SIZES)}) and difficulty ({', '.join(DIFFICULTIES)})")
    m = s.get("music")
    if not isinstance(m, dict):
        bad.append("music is required")
    else:
        _text(m, "mood", LIMITS["mood"], bad, "music")
        _num(m, "bpm", 60, 180, 110)
        m["bpm"] = int(m["bpm"])
    story = s.get("story")
    if not isinstance(story, dict) or not isinstance(story.get("intro"), list) or not story["intro"]:
        bad.append("story.intro is a list of lines")
    elif s.get("kit") == "mystery":
        sus, clues = story.get("suspects"), story.get("clues")
        if not isinstance(sus, list) or not 2 <= len(sus) <= 4 or not all(isinstance(x, dict) and x.get("name") and x.get("line") for x in sus):
            bad.append("story.suspects is 2 to 4 people, each with a name and a line")
        if not isinstance(clues, list) or not 2 <= len(clues) <= 6 or not all(isinstance(x, dict) and x.get("name") and x.get("text") for x in clues):
            bad.append("story.clues is 2 to 6 clues, each with a name and a text")
        c = story.get("culprit")
        if isinstance(sus, list) and (not isinstance(c, int) or isinstance(c, bool) or not 0 <= c < len(sus)):
            bad.append("story.culprit is the number of one of the suspects")
    elif s.get("kit") == "quest" and not (isinstance(story.get("npcs"), list) and story["npcs"] and isinstance(story["npcs"][0], dict) and story["npcs"][0].get("name")):
        bad.append("story.npcs needs a guide")
    # Everything a person or a model typed, wherever it is.
    words = {k: v for k, v in s.items() if k not in ("schema", "kit", "source", "kit_why", "theme", "seed")}
    refused = text_problems(words)
    if refused:
        bad.append(refused)
    for key in ("title", "tagline"):
        if isinstance(s.get(key), str) and re.search(r"[<>{}\[\]\\]", s[key]):
            bad.append(f"{key} has characters a title doesn't need")
    return s, bad


# ---------- the model's turn
QWEN_FIELDS = ("title", "tagline", "kit", "time", "weather", "palette", "ground", "rock", "road", "hero", "foe", "item", "item_plural", "props", "mood", "intro", "win", "lose", "setting_name")
QWEN_SYSTEM = ("You design small 3D video games from a person's prompts. You choose one kit from a fixed list and write the words for it. You never write code. All characters are invented adults, with no real people, brands or characters from other games or films. Violence stays cartoon-level: foes turn to confetti. "
               "Answer with one JSON object and nothing else, with exactly these keys: title (up to 40 letters, a real game title), tagline (up to 90), kit (one of: platformer, quest, arena, kart, mystery), setting_name (up to 40), time (day, golden or night), weather (clear, overcast, rain, snow or fog), "
               "palette (an object of #rrggbb colours: sky, horizon, ground, accent, accent2, danger), ground, rock, road (each a short description of a surface, for a seamless texture), hero (a short visual description of the player: an invented adult person; for the kart kit, the vehicle instead), foe (a short visual description of a cartoon creature or robot), "
               "item (singular name of what is collected, up to 3 words), item_plural, props (a list of exactly 3 short visual descriptions of objects that stand in this world), mood (a music style, instruments and feeling, up to 160 letters), intro (a list of 2 short story lines), win (one line), lose (one line). No text or logos in any description.")


def merge_model(base: dict, ans: dict) -> tuple[dict, list[str]]:
    """Put a model's words over the deterministic spec. Unknown keys are ignored; the level, seeds and structure are never the model's."""
    notes: list[str] = []
    s = json.loads(json.dumps(base))
    if ans.get("kit") in KITS and ans["kit"] != s["kit"]:
        chosen = ans["kit"]
        s = deterministic(s["prompts"], seed=s["seed"], kit=chosen, size=s["level"]["size"], difficulty=s["level"]["difficulty"])
    s["source"] = "qwen"
    s["kit_why"] = "chosen by Qwen from the five kits"
    for k in ("title", "tagline"):
        if isinstance(ans.get(k), str) and ans[k].strip():
            s[k] = ans[k]
    st = s["setting"]
    if isinstance(ans.get("setting_name"), str) and ans["setting_name"].strip():
        st["name"] = ans["setting_name"]
    if ans.get("time") in TIMES:
        st["time"] = ans["time"]
    if ans.get("weather") in WEATHERS:
        st["weather"] = ans["weather"]
    if isinstance(ans.get("palette"), dict):
        for k, v in ans["palette"].items():
            if k in st["palette"] and isinstance(v, str) and HEX.match(v):
                st["palette"][k] = v
    for k in ("ground", "rock", "road"):
        if isinstance(ans.get(k), str) and ans[k].strip():
            st[k] = ans[k][:LIMITS["description"]]
    if isinstance(ans.get("hero"), str) and ans["hero"].strip():
        s["player"]["description"] = ans["hero"]
    if s["enemies"] and isinstance(ans.get("foe"), str) and ans["foe"].strip():
        s["enemies"][0]["description"] = ans["foe"]
    if s["kit"] != "mystery" and s["items"] and isinstance(ans.get("item"), str) and ans["item"].strip():
        s["items"][0].update(name=ans["item"].title(), description=_article(ans["item"]), plural=str(ans.get("item_plural") or _plural(ans["item"])))
    if isinstance(ans.get("props"), list):
        rows = [p for p in ans["props"] if isinstance(p, str) and p.strip()][:3]
        if rows:
            s["props"] = [{"name": p[:LIMITS["name"]], "description": p, "size_m": real_size(p), "asset": ""} for p in rows]
    if isinstance(ans.get("mood"), str) and ans["mood"].strip():
        s["music"]["mood"] = ans["mood"]
    story = s["story"]
    if isinstance(ans.get("intro"), list) and all(isinstance(x, str) for x in ans["intro"]) and ans["intro"]:
        story["intro"] = [x[:LIMITS["line"]] for x in ans["intro"][:3]]
    for k in ("win", "lose"):
        if isinstance(ans.get(k), str) and ans[k].strip():
            story[k] = ans[k][:LIMITS["line"]]
    return s, notes


def parse_json(text: str):
    m = re.search(r"\{.*\}", str(text or ""), re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def from_model(prompts, ask, *, seed=None, kit=None, size="medium", difficulty="normal") -> tuple[dict, str]:
    """ask(system, user) -> the model's text, or raises when it isn't there. -> (a valid spec, a sentence saying what happened). Always gives back a spec that passes validate."""
    base = deterministic(prompts, seed=seed, kit=kit, size=size, difficulty=difficulty)
    try:
        ans = parse_json(ask(QWEN_SYSTEM, "\n".join(clean(prompts))))
    except Exception as exc:
        return base, f"Qwen isn't running ({type(exc).__name__}), so the spec comes from the prompt's own words."
    if not isinstance(ans, dict):
        return base, "Qwen's answer wasn't JSON, so the spec comes from the prompt's own words."
    merged, _ = merge_model(base, ans)
    if kit in KITS and merged["kit"] != kit:
        merged, _ = merge_model(deterministic(prompts, seed=seed, kit=kit, size=size, difficulty=difficulty), {**ans, "kit": kit})
    checked, bad = validate(merged)
    if bad:
        return base, "Qwen's answer failed the checks (" + "; ".join(bad)[:200] + "), so the spec comes from the prompt's own words."
    return checked, "Written by Qwen, checked field by field."
