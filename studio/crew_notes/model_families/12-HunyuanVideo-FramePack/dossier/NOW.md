# HunyuanVideo and FramePack: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

HunyuanVideo 1.5 rendered on 2026-11-03 on its own family server: template video_hunyuan_video_1.5_720p_t2v (ComfyUI's own 720p text-to-video graph), seed 20261103, 868 s, 65.2 GiB peak. The clip was looked at frame by frame. One run on the test machine; at that peak it needs a large card. Its licence, the Tencent Hunyuan Community License, does not apply in the EU, the UK or South Korea. [run: studio/family_status.json]

HunyuanVideo 1.5's 720p text-to-video fp16 file (16.7 GB) was downloaded on 2026-11-03, which is what let the render above run. The 1080p super-resolution distilled file and the older HunyuanVideo 720p bf16 file were not fetched. [run: studio/family_status.json] [claim: studio disk check 2026-11-03]

HunyuanVideo 1.5 prompting is covered by GUIDE.md, added in the last session from Tencent's repository, its prompt handbook and earlier-studio tests. Only the one 720p render above has run, from ComfyUI's own template, so the guide's rules are still untested here. [docs: studio/crew_notes/model_families/12-HunyuanVideo-FramePack/dossier/GUIDE.md]

Capybara, an instruction video editor built on HunyuanVideo 1.5, is listed on the Edit page but marked not shipped. It is under the Tencent Hunyuan Community License, which limits territories and user counts, so the studio does not download it. HunyuanVideo's own licence does not apply in the EU, the UK or South Korea. [code: studio/edits.py:19] [run: studio/family_status.json]

FramePack has no family row, template or render in the studio. It is in this specialist's name as a topic only. [run: studio/family_status.json] [inference]
