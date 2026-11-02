# Music page: state on 2026-11-01

The Music page is in the studio's rail, and every music model has its own page at #music/ID. Where this file and older notes in this folder disagree, this file wins. Nobody has listened to any render on it: a program measured them and Whisper transcribed them, so don't describe how anything sounds. [code: studio/feature_music.py:1-3] [run: studio/music_proof.json]

## The brief

Every render used one original brief, written for the page: the song "Paper Boats", seed 7701, a 75 s ceiling. Models with no lyric input got the instrumental line. [run: studio/music_proof.json]

## What rendered

MiniMax Music 3: 70.0 s long, -12.5 LUFS, true peak 0.5 dB, 161.5 BPM found, rendered in 69.6 s at 23.5 GiB peak on the test machine, one run, not a promise for others. Whisper matched 12 of 12 unique lyric lines. Licence: MiniMax-Music3 Community License. [run: studio/music_proof.json]

ACE-Step 1.5 XL Turbo: 75.0 s long, -12.4 LUFS, true peak 0.1 dB, 73.8 BPM found, rendered in 16.8 s at 19.4 GiB peak on the test machine, one run, not a promise for others. Whisper matched 12 of 12 unique lyric lines. Licence: MIT (ACE-Step's own repository). [run: studio/music_proof.json]

ACE-Step 1.5 XL Base: 75.0 s long, -10.8 LUFS, true peak 0.3 dB, 73.8 BPM found, rendered in 35.9 s at 19.5 GiB peak on the test machine, one run, not a promise for others. Whisper matched 12 of 12 unique lyric lines. Licence: MIT (ACE-Step's own repository). [run: studio/music_proof.json]

ACE-Step 1.5 Turbo: 75.0 s long, -11.0 LUFS, true peak 0.4 dB, 143.6 BPM found, rendered in 23.0 s at 10.1 GiB peak on the test machine, one run, not a promise for others. Whisper matched 8 of 12 unique lyric lines. Licence: MIT (ACE-Step's own repository). [run: studio/music_proof.json]

YuE2 3B (int8): 75.0 s long, -13.6 LUFS, true peak 0.1 dB, 143.6 BPM found, rendered in 28.9 s at 5.5 GiB peak on the test machine, one run, not a promise for others. Whisper matched 8 of 12 unique lyric lines. Licence: CC BY-NC 4.0. [run: studio/music_proof.json]

YuE2 3B (bf16): 75.0 s long, -13.9 LUFS, true peak 0.2 dB, 143.6 BPM found, rendered in 39.9 s at 10.9 GiB peak on the test machine, one run, not a promise for others. Whisper matched 8 of 12 unique lyric lines. Licence: CC BY-NC 4.0. [run: studio/music_proof.json]

Stable Audio Open 1.0: 47.0 s long, -18.4 LUFS, true peak -5.1 dB, 76.0 BPM found, rendered in 10.2 s at 3.4 GiB peak on the test machine, one run, not a promise for others. No lyrics to check. Licence: Stability AI Community License. [run: studio/music_proof.json]

DiffSynth-Music: 75.0 s long, -11.9 LUFS, true peak -0.6 dB, 143.6 BPM found, rendered in 6.0 s at 11.4 GiB peak on the test machine, one run, not a promise for others. Whisper matched 12 of 12 unique lyric lines. Licence: Apache-2.0. [run: studio/music_proof.json]

## Models with no render on the page

Stable Audio 3 has no render on the page. It is listed for: Newer Stable Audio: medium, small music, small sound effects. Licence: Stability AI Community License. [code: studio/music_models.json]

MuLaCover has no render on the page. It is listed for: Cover songs and remixes, from reference music or MIDI. Licence: CC BY-NC 4.0. [code: studio/music_models.json]

Magenta RealTime 2 has no render on the page. It is listed for: Live music you steer as it plays, on the device. Licence: Apache-2.0 code, CC BY 4.0 weights. [code: studio/music_models.json]

SongGeneration v2 has no render on the page. It is listed for: Song generation, run through a community node pack. Licence: Unknown: the mirror states none. [code: studio/music_models.json]

TangoFlux has no render on the page. It is listed for: Fast text to sound. Sound effects more than songs. Licence: Non-commercial research use. [code: studio/music_models.json]

MusicGen Small has no render on the page. It is listed for: The small, older instrumental generator. Licence: CC BY-NC 4.0. [code: studio/music_models.json]

## Change a song

ACE-Step cover: made a real take, 70.0 s, -11.9 LUFS. ACE-Step 1.5 Turbo with his Cover guider, in a new style. It keeps the source's structure. [run: studio/music_proof.json]

YuE2 cover: made a real take, 69.5 s, -13.2 LUFS. ComfyUI's own YuE2 cover graph: SheetSage reads the melody, YuE2 re-sings it in a new style. [run: studio/music_proof.json]

ACE-Step repaint and extend: made a real take, 85.0 s, -12.1 LUFS. His Edit guider redoes 30 to 40 s and adds 15 s at the end. Against the source, the loudness shape correlated 0.95 and 0.91 outside the repainted stretch and 0.36 inside it, so the song's shape held. The waveform didn't match anywhere (about 0.08), so the rest is regenerated rather than kept. His post-processor, wired in here, handed back the source unchanged, so this take doesn't use it. [run: studio/music_proof.json]

Vocals, extracted: made a real take, 70.0 s, -14.6 LUFS. ACE-Step 1.5 XL Base with his Extract guider, asked for the vocals only. The model generates the stem, so it's a new performance of that part rather than a clean separation. [run: studio/music_proof.json]

Drums, extracted: made a real take, 70.0 s, -17.7 LUFS. The same guider, asked for the drums only. Generated, not separated. [run: studio/music_proof.json]

Bass, extracted: made a real take, 70.0 s, -21.8 LUFS. The same guider, asked for the bass only. Generated, not separated. [run: studio/music_proof.json]

## RyanOnTheInside

RyanOnTheInside wrote the audio-reactive idea and the ACE-Step guiders the page shows. His pack is ComfyUI_RyanOnTheInside, MIT, at https://github.com/ryanontheinside/ComfyUI_RyanOnTheInside and it is not bundled. It ran on a separate ComfyUI; its nodes are called by name in workflows/music_roti_*.json, which need it installed, and /api/music/run answers 409 with how to install it when ComfyUI doesn't have it. [code: studio/feature_music.py] [code: studio/music_models.json]

Before installing his pack in a shared ComfyUI: On load it deletes and rewrites its own folder inside ComfyUI's web/extensions, so it should not go straight into a shared install. nodes/acestep/patches.py replaces one ComfyUI helper, reshape_mask, for everyone in that process. Its Open-Unmix node runs torch.hub.load, which downloads and runs code and weights from GitHub the first time. That node wasn't run for this page. The extend and repaint guiders download silence_latent.pt from ACE-Step's Hugging Face page the first time, loaded with weights_only=True. [code: studio/music_models.json]

The reactive video is real output of his FlexAudioVisualizerCircular, FlexImageBloom and FlexImageChromaticAberration, tinted yellow afterwards. The ring beside it is the page's own drawing from numbers his AudioFeatureExtractor made, and is not a render. [run: studio/music_proof.json]

## Choosing

Sell the song: ACE-Step 1.5 is MIT; MiniMax Music 3 needs its name shown prominently; YuE2, MuLaCover, TangoFlux and MusicGen are non-commercial. For how they compare on this one brief, read the measurements above and say they come from one run. [code: studio/music_models.json]
