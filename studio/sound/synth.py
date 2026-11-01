"""Procedural sound synthesis for the 🔊 Sound maker: ~80 named sounds built from oscillators, noise and envelopes in numpy
(studio/sound_dsp.py). No GPU, no model, no network, no sample: every sound is computed from parameters, so it is original, fully
reproducible from (kind, params, seed) and free of anybody's recording.

Each KIND has a family, a label, a one-line description, search tags (the words people type: "boom", "bonk", "womp", "whoosh"), its
own parameters with ranges, a length range, and a render function. `render()` resolves and clamps the parameters (anything unknown
is reported, never silently kept), adds a global `tone` slider (dark to bright), applies optional `variation` (seed-based jitter
of every parameter, which is what the A/B/C takes are) and returns the audio peak-normalised to -3 dBFS so chains see a
consistent level. The "in the spirit of" tags name a sound CATEGORY (a deep boom hit, a descending brass slide); nothing here copies a
recording and no preset is a specific track.

Proof level: wired + unit-tested for being finite, the right length, not silent and deterministic. Whether a sound is GOOD is
an ear question: see docs/processes/sound-maker.md "Listen list".
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from studio.sound import dsp as D
from studio.sound.dsp import SR

PRE_CHAIN_PEAK_DB = -3.0
MIN_S, MAX_S = 0.03, 30.0


class SynthError(ValueError):
    """Reported to the user as a message."""


@dataclass(frozen=True)
class P:
    """One parameter: default and range; `options` makes it a choice (value is the option's string); `integer` rounds."""
    default: float | str
    lo: float = 0.0
    hi: float = 1.0
    label: str = ""
    options: tuple = ()
    integer: bool = False
    unit: str = ""


@dataclass
class Kind:
    id: str
    family: str
    label: str
    desc: str
    params: dict
    seconds: tuple                # (min, max, default); min == max means the sound sets its own length
    fn: Callable
    tags: tuple = ()
    loop: bool = False            # steady / loopable by nature
    natural: bool = False         # the function decides the length (hook sketches, melodies); `seconds` is the default only


KINDS: dict[str, Kind] = {}
FAMILIES = {"impact": "Hits and impacts", "transition": "Risers, whooshes, transitions", "game": "Game and interface sounds",
            "cartoon": "Cartoon and comedy", "glitch": "Glitch and digital", "ambience": "Ambience and foley",
            "asmr": "Textures and ASMR-style", "music": "Notes, hooks and musical stings"}


def kind(id: str, family: str, label: str, desc: str, seconds: tuple, params: dict | None = None, tags: tuple = (), loop: bool = False,
         natural: bool = False):
    def deco(fn):
        KINDS[id] = Kind(id, family, label, desc, params or {}, seconds, fn, tags, loop, natural)
        return fn
    return deco


# --------------------------------------------------------------------------- helpers
def _t(n: int) -> np.ndarray:
    return np.arange(n) / SR


def hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)


_NOTE = re.compile(r"^([A-Ga-g])([#b]?)(-?\d)$")
_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_midi(tok: str) -> float | None:
    """'C5', 'F#3', 'Bb4' or a MIDI number -> MIDI note; None when it is not a note."""
    tok = tok.strip()
    if re.fullmatch(r"\d{2,3}", tok):
        return float(tok) if 12 <= float(tok) <= 127 else None
    m = _NOTE.match(tok)
    if not m:
        return None
    base = _SEMI[m.group(1).upper()] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return float(base + 12 * (int(m.group(3)) + 1))


def parse_notes(text: str, limit: int = 32) -> list[float]:
    out = []
    for tok in re.split(r"[\s,;]+", str(text or "").strip()):
        if not tok:
            continue
        if tok in ("-", "_", "r", "R"):
            out.append(float("nan"))                 # a rest
            continue
        m = note_midi(tok)
        if m is None:
            raise SynthError(f"{tok!r} is not a note (use C5, F#3, Bb4 or a MIDI number; '-' is a rest)")
        out.append(m)
    if not out:
        raise SynthError("write at least one note, e.g. C5 E5 G5 C6")
    return out[:limit]


def _hit(n: int, tau: float, attack: float = 0.0008) -> np.ndarray:
    e = D.exp_decay(n, tau)
    a = min(n, max(1, int(attack * SR)))
    e[:a] *= np.linspace(0, 1, a, endpoint=False)
    return e


def _pitch_drop(n: int, f_start: float, f_end: float, tau: float) -> np.ndarray:
    return f_end + (f_start - f_end) * np.exp(-_t(n) / tau)


def _place(out: np.ndarray, part: np.ndarray, at_s: float, gain: float = 1.0) -> None:
    a = int(at_s * SR)
    if a >= len(out):
        return
    e = min(len(out), a + len(part))
    out[a:e] += part[: e - a] * gain


def _bp(x, lo, hi, order=2):
    return D.bandpass(x, lo, min(hi, 0.45 * SR), order=order)


def _bell_partials(n: int, f0: float, ratios, tau: float, rng, spread: float = 0.0) -> np.ndarray:
    t = _t(n)
    y = np.zeros(n)
    for k, r in enumerate(ratios):
        f = f0 * r * (1 + spread * (rng.random() - 0.5))
        if f > 0.45 * SR:
            continue
        y += np.sin(2 * math.pi * f * t + rng.random() * 6.28) * np.exp(-t / (tau / (1 + 0.55 * k))) / (1 + 0.35 * k)
    return y


def _pitch_p(default: float = 0.0) -> P:
    return P(default, -12, 12, "pitch (semitones)", unit="st")


def _k(p: dict) -> float:
    return 2.0 ** (p.get("pitch", 0.0) / 12.0)


# =========================================================================== IMPACTS
@kind("boom", "impact", "Deep boom hit", "A deep sub drop with a thump: the cinematic / meme boom. Add reverb in the chain for a bigger room.",
      (0.6, 6.0, 1.8), {"pitch": _pitch_p(), "tail": P(0.6, 0.15, 1.5, "tail length (s)", unit="s"), "punch": P(0.6, 0, 1, "thump"),
                        "drive": P(0.5, 0, 1, "drive")}, tags=("boom", "vine boom", "sub drop", "impact", "bass hit", "cinematic hit", "thump"))
def _boom(p, n, rng):
    k, t = _k(p), _t(n)
    f = _pitch_drop(n, 125 * k, 36 * k, 0.085)
    body = np.sin(2 * math.pi * np.cumsum(f) / SR) * D.exp_decay(n, p["tail"])
    sub = np.sin(2 * math.pi * 36 * k * t) * D.exp_decay(n, p["tail"] * 1.4) * 0.5
    thump = D.lowpass(rng.standard_normal(n), 350 * k, order=3) * _hit(n, 0.045) * 2.0 * p["punch"]
    x = body + sub + thump
    return D.distort(x, 3 + 14 * p["drive"], "tanh") * 0.8


@kind("thud", "impact", "Dull thud", "A short low thud: a bag falling, a fist on a door.", (0.2, 2.0, 0.6),
      {"pitch": _pitch_p(), "body": P(0.5, 0, 1, "body"), "click": P(0.4, 0, 1, "click")}, tags=("thud", "thump", "punch", "bag"))
def _thud(p, n, rng):
    k = _k(p)
    f = _pitch_drop(n, 110 * k, 55 * k, 0.04)
    x = np.sin(2 * math.pi * np.cumsum(f) / SR) * _hit(n, 0.07 + 0.12 * p["body"])
    x += D.lowpass(rng.standard_normal(n), 900, order=2) * _hit(n, 0.02) * p["click"] * 1.5
    return x


@kind("slam", "impact", "Heavy slam", "A big metal-and-concrete slam: boom plus a bright rattle.", (0.5, 4.0, 1.4),
      {"pitch": _pitch_p(), "rattle": P(0.5, 0, 1, "rattle"), "tail": P(0.5, 0.2, 1.2, "tail (s)")}, tags=("slam", "door slam", "crash", "heavy hit"))
def _slam(p, n, rng):
    k = _k(p)
    x = _boom({"pitch": p["pitch"], "tail": p["tail"], "punch": 0.8, "drive": 0.7}, n, rng)
    rat = _bp(rng.standard_normal(n), 700 * k, 6000 * k) * _hit(n, 0.11 + 0.1 * p["rattle"]) * (0.5 + p["rattle"])
    return x + rat * 0.6


@kind("kick", "impact", "Kick drum (808)", "A round sine kick with a tuned tail.", (0.2, 2.0, 0.6),
      {"pitch": _pitch_p(), "decay": P(0.35, 0.1, 1.2, "decay (s)"), "click": P(0.4, 0, 1, "click")}, tags=("kick", "808", "bass drum"))
def _kick(p, n, rng):
    k = _k(p)
    f = _pitch_drop(n, 190 * k, 47 * k, 0.03)
    x = np.sin(2 * math.pi * np.cumsum(f) / SR) * _hit(n, p["decay"], 0.0005)
    x += D.highpass(rng.standard_normal(n), 3000) * _hit(n, 0.004) * p["click"] * 0.6
    return D.distort(x, 4, "tanh")


@kind("clap", "impact", "Hand clap", "Layered noise bursts: a studio clap.", (0.2, 2.0, 0.5),
      {"pitch": _pitch_p(), "bursts": P(4, 2, 6, "bursts", integer=True), "room": P(0.4, 0, 1, "room")}, tags=("clap", "hand clap", "applause hit"))
def _clap(p, n, rng):
    k = _k(p)
    x = np.zeros(n)
    for i in range(p["bursts"]):
        _place(x, _bp(rng.standard_normal(int(0.03 * SR)), 900 * k, 3200 * k) * _hit(int(0.03 * SR), 0.006), i * 0.011)
    tail = _bp(rng.standard_normal(n), 900 * k, 3000 * k) * _hit(n, 0.05 + 0.18 * p["room"])
    tail[: int(0.034 * SR)] = 0
    return x * 3 + tail * 1.2


