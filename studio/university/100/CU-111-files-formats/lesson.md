# CU-111 - Files and formats: PNG metadata, MP4, WAV, safetensors

**Objective.** Open four kinds of file the way a program does: find the signature, read the chunk or box list, and say where the picture, the sound, the video and the workflow live in the bytes. Taught by Bit Bandit.

## The idea

Every format answers two questions at the start: what am I, and how do I find my parts? A PNG begins with a signature and then a list of chunks. A WAV file is a list of chunks inside a RIFF wrapper. An MP4 is a list of boxes. A safetensors file starts with the size of a JSON header (CU-107). In all four, a small index of labelled parts sits beside the bulk data. In the first three, a reader may also skip a part it does not know. That rule is how ComfyUI hides a whole workflow inside a picture without changing a pixel: it adds text chunks that a decoder is free to skip.

## The mechanism

**PNG.** The first eight bytes are the signature 89 50 4E 47 0D 0A 1A 0A. After it come chunks, each made of a four-byte length that counts only the data, a four-byte type, the data, and a four-byte CRC computed over the type and the data. Numbers are big-endian. The CRC polynomial is the one used by gzip, so Python's `zlib.crc32` computes it. The case of the type's letters carries information: a capital first letter means critical, as in IHDR, IDAT and IEND, and a lowercase first letter means ancillary, as in tEXt, which a decoder may skip. IHDR comes first with the width, the height and five one-byte format fields. IDAT holds the pixels, zlib-compressed with a filter byte at the start of every row. A tEXt chunk is a keyword of 1 to 79 bytes, a zero byte and Latin-1 text. Text outside Latin-1 belongs in an iTXt chunk.

Before the other formats, take a PNG apart. This one is really built in your browser, from the same recipe.

{{play:pngcut}}

**WAV.** A RIFF file is the bytes RIFF, a four-byte size, the form name WAVE, and then chunks. Each chunk is a four-character id, a four-byte size, the data, and one pad byte when the size is odd. Numbers are little-endian, the opposite of PNG. The `fmt ` chunk must come before `data`, and a reader must expect and ignore chunks it does not know. For plain PCM the `fmt ` chunk gives the format code 1, the channel count, the sample rate, the byte rate, the block align and the bits per sample. PCM samples are two's-complement integers, except at 8 bits or fewer, where they are offset binary.

**MP4.** An ISO-style file consists of boxes, and no data exists outside a box. A box is a four-byte size that counts its own eight header bytes, a four-character type and a payload. A size of 1 means a 64-bit size follows, and a size of 0 means the box runs to the end of the file. The `ftyp` box comes at or near the start and names the brand, `moov` holds the structural metadata that indexes the media, and `mdat` holds the media bytes. FFmpeg's documentation says the index is usually written at the end of the file. FFmpeg can run a second pass with `+faststart` that moves the `moov` box to the front, for better playback.

## In ComfyUI

Run this no-model graph with a `SaveImage` in place of the preview and you get a real PNG with these chunks.

{{graph:nm_first}}

`SaveImage` builds a `PngInfo`, adds the API prompt as a text entry named `prompt` and every key of `extra_pnginfo` under its own name, and saves with a compression level of 4. `PreviewImage` uses level 1. The documentation lists where the built-in save nodes put the same two JSON fields: PNG `tEXt` chunks, animated WebP EXIF tags, MP4 and WebM container metadata tags, and safetensors metadata for `.latent` files. With `--disable-metadata` the save nodes skip it.

`SaveVideo` offers the containers mp4, mkv and webm with the codecs h264 and av1, and "auto" means MP4 for h264 and WebM for av1. For MP4 written to a path it opens the output with the FFmpeg flags `use_metadata_tags+faststart`, so the index is moved to the front, and the metadata goes into the `mdta` metadata box. A comment in the code says the flag preserves the custom tags (workflow, prompt, extra_pnginfo) in the ISO file.

The audio save nodes in `comfy_extras/nodes_audio.py` write FLAC by default, with MP3 and Opus nodes alongside, and WAV is not one of their formats. This small graph writes a real audio file with no model. It uses the default format and not WAV.

{{graph:nm_audio}}

`LoadAudio` decodes with PyAV and turns integer samples into float32 by dividing 16-bit values by 2^15 and 32-bit values by 2^31. The AUDIO value is a dictionary with a `waveform` of shape [B, C, T] and a `sample_rate`.

## What goes wrong

- **Dragging a picture onto the canvas does nothing.** The chunks are gone, because another program re-encoded the file, or the server ran with `--disable-metadata`. Check with a chunk reader, as in the lab.
- **You shared more than the picture.** A PNG from `SaveImage` carries your whole graph, with your prompts and the names of your files. Before posting one, decide whether that's fine. To remove it, turn on `--disable-metadata` or strip the text chunks.
- **Reading a WAV at byte 44.** The lab shows an odd-sized chunk moving the data to byte 56. Walk the chunks.
- **Trusting what the metadata says.** It isn't signed, so anyone can edit the prompt in a file. It says what the file claims and proves nothing about how the picture was made.
- **A video won't start playing until it has fully loaded.** The index may be at the end. A file written to a path by `SaveVideo` as MP4 gets `+faststart`. Writing to a buffer can't use it, as a comment in the code says.
- **Non-Latin text looks garbled in your own chunk reader.** tEXt is Latin-1, and JSON from `json.dumps` is safe because it escapes other characters. Text from elsewhere may arrive in iTXt.
- **A `.latent` or safetensors file treated as a picture.** Each format has its own index. Ask what the first bytes are.

