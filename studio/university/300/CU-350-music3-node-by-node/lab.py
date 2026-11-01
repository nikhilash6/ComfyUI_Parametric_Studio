# CU-350 lab: seconds, frames and the prompt in MiniMax Music 3, ported from comfy_extras/nodes_minimax_music.py and comfy/ldm/minimax_music/{ar,dit,prompt}.py (ComfyUI v0.43.0).
import math, re
AUDIO_FRAMES_PER_SECOND, MAX_AUDIO_FRAMES = 25, 9000
def latent_length(frames): return max(1, int(frames * 44100 / 24000 * 960 / 512))
def frames_for(seconds): return min(MAX_AUDIO_FRAMES, max(1, round(seconds * AUDIO_FRAMES_PER_SECOND)))
print(f"longest allowed: {MAX_AUDIO_FRAMES} / {AUDIO_FRAMES_PER_SECOND} = {MAX_AUDIO_FRAMES / AUDIO_FRAMES_PER_SECOND:.0f} s")
print("seconds   AR frames   8-code groups   latent [B, 128, L]   samples per channel   duration at 44100 Hz")
for s in (30, 60, 120, 360, 500):
    f = frames_for(s); L = latent_length(f); print(f"{s:<9d} {f:<11d} {f * 8:<15,d} [1, 128, {L:<6d}]      {L * 512:<21,d} {L * 512 / 44100:.3f} s")
assert latent_length(750) == 2583 and frames_for(500) == 9000
print(f"latent frames a second: {latent_length(25000) / 1000:.3f}, against 44100 / 512 = {44100 / 512:.3f}")
# The DiT works in windows above 200 AR frames (dit.py), with a hop of 100.
win, hop = latent_length(200), latent_length(100)
def n_windows(L):
    n, s = 0, 0
    while s < L:
        n += 1
        if min(s + win, L) == L: break
        s += hop
    return n
print(f"\nDiT window {win} latent frames ({win * 512 / 44100:.1f} s), hop {hop}")
for s in (5, 30, 60, 120): print(f"{s:>4d} s: {n_windows(latent_length(frames_for(s)))} DiT passes per sampling step, with CFG on twice that")
assert n_windows(latent_length(frames_for(5))) == 1
# The 128 channels: dav.py reshapes [B, 128, L] to [2B, 64, L], so each stereo channel owns 64.
print(f"\nDAV decode: [1, 128, L] -> [2, 64, L], one 64-channel stream per stereo channel. Values per second {128 * 44100 / 512:.0f} for {2 * 44100} samples: {2 * 44100 / (128 * 44100 / 512):.0f} to 1")
# prompt.py: what the tokenizer really sees.
_S = re.compile(r"<\|([^|]*)\|>"); _L = re.compile(r"\s*(\[[^\]]+\])\s*")
def md(text):
    ls = []
    for raw in text.splitlines():
        l = re.sub(r"^\s{0,3}#{1,6}\s+", "", raw); l = re.sub(r"^\s*[*+-]\s+", "", l)
        while "**" in l:
            u = re.sub(r"\*\*([^*]+)\*\*", r"\1", l)
            if u == l: break
            l = u
        l = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", l); ls.append(l.rstrip())
    t = "\n".join(ls); t = re.sub(r"^\s*[-*_]{3,}\s*$", "", t, flags=re.M); return t.replace("• ", "").replace("    ", "")
def rep(m):
    i = m.group(1).strip(); p = i.split(None, 1); return f"{p[0]} is {p[1]}" if len(p) == 2 else i
def clean_caption(c): return re.sub(r"\n{2,}", "\n", md(_S.sub(rep, c)))
def normalize_lyrics(l):
    parts = _L.split(l); t = "\n".join(p.lower() if p.startswith("[") else p for p in parts if p); return "[start]\n" + t.replace(" ^ ", "\n")
cap = "## Global Metadata\n\n- **Genre**: lo-fi\n- <|BPM 72|>"
lyr = "[Verse] Rain on the glass ^ I stay [CHORUS]\nHold on"
print("\ncaption in :", repr(cap)); print("caption out:", repr(clean_caption(cap)))
print("lyrics in  :", repr(lyr)); print("lyrics out :", repr(normalize_lyrics(lyr)))
assert normalize_lyrics(lyr).startswith("[start]\n[verse]\nRain") and "[chorus]" in normalize_lyrics(lyr) and "BPM is 72" in clean_caption(cap)
# Padding. If the empty latent is longer than the AR output, the DiT pads the condition with zeros (dit.py forward).
got, asked = latent_length(frames_for(21.0)), latent_length(frames_for(30.0))
print(f"\nThe AR stage stops at 21 s and you typed 30 s by hand: {asked - got} latent frames, {(asked - got) * 512 / 44100:.1f} s, are decoded with a zero condition")
