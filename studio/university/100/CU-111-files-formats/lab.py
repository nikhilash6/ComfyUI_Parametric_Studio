# CU-111 lab: three containers built and parsed by hand, with the standard library only: a PNG that carries a workflow, a WAV file, and an MP4-style box stream.
# Run: python lab.py   (well under a second)
# The byte layouts follow the PNG specification (Third Edition), the RIFF/WAVE description from Microsoft and IBM, and the box (atom) layout of ISO/QuickTime files.
# The MP4 part is a synthetic box stream, not a playable video.
import json, math, struct, zlib

def u32(b): return struct.unpack(">I", b)[0]

# 1. PNG. Eight signature bytes, then chunks: 4-byte length (data only), 4-byte type, data, 4-byte CRC over type + data. All numbers big-endian.
SIG = bytes.fromhex("89504e470d0a1a0a")
def chunk(kind, data): return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
W = H = 8
pixels = bytes(v for y in range(H) for x in range(W) for v in (x * 32, y * 32, 128))              # a small RGB gradient
raw = b"".join(b"\x00" + pixels[y * W * 3:(y + 1) * W * 3] for y in range(H))                      # each scanline starts with a filter-type byte (0 = none)
prompt = {"3": {"class_type": "KSampler", "inputs": {"seed": 42, "steps": 20, "positive": ["6", 0]}}, "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red fox, caf" + chr(233)}}}
workflow = {"version": 0.4, "nodes": [{"id": 3, "type": "KSampler"}, {"id": 6, "type": "CLIPTextEncode"}], "links": []}
def text(key, obj): return chunk(b"tEXt", key.encode("latin-1") + b"\x00" + json.dumps(obj).encode("latin-1"))   # keyword, null separator, Latin-1 text
png = SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + text("prompt", prompt) + text("workflow", workflow) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")

def read_chunks(buf):
    assert buf[:8] == SIG; pos, out = 8, []
    while pos < len(buf):
        n, kind = u32(buf[pos:pos + 4]), buf[pos + 4:pos + 8]; data = buf[pos + 8:pos + 8 + n]; crc = u32(buf[pos + 8 + n:pos + 12 + n])
        out.append((kind, data, crc == zlib.crc32(kind + data))); pos += 12 + n
    return out
print(f"PNG of {W} x {H} pixels: {len(png)} bytes, signature {png[:8].hex(' ')}")
print("\ntype  data bytes  crc ok  kind        what")
for kind, data, ok in read_chunks(png):
    what = {b"IHDR": lambda d: "width %d, height %d, bit depth %d, color type %d" % (u32(d[:4]), u32(d[4:8]), d[8], d[9]), b"tEXt": lambda d: "keyword " + d.split(b"\x00")[0].decode(),
            b"IDAT": lambda d: "zlib data, %d bytes once unpacked" % len(zlib.decompress(d)), b"IEND": lambda d: "end marker"}[kind](data)
    print(f"{kind.decode():<6}{len(data):<12}{str(ok):<8}{'critical' if kind.decode()[0].isupper() else 'ancillary':<12}{what}")
chunks = read_chunks(png)
texts = {d.split(b"\x00")[0].decode(): json.loads(d.split(b"\x00", 1)[1]) for k, d, _ in chunks if k == b"tEXt"}
assert texts["prompt"] == prompt and texts["workflow"] == workflow and zlib.decompress(next(d for k, d, _ in chunks if k == b"IDAT")) == raw
print(f"\nthe last 12 bytes of every PNG: {png[-12:].hex(' ')}   crc of the bytes IEND: {zlib.crc32(b'IEND'):08x}")
print(f"json.dumps writes only ASCII by default: {json.dumps('snowman ' + chr(0x2603)).encode('ascii').decode()}   the raw character does not fit Latin-1: {not all(ord(c) < 256 for c in chr(0x2603))}")

hit = bytearray(png); at = png.index(b"a red fox") + 4; hit[at] ^= 0x01                   # flip one bit inside the prompt text
bad = [k.decode() + (" " + d.split(b"\x00")[0].decode() if k == b"tEXt" else "") for k, d, ok in read_chunks(bytes(hit)) if not ok]
print(f"one bit flipped inside the prompt text: chunks failing their crc: {bad}")
critical = SIG + b"".join(chunk(k, d) for k, d, _ in chunks if k.decode()[0].isupper())
after = read_chunks(critical)
print(f"only the critical chunks kept: {len(png)} -> {len(critical)} bytes, text chunks left: {sum(k == b'tEXt' for k, _, _ in after)}, same pixels: {zlib.decompress(next(d for k, d, _ in after if k == b'IDAT')) == raw}")
assert bad == ["tEXt prompt"] and png[-12:].hex() == "0000000049454e44ae426082"