## Lab

The lab builds a tiny PNG with the standard library, with a prompt and a workflow in tEXt chunks, and reads it back.

```text
PNG of 8 x 8 pixels: 488 bytes, signature 89 50 4e 47 0d 0a 1a 0a

type  data bytes  crc ok  kind        what
IHDR  13          True    critical    width 8, height 8, bit depth 8, color type 2
tEXt  182         True    ancillary   keyword prompt
tEXt  117         True    ancillary   keyword workflow
IDAT  108         True    critical    zlib data, 200 bytes once unpacked
IEND  0           True    critical    end marker
```

The 200 unpacked bytes are 8 rows of 1 filter byte and 24 pixel bytes. The two text chunks hold 299 data bytes between them, and a reader never needs to understand them to find the pixels.

```text
the last 12 bytes of every PNG: 00 00 00 00 49 45 4e 44 ae 42 60 82   crc of the bytes IEND: ae426082
json.dumps writes only ASCII by default: "snowman \u2603"   the raw character does not fit Latin-1: True
```

The end marker has no data, so its twelve bytes are always the same. The second line is why a JSON string with a snowman can sit in a Latin-1 chunk: `json.dumps` escapes it.

```text
one bit flipped inside the prompt text: chunks failing their crc: ['tEXt prompt']
only the critical chunks kept: 488 -> 165 bytes, text chunks left: 0, same pixels: True
```

A single flipped bit is caught by exactly one chunk's CRC, and the image chunks are unharmed. Dropping the ancillary chunks leaves the picture identical and removes the workflow, which is what happens when a tool re-encodes a file.

```text
WAV: 32044 bytes = 44 header bytes + 32000 data bytes; RIFF size field 32036 = file size - 8
fmt: format 1 (PCM), 2 channels, 8000 Hz, byte rate 32000 = 8000 x 2 x 2, block align 4, 16 bits per sample
first two sample pairs as integers (0, 0, 4064, 5945), as floats (0.0, 0.0, 0.124, 0.1814), extremes -1.0 and 0.99997
the AUDIO tensor ComfyUI would hold for this file: waveform [1, 2, 8000], sample_rate 8000
with an odd-sized 'note' chunk before the data: data starts at byte 56, not 44; walking the chunks finds True, reading at 44 finds False
```

One second of 8000 Hz stereo at 16 bits is 32000 bytes of samples, and the byte rate is the product of the three numbers. Dividing by 32768 puts the integers between −1.0 and 0.99997. The last line is the lesson for anyone tempted to read the audio at byte 44: an extra chunk of odd size, padded to an even length, moves the data to byte 56.

```text
index last : ftyp at 0 (24 bytes), mdat at 24 (1000008 bytes), moov at 1000032 (208 bytes)
   bytes to read before the index (moov) is complete: 1,000,240 of 1,000,240

index first: ftyp at 0 (24 bytes), moov at 24 (208 bytes), mdat at 232 (1000008 bytes)
   bytes to read before the index (moov) is complete: 232 of 1,000,240
```

```text
box with size field 1: real size read from the next 8 bytes = 21; box with size field 0 in a 12-byte stream: size 12
```

The synthetic stream has a one-megabyte `mdat` and a small `moov`. With the index last, a reader must go through the whole file before it knows how to play it. With the index first, 232 bytes are enough. The stream is not a playable video, because its `moov` holds filler instead of tracks and sample tables.

## What is contested

Embedded metadata is not authenticated. The ComfyUI documentation says it is not a digital signature and should be treated as optional, untrusted input, and that image and video editors may drop it. The lab's PNG is eight pixels wide and says nothing about how large the workflow text is in a real image. The WAV part covers PCM only, and the format also allows float samples and an extensible header. The MP4 part shows the box layout, not the tracks inside `moov`.

## Sources

- [Portable Network Graphics (PNG) Specification (Third Edition)](https://www.w3.org/TR/png-3/)
- [Wave File Specifications](https://www.mmsp.ece.mcgill.ca/Documents/AudioFormats/WAVE/WAVE.html)
- [Multimedia Data Standards Update (IBM and Microsoft), April 15, 1994](https://www.mmsp.ece.mcgill.ca/Documents/AudioFormats/WAVE/Docs/RIFFNEW.pdf)
- [ISO Base Media File Format, Library of Congress format description](https://www.loc.gov/preservation/digital/formats/fdd/fdd000079.shtml)
- [Atoms, QuickTime File Format](https://developer.apple.com/documentation/quicktime-file-format/atoms)
- [FFmpeg Formats Documentation](https://ffmpeg.org/ffmpeg-formats.html)
- [Workflow Metadata](https://docs.comfy.org/development/api-development/workflow-metadata)
- [ComfyUI Custom Node Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_audio.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_audio.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_video.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_video.py)
- [ComfyUI v0.43.0, comfy_api/latest/_input_impl/video_types.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_input_impl/video_types.py)
