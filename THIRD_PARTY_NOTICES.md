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

The MiniMax-Music3 row is data from MiniMax, not code: it keeps its own licence and is not relicensed under AGPL-3.0, and that licence asks commercial products to show "MiniMax-Music3" prominently. See the [upstream repository](https://github.com/MiniMax-AI/MiniMax-Music3) and the note in MODELS.md.

### MiniMax-Music3 notice

The official styles in `studio/music3_styles.json` are substantial portions of MiniMax-Music3 material, so this notice travels with them. The whole licence is in `studio/LICENSE-MiniMax-Music3.txt`.

> Copyright (c) 2026 MiniMax
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this Software, including the model weights, parameters, configuration files, inference code and associated documentation (the “Software”), to deal in the Software, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or provide copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> 1. The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

We take the upstream licence to cover the caption-rewriter folder: the GitHub repository has no LICENSE file of its own and its README badge links to the Hugging Face licence. That reading is our inference, not stated text.

### RES4LYF

RES4LYF is not bundled. The RES4LYF page credits it, with our own notes and short quotes. Its LICENSE adds a commercial-service restriction in front of the AGPL-3.0 text.

### ComfyUI template thumbnails

Family pages show some thumbnails from ComfyUI's template package, marked as not ours in `studio/family_status.json`. Their licence has not been checked.

AGPL-3.0 section 13 and GPL-3.0 section 13 allow the two to be combined. Other Python dependencies are installed from PyPI under their own licences (see the installer's lock files).

**Models are not part of this repository and are not relicensed.** Each model keeps its author's licence, shown on its tile in the studio and listed in MODELS.md: for example FLUX.2 Klein 4B and Wan 2.2 are Apache-2.0; FLUX.3 Klein, LTX-2.x, MiniMax H3 and MiniMax Music 3 use their authors' community licences; Anima is non-commercial for the model, though its licence allows outputs for any purpose except where it says otherwise. Read each licence before using outputs commercially.
