"""What a game gets when no model made it, or before one has: sound effects synthesised from sine waves and noise, a simple music loop, textures, title art and an icon. Everything here is drawn by code in this repo, is noted as such in the game's credits, and carries this repo's licence. Nothing here pretends to be a model's work."""
from __future__ import annotations

import math
import random
import struct
import subprocess
import wave
from pathlib import Path

import numpy as np

RATE = 22050


def _write(path: Path, x: np.ndarray, rate: int = RATE) -> Path:
    x = np.clip(x, -1.0, 1.0)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((x * 32000).astype("<i2").tobytes())
    return path


def _t(sec):
    return np.arange(int(sec * RATE)) / RATE


def _env(n, a=0.005, d=1.0):
    t = np.arange(n) / RATE
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(d, 1e-4))


def _sweep(f0, f1, sec, kind="sine"):
    t = _t(sec)
    f = f0 * (f1 / f0) ** (t / sec)
    ph = 2 * np.pi * np.cumsum(f) / RATE
    return np.sign(np.sin(ph)) * 0.6 if kind == "square" else np.sin(ph)


SFX = {
    "jump": lambda r: _sweep(280, 720, 0.18) * _env(int(0.18 * RATE), d=0.12) * 0.6,
    "land": lambda r: r.standard_normal(int(0.1 * RATE)) * _env(int(0.1 * RATE), d=0.03) * 0.5,
    "step": lambda r: r.standard_normal(int(0.05 * RATE)) * _env(int(0.05 * RATE), d=0.012) * 0.4,
    "coin": lambda r: np.concatenate([np.sin(2 * np.pi * 988 * _t(0.06)), np.sin(2 * np.pi * 1319 * _t(0.2)) * _env(int(0.2 * RATE), d=0.09)]) * 0.5,
    "star": lambda r: sum(np.pad(np.sin(2 * np.pi * f * _t(0.3)) * _env(int(0.3 * RATE), d=0.14), (int(i * 0.07 * RATE), int((3 - i) * 0.07 * RATE))) for i, f in enumerate((659, 784, 988, 1319))) * 0.4,
    "hurt": lambda r: _sweep(420, 110, 0.3, "square") * _env(int(0.3 * RATE), d=0.2) * 0.5,
    "zap": lambda r: _sweep(1500, 300, 0.11, "square") * _env(int(0.11 * RATE), d=0.06) * 0.4,
    "poof": lambda r: r.standard_normal(int(0.25 * RATE)) * _env(int(0.25 * RATE), d=0.08) * 0.45 + _sweep(600, 1400, 0.25) * _env(int(0.25 * RATE), d=0.06) * 0.3,
    "boost": lambda r: _sweep(200, 1000, 0.45) * _env(int(0.45 * RATE), a=0.02, d=0.3) * 0.55,
    "hit": lambda r: r.standard_normal(int(0.16 * RATE)) * _env(int(0.16 * RATE), d=0.05) * 0.6 + _sweep(180, 60, 0.16) * 0.4,
    "fall": lambda r: _sweep(900, 180, 0.7) * _env(int(0.7 * RATE), a=0.01, d=0.5) * 0.4,
    "click": lambda r: np.sin(2 * np.pi * 880 * _t(0.04)) * _env(int(0.04 * RATE), d=0.015) * 0.4,
    "talk": lambda r: np.sin(2 * np.pi * 520 * _t(0.09)) * _env(int(0.09 * RATE), d=0.04) * 0.35,
    "win": lambda r: sum(np.pad(np.sin(2 * np.pi * f * _t(0.5)) * _env(int(0.5 * RATE), d=0.3), (int(i * 0.14 * RATE), int((4 - i) * 0.14 * RATE))) for i, f in enumerate((523, 659, 784, 1047, 1319))) * 0.35,
    "lose": lambda r: sum(np.pad(np.sin(2 * np.pi * f * _t(0.6)) * _env(int(0.6 * RATE), d=0.4), (int(i * 0.22 * RATE), int((2 - i) * 0.22 * RATE))) for i, f in enumerate((392, 311, 233))) * 0.4,
}


def _engine() -> np.ndarray:
    """A motor loop: a whole number of cycles, so it has no click at the seam."""
    sec, base = 1.0, 60
    t = _t(sec)
    x = sum(a * np.sign(np.sin(2 * np.pi * base * h * t)) for h, a in ((1, 0.5), (2, 0.25), (3, 0.12)))
    return x * 0.5


def _wind() -> np.ndarray:
    """Soft air: smoothed noise, folded end over start so the loop has no seam."""
    r = np.random.default_rng(11)
    n = int(6 * RATE)
    fold = int(1.0 * RATE)
    x = r.standard_normal(n + fold)
    k = 60
    x = np.convolve(x, np.ones(k) / k, mode="same")
    swell = 0.7 + 0.3 * np.sin(np.linspace(0, 2 * np.pi * 3, n + fold))
    x = x * swell
    fade = np.linspace(0, 1, fold)
    x[:fold] = x[:fold] * fade + x[-fold:] * (1 - fade)
    x = x[:n]
    return x / max(np.abs(x).max(), 1e-6) * 0.5


