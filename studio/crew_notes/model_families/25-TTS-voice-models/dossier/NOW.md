# Speech, voice cloning, dubbing and captions: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

Every number below was measured by a program: Whisper for words, ffmpeg for loudness, one voice encoder for likeness. No person has listened to any of these voices, so don't describe how they sound. [run: studio/dub_proof.json] [run: studio/clipsound_proof.json]

## Dub & Voice page

The Dub & Voice page has three jobs: a voiceover laid on music, ducked and mastered; a voice clone, only with consent; and a dub of a clip into another language. Whisper large-v3 writes down what is said, the local LLM or the person translates it, and every dub is transcribed again in the new language so its word error rate travels with the result. Speech models run in their own process, never inside ComfyUI. [code: studio/feature_dub.py:1-7]

Dub & Voice voiceover proof: Qwen3-TTS 1.7B CustomVoice, built-in speaker Ryan, seed 7, read a 9.28 s line in 18.5 s at 5.0 GiB peak on the test machine, one run. Whisper's word error rate was 0.0345. Laid over a Music 3 instrumental, it was ducked and mastered to -14.1 LUFS and -1.5 dBTP. [run: studio/dub_proof.json]

Dub & Voice voice clone needs consent. Cloning is refused unless the person says the reference is their own voice, that the speaker gave permission, or that it is a made-up (synthetic) voice, and a consent JSON is written beside the clone. Without own voice or permission, the page offers to design a voice first and clone that. [code: studio/feature_dub.py:22] [code: studio/feature_dub.py:27] [code: studio/feature_dub.py:267-272] [code: studio/feature_dub.py:478-483] [test: tests/test_feature_dub.py]

Dub & Voice clone proof: Qwen3-TTS 1.7B VoiceDesign made a reference voice from a written description (14.4 s, 4.8 GiB peak), then Qwen3-TTS 1.7B Base cloned it on a new line (17.5 s, 5.1 GiB peak, 5.44 s of speech). Likeness to the reference was 0.888 against 0.598 for a different voice, by cosine of the Chatterbox voice encoder's embeddings; word error rate 0.056. The consent file records it as synthetic, with the reference's SHA-256. Likeness is one encoder's opinion. [run: studio/dub_proof.json]

Dub & Voice voice-only dub: Qwen3-TTS 1.7B Base cloned the clip's own voice and read a Spanish line, sped up 1.23 times to fit the clip, in 18.7 s at 5.1 GiB peak. Likeness to the source voice was 0.870. Word error rate was 0.2: Whisper heard "es claro" before the line, because the clone carried the tail of the source's half-finished English sentence into the new voice. The mouth still moves to the English words. [run: studio/dub_proof.json]

Dub & Voice relip: the same cloned Spanish voice, then the Motion page's LatentSync 1.6 route redraws the mouth. 142.3 s at 14.6 GiB peak, word error rate 0.2 from the same carried-over "es claro", and the lower face comes out a little softer than the rest of the frame. [run: studio/dub_proof.json]

Dub & Voice DubIt: LTX-2.5 distilled int8 with the LTX-2.3 DubIt IC-LoRA 0.9 redraws the mouth and speaks the line in one pass, using the clip's sound as the voice reference. The proof made 121 frames at 768x768, seed 7, in 53.2 s at 43.1 GiB peak, one run on the test machine. Whisper heard the Spanish line exactly, word error rate 0.0. The page caps a DubIt render at 5.05 s, the 121 frames at 24 fps that DubIt's example graph uses, and plans for a 44 GiB peak. [run: studio/dub_proof.json] [code: studio/feature_dub.py:23-24] [code: studio/feature_dub.py:105] [code: workflows/dub_ltx_api.json]

DubIt's voice is only a little like the speaker's: likeness 0.63 to the source voice, against 0.87 for the Qwen3-TTS clone and about 0.60 for an unrelated stock voice. Curls of hair shift between frames, and the sound comes out unmastered at -11.5 LUFS and -0.6 dBTP. [run: studio/dub_proof.json]