@kind("snare", "impact", "Snare", "A tone plus a noise rattle.", (0.2, 2.0, 0.5),
      {"pitch": _pitch_p(), "snap": P(0.6, 0, 1, "snap"), "decay": P(0.16, 0.05, 0.6, "decay (s)")}, tags=("snare", "drum"))
def _snare(p, n, rng):
    k, t = _k(p), _t(n)
    tone = np.sin(2 * math.pi * 190 * k * t) * _hit(n, 0.07)
    nz = D.highpass(rng.standard_normal(n), 1800) * _hit(n, p["decay"]) * (0.4 + p["snap"])
    return tone * 0.8 + nz * 0.9


@kind("rim", "impact", "Rim click", "A dry wooden click.", (0.1, 1.0, 0.3), {"pitch": _pitch_p()}, tags=("rim", "click", "side stick", "wood"))
def _rim(p, n, rng):
    k, t = _k(p), _t(n)
    return np.sin(2 * math.pi * 1700 * k * t) * _hit(n, 0.012) + _bp(rng.standard_normal(n), 1500, 5000) * _hit(n, 0.006) * 0.6


@kind("snap", "impact", "Finger snap", "A crisp finger snap.", (0.1, 1.0, 0.3), {"pitch": _pitch_p()}, tags=("snap", "finger snap"))
def _snap(p, n, rng):
    k, t = _k(p), _t(n)
    return _bp(rng.standard_normal(n), 1500 * k, 5500 * k) * _hit(n, 0.02) + np.sin(2 * math.pi * 2300 * k * t) * _hit(n, 0.012) * 0.5


@kind("clang", "impact", "Metal clang", "Inharmonic partials: a pipe, a pan, a bell-less clang.", (0.3, 5.0, 1.6),
      {"pitch": _pitch_p(), "ring": P(0.8, 0.15, 3.0, "ring (s)"), "dent": P(0.4, 0, 1, "inharmonic")},
      tags=("clang", "metal", "pipe", "pan", "metal pipe", "bang"))
def _clang(p, n, rng):
    k = _k(p)
    ratios = [1.0, 2.76 - 0.2 * p["dent"], 5.40, 8.93, 11.34, 14.9]
    x = _bell_partials(n, 410 * k, ratios, p["ring"], rng, spread=0.02)
    x += _bp(rng.standard_normal(n), 2000, 9000) * _hit(n, 0.02) * 0.8
    return x


@kind("glass", "impact", "Glass ting", "A bright glassy ting.", (0.3, 4.0, 1.2), {"pitch": _pitch_p(), "ring": P(0.7, 0.1, 2.5, "ring (s)")},
      tags=("glass", "ting", "clink", "wine glass"))
def _glass(p, n, rng):
    return _bell_partials(n, 2200 * _k(p), [1.0, 2.32, 4.25, 6.63], p["ring"], rng, spread=0.01)


@kind("stab", "impact", "Brass stab", "A short detuned-saw chord stab (dramatic sting).", (0.3, 3.0, 0.9),
      {"pitch": _pitch_p(), "chord": P("minor", options=("minor", "major", "power", "tritone", "single")), "bright": P(0.6, 0, 1, "bright"),
       "hold": P(0.25, 0.05, 1.5, "hold (s)")}, tags=("stab", "sting", "brass", "orchestra hit", "dramatic", "dun dun"))
def _stab(p, n, rng):
    notes = {"minor": (0, 3, 7, 12), "major": (0, 4, 7, 12), "power": (0, 7, 12, 19), "tritone": (0, 6, 12, 18), "single": (0, 12, 24)}[p["chord"]]
    root = 48 + p["pitch"]
    x = np.zeros(n)
    for st in notes:
        for det in (-0.12, 0.0, 0.12):
            x += D.osc("saw", np.full(n, hz(root + st + det)))
    env = _hit(n, p["hold"], 0.006)
    fc = D.curve([(0, 600 + 5500 * p["bright"]), (0.12, 500 + 1500 * p["bright"]), (n / SR, 400)], n, log=True)
    return D.sweep_filter(x, fc, "lowpass", order=2) * env * 0.12


@kind("bonk", "impact", "Cartoon bonk", "A wooden / hollow bonk: a head hit in a cartoon.", (0.15, 1.5, 0.45),
      {"pitch": _pitch_p(), "hollow": P(0.5, 0, 1, "hollow"), "decay": P(0.1, 0.03, 0.4, "decay (s)")}, tags=("bonk", "boink", "wood block", "head hit", "bop", "cartoon hit"))
def _bonk(p, n, rng):
    k = _k(p)
    f = _pitch_drop(n, (560 + 120 * p["hollow"]) * k, 330 * k, 0.025)
    x = np.sin(2 * math.pi * np.cumsum(f) / SR) * _hit(n, p["decay"], 0.0003)
    x += np.sin(2 * math.pi * np.cumsum(f * 2.4) / SR) * _hit(n, p["decay"] * 0.4) * 0.35
    x += _bp(rng.standard_normal(n), 800, 4000) * _hit(n, 0.004) * 0.5
    return x


@kind("crash", "impact", "Cymbal crash", "Bright shimmering crash.", (0.5, 6.0, 2.2), {"pitch": _pitch_p(), "ring": P(1.2, 0.3, 3.0, "ring (s)")},
      tags=("crash", "cymbal", "tss"))
def _crash(p, n, rng):
    k, t = _k(p), _t(n)
    x = np.zeros(n)
    for f in (rng.uniform(300, 600, 14) * k * 7.3):
        x += D.osc("square", np.full(n, f)) * 0.05
    x += rng.standard_normal(n) * 0.5
    return D.highpass(x, 3500 * k) * _hit(n, p["ring"], 0.002)


@kind("rimshot", "impact", "Rimshot pattern", "Kick, snare and cymbal in a short comic 'ba-dum-tss' pattern.", (0.8, 4.0, 1.8),
      {"pitch": _pitch_p(), "gap": P(0.22, 0.1, 0.5, "gap between hits (s)")}, tags=("rimshot", "ba dum tss", "joke drums", "drum sting"))
def _rimshot(p, n, rng):
    out = np.zeros(n)
    g = p["gap"]
    _place(out, _kick({"pitch": p["pitch"], "decay": 0.3, "click": 0.4}, int(0.5 * SR), rng), 0.0, 1.0)
    _place(out, _snare({"pitch": p["pitch"], "snap": 0.7, "decay": 0.15}, int(0.5 * SR), rng), g, 0.9)
    _place(out, _crash({"pitch": p["pitch"], "ring": 0.9}, int(max(0.6, n / SR - 2 * g) * SR), rng), 2 * g + 0.04, 0.7)
    return out


@kind("stomp", "impact", "Stomp", "A heavy footfall: low thud with a gravel crack.", (0.2, 2.0, 0.6), {"pitch": _pitch_p(), "gravel": P(0.4, 0, 1, "gravel")},
      tags=("stomp", "footstep", "giant step"))
def _stomp(p, n, rng):
    x = _thud({"pitch": p["pitch"] - 3, "body": 0.7, "click": 0.3}, n, rng)
    x += _bp(rng.standard_normal(n), 1000, 5000) * _hit(n, 0.05) * p["gravel"] * 0.7
    return x


# =========================================================================== TRANSITIONS
@kind("riser", "transition", "Riser", "A rising noise-and-saw sweep that builds to a cut. End it on the cut.", (0.8, 12.0, 3.0),
      {"pitch": _pitch_p(), "noise": P(0.7, 0, 1, "noise"), "tone": P(0.5, 0, 1, "tonal saw"), "shape": P("exp", options=("exp", "linear"))},
      tags=("riser", "build up", "build-up", "sweep up", "tension rise", "uplifter"))
def _riser(p, n, rng):
    k = _k(p)
    dur = n / SR
    fc = D.curve([(0, 250), (dur, 14000)], n, log=True)
    nz = D.sweep_filter(D.noise("pink", n, rng), fc, "lowpass", order=2, res_db=4)
    amp = (np.linspace(0, 1, n) ** (2.2 if p["shape"] == "exp" else 1.0))
    saw = D.osc("saw", D.curve([(0, 110 * k), (dur, 880 * k)], n, log=True)) * 0.25
    saw = D.sweep_filter(saw, fc * 0.6, "lowpass")
    return (nz * p["noise"] + saw * p["tone"] * 1.5) * amp


@kind("downlifter", "transition", "Downlifter", "A falling sweep: the release after a drop.", (0.5, 8.0, 2.0), {"pitch": _pitch_p()},
      tags=("downlifter", "sweep down", "fall", "downsweep"))
def _downlifter(p, n, rng):
    return _riser({**p, "noise": 0.7, "tone": 0.4, "shape": "linear"}, n, rng)[::-1].copy()


@kind("whoosh", "transition", "Whoosh", "A filtered-noise swell that passes by: a cut, a swing, a swipe.", (0.2, 3.0, 0.8),
      {"pitch": _pitch_p(), "tone": P(0.5, 0, 1, "bright"), "swell": P(0.5, 0.1, 0.9, "peak position")}, tags=("whoosh", "swoosh", "swish", "transition", "swipe", "pass by"))
def _whoosh(p, n, rng):
    k, dur = _k(p), n / SR
    c = p["swell"]
    fc = D.curve([(0, 250 * k), (dur * c, (1200 + 3500 * p["tone"]) * k), (dur, 300 * k)], n, log=True)
    x = D.sweep_filter(D.noise("white", n, rng), fc, "lowpass", order=2, res_db=3)
    x = D.highpass(x, 120)
    return x * np.sin(np.pi * np.linspace(0, 1, n) ** (math.log(0.5) / math.log(c))) ** 1.4


