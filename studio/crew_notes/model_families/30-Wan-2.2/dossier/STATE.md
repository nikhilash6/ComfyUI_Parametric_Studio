# Model families: state on 2026-11-03

This specialist's records cover 4 studio families: TurboWan2.2-I2V, Wan2.2, Wan2.2-Animate, Wan2.2-Dancer. 2 of them have a recorded render. Older notes in this folder can be out of date; where they disagree, this record of what ran wins. [run: studio/family_status.json]

### TurboWan2.2-I2V

TurboWan2.2-I2V is a video family, era 2025, licence Apache-2.0: its template validated; no render on record. What it does, from its knowledge base: A quantized/distilled variant for faster inference. [run: studio/family_status.json]

### Wan2.2

Wan2.2 is a video family, era 2025, licence Apache-2.0: has a recorded render. What it does, from its ComfyUI template notes: Creates a smooth video using 6 key frames. It auto fills in the motion between frames and stitches the segments together seamlessly. [run: studio/family_status.json]

Wan2.2 last recorded render: template wan22_5b_t2v_api, 20.0 s, peak 68.1 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Wan2.2 has 1 studio template: wan22_14b_t2v_kj. [code: studio/family_templates/index.json]

Wan2.2 model files with a recorded render on 2026-11-03: Wan2_2-T2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors, Wan2_2-T2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors, wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors, wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors, wan2.2_fun_control_5B_bf16.safetensors, wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors. Runs: matrix-3d/video_wan2_2_5B_ti2v (90.7 s); looked at: thumbnail sheet, two frames differ, on brief; wan2-2/templates-6-key-frames (41.0 s); not looked at yet; wan2-2/video_wan2_2_14B_fun_camera (307.7 s); looked at: thumbnail sheet, two frames, camera moves; wan2-2/video_wan2_2_14B_fun_control (232.0 s); looked at: thumbnail sheet, two frames, follows the control clip; wan2-2/video_wan2_2_5B_fun_control (90.9 s); looked at: thumbnail sheet, two frames, follows the clip's framing. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Wan2.2-Animate

Wan2.2-Animate is a video family, era 2025, licence Apache-2.0: has a recorded render. What it does, from its ComfyUI template notes: Animate a still character using a driving video with Wan Animate 2, transferring motion directly from video frames without any pose extraction or skeleton preprocessing. The output preserves the reference character's identity while generating a fresh background and camera movement from your text pro [run: studio/family_status.json]

Wan2.2-Animate last recorded render: template video_wan_animate2_distilled, 2.0 s, peak 6.9 GiB, on the test machine, one run. Not a promise for other machines. [run: studio/family_status.json]

Wan2.2-Animate has 1 studio template: motion_wan_animate2. [code: studio/family_templates/index.json]

Wan2.2-Animate model files with a recorded render on 2026-11-03: Wan2_1_VAE_bf16.safetensors, wan_animate_2_distill_int8_convrot.safetensors. Runs: Wan2.2-Animate/video_wan_animate2_distilled (families/wan2-2-animate_0.webp); not looked at yet. [run: studio/crew_notes/evidence/model_proof_2026-11-03.tsv]

### Wan2.2-Dancer

Wan2.2-Dancer is a video family, era 2026, licence Apache-2.0 (ComfyUI repackage): its template validated; no render on record. What it does, from its ComfyUI template notes: Generate minute-scale coherent dance videos from music using a hierarchical Wan Dancer framework. Input a music file and reference image to produce high-resolution dance videos with global structure and temporal continuity. [run: studio/family_status.json]

Wan2.2-Dancer last recorded test result: empty-output, template video_wan_dancer. Do not assume it renders. [run: studio/family_status.json]

Wan2.2-Dancer has 1 studio template: motion_wan_dancer. [code: studio/family_templates/index.json]
