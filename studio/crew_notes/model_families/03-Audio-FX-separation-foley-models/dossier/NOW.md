# Sound effects, foley and delivery levels: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

## Add sound with ControlFoley (Captions & Sound page)

Add sound on the Captions & Sound page runs ControlFoley (Xiaomi Research, large 44 kHz) on a silent clip, as a ComfyUI graph. It watches the clip and makes sound for it; a few words can steer it, but the proof runs used no words at all. [code: studio/foley.py:1-4] [code: studio/feature_clipsound.py:1-5] [code: workflows/clipsound_foley_api.json]

ControlFoley is non-commercial and off the default path. Its weights are CC BY-NC 4.0 and the Apple DFN5B-CLIP image encoder it loads is research only, so the model is marked not default and not commercial, and every run is refused unless the person ticks a box saying the sound is for non-commercial use. A licence receipt JSON is written beside each result, listing every licence the run used. [code: studio/foley.py:15-31] [code: studio/foley.py:74-86] [code: studio/foley.py:135-139] [test: tests/test_clipsound.py]

ControlFoley's licence list in the studio has six entries. CC BY-NC 4.0 for the ControlFoley weights and for MusicGen-style and MERT-v1-95M; the Apple Machine Learning Research Model License for DFN5B-CLIP; MIT for the BigVGAN v2 44 kHz vocoder; Apache-2.0 and MIT for the T5-base, BERT-base, BART-base and RoBERTa-base text encoders; Apache-2.0 for the code and ComfyUI nodes. The strictest one decides: research and other non-commercial use only. [code: studio/foley.py:15-27]

ControlFoley settings in the studio: steps 10, 25 or 40 (25 is the pack's fixed default), guidance 1 to 10 with 4.5 by default, seed 42 by default, and clips from 0.7 s to 30 s, the video loader's own limit. This replaces the older PITFALLS and RECIPES lines saying ControlFoley's settings were not in the sources. [code: studio/foley.py:10-12] [code: studio/foley.py:74-86]

ControlFoley readiness is checked without downloading. The studio asks the Hugging Face cache the same question the node asks before it downloads, needs a complete snapshot with real weight files for each of eight repos, and treats a cache holding only a tokenizer as missing. When anything is missing the run is refused with a list, because the node would otherwise download during the run. [code: studio/foley.py:33-66] [code: studio/feature_clipsound.py:241-253]

Add sound keeps every frame of the picture. ffmpeg copies the video stream packet for packet and adds the new sound as the only audio track (AAC 192k). The sound is trimmed to the picture's length instead of using -shortest, which dropped the last frames when the picture is copied. Both proof clips came back with the picture byte-identical. [code: studio/foley.py:113-120] [run: studio/clipsound_proof.json]

Add sound levels every result to -16 LUFS under a -1.5 dBTP true-peak ceiling, with ffmpeg loudnorm in two passes (measure, then linear levelling), then measures it again with ffmpeg's EBU R128 filter. The raw loudness is kept beside the levelled one. [code: studio/foley.py:95-120] [code: studio/feature_clipsound.py:212-235]

ControlFoley proof, waves on rocks: a silent Wan clip, bf16, 25 steps, seed 42, no words. 42.5 s wall time at 13.6 GiB peak, one run on the test machine. Raw -20.4 LUFS and -3.7 dBTP, levelled to -15.6 LUFS and -1.5 dBTP. [run: studio/clipsound_proof.json]

ControlFoley proof, the VOID flambé clip: the studio's VOID removal example, same settings. 55.2 s wall time at 13.6 GiB peak, one run on the test machine. As generated it was too loud and clipped, -12.4 LUFS with a true peak of +0.5 dBTP; levelled it measured -16.1 LUFS and -3.1 dBTP. [run: studio/clipsound_proof.json]

ControlFoley showed no measurable event sync. Against the picture's motion, the whole-clip cross-correlation was r 0.019 for the waves (p 0.90 against 2000 randomly shifted copies) and r 0.041 for the flambé (p 0.79). On the waves the strongest sound near each splash was only 1.5 to 1.9 times the clip's typical onset strength. On the flambé two flare-ups at 3.67 and 4.08 s had a strong sound within 7 ms, but over the whole clip it was no better than chance. The model's own description says its sound is timed to the picture; this measurement did not find that. [run: studio/clipsound_proof.json] [code: studio/foley.py:29-31]

ControlFoley results are labelled as generated ambience. The page and every job say "Generated ambience for the whole clip. It doesn't place sounds on visible events (measured: no better than chance)." Nobody has listened to either proof sound: loudness, onsets and sync were all measured by programs. [code: studio/foley.py:26] [run: studio/clipsound_proof.json]

ControlFoley needed a local patch to run on the test machine: its BigVGAN loader passed a Hugging Face download argument the installed hub library no longer accepts. Two Python packages it needs (laion_clap 1.1.7 and torchlibrosa 0.1.0) were installed without their dependencies, and it ran with transformers 5.21 although the pack declares transformers below 5. [claim: studio test run 2026-11-02]

## Delivery levels in studio/audio_master.py

The studio's mastering module, used by the Dub & Voice page, targets -14 LUFS integrated with a true peak at or under -1 dBTP and a 0.5 LU tolerance. While a voice speaks the music is drawn 12 dB under it, and 6 dB under between lines, with 0.25 s fades and pauses shorter than 0.45 s kept ducked. Add sound uses its own, quieter target of -16 LUFS and -1.5 dBTP, so the two pages do not share one delivery level. [code: studio/audio_master.py:1-8] [code: studio/foley.py:95]

Voiceover mastering proof: a Qwen3-TTS voice over a Music 3 instrumental. The mix measured -14.1 LUFS, LRA 1.9, true peak -1.5 dBTP, and passed; mastering took 0.5 s. The music sat 15.3 dB under the voice while it spoke, deeper than the 12 dB asked, because the score is quieter in those stretches than on average. One run on the test machine, measured by ffmpeg, not listened to. [run: studio/dub_proof.json]

Only the voiceover path on the Dub & Voice page runs the mastering step; a dub is laid on the clip without it. The DubIt proof came out at -11.5 LUFS with a true peak of -0.6 dBTP, unmastered and hotter than the voiceover path's -14 LUFS. The voiceover form accepts targets from -24 to -9 LUFS and true peaks from -3 to -0.5 dBTP. [code: studio/feature_dub.py:365] [code: studio/feature_dub.py:492] [run: studio/dub_proof.json]
