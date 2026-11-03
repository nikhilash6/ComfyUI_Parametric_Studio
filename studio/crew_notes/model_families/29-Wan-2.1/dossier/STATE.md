# Model families: state on 2026-11-03

This specialist's records cover 2 studio families: Wan-SCAIL-2, Wan2.1. 2 of them have a recorded render. Older notes in this folder can be out of date; where they disagree, this record of what ran wins. [run: studio/family_status.json]

### Wan-SCAIL-2

Wan-SCAIL-2 is a video family, era 2026, licence MIT (ComfyUI repackage); the lightx2v distill LoRA is Apache-2.0: has a recorded render. What it does, from its ComfyUI template notes: Upload 1 reference character image and 1 driving video. Generate an animated video of the character matching the driving video's motion. Ideal for character animation, in-video character replacement, and motion transfer projects. [run: studio/family_status.json]

Wan-SCAIL-2 last recorded render: template motion_scail2, 96.4 s, peak 28.2 GiB, 2026-11-02, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Wan-SCAIL-2 has 1 studio template: motion_scail2. [code: studio/family_templates/index.json]

Wan-SCAIL-2 model files with a recorded render on 2026-11-03: lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors, wan2.1_14B_SCAIL_2_nvfp4_mxpf8_mix.safetensors, wan2.1_SCAIL_2_DPO_lora_bf16.safetensors. Runs: Wan-SCAIL-2/motion_scail2 (motion/scail2_0.mp4); not looked at yet. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Wan2.1

Wan2.1 is a video family, era 2025, licence Apache-2.0; InfiniteTalk Apache-2.0, its wav2vec2 encoder MIT: has a recorded render. What it does, from its ComfyUI template notes: Image editing powered by video models' dynamic understanding, creating physically plausible results while preserving character and style consistency. [run: studio/family_status.json]

Wan2.1 last recorded render: template text_to_video_wan, 14.0 s, peak 45.6 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Wan2.1 has 1 studio template: motion_infinitetalk. [code: studio/family_templates/index.json]

Wan2.1 model files with a recorded render on 2026-11-03: causal_forcing-framewise.safetensors, clip_vision_h.safetensors, lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors, wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors, wan2.1_fun_control_1.3B_bf16.safetensors, wan2.1_fun_inp_1.3B_bf16.safetensors. Runs: wan2-1/text_to_video_wan (61.8 s); looked at: thumbnail sheet, two frames differ, on brief; wan2-1/video_causal_forcing_i2v (61.0 s); looked at: thumbnail sheet, two frames, starts from the picture and moves; wan2-1/video_wan2.1_alpha_t2v_14B (96.1 s); not looked at yet; wan2-1/video_wan2.1_fun_camera_v1.1_1.3B (46.0 s); looked at: thumbnail sheet, two frames differ, on brief; wan2-1/wan2.1_fun_control (164.4 s); looked at: thumbnail sheet, two frames differ, on brief. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]
