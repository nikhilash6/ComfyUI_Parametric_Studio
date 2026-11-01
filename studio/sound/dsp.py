"""Sound DSP for the 🔊 Sound maker: numpy only (plus the stdlib `wave`, and ffmpeg for decoding and mp3). No scipy, no soundfile, no
torch and no model, so every function here works on the studio server's own venv (which has numpy and nothing else audio-ish) with
no GPU. Audio is a float64 numpy array at SR, mono (n,) while it is being made, or stereo (n, 2) after the optional widen step.

What is in here
  I/O          decode (any file -> array via ffmpeg), read_wav / write_wav (16 or 24 bit), encode_mp3
  generators   osc (sine / saw / square / triangle, polyBLEP), noise (white / pink / brown / blue), envelopes and curves
  filters      zero-phase FFT filters (lowpass / highpass / bandpass / notch / peak / shelf), a time-varying filter sweep
  spectral     stft / istft, phase-vocoder time stretch, pitch shift, formant shift, f0 tracking, "autotune-ish" pitch snap
  effects      distortion, bitcrush, echo, reverb (synthesised impulse response), chorus / flanger / vibrato / tremolo, ring mod,
               tape stop, stutter, glitch, reverse, sidechain pump, compressor, gate, stereo widen (mono-sum safe)
  measuring    peak, true peak (4x oversampled), K-weighted loudness (ITU-R BS.1770 shape, gated; checked against ffmpeg's ebur128 in
               the tests), silence trim, onset / attack time, silence gaps, loop seam, tempo guess, stereo mono-compat
  safety       limit() (look-ahead brick wall that also holds the true peak) and master() (loudness target with a cap)

Everything is deterministic for a given seed. Nothing here touches the network, a model or a port.
"""
from __future__ import annotations

import math
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100
EPS = 1e-12
MAX_SECONDS = 60.0                      # decode / render ceiling for one clip


class DSPError(ValueError):
    """Reported to the user as a message."""


# --------------------------------------------------------------------------- small helpers
def db(x: float) -> float:
    return 20.0 * math.log10(max(float(x), EPS))


def lin(d: float) -> float:
    return 10.0 ** (float(d) / 20.0)


def rng_for(seed) -> np.random.Generator:
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def n_of(seconds: float, sr: int = SR) -> int:
    return max(1, int(round(float(seconds) * sr)))


def next_pow2(n: int) -> int:
    return 1 << max(1, int(n - 1).bit_length())


def peak(x: np.ndarray) -> float:
    return float(np.max(np.abs(x))) if x.size else 0.0


def peak_db(x: np.ndarray) -> float:
    return db(peak(x))


def rms_db(x: np.ndarray) -> float:
    return db(math.sqrt(float(np.mean(np.square(x)))) if x.size else 0.0)


def to_mono(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=1) if x.ndim == 2 else x


def per_channel(fn, x: np.ndarray, *a, **k) -> np.ndarray:
    """Apply a mono function to each channel of a stereo array (the same length out for both is the caller's job)."""
    if x.ndim == 1:
        return fn(x, *a, **k)
    ys = [fn(x[:, c], *a, **k) for c in range(x.shape[1])]
    n = min(len(y) for y in ys)
    return np.stack([y[:n] for y in ys], axis=1)


def fit_len(x: np.ndarray, n: int) -> np.ndarray:
    if x.shape[0] >= n:
        return x[:n]
    pad = [(0, n - x.shape[0])] + [(0, 0)] * (x.ndim - 1)
    return np.pad(x, pad)


def fade(x: np.ndarray, in_s: float = 0.0, out_s: float = 0.0, sr: int = SR) -> np.ndarray:
    """Raised-cosine fades (never a click at the cut)."""
    y = x.copy()
    n = y.shape[0]
    a = min(n, int(in_s * sr))
    b = min(n, int(out_s * sr))
    shape = (-1,) + (1,) * (y.ndim - 1)
    if a > 1:
        y[:a] *= (0.5 - 0.5 * np.cos(np.linspace(0, math.pi, a))).reshape(shape)
    if b > 1:
        y[n - b:] *= (0.5 + 0.5 * np.cos(np.linspace(0, math.pi, b))).reshape(shape)
    return y


def mix_at(parts: list[tuple[np.ndarray, int, float]], n: int) -> np.ndarray:
    """Sum (audio, start_sample, gain_db) onto a silent bed of n samples (stereo if any part is stereo)."""
    stereo = any(p.ndim == 2 for p, _, _ in parts)
    out = np.zeros((n, 2) if stereo else (n,))
    for p, at, g in parts:
        if stereo and p.ndim == 1:
            p = np.stack([p, p], axis=1)
        at = max(0, int(at))
        end = min(n, at + p.shape[0])
        if end > at:
            out[at:end] += p[: end - at] * lin(g)
    return out


# --------------------------------------------------------------------------- I/O
def ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or str(Path.home() / ".local" / "bin" / "ffmpeg")


