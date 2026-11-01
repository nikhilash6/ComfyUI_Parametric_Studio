"""Effect chains for the 🔊 Sound maker: named steps (numpy DSP from studio/sound_dsp.py), presets for the classic meme-sound looks,
parameter sliders, and the mastering step that guarantees nothing leaves painfully loud.

A CHAIN is {"preset": id | None, "sliders": {slider id: 0..1}, "steps": [{"step": id, "params": {...}}]}: the preset's steps first
(with the sliders moving their mapped parameters), then any extra steps. Every parameter is clamped to its range and every clamp is
reported. Unknown steps and unknown parameters are errors/notes, never ignored silently.

MASTER is separate and always runs last: trim the silent edges, click-free edges, optional loop crossfade, loudness to a TARGET
(-23 / -18 / -16 / -14 / -12 LUFS; nothing above -9 is accepted), then the look-ahead limiter holding the true peak at or below
-1 dBTP (never above -0.5). A sound that cannot reach its target without more than 6 dB of limiting stops short and says so.
No preset, not even "blown-out loud", can switch the limiter off.

Proof level: wired + unit-tested (finite, bounded, deterministic, limiter holds). Whether a preset sounds like its name is an
ear question: docs/processes/sound-maker.md "Listen list".
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from studio.sound import dsp as D
from studio.sound.dsp import SR
from studio.sound.synth import P

MAX_STEPS = 12
MAX_OUT_S = 30.0


class ChainError(ValueError):
    """Reported to the user as a message."""


@dataclass
class Step:
    id: str
    group: str
    label: str
    desc: str
    params: dict
    fn: Callable                      # fn(x, p, rng) -> array (mono in; stereo out only for "widen" / "autopan")
    stereo: bool = False              # produces a stereo array


STEPS: dict[str, Step] = {}


def step(id: str, group: str, label: str, desc: str, params: dict | None = None, stereo: bool = False):
    def deco(fn):
        STEPS[id] = Step(id, group, label, desc, params or {}, fn, stereo)
        return fn
    return deco


def _mixwet(dry, wet, m):
    n = min(len(dry), len(wet))
    return (1 - m) * dry[:n] + m * wet[:n]


# --------------------------------------------------------------------------- level and dynamics
@step("gain", "level", "Gain", "Raise or lower the level.", {"db": P(0, -40, 24, "dB", unit="dB")})
def _gain(x, p, rng):
    return x * D.lin(p["db"])


@step("fade", "level", "Fade in / out", "Click-free fades at the edges.", {"in_ms": P(2, 0, 2000, "in (ms)", unit="ms"), "out_ms": P(20, 0, 5000, "out (ms)", unit="ms")})
def _fade(x, p, rng):
    return D.fade(x, p["in_ms"] / 1000, p["out_ms"] / 1000)


@step("compress", "level", "Compressor", "Evens out the level (glue / punch).", {"thresh_db": P(-18, -50, 0, "threshold (dB)"), "ratio": P(4, 1, 20, "ratio"),
      "attack_ms": P(5, 0.5, 100, "attack (ms)"), "release_ms": P(90, 10, 800, "release (ms)"), "makeup_db": P(3, 0, 18, "make-up (dB)")})
def _compress(x, p, rng):
    return D.compress(x, p["thresh_db"], p["ratio"], p["attack_ms"], p["release_ms"], p["makeup_db"])


@step("gate", "level", "Noise gate", "Cuts what is quieter than the threshold.", {"thresh_db": P(-40, -80, -5, "threshold (dB)"), "release_ms": P(60, 5, 500, "release (ms)")})
def _gate(x, p, rng):
    return D.gate(x, p["thresh_db"], 2.0, p["release_ms"])


@step("saturate", "level", "Saturation / distortion", "Warm to wrecked. Always followed by the master limiter.", {"drive_db": P(12, 0, 48, "drive (dB)"),
      "kind": P("tanh", options=("tanh", "tube", "hard", "fold")), "mix": P(1.0, 0, 1, "wet")})
def _saturate(x, p, rng):
    return D.distort(x, p["drive_db"], p["kind"], p["mix"])


@step("hard_clip", "level", "Hard clip", "Square off the peaks (loud, harsh).", {"ceiling_db": P(-12, -36, 0, "clip level (dB)"), "makeup_db": P(10, 0, 30, "make-up (dB)")})
def _hard_clip(x, p, rng):
    c = D.lin(p["ceiling_db"])
    return np.clip(x, -c, c) * D.lin(p["makeup_db"])


@step("limit", "level", "Limiter", "A look-ahead limiter inside the chain (the master one always runs after).", {"ceiling_db": P(-3, -24, -0.5, "ceiling (dB)")})
def _limit(x, p, rng):
    return D.limit(x, p["ceiling_db"])


# --------------------------------------------------------------------------- filters / EQ
@step("lowpass", "filter", "Low-pass", "Remove highs.", {"fc": P(4000, 100, 20000, "cutoff (Hz)", unit="Hz"), "order": P(4, 1, 8, "steepness", integer=True), "res_db": P(0, 0, 18, "resonance (dB)")})
def _lowpass(x, p, rng):
    return D.lowpass(x, p["fc"], p["order"], res_db=p["res_db"])


@step("highpass", "filter", "High-pass", "Remove lows.", {"fc": P(200, 20, 12000, "cutoff (Hz)", unit="Hz"), "order": P(4, 1, 8, "steepness", integer=True)})
def _highpass(x, p, rng):
    return D.highpass(x, p["fc"], p["order"])


@step("bandpass", "filter", "Band-pass", "Keep a band.", {"lo": P(300, 20, 10000, "low (Hz)", unit="Hz"), "hi": P(3400, 100, 20000, "high (Hz)", unit="Hz")})
def _bandpass(x, p, rng):
    return D.bandpass(x, min(p["lo"], p["hi"] * 0.9), p["hi"], 3)


@step("eq_peak", "filter", "EQ bell", "Boost or cut around one frequency.", {"fc": P(1000, 40, 16000, "frequency (Hz)", unit="Hz"), "gain_db": P(6, -24, 24, "gain (dB)"), "q": P(1.0, 0.2, 6, "width (Q)")})
def _eq_peak(x, p, rng):
    return D.eq_peak(x, p["fc"], p["gain_db"], p["q"])


@step("low_shelf", "filter", "Bass shelf", "Boost or cut everything below the frequency.", {"fc": P(120, 30, 800, "frequency (Hz)", unit="Hz"), "gain_db": P(8, -18, 18, "gain (dB)")})
def _low_shelf(x, p, rng):
    return D.shelf(x, p["fc"], p["gain_db"], "low")


@step("high_shelf", "filter", "Treble shelf", "Boost or cut everything above the frequency.", {"fc": P(6000, 1000, 16000, "frequency (Hz)", unit="Hz"), "gain_db": P(5, -18, 18, "gain (dB)")})
def _high_shelf(x, p, rng):
    return D.shelf(x, p["fc"], p["gain_db"], "high")


@step("filter_sweep", "filter", "Filter sweep", "A low-pass whose cutoff moves from one value to another over the clip.", {"start_hz": P(300, 60, 18000, "start (Hz)", unit="Hz"),
      "end_hz": P(8000, 60, 18000, "end (Hz)", unit="Hz"), "res_db": P(4, 0, 18, "resonance (dB)")})
def _filter_sweep(x, p, rng):
    return D.sweep_filter(x, D.curve([(0, p["start_hz"]), (len(x) / SR, p["end_hz"])], len(x), log=True), "lowpass", order=2, res_db=p["res_db"])


# --------------------------------------------------------------------------- pitch and time
@step("pitch", "pitch", "Pitch shift (keep length)", "Shift the pitch, keep the length (phase vocoder; smears sharp hits a little).", {"semitones": P(0, -24, 24, "semitones", unit="st")})
def _pitch(x, p, rng):
    return D.pitch_shift(x, p["semitones"], True)


@step("varispeed", "pitch", "Speed + pitch (tape speed)", "Faster is higher and shorter; slower is lower and longer (the chipmunk / slowed sound).", {"semitones": P(0, -24, 24, "semitones", unit="st")})
def _varispeed(x, p, rng):
    return D.pitch_shift(x, p["semitones"], False)


@step("stretch", "pitch", "Time stretch", "Change the length, keep the pitch.", {"rate": P(1.0, 0.4, 2.5, "speed")})
def _stretch(x, p, rng):
    return D.time_stretch(x, p["rate"])


@step("formant", "pitch", "Formant shift", "Change the voice's 'size' without changing its pitch (below 1 deeper, above 1 smaller).", {"ratio": P(1.0, 0.6, 1.6, "ratio")})
def _formant(x, p, rng):
    return D.formant_shift(x, p["ratio"])


@step("pitch_slide", "pitch", "Pitch slide", "The pitch glides from one offset to another across the clip (a falling or rising whine).",
      {"from_st": P(0, -24, 24, "start (semitones)", unit="st"), "to_st": P(-7, -24, 24, "end (semitones)", unit="st")})
def _pitch_slide(x, p, rng):
    n = len(x)
    r = 2.0 ** (D.curve([(0, p["from_st"]), (n / SR, p["to_st"])], n) / 12.0)
    return D.varispeed(x, r, n)


@step("tape_stop", "pitch", "Tape stop", "The tape winds down to a halt.", {"start_s": P(0.0, 0, 10, "starts at (s)", unit="s"), "stop_s": P(0.6, 0.05, 4, "wind-down (s)", unit="s")})
def _tape_stop(x, p, rng):
    return D.tape_stop(x, p["start_s"], p["stop_s"])


@step("autotune", "pitch", "Autotune-ish pitch snap", "Pulls a voice or note toward a scale (the hard-tuned robot-pop sound). A rough method, not a transparent corrector.",
      {"key": P(0, 0, 11, "key (0 = C)", integer=True), "scale": P("major", options=tuple(D.SCALES)), "strength": P(1.0, 0, 1, "strength"), "retune_ms": P(15, 1, 400, "retune speed (ms)")})
def _autotune(x, p, rng):
    return D.pitch_snap(x, p["key"], p["scale"], p["strength"], p["retune_ms"])


# --------------------------------------------------------------------------- time-slice effects
@step("reverse", "time", "Reverse", "Play it backwards.")
def _reverse(x, p, rng):
    return D.reverse(x)


@step("reverse_swell", "time", "Reverse reverb swell", "The reverb tail played backwards INTO the sound (a suck-in before the hit).", {"rt60": P(1.6, 0.4, 5, "tail (s)", unit="s"), "mix": P(0.8, 0, 1, "level")})
def _reverse_swell(x, p, rng):
    wet = D.reverb(x, p["rt60"], 1.0, 0.7, 0.4, 5.0, int(rng.integers(1, 1 << 30)), tail=True)[len(x):]
    if wet.size < 100:
        return x
    swell = D.reverse(wet) * p["mix"]
    return np.concatenate([swell, x])


@step("stutter", "time", "Stutter", "Repeat a tiny slice (the glitchy 'buh-buh-buh').", {"at_s": P(0.0, 0, 10, "starts at (s)", unit="s"), "slice_ms": P(80, 15, 400, "slice (ms)", unit="ms"),
      "repeats": P(6, 2, 24, "repeats", integer=True), "decay_db": P(0.0, 0, 6, "fade per repeat (dB)")})
def _stutter(x, p, rng):
    return D.stutter(x, p["at_s"], p["slice_ms"] / 1000, p["repeats"], p["decay_db"])


@step("chop", "time", "Rhythmic chop", "Gate the sound on and off in a rhythm.", {"rate_hz": P(8, 1, 32, "chops per second"), "duty": P(0.5, 0.1, 0.9, "on-time"), "smooth_ms": P(3, 0.5, 30, "edge (ms)")})
def _chop(x, p, rng):
    ph = (np.arange(len(x)) / SR * p["rate_hz"]) % 1.0
    g = (ph < p["duty"]).astype(float)
    return x * D.lowpass(g, 1000.0 / max(p["smooth_ms"], 0.5), order=2).clip(0, 1)


@step("loop", "time", "Repeat / loop", "Repeat the whole sound N times with a short crossfade.", {"times": P(3, 2, 16, "times", integer=True), "xfade_ms": P(20, 0, 300, "crossfade (ms)", unit="ms")})
def _loop(x, p, rng):
    xf = int(p["xfade_ms"] / 1000 * SR)
    out = x.copy()
    for _ in range(p["times"] - 1):
        if xf > 8 and len(out) > xf and len(x) > xf:
            t = np.linspace(0, math.pi / 2, xf)
            out = np.concatenate([out[:-xf], out[-xf:] * np.cos(t) + x[:xf] * np.sin(t), x[xf:]])
        else:
            out = np.concatenate([out, x])
    return out[: int(MAX_OUT_S * SR)]


@step("glitch", "time", "Glitch", "Random repeats, reversals and bit-crush bursts.", {"intensity": P(0.5, 0, 1, "intensity")})
def _glitch(x, p, rng):
    return D.glitch(x, rng, p["intensity"])


@step("sidechain", "time", "Sidechain pump", "The level ducks on every beat (the EDM pump).", {"bpm": P(124, 60, 200, "BPM"), "depth_db": P(10, 2, 24, "depth (dB)"), "release_s": P(0.18, 0.05, 0.6, "release (s)")})
def _sidechain(x, p, rng):
    return D.sidechain_pump(x, p["bpm"], p["depth_db"], p["release_s"])


# --------------------------------------------------------------------------- space and modulation
@step("reverb", "space", "Reverb", "A synthetic room, from a booth to a cathedral.", {"rt60": P(1.2, 0.1, 8, "decay (s)", unit="s"), "mix": P(0.3, 0, 1, "wet"), "size": P(0.5, 0, 1, "size"),
      "damping": P(0.5, 0, 1, "damping"), "predelay_ms": P(8, 0, 120, "pre-delay (ms)", unit="ms")})
def _reverb(x, p, rng):
    return D.reverb(x, p["rt60"], p["mix"], p["size"], p["damping"], p["predelay_ms"], int(rng.integers(1, 1 << 30)))


@step("echo", "space", "Echo", "Repeats that fade away.", {"delay_ms": P(250, 2, 1500, "delay (ms)", unit="ms"), "feedback": P(0.4, 0, 0.9, "repeats"), "mix": P(0.5, 0, 1, "wet")})
def _echo(x, p, rng):
    return D.echo(x, p["delay_ms"] / 1000, p["feedback"], p["mix"])


@step("chorus", "space", "Chorus / flanger", "Thickens (chorus) or whooshes (flanger) with a modulated delay.", {"base_ms": P(18, 0.5, 40, "delay (ms)", unit="ms"), "depth_ms": P(3, 0.2, 10, "depth (ms)", unit="ms"),
      "rate_hz": P(0.5, 0.05, 8, "rate (Hz)", unit="Hz"), "mix": P(0.5, 0, 1, "wet")})
def _chorus(x, p, rng):
    return D.mod_delay(x, p["base_ms"], p["depth_ms"], p["rate_hz"], p["mix"])


@step("vibrato", "space", "Vibrato", "A wobbling pitch.", {"rate_hz": P(5.5, 0.5, 12, "rate (Hz)", unit="Hz"), "depth_ms": P(0.6, 0.05, 4, "depth (ms)", unit="ms")})
def _vibrato(x, p, rng):
    return D.vibrato(x, p["rate_hz"], p["depth_ms"])


@step("tremolo", "space", "Tremolo", "A wobbling level.", {"rate_hz": P(6, 0.5, 20, "rate (Hz)", unit="Hz"), "depth": P(0.5, 0, 1, "depth")})
def _tremolo(x, p, rng):
    return D.tremolo(x, p["rate_hz"], p["depth"])


@step("ring_mod", "space", "Ring modulator", "Metallic, robotic sidebands.", {"freq": P(120, 5, 2000, "frequency (Hz)", unit="Hz"), "mix": P(1.0, 0, 1, "wet")})
def _ring(x, p, rng):
    return D.ring_mod(x, p["freq"], p["mix"])


@step("widen", "space", "Stereo widen (mono-safe)", "Mono to stereo through a side signal, so the mono sum is unchanged.", {"width": P(0.6, 0, 1, "width"), "delay_ms": P(17, 5, 40, "delay (ms)")}, stereo=True)
def _widen(x, p, rng):
    return D.widen(x, p["width"], p["delay_ms"])


@step("autopan", "space", "Auto-pan", "The sound swings left and right.", {"rate_hz": P(0.8, 0.1, 6, "rate (Hz)", unit="Hz"), "depth": P(0.7, 0, 1, "depth")}, stereo=True)
def _autopan(x, p, rng):
    m = D.to_mono(x)
    pan = 0.5 + 0.5 * p["depth"] * np.sin(2 * math.pi * p["rate_hz"] * np.arange(len(m)) / SR)
    return np.stack([m * np.sqrt(1 - pan), m * np.sqrt(pan)], axis=1) * math.sqrt(2.0) * 0.75


@step("mono", "space", "Make mono", "Sum to mono.")
def _mono(x, p, rng):
    return D.to_mono(x)


# --------------------------------------------------------------------------- character / degradation looks
@step("bitcrush", "look", "Bit crush", "Fewer bits and a lower sample rate: 8-bit, arcade, crunchy.", {"bits": P(8, 2, 16, "bits", integer=True), "hold": P(1, 1, 40, "sample hold", integer=True)})
def _bitcrush(x, p, rng):
    return D.bitcrush(x, p["bits"], p["hold"])


@step("telephone", "look", "Telephone", "A narrow phone line: 300-3400 Hz, a little grit.", {"amount": P(0.6, 0, 1, "amount")})
def _telephone(x, p, rng):
    a = p["amount"]
    y = D.bandpass(x, 300 + 150 * a, 3400 - 600 * a, 4)
    y = D.distort(y, 3 + 9 * a, "tanh") * 0.6
    return D.bitcrush(y, 12 - int(4 * a), 1 + int(2 * a))


@step("megaphone", "look", "Megaphone / bullhorn", "Band-limited, resonant, clipped: shouted through a horn.", {"amount": P(0.6, 0, 1, "amount")})
def _megaphone(x, p, rng):
    a = p["amount"]
    y = D.bandpass(x, 500, 4200, 3)
    y = D.eq_peak(y, 1800, 6 + 6 * a, 1.5)
    y = D.distort(y, 8 + 14 * a, "hard") * 0.6
    return D.echo(y, 0.045, 0.3, 0.25 * a, repeats=3, tail=True)


@step("radio", "look", "Old radio / walkie-talkie", "AM band, static and a squelch.", {"amount": P(0.6, 0, 1, "amount"), "static": P(0.4, 0, 1, "static")})
def _radio(x, p, rng):
    y = D.bandpass(x, 400, 2800 + 600 * (1 - p["amount"]), 3)
    y = D.distort(y, 4 + 8 * p["amount"], "tanh") * 0.7
    n = len(y)
    st = D.highpass(rng.standard_normal(n), 900) * 0.05 * p["static"] * (1 + 3 * (np.abs(D.lowpass(rng.standard_normal(n), 30, order=2)) > 0.3))
    y = D.tremolo(y, 37, 0.1 * p["amount"]) + D.bandpass(st, 600, 4000)
    out = D.bitcrush(y, 11, 1)
    squelch = np.zeros(len(out))
    m = int(0.05 * SR)
    squelch[:m] = rng.standard_normal(m) * np.linspace(0.3, 0, m) * 0.2 * p["static"]
    return out + squelch


@step("underwater", "look", "Underwater", "Muffled, wobbling, in a big wet room.", {"amount": P(0.6, 0, 1, "amount")})
def _underwater(x, p, rng):
    a = p["amount"]
    y = D.lowpass(x, 1400 - 900 * a, 4)
    y = D.vibrato(y, 2.6, 0.5 + 1.2 * a)
    y = D.mod_delay(y, 12, 4, 0.3, 0.45)
    return D.reverb(y, 1.1, 0.25 * a + 0.1, 0.5, 0.9)


@step("muffled", "look", "Behind a wall", "Dull and distant, as if through a door or wall.", {"amount": P(0.6, 0, 1, "amount")})
def _muffled(x, p, rng):
    y = D.lowpass(x, 900 - 600 * p["amount"], 4)
    return D.reverb(y, 0.5, 0.2, 0.2, 0.9) * 0.9


@step("vinyl", "look", "Vinyl", "Dust, crackle, a slow warble and a rolled-off top.", {"amount": P(0.6, 0, 1, "amount")})
def _vinyl(x, p, rng):
    a, n = p["amount"], len(x)
    y = D.vibrato(D.lowpass(x, 11000 - 5000 * a, 2), 0.7, 0.35 * a)
    crack = np.zeros(n)
    for _ in range(int(n / SR * (8 + 50 * a))):
        m = int(rng.uniform(0.0005, 0.003) * SR)
        at = int(rng.integers(0, max(1, n - m)))
        crack[at:at + m] += rng.standard_normal(m) * rng.uniform(0.1, 0.7) * 0.15 * a
    hiss = D.highpass(rng.standard_normal(n), 3000) * 0.012 * a
    return y + crack + hiss


@step("tape", "look", "Cassette tape", "Wow and flutter, soft saturation and hiss.", {"amount": P(0.6, 0, 1, "amount")})
def _tape(x, p, rng):
    a = p["amount"]
    y = D.vibrato(x, 0.9, 0.45 * a)
    y = D.vibrato(y, 7.5, 0.06 * a)
    y = D.distort(y, 4 + 6 * a, "tube", 0.8)
    y = D.lowpass(y, 12000 - 6000 * a, 2)
    return y + D.highpass(D.noise("white", len(y), rng), 4000) * 0.01 * a


@step("lofi", "look", "Lo-fi", "Crunch, rolled-off highs, wobble: dusty and cheap on purpose.", {"amount": P(0.6, 0, 1, "amount")})
def _lofi(x, p, rng):
    a = p["amount"]
    y = D.bitcrush(x, 12 - int(5 * a), 1 + int(5 * a))
    y = D.lowpass(y, 9000 - 5500 * a, 3)
    return D.vibrato(y, 0.6, 0.3 * a)


@step("bass_boost", "look", "Bass boost", "Heavy low end (the limiter keeps it from clipping).", {"amount": P(0.6, 0, 1, "amount")})
def _bass(x, p, rng):
    a = p["amount"]
    y = D.shelf(x, 110, 6 + 12 * a, "low")
    y = D.eq_peak(y, 60, 4 + 8 * a, 1.0)
    return D.distort(y, 2 + 6 * a, "tanh", 0.35)


@step("noise_bed", "look", "Add noise bed", "Mix in hiss, hum or room tone under the sound.", {"kind": P("pink", options=("white", "pink", "brown")), "level_db": P(-34, -60, -10, "level (dB)")})
def _noise_bed(x, p, rng):
    return x + D.noise(p["kind"], len(x), rng) * D.lin(p["level_db"]) * max(D.peak(x), 0.1)


@step("trim", "level", "Trim silence", "Cut the silent head and tail.", {"thresh_db": P(-55, -80, -20, "threshold (dB)")})
def _trim(x, p, rng):
    return D.trim_silence(x, p["thresh_db"], 0.0, 0.05)[0]


# =========================================================================== presets
@dataclass
class Preset:
    id: str
    group: str
    label: str
    desc: str
    steps: list
    sliders: list
    tags: tuple = ()
    loud: bool = False
    suggest_lufs: float | None = None


PRESETS: dict[str, Preset] = {}


def preset(id, group, label, desc, steps, sliders=(), tags=(), loud=False, suggest_lufs=None):
    PRESETS[id] = Preset(id, group, label, desc, [dict(s) for s in steps], [dict(s) for s in sliders], tuple(tags), loud, suggest_lufs)


def slider(id, label, default, *targets):
    """targets: (step index, param, value at 0, value at 1)"""
    return {"id": id, "label": label, "default": default, "targets": [{"step": i, "param": p, "lo": lo, "hi": hi} for i, p, lo, hi in targets]}


S = lambda sid, **p: {"step": sid, "params": p}

preset("clean", "clean", "Clean", "No colour: just the master (trim, loudness, limiter).", [])
preset("punchy", "clean", "Dry and punchy", "Compressed and tight, a touch of top.", [S("compress", thresh_db=-20, ratio=4, makeup_db=4), S("high_shelf", fc=5000, gain_db=2.5)],
       [slider("punch", "punch", 0.5, (0, "ratio", 2, 10))], tags=("tight", "punch"))
preset("hype_hit", "space", "Hype hit", "A small bright room, glue compression and a hard ceiling: made to hit on a cut.",
       [S("compress", thresh_db=-22, ratio=5, makeup_db=4), S("reverb", rt60=0.8, mix=0.18, size=0.4, damping=0.5), S("high_shelf", fc=4500, gain_db=3)],
       [slider("room", "room", 0.5, (1, "mix", 0.05, 0.4), (1, "rt60", 0.4, 2.0))], tags=("hit", "cut"))
preset("big_room", "space", "Big room", "A large hall.", [S("reverb", rt60=2.2, mix=0.32, size=0.8, damping=0.5, predelay_ms=18)],
       [slider("wet", "wet", 0.5, (0, "mix", 0.1, 0.7)), slider("length", "length", 0.4, (0, "rt60", 0.8, 5.0))], tags=("hall", "reverb"))
preset("cathedral", "space", "Cathedral", "A huge stone space with a long dark tail.", [S("reverb", rt60=5.0, mix=0.45, size=1.0, damping=0.7, predelay_ms=30), S("low_shelf", fc=250, gain_db=-3)],
       [slider("wet", "wet", 0.5, (0, "mix", 0.15, 0.8))], tags=("church", "cavernous"))
preset("cave", "space", "Cave", "Close stone walls with slapback echoes.", [S("echo", delay_ms=180, feedback=0.45, mix=0.4), S("reverb", rt60=2.5, mix=0.3, size=0.7, damping=0.8)],
       [slider("echoes", "echoes", 0.5, (0, "feedback", 0.1, 0.8))], tags=("echoey", "cavern"))
preset("canyon", "space", "Canyon echo", "A far wall: long separate echoes.", [S("echo", delay_ms=520, feedback=0.55, mix=0.55), S("reverb", rt60=1.6, mix=0.2, size=0.9, damping=0.7)],
       [slider("echoes", "echoes", 0.55, (0, "feedback", 0.2, 0.85)), slider("distance", "distance", 0.5, (0, "delay_ms", 200, 1100))], tags=("echo", "yodel"))
preset("small_room", "space", "Small room", "A bathroom-size ambience.", [S("reverb", rt60=0.5, mix=0.22, size=0.15, damping=0.4)], [slider("wet", "wet", 0.5, (0, "mix", 0.05, 0.5))])
preset("telephone", "voice", "Telephone", "A phone line.", [S("telephone", amount=0.6)], [slider("amount", "grit", 0.6, (0, "amount", 0, 1))], tags=("phone", "call", "voicemail"))
preset("megaphone", "voice", "Megaphone", "Shouting through a bullhorn.", [S("megaphone", amount=0.6)], [slider("amount", "grit", 0.6, (0, "amount", 0, 1))], tags=("bullhorn", "loudspeaker", "police"), loud=True)
preset("walkie", "voice", "Walkie-talkie", "Radio crackle with a squelch click.", [S("radio", amount=0.7, static=0.5)],
       [slider("amount", "grit", 0.7, (0, "amount", 0, 1)), slider("static", "static", 0.5, (0, "static", 0, 1))], tags=("radio", "comms", "over"))
preset("old_radio", "voice", "Old radio", "A warm 1940s broadcast.", [S("radio", amount=0.3, static=0.25), S("low_shelf", fc=200, gain_db=2), S("tape", amount=0.3)],
       [slider("static", "static", 0.25, (0, "static", 0, 0.9))], tags=("1940s", "vintage", "broadcast"))
preset("intercom", "voice", "Intercom", "A boxy lobby speaker.", [S("bandpass", lo=500, hi=3000), S("saturate", drive_db=8, kind="tanh", mix=0.7), S("reverb", rt60=0.4, mix=0.15, size=0.2, damping=0.6)],
       tags=("speaker", "pa", "announcement"))
preset("underwater", "voice", "Underwater", "Muffled and wobbling under the surface.", [S("underwater", amount=0.7)], [slider("amount", "depth", 0.7, (0, "amount", 0, 1))], tags=("pool", "submerged"))
preset("behind_wall", "voice", "Behind a wall", "A party next door.", [S("muffled", amount=0.7)], [slider("amount", "thickness", 0.7, (0, "amount", 0, 1))], tags=("muffled", "next door", "distant"))
preset("chipmunk", "voice", "Chipmunk", "Higher and smaller: speed-up pitch with a lighter body.", [S("pitch", semitones=7), S("formant", ratio=1.25)],
       [slider("height", "height", 0.55, (0, "semitones", 2, 12), (1, "ratio", 1.05, 1.5))], tags=("squeaky", "helium", "high voice"))
preset("deep_monster", "voice", "Deep monster", "Lower and bigger, a little grit and a dark room.", [S("pitch", semitones=-7), S("formant", ratio=0.8), S("saturate", drive_db=8, kind="tube", mix=0.5), S("reverb", rt60=1.4, mix=0.2, size=0.6, damping=0.8)],
       [slider("depth", "depth", 0.55, (0, "semitones", -2, -12), (1, "ratio", 0.95, 0.65))], tags=("demon", "villain", "low voice", "giant"))
preset("robot", "voice", "Robot", "Ring-modulated and combed: a cold machine voice.", [S("ring_mod", freq=70, mix=0.85), S("echo", delay_ms=7, feedback=0.5, mix=0.4), S("bandpass", lo=150, hi=7000)],
       [slider("buzz", "buzz", 0.4, (0, "freq", 30, 220))], tags=("android", "vocoder", "cyborg", "ai voice"))
preset("ghost", "voice", "Ghost", "Pitched down, tremoring, in a long dark room.", [S("pitch", semitones=-3), S("tremolo", rate_hz=4.5, depth=0.35), S("highpass", fc=180), S("reverb", rt60=3.2, mix=0.5, size=0.9, damping=0.6)],
       [slider("haunt", "haunt", 0.5, (3, "mix", 0.2, 0.8))], tags=("spooky", "haunted", "whisper", "horror"))
preset("hard_tune", "voice", "Hard-tune (robot pop)", "Pitch pulled hard to the scale: the T-Pain-style effect, as a rough approximation.", [S("autotune", key=0, scale="pentatonic", strength=1.0, retune_ms=8), S("compress", thresh_db=-22, ratio=3, makeup_db=3)],
       [slider("strength", "strength", 1.0, (0, "strength", 0.2, 1.0)), slider("speed", "retune speed", 0.8, (0, "retune_ms", 120, 2))], tags=("autotune", "tuned", "pop vocal"))
preset("lofi", "look", "Lo-fi", "Dusty, wobbly, rolled-off.", [S("lofi", amount=0.6), S("vinyl", amount=0.3)], [slider("amount", "amount", 0.6, (0, "amount", 0, 1))], tags=("chill", "cassette", "nostalgic"))
preset("vinyl", "look", "Vinyl", "Crackle and warble.", [S("vinyl", amount=0.6)], [slider("amount", "dust", 0.6, (0, "amount", 0, 1))], tags=("record", "old", "dusty"))
preset("cassette", "look", "Cassette", "Tape wobble and hiss.", [S("tape", amount=0.6)], [slider("amount", "wear", 0.6, (0, "amount", 0, 1))], tags=("tape", "walkman", "80s"))
preset("eight_bit", "look", "8-bit / arcade", "Crushed to a few bits and a low sample rate.", [S("bitcrush", bits=6, hold=4), S("lowpass", fc=9000, order=2)],
       [slider("crush", "crush", 0.6, (0, "bits", 10, 3), (0, "hold", 1, 12))], tags=("chiptune", "retro", "game boy", "nes"))
preset("crushed", "look", "Crushed digital", "Harsh sample-rate reduction.", [S("bitcrush", bits=5, hold=10), S("saturate", drive_db=6, kind="hard", mix=0.5)], [slider("crush", "crush", 0.6, (0, "hold", 2, 30))], tags=("glitchy", "digital"))
preset("bass_boosted", "loud", "Bass boosted", "Heavy sub and low-mids, then limited.", [S("bass_boost", amount=0.8), S("compress", thresh_db=-16, ratio=4, makeup_db=2)],
       [slider("amount", "boost", 0.8, (0, "amount", 0.2, 1.0))], tags=("bass", "subwoofer", "boosted", "bass test"), loud=True, suggest_lufs=-12)
preset("blown_out", "loud", "Blown-out (loud meme, safety-limited)", "Hard-clipped, bass-heavy, bright: the 'ruined speaker' look. The limiter and a loudness cap still run, so it is loud but never painful.",
       [S("saturate", drive_db=26, kind="hard", mix=1.0), S("bass_boost", amount=0.8), S("high_shelf", fc=4000, gain_db=4), S("limit", ceiling_db=-3)],
       [slider("wreck", "wreck", 0.7, (0, "drive_db", 8, 40))], tags=("loud", "distorted", "ear rape", "bass boosted", "blown speaker", "fried"), loud=True, suggest_lufs=-11)
preset("fried", "loud", "Deep-fried", "Saturation, bit crush and a bright shelf: an over-processed meme look.", [S("saturate", drive_db=20, kind="tube"), S("bitcrush", bits=9, hold=2), S("high_shelf", fc=3500, gain_db=6)],
       [slider("fry", "fry", 0.6, (0, "drive_db", 6, 36))], tags=("deep fried", "crunchy", "over-compressed"), loud=True, suggest_lufs=-12)
preset("slowed_reverb", "time", "Slowed + reverb", "Slower, lower, in a large dreamy room.", [S("varispeed", semitones=-3), S("lowpass", fc=9000, order=2), S("reverb", rt60=2.6, mix=0.35, size=0.8, damping=0.7)],
       [slider("slow", "slowness", 0.35, (0, "semitones", -1, -8)), slider("wet", "reverb", 0.35, (2, "mix", 0.1, 0.7))], tags=("slowed", "chill", "dreamy", "phonk"))
preset("sped_up", "time", "Sped up", "Faster and higher (the sped-up edit sound).", [S("varispeed", semitones=3)], [slider("speed", "speed", 0.3, (0, "semitones", 1, 8))], tags=("nightcore", "fast", "speed up"))
preset("tape_stop", "time", "Tape stop", "The sound winds down to a halt at the end.", [S("tape_stop", start_s=0.4, stop_s=0.7)],
       [slider("stop", "wind-down", 0.4, (0, "stop_s", 0.15, 2.0))], tags=("record stop", "power down", "stop"))
preset("reverse_in", "time", "Reverse swell into the hit", "A backwards reverb tail that sucks into the sound.", [S("reverse_swell", rt60=1.8, mix=0.8)], [slider("length", "length", 0.4, (0, "rt60", 0.6, 3.5))], tags=("suck in", "pre-hit", "build"))
preset("backwards", "time", "Backwards", "Play it in reverse.", [S("reverse")], [], tags=("reverse", "reversed"))
preset("stutter_hit", "time", "Stutter hit", "A short stutter on the front.", [S("stutter", at_s=0.0, slice_ms=70, repeats=6, decay_db=1.0)],
       [slider("slice", "slice", 0.4, (0, "slice_ms", 25, 220)), slider("count", "repeats", 0.4, (0, "repeats", 3, 14))], tags=("glitch", "buh buh", "stammer"))
preset("glitched", "time", "Glitched", "Chopped, reversed and crushed at random (set by the seed).", [S("glitch", intensity=0.6)], [slider("mess", "mess", 0.6, (0, "intensity", 0.1, 1.0))], tags=("glitch", "corrupt"))
preset("pump", "time", "Sidechain pump", "The EDM duck-on-the-beat feel.", [S("sidechain", bpm=124, depth_db=10, release_s=0.18)],
       [slider("depth", "depth", 0.5, (0, "depth_db", 3, 20)), slider("tempo", "tempo", 0.4, (0, "bpm", 80, 170))], tags=("edm", "pump", "ducking"))
preset("helicopter", "time", "Chopped (helicopter)", "A fast rhythmic gate.", [S("chop", rate_hz=12, duty=0.45, smooth_ms=4)], [slider("rate", "rate", 0.4, (0, "rate_hz", 3, 28))], tags=("tremble", "stutter gate", "trance gate"))
preset("wide", "space", "Wide stereo", "A stereo width that folds to mono without loss.", [S("widen", width=0.7, delay_ms=17)], [slider("width", "width", 0.7, (0, "width", 0.1, 1.0))], tags=("stereo",))
preset("swirl", "space", "Swirl", "Chorus and a slow auto-pan.", [S("chorus", base_ms=16, depth_ms=4, rate_hz=0.4, mix=0.5), S("autopan", rate_hz=0.5, depth=0.6)], [slider("depth", "depth", 0.6, (1, "depth", 0.1, 1.0))], tags=("movement", "psychedelic"))
preset("wobble", "look", "Wobble", "Vibrato and tremolo together: drunk, dizzy.", [S("vibrato", rate_hz=4.5, depth_ms=1.3), S("tremolo", rate_hz=3, depth=0.3)], [slider("wobble", "wobble", 0.5, (0, "depth_ms", 0.3, 3.0))], tags=("dizzy", "drunk", "warble"))


def presets_public() -> list[dict]:
    return [{"id": p.id, "group": p.group, "label": p.label, "desc": p.desc, "tags": list(p.tags), "loud": p.loud, "suggest_lufs": p.suggest_lufs,
             "steps": [s["step"] for s in p.steps], "sliders": [{"id": s["id"], "label": s["label"], "default": s["default"]} for s in p.sliders]} for p in PRESETS.values()]


def steps_public() -> list[dict]:
    return [{"id": s.id, "group": s.group, "label": s.label, "desc": s.desc, "stereo": s.stereo,
             "params": {n: {"default": q.default, "min": q.lo, "max": q.hi, "label": q.label or n, "options": list(q.options), "integer": q.integer, "unit": q.unit}
                        for n, q in s.params.items()}} for s in STEPS.values()]


# =========================================================================== resolving and running
def _resolve_step_params(st: Step, given: dict | None, where: str, notes: list) -> dict:
    given = dict(given or {})
    out = {}
    for name, q in st.params.items():
        v = given.pop(name, q.default)
        if q.options:
            if v not in q.options:
                notes.append(f"{where}.{name}: {v!r} is not one of {list(q.options)}; used {q.default!r}")
                v = q.default
        else:
            try:
                fv = float(v)
            except (TypeError, ValueError):
                notes.append(f"{where}.{name}: {v!r} is not a number; used {q.default}")
                fv = float(q.default)
            if fv != fv or abs(fv) == float("inf"):
                fv = float(q.default)
            c = min(max(fv, q.lo), q.hi)
            if c != fv:
                notes.append(f"{where}.{name}: {fv:g} is outside {q.lo:g}..{q.hi:g}; used {c:g}")
            v = int(round(c)) if q.integer else c
        out[name] = v
    for extra in given:
        notes.append(f"{where}.{extra}: not a parameter of {st.id}; ignored")
    return out


def resolve_chain(raw) -> tuple[dict, list[str]]:
    """Validate a chain spec -> ({"preset", "sliders", "steps": [{"step", "params"}]} with every parameter filled and clamped, notes).
    Raises ChainError for an unknown preset or step (a typo must not become a silent no-op)."""
    notes: list[str] = []
    if raw in (None, "", {}):
        return {"preset": None, "sliders": {}, "steps": []}, notes
    if isinstance(raw, str):
        raw = {"preset": raw}
    if not isinstance(raw, dict):
        raise ChainError("chain must be an object {preset, sliders, steps}")
    pid = raw.get("preset")
    sliders_in = raw.get("sliders") if isinstance(raw.get("sliders"), dict) else {}
    steps: list[dict] = []
    sliders_out: dict = {}
    if pid:
        pre = PRESETS.get(str(pid))
        if pre is None:
            raise ChainError(f"unknown preset {pid!r}")
        base = [{"step": s["step"], "params": dict(s["params"])} for s in pre.steps]
        for sl in pre.sliders:
            v = sliders_in.get(sl["id"], sl["default"])
            try:
                v = min(max(float(v), 0.0), 1.0)
            except (TypeError, ValueError):
                v = sl["default"]
            sliders_out[sl["id"]] = round(v, 4)
            for t in sl["targets"]:
                if 0 <= t["step"] < len(base):
                    base[t["step"]]["params"][t["param"]] = t["lo"] + (t["hi"] - t["lo"]) * v
        for k in sliders_in:
            if k not in {s["id"] for s in pre.sliders}:
                notes.append(f"slider {k!r} is not a slider of {pre.id}; ignored")
        steps += base
    extra = raw.get("steps") or []
    if not isinstance(extra, list):
        raise ChainError("steps must be a list")
    steps += [s for s in extra if True]
    if len(steps) > MAX_STEPS:
        notes.append(f"a chain has at most {MAX_STEPS} steps; the rest were dropped")
        steps = steps[:MAX_STEPS]
    clean = []
    for i, s in enumerate(steps):
        if not isinstance(s, dict) or str(s.get("step")) not in STEPS:
            raise ChainError(f"step {i + 1}: unknown step {s.get('step') if isinstance(s, dict) else s!r} (one of {sorted(STEPS)})")
        st = STEPS[str(s["step"])]
        clean.append({"step": st.id, "params": _resolve_step_params(st, s.get("params"), f"{st.id}", notes)})
    return {"preset": str(pid) if pid else None, "sliders": sliders_out, "steps": clean}, notes


def run_chain(x: np.ndarray, chain: dict, seed: int = 1) -> np.ndarray:
    """Run a RESOLVED chain over audio. Mono in; a widen / auto-pan step makes stereo and later steps run per channel."""
    rng = D.rng_for(seed + 101)
    y = np.asarray(x, dtype=np.float64)
    for s in chain.get("steps", []):
        st = STEPS[s["step"]]
        if y.ndim == 2 and not st.stereo:
            ys = [st.fn(y[:, c], s["params"], D.rng_for(seed + 101 + c)) for c in range(y.shape[1])]
            n = min(len(a) for a in ys)
            y = np.stack([a[:n] for a in ys], axis=1)
        else:
            y = st.fn(y, s["params"], rng)
        y = np.nan_to_num(y)
        if y.shape[0] > MAX_OUT_S * SR:
            y = y[: int(MAX_OUT_S * SR)]
    return y


# =========================================================================== master
MASTER_DEFAULT = {"lufs": -14.0, "ceiling_db": -1.0, "trim": True, "loop": False, "fade_ms": 6.0, "stereo": False, "max_seconds": None}


def resolve_master(raw) -> tuple[dict, list[str]]:
    notes: list[str] = []
    m = dict(MASTER_DEFAULT)
    raw = raw if isinstance(raw, dict) else {}
    try:
        l = float(raw.get("lufs", m["lufs"]))
    except (TypeError, ValueError):
        l = m["lufs"]
    if not (-35.0 <= l <= D.MAX_LUFS):
        c = min(max(l, -35.0), D.MAX_LUFS)
        notes.append(f"master.lufs: {l:g} is outside -35..{D.MAX_LUFS:g}; used {c:g}")
        l = c
    m["lufs"] = l
    try:
        c = float(raw.get("ceiling_db", m["ceiling_db"]))
    except (TypeError, ValueError):
        c = m["ceiling_db"]
    if c > -0.5 or c < -12:
        notes.append(f"master.ceiling_db: {c:g} is outside -12..-0.5; used {min(max(c, -12), -0.5):g}")
        c = min(max(c, -12), -0.5)
    m["ceiling_db"] = c
    m["trim"] = bool(raw.get("trim", True))
    m["loop"] = bool(raw.get("loop", False))
    m["stereo"] = bool(raw.get("stereo", False))
    try:
        m["fade_ms"] = min(max(float(raw.get("fade_ms", 6.0)), 0.0), 500.0)
    except (TypeError, ValueError):
        pass
    ms = raw.get("max_seconds")
    if ms not in (None, ""):
        try:
            m["max_seconds"] = min(max(float(ms), 0.1), MAX_OUT_S)
        except (TypeError, ValueError):
            pass
    return m, notes


def finish(x: np.ndarray, master: dict) -> tuple[np.ndarray, dict]:
    """Trim, click-free edges, optional loop crossfade, loudness target, limiter. Always limits. Returns (audio, report)."""
    y = np.nan_to_num(np.asarray(x, dtype=np.float64))
    rep: dict = {}
    if master.get("max_seconds") and len(y) > master["max_seconds"] * SR:
        y = D.fade(y[: int(master["max_seconds"] * SR)], 0.0, 0.02)
        rep["cut_to_seconds"] = master["max_seconds"]
    if master.get("trim", True) and not master.get("loop"):
        y, head, tail = D.trim_silence(y, -55.0, 0.0, 0.03)
        rep["trimmed_s"] = {"head": round(head, 3), "tail": round(tail, 3)}
    if master.get("loop"):
        y = D.make_loop(y, 0.06)
        rep["loop"] = D.loop_seam(y)
    else:
        y = D.fade(y, 0.001, master.get("fade_ms", 6.0) / 1000)
    y, mrep = D.master(y, master["lufs"], master["ceiling_db"])
    if master.get("stereo") and y.ndim == 1:
        y = D.limit(D.widen(y, 0.5), master["ceiling_db"])
        rep["widen"] = "mono-safe side signal added"
    rep.update(mrep)
    rep["peak_db"] = round(D.peak_db(y), 2)
    return y, rep