@kind("reverse_hit", "transition", "Reverse crash", "A cymbal-and-boom played backwards: it sucks into the beat.", (0.5, 5.0, 1.8), {"pitch": _pitch_p()},
      tags=("reverse", "reverse crash", "reverse cymbal", "suck in"))
def _reverse_hit(p, n, rng):
    a = _crash({"pitch": p["pitch"], "ring": n / SR * 0.5}, n, rng)
    b = _boom({"pitch": p["pitch"], "tail": 0.3, "punch": 0.3, "drive": 0.2}, n, rng) * 0.3
    return (a + b)[::-1].copy() * np.linspace(0.4, 1.0, n)


@kind("drop", "transition", "Riser then drop", "A short riser, a breath of silence, then a big boom.", (1.5, 10.0, 3.5),
      {"pitch": _pitch_p(), "gap": P(0.12, 0.0, 0.5, "silence before the boom (s)")}, tags=("drop", "build and drop", "bass drop", "riser and boom"))
def _drop(p, n, rng):
    dur = n / SR
    boom_len = min(2.2, dur * 0.5)
    rise = max(0.4, dur - boom_len - p["gap"])
    out = np.zeros(n)
    _place(out, _riser({"pitch": p["pitch"], "noise": 0.8, "tone": 0.5, "shape": "exp"}, int(rise * SR), rng), 0.0, 0.7)
    _place(out, _boom({"pitch": p["pitch"], "tail": boom_len * 0.4, "punch": 0.9, "drive": 0.6}, int(boom_len * SR), rng), rise + p["gap"], 1.0)
    return out


@kind("laser_sweep", "transition", "Sci-fi sweep", "A long sine sweep with a wobble: a scanner or a portal.", (0.5, 6.0, 2.0),
      {"pitch": _pitch_p(), "up": P(1, 0, 1, "direction (1 up, 0 down)", integer=True), "wobble": P(0.4, 0, 1, "wobble")}, tags=("sweep", "scanner", "portal", "sci-fi"))
def _laser_sweep(p, n, rng):
    k, dur = _k(p), n / SR
    a, b = (200, 2400) if p["up"] else (2400, 200)
    f = D.curve([(0, a * k), (dur, b * k)], n, log=True) * (1 + 0.05 * p["wobble"] * np.sin(2 * math.pi * 7 * _t(n)))
    return D.osc("sine", f) * np.sin(np.pi * np.linspace(0, 1, n)) ** 0.7


# =========================================================================== GAME / UI
@kind("blip", "game", "Blip", "A short 8-bit blip.", (0.04, 1.0, 0.12),
      {"pitch": _pitch_p(), "note": P(81, 48, 100, "note (MIDI)", integer=True), "shape": P("square", options=("square", "tri", "sine", "saw")),
       "slide": P(0.0, -12, 12, "slide (semitones)", unit="st")}, tags=("blip", "beep", "8-bit", "bleep"))
def _blip(p, n, rng):
    f0 = hz(p["note"] + p["pitch"])
    f = D.curve([(0, f0), (n / SR, f0 * 2 ** (p["slide"] / 12))], n, log=True)
    return D.osc(p["shape"], f, width=0.5) * np.minimum(1.0, _hit(n, n / SR * 0.5)) * D.fade(np.ones(n), 0.002, 0.01) * 0.6


@kind("tick", "game", "UI tick", "A tiny interface click.", (0.03, 0.6, 0.12), {"pitch": _pitch_p()}, tags=("tick", "click", "ui click", "tap", "switch"))
def _tick(p, n, rng):
    k, t = _k(p), _t(n)
    return np.sin(2 * math.pi * 2600 * k * t) * _hit(n, 0.006) + _bp(rng.standard_normal(n), 2000, 8000) * _hit(n, 0.002) * 0.7


@kind("ping", "game", "Notification ping", "Two soft bell notes: a message-arrived sound.", (0.4, 3.0, 1.0),
      {"pitch": _pitch_p(), "interval": P(5, 1, 12, "interval (semitones)", integer=True), "gap": P(0.13, 0.05, 0.4, "gap (s)"), "ring": P(0.35, 0.1, 1.2, "ring (s)")},
      tags=("ping", "notification", "chime", "message", "ding", "alert tone", "ui ding"))
def _ping(p, n, rng):
    out = np.zeros(n)
    root = 88 + p["pitch"]
    for i, st in enumerate((0, p["interval"])):
        m = int(1.0 * SR)
        t = _t(m)
        f = hz(root + st)
        tone = (np.sin(2 * math.pi * f * t) + 0.3 * np.sin(2 * math.pi * f * 2.0 * t) * np.exp(-t / 0.08)) * _hit(m, p["ring"], 0.001)
        _place(out, tone, i * p["gap"], 0.7)
    return out


@kind("success", "game", "Success jingle", "A rising arpeggio: task done.", (0.5, 3.0, 1.0),
      {"pitch": _pitch_p(), "steps": P(4, 3, 6, "notes", integer=True), "speed": P(0.075, 0.04, 0.2, "note gap (s)")}, tags=("success", "complete", "level up", "arpeggio", "achievement"))
def _success(p, n, rng):
    out = np.zeros(n)
    steps = [0, 4, 7, 12, 16, 19][: p["steps"]]
    for i, st in enumerate(steps):
        m = n - int(i * p["speed"] * SR)
        if m <= 0:
            break
        f = hz(72 + p["pitch"] + st)
        t = _t(m)
        last = i == len(steps) - 1
        tone = (D.osc("tri", np.full(m, f)) + 0.4 * D.osc("sine", np.full(m, f * 2))) * _hit(m, 0.45 if last else 0.12, 0.002)
        _place(out, tone, i * p["speed"], 0.5)
    return out


@kind("error", "game", "Error buzz", "Two low buzzes: refused / wrong.", (0.3, 2.0, 0.55),
      {"pitch": _pitch_p(), "count": P(2, 1, 3, "buzzes", integer=True)}, tags=("error", "wrong", "denied", "refused", "fail buzz", "nope"))
def _error(p, n, rng):
    out = np.zeros(n)
    f = hz(55 + p["pitch"])
    for i in range(p["count"]):
        m = int(0.14 * SR)
        x = D.lowpass(D.osc("square", np.full(m, f)) + D.osc("saw", np.full(m, f * 1.01)), 1800) * D.fade(np.ones(m), 0.004, 0.02)
        _place(out, x, i * 0.18, 0.4)
    return out


@kind("coin", "game", "Coin pickup", "Two quick square notes with a ring: a collectible.", (0.2, 2.0, 0.6),
      {"pitch": _pitch_p(), "jump": P(5, 2, 12, "jump (semitones)", integer=True)}, tags=("coin", "pickup", "collect", "point", "score"))
def _coin(p, n, rng):
    out = np.zeros(n)
    a = hz(83 + p["pitch"])
    m1, m2 = int(0.07 * SR), n
    _place(out, D.osc("square", np.full(m1, a)) * D.fade(np.ones(m1), 0.001, 0.005), 0.0, 0.3)
    _place(out, D.osc("square", np.full(m2, a * 2 ** (p["jump"] / 12))) * _hit(m2, 0.22, 0.001), 0.07, 0.3)
    return out


@kind("power_up", "game", "Power-up", "A fast climbing arpeggio.", (0.3, 3.0, 0.8), {"pitch": _pitch_p(), "steps": P(8, 4, 14, "notes", integer=True)},
      tags=("power up", "power-up", "boost", "upgrade", "level up"))
def _power_up(p, n, rng):
    out = np.zeros(n)
    gap = min(0.07, 0.6 * n / SR / p["steps"])
    scale = (0, 4, 7, 12, 16, 19, 24, 28, 31, 36, 40, 43, 48, 52)
    for i in range(p["steps"]):
        m = int(max(gap * 1.6, 0.05) * SR)
        x = D.osc("square", np.full(m, hz(60 + p["pitch"] + scale[i] * 0.5))) * D.fade(np.ones(m), 0.001, 0.01)
        _place(out, x, i * gap, 0.25)
    out[int((p["steps"] * gap + 0.05) * SR):] *= 0.0
    return out


@kind("power_down", "game", "Power-down", "A falling slide: out of energy.", (0.3, 3.0, 0.9), {"pitch": _pitch_p()}, tags=("power down", "powerdown", "wind down", "die"))
def _power_down(p, n, rng):
    f = D.curve([(0, hz(84 + p["pitch"])), (n / SR, hz(48 + p["pitch"]))], n, log=True)
    return D.osc("square", f, width=0.35) * np.linspace(1, 0, n) ** 0.6 * 0.4


@kind("game_over", "game", "Game over", "Four falling notes with a wobbling last one.", (1.0, 5.0, 2.2), {"pitch": _pitch_p(), "tempo": P(0.28, 0.12, 0.6, "note length (s)")},
      tags=("game over", "lose", "defeat", "failure jingle"))
def _game_over(p, n, rng):
    out = np.zeros(n)
    seq = (67, 66, 65, 64)
    for i, m in enumerate(seq):
        ln = int((p["tempo"] if i < 3 else n / SR - 3 * p["tempo"]) * SR)
        f = np.full(ln, hz(m - 12 + p["pitch"]))
        if i == 3:
            f = f * (1 + 0.012 * np.sin(2 * math.pi * 6 * _t(ln)))
        x = D.osc("square", f, width=0.4) * _hit(ln, 0.3 if i < 3 else 0.9, 0.002)
        _place(out, x, i * p["tempo"], 0.3)
    return out


@kind("laser", "game", "Laser zap", "A falling saw sweep: pew.", (0.1, 2.0, 0.35),
      {"pitch": _pitch_p(), "drop": P(0.6, 0, 1, "drop"), "wobble": P(0.3, 0, 1, "wobble")}, tags=("laser", "pew", "zap", "blaster", "shot", "sci-fi gun"))
def _laser(p, n, rng):
    k, dur = _k(p), n / SR
    f = D.curve([(0, 3600 * k), (dur * 0.3, 1400 * k), (dur, (500 - 400 * p["drop"]) * k + 100)], n, log=True)
    f = f * (1 + 0.06 * p["wobble"] * np.sin(2 * math.pi * 55 * _t(n)))
    return D.osc("saw", f) * _hit(n, dur * 0.45, 0.001) * 0.6


@kind("zap", "game", "Electric zap", "A crackling electric zap with a ring-mod buzz.", (0.15, 2.0, 0.5), {"pitch": _pitch_p(), "crackle": P(0.6, 0, 1, "crackle")},
      tags=("zap", "electric", "shock", "spark", "static zap"))
def _zap(p, n, rng):
    k, t = _k(p), _t(n)
    f = 2600 * k * np.exp(-t / 0.08) + 180 * k
    x = D.osc("sine", f) * np.sin(2 * math.pi * 130 * t) * 0.8
    x += _bp(rng.standard_normal(n), 2500, 9000) * _hit(n, 0.12) * p["crackle"]
    return D.distort(x, 6, "hard") * _hit(n, n / SR * 0.5)


@kind("pop", "game", "Bubble pop", "A short rising 'blup'.", (0.05, 0.8, 0.18), {"pitch": _pitch_p()}, tags=("pop", "bubble", "blup", "plop", "notification pop"))
def _pop(p, n, rng):
    k = _k(p)
    f = D.curve([(0, 280 * k), (0.045, 900 * k), (n / SR, 700 * k)], n, log=True)
    return D.osc("sine", f) * _hit(n, 0.05, 0.001)


@kind("buzzer", "game", "Wrong-answer buzzer", "A harsh low buzz held for half a second.", (0.2, 3.0, 0.7), {"pitch": _pitch_p(), "grit": P(0.5, 0, 1, "grit")},
      tags=("buzzer", "wrong answer", "incorrect", "game show", "nope buzzer"))
def _buzzer(p, n, rng):
    f = hz(43 + p["pitch"])
    x = D.osc("square", np.full(n, f)) + 0.6 * D.osc("saw", np.full(n, f * 1.005)) + 0.3 * D.osc("square", np.full(n, f * 2))
    return D.distort(D.lowpass(x, 2400), 2 + 8 * p["grit"], "hard") * D.fade(np.ones(n), 0.004, 0.03) * 0.5


@kind("alarm", "game", "Alarm beeps", "Three sharp beeps.", (0.5, 4.0, 1.2), {"pitch": _pitch_p(), "beeps": P(3, 1, 8, "beeps", integer=True), "rate": P(0.28, 0.1, 0.6, "spacing (s)")},
      tags=("alarm", "beep beep", "warning", "alert"))
def _alarm(p, n, rng):
    out = np.zeros(n)
    for i in range(p["beeps"]):
        m = int(min(p["rate"] * 0.55, 0.3) * SR)
        _place(out, D.osc("square", np.full(m, hz(87 + p["pitch"]))) * D.fade(np.ones(m), 0.002, 0.005) * 0.3, i * p["rate"])
    return out


# =========================================================================== CARTOON / COMEDY
@kind("boing", "cartoon", "Boing", "A springy, wobbling tone.", (0.3, 3.0, 0.9),
      {"pitch": _pitch_p(), "wobble": P(0.6, 0, 1, "wobble"), "rate": P(9, 3, 18, "wobble rate (Hz)", unit="Hz"), "fall": P(0.45, 0.1, 1.0, "settle (s)")},
      tags=("boing", "spring", "sproing", "bounce", "jump"))
def _boing(p, n, rng):
    k, t = _k(p), _t(n)
    f = 330 * k * (1 + 1.1 * np.exp(-t / 0.05)) * (1 + 0.35 * p["wobble"] * np.exp(-t / p["fall"]) * np.sin(2 * math.pi * p["rate"] * t))
    x = np.sin(2 * math.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * math.pi * np.cumsum(f) / SR)
    return x * _hit(n, p["fall"] * 1.4, 0.002)


@kind("slide_whistle", "cartoon", "Slide whistle", "A whistle gliding up or down.", (0.3, 3.0, 1.0),
      {"pitch": _pitch_p(), "up": P(1, 0, 1, "direction (1 up, 0 down)", integer=True), "breath": P(0.25, 0, 1, "breath")},
      tags=("slide whistle", "whistle", "swoop", "fall whistle", "wheee"))
def _slide_whistle(p, n, rng):
    k, dur = _k(p), n / SR
    a, b = (450, 2100) if p["up"] else (2100, 450)
    f = D.curve([(0, a * k), (dur, b * k)], n, log=True) * (1 + 0.012 * np.sin(2 * math.pi * 6.3 * _t(n)))
    x = np.sin(2 * math.pi * np.cumsum(f) / SR)
    x += _bp(rng.standard_normal(n), 2500, 6000) * 0.25 * p["breath"]
    return x * D.fade(np.ones(n), 0.02, 0.05)


@kind("womp", "cartoon", "Sad slide-down brass", "Four falling muted-brass notes with a drooping last one: the 'fail' sting.", (1.0, 5.0, 2.4),
      {"pitch": _pitch_p(), "tempo": P(0.42, 0.2, 0.8, "note length (s)"), "droop": P(3.0, 0, 6, "last-note droop (semitones)", unit="st"), "mute": P(0.6, 0, 1, "muted (wah)")},
      tags=("womp", "womp womp", "sad trombone", "fail", "sad horn", "wah wah wah", "trombone"))
def _womp(p, n, rng):
    out = np.zeros(n)
    seq = (46, 45, 44, 43)
    for i, m in enumerate(seq):
        ln = int((p["tempo"] * (0.9 if i < 3 else 2.5)) * SR)
        ln = min(ln, n - int(i * p["tempo"] * SR))
        if ln <= 0:
            break
        st = (m + p["pitch"])
        f = np.full(ln, hz(st))
        if i == 3:
            f = f * 2 ** (-p["droop"] * np.linspace(0, 1, ln) ** 1.6 / 12) * (1 + 0.01 * np.sin(2 * math.pi * 5.5 * _t(ln)))
        x = np.zeros(ln)
        for det in (-0.07, 0.0, 0.07):
            x += D.osc("saw", f * 2 ** (det / 12))
        fc = D.curve([(0, 400 + 600 * (1 - p["mute"])), (0.1, 1100 + 1200 * (1 - p["mute"])), (ln / SR, 500)], ln, log=True)
        x = D.sweep_filter(x, fc, "lowpass", order=2, res_db=3)
        env = D.adsr(ln, 0.025, 0.08, 0.8, 0.1 if i < 3 else 0.5)
        _place(out, x * env, i * p["tempo"], 0.17)
    return out


@kind("squeak", "cartoon", "Squeak", "A rubber-toy squeak (one or several).", (0.1, 2.0, 0.4),
      {"pitch": _pitch_p(), "count": P(1, 1, 5, "squeaks", integer=True), "rise": P(0.6, 0, 1, "rise")}, tags=("squeak", "squeaky toy", "rubber duck", "eek"))
def _squeak(p, n, rng):
    k = _k(p)
    out = np.zeros(n)
    m = int(min(0.12, n / SR / p["count"]) * SR)
    for i in range(p["count"]):
        f = D.curve([(0, 1500 * k), (m / SR * 0.6, (1500 + 1900 * p["rise"]) * k), (m / SR, 2000 * k)], m, log=True)
        x = np.sin(2 * math.pi * np.cumsum(f) / SR + 2.0 * np.sin(2 * math.pi * 40 * _t(m)))
        _place(out, x * D.fade(np.ones(m), 0.004, 0.02), i * m / SR * 1.3, 0.6)
    return out


@kind("honk", "cartoon", "Clown honk", "A reedy two-tone horn honk.", (0.2, 2.0, 0.5), {"pitch": _pitch_p(), "double": P(0, 0, 1, "double honk", integer=True)},
      tags=("honk", "clown horn", "bike horn", "car horn", "toot"))
def _honk(p, n, rng):
    k = _k(p)
    out = np.zeros(n)
    def one(m):
        x = D.osc("square", np.full(m, 330 * k), width=0.3) + D.osc("square", np.full(m, 415 * k * 1.003), width=0.45)
        return D.lowpass(x, 2600) * D.fade(np.ones(m), 0.006, 0.03) * 0.25
    if p["double"]:
        m = int(min(n / SR / 2.4, 0.22) * SR)
        _place(out, one(m), 0.0)
        _place(out, one(m), m / SR * 1.5)
    else:
        _place(out, one(int(min(n / SR, 0.4) * SR)), 0.0)
    return out


@kind("bloop", "cartoon", "Bloop", "A rising liquid 'bloop'.", (0.1, 1.0, 0.3), {"pitch": _pitch_p()}, tags=("bloop", "blorp", "gloop", "bubble up"))
def _bloop(p, n, rng):
    k = _k(p)
    f = D.curve([(0, 220 * k), (0.12, 780 * k), (n / SR, 600 * k)], n, log=True)
    return D.osc("sine", f) * _hit(n, 0.11, 0.003)


@kind("splat", "cartoon", "Splat", "A wet splat: noise slap plus a low thud.", (0.2, 2.0, 0.6), {"pitch": _pitch_p(), "wet": P(0.6, 0, 1, "wet")},
      tags=("splat", "squish", "wet hit", "pie", "slime"))
