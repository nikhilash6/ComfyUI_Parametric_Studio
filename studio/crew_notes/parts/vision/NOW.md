# Vision encoders and picture readers: state on 2026-11-03

Where this file and older notes in this folder disagree, this file and STATE.md win. [inference]

CLIP vision for IP-Adapter: the 11 IP-Adapter templates load a CLIP vision model to read the reference picture. The SD 1.5 and SDXL ViT-H adapters use a ViT-H CLIP vision file, the ViT-G adapters (SDXL base and the SD 1.5 vit-G variant) use clip_vision_g, and the SD 3.5 Large InstantX adapter uses SigLIP (patch 14, 384 px). [code: studio/family_templates/ipa_ip_adapter_sd15.json:17, studio/family_templates/ipa_ip_adapter_sdxl.json:17, studio/family_templates/ipa_ip_adapter_sd15_vit_g.json:17, studio/family_templates/ipa_sd35_large_instantx.json:24-26]

CLIP vision results: on SDXL at weight 0.8 the reference picture won over the words: the mug, its gold rim and dark glass carried over and the asked-for wooden table never appeared. On SD 3.5 Large with SigLIP the look carried over but the mug's shape did not; that run is recorded as weak and kept off the Families page. [run: studio/family_status.json] [code: scripts/record_family_renders.py:13] [claim: commit e162c772, 2026-11-02]

Qwen3-VL reads a picture: a studio template runs Qwen3-VL 4B (fp8) through ComfyUI's core TextGenerate node to say what a picture shows and what looks physically wrong. On the Iris-3B fox render (9.5 s, 6.0 GiB) it gave an accurate description and caught the render's real fault, the stylised steam plume. It also made two errors of its own: it put the steam at the fox's nose when it floats well above, and claimed breath only shows below -20 C, which is wrong. The list was cut at 400 tokens. [code: studio/family_templates/index.json] [run: studio/family_status.json]

InsightFace landmarks: buffalo_l ran on the CPU on an invented adult from World Kit's character library: one face found at score 0.80, with the 106 points on the jaw, brows, eyes, nose and lips. Detection and landmarks only; the restore, swap and identity models that family also covers were not on disk at the time. The InsightFace model zoo is for non-commercial research only. [run: studio/family_status.json]

Cross-attention heatmaps (Which word painted what): two studio nodes swap every SD 1.5 or SDXL cross-attention layer for an exact float32 softmax and keep each picture cell's attention to each prompt token, then group CLIP-L tokens into words and give one heatmap and one mask per word. DiT models are refused. Recording took 1.7 to 10.0 s per render, against 0.8 s for a plain warm SD 1.5 render, at 3.2 to 9.6 GiB. [code: studio/feature_words.py:1-2] [run: studio/sampling_lab/attention.json] [claim: commit db3a269a, 2026-11-02]

Cross-attention checks: each recorded render tests whether a word's map lands in the region it names. Across the four renders with checks, 9 of 14 passed by plain lift and 11 of 14 above each map's own floor. On the SD 1.5 red hat, "hat" scored a 2.96 lift inside the hat while "red" scored 1.44, under the bar. [run: studio/sampling_lab/attention.json]

ControlFoley's image encoder: the add-sound feature sees the clip through Apple's DFN5B-CLIP, which is licensed for research only. That is one reason the sound it makes is labelled non-commercial. [code: studio/foley.py:2, studio/foley.py:18]

Checking outputs with vision models: the studio's checking guide suggests VQAScore first for prompt adherence (it asks a vision-language model whether the picture shows the prompt; recent versions support Qwen3-VL), then OCR at edit distance 0 for quoted text, then face embeddings for identity. None of these is installed or wired into the studio, and the memory use of a small Qwen3-VL scorer was not measured. [docs: docs/CHECKING_OUTPUTS.md]

Caption OCR check: Captions & Sound reads each caption card back off the burned frames with Tesseract OCR. It matched 100% on the voice-over example and 84.2% on the H3 talking example. [run: studio/clipsound_proof.json:4-50]
