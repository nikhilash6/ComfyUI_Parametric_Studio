# Third-party notices

This project is AGPL-3.0-or-later. It bundles or builds on the following, each under its own licence (all are compatible with AGPL-3.0, except where the note under the table says otherwise):

| Component | Where | Licence |
|---|---|---|
| Preact 10.24.3 | `studio/web/vendor/preact.mjs`, `hooks.mjs` (licence text beside them) | MIT |
| htm 3.1.1 | `studio/web/vendor/htm.mjs` | Apache-2.0 |
| three.js r160 (core, OrbitControls, GLTFLoader, BufferGeometryUtils) | `studio/web/vendor/` | MIT |
| awesome-claude-agents (role playbook excerpts) | `psn/subagents/playbooks/` (licence file included) | MIT |
| Archivo (font) | `studio/web/vendor/fonts/` (licence text beside it) | SIL OFL 1.1 |
| Inter (font) | `studio/web/vendor/fonts/` (licence text beside it) | SIL OFL 1.1 |
| STIX General, regular and italic (font, subset to the characters the Sampling Lab's equations use) | `studio/web/vendor/fonts/stix-math-*.woff2` (licence text beside it) | SIL OFL 1.1 |
| MiniMax-Music3 caption-rewriter library (style names, tempos, keys and short excerpts of its templates, at upstream commit `945655064d59`) | official styles in `studio/music3_styles.json` (full licence in `studio/LICENSE-MiniMax-Music3.txt`) | MiniMax-Music3 Community License |
| QR Code Generator for JavaScript | `studio/web/vendor/qrcode.js` (licence header kept in the file) | MIT |
| ComfyUI | runtime dependency, not bundled; the node packs load inside it | GPL-3.0 |
| Pool 51 node packs (215 repositories at pinned commits) | not bundled: `install.py --packs pool51` clones them from their own repositories; `studio/pool51_catalogue.json` lists each one's repository, commit and licence as stated | each pack's own licence: MIT (134), GPL-3.0 (39), Apache-2.0 (38), AGPL-3.0 (2), GPL-2.0 (1), Unlicense (1) |
| Patches over four of those packs (context lines are excerpts of their code) | `studio/pool51_patches/` (Comfy-FilmSimulator, comfyui_controlnet_aux, ComfyUI-MagCache, ComfyUI-Depth-Pro) | Apache-2.0, as each of those packs is |

The MiniMax-Music3 row is data from MiniMax, not code: it keeps its own licence and is not relicensed under AGPL-3.0, and that licence asks commercial products to show "MiniMax-Music3" prominently. See the [upstream repository](https://github.com/MiniMax-AI/MiniMax-Music3) and the note in MODELS.md.

### MiniMax-Music3 notice

The official styles in `studio/music3_styles.json` are substantial portions of MiniMax-Music3 material, so this notice travels with them. The whole licence is in `studio/LICENSE-MiniMax-Music3.txt`.

> Copyright (c) 2026 MiniMax
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this Software, including the model weights, parameters, configuration files, inference code and associated documentation (the “Software”), to deal in the Software, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or provide copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> 1. The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

We take the upstream licence to cover the caption-rewriter folder: the GitHub repository has no LICENSE file of its own and its README badge links to the Hugging Face licence. That reading is our inference, not stated text.

### RyanOnTheInside

[ComfyUI_RyanOnTheInside](https://github.com/ryanontheinside/ComfyUI_RyanOnTheInside), MIT, Copyright (c) 2024 RyanOnTheInside, is not bundled, and no line of it is copied here. The Music page credits it. Some of its audio, video and feature numbers were made by running the real pack on a separate ComfyUI: `studio/web/music/reactive.mp4`, `*.features.json`, and takes marked with his name. The graphs `workflows/music_roti_*.json` call his nodes by name and need the pack installed.

### Music page audio

`studio/web/music/` holds renders of one original brief written for the page. No samples, no real artist, no existing lyric. Each model's licence applies to its own files: the MiniMax-Music3 Community License needs "MiniMax-Music3" shown prominently in a commercial product; YuE2 is CC BY-NC 4.0, so its demo renders are non-commercial; Stable Audio Open is under the Stability AI Community License; ACE-Step 1.5 is MIT. No model weights are shipped.

### RES4LYF

RES4LYF is not bundled. The RES4LYF page credits it, with our own notes and short quotes. Its LICENSE adds a commercial-service restriction in front of the AGPL-3.0 text.

### Node packs the studio uses but does not bundle

No node pack's code is in this repository. These are fetched by the installer, linked into a family's own ComfyUI, or named by a graph, and each keeps its own licence. Licences were read from each repository's GitHub licence field or LICENSE file on 2026-11-02.

| Pack | How the studio uses it | Licence |
|---|---|---|
| [Lightricks/ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) | The installer clones it for the LTX goals; the LTX-2.5 family links it | **LTX-2 Community License**, the same terms as the LTX weights (not an open-source code licence: a revenue threshold applies) |
| [kijai/ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) | The installer clones it for Recast; every family ComfyUI links it | GPL-3.0 |
| [kijai/ComfyUI-WanVideoWrapper](https://github.com/kijai/ComfyUI-WanVideoWrapper) | Wan 2.1, 2.2, Animate, Dancer, SCAIL 2 and DWPose families | Apache-2.0 |
| [Kosinkadink/ComfyUI-AnimateDiff-Evolved](https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved) | AnimateDiff family | Apache-2.0 |
| [kijai/ComfyUI-IC-Light](https://github.com/kijai/ComfyUI-IC-Light) | IC-Light family | Apache-2.0 |
| [kijai/ComfyUI-CCSR](https://github.com/kijai/ComfyUI-CCSR) | CCSR family | No licence file found |
| [tungthedev/ComfyUI-TripoSG](https://github.com/tungthedev/ComfyUI-TripoSG) | PartCrafter family | MIT |
| [kijai/ComfyUI-LivePortraitKJ](https://github.com/kijai/ComfyUI-LivePortraitKJ) | LivePortrait family | MIT |
| [T8mars/comfyui-minimax-h3-audio-T8](https://github.com/T8mars/comfyui-minimax-h3-audio-T8) | MiniMax H3 family; the Virtual Set's union graph names its nodes | GPL-3.0-or-later |
| [Larryvrh/ComfyUI-MiniMax-H3-Turbo](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo), [vizart-vj/ComfyUI-MiniMax-H3-LongMedia](https://github.com/vizart-vj/ComfyUI-MiniMax-H3-LongMedia), [YJX-Research/comfyui-controlfoley-official](https://github.com/YJX-Research/comfyui-controlfoley-official) | MiniMax H3 family | Apache-2.0 |
| [TripleHeadedMonkey/ComfyUI-MiniMaxH3_LatentUpscaler](https://github.com/TripleHeadedMonkey/ComfyUI-MiniMaxH3_LatentUpscaler) | MiniMax H3 family | No licence file found |
| [bbaudio-2025/Comfyui-MMH3-UltimateUpscale](https://github.com/bbaudio-2025/Comfyui-MMH3-UltimateUpscale) | SeedVR2 family | MIT |
| [ryanontheinside/ComfyUI_RyanOnTheInside](https://github.com/ryanontheinside/ComfyUI_RyanOnTheInside) | Music page graphs, below | MIT |
| [ClownsharkBatwing/RES4LYF](https://github.com/ClownsharkBatwing/RES4LYF) | RES4LYF page graphs, below | AGPL-3.0 text with a commercial-service restriction in front of it |

Trainers the Train page drives as separate installs: [ostris/ai-toolkit](https://github.com/ostris/ai-toolkit) (MIT) and [bghira/SimpleTuner](https://github.com/bghira/SimpleTuner) (AGPL-3.0). Neither is bundled.
### ComfyMath-NG

[ComfyMath-NG](https://github.com/rabanti-github/ComfyMath) by Raphael Stoeckli, a fork of [ComfyMath](https://github.com/evanspearman/ComfyMath) by Evan Spearman, Apache-2.0, is not bundled, and no line of it is copied here. The demo graphs `studio/web/pack_lab_demos/comfymath_*.json` call its `CM_*` nodes by name and need the pack installed. It is a Pack Lab pick, not part of the studio's install. Its numbers in the docs and on the 3D page come from running the pack on a separate ComfyUI with no internet.

### ComfyUI-GeometryPack

[ComfyUI-GeometryPack](https://github.com/PozzettiAndrea/ComfyUI-GeometryPack), GPL-3.0-or-later, Copyright (C) 2025 ComfyUI-GeometryPack Contributors, is not bundled, not installed by the studio, and was not run. The 3D page and the Pack Lab notes describe it from its own files.

### ComfyUI template thumbnails

Family pages show some thumbnails from ComfyUI's template package, marked as not ours in `studio/family_status.json`. They come from Comfy-Org/workflow_templates, MIT License, Copyright (c) 2023-present Comfy Org: https://github.com/Comfy-Org/workflow_templates/blob/main/LICENSE

AGPL-3.0 section 13 and GPL-3.0 section 13 allow the two to be combined. Other Python dependencies are installed from PyPI under their own licences (see the installer's lock files).

**Models are not part of this repository and are not relicensed.** Each model keeps its author's licence, shown on its tile in the studio and listed in MODELS.md: for example FLUX.2 Klein 4B and Wan 2.2 are Apache-2.0; FLUX.3 Klein, LTX-2.x, Krea 2, MiniMax H3 and MiniMax Music 3 use their authors' community licences, with revenue caps, and MiniMax H3's also excludes the US, EU, UK and South Korea; Anima is non-commercial for the model, though its licence allows outputs for any purpose except where it says otherwise; Qwen-Image 2.1 is research only. InsightFace `buffalo_l`, which the character picture check and the face-finding motion routes download, is for non-commercial research only. Read each licence before using outputs commercially.
