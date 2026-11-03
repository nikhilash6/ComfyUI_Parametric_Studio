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

## Final session findings, 2026-11-03

Music 3 turbo is a studio template: ComfyUI's Music 3 graph with guillaume127's 8-step turbo LoRA on the DiT at strength 1.0, 8 steps, cfg 1.6, euler sampler, simple scheduler, settings taken from the LoRA's card. One render on 2026-11-02 took 61.0 s at 15.9 GiB peak, seed 238203647, on the test machine, one run. [code: studio/family_templates/music3_turbo8.json:80-90] [code: studio/family_templates/music3_turbo8.json:150-160] [run: studio/family_status.json:6118-6129]

Music 3 with the full DAV is a studio template that decodes with minimax_music3_dav_full (292 MB) in place of the 207 MB DAV decoder, keeping 30 steps and cfg 1.7. One render on 2026-11-02 took 55.6 s at 14.7 GiB peak, seed 1450167393, on the test machine, one run. [code: studio/family_templates/music3_dav_full.json:38] [code: studio/family_templates/music3_dav_full.json:83-84] [run: studio/family_status.json:6106-6117]

Music 3 turbo and full DAV were checked by loudness and spectrum only: each made about 60 s of music with a steady beat, harmonic content and no silence. Nobody listened, so don't say which sounds better. [claim: commit 2099f6d7, 2026-11-02]

Music 3 full DAV has an unknown origin. The template index says its origin was not identified, and its download link points to the ordinary 207 MB DAV file, not a 292 MB one, so following that link will not get the file that rendered. The turbo LoRA has no download link in the index at all. [code: studio/family_templates/index.json:3495-3520] [code: studio/family_templates/index.json:3527-3559]

The Music page now shows a whole music video, "Light the Wreckage" by Wren Halloway, an invented singer. It is labelled "Made before this studio": it was made on 2026-10-06 with the earlier studio's scripts, and no page or graph in this studio made it. [code: studio/music_models.json:676-685] [code: studio/music_models.json:706-707] [test: tests/test_music_page.py]

Wren Halloway video credits: the 175 s song and vocals are MiniMax Music 3, seed 9140, mastered to -14 LUFS. The 28 shots are LTX-2.5 distilled two-stage image to video at 1344x768 with the song locked into the video's audio. The stills of Wren and the four sets are CyberRealistic Flux v2.5, a FLUX.1 dev fine-tune under the FLUX.1 dev non-commercial licence. [code: studio/music_models.json:686-705]

Wren Halloway video flaws: it is a first cut of the first take of all 28 shots. 13 shots failed the lip-sync check and retakes stopped after 7, so in some shots her mouth drifts from the words. Whisper (distil-large-v3) made out 240 of the 260 lyric words in the finished mix. The page copy is scaled to 720p, 18 MiB, from the 1080p cut. [code: studio/music_models.json:708-712]

A Music 3 instrumental made in the studio was the music bed for the Dub & Voice page's voiceover proof. Ducked under a Qwen3-TTS voice and mastered, the mix measured -14.1 LUFS and -1.5 dBTP; the music sat 15.3 dB under the voice while it spoke, deeper than the 12 dB asked, because the score is quieter there than on average. [run: studio/dub_proof.json]