def decode(path, *, sr: int = SR, channels: int = 1, max_seconds: float = MAX_SECONDS, start: float = 0.0, run=None) -> np.ndarray:
    """Any audio (or video) file -> float64 array at `sr` via ffmpeg (f32le on a pipe), from `start` seconds for at most `max_seconds`.
    Raises DSPError when it cannot be read."""
    run = run or subprocess.run
    p = run([ffmpeg_bin(), "-nostdin", "-hide_banner", "-v", "error", "-ss", f"{max(0.0, start):.3f}", "-i", str(path), "-vn", "-t", f"{max_seconds:.3f}",
             "-ac", str(channels), "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, timeout=180)
    if p.returncode != 0 or not p.stdout:
        raise DSPError(f"could not read {Path(str(path)).name}: {(p.stderr or b'')[-200:].decode('utf-8', 'replace')}")
    x = np.frombuffer(p.stdout, dtype="<f4").astype(np.float64)
    if channels == 2:
        x = x[: len(x) // 2 * 2].reshape(-1, 2)
    if not np.all(np.isfinite(x)):
        x = np.nan_to_num(x)
    return x


def write_wav(path, x: np.ndarray, sr: int = SR, bits: int = 16) -> Path:
    """Write mono / stereo float audio as PCM (16 or 24 bit). Clipped to [-1, 1]; never normalised here."""
    if bits not in (16, 24):
        raise DSPError("bits must be 16 or 24")
    x = np.clip(np.nan_to_num(np.asarray(x, dtype=np.float64)), -1.0, 1.0)
    ch = 1 if x.ndim == 1 else x.shape[1]
    scale = float(2 ** (bits - 1) - 1)
    q = np.round(x * scale).astype("<i4")
    raw = q.astype("<i2").tobytes() if bits == 16 else q.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.part")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(bits // 8)
        w.setframerate(int(sr))
        w.writeframes(raw)
    tmp.replace(path)
    return path


def read_wav(path) -> tuple[np.ndarray, int]:
    """Read a PCM wav (16 / 24 / 32 bit) with the stdlib. Returns (float64 array mono or (n, ch), sample rate)."""
    with wave.open(str(path), "rb") as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        a = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v & 0x800000, v - 0x1000000, v)
        a = v.astype(np.float64) / 8388608.0
    elif sw == 4:
        a = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise DSPError(f"{sw * 8}-bit wav is not supported")
    return (a if ch == 1 else a[: len(a) // ch * ch].reshape(-1, ch)), sr


def encode_mp3(src, dest, *, run=None, quality: int = 2) -> Path:
    run = run or subprocess.run
    p = run([ffmpeg_bin(), "-nostdin", "-v", "error", "-y", "-i", str(src), "-c:a", "libmp3lame", "-q:a", str(int(quality)), str(dest)],
            capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise DSPError(f"mp3 encode failed: {(p.stderr or '')[-200:]}")
    return Path(dest)


# --------------------------------------------------------------------------- generators
def _blep(p: np.ndarray, dt: np.ndarray) -> np.ndarray:
    out = np.zeros_like(p)
    m = p < dt
    if m.any():
        t = p[m] / dt[m]
        out[m] = t + t - t * t - 1.0
    m = p > 1.0 - dt
    if m.any():
        t = (p[m] - 1.0) / dt[m]
        out[m] = t * t + t + t + 1.0
    return out


def osc(kind: str, freq, n: int | None = None, sr: int = SR, phase0: float = 0.0, width: float = 0.5) -> np.ndarray:
    """One oscillator. `freq` is a number or an array of Hz per sample (a sweep). kind: sine | saw | square | tri."""
    f = np.asarray(freq, dtype=np.float64)
    if f.ndim == 0:
        f = np.full(int(n or 0), float(f))
    ph = phase0 + np.cumsum(f) / sr
    p = ph % 1.0
    dt = np.clip(np.abs(f) / sr, 1e-6, 0.49)
    if kind == "sine":
        return np.sin(2 * math.pi * ph)
    if kind == "saw":
        return 2.0 * p - 1.0 - _blep(p, dt)
    if kind == "square":
        w = float(np.clip(width, 0.05, 0.95))
        return np.where(p < w, 1.0, -1.0) + _blep(p, dt) - _blep((p - w) % 1.0, dt)
    if kind in ("tri", "triangle"):
        return 2.0 * np.abs(2.0 * p - 1.0) - 1.0
    raise DSPError(f"unknown oscillator {kind!r}")


def noise(kind: str, n: int, rng: np.random.Generator) -> np.ndarray:
    """Noise at unit RMS: white | pink | brown | blue | violet."""
    w = rng.standard_normal(n)
    if kind == "white":
        return w
    X = np.fft.rfft(w)
    f = np.maximum(np.fft.rfftfreq(n, 1.0 / SR), 20.0)
    shape = {"pink": f ** -0.5, "brown": f ** -1.0, "blue": f ** 0.5, "violet": f ** 1.0}.get(kind)
    if shape is None:
        raise DSPError(f"unknown noise {kind!r}")
    y = np.fft.irfft(X * shape, n)
    return y / max(float(np.sqrt(np.mean(y * y))), EPS)


def curve(points, n: int, sr: int = SR, *, log: bool = False) -> np.ndarray:
    """A control curve of n samples through [(seconds, value), ...]. log=True interpolates in log space (pitch / filter sweeps)."""
    pts = sorted((float(t), float(v)) for t, v in points)
    ts = np.array([t * sr for t, _ in pts])
    vs = np.array([v for _, v in pts])
    i = np.arange(n)
    if log:
        return np.exp(np.interp(i, ts, np.log(np.maximum(vs, 1e-9))))
    return np.interp(i, ts, vs)


def exp_decay(n: int, tau_s: float, sr: int = SR) -> np.ndarray:
    return np.exp(-np.arange(n) / (max(tau_s, 1e-4) * sr))


def adsr(n: int, a: float, d: float, s: float, r: float, sr: int = SR) -> np.ndarray:
    """Attack / decay / sustain-level / release envelope over n samples (r is the release at the end)."""
    na, nd, nr = int(a * sr), int(d * sr), int(r * sr)
    env = np.ones(n) * s
    na = min(na, n)
    if na:
        env[:na] = np.linspace(0, 1, na, endpoint=False)
    nd = min(nd, max(0, n - na))
    if nd:
        env[na:na + nd] = np.linspace(1, s, nd)
    nr = min(nr, n)
    if nr:
        env[n - nr:] *= np.linspace(1, 0, nr)
    return env


def read_at(x: np.ndarray, pos: np.ndarray) -> np.ndarray:
    """Cubic (Catmull-Rom) read of x at fractional sample positions; outside the clip is silence."""
    n = len(x)
    i = np.floor(pos).astype(np.int64)
    f = pos - i
    def g(k):
        j = i + k
        return np.where((j >= 0) & (j < n), x[np.clip(j, 0, n - 1)], 0.0)
    xm1, x0, x1, x2 = g(-1), g(0), g(1), g(2)
    a = -0.5 * xm1 + 1.5 * x0 - 1.5 * x1 + 0.5 * x2
    b = xm1 - 2.5 * x0 + 2.0 * x1 - 0.5 * x2
    c = -0.5 * xm1 + 0.5 * x1
    return ((a * f + b) * f + c) * f + x0


# --------------------------------------------------------------------------- filters (zero phase, FFT domain)
def _fft_apply(x: np.ndarray, resp, sr: int = SR) -> np.ndarray:
    n = len(x)
    nfft = next_pow2(2 * n)
    X = np.fft.rfft(x, nfft)
    f = np.fft.rfftfreq(nfft, 1.0 / sr)
    return np.fft.irfft(X * resp(f), nfft)[:n]


def _bw_lp(f: np.ndarray, fc: float, order: int) -> np.ndarray:
    return 1.0 / np.sqrt(1.0 + (np.maximum(f, 1e-9) / max(fc, 1.0)) ** (2 * order))


def lowpass(x, fc, order=4, sr=SR, res_db=0.0):
    def resp(f):
        r = _bw_lp(f, fc, order)
        if res_db:
            r = r * (1.0 + (lin(res_db) - 1.0) * np.exp(-0.5 * (np.log2(np.maximum(f, 1.0) / fc) / 0.12) ** 2))
        return r
    return _fft_apply(x, resp, sr)


def highpass(x, fc, order=4, sr=SR):
    return _fft_apply(x, lambda f: np.sqrt(1.0 - _bw_lp(f, fc, order) ** 2), sr)


def bandpass(x, lo, hi, order=3, sr=SR):
    return _fft_apply(x, lambda f: _bw_lp(f, hi, order) * np.sqrt(1.0 - _bw_lp(f, lo, order) ** 2), sr)


def notch(x, fc, q=4.0, sr=SR):
    return _fft_apply(x, lambda f: 1.0 - np.exp(-0.5 * (np.log2(np.maximum(f, 1.0) / fc) * q) ** 2), sr)


def eq_peak(x, fc, gain_db, q=1.0, sr=SR):
    g = lin(gain_db) - 1.0
    return _fft_apply(x, lambda f: 1.0 + g * np.exp(-0.5 * (np.log2(np.maximum(f, 1.0) / fc) * q * 2.0) ** 2), sr)


def shelf(x, fc, gain_db, kind="low", sr=SR):
    g = lin(gain_db)
    def resp(f):
        s = 0.5 * (1.0 + np.tanh(2.2 * np.log2(np.maximum(f, 1.0) / fc)))       # 0 below fc -> 1 above
        return (g * (1.0 - s) + s) if kind == "low" else (1.0 - s + g * s)
    return _fft_apply(x, resp, sr)


# --------------------------------------------------------------------------- STFT and what builds on it
def stft(x: np.ndarray, n_fft: int = 2048, hop: int = 512) -> np.ndarray:
    xp = np.pad(x, (n_fft // 2, n_fft + n_fft // 2))
    nf = 1 + (len(xp) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(nf)[:, None]
    w = np.hanning(n_fft + 1)[:-1]
    return np.fft.rfft(xp[idx] * w, axis=1)


def istft(S: np.ndarray, n_fft: int, hop: int, length: int) -> np.ndarray:
    w = np.hanning(n_fft + 1)[:-1]
    frames = np.fft.irfft(S, n_fft, axis=1) * w
    out = np.zeros(hop * (len(S) - 1) + n_fft)
    norm = np.zeros_like(out)
    for i in range(len(S)):
        out[i * hop:i * hop + n_fft] += frames[i]
        norm[i * hop:i * hop + n_fft] += w * w
    out /= np.maximum(norm, 1e-6)
    return out[n_fft // 2:n_fft // 2 + length]


def sweep_filter(x, fc, kind="lowpass", order=2, res_db=0.0, sr=SR, n_fft=2048, hop=512):
    """A filter whose cutoff moves over time. `fc` is an array of Hz per sample (use curve(..., log=True))."""
    S = stft(x, n_fft, hop)
    f = np.fft.rfftfreq(n_fft, 1.0 / sr)
    centres = np.clip(np.arange(len(S)) * hop - n_fft // 2 + n_fft // 2, 0, len(x) - 1)
    fcs = np.asarray(fc, dtype=np.float64)[np.clip(centres, 0, len(fc) - 1)][:, None]
    r = 1.0 / np.sqrt(1.0 + (np.maximum(f[None, :], 1e-9) / np.maximum(fcs, 20.0)) ** (2 * order))
    if kind == "highpass":
        r = np.sqrt(np.maximum(0.0, 1.0 - r * r))
    if res_db:
        r = r * (1.0 + (lin(res_db) - 1.0) * np.exp(-0.5 * (np.log2(np.maximum(f[None, :], 1.0) / np.maximum(fcs, 20.0)) / 0.15) ** 2))
    return istft(S * r, n_fft, hop, len(x))


def time_stretch(x: np.ndarray, rate: float, n_fft: int = 2048, hop: int = 512) -> np.ndarray:
    """Phase-vocoder stretch: rate > 1 is faster / shorter, pitch kept. Smears sharp transients a little (use varispeed for hits)."""
    if abs(rate - 1.0) < 1e-4 or len(x) < n_fft:
        return x.copy()
    S = stft(x, n_fft, hop)
    mag, ang = np.abs(S), np.angle(S)
    steps = np.arange(0, len(S) - 1, rate)
    omega = 2 * math.pi * hop * np.arange(S.shape[1]) / n_fft
    phi = ang[0].copy()
    out = np.empty((len(steps), S.shape[1]), dtype=np.complex128)
    for k, t in enumerate(steps):
        i = int(t)
        fr = t - i
        m = (1 - fr) * mag[i] + fr * mag[i + 1]
        out[k] = m * np.exp(1j * phi)
        d = ang[i + 1] - ang[i] - omega
        d -= 2 * math.pi * np.round(d / (2 * math.pi))
        phi = phi + omega + d
    return istft(out, n_fft, hop, int(round(len(x) / rate)))


def varispeed(x: np.ndarray, rate, n_out: int | None = None) -> np.ndarray:
    """Play x back at a time-varying speed (`rate` per OUTPUT sample; 1 = normal, 2 = octave up and half as long, 0 = frozen)."""
    r = np.asarray(rate, dtype=np.float64)
    if r.ndim == 0:
        n_out = n_out or int(len(x) / max(float(r), 1e-3))
        r = np.full(n_out, float(r))
    pos = np.concatenate([[0.0], np.cumsum(r[:-1])])
    if n_out is None:
        n_out = len(r)
    keep = pos < len(x)
    y = read_at(x, pos[:n_out])
    if not keep[:n_out].all():
        y[~keep[:n_out]] = 0.0
    return y


def resample_ratio(x: np.ndarray, ratio: float) -> np.ndarray:
    """ratio > 1 reads faster (higher, shorter). Low-passes first when it would alias."""
    if abs(ratio - 1.0) < 1e-6:
        return x.copy()
    y = lowpass(x, 0.45 * SR / ratio, order=6) if ratio > 1.0 else x
    return varispeed(y, ratio, int(len(x) / ratio))


def pitch_shift(x: np.ndarray, semitones: float, keep_duration: bool = True) -> np.ndarray:
    """Shift pitch by semitones. keep_duration=False is plain varispeed (the classic chipmunk / slowed sound)."""
    ratio = 2.0 ** (semitones / 12.0)
    if abs(semitones) < 1e-3:
        return x.copy()
    y = resample_ratio(x, ratio)
    return fit_len(time_stretch(y, len(y) / len(x)), len(x)) if keep_duration else y


def formant_shift(x: np.ndarray, ratio: float, n_fft: int = 2048, hop: int = 512, lifter: int = 44) -> np.ndarray:
    """Move the spectral envelope (the 'vocal tract') by `ratio` and leave the pitch: ratio < 1 deeper / bigger, > 1 smaller / chipmunky."""
    if abs(ratio - 1.0) < 1e-3:
        return x.copy()
    S = stft(x, n_fft, hop)
    mag = np.abs(S) + 1e-9
    cep = np.fft.irfft(np.log(mag), n_fft, axis=1)
    cep[:, lifter:n_fft - lifter] = 0.0
    env = np.exp(np.fft.rfft(cep, axis=1).real)
    k = np.arange(S.shape[1])
    src = np.clip(k / ratio, 0, S.shape[1] - 1)
    i0 = np.floor(src).astype(int)
    i1 = np.minimum(i0 + 1, S.shape[1] - 1)
    fr = src - i0
    env_w = env[:, i0] * (1 - fr) + env[:, i1] * fr
    return istft(S / env * env_w, n_fft, hop, len(x))


def f0_track(x: np.ndarray, sr: int = SR, fmin: float = 70.0, fmax: float = 900.0, frame: int = 2048, hop: int = 512) -> tuple[np.ndarray, np.ndarray]:
    """(f0 per frame in Hz, 0 where unvoiced; the frame centre sample). Autocorrelation with parabolic refinement."""
    xp = np.pad(x, (frame // 2, frame))
    nf = 1 + (len(xp) - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(nf)[:, None]
    fr = xp[idx] * np.hanning(frame)
    spec = np.fft.rfft(fr, 2 * frame, axis=1)
    ac = np.fft.irfft(np.abs(spec) ** 2, axis=1)[:, :frame]
    ac /= np.maximum(ac[:, :1], 1e-9)
    lo, hi = int(sr / fmax), int(sr / fmin)
    seg = ac[:, lo:hi]
    k = np.argmax(seg, axis=1)
    val = seg[np.arange(nf), k]
    lag = (k + lo).astype(np.float64)
    ki = np.clip(k + lo, 1, frame - 2)
    a, b, c = ac[np.arange(nf), ki - 1], ac[np.arange(nf), ki], ac[np.arange(nf), ki + 1]
    den = a - 2 * b + c
    shift = 0.5 * (a - c) / np.where(np.abs(den) > 1e-9, den, 1.0) * (np.abs(den) > 1e-9)
    f0 = sr / (lag + shift)
    energy = np.sqrt(np.mean(fr ** 2, axis=1))
    voiced = (val > 0.5) & (energy > 0.01 * max(float(energy.max()), 1e-9))
    return np.where(voiced, f0, 0.0), np.arange(nf) * hop


SCALES = {"chromatic": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), "major": (0, 2, 4, 5, 7, 9, 11), "minor": (0, 2, 3, 5, 7, 8, 10),
          "pentatonic": (0, 2, 4, 7, 9), "minor_pentatonic": (0, 3, 5, 7, 10), "blues": (0, 3, 5, 6, 7, 10)}
NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def snap_midi(m: np.ndarray, key: int, scale: str) -> np.ndarray:
    degrees = np.array(SCALES[scale])
    cand = np.concatenate([(key + degrees + 12 * o) for o in range(-1, 11)])
    cand = np.sort(cand)
    j = np.abs(m[:, None] - cand[None, :]).argmin(axis=1)
    return cand[j]


def pitch_snap(x: np.ndarray, key: int = 0, scale: str = "major", strength: float = 1.0, retune_ms: float = 20.0, sr: int = SR) -> np.ndarray:
    """"Autotune-ish": detect the pitch per frame, move it toward the nearest scale note (strength 0..1, retune_ms = how fast), keep the length.
    A rough method (varispeed + phase-vocoder length repair): good for the robotic hard-tune meme sound, not a transparent corrector."""
    if scale not in SCALES:
        raise DSPError(f"scale must be one of {sorted(SCALES)}")
    f0, centres = f0_track(x, sr)
    v = f0 > 0
    if not v.any():
        return x.copy()
    midi = np.where(v, 69 + 12 * np.log2(np.maximum(f0, 1.0) / 440.0), 0.0)
    for i in range(1, len(midi) - 1):                                  # median of 3 on voiced runs
        if v[i - 1] and v[i] and v[i + 1]:
            midi[i] = float(np.median(midi[i - 1:i + 2]))
    target = np.where(v, snap_midi(np.where(v, midi, 60.0), int(key) % 12, scale), 0.0)
    shift_st = np.where(v, (target - midi) * float(np.clip(strength, 0.0, 1.0)), 0.0)
    a = math.exp(-512.0 / sr / max(retune_ms / 1000.0, 1e-3))          # one-pole retune speed per hop
    sm = np.zeros_like(shift_st)
    for i in range(len(shift_st)):
        sm[i] = shift_st[i] * (1 - a) + (sm[i - 1] * a if i else 0.0)
    ratio = 2.0 ** (np.interp(np.arange(len(x)), centres, sm) / 12.0)
    y = varispeed(x, ratio, len(x))
    used = float(np.sum(ratio))                                        # input samples consumed
    y = y[: max(1, int(len(x)))]
    return fit_len(time_stretch(y, len(y) / max(len(x), 1)), len(x)) if used > 0 else y


# --------------------------------------------------------------------------- effects
def distort(x, drive_db=12.0, kind="tanh", mix=1.0, bias=0.0):
    g = lin(drive_db)
    if kind == "tanh":
        y = np.tanh(g * x + bias)
    elif kind == "hard":
        y = np.clip(g * x + bias, -1.0, 1.0)
    elif kind == "fold":
        y = np.sin(0.5 * math.pi * g * x + bias)
    elif kind == "tube":
        z = g * x + bias
        y = np.where(z >= 0, np.tanh(z), 0.6 * np.tanh(1.8 * z))
    else:
        raise DSPError(f"unknown distortion {kind!r}")
    return mix * y + (1 - mix) * x


def bitcrush(x, bits=8, hold=1):
    y = x
    if hold > 1:
        n = len(y)
        y = np.repeat(y[::hold], hold)[:n]
    if bits < 16:
        q = 2.0 ** (bits - 1)
        y = np.round(y * q) / q
    return y


def echo(x, delay_s=0.25, feedback=0.4, mix=0.5, repeats=6, tail=True, sr=SR):
    d = max(1, int(delay_s * sr))
    n = len(x) + (d * repeats if tail else 0)
    wet = np.zeros(n)
    for k in range(1, repeats + 1):
        g = feedback ** k
        if g < 1e-3:
            break
        end = min(n, k * d + len(x))
        wet[k * d:end] += x[: end - k * d] * g
    dry = np.zeros(n)
    dry[:len(x)] = x
    return dry + mix * wet


def fftconvolve(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    n = len(a) + len(b) - 1
    nfft = next_pow2(n)
    return np.fft.irfft(np.fft.rfft(a, nfft) * np.fft.rfft(b, nfft), nfft)[:n]


def impulse_response(rt60=1.2, size=0.5, damping=0.5, predelay_ms=8.0, seed=1, sr=SR) -> np.ndarray:
    """A synthetic room: sparse early reflections, then noise that decays faster in the highs (damping 0..1). Unit energy."""
    rng = rng_for(seed)
    n = int(min(max(rt60, 0.05), 8.0) * 1.15 * sr)
    t = np.arange(n) / sr
    bands = [(0, 400, 1.15), (400, 3000, 1.0), (3000, 12000, 1.0 - 0.7 * damping), (12000, 21000, 1.0 - 0.9 * damping)]
    ir = np.zeros(n)
    base = rng.standard_normal(n)
    for lo, hi, m in bands:
        b = bandpass(base, max(lo, 20), hi, order=2) if lo else lowpass(base, hi, order=2)
        ir += b * np.exp(-6.91 * t / max(rt60 * m, 0.03))
    early = int((0.012 + 0.05 * size) * sr)
    ir[:early] *= np.linspace(0.2, 1.0, early)
    for k in range(8):                                                 # early reflections
        at = int((0.004 + 0.055 * size * rng.random()) * sr)
        if at < n:
            ir[at] += (0.6 - 0.05 * k) * rng.choice([-1.0, 1.0]) * np.sqrt(np.mean(ir ** 2)) * 6
    ir = np.concatenate([np.zeros(int(predelay_ms / 1000 * sr)), ir])
    return ir / max(float(np.sqrt(np.sum(ir ** 2))), EPS)


def reverb(x, rt60=1.2, mix=0.3, size=0.5, damping=0.5, predelay_ms=8.0, seed=1, tail=True, sr=SR):
    ir = impulse_response(rt60, size, damping, predelay_ms, seed, sr)
    wet = fftconvolve(x, ir)
    # wet is scaled so that a steady input keeps its loudness
    wet *= math.sqrt(np.sum(x ** 2) / max(np.sum(wet[: len(x)] ** 2), EPS)) if np.sum(x ** 2) > 0 else 1.0
    n = len(wet) if tail else len(x)
    dry = np.zeros(len(wet))
    dry[:len(x)] = x
    return (np.sqrt(1 - mix) * dry + np.sqrt(mix) * wet)[:n]


def mod_delay(x, base_ms=8.0, depth_ms=3.0, rate_hz=0.4, mix=0.5, sr=SR, phase=0.0):
    """Chorus (base 15-30 ms, depth 2-5) / flanger (base 1-5 ms, depth 1-3) / vibrato (mix 1) from one modulated delay line."""
    i = np.arange(len(x))
    d = (base_ms + depth_ms * np.sin(2 * math.pi * rate_hz * i / sr + phase)) * sr / 1000.0
    wet = read_at(x, i - d)
    return (1 - mix) * x + mix * wet


def vibrato(x, rate_hz=5.5, depth_ms=0.6, sr=SR):
    return mod_delay(x, base_ms=depth_ms * 1.2, depth_ms=depth_ms, rate_hz=rate_hz, mix=1.0, sr=sr)


def tremolo(x, rate_hz=6.0, depth=0.5, sr=SR):
    i = np.arange(len(x))
    return x * (1 - depth * 0.5 * (1 + np.sin(2 * math.pi * rate_hz * i / sr)))


def ring_mod(x, freq=200.0, mix=1.0, sr=SR):
    return (1 - mix) * x + mix * x * np.sin(2 * math.pi * freq * np.arange(len(x)) / sr)


def reverse(x):
    return x[::-1].copy()


def tape_stop(x, start_s=0.0, stop_s=0.6, power=1.6, sr=SR):
    """The pitch and speed fall to a halt from `start_s`, over `stop_s`."""
    n = len(x)
    s0, ln = int(start_s * sr), max(1, int(stop_s * sr))
    r = np.ones(n + ln * 2)
    k = np.arange(len(r)) - s0
    r = np.where(k < 0, 1.0, np.clip(1.0 - k / ln, 0.0, 1.0) ** power)
    y = varispeed(x, r, n)
    return y * np.where(np.arange(n) > s0 + ln, 0.0, 1.0)


def stutter(x, at_s=0.0, slice_s=0.08, repeats=6, decay=0.0, sr=SR):
    """Keep x up to `at_s`, then repeat the next slice_s `repeats` times (each quieter by `decay` dB), as a glitch stutter."""
    a, ln = int(at_s * sr), max(8, int(slice_s * sr))
    seg = x[a:a + ln]
    if len(seg) < 8:
        return x.copy()
    seg = fade(seg, 0.002, 0.002)
    pieces = [x[:a]] + [seg * lin(-decay * k) for k in range(max(1, repeats))]
    return np.concatenate(pieces)


def glitch(x, rng, intensity=0.5, sr=SR):
    """Random slice repeats, reversals and bit-crush bursts. intensity 0..1."""
    n = len(x)
    y = x.copy()
    count = int(2 + 10 * float(np.clip(intensity, 0, 1)))
    for _ in range(count):
        ln = int(rng.uniform(0.02, 0.12) * sr)
        a = int(rng.integers(0, max(1, n - ln)))
        seg = y[a:a + ln].copy()
        r = rng.random()
        if r < 0.35:
            seg = np.tile(seg[: max(8, ln // 4)], 4)[:ln]
        elif r < 0.6:
            seg = seg[::-1]
        elif r < 0.85:
            seg = bitcrush(seg, bits=int(rng.integers(3, 7)), hold=int(rng.integers(2, 9)))
        else:
            seg = np.zeros_like(seg)
        y[a:a + len(seg)] = fade(seg, 0.001, 0.001)
    return y


def sidechain_pump(x, bpm=124.0, depth_db=10.0, release_s=0.18, sr=SR):
    period = 60.0 / max(bpm, 30.0)
    ph = (np.arange(len(x)) / sr) % period
    g = 1.0 - (1.0 - lin(-depth_db)) * np.exp(-ph / max(release_s, 0.01)) * np.clip(ph / 0.004, 0, 1) ** 0
    attack = np.clip(ph / 0.006, 0, 1)
    g = 1.0 - (1.0 - lin(-depth_db)) * np.exp(-ph / max(release_s, 0.01))
    g = np.where(ph < 0.006, 1.0 - (1.0 - lin(-depth_db)) * attack, g)
    return x * g


def widen(x, width=0.5, delay_ms=17.0, sr=SR):
    """Mono -> stereo with a decorrelated SIDE signal: L = m + s, R = m - s, so the mono sum is exactly 2m (no comb filtering)."""
    m = to_mono(x)
    d = int(delay_ms / 1000 * sr)
    s = np.concatenate([np.zeros(d), highpass(m, 250.0, order=2)])[: len(m)]
    s = s * float(np.clip(width, 0, 1)) * 0.7
    return np.stack([m + s, m - s], axis=1)


def _env_blocks(a: np.ndarray, block: int) -> np.ndarray:
    n = len(a) // block * block
    head = np.abs(a[:n]).reshape(-1, block).max(axis=1) if n else np.zeros(0)
    if len(a) > n:
        head = np.append(head, np.abs(a[n:]).max())
    return head


def compress(x, thresh_db=-18.0, ratio=4.0, attack_ms=5.0, release_ms=80.0, makeup_db=0.0, sr=SR, block=64):
    env = _env_blocks(x, block)
    lvl = 20 * np.log10(np.maximum(env, 1e-6))
    over = np.maximum(lvl - thresh_db, 0.0)
    gr = over * (1 - 1.0 / max(ratio, 1.0))                            # gain reduction in dB
    a = math.exp(-block / sr / max(attack_ms / 1000, 1e-4))
    r = math.exp(-block / sr / max(release_ms / 1000, 1e-3))
    sm = np.zeros_like(gr)
    for i in range(len(gr)):
        prev = sm[i - 1] if i else 0.0
        c = a if gr[i] > prev else r
        sm[i] = gr[i] + (prev - gr[i]) * c
    gain = lin(makeup_db) * 10 ** (-sm / 20.0)
    g = np.interp(np.arange(len(x)), (np.arange(len(gain)) + 0.5) * block, gain)
    return x * g


def gate(x, thresh_db=-40.0, attack_ms=2.0, release_ms=60.0, sr=SR, block=64):
    env = _env_blocks(x, block)
    open_ = (20 * np.log10(np.maximum(env, 1e-6)) > thresh_db).astype(float)
    a = math.exp(-block / sr / max(attack_ms / 1000, 1e-4))
    r = math.exp(-block / sr / max(release_ms / 1000, 1e-3))
    g = np.zeros_like(open_)
    for i in range(len(g)):
        prev = g[i - 1] if i else 0.0
        c = a if open_[i] > prev else r
        g[i] = open_[i] + (prev - open_[i]) * c
    return x * np.interp(np.arange(len(x)), (np.arange(len(g)) + 0.5) * block, g)


# --------------------------------------------------------------------------- measuring
_TP_TAPS = None


def _tp_taps() -> np.ndarray:
    """Three 32-tap windowed-sinc phases (1/4, 2/4, 3/4 sample) for 4x oversampling (BS.1770 Annex 2 shape)."""
    global _TP_TAPS
    if _TP_TAPS is None:
        m = np.arange(-16, 16)
        win = 0.5 + 0.5 * np.cos(math.pi * (m + 0.5) / 16.5)
        _TP_TAPS = np.stack([np.sinc(p / 4.0 - m) * win for p in (1, 2, 3)])
    return _TP_TAPS


def _tp_envelope(x: np.ndarray) -> np.ndarray:
    """Per sample, the largest magnitude among the sample and the three oversampled points after it."""
    env = np.abs(x)
    for c in _tp_taps():
        env = np.maximum(env, np.abs(np.convolve(x, c[::-1], mode="full")[15:15 + len(x)]))
    return env


def true_peak_db(x: np.ndarray) -> float:
    """4x oversampled peak in dBFS, the inter-sample peak a DAC / lossy encoder can produce."""
    if x.ndim == 2:
        return max(true_peak_db(x[:, c]) for c in range(x.shape[1]))
    if x.size == 0:
        return -200.0
    best = peak(x)
    for c in _tp_taps():
        y = np.convolve(x, c[::-1], mode="full")[15:15 + len(x)]
        best = max(best, float(np.max(np.abs(y))))
    return db(best)


def _kweight_mag(f: np.ndarray, sr: int) -> np.ndarray:
    def biquad(b, a):
        w = 2 * math.pi * f / sr
        z1, z2 = np.exp(-1j * w), np.exp(-2j * w)
        return np.abs((b[0] + b[1] * z1 + b[2] * z2) / (a[0] + a[1] * z1 + a[2] * z2))
    G, Q, fc = 3.999843853973347, 0.7071752369554196, 1681.9744509555319
    A = 10 ** (G / 40)
    w0 = 2 * math.pi * fc / sr
    al = math.sin(w0) / (2 * Q)
    c = math.cos(w0)
    sA = math.sqrt(A)
    b = (A * ((A + 1) + (A - 1) * c + 2 * sA * al), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - 2 * sA * al))
    a = ((A + 1) - (A - 1) * c + 2 * sA * al, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - 2 * sA * al)
    Q2, fc2 = 0.5003270373253953, 38.13547087613982
    w1 = 2 * math.pi * fc2 / sr
    al2 = math.sin(w1) / (2 * Q2)
    c1 = math.cos(w1)
    b2 = ((1 + c1) / 2, -(1 + c1), (1 + c1) / 2)
    a2 = (1 + al2, -2 * c1, 1 - al2)
    return biquad(b, a) * biquad(b2, a2)


def lufs(x: np.ndarray, sr: int = SR) -> float:
    """Integrated loudness, BS.1770 shape: K-weighting (applied in the frequency domain), 400 ms blocks at 75 % overlap, absolute gate -70 LUFS and
    relative gate -10 LU. A clip shorter than 400 ms is measured whole, ungated. -inf (as -200.0) for silence."""
    chans = [x] if x.ndim == 1 else [x[:, c] for c in range(x.shape[1])]
    filt = []
    for ch in chans:
        n = len(ch)
        if n == 0:
            return -200.0
        nfft = next_pow2(n)
        X = np.fft.rfft(ch, nfft)
        filt.append(np.fft.irfft(X * _kweight_mag(np.fft.rfftfreq(nfft, 1.0 / sr), sr), nfft)[:n])
    n = len(filt[0])
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    if n < blk:
        z = sum(float(np.mean(c * c)) for c in filt)
        return -0.691 + 10 * math.log10(z) if z > 1e-14 else -200.0
    starts = np.arange(0, n - blk + 1, hop)
    cs = [np.concatenate([[0.0], np.cumsum(c * c)]) for c in filt]
    z = sum((c[starts + blk] - c[starts]) / blk for c in cs)
    l = -0.691 + 10 * np.log10(np.maximum(z, 1e-14))
    keep = l > -70.0
    if not keep.any():
        return -200.0
    rel = -0.691 + 10 * math.log10(float(np.mean(z[keep]))) - 10.0
    keep2 = keep & (l > rel)
    if not keep2.any():
        return -200.0
    return float(-0.691 + 10 * math.log10(float(np.mean(z[keep2]))))


def envelope(x: np.ndarray, win_ms: float = 5.0, sr: int = SR) -> np.ndarray:
    m = to_mono(x)
    w = max(1, int(win_ms / 1000 * sr))
    cs = np.concatenate([[0.0], np.cumsum(m * m)])
    idx = np.arange(len(m))
    lo = np.maximum(idx - w // 2, 0)
    hi = np.minimum(idx + w // 2 + 1, len(m))
    return np.sqrt((cs[hi] - cs[lo]) / np.maximum(hi - lo, 1))


def trim_silence(x: np.ndarray, thresh_db: float = -50.0, keep_head_s: float = 0.0, keep_tail_s: float = 0.03, rel_db: float = 55.0,
                 sr: int = SR) -> tuple[np.ndarray, float, float]:
    """(trimmed, head_removed_s, tail_removed_s). The threshold is the higher of thresh_db and (peak - rel_db), so a quiet noise floor under a loud hit is cut too."""
    e = envelope(x, 5.0, sr)
    pk = float(e.max()) if e.size else 0.0
    if pk <= 1e-6:
        return x, 0.0, 0.0
    th = max(lin(thresh_db), pk * lin(-rel_db))
    on = np.nonzero(e > th)[0]
    if on.size == 0:
        return x, 0.0, 0.0
    a = max(0, int(on[0]) - int(keep_head_s * sr))
    b = min(len(x), int(on[-1]) + 1 + int(keep_tail_s * sr))
    return x[a:b], a / sr, (len(x) - b) / sr


def onset_time(x: np.ndarray, within_db: float = 30.0, sr: int = SR) -> float:
    """Seconds until the sound first gets within `within_db` of its loudest 5 ms (the moment the hook starts)."""
    e = envelope(x, 5.0, sr)
    pk = float(e.max()) if e.size else 0.0
    if pk <= 1e-6:
        return 0.0
    return float(np.argmax(e > pk * lin(-within_db))) / sr


def attack_time(x: np.ndarray, sr: int = SR) -> float:
    """10 % -> 90 % rise time of the first main peak, in seconds."""
    e = envelope(x, 1.0, sr)
    if not e.size or e.max() <= 1e-6:
        return 0.0
    k = int(np.argmax(e > 0.9 * e.max()))
    j = int(np.argmax(e[: k + 1] > 0.1 * e.max())) if k else 0
    return max(0, k - j) / sr


def silence_gaps(x: np.ndarray, thresh_db: float = -45.0, min_s: float = 0.15, sr: int = SR) -> list[tuple[float, float]]:
    """Silent stretches INSIDE the sound (not the head and tail): [(start_s, length_s)]."""
    e = envelope(x, 10.0, sr)
    pk = float(e.max()) if e.size else 0.0
    if pk <= 1e-6:
        return []
    quiet = e < max(lin(thresh_db), pk * lin(-50))
    on = np.nonzero(~quiet)[0]
    if on.size == 0:
        return []
    q = quiet[on[0]:on[-1] + 1]
    out, i = [], 0
    while i < len(q):
        if q[i]:
            j = i
            while j < len(q) and q[j]:
                j += 1
            if (j - i) / sr >= min_s:
                out.append((round((on[0] + i) / sr, 3), round((j - i) / sr, 3)))
            i = j
        else:
            i += 1
    return out


def spectral_centroid(x: np.ndarray, sr: int = SR) -> float:
    m = to_mono(x)
    if m.size < 16:
        return 0.0
    X = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    f = np.fft.rfftfreq(len(m), 1.0 / sr)
    return float(np.sum(f * X) / max(float(np.sum(X)), EPS))


def loop_seam(x: np.ndarray, sr: int = SR) -> dict:
    """Would the clip repeat without a click or a level jump? Slope-aware (works for low-frequency sounds, where a raw sample difference breaks):
    the wrap point is judged by how far the last samples' quadratic extrapolation misses the first sample, relative to how far the same predictor
    misses inside the clip (so a 4 kHz tone and a 50 Hz boom are judged alike), plus the level mismatch of the last vs first 0.4 s and the spectral similarity of the last vs first 0.5 s."""
    m = to_mono(x)
    if len(m) < int(0.3 * sr):
        return {"jump": 1.0, "level_diff_db": 0.0, "spectral_cos": 0.0, "ok": False}
    w = max(8, int(0.01 * sr))
    local = max(math.sqrt(float(np.mean(m[-w:] ** 2))), math.sqrt(float(np.mean(m[:w] ** 2))), 1e-4)
    pred = 3 * m[-1] - 3 * m[-2] + m[-3]
    pred_head = 3 * m[0] - 3 * m[1] + m[2]
    span = int(0.2 * sr)

    def interior(seg):                                              # how far the same predictor misses INSIDE the clip: the yardstick for the seam miss
        return np.abs(3 * seg[2:-1] - 3 * seg[1:-2] + seg[:-3] - seg[3:])
    ref = max(float(np.percentile(np.concatenate([interior(m[-span:]), interior(m[:span])]), 95)), 0.003 * local)
    jump = max(abs(float(pred - m[0])), abs(float(pred_head - m[-1]))) / ref
    lw = int(min(0.4, len(m) / sr / 4) * sr)                         # long enough to average over gated / pulsing content
    head, tail = rms_db(m[:lw]), rms_db(m[-lw:])
    diff = abs(head - tail) if min(head, tail) > -80 else 60.0
    bw = int(0.5 * sr)
    def bands(seg):
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        edges = np.unique(np.geomspace(2, len(sp) - 1, 21).astype(int))
        return np.log10(np.array([sp[a:b].sum() + 1e-12 for a, b in zip(edges[:-1], edges[1:])]))
    h, t = bands(m[:bw]), bands(m[-bw:])
    h, t = h - h.mean(), t - t.mean()
    cos = float(np.dot(h, t) / max(np.linalg.norm(h) * np.linalg.norm(t), 1e-9))
    return {"jump": round(jump, 4), "level_diff_db": round(diff, 2), "spectral_cos": round(cos, 3), "ok": jump < 4.0 and diff < 6.0 and cos > 0.8}


def make_loop(x: np.ndarray, xfade_s: float = 0.08, sr: int = SR) -> np.ndarray:
    """Equal-power crossfade of the tail into the head: a clip that repeats without a click (shorter by the fade)."""
    n = len(x)
    f = int(min(max(xfade_s, 0.005) * sr, n // 3))
    if f < 8:
        return x.copy()
    t = np.linspace(0, math.pi / 2, f)
    shape = (-1,) + (1,) * (x.ndim - 1)
    head, tail = x[:f] * np.sin(t).reshape(shape), x[n - f:] * np.cos(t).reshape(shape)
    body = x[f:n - f]
    return np.concatenate([body[: len(body)], head + tail], axis=0) if len(body) else head + tail


def tempo_guess(x: np.ndarray, sr: int = SR) -> float | None:
    """A BPM guess (60-200) from the onset envelope's autocorrelation, or None when there is no steady repetition (most one-shots)."""
    m = to_mono(x)
    if len(m) < 2 * sr:
        return None
    hop = 441
    e = envelope(m, 10.0, sr)[::hop]
    o = np.maximum(np.diff(e), 0.0)
    if o.size < 40 or o.max() <= 1e-6:
        return None
    o = o - o.mean()
    ac = np.correlate(o, o, mode="full")[len(o) - 1:]
    ac /= max(ac[0], EPS)
    fps = sr / hop
    lo, hi = int(fps * 60 / 200), int(fps * 60 / 60)
    if hi >= len(ac):
        return None
    k = lo + int(np.argmax(ac[lo:hi]))
    return round(60.0 * fps / k, 1) if ac[k] > 0.3 else None


def mono_compat(x: np.ndarray) -> dict:
    """For stereo: channel correlation and how much level the mono sum loses (dB). Mono is perfect by definition."""
    if x.ndim == 1:
        return {"correlation": 1.0, "mono_loss_db": 0.0, "ok": True}
    l, r = x[:, 0], x[:, 1]
    den = math.sqrt(float(np.sum(l * l) * np.sum(r * r)))
    corr = float(np.sum(l * r) / den) if den > EPS else 1.0
    st, mo = rms_db(x), rms_db((l + r) / 2.0)
    loss = st - mo if st > -80 else 0.0
    return {"correlation": round(corr, 3), "mono_loss_db": round(loss, 2), "ok": corr > 0.2 and loss < 3.0}


# --------------------------------------------------------------------------- safety: limiter and mastering
def _sliding_min(a: np.ndarray, w: int) -> np.ndarray:
    """Centered running minimum over a window of w samples (doubling steps, no loop over samples)."""
    if w <= 1:
        return a.copy()
    out = a.copy()
    span = 1
    while span * 2 <= w:
        out = np.minimum(out, np.concatenate([out[span:], np.full(span, out[-1])]))
        span *= 2
    if span < w:
        sh = w - span
        out = np.minimum(out, np.concatenate([out[sh:], np.full(sh, out[-1])]))
    half = w // 2
    return np.concatenate([np.full(half, out[0]), out[: len(out) - half]]) if half else out


def limit(x: np.ndarray, ceiling_db: float = -1.0, lookahead_ms: float = 5.0, release_ms: float = 80.0, sr: int = SR) -> np.ndarray:
    """Look-ahead brick-wall limiter. The result's sample AND (4x oversampled) true peak never exceed `ceiling_db`."""
    c = lin(ceiling_db)
    if x.size == 0:
        return x
    link = np.max(np.stack([_tp_envelope(x[:, k]) for k in range(x.shape[1])], axis=1), axis=1) if x.ndim == 2 else _tp_envelope(x)
    n = len(link)
    need = np.minimum(1.0, c / np.maximum(link, 1e-9))
    w = max(3, int(lookahead_ms / 1000 * sr) | 1)
    gmin = _sliding_min(need, w)
    k = np.ones(w) / w
    gs = np.convolve(np.pad(gmin, (w // 2, w // 2), mode="edge"), k, mode="valid")[:n]
    gs = np.minimum(gs, need)
    # release: let the gain recover slowly (done on a coarse grid, then min() with the exact gain keeps the guarantee)
    blk = 32
    coarse = gs[: n // blk * blk].reshape(-1, blk).min(axis=1) if n >= blk else gs.min(keepdims=True)
    rel = math.exp(-blk / sr / max(release_ms / 1000, 1e-3))
    smooth = coarse.copy()
    for i in range(1, len(smooth)):                                    # forwards: recovery speed limited by `rel`
        smooth[i] = min(coarse[i], smooth[i - 1] + (1.0 - smooth[i - 1]) * (1 - rel))
    g_rel = np.interp(np.arange(n), (np.arange(len(smooth)) + 0.5) * blk, smooth)
    g = np.minimum(gs, g_rel)
    y = x * (g[:, None] if x.ndim == 2 else g)
    tp = true_peak_db(y)
    if tp > ceiling_db:
        y = y * lin(ceiling_db - tp - 0.01)
    return y


LUFS_TARGETS = (-23.0, -18.0, -16.0, -14.0, -12.0)
MAX_LUFS = -9.0                           # nothing leaves louder than this, whatever a preset asks for
DEFAULT_CEILING_DB = -1.0


def master(x: np.ndarray, target_lufs: float = -14.0, ceiling_db: float = DEFAULT_CEILING_DB, *, max_gain_db: float = 30.0,
           max_limit_db: float = 6.0, sr: int = SR) -> tuple[np.ndarray, dict]:
    """Bring the clip to `target_lufs` (never louder than MAX_LUFS) and hold the true peak under `ceiling_db` (never above -0.5).
    A transient sound that cannot reach the target without more than `max_limit_db` of limiting stops short and says so.
    Returns (audio, report)."""
    target = float(min(target_lufs, MAX_LUFS))
    ceiling = float(min(ceiling_db, -0.5))
    before = lufs(x, sr)
    if before <= -100 or peak(x) < 1e-5:
        raise DSPError("the sound is silent")
    x = x - np.mean(x, axis=0) if abs(float(np.mean(x))) > 1e-4 else x                      # DC off
    gain = min(max_gain_db, target - before)
    y = x * lin(gain)
    reached = lufs(y, sr)
    pre_tp = true_peak_db(y)
    y2 = limit(y, ceiling, sr=sr)
    lim_db = max(0.0, pre_tp - ceiling)
    for _ in range(3):                                                 # limiting costs loudness: add gain back while the limiter reduction stays sane
        got = lufs(y2, sr)
        short = target - got
        if short < 0.3 or lim_db >= max_limit_db or got <= -100:
            break
        step = min(short, max_limit_db - lim_db + 0.5)
        y = y * lin(step)
        pre_tp = true_peak_db(y)
        lim_db = max(0.0, pre_tp - ceiling)
        y2 = limit(y, ceiling, sr=sr)
    final = lufs(y2, sr)
    return y2, {"lufs_before": round(before, 1), "lufs": round(final, 1), "target_lufs": target, "ceiling_db": ceiling,
                "true_peak_db": round(true_peak_db(y2), 2), "limiter_reduction_db": round(lim_db, 1), "reached_target": final >= target - 1.0,
                "gain_db": round(gain, 1)}