def _splat(p, n, rng):
    k = _k(p)
    fc = D.curve([(0, 5000 * k), (0.2, 500 * k), (n / SR, 300)], n, log=True)
    x = D.sweep_filter(rng.standard_normal(n), fc, "lowpass", order=2) * _hit(n, 0.12 + 0.18 * p["wet"], 0.001)
    x += _thud({"pitch": p["pitch"] - 6, "body": 0.4, "click": 0.0}, n, rng) * 0.8
    b = D.vibrato(D.osc("sine", np.full(n, 160 * k)), 14, 1.2) * _hit(n, 0.15) * p["wet"] * 0.4
    return x + b


@kind("sproing", "cartoon", "Sproing", "A fast ricocheting spring: a bouncing wobble.", (0.2, 2.0, 0.7), {"pitch": _pitch_p(), "bounces": P(5, 2, 12, "bounces", integer=True)},
      tags=("sproing", "ricochet", "spring bounce", "twang"))
def _sproing(p, n, rng):
    k, dur = _k(p), n / SR
    t = _t(n)
    f = 400 * k * (1 + 0.9 * np.exp(-t / (dur * 0.5)) * np.sin(2 * math.pi * p["bounces"] / dur * t))
    return np.sin(2 * math.pi * np.cumsum(f) / SR) * _hit(n, dur * 0.6, 0.002)


@kind("zip", "cartoon", "Cartoon run", "A fast scurry of rising chirps: legs spinning.", (0.4, 3.0, 1.0), {"pitch": _pitch_p(), "chirps": P(10, 4, 24, "chirps", integer=True)},
      tags=("zip", "scurry", "run", "cartoon run", "scamper", "zoom"))
def _zip(p, n, rng):
    k = _k(p)
    out = np.zeros(n)
    gap = n / SR / (p["chirps"] + 1)
    m = int(gap * 0.9 * SR)
    for i in range(p["chirps"]):
        f = D.curve([(0, (500 + 40 * i) * k), (m / SR, (1100 + 60 * i) * k)], m, log=True)
        _place(out, D.osc("tri", f) * D.fade(np.ones(m), 0.002, 0.01), i * gap, 0.4)
    return out


@kind("bell", "cartoon", "Bicycle bell", "A bright two-ring bell.", (0.3, 3.0, 1.1), {"pitch": _pitch_p(), "rings": P(2, 1, 4, "rings", integer=True)},
      tags=("bell", "ding", "bicycle", "service bell", "hotel bell"))
def _bell_k(p, n, rng):
    k = _k(p)
    out = np.zeros(n)
    for i in range(p["rings"]):
        m = n - int(i * 0.09 * SR)
        _place(out, _bell_partials(m, 2900 * k, [1, 2.4, 5.9], 0.5, rng, spread=0.01) * 0.7, i * 0.09)
    return out


# =========================================================================== GLITCH / DIGITAL
@kind("glitch", "glitch", "Glitch burst", "A chopped-up tone: stutters, reversals and bit crush.", (0.2, 4.0, 0.8),
      {"pitch": _pitch_p(), "mess": P(0.6, 0, 1, "mess"), "base": P("saw", options=("saw", "square", "sine", "noise"))}, tags=("glitch", "stutter", "error noise", "corrupted", "digital error"))
def _glitch(p, n, rng):
    k = _k(p)
    if p["base"] == "noise":
        x = rng.standard_normal(n) * 0.4
    else:
        x = D.osc(p["base"], D.curve([(0, 440 * k), (n / SR, 220 * k)], n, log=True)) * 0.6
    return D.glitch(x, rng, p["mess"])


@kind("static_burst", "glitch", "Static burst", "A gated burst of digital static.", (0.1, 3.0, 0.5), {"pitch": _pitch_p(), "chop": P(0.6, 0, 1, "chop")},
      tags=("static", "tv static", "interference", "radio static"))
def _static(p, n, rng):
    x = D.highpass(rng.standard_normal(n), 400 * _k(p))
    steps = np.repeat(rng.random(max(2, int(n / SR * 40)) ) > (0.2 + 0.5 * p["chop"]), int(SR / 40))[:n]
    steps = np.pad(steps, (0, n - len(steps)), constant_values=False).astype(float)
    return x * steps * 0.5 * D.fade(np.ones(n), 0.003, 0.02)


@kind("data_chirps", "glitch", "Data chirps", "Random short beeps like a data link or a modem.", (0.3, 5.0, 1.2), {"pitch": _pitch_p(), "density": P(0.6, 0.1, 1, "density")},
      tags=("data", "chirps", "computer", "hacker", "dial-up", "telemetry"))
def _chirps(p, n, rng):
    out = np.zeros(n)
    count = int(n / SR * (15 + 40 * p["density"]))
    for _ in range(count):
        m = int(rng.uniform(0.012, 0.045) * SR)
        at = rng.uniform(0, max(0.001, n / SR - 0.05))
        f = hz(rng.integers(70, 105) + p["pitch"])
        _place(out, D.osc(rng.choice(["square", "sine", "tri"]), np.full(m, f)) * D.fade(np.ones(m), 0.001, 0.004), at, 0.25)
    return out


@kind("scratch", "glitch", "Record scratch", "A voice-like tone dragged back and forth: the record-stop beat.", (0.4, 3.0, 1.1),
      {"pitch": _pitch_p(), "violence": P(0.6, 0, 1, "violence"), "noise": P(0.3, 0, 1, "vinyl noise")}, tags=("scratch", "record scratch", "record stop", "dj", "wait what"))
def _scratch(p, n, rng):
    k, dur = _k(p), n / SR
    m = int(1.6 * SR)
    t = _t(m)
    src = D.osc("saw", 150 * k * (1 + 0.25 * np.sin(2 * math.pi * 2.2 * t)))
    src = D.sweep_filter(src, D.curve([(0, 500), (0.4, 2200), (0.8, 700), (1.6, 1600)], m, log=True), "lowpass", order=2, res_db=6)
    src += _bp(rng.standard_normal(m), 1500, 5000) * 0.1
    pts = [(0.0, 0.0)]
    cur = 0.0
    segs = max(4, int(dur * 7))
    for i in range(1, segs + 1):
        cur += rng.uniform(0.04, 0.22) * (1 if rng.random() > 0.35 * p["violence"] else -1) * (0.6 + p["violence"])
        pts.append((dur * i / segs, abs(cur)))
    pos = D.curve(pts, n)
    pos = D.lowpass(pos, 40, order=2)
    x = D.read_at(src, np.clip(pos * SR * 0.5 + 0.3 * SR, 0, m - 2))
    stop = np.clip(1.0 - (np.arange(n) / SR - dur * 0.85) / (dur * 0.15), 0, 1)
    return (x + D.highpass(rng.standard_normal(n), 3000) * 0.04 * p["noise"]) * stop * 0.7


@kind("tape_stop_chord", "glitch", "Tape-stop chord", "A held chord whose tape winds down to a halt.", (0.6, 4.0, 1.8),
      {"pitch": _pitch_p(), "stop": P(0.8, 0.2, 2.5, "wind-down (s)"), "hold": P(0.5, 0, 2, "hold before stop (s)")}, tags=("tape stop", "wind down", "slow down", "stop"))
def _tape_stop_chord(p, n, rng):
    x = np.zeros(n + SR)
    for st in (0, 3, 7, 10):
        for det in (-0.1, 0.1):
            x += D.osc("saw", np.full(n + SR, hz(52 + p["pitch"] + st + det)))
    x = D.lowpass(x, 2200) * 0.08
    return D.tape_stop(x, p["hold"], p["stop"])[:n]


@kind("dial_tones", "glitch", "Keypad tones", "The standard dual-tone keypad beeps for a short number.", (0.6, 6.0, 2.0), {"digits": P("5551234", options=()), "speed": P(0.11, 0.06, 0.3, "tone length (s)")},
      tags=("dial", "keypad", "phone number", "touch tone", "dtmf"))