def sfx_set(dest: Path, seed: int = 7) -> list[str]:
    """Write every effect as sfx_<name>.wav. -> the names."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    r = np.random.default_rng(seed)
    names = []
    for name, make in SFX.items():
        _write(dest / f"sfx_{name}.wav", make(r))
        names.append(name)
    _write(dest / "sfx_engine.wav", _engine())
    _write(dest / "sfx_wind.wav", _wind())
    return [*names, "engine", "wind"]


SCALES = {"minor": (0, 3, 5, 7, 10), "major": (0, 2, 4, 7, 9)}


def music_loop(dest: Path, *, seed: int = 1, bpm: int = 110, bars: int = 16, minor: bool = False) -> Path:
    """A small chiptune loop: chords, bass and a melody from a pentatonic scale. Not a model's work, and the credits say so. dest is a .wav."""
    r = random.Random(seed)
    beat = 60 / bpm
    bar = beat * 4
    n = int(bars * bar * RATE)
    out = np.zeros(n + RATE)
    scale = SCALES["minor" if minor else "major"]
    root = 48 + r.randrange(5)
    prog = r.choice([(0, 5, 3, 4), (0, 3, 5, 4), (0, 4, 5, 3)])

    def midi(m):
        return 440 * 2 ** ((m - 69) / 12)

    def put(start, sec, f, vol, shape="tri"):
        i = int(start * RATE)
        t = np.arange(int(sec * RATE)) / RATE
        ph = (t * f) % 1
        w = (np.abs(ph * 4 - 2) - 1) if shape == "tri" else np.where(ph < 0.5, 1.0, -1.0) * 0.5
        e = np.minimum(1, t / 0.006) * np.exp(-t * 3.0 / max(sec, 0.05))
        seg = w * e * vol
        end = min(i + len(seg), len(out))
        out[i:end] += seg[: end - i]

    for b in range(bars):
        s = b * bar
        deg = prog[b % 4]
        chord_root = root + deg + (0 if deg in (0, 5, 7) else 0)
        for k in range(8):
            put(s + k * beat / 2, beat * 0.45, midi(chord_root - 12 + (12 if k % 4 == 2 else 0)), 0.3)
        for k in (0, 2):
            for iv in (0, 4 if not minor else 3, 7):
                put(s + k * beat, beat * 1.8, midi(chord_root + 12 + iv), 0.08, "sq")
        if b >= 2:
            k = 0.0
            while k < 4:
                d = r.choice((0.5, 0.5, 1.0, 1.5))
                if r.random() < 0.8:
                    put(s + k * beat, d * beat * 0.9, midi(root + 24 + scale[r.randrange(len(scale))] + 12 * r.randrange(2)), 0.14)
                k += d
        for k in (0, 1, 2, 3):
            i = int((s + k * beat) * RATE)
            nl = int(0.06 * RATE)
            noise = np.random.default_rng(b * 7 + k).standard_normal(nl) * np.exp(-np.arange(nl) / (0.012 * RATE))
            end = min(i + nl, len(out))
            out[i:end] += noise[: end - i] * (0.18 if k % 2 else 0.1)
    return _write(Path(dest), out[:n] * 0.8)


def to_ogg(wav: Path, dest: Path, ffmpeg: str = "ffmpeg", seconds: float | None = None) -> Path:
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(wav), "-ac", "2", "-ar", "44100"]
    if seconds:
        cmd += ["-t", f"{seconds:.2f}"]
    cmd += ["-c:a", "libvorbis", "-q:a", "3", str(dest)]
    subprocess.run(cmd, check=True, timeout=180)
    return Path(dest)