DubIt is refused on a ComfyUI started with --bf16-vae or --fp16-vae. DubIt encodes the clip's sound, and ComfyUI's LTX audio encoder stops with a bf16/float mismatch when the VAE is forced to half precision. The proof ran on a separate ComfyUI 0.43.0 started with --fp32-vae; otherwise pick the new-voice-then-LatentSync route. [code: studio/feature_dub.py:52-63] [run: studio/dub_proof.json] [test: tests/test_feature_dub.py]

Dub & Voice licences: Qwen3-TTS is Apache-2.0; DubIt and LTX-2.5 are under the LTX-2 Community License, which requires generated content to be labelled; LatentSync's code is Apache-2.0 and its weights OpenRAIL++, but its face finder (InsightFace buffalo_l) is non-commercial. [code: studio/feature_dub.py:26]

## Voice personas for the design models

The Voices page has 56 ready voice personas built from 21 voice trait groups (presentation, adult age bands, language, accents, register, timbre, pace, energy, mood, delivery style, recording and more). On a design model's form, "Start from a persona" fills the voice description box, which stays editable. [code: studio/feature_voice_personas.py:1-3] [code: studio/web/voice_personas.js:1-2] [test: tests/test_voice_personas.py]

Voice persona rules: every description opens "An adult ...", ages are 21 and over, and no phrase names a person, character or brand (a brand word list and the studio's safe-for-work filter check every option). Over the 300-character limit the voice runner keeps, the least important traits are dropped first and the reply names them; traits that pull against each other (slow and fast, soft and loud, low and high) come back as warnings. [code: studio/feature_voice_personas.py:11-12] [code: studio/feature_voice_personas.py:56-80] [code: studio/feature_voices.py:73]

No render was made from a persona when they were added, so nothing is known yet about how well the design models follow them. The picker itself says design models read a description as a guide, not a promise. [code: studio/web/voice_personas.js:13] [inference]

## Qwen3-TTS VoiceDesign in a commercial

The perfume commercial "Nocturne No. 7" for the invented house Maison Ombrelle was voiced by Qwen3-TTS 1.7B VoiceDesign from a written description of a soft, slow, husky voice. Its mix measured -15.0 LUFS and -1.3 dBTP. It was rendered on 2026-11-02 and nobody listened. [run: studio/commercial_proof.json]

Whisper heard only 53.3% of the perfume voice-over script, mostly for spelling reasons: it wrote "No. 7" as "number seven", "Nocturne" as "Nocturn" and "Ombrelle" as "Ombrel", which a plain word match counts as misses. Invented product names score low with Whisper even when the read is right. [run: studio/commercial_proof.json] [inference]

## Kokoro voices for the crew

Each crew member speaks with a Kokoro voice. Only Kokoro's 28 English voices read English well; the others garbled it when transcribed with Whisper, so ten English voices are used twice at a clearly different pace. [code: studio/crew.py:381]

## Captions & Sound: speech captions

Captions on the Captions & Sound page come from Whisper's timed words, written as SRT and WebVTT and, if asked, drawn onto a copy of the clip by ffmpeg with a real system font, so the letters are never painted by a model. Whisper runs in its own process on the CPU unless told otherwise, so it never touches a running graph. [code: studio/captions.py:1-3] [code: studio/feature_clipsound.py:1-5]

Captions use three Whisper models from the Voices page's catalogue: distil-large-v3 (English only), large-v3 for other languages, and tiny. Asking the English-only model for another language is refused. [code: studio/feature_clipsound.py:16] [code: studio/feature_clipsound.py:32-42] [code: studio/feature_clipsound.py:158]

Captions proof on a silent LTX-2.5 clip voiced by Kokoro am_michael: Whisper took 4.4 s on the CPU (no VRAM), the whole job 5.1 s for an 8.4 s clip. Whisper matched 94.7% of the script's words, and OCR read the burned captions back at 100%. One fault: Whisper wrote "ffmpeg" as "FFM peg", so one word is wrong and split across two caption cards. The audio track was checked byte for byte and left unchanged. [run: studio/clipsound_proof.json]

Captions proof on a MiniMax H3 clip with its own speech: 4.2 s of Whisper on the CPU, OCR read the burned captions back at 84.2%. H3's speech is unclear in places and the captions say what Whisper heard ("So I have you on a wait moment here"); there was no script to score against. [run: studio/clipsound_proof.json]