# 2. WAV. A RIFF container: 'RIFF', size, 'WAVE', then chunks. Numbers are little-endian. 'fmt ' must come before 'data'; unknown chunks are skipped; odd sizes are padded.
RATE, CH, SECONDS = 8000, 2, 1
frames = [(int(12000 * math.sin(2 * math.pi * 440 * i / RATE)), int(12000 * math.sin(2 * math.pi * 660 * i / RATE))) for i in range(RATE * SECONDS)]
pcm = b"".join(struct.pack("<hh", l, r) for l, r in frames)
def riff_chunk(kind, data): return kind + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) % 2 else b"")
fmt = struct.pack("<HHIIHH", 1, CH, RATE, RATE * CH * 2, CH * 2, 16)                       # format 1 = PCM, channels, rate, byte rate, block align, bits per sample
wav = b"RIFF" + struct.pack("<I", 4 + len(riff_chunk(b"fmt ", fmt)) + len(riff_chunk(b"data", pcm))) + b"WAVE" + riff_chunk(b"fmt ", fmt) + riff_chunk(b"data", pcm)
def parse_wav(buf):
    assert buf[:4] == b"RIFF" and buf[8:12] == b"WAVE"; pos, found = 12, {}
    while pos + 8 <= len(buf):
        kind, n = buf[pos:pos + 4], struct.unpack("<I", buf[pos + 4:pos + 8])[0]; found[kind] = (pos + 8, n); pos += 8 + n + (n % 2)
    return found
info = parse_wav(wav); f = struct.unpack("<HHIIHH", wav[info[b"fmt "][0]:info[b"fmt "][0] + 16])
print(f"\nWAV: {len(wav)} bytes = 44 header bytes + {info[b'data'][1]} data bytes; RIFF size field {struct.unpack('<I', wav[4:8])[0]} = file size - 8")
print(f"fmt: format {f[0]} (PCM), {f[1]} channels, {f[2]} Hz, byte rate {f[3]} = {f[2]} x {f[1]} x {f[5] // 8}, block align {f[4]}, {f[5]} bits per sample")
first = struct.unpack("<4h", wav[info[b"data"][0]:info[b"data"][0] + 8])
print(f"first two sample pairs as integers {first}, as floats {tuple(round(v / 32768, 4) for v in first)}, extremes {-32768 / 32768} and {32767 / 32768:.5f}")
print(f"the AUDIO tensor ComfyUI would hold for this file: waveform [1, {CH}, {info[b'data'][1] // (CH * 2)}], sample_rate {RATE}")
extra = riff_chunk(b"fmt ", fmt) + riff_chunk(b"note", b"odd") + riff_chunk(b"data", pcm)      # an extra chunk with an odd size, before the data
wav2 = b"RIFF" + struct.pack("<I", 4 + len(extra)) + b"WAVE" + extra; info2 = parse_wav(wav2)
print(f"with an odd-sized 'note' chunk before the data: data starts at byte {info2[b'data'][0]}, not 44; walking the chunks finds {wav2[info2[b'data'][0]:info2[b'data'][0] + 8] == pcm[:8]}, reading at 44 finds {wav2[44:52] == pcm[:8]}")
assert info[b"data"] == (44, 32000) and info2[b"data"][0] == 12 + 24 + 12 + 8 and wav2[info2[b"data"][0]:info2[b"data"][0] + 8] == pcm[:8] and wav2[44:52] != pcm[:8]

# 3. MP4-style boxes: 4-byte size (counts the 8 header bytes), 4-byte type, payload; size 1 means an 8-byte size follows, size 0 means "to the end of the file".
def box(kind, payload): return struct.pack(">I", 8 + len(payload)) + kind + payload
def boxes(buf):
    pos, out = 0, []
    while pos < len(buf):
        size, kind = u32(buf[pos:pos + 4]), buf[pos + 4:pos + 8]; head = 8
        if size == 1: size, head = struct.unpack(">Q", buf[pos + 8:pos + 16])[0], 16
        elif size == 0: size = len(buf) - pos
        out.append((kind.decode(), pos, size)); pos += size
    return out
ftyp = box(b"ftyp", b"isom" + struct.pack(">I", 0) + b"isom" + b"mp42"); mdat = box(b"mdat", bytes(1_000_000)); moov = box(b"moov", b"index" * 40)
for label, order in (("index last ", ftyp + mdat + moov), ("index first", ftyp + moov + mdat)):
    lay = boxes(order); end_of_moov = next(p + s for k, p, s in lay if k == "moov")
    print(f"\n{label}: " + ", ".join(f"{k} at {p} ({s} bytes)" for k, p, s in lay))
    print(f"   bytes to read before the index (moov) is complete: {end_of_moov:,d} of {len(order):,d}")
big = struct.pack(">I", 1) + b"mdat" + struct.pack(">Q", 16 + 5) + b"hello"; rest = struct.pack(">I", 0) + b"free" + b"tail"
print(f"\nbox with size field 1: real size read from the next 8 bytes = {boxes(big)[0][2]}; box with size field 0 in a {len(rest)}-byte stream: size {boxes(rest)[0][2]}")
assert boxes(ftyp + mdat + moov)[1][2] == 1_000_008 and boxes(big) == [("mdat", 0, 21)] and boxes(rest) == [("free", 0, 12)]