def _hex(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return int(s[:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def title_art(dest: Path, palette: dict, *, seed: int = 1, size=(1280, 720)) -> Path:
    """A plain graded backdrop with hills: no lettering (the game draws its title in a font)."""
    from PIL import Image, ImageDraw
    r = random.Random(seed)
    w, h = size
    top, hor = np.array(_hex(palette.get("sky", "#335577"))), np.array(_hex(palette.get("horizon", "#ccddee")))
    g = np.linspace(0, 1, h)[:, None]
    grad = (top[None, :] * (1 - g) + hor[None, :] * g)
    img = Image.fromarray(np.repeat(grad[:, None, :], w, axis=1).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img)
    ground = np.array(_hex(palette.get("ground", "#556644")))
    for layer in range(4):
        base = h * (0.5 + layer * 0.13)
        amp = h * (0.13 - layer * 0.02)
        a, b = r.uniform(0.004, 0.009), r.uniform(0, 6.28)
        pts = [(0, h)] + [(x, base + amp * math.sin(x * a + b) + amp * 0.3 * math.sin(x * a * 3.1 + b)) for x in range(0, w + 20, 20)] + [(w, h)]
        c = (hor * (0.75 - layer * 0.25) + ground * (0.25 + layer * 0.25)).astype(int)
        d.polygon(pts, fill=tuple(int(v) for v in c))
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")
    return Path(dest)


def sky_art(dest: Path, palette: dict, *, seed: int = 1, size=(2048, 1024)) -> Path:
    """A sky drawn by code: a gradient with soft clouds that wraps round, for when no model made one."""
    from PIL import Image
    from studio.worldkit import textures as T
    w, h = size
    top, hor = np.array(_hex(palette.get("sky", "#335577")), dtype=np.float32), np.array(_hex(palette.get("horizon", "#ccddee")), dtype=np.float32)
    g = np.clip(np.linspace(0, 1, h) / 0.5, 0, 1)[:, None, None] ** 1.6
    px = np.repeat(top[None, None, :] * (1 - g) + hor[None, None, :] * g, w, axis=1)
    n = T._fractal(np.random.default_rng(seed), w)
    cloud = np.clip((n[: h, :] - 0.55) * 4, 0, 1)[:, :, None] * (np.linspace(0, 1, h)[:, None, None] < 0.5)
    px = px * (1 - cloud * 0.7) + 245 * cloud * 0.7
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(px, 0, 255).astype(np.uint8), "RGB").save(dest, "PNG")
    return Path(dest)


def sky_from_picture(src: Path, dest: Path, size=(2048, 1024)) -> tuple[Path, dict]:
    """A model's picture made into a panorama: its ends cross-faded so it wraps, the top melted into one colour so the pole doesn't pinch, and a mirrored sea of cloud under the horizon. -> (file, the colours found in the sky and overhead, so fog can match)."""
    from PIL import Image, ImageFilter
    w, h = size
    with Image.open(src) as im:
        a = np.asarray(im.convert("RGB").resize((w, h), Image.LANCZOS), dtype=np.float32).copy()
    fold = w // 8
    fade = np.linspace(0, 1, fold)[None, :, None]
    a[:, :fold] = a[:, :fold] * fade + a[:, -fold:][:, ::1] * (1 - fade)
    a = np.array(Image.fromarray(a[:, : w - fold].astype(np.uint8), "RGB").resize((w, h), Image.LANCZOS), dtype=np.float32)
    upper = a[int(h * 0.15): int(h * 0.42)]
    horizon = upper.mean(axis=(0, 1))
    zenith = a[: int(h * 0.06)].mean(axis=(0, 1))
    y = np.linspace(0, 1, h)[:, None, None]
    # Under the horizon the sky goes on: the top half mirrored and softened, a sea of cloud. Ground, where a kit has any, hides it; islands float in it.
    half = h // 2
    below = np.array(Image.fromarray(a[half - (h - half): half][::-1].astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(6)), dtype=np.float32)
    a[half:] = below * 0.8 + horizon * 0.2
    band = np.exp(-((y - 0.5) / 0.05) ** 2)
    a = a * (1 - band * 0.8) + horizon * band * 0.8
    high = np.clip((0.12 - y) / 0.12, 0, 1)
    a = a * (1 - high) + zenith * high
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB").save(dest, "PNG")
    tohex = lambda c: "#%02x%02x%02x" % tuple(int(v) for v in c)
    return Path(dest), {"horizon": tohex(horizon), "sky": tohex(zenith)}


def icon(dest: Path, palette: dict) -> Path:
    from PIL import Image, ImageDraw
    a = _hex(palette.get("accent", "#f5c518"))
    img = Image.new("RGB", (256, 256), (9, 9, 10))
    d = ImageDraw.Draw(img)
    d.polygon([(128, 30), (150, 100), (226, 100), (165, 145), (188, 220), (128, 175), (68, 220), (91, 145), (30, 100), (106, 100)], fill=a)
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")
    return Path(dest)


def texture(what: str, dest: Path, seed: int = 0, tint: str | None = None, size: int = 512) -> Path:
    """A tiling surface. World Kit's procedural maker for what it knows; a tinted noise otherwise, in the setting's own colour."""
    from PIL import Image
    from studio.worldkit import textures as T
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    words = str(what or "").lower()
    if any(w for w, _ in T.WORDS if w in words):
        T.procedural(what, dest, size=size, seed=seed)
        return dest
    rng = np.random.default_rng(seed)
    n = T._fractal(rng, size)
    base = np.array(_hex(tint or "#778877"), dtype=np.float32)
    px = base[None, None, :] * (0.72 + 0.56 * n[:, :, None])
    Image.fromarray(np.clip(px, 0, 255).astype(np.uint8), "RGB").save(dest, "PNG")
    return dest