def _dial(p, n, rng):
    low, high = (697, 770, 852, 941), (1209, 1336, 1477)
    keys = "123456789*0#"
    out = np.zeros(n)
    digits = [c for c in str(p["digits"]) if c in keys][:16] or list("5551234")
    for i, c in enumerate(digits):
        j = keys.index(c)
        m = int(p["speed"] * SR)
        t = _t(m)
        x = (np.sin(2 * math.pi * low[j // 3] * t) + np.sin(2 * math.pi * high[j % 3] * t)) * D.fade(np.ones(m), 0.003, 0.004)
        _place(out, x, i * p["speed"] * 1.45, 0.25)
    return out


# =========================================================================== AMBIENCE / FOLEY
def _loop_ready(x: np.ndarray, sec: float = 0.4) -> np.ndarray:
    return D.make_loop(x, sec) if len(x) > 3 * sec * SR else x


@kind("rain", "ambience", "Rain", "Steady rain with drops; loops.", (2.0, 30.0, 8.0), {"pitch": _pitch_p(), "heavy": P(0.5, 0, 1, "heaviness")}, tags=("rain", "storm", "drizzle", "shower"), loop=True)
def _rain(p, n, rng):
    x = D.highpass(D.noise("pink", n + int(0.4 * SR), rng), 900 * _k(p)) * (0.3 + 0.5 * p["heavy"])
    drops = np.zeros(len(x))
    for _ in range(int(len(x) / SR * (30 + 220 * p["heavy"]))):
        m = int(0.012 * SR)
        _place(drops, _bp(rng.standard_normal(m), 2500, 9000) * np.exp(-np.arange(m) / (0.003 * SR)), rng.uniform(0, len(x) / SR - 0.02), rng.uniform(0.2, 1.0))
    return _loop_ready((x + drops * 0.6)[: n + int(0.4 * SR)], 0.4)[:n]


@kind("wind", "ambience", "Wind", "Moving wind with gusts; loops.", (2.0, 30.0, 8.0), {"pitch": _pitch_p(), "gust": P(0.6, 0, 1, "gustiness")}, tags=("wind", "howl", "breeze", "gale"), loop=True)
def _wind(p, n, rng):
    m = n + int(0.5 * SR)
    ctrl = D.lowpass(rng.standard_normal(m), 0.6, order=2) if False else D.lowpass(rng.standard_normal(m), 1.2, order=2)
    ctrl = ctrl / max(float(np.abs(ctrl).max()), 1e-6)
    fc = 350 * _k(p) * 2 ** (1.8 * p["gust"] * ctrl + 0.6)
    x = D.sweep_filter(D.noise("pink", m, rng), fc, "lowpass", order=2, res_db=6)
    amp = 0.6 + 0.4 * p["gust"] * ctrl
    return _loop_ready(x * amp, 0.5)[:n]


@kind("ocean", "ambience", "Ocean waves", "Slow rolling waves; loops.", (3.0, 30.0, 10.0), {"pitch": _pitch_p(), "period": P(7.0, 3, 14, "wave period (s)")}, tags=("ocean", "sea", "waves", "beach", "surf"), loop=True)
def _ocean(p, n, rng):
    m = n + int(0.6 * SR)
    t = _t(m)
    swell = 0.5 + 0.5 * np.sin(2 * math.pi * t / p["period"] - 1.2)
    fc = 250 * _k(p) * 2 ** (3.0 * swell)
    x = D.sweep_filter(D.noise("pink", m, rng), fc, "lowpass", order=2) * (0.15 + 0.85 * swell ** 1.5)
    return _loop_ready(x, 0.6)[:n]


@kind("room_tone", "ambience", "Room tone", "A quiet room: low air and a faint mains hum.", (2.0, 30.0, 8.0), {"pitch": _pitch_p(), "hum": P(0.3, 0, 1, "hum")}, tags=("room tone", "silence", "quiet", "air", "awkward silence"), loop=True)
def _room(p, n, rng):
    x = D.lowpass(D.noise("pink", n, rng), 500, order=2) * 0.15
    t = _t(n)
    x += (np.sin(2 * math.pi * 50 * t) + 0.4 * np.sin(2 * math.pi * 100 * t)) * 0.02 * p["hum"] * 3
    return _loop_ready(x, 0.4)


@kind("crickets", "ambience", "Crickets", "A night field of chirping crickets: the awkward-silence sound.", (2.0, 30.0, 6.0),
      {"pitch": _pitch_p(), "crickets": P(5, 1, 12, "crickets", integer=True)}, tags=("crickets", "night", "awkward silence", "chirp", "awkward"), loop=True)
def _crickets(p, n, rng):
    t = _t(n)
    out = np.zeros(n)
    for c in range(p["crickets"]):
        f = rng.uniform(4000, 5200) * _k(p)
        rate = rng.uniform(26, 34)
        group = rng.uniform(0.9, 1.6)
        phase = rng.uniform(0, group)
        gate = ((t + phase) % group) < rng.uniform(0.25, 0.45)
        pulse = (np.sin(2 * math.pi * rate * t) > 0.2).astype(float)
        pulse = D.lowpass(pulse, 220, order=2)
        out += np.sin(2 * math.pi * f * t) * pulse * gate * rng.uniform(0.15, 0.4)
    return _loop_ready(out, 0.3)


@kind("hum", "ambience", "Mains hum", "A 50 or 60 Hz electrical hum with harmonics; loops.", (1.0, 30.0, 6.0), {"freq": P(50, 40, 70, "base (Hz)", integer=True, unit="Hz"), "buzz": P(0.4, 0, 1, "buzz")},
      tags=("hum", "electric hum", "fluorescent", "mains", "buzz"), loop=True)
def _hum(p, n, rng):
    t = _t(n)
    x = sum(np.sin(2 * math.pi * p["freq"] * h * t + h) / h ** (1.2 - 0.9 * p["buzz"]) for h in range(1, 12))
    f = int(p["freq"])
    return x * 0.2 if (n / SR * f) % 1 == 0 else _loop_ready(x * 0.2, 0.2)


@kind("drone", "ambience", "Dark drone", "A slow detuned low drone: tension underneath.", (3.0, 30.0, 10.0), {"pitch": _pitch_p(), "dark": P(0.6, 0, 1, "dark"), "motion": P(0.4, 0, 1, "motion")},
      tags=("drone", "tension", "dark", "ominous", "horror", "suspense"), loop=True)
def _drone(p, n, rng):
    m = n + int(0.8 * SR)
    x = np.zeros(m)
    for det in (-0.18, -0.06, 0.07, 0.19):
        x += D.osc("saw", np.full(m, hz(33 + p["pitch"] + det)))
    x += D.osc("sine", np.full(m, hz(21 + p["pitch"]))) * 3
    fc = 250 * 2 ** ((1 - p["dark"]) * 2 + 1.2 * p["motion"] * np.sin(2 * math.pi * _t(m) / 6.5))
    return _loop_ready(D.sweep_filter(x, fc, "lowpass", order=2) * 0.12, 0.8)[:n]


@kind("heartbeat", "ambience", "Heartbeat", "A lub-dub heartbeat at a set rate.", (1.0, 30.0, 5.0), {"pitch": _pitch_p(), "bpm": P(72, 40, 160, "beats per minute", integer=True)},
      tags=("heartbeat", "heart", "pulse", "tension", "anxious"))
def _heartbeat(p, n, rng):
    out = np.zeros(n)
    period = 60.0 / p["bpm"]
    one = lambda amp: _thud({"pitch": p["pitch"] - 4, "body": 0.2, "click": 0.0}, int(0.22 * SR), rng) * amp
    for i in range(int(n / SR / period) + 1):
        _place(out, one(1.0), i * period)
        _place(out, one(0.65), i * period + 0.27 * min(1.0, 0.9 * period / 0.9))
    return out


@kind("clock", "ambience", "Clock ticking", "A wall-clock tick-tock.", (1.0, 30.0, 5.0), {"pitch": _pitch_p(), "bpm": P(60, 30, 120, "ticks per minute", integer=True)},
      tags=("clock", "tick tock", "ticking", "time passing", "watch"))
def _clock(p, n, rng):
    k = _k(p)
    out = np.zeros(n)
    period = 60.0 / p["bpm"]
    for i in range(int(n / SR / period) + 1):
        m = int(0.05 * SR)
        f = (1700 if i % 2 == 0 else 1350) * k
        _place(out, (np.sin(2 * math.pi * f * _t(m)) * _hit(m, 0.012, 0.0004) + _bp(rng.standard_normal(m), 1500, 6000) * _hit(m, 0.004) * 0.6), i * period, 0.9)
    return out


@kind("fire", "ambience", "Fire crackle", "Crackling embers and a low roar.", (2.0, 30.0, 8.0), {"pitch": _pitch_p(), "crackle": P(0.6, 0.1, 1, "crackle")}, tags=("fire", "crackle", "campfire", "fireplace", "embers"), loop=True)
def _fire(p, n, rng):
    x = D.lowpass(D.noise("brown", n, rng), 700, order=2) * 0.25
    for _ in range(int(n / SR * (6 + 35 * p["crackle"]))):
        m = int(rng.uniform(0.004, 0.02) * SR)
        _place(x, _bp(rng.standard_normal(m), 800, 6000) * np.exp(-np.arange(m) / (0.2 * m)), rng.uniform(0, n / SR), rng.uniform(0.3, 1.8))
    return _loop_ready(x, 0.4)


@kind("typing", "ambience", "Keyboard typing", "Fast keyboard key clicks.", (1.0, 20.0, 4.0), {"pitch": _pitch_p(), "speed": P(7, 2, 14, "keys per second"), "loud": P(0.6, 0.2, 1, "loudness")},
      tags=("typing", "keyboard", "keys", "clicky", "typewriter"))
def _typing(p, n, rng):
    k = _k(p)
    out = np.zeros(n)
    t = 0.05
    while t < n / SR - 0.05:
        m = int(0.045 * SR)
        click = _bp(rng.standard_normal(m), 1800 * k, 7000 * k) * _hit(m, 0.004) + np.sin(2 * math.pi * rng.uniform(180, 320) * k * _t(m)) * _hit(m, 0.012) * 0.5
        _place(out, click, t, rng.uniform(0.5, 1.0) * p["loud"])
        t += rng.exponential(1.0 / p["speed"]) * (0.5 + rng.random() * 0.7)
    return out


@kind("footsteps", "ambience", "Footsteps", "A walker: steps at a pace on a hard or soft surface.", (1.0, 20.0, 5.0),
      {"pitch": _pitch_p(), "pace": P(1.8, 0.8, 4, "steps per second"), "surface": P("hard", options=("hard", "soft", "gravel", "wood"))}, tags=("footsteps", "walking", "steps", "running", "gravel"))
def _footsteps(p, n, rng):
    out = np.zeros(n)
    cut = {"hard": 4200, "soft": 900, "gravel": 6500, "wood": 2400}[p["surface"]] * _k(p)
    i, t = 0, 0.1
    while t < n / SR - 0.1:
        m = int(0.16 * SR)
        step = D.lowpass(rng.standard_normal(m), cut, order=2) * _hit(m, 0.035 if p["surface"] != "gravel" else 0.07)
        step += np.sin(2 * math.pi * (95 + 25 * (i % 2)) * _t(m)) * _hit(m, 0.05) * (1.5 if p["surface"] != "gravel" else 0.6)
        _place(out, step, t, rng.uniform(0.75, 1.0))
        t += 1.0 / p["pace"] * rng.uniform(0.94, 1.06)
        i += 1
    return out


@kind("knock", "ambience", "Door knock", "Three wooden knocks.", (0.5, 5.0, 1.6), {"pitch": _pitch_p(), "knocks": P(3, 1, 8, "knocks", integer=True), "gap": P(0.22, 0.1, 0.6, "gap (s)")},
      tags=("knock", "door knock", "knocking", "someone is here"))
def _knock(p, n, rng):
    k = _k(p)
    out = np.zeros(n)
    for i in range(p["knocks"]):
        m = int(0.18 * SR)
        f = _pitch_drop(m, 260 * k, 150 * k, 0.02)
        x = np.sin(2 * math.pi * np.cumsum(f) / SR) * _hit(m, 0.05) + _bp(rng.standard_normal(m), 500, 2500) * _hit(m, 0.008) * 0.8
        _place(out, x, 0.05 + i * p["gap"] * rng.uniform(0.92, 1.08), 0.9 - 0.05 * (i % 2))
    return out


@kind("shutter", "ambience", "Camera shutter", "Two crisp mechanical clicks.", (0.2, 1.5, 0.45), {"pitch": _pitch_p()}, tags=("shutter", "camera", "photo", "snapshot"))
def _shutter(p, n, rng):
    k = _k(p)
    out = np.zeros(n)
    for at, f in ((0.0, 3100), (0.07, 2300)):
        m = int(0.03 * SR)
        _place(out, (_bp(rng.standard_normal(m), 1500, 8000) + np.sin(2 * math.pi * f * k * _t(m)) * 0.6) * _hit(m, 0.006), at)
    return out


@kind("phone_ring", "ambience", "Phone ring", "The classic double ring of a landline.", (1.0, 8.0, 3.0), {"pitch": _pitch_p(), "rings": P(2, 1, 4, "rings", integer=True)},
      tags=("phone", "ring", "landline", "telephone ring", "ringing"))
def _phone_ring(p, n, rng):
    k, t = _k(p), _t(n)
    tone = np.sin(2 * math.pi * 440 * k * t) + np.sin(2 * math.pi * 480 * k * t)
    gate = np.zeros(n)
    for r in range(p["rings"]):
        a = int((r * 3.0) * SR)
        gate[a:a + int(0.8 * SR)] = 1.0
    gate = D.lowpass(gate, 60, order=2).clip(0, 1)
    return tone * gate * 0.3


@kind("siren", "ambience", "Siren", "A wailing two-tone siren.", (1.0, 12.0, 4.0), {"pitch": _pitch_p(), "rate": P(0.7, 0.2, 2, "wail rate (Hz)")}, tags=("siren", "ambulance", "police", "emergency", "wail"))
def _siren(p, n, rng):
    f = (600 + 300 * (1 + np.sin(2 * math.pi * p["rate"] * _t(n)))) * _k(p)
    x = D.osc("saw", f) + 0.5 * D.osc("sine", f * 2)
    return D.lowpass(x, 3500) * 0.2


# =========================================================================== TEXTURES (ASMR-style, all non-vocal)
@kind("brush", "asmr", "Soft brushing", "Slow soft brush strokes over a surface.", (2.0, 20.0, 6.0), {"pitch": _pitch_p(), "stroke": P(1.1, 0.4, 3, "strokes per second"), "soft": P(0.6, 0, 1, "softness")},
      tags=("brush", "brushing", "stroke", "asmr", "soft"), loop=True)
def _brush(p, n, rng):
    x = _bp(D.noise("white", n, rng), 600 * _k(p), 7000 * (1 - 0.6 * p["soft"]) * _k(p), order=2)
    amp = 0.5 + 0.5 * np.sin(2 * math.pi * p["stroke"] * _t(n) - 1.6)
    return x * amp ** 1.3 * 0.7


@kind("tapping", "asmr", "Soft tapping", "Gentle fingertip taps in a loose rhythm.", (2.0, 20.0, 6.0), {"pitch": _pitch_p(), "rate": P(3.0, 0.8, 8, "taps per second"), "hollow": P(0.5, 0, 1, "hollow")},
      tags=("tapping", "taps", "fingernails", "asmr", "tap tap"))
def _tapping(p, n, rng):
    k = _k(p)
    out = np.zeros(n)
    t = 0.05
    while t < n / SR - 0.05:
        m = int(0.06 * SR)
        f = (500 + 600 * p["hollow"]) * k * rng.uniform(0.95, 1.05)
        x = np.sin(2 * math.pi * f * _t(m)) * _hit(m, 0.012, 0.0003) + _bp(rng.standard_normal(m), 1500, 6000) * _hit(m, 0.003) * 0.5
        _place(out, x, t, rng.uniform(0.6, 1.0))
        t += (1.0 / p["rate"]) * rng.uniform(0.7, 1.3)
    return out


@kind("crinkle", "asmr", "Crinkle", "Dense crinkling paper / foil.", (1.0, 20.0, 4.0), {"pitch": _pitch_p(), "density": P(0.6, 0.1, 1, "density")}, tags=("crinkle", "paper", "foil", "wrapper", "crumple", "asmr"))
def _crinkle(p, n, rng):
    out = np.zeros(n)
    for _ in range(int(n / SR * (60 + 500 * p["density"]))):
        m = int(rng.uniform(0.001, 0.006) * SR)
        _place(out, _bp(rng.standard_normal(m), 2500 * _k(p), 9000 * _k(p), order=1) * np.exp(-np.arange(m) / (0.3 * m)), rng.uniform(0, n / SR), rng.lognormal(-0.8, 0.8))
    slow = 0.4 + 0.6 * np.abs(D.lowpass(rng.standard_normal(n), 3, order=2))
    return out * slow / max(float(slow.max()), 1e-6)


@kind("bubbles", "asmr", "Bubbles", "Lots of small liquid bubbles.", (1.0, 20.0, 4.0), {"pitch": _pitch_p(), "density": P(0.5, 0.1, 1, "density")}, tags=("bubbles", "boiling", "water", "fizz", "gurgle"))
def _bubbles(p, n, rng):
    out = np.zeros(n)
    for _ in range(int(n / SR * (6 + 40 * p["density"]))):
        m = int(rng.uniform(0.04, 0.12) * SR)
        f0 = rng.uniform(250, 1200) * _k(p)
        f = D.curve([(0, f0), (m / SR * 0.5, f0 * 1.6), (m / SR, f0 * 1.4)], m, log=True)
        _place(out, D.osc("sine", f) * _hit(m, 0.03, 0.002), rng.uniform(0, n / SR - 0.12), rng.uniform(0.2, 0.8))
    return out


@kind("hiss", "asmr", "Tape hiss", "A band of soft hiss; loops.", (1.0, 30.0, 6.0), {"pitch": _pitch_p(), "air": P(0.5, 0, 1, "air")}, tags=("hiss", "tape hiss", "white noise", "static", "air"), loop=True)
def _hiss(p, n, rng):
    return D.lowpass(D.highpass(D.noise("pink", n, rng), 1500 * _k(p), order=2), 14000 * (0.4 + 0.6 * p["air"]), order=2) * 0.3


# =========================================================================== NOTES, HOOKS, STINGS
def _pluck_note(n: int, f: float, damp: float, rng) -> np.ndarray:
    N = max(2, int(round(SR / f)))
    y = np.zeros(n + N * 2)
    seed = rng.uniform(-1, 1, N)
    seed = D.lowpass(seed, 6000, order=1) if N > 16 else seed
    y[:N] = seed
    for i in range(N, len(y) - N, N):
        blk = y[i - N:i]
        y[i:i + N] = damp * 0.5 * (blk + np.roll(blk, 1))
    return y[:n]


@kind("pluck", "music", "Plucked note", "A Karplus-Strong string pluck.", (0.3, 6.0, 1.5), {"note": P(60, 28, 96, "note (MIDI)", integer=True), "pitch": _pitch_p(), "damp": P(0.996, 0.95, 0.9995, "sustain")},
      tags=("pluck", "string", "guitar", "harp", "note"))
def _pluck(p, n, rng):
    return _pluck_note(n, hz(p["note"] + p["pitch"]), p["damp"], rng) * 1.6


@kind("fm_bell", "music", "FM bell", "A glassy FM bell note.", (0.3, 6.0, 2.0), {"note": P(72, 36, 108, "note (MIDI)", integer=True), "pitch": _pitch_p(), "ring": P(1.2, 0.2, 4, "ring (s)"), "ratio": P(3.5, 1, 7, "FM ratio")},
      tags=("bell", "fm", "glock", "bright note", "chime"))
def _fm_bell(p, n, rng):
    f, t = hz(p["note"] + p["pitch"]), _t(n)
    idx = 4.0 * np.exp(-t / (p["ring"] * 0.4))
    return np.sin(2 * math.pi * f * t + idx * np.sin(2 * math.pi * f * p["ratio"] * t)) * _hit(n, p["ring"], 0.001)


@kind("sub_drop", "music", "Bass drop (sub)", "A pure sub-bass falling from mid to deep with a little drive.", (0.5, 6.0, 2.0), {"pitch": _pitch_p(), "from": P(70, 40, 120, "start (Hz)", integer=True, unit="Hz"), "to": P(26, 18, 45, "end (Hz)", integer=True, unit="Hz")},
      tags=("sub drop", "bass drop", "dubstep drop", "808 slide", "sub"))
def _sub_drop(p, n, rng):
    dur = n / SR
    f = D.curve([(0, p["from"] * _k(p)), (dur * 0.6, p["to"] * _k(p)), (dur, p["to"] * _k(p))], n, log=True)
    return D.distort(np.sin(2 * math.pi * np.cumsum(f) / SR), 6, "tanh") * D.fade(np.ones(n), 0.004, 0.08)


@kind("chime_arp", "music", "Bell arpeggio", "A pentatonic bell arpeggio: a sparkle or a reveal.", (0.8, 8.0, 2.5),
      {"pitch": _pitch_p(), "count": P(6, 3, 12, "notes", integer=True), "speed": P(0.11, 0.05, 0.4, "note gap (s)"), "direction": P("up", options=("up", "down", "random"))},
      tags=("arpeggio", "sparkle", "magic", "reveal", "twinkle", "chimes"))
def _chime_arp(p, n, rng):
    scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26]
    seq = scale[: p["count"]]
    if p["direction"] == "down":
        seq = seq[::-1]
    elif p["direction"] == "random":
        seq = list(rng.permutation(seq))
    out = np.zeros(n)
    for i, st in enumerate(seq):
        m = n - int(i * p["speed"] * SR)
        if m <= 0:
            break
        _place(out, _fm_bell({"note": 76, "pitch": p["pitch"] + st, "ring": 0.9, "ratio": 3.5}, min(m, int(1.6 * SR)), rng), i * p["speed"], 0.5)
    return out


@kind("jingle", "music", "Note melody (jingle)", "Your own notes, e.g. 'C5 E5 G5 C6', played as pluck / bell / square / sine.", (0.5, 20.0, 2.0),
      {"notes": P("C5 E5 G5 C6", options=()), "voice": P("bell", options=("bell", "pluck", "square", "sine", "tri")), "step": P(0.18, 0.06, 0.8, "note length (s)"), "pitch": _pitch_p()},
      tags=("jingle", "melody", "tune", "ringtone", "notes", "motif"), natural=True)
def _jingle(p, n, rng):
    notes = parse_notes(str(p["notes"]))
    step = p["step"]
    total = int((len(notes) * step + 0.8) * SR)
    out = np.zeros(max(total, n))
    for i, m in enumerate(notes):
        if m != m:
            continue
        ln = int((step * 2.5 if p["voice"] in ("bell", "pluck") else step * 0.95) * SR)
        if p["voice"] == "bell":
            x = _fm_bell({"note": m, "pitch": p["pitch"], "ring": 0.8, "ratio": 3.5}, ln, rng)
        elif p["voice"] == "pluck":
            x = _pluck_note(ln, hz(m + p["pitch"]), 0.994, rng) * 1.6
        else:
            x = D.osc(p["voice"], np.full(ln, hz(m + p["pitch"]))) * D.fade(np.ones(ln), 0.003, 0.02) * 0.5
        _place(out, x, i * step, 0.6)
    return out


@kind("hook_sketch", "music", "Hook sketch (loop)", "A loopable 1-4 bar beat-and-melody sketch. A CPU doodle to audition a rhythm; the real song is a Music 3 / ACE route.", (2.0, 30.0, 8.0),
      {"bpm": P(104, 70, 180, "tempo (BPM)", integer=True), "bars": P(2, 1, 4, "bars", integer=True), "key": P(0, 0, 11, "key (0 = C)", integer=True),
       "scale": P("minor_pentatonic", options=("minor_pentatonic", "pentatonic", "minor", "major", "blues")), "density": P(0.5, 0.1, 1, "melody density"),
       "swing": P(0.0, 0, 0.5, "swing"), "drums": P(1, 0, 1, "drums on", integer=True), "pitch": _pitch_p()},
      tags=("hook", "loop", "beat", "melody", "earworm", "sketch", "jingle loop", "bounce"), loop=True, natural=True)
def _hook(p, n, rng):
    beat = 60.0 / p["bpm"]
    steps = 16 * p["bars"]
    step_s = beat / 4
    total = int(steps * step_s * SR)
    out = np.zeros(total)
    sw = lambda i: (i % 2) * p["swing"] * step_s * 0.6
    if p["drums"]:
        for i in range(steps):
            at = i * step_s + sw(i)
            if i % 4 == 0 and (i % 16 not in (4, 12) or rng.random() < 0.3):
                _place(out, _kick({"pitch": 0, "decay": 0.28, "click": 0.3}, int(0.4 * SR), rng), at, 0.9)
            if i % 8 == 4:
                _place(out, _clap({"pitch": 0, "bursts": 3, "room": 0.3}, int(0.3 * SR), rng), at, 0.55)
            if i % 2 == 0 or rng.random() < 0.25:
                m = int(0.05 * SR)
                _place(out, D.highpass(rng.standard_normal(m), 7000) * _hit(m, 0.012) * (0.5 if i % 4 else 0.8), at, 0.25)
    degrees = np.array(D.SCALES[p["scale"]])
    root = 36 + p["key"] + p["pitch"]
    bass_pat = [0, None, None, 0, None, 0, None, None, 3 % len(degrees), None, None, 0, None, 4 % len(degrees), None, None]
    for i in range(steps):
        d = bass_pat[i % 16]
        if d is None:
            continue
        ln = int(step_s * 2.2 * SR)
        f = hz(root + int(degrees[d % len(degrees)]))
        x = D.lowpass(D.osc("saw", np.full(ln, f)), 420, order=2) * D.fade(np.ones(ln), 0.004, 0.04) + D.osc("sine", np.full(ln, f)) * 0.5
        _place(out, x, i * step_s + sw(i), 0.35)
    pos = int(rng.integers(0, len(degrees)))
    for i in range(steps):
        if rng.random() > p["density"] * 0.85 + (0.3 if i % 4 == 0 else 0.0):
            continue
        pos = int(np.clip(pos + rng.integers(-2, 3), 0, len(degrees) * 2 - 1))
        octv, d = divmod(pos, len(degrees))
        m = 60 + p["key"] + p["pitch"] + int(degrees[d]) + 12 * octv
        ln = int(step_s * 3.0 * SR)
        _place(out, _pluck_note(ln, hz(m), 0.992, rng) * 1.4, i * step_s + sw(i), 0.55)
    return out


# =========================================================================== rendering
def kinds_public() -> list[dict]:
    """The picker's data: every kind with its parameters (ranges, defaults, options)."""
    out = []
    for k in KINDS.values():
        out.append({"id": k.id, "family": k.family, "family_label": FAMILIES[k.family], "label": k.label, "desc": k.desc, "tags": list(k.tags),
                    "seconds": {"min": k.seconds[0], "max": k.seconds[1], "default": k.seconds[2]}, "loop": k.loop, "natural": k.natural,
                    "params": {name: {"default": q.default, "min": q.lo, "max": q.hi, "label": q.label or name, "options": list(q.options), "integer": q.integer,
                                      "unit": q.unit} for name, q in k.params.items()}})
    return out


def resolve_params(k: Kind, given: dict | None) -> tuple[dict, list[str]]:
    """(clean params with every default filled and every value clamped, notes). An unknown name or an out-of-range / wrong-type value is noted."""
    notes: list[str] = []
    given = dict(given or {})
    out = {}
    for name, q in k.params.items():
        v = given.pop(name, q.default)
        if q.options and name not in ("notes", "digits"):
            if v not in q.options:
                notes.append(f"{name}: {v!r} is not one of {list(q.options)}; used {q.default!r}")
                v = q.default
        elif name in ("notes", "digits"):
            v = str(v)[:200]
        else:
            try:
                fv = float(v)
            except (TypeError, ValueError):
                notes.append(f"{name}: {v!r} is not a number; used {q.default}")
                fv = float(q.default)
            if fv != fv or fv in (float("inf"), float("-inf")):
                fv = float(q.default)
            c = min(max(fv, q.lo), q.hi)
            if c != fv:
                notes.append(f"{name}: {fv:g} is outside {q.lo:g}..{q.hi:g}; used {c:g}")
            v = int(round(c)) if q.integer else c
        out[name] = v
    for extra in given:
        notes.append(f"{extra}: not a parameter of {k.id}; ignored")
    return out, notes


def vary(k: Kind, params: dict, seed: int, amount: float) -> dict:
    """The take-to-take variation: nudge every numeric parameter by up to `amount` (0..1) of its range / 8, deterministically from the seed."""
    if amount <= 0:
        return dict(params)
    rng = D.rng_for(seed * 7919 + 13)
    out = dict(params)
    for name, q in k.params.items():
        if q.options or name in ("notes", "digits"):
            continue
        span = (q.hi - q.lo) * amount / 8.0
        v = float(out[name]) + rng.uniform(-span, span)
        v = min(max(v, q.lo), q.hi)
        out[name] = int(round(v)) if q.integer else v
    return out


def render(kind_id: str, params: dict | None = None, *, seconds: float | None = None, seed: int = 1, variation: float = 0.0, tone: float = 0.0) -> tuple[np.ndarray, dict]:
    """Synthesise one sound. Returns (mono float audio peak-normalised to -3 dBFS, info {kind, params, seconds, seed, notes})."""
    k = KINDS.get(kind_id)
    if k is None:
        raise SynthError(f"unknown sound {kind_id!r}")
    p, notes = resolve_params(k, params)
    if variation:
        p = vary(k, p, seed, float(min(max(variation, 0.0), 1.0)))
    lo, hi, default = k.seconds
    s = default if seconds is None else float(seconds)
    if s != s or not (MIN_S <= s <= MAX_S):
        raise SynthError(f"seconds must be between {MIN_S} and {MAX_S}")
    if s < lo or s > hi:
        c = min(max(s, lo), hi)
        notes.append(f"seconds: {s:g} is outside {lo:g}..{hi:g} for {k.id}; used {c:g}")
        s = c
    n = D.n_of(s)
    rng = D.rng_for(seed)
    x = np.asarray(k.fn(p, n, rng), dtype=np.float64)
    if not k.natural:
        x = D.fit_len(x, n)
    x = np.nan_to_num(x)
    tn = float(min(max(tone, -1.0), 1.0))
    if abs(tn) > 0.02:
        x = D.shelf(x, 3000, 7.0 * tn, "high") if tn > 0 else D.lowpass(x, 12000 * (1 + tn) ** 2 + 1200, order=2)
    pk = D.peak(x)
    if pk < 1e-6:
        raise SynthError(f"{k.id} came out silent with these settings")
    x = x * (D.lin(PRE_CHAIN_PEAK_DB) / pk)
    return x, {"kind": k.id, "params": p, "seconds": round(len(x) / SR, 3), "seed": int(seed), "variation": float(variation), "notes": notes}
