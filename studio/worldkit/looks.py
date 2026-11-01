"""Look presets: Blender's sky and light rigs, with time of day and weather. A look is a preset plus optional time-of-day and weather overrides; resolve() gives the dict that
blender_scripts/_wk.apply_look reads. Worlds are Blender's bundled studio-light HDRIs (datafiles/studiolights/world:
city, courtyard, forest, interior, night, sunrise, sunset), so nothing is downloaded. The numbers are starting points,
chosen by eye rather than measured."""
from __future__ import annotations

import copy

TIMES = ("day", "golden", "night")
WEATHERS = ("clear", "overcast", "rain")
_DAY_SUN = {"elevation_deg": 55.0, "azimuth_deg": 135.0, "strength": 4.0, "colour": [1.0, 0.97, 0.92]}
_GOLDEN_SUN = {"elevation_deg": 8.0, "azimuth_deg": 250.0, "strength": 3.0, "colour": [1.0, 0.72, 0.45]}
_MOON = {"elevation_deg": 50.0, "azimuth_deg": 60.0, "strength": 0.5, "colour": [0.62, 0.72, 1.0]}
LOOKS: dict[str, dict] = {
    "day_clear": {"label": "Daylight, clear sky", "world": "courtyard", "sky_colour": [0.20, 0.42, 0.95], "world_strength": 1.0, "sun": _DAY_SUN,
                  "fog": 0.0, "wet": 0.0, "exposure": 0.0, "night": False, "time": "day", "weather": "clear"},
    "golden_hour": {"label": "Golden hour", "world": "sunset", "sky_colour": [0.95, 0.62, 0.38], "world_strength": 0.9, "sun": _GOLDEN_SUN, "fog": 0.0,
                    "wet": 0.0, "exposure": 0.0, "night": False, "time": "golden", "weather": "clear"},
    "overcast": {"label": "Overcast", "world": "city", "sky_colour": [0.55, 0.58, 0.62], "world_strength": 1.2, "sun": None, "fog": 0.0, "wet": 0.0,
                 "exposure": 0.3, "night": False, "time": "day", "weather": "overcast"},
    "rainy": {"label": "Rainy street", "world": "city", "sky_colour": [0.33, 0.36, 0.40], "world_strength": 0.8, "sun": None, "fog": 0.003, "wet": 0.8,
              "exposure": 0.2, "night": False, "time": "day", "weather": "rain"},
    "night_city": {"label": "Night, city lights", "world": "night", "sky_colour": [0.012, 0.018, 0.04], "world_strength": 1.5, "sun": None, "fog": 0.001,
                   "wet": 0.0, "exposure": 1.0, "night": True, "time": "night", "weather": "clear"},
    "interior_day": {"label": "Interior, daylight", "world": "interior", "world_strength": 1.0,
                     "sun": {**_DAY_SUN, "elevation_deg": 30.0, "strength": 2.0}, "fog": 0.0, "wet": 0.0,
                     "exposure": 0.2, "night": False, "time": "day", "weather": "clear"},
    "interior_night": {"label": "Interior, warm lamps", "world": "interior", "world_strength": 0.15, "sun": None,
                       "fog": 0.0, "wet": 0.0, "exposure": 0.5, "night": True, "time": "night", "weather": "clear"},
}
DEFAULT = "day_clear"


def problems(preset, time=None, weather=None) -> list[str]:
    bad = []
    if preset not in LOOKS:
        bad.append(f"look must be one of {', '.join(LOOKS)}")
    if time not in (None, "", *TIMES):
        bad.append(f"time of day must be one of {', '.join(TIMES)}")
    if weather not in (None, "", *WEATHERS):
        bad.append(f"weather must be one of {', '.join(WEATHERS)}")
    return bad


def resolve(preset: str = DEFAULT, time: str | None = None, weather: str | None = None) -> dict:
    bad = problems(preset, time, weather)
    if bad:
        raise ValueError("; ".join(bad))
    look = copy.deepcopy(LOOKS[preset])
    look["preset"] = preset
    inside = preset.startswith("interior")
    if time == "golden":
        look.update(world="interior" if inside else "sunset", sun=copy.deepcopy(_GOLDEN_SUN), night=False, time="golden")
    elif time == "night":
        look.update(world="interior" if inside else "night", world_strength=0.15 if inside else 1.5, sun=None,
                    exposure=1.0, night=True, time="night")
    elif time == "day":
        look.update(night=False, time="day")
        if look["sun"] is None and weather in (None, "", "clear") and look["weather"] == "clear":
            look["sun"] = copy.deepcopy(_DAY_SUN)
    if look["night"] and not inside:
        look["moon"] = copy.deepcopy(_MOON)
    if weather == "rain":
        look.update(fog=0.003, wet=0.8, sun=None, weather="rain")
    elif weather == "overcast":
        look.update(sun=None, world_strength=max(float(look["world_strength"]), 0.8), weather="overcast")
    elif weather == "clear":
        look.update(weather="clear")
    return look


def public() -> list[dict]:
    return [{"id": k, "label": v["label"], "time": v["time"], "weather": v["weather"]} for k, v in LOOKS.items()]
