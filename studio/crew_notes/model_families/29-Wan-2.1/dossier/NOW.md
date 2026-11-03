# Wan 2.1: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

Every time and peak below is one run on the test machine's 96 GB card, not a promise for other cards. [inference]

Wan-SCAIL-2 now has a render, and STATE.md, rebuilt on 2026-11-03, lists it. On 2026-11-02 the motion_scail2 graph ran through the Motion page on the family's own server in 96.4 s; the 28.2 GiB peak comes from the same graph on a private ComfyUI. An invented man takes over an invented woman's clip, looked at frame by frame. [run: studio/family_status.json]

Wan-SCAIL-2's flaws on that run: 3.4 s at 24 frames a second per graph (longer clips need its next segments, not run here), a face that drifts a little from the picture when the head turns, and small artefacts carried over from the driving clip. [run: studio/motion_proof.json]

Wan 2.1 Causal Forcing image to video rendered on 2026-11-02 from the causal_forcing-framewise file: 61.0 s, 16.1 GiB peak. The record holds no verdict on quality. [run: studio/family_status.json]

InfiniteTalk, which the Wan 2.1 family row lists by licence, rendered through its family server on 2026-11-02: one invented man speaking a made-up line, 3.2 s (81 frames), 78.7 s for the whole call, 33.0 GiB peak. Sync was measured, not listened to: the mouth leads the voice by about 80 ms (correlation 0.57 at the best lag). Its fp8 patch had to be converted to fp16 for ComfyUI's own loader. [run: studio/motion_proof.json, studio/family_status.json]

Wan 2.1 LoRA templates: three family graphs, wan21_t2v_14b, wan21_i2v_14b and wan21_t2v_1p3b, now carry CausVid and lightx2v step-distill LoRA cards at CFG 1. The settings are the studio's own starting point and none has rendered through a recipe. [code: studio/family_templates/wan21_t2v_14b.json, studio/family_templates/wan21_i2v_14b.json, studio/family_templates/wan21_t2v_1p3b.json] [run: studio/lora_recipes.json]

Wan VACE (Wan 2.1 VACE 14B) is listed as three edit tools: video to video, fill a region and widen the frame. Wan 2.1 VACE 14B itself is not on the test machine, so when its file is missing the studio now runs the three templates on the Wan 2.2 VACE-Fun A14B low-noise expert, which has the same 14B layout with VACE blocks. The fill-a-region edit rendered that way on 2026-11-03 and was looked at: 81 frames, coherent; it repainted the masked pan but did not follow the reference picture. Video to video and widen the frame were still queued. Reservations of 62 GiB (outpaint, video to video) and 46 GiB (inpaint) are planned figures, not measured peaks. [code: studio/edits.py:17, studio/edits.py:21-22, studio/names.py:19] [claim: studio commit 661f997a, 2026-11-03]