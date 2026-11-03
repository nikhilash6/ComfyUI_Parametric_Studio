# Model families: state on 2026-11-03

This specialist's records cover 3 studio families: ACE-Step-1.5, Mini-Max-Music3, yue2. 3 of them have a recorded render. Older notes in this folder can be out of date; where they disagree, this record of what ran wins. [run: studio/family_status.json]

### ACE-Step-1.5

ACE-Step-1.5 is an audio family, era 2026, licence MIT (ACE-Step's repository); the ComfyUI repackage is tagged Apache-2.0: has a recorded render. What it does, from its ComfyUI template notes: Generate high-quality audio from text prompts using the 4B parameter ACE-Step 1.5 XL model. [run: studio/family_status.json]

ACE-Step-1.5 last recorded render: template audio_ace_step1_5_xl_base, 26.0 s, peak 51.1 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

ACE-Step-1.5 model files with a recorded render on 2026-11-03: ace_1.5_vae.safetensors, acestep_v1.5_turbo.safetensors, acestep_v1.5_xl_base_bf16.safetensors, acestep_v1.5_xl_turbo_bf16.safetensors, qwen_0.6b_ace15.safetensors, qwen_1.7b_ace15.safetensors. Runs: ace-step-1-5/audio_ace_step1_5_xl_base (72.8 s); looked at: spectrogram only: structured sound, not listened to; ace-step-1-5/audio_ace_step1_5_xl_turbo (25.6 s); looked at: spectrogram only: structured sound, not listened to; ace-step-1-5/audio_ace_step_1_5_split (25.3 s); looked at: spectrogram only: structured sound, not listened to. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Mini-Max-Music3

Mini-Max-Music3 is an audio family, era 2026, licence MiniMax-Music3 Community License (the ComfyUI repackage is tagged Apache-2.0; the studio follows MiniMax's own text): commercial products must show "MiniMax-Music3", and over US$20,000,000 yearly revenue needs MiniMax's written authorization: has a recorded render. What it does, from its notes: Full songs from a style description and optional lyrics. [run: studio/family_status.json]

Mini-Max-Music3 last recorded render: template music3_api, 28.4 s, peak 43.6 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Mini-Max-Music3 has 2 studio templates: music3_dav_full, music3_turbo8. [code: studio/family_templates/index.json]

Mini-Max-Music3 model files with a recorded render on 2026-11-03: minimax_music3_dav.safetensors, minimax_music3_dav_full.safetensors, minimax_music3_dit_fp16.safetensors, minimax_music3_text_encoder_pruned_int8_convrot.safetensors, minimax_music3_turbo_lora_8step.safetensors. Runs: mini-max-music3/audio_minimax_music_3 (65.3 s); looked at: spectrogram only: structured sound, not listened to; mini-max-music3/music3_dav_full (55.6 s); looked at: 60 s of audio, -16.3 LUFS, LRA 5.1, peak +0.2 dBFS (touches full scale); the spectrum shows a soft intro then steady beat transients over low harmonic content, no silence (read from the spectrum and loudness, not listened to) (2026-11-02); mini-max-music3/music3_turbo8 (61.0 s); looked at: 60 s of audio at 8 steps, -18.6 LUFS, LRA 9.4, peak -1.4 dBFS; the spectrum shows a quiet intro then regular beat transients and harmonic content to the end, no silence (read from the spectrum and loudness, not listened to) (2026-11-02). [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### yue2

yue2 is an audio family, era 2026, licence CC BY-NC 4.0: has a recorded render. What it does, from its ComfyUI template notes: Create a new version of a song from reference audio with YuE2. Preserve the original melody while changing the musical style, vocals, lyrics, and arrangement. [run: studio/family_status.json]

yue2 last recorded render: template audio_yue2_text2music, 55.4 s, peak 6.9 GiB, 2026-11-01, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

yue2 model files with a recorded render on 2026-11-03: yue2_3b_int8_convrot.safetensors. Runs: yue2/audio_yue2_text2music (55.4 s); looked at: spectrogram only: structured sound, not listened to. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]
