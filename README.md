<div align="center">

# PARAMETRIC STUDIO

### One clip in, a whole shoot out, on your own GPU.

**[▶ Watch the Shot Board demo (1:49)](docs/media/shotboard_demo.mp4)** &nbsp;·&nbsp; **[See how big it is](#see-how-big-it-is)** &nbsp;·&nbsp; **[Try the read-only demo](https://parametricparadigm.github.io/ComfyUI_Parametric_Studio/)** &nbsp;·&nbsp; **[⚡ Install](#install)** &nbsp;·&nbsp; **[For the judges](#for-the-judges)** &nbsp;·&nbsp; **[✅ What's proven](#whats-proven)**
<!-- shot board demo link: for GitHub's inline player, drop docs/media/shotboard_demo.mp4 (4.3 MB) into a comment box on github.com and paste the user-attachments URL on its own line here -->

[![One source clip on the Shot Board: reshoot, orbit 360, recast, then LTX-2.5 water, clean plate, day to night and a matte](docs/media/shotboard_preview.webp)](docs/media/shotboard_demo.mp4)

<sub>One real Shot Board run: the source clip and its seven results, from the contact video the board exported, scaled down. Click for the 1:49 screen recording of that run (waits sped up and labelled, captions, no sound).</sub>

</div>

Bring one clip and queue the shoot: a new camera, a frozen orbit, a recast lead, then LTX-2.5 for water, a clean plate, day to night and a matte. Jobs run one at a time on your GPU, at 0 credits. Every result keeps its exact ComfyUI graph and seed, and you can open that graph and copy it out. Every clip and image on this page is AI-generated.

- **Real graphs.** What you see in Pro is what ComfyUI runs, not a diagram of it.
- **Audited nodes.** We read all 544 custom nodes and published the result: 158 do real work, 364 are honest utilities or payload builders that load no model, and 22 don't work yet, [listed by name](docs/NODES.md#node-reference). We removed or renamed the ones that faked results. The two nodes added since record and draw the attention maps on the Which Word page.
- **Open weights only.** No partner nodes or closed APIs in the open edition, enforced by tests. Models keep their own licences, and some limit where or how you can use them. MiniMax H3's community licence excludes the US, EU, UK and South Korea: [read MODELS.md](MODELS.md) before you install those goals.

## Made in Parametric Studio

| [![Film A "RUN": she presses Run on a real MiniMax H3 graph and her room becomes a film set](docs/media/ParametricStudio_FilmA_RUN_MiniMaxH3.webp)](https://github.com/parametricparadigm/ComfyUI_Parametric_Studio/releases/download/demo/ParametricStudio_FilmA_RUN_MiniMaxH3.mp4) | [![Film B "ONE CLIP": one clip of a square, then water, day to night and a matte from LTX-2.5](docs/media/ParametricStudio_FilmB_ONE_CLIP_LTX25.webp)](https://github.com/parametricparadigm/ComfyUI_Parametric_Studio/releases/download/demo/ParametricStudio_FilmB_ONE_CLIP_LTX25.mp4) |
|---|---|
| **[▶ Film A "RUN"](https://github.com/parametricparadigm/ComfyUI_Parametric_Studio/releases/download/demo/ParametricStudio_FilmA_RUN_MiniMaxH3.mp4)** (1:31, MiniMax H3). One room, one GPU, one real 24-node H3 graph | **[▶ Film B "ONE CLIP"](https://github.com/parametricparadigm/ComfyUI_Parametric_Studio/releases/download/demo/ParametricStudio_FilmB_ONE_CLIP_LTX25.mp4)** (1:31, LTX-2.5). One plain clip, then water, night, a clean plate and a matte |
| <sub>AI-generated, an invented person. Video: MiniMax H3 (MiniMax H3 Community License, which excludes the US, EU, UK and South Korea). Keyframes: FLUX.2 Klein 9B (FLUX Non-Commercial License) from a FLUX.3 Klein reference. Sound: a Music 3 score over H3's own room and set ambience, no dialogue. Score: MiniMax Music 3 (MiniMax-Music3 Community License). Screens are real captures.</sub> | <sub>AI-generated, an invented person and town. Video and VFX: LTX-2.5 with four Lightricks IC-LoRAs (LTX-2.x Community License). Keyframes: FLUX.2 Klein 9B (FLUX Non-Commercial License) from a FLUX.3 Klein reference. Sound: a Music 3 score over LTX-2.5's own ambience, no dialogue. Score: MiniMax Music 3 (MiniMax-Music3 Community License). Screens are real captures.</sub> |

### See how big it is

| [![Highlight reel: 48 clips from 11 parts of the repo, each labelled with the model or graph that made it](docs/media/demo_reel.webp)](docs/media/demo_reel.mp4) | [![The wall: 100 different renders fill a 10 by 10 grid while a counter runs to 2,034](docs/media/demo_wall.webp)](docs/media/demo_wall.mp4) | [![Studio tour: every one of the 46 tabs, with a caption naming each](docs/media/demo_tour.webp)](docs/media/demo_tour.mp4) |
|---|---|---|
| **[▶ Highlight reel](docs/media/demo_reel.mp4)** (1:10). 48 clips from 11 parts of the repo: model families, recipes, pipelines, 3D, commercials, Shot Board, music, ComfyUniversity and the films. [1080p](https://github.com/parametricparadigm/ComfyUI_Parametric_Studio/releases/download/demo/ParametricStudio_Demo_Reel.mp4) | **[▶ The wall](docs/media/demo_wall.mp4)** (0:25). 100 different renders fill in while the counter runs to the 2,034 rendered files in the repo. [1080p](https://github.com/parametricparadigm/ComfyUI_Parametric_Studio/releases/download/demo/ParametricStudio_Demo_Wall.mp4) | **[▶ Studio tour](docs/media/demo_tour.mp4)** (1:49). All 46 tabs, recorded on a preview of this release with no GPU attached. Also on a [phone](docs/media/demo_tour_phone.mp4) (0:20). [1080p](https://github.com/parametricparadigm/ComfyUI_Parametric_Studio/releases/download/demo/ParametricStudio_Demo_Tour.mp4) |
| <sub>Every label names the model or graph from that clip's own record: [`docs/demos/reel_edl.json`](docs/demos/reel_edl.json). The Wren Halloway clip was made before the studio and says so.</sub> | <sub>Each tile is a different render already in the repo: [`docs/demos/wall_tiles.json`](docs/demos/wall_tiles.json). Counted from this release, with how each figure was counted, in [`docs/demos/numbers.json`](docs/demos/numbers.json).</sub> | <sub>Pages, renders and figures are the repo's own; ComfyUI shows as offline because none was attached. Tabs and times: [`docs/demos/tour_edl.json`](docs/demos/tour_edl.json).</sub> |

<sub>Counted from this release: 6,303 ComfyUI node classes loaded (partner API nodes left out), 1,093 graphs that open in the studio, 818 recipes, 76 model families rendered here, 24 pipelines, 163 lessons, 46 tabs, 2,034 rendered files, 189 crew notes, 7,423 tests. All AI-generated. Music: the studio's own renders of one song, "Paper Boats": MiniMax-Music3 (MiniMax-Music3 Community License) on the reel, ACE-Step 1.5 (MIT) and DiffSynth-Music (Apache-2.0) on the wall and the tour, levelled to -16 LUFS.</sub>

## For the judges

Built for the Open Source Higgsfield contest. Entered in **Open Weights Only** and **VFX Workflow Built with LTX**. Best Overall considers every entry.

| | |
|---|---|
| **What's new** | One clip becomes a whole shoot in one queue: reshoot, frozen-time orbit, recast, then four LTX-2.5 effects, and every result keeps its exact graph and seed. Code: the queue in [`studio/web/shotboard.js`](studio/web/shotboard.js), job states in [`shotboard_logic.js`](studio/web/shotboard_logic.js), the board in [`shotboard_view.js`](studio/web/shotboard_view.js), the contact-video export in [`studio/shot_board.py`](studio/shot_board.py). Tests: [`tests/test_shot_board.py`](tests/test_shot_board.py) |
| **Open Weights Only** | [`tests/test_open_edition_no_paid_apis.py`](tests/test_open_edition_no_paid_apis.py) checks every graph in [`workflows/`](workflows) and [`studio/family_templates/`](studio/family_templates) against the 322 partner node ids in ComfyUI 0.43.0 ([`tests/partner_node_ids.txt`](tests/partner_node_ids.txt)), and keeps paid API hosts and SDKs out of `psn/` and `psn_nodes/`. The open edition hides partner apps: [`tests/test_publication.py`](tests/test_publication.py) |
| **LTX is the core** | [`workflows/ltx25_vfx_api.json`](workflows/ltx25_vfx_api.json): 30 nodes, LTX-2.5 with one of four Lightricks IC-LoRAs, picked per effect in `VFX_EFFECTS` in [`studio/goals.py`](studio/goals.py): water, clean plate, day to night, matte. A transition between two clips runs the LTX-2.3 transition LoRA on LTX-2.5 ([`workflows/ltx25_transition_api.json`](workflows/ltx25_transition_api.json)), rendered: [`studio/web/showcase/transition_proof.json`](studio/web/showcase/transition_proof.json) |
| **Demo** | [1:49 screen recording of one real run](docs/media/shotboard_demo.mp4): waits sped up and labelled, captions, no sound |
| **Made in Parametric Studio** | Two 90-second films made with the studio: [Film A "RUN"](https://github.com/parametricparadigm/ComfyUI_Parametric_Studio/releases/download/demo/ParametricStudio_FilmA_RUN_MiniMaxH3.mp4) on MiniMax H3 and [Film B "ONE CLIP"](https://github.com/parametricparadigm/ComfyUI_Parametric_Studio/releases/download/demo/ParametricStudio_FilmB_ONE_CLIP_LTX25.mp4) on LTX-2.5 with four IC-LoRAs. AI-generated, model licences [under the posters](#made-in-parametric-studio) |
| **Try it** | [Read-only demo](https://parametricparadigm.github.io/ComfyUI_Parametric_Studio/): the real UI and real renders, it generates nothing |
| **Install** | [Three lines if you already run ComfyUI](#install), or one installer command |
| **Hardware** | Tested only on one Linux box with a 96 GB card. See [Shot Board](#shot-board-one-clip-in-a-whole-shoot-out) for the peak VRAM we recorded |
| **What's run and what isn't** | [What's proven](#whats-proven) |

## Shot Board: one clip in, a whole shoot out

Bring one clip and queue the lot: reshoot it with a new camera, orbit around the subject, recast the lead from a single picture, then run LTX-2.5 VFX for water, a clean plate, day to night and a matte. Jobs run one at a time on your GPU. The queue survives a reload, but the tab does need to stay open. Every result keeps its exact graph and seed. Export the grid as one captioned contact video. Seven jobs on one clip took about 13 minutes on our 96 GB card. A clean plate can leave a small smear when the subject fills the frame, and the page says so.

**The four LTX-2.5 effects on one clip**, from the same run (source, water, clean plate, day to night, matte). All four use [`workflows/ltx25_vfx_api.json`](workflows/ltx25_vfx_api.json) with a different IC-LoRA:

![Source clip, then LTX-2.5 water, clean plate, day to night and matte](docs/media/shotboard_ltx_vfx.webp)

| | |
|---|---|
| ![Flood: the LTX-2.5 water effect wiped over the source clip](docs/media/shotboard_flood.gif) | ![Night: the LTX-2.5 day to night effect wiped over the source clip](docs/media/shotboard_night.gif) |
| ![Clean plate: the person painted out by LTX-2.5, wiped over the source clip](docs/media/shotboard_clean_plate.gif) | ![Cutout: the LTX-2.5 matte used as alpha over a checkerboard, wiped over the source clip](docs/media/shotboard_cutout.gif) |

<sub>Our own renders of one invented clip: the source is itself an LTX-2.5 render of a made-up person, not real footage. Each GIF wipes the effect (left of the line) over the source (right). Flood, night, clean plate and the cutout made from the matte, with their settings, seeds and render times in [`studio/web/showcase/vfx_same_clip.json`](studio/web/showcase/vfx_same_clip.json).</sub>

**Peak VRAM** for the same goals rendered on their own on our 96 GB card: reshoot 49.3 GiB, VFX water 47.3 GiB, VFX clean plate 44.8 GiB, recast 36.3 GiB (recorded in [`studio/web/showcase/showcase.json`](studio/web/showcase/showcase.json)). These are peaks on a card with room to spare, not minimums. No smaller card has been tried.

![Shot Board: one source clip, reshot, orbited, recast and run through four LTX-2.5 effects](docs/img/shotboard.jpg)

## What's proven

Run on one Linux box with a 96 GB RTX PRO 6000. Nothing here has been run on Windows, macOS, AMD or a smaller card. One fresh install has rendered: a clean Ubuntu 24.04 Docker container on that same card, with only the NVIDIA driver passed in, following INSTALL.md. Its first picture, on the Anima goal, took 30 s once the software and the 9.2 GB of models were in place. Fresh installs of other goals and on other machines have not been tried.

| Feature | Run for real here | Not run yet |
|---|---|---|
| Shot Board | Full 7-job board and export. About 13 minutes, and the tab has to stay open | Other hardware |
| Train | Short real runs on SDXL, SD 1.5, SD3.5 Medium, FLUX.2 Klein 4B and 9B, FLUX.1 dev, Z-Image, Lumina 2, Wan 2.2 5B and LTX-2.5, each with its peak and an A/B we looked at. The effect ranged from strong (Klein 9B, Wan, LTX) to weak (Lumina, FLUX.1 dev). Wan and LTX trained on stills and were tested on one frame. Klein 9B used about 72 GB | Any base marked Not run, including MiniMax H3, Qwen-Image 2.1, HiDream-O1 and Music 3. FLUX.1 schnell and Krea 2 ran out of memory here. FLUX.3 Klein, Anima and ERNIE fail in ComfyUI's training node. Video motion |
| Virtual Set | Blender passes on the CPU. Modes A (H3 and LTX-2.5), B, C and D rendered once each on one street shot | Wan, a pose pass, Qwen keyframes, any other shot |
| World Kit | Places, looks, library, Godot export, a prop from a mesh, on the CPU with Blender. A character from words to a rigged, moving, textured figure | Other steps that need a model (tested with fakes) |
| Recipes | 10 of 10 flagships rendered. A library of 818 passes an offline format check, and 701 of its recipes show a result we rendered here (487 pictures, 141 clips, 48 sounds, 25 3D models), each from one run. The sounds were checked for level and length, not listened to. | The rest of the library |
| Sampling Lab | 44 renders on SDXL, SD 1.5 and SD 3.5, and core sampler measurements | Pack entries are read from source, not run |
| RES4LYF page | A credit page. The pack is not shipped; run separately, of 154 nodes checked 92 rendered, 14 ran and 44 errored | The other nodes in the pack |
| Families | 95 wired, 80 with a render on record | The other 15 have no render on record. World Kit and Virtual Set extras are not in the installer yet |

## Bonus tracks: what's built for each

The contest has three model-provider bonus tracks, and its Q&A says: "Each entry is eligible for both a main category and a model-provider bonus category." **This entry is submitted under Open Weights Only and VFX Workflow Built with LTX.** The FLUX and MiniMax H3 work below is shown so you can see what's there, not as more entries. Each item links its graph and a render we made with it. Every person shown is invented and AI-generated.

### VFX Workflow Built with LTX (entered)

LTX-2.5 22B is the core video model in every graph in this block. Each adds one Lightricks IC-LoRA, or an LTX-2.3 LoRA run on LTX-2.5.

<table><tr>
<td width="33%"><a href="studio/web/showcase/vfx_same_ba_water.mp4"><img src="studio/web/showcase/vfx_same_ba_water.webp" alt="LTX-2.5 water wiped over the source clip of a woman in a red coat on a cobbled street"></a><br><sub><b>Shot Board VFX.</b> Water, clean plate, day to night and matte, four IC-LoRAs on one graph: <a href="workflows/ltx25_vfx_api.json">graph</a> · <a href="studio/web/showcase/vfx_same_clip.json">renders, seeds, times</a>. Core: LTX-2.5</sub></td>
<td width="33%"><a href="studio/web/showcase/vfx_same_transition.mp4"><img src="studio/web/showcase/vfx_same_transition.webp" alt="LTX-2.5 transition bridging the day clip into its night take"></a><br><sub><b>Transitions.</b> A 49-frame bridge from one clip's last frame to the next clip's first, with the LTX-2.3 transition LoRA: <a href="workflows/ltx25_transition_api.json">graph</a> · <a href="studio/web/showcase/transition_proof.json">proof</a>. Core: LTX-2.5</sub></td>
<td width="33%"><a href="studio/web/finish/colorize_fresh.mp4"><img src="studio/web/finish/colorize_thumb.jpg" alt="LTX Finish colorize: a black and white tram street brought back to colour"></a><br><sub><b>LTX Finish.</b> Restore, deblur, remove compression, colorize, upscale x2, and SDR to HDR with HLG, EXR and ProRes masters, six IC-LoRAs: <a href="workflows/ltxfin_repair_api.json">repair graph</a> · <a href="workflows/ltxfin_hdr_api.json">HDR graph</a> · <a href="studio/finish_proof.json">measured proof</a>. Core: LTX-2.5</sub></td>
</tr><tr>
<td><a href="studio/web/campath/track_boat.mp4"><img src="studio/web/campath/track_boat.webp" alt="A red paper boat following a drawn line down a forest stream"></a><br><sub><b>Camera Paths: follow a line.</b> Draw a path and the subject follows it, with the LTX-2.3 Motion-Track-Control IC-LoRA (39.2 GiB peak): <a href="workflows/campath_ltx_track_api.json">graph</a> · <a href="studio/camera_proof.json">proof</a> (<code>track</code>). Core: LTX-2.5</sub></td>
<td><a href="studio/web/oneclick_art/matte/on_new_set.mp4"><img src="studio/web/oneclick_art/matte/on_new_set.webp" alt="The woman in the red coat cut out with an LTX matte and set on a seaside boardwalk"></a><br><sub><b>One-click matte.</b> A clip to an alpha matte, a WebM with alpha and a ProRes 4444 file, then onto a new set: <a href="workflows/oneclick_matte_api.json">graph</a> · <a href="studio/web/oneclick_art/index.json">proof</a> (<code>matte</code>). The matte is soft between the legs. Core: LTX-2.5</sub></td>
<td><a href="studio/web/showcase/vfx_same_ba_night.mp4"><img src="studio/web/showcase/vfx_same_ba_night.webp" alt="LTX-2.5 day to night wiped over the source clip"></a><br><sub><b>Day to night</b>, the same clip and graph with the day-to-night IC-LoRA. The four per-effect graphs are in <a href="workflows/vfx"><code>workflows/vfx/</code></a>. Core: LTX-2.5</sub></td>
</tr></table>

### Built with FLUX (shown, not entered)

Only graphs whose core model is FLUX.3 Klein count for this track. All of ours are text to image. There is no FLUX.3 Klein edit, reference or swap graph in the repo yet.

<table><tr>
<td width="33%"><img src="studio/web/showcase/s_sneaker.webp" alt="FLUX.3 Klein: a running sneaker over wet obsidian"><br><sub><b>Image HQ</b> goal, 9.3 s, 23.6 GiB peak: <a href="workflows/flux3_klein_core_t2i_api.json">graph</a> · record <code>s_sneaker</code> in <a href="studio/web/showcase/showcase.json">showcase.json</a>. Core: FLUX.3 Klein</sub></td>
<td width="33%"><img src="studio/web/showcase/s_temple.webp" alt="FLUX.3 Klein: a jungle temple in shafts of light"><br><sub><b>Image HQ</b> goal, 16:9, 9.3 s, 24.1 GiB peak: same <a href="workflows/flux3_klein_core_t2i_api.json">graph</a> · record <code>s_temple</code>. The <b>Product Studio</b> goal runs this graph too. Core: FLUX.3 Klein</sub></td>
<td width="33%"><img src="studio/web/pipelines/product_hero/photo.webp" alt="FLUX.3 Klein: an amber perfume bottle on a plain studio background"><br><sub><b>Product hero pipeline</b>, the photo stage: <a href="studio/web/pipelines/product_hero/graphs/photo.json">graph</a> · <a href="studio/web/pipelines/product_hero/proof.json">proof</a>. Core: FLUX.3 Klein</sub></td>
</tr></table>

FLUX.3 Klein family templates in bf16, nvfp4 and SD nvfp4 ([`flux3_klein_bf16_t2i.json`](studio/family_templates/flux3_klein_bf16_t2i.json), [`flux3_klein_nvfp4_t2i.json`](studio/family_templates/flux3_klein_nvfp4_t2i.json), [`flux3_klein_sd_nvfp4_t2i.json`](studio/family_templates/flux3_klein_sd_nvfp4_t2i.json)) each have a test render under `Flux.3-Klein` in [`studio/family_status.json`](studio/family_status.json).

**Other FLUX models, not part of this track:** FLUX.2 Klein 4B and 9B run the Image goal, try-on, edit and style graphs and the keyframes in both films; FLUX.1 schnell has a family template, and FLUX.1 dev runs the HunyuanWorld panorama template. FLUX.3 Klein uses the FLUX Kommunity licence (gated download); FLUX.2 Klein 9B is non-commercial and Klein 4B is Apache-2.0.

### Built with MiniMax H3 (shown, not entered)

MiniMax H3's community licence excludes the US, EU, UK and South Korea, outputs included: read [MODELS.md](MODELS.md) before you install these.

<table><tr>
<td width="33%"><a href="studio/web/showcase/recipes/recast_character.mp4"><img src="studio/web/showcase/recipes/recast_character.webp" alt="H3 Recast side by side: a chef flambéing, and the same shot with a red-bearded sailor in her place"></a><br><sub><b>Recast</b>: swap the character, keep the performance, camera and sound, with the character-swap LoRA on H3 Ref2VA: <a href="workflows/h3_recast_api.json">graph</a> · record <code>recast_character</code> in <a href="studio/recipes.json">recipes.json</a>. Core: MiniMax H3</sub></td>
<td width="33%"><a href="studio/web/showcase/reshoot_orbit_take.mp4"><img src="studio/web/showcase/reshoot_orbit_take.webp" alt="H3 Reshoot: the chef clip retaken with the camera orbiting right"></a><br><sub><b>Reshoot</b>: a new take from a clip's first frame with a new camera move, 147 s, 49.3 GiB peak: <a href="workflows/h3_reshoot_api.json">graph</a> · record <code>reshoot_orbit_take</code> in <a href="studio/web/showcase/showcase.json">showcase.json</a>. Core: MiniMax H3</sub></td>
<td width="33%"><a href="studio/web/recipe_renders/lora_c87bc8ef16.mp4"><img src="studio/web/recipe_renders/lora_c87bc8ef16.poster.webp" alt="H3 orbit LoRA: a frozen instant of a man in a blue jacket in a sunlit plaza, the camera circling"></a><br><sub><b>Orbit 360</b>, frozen time with the orbit LoRA: this render is its LoRA recipe (<code>lora_c87bc8ef16</code> in <a href="studio/recipe_renders.json">recipe_renders.json</a>). The Orbit goal's own graph, <a href="workflows/h3_orbit360_api.json">h3_orbit360_api.json</a>, has no render on record and the app marks it unproven. Core: MiniMax H3</sub></td>
</tr></table>

**H3 voice with written lines:** every talking template gives H3 the exact words to say, in the vendor's `<d>[English] …</d>` form ([`video_templates.json`](studio/recipe_library/video_templates.json), held to it by [`tests/test_h3_dialogue.py`](tests/test_h3_dialogue.py)), because with no words H3 voices made-up babble. The greeting card, an H3 clip with the turbo LoRA, speaks its line ([render](studio/web/recipe_renders/vid_short_greeting.mp4), record `vid_short_greeting` in [`recipe_renders.json`](studio/recipe_renders.json)): Whisper hears exactly "Happy birthday, Sam!". That was measured by Whisper, not listened to.

**H3 LoRAs:** 75 H3 LoRA settings in [`studio/lora_recipes.json`](studio/lora_recipes.json), 59 of them with a render in [`studio/recipe_renders.json`](studio/recipe_renders.json) (sliders, bullet time, voice and lip-sync LoRAs, character swap, orbit). Text to video with sound, image to video and first-and-last-frame run on [`h3_t2v_api.json`](workflows/h3_t2v_api.json), [`h3_i2v_api.json`](workflows/h3_i2v_api.json) and [`h3_fl2v_api.json`](workflows/h3_fl2v_api.json), with renders in [`showcase.json`](studio/web/showcase/showcase.json) (`v_h3_dragon`, `v_h3_foundry`, `director_keyframes_bloom`).

## Swap the person, on any model

These graphs swap a person: a whole character in a video, a performer, or an outfit. Each row below links the graph and a render we made with it on our card. The studio's **Swap** page shows the same rows with the clips playing, from the same file ([`studio/swap_showcase.json`](studio/swap_showcase.json)). Swap only invented adults, or people who gave you permission.

<!-- swap-table:start (scripts/build_swap_table.py writes this) -->
9 graphs with a render, on 6 model families (MiniMax H3, Wan 2.1 SCAIL-2, Wan 2.2 Animate, Qwen-Image 2.1, FLUX.2 Klein, Krea 2).

| Render | Swap | Core model | What it swaps | Out | Graph and proof | Licence |
|---|---|---|---|---|---|---|
| [<img src="studio/web/showcase/recipes/recast_character.webp" width="120" alt="Recast: Source and recast side by side: the camera push, the second cook and the flambé are kept, and the chef becomes the red-bearded sailor from the picture.">](studio/web/showcase/recipes/recast_character.mp4) | **Recast** | MiniMax H3 (Ref2VA) + character-swap LoRA | the whole character: face, hair and clothes | video | [graph](workflows/h3_recast_api.json) · [render](studio/web/showcase/recipes/recast_character.mp4) · record `studio/recipes.json` (recast_character), 468.3 s (swap step), peak 30.1 GiB. Mid-clip the flame comes out paler than in the source. | MiniMax H3 Community License: excludes the US, EU, UK and South Korea, outputs included |
| [<img src="studio/web/motion/scail2_0.webp" width="120" alt="SCAIL 2: An invented man takes over an invented woman's clip, wave and gestures kept. Looked at frame by frame.">](studio/web/motion/scail2_0.mp4) | **SCAIL 2** | Wan 2.1 14B SCAIL-2 | the whole character in a clip | video | [graph](studio/family_templates/motion_scail2.json) · [render](studio/web/motion/scail2_0.mp4) · record `studio/motion_proof.json` (routes.scail2), 112.6 s, peak 28.2 GiB. 3.4 s per segment in this graph. The face drifts a little from the picture when the head turns. | MIT on Hugging Face, Apache-2.0 on GitHub; the lightx2v distill LoRA is Apache-2.0 |
| [<img src="studio/web/motion/wan_animate2_0.webp" width="120" alt="Wan Animate 2: An invented woman follows an invented woman's clip. Looked at frame by frame.">](studio/web/motion/wan_animate2_0.mp4) | **Wan Animate 2** | Wan 2.2 Animate 2 (distilled, int8) | the performer: the person in a picture takes over a clip's movement | video | [graph](studio/family_templates/motion_wan_animate2.json) · [render](studio/web/motion/wan_animate2_0.mp4) · record `studio/motion_proof.json` (routes.wan_animate2), 151.3 s, peak 40.9 GiB. It makes its own plain background rather than keeping the clip's, and the face reads younger than the picture. | Apache-2.0 |
| [<img src="studio/web/families/qwen-image-2-1_13.webp" width="120" alt="Qwen outfit swap: Best on our test: the coat kept its full length and buttons, and the jeans and face stayed the same.">](studio/web/families/qwen-image-2-1_13.webp) | **Qwen outfit swap** | Qwen-Image 2.1 + Outfit Swap LoRA | the outfit | still | [graph](studio/family_templates/qwen21_tryon.json) · [render](studio/web/families/qwen-image-2-1_13.webp) · record `studio/family_status.json` (fam_qwen-image-2-1_13), 53.7 s, peak 35.1 GiB. Tested on one coat and one person only. | Qwen Research License (research or evaluation only); the LoRA is rent-only at its source |
| [<img src="studio/web/families/flux-2_11.webp" width="120" alt="Klein 4B try-on: The cleanest on our tests: it replaced the whole outfit on both the coat and the dress and kept the face.">](studio/web/families/flux-2_11.webp) | **Klein 4B try-on** | FLUX.2 Klein Base 4B + try-on LoRA | the outfit | still | [graph](studio/family_templates/klein4b_tryon.json) · [render](studio/web/families/flux-2_11.webp) · record `studio/family_status.json` (fam_flux-2_11), 66.2 s, peak 21.2 GiB. The LoRA is rent-only on Civitai, so check before selling pictures. | Klein 4B Apache-2.0; the LoRA is rent-only on Civitai |
| [<img src="studio/web/families/flux-2_12.webp" width="120" alt="Klein 9B try-on, two references + LoRA: Quicker than 4B, and it replaced the whole outfit.">](studio/web/families/flux-2_12.webp) | **Klein 9B try-on, two references + LoRA** | FLUX.2 Klein 9B + try-on LoRA | the outfit | still | [graph](studio/family_templates/klein9b_tryon_lora.json) · [render](studio/web/families/flux-2_12.webp) · record `studio/family_status.json` (fam_flux-2_12), 43.4 s, peak 29.1 GiB. On our dress test the colour came out paler and the hem shorter. The LoRA was made for Base 9B and runs here on the distilled 9B. | FLUX Non-Commercial License (Klein 9B); the LoRA is rent-only on Civitai |
| [<img src="studio/web/families/flux-2_10.webp" width="120" alt="Klein 9B try-on, two references: It dressed the coat well.">](studio/web/families/flux-2_10.webp) | **Klein 9B try-on, two references** | FLUX.2 Klein 9B, no LoRA | the outfit | still | [graph](studio/family_templates/klein9b_tryon.json) · [render](studio/web/families/flux-2_10.webp) · record `studio/family_status.json` (fam_flux-2_10), 79.9 s, peak 27.5 GiB. It also recoloured the trousers to match the coat. | FLUX Non-Commercial License (Klein 9B) |
| [<img src="studio/web/families/flux-2_15.webp" width="120" alt="Klein 9B, three references: Three pictures in (an invented painter, a rust field jacket, an empty greenhouse), and he stands in the greenhouse wearing the jacket. Face and build held; the pockets and collar carried over. The render shows the three references beside the result.">](studio/web/families/flux-2_15.webp) | **Klein 9B, three references** | FLUX.2 Klein 9B | the character into a scene: character, outfit and place from three pictures | still | [graph](studio/family_templates/klein9b_character_scene.json) · [render](studio/web/families/flux-2_15.webp) · record `studio/family_status.json` (fam_flux-2_15), 17.5 s, peak 28.6 GiB. A slight smile was added and the hair came out a little lighter in the warm light. His own trousers stay. | FLUX Non-Commercial License (Klein 9B) |
| [<img src="studio/web/families/krea2_2.webp" width="120" alt="Krea 2 identity edit: An invented man at a rainy tram shelter is swapped for an invented lifeguard. The street, shelter, shop window and light held, and the face matches the picture. The render shows both inputs beside the result.">](studio/web/families/krea2_2.webp) | **Krea 2 identity edit** | Krea 2 Turbo + Krea 2 Identity Edit LoRA (community fine-tune, not by Krea) | the person in an existing scene | still | [graph](studio/family_templates/krea2_identity_swap.json) · [render](studio/web/families/krea2_2.webp) · record `studio/family_status.json` (fam_krea2_2), 36.9 s, peak 36.9 GiB. The new person brought his own arms-out pose and bare feet instead of taking the man's stance, and the camera sits a little closer. | Krea 2 Community License: commercial use only for companies under US$1,000,000 annual revenue; the Identity Edit LoRA is a community fine-tune, not by Krea |

**Coming** (graph written, proof render under way; each gets a row above once its render is on record): **Qwen outfit swap, turbo** (Qwen-Image 2.1 Turbo + Outfit Swap LoRA; still; swaps the outfit).
<!-- swap-table:end -->

## Install

**Already run ComfyUI?** You only need the studio, and a link so ComfyUI loads its `PSN_` nodes:

```bash
git clone --depth 1 https://github.com/parametricparadigm/ComfyUI_Parametric_Studio.git && cd ComfyUI_Parametric_Studio
python3 -m venv .venv && . .venv/bin/activate                            # Python 3.12 is the tested version
pip install fastapi "uvicorn[standard]" python-multipart pydantic numpy pillow brotli apscheduler "huggingface_hub[hf_xet]"
ln -s "$PWD" /path/to/ComfyUI/custom_nodes/comfyui_parametric_studio    # then restart ComfyUI
COMFYUI_URL=http://127.0.0.1:8188 python -m studio.server               # open http://127.0.0.1:8310
```

With uv instead: `uv sync`, then `COMFYUI_URL=http://127.0.0.1:8188 uv run python -m studio.server`. On Ubuntu, get uv with `sudo apt install pipx && pipx install uv`; a plain `pip install uv` fails there.

**Models in one command.** Every model file the studio uses has its official link, size, SHA-256, licence and folder in [`studio/models_manifest.json`](studio/models_manifest.json), and `scripts/get_models.py` fetches them into your ComfyUI (resumable, hash-checked, skips what you have; gated models read `HF_TOKEN` from the environment only):

```bash
python3 scripts/get_models.py --list                                                   # goals and families
python3 scripts/get_models.py --for image --models-dir /path/to/ComfyUI/models --dry-run  # see what is missing, then drop --dry-run
python3 scripts/get_models.py --for family:Anima --models-dir /path/to/ComfyUI/models     # or --for all, a graph id, or one file name
```

Each app's page lists the model files it is missing and any node your ComfyUI doesn't have. The Shot Board needs MiniMax H3 for reshoot, orbit and recast, LTX-2.5 with four Lightricks IC-LoRAs for the VFX, and the ComfyUI-LTXVideo and KJNodes packs. The files, sizes and hashes for each goal are in [`studio/models_manifest.json`](studio/models_manifest.json) (goals `reshoot`, `orbit360`, `recast`, `vfx_ltx`), and the licences are in [MODELS.md](MODELS.md). Folder settings are in [INSTALL.md](INSTALL.md#using-a-comfyui-you-already-have).

**Starting from nothing?** One command, sized to your machine. See what it would do first:

```bash
sudo apt update && sudo apt install -y git ffmpeg python3-venv   # Ubuntu or Debian; other systems are in INSTALL.md
git clone --depth 1 https://github.com/parametricparadigm/ComfyUI_Parametric_Studio.git
cd ComfyUI_Parametric_Studio
python3 install.py --dry-run     # shows what fits this box and the disk it needs, changes nothing
python3 install.py               # or --goals anime for the smallest download, --channel nightly, --goals image,video
```

`install.py` fetches the models for the goals it installs. For a family or anything else, run `python3 scripts/get_models.py --for family:<name> --models-dir ../parametric-studio-runtime/ComfyUI/models` afterwards (on Windows, `scripts\install_windows.ps1 -Models family:<name>` does both).

It needs a GPU driver already installed, and about 10 GB of disk plus the models: 25 GB is enough for the default goal. Then run the launcher it prints and open http://127.0.0.1:8310.

Full install on a clean Ubuntu 24.04 box: about 29 min to the studio page (PyTorch is ~3 GB), first image about 30 s once the models are in. Model download time depends on your Hugging Face speed.

**For the Shot Board:** `python3 install.py --goals reshoot,orbit360,recast,vfx_ltx --include-gated`. LTX-2.5 and its IC-LoRAs are gated: accept each licence on Hugging Face and set `HF_TOKEN` first. On our box, the dry run of that command plans 99.9 GB of models and about 110 GB of disk, and adds the ComfyUI-LTXVideo and KJNodes packs. It has not been run end to end on a clean machine.

Measured: about 38.5 GiB per effect job; about 20 GiB peak with `--vram-headroom` (24 GB cards likely, not yet run on one); 16 GB not supported yet.

Full details, including Windows, Mac and what has and hasn't been tested on each, are in **[INSTALL.md](INSTALL.md)**. Models and their licences are in **[MODELS.md](MODELS.md)**; they are not in this repo, and some have their own terms and regional limits. MiniMax H3's licence excludes the US, EU, UK and South Korea, and that reaches its outputs too, so read it before you install those goals.

---

## Also in the box

The Shot Board is the contest entry. The rest of the studio comes with it.

### Why this exists

Closed AI video apps give you a prompt box and hide everything else. ComfyUI gives you everything, and a blank canvas. **Parametric Studio is both at once:** a form anyone can use, and one click from the exact ComfyUI graph that made the result. It runs on your machine, it reads your machine, and it teaches you how it all works while you use it.

| | Closed creative suites | Parametric Studio |
|---|---|---|
| **Cost per render** | Credits | **0 on your own GPU** |
| **How a result was made** | Hidden | **The real graph, in 3D** |
| **Which models** | The ones they sell you | **95 families wired, 80 with a render on record** |
| **Your files and prompts** | On their servers | **Stay on your machine** |
| **Help** | A docs page | **A crew of characters that answer from cited notes, out loud** |
| **Can you fork it?** | No | **Yes: AGPL-3.0** |

### The apps

Named after what you want to do, not which node to wire.

| App | What it does | Core model |
|---|---|---|
| **Recast** | Swap the character in a video and keep the performance, scene and sound | MiniMax H3 |
| **VFX** | Flood a street, clear a plate, turn day to night, pull a matte | LTX-2.5 with IC-LoRAs |
| **Director** | Direct a shot like a film set: camera move, lens, light, mood, first and last frame | MiniMax H3 |
| **Reshoot** | A new take of your clip with a new camera move, from its first frame | MiniMax H3 |
| **Product Studio** | Your product, shot like an ad: pick the set and the light | FLUX.3 Klein |
| **Music Video Maker** | A song, the shots and the cut, on the beat | MiniMax Music 3 + H3 |
| **One sentence to a short film** | Plan, character, shots, score and edit from a single line | Klein + H3 + Music 3 |

Plus Image, Image HQ, Anime, Video, Animate, Video + Sound and Music as direct goals on FLUX.2 Klein, FLUX.3 Klein, Anima, Wan 2.2, LTX-2.5, MiniMax H3 and MiniMax Music 3.

<table><tr>
<td><a href="studio/web/showcase/v_h3_dragon.mp4"><img src="studio/web/showcase/v_h3_dragon.webp" alt="MiniMax H3: dragon" width="280"></a><br><sub><b>MiniMax H3</b>: dragon, with sound</sub></td>
<td><a href="studio/web/showcase/vfx_flood.mp4"><img src="studio/web/showcase/vfx_flood.webp" alt="LTX-2.5 VFX: flood the street" width="280"></a><br><sub><b>LTX-2.5 VFX</b>: flood the street</sub></td>
<td><a href="studio/web/showcase/recast_chef.mp4"><img src="studio/web/showcase/recast_chef.webp" alt="Recast" width="280"></a><br><sub><b>Recast</b>: same scene, new character</sub></td>
</tr><tr>
<td><img src="studio/web/showcase/s_mecha.webp" alt="Anima: mecha" width="280"><br><sub><b>Anima</b>: mecha in the rain</sub></td>
<td><img src="studio/web/showcase/s_foundry.webp" alt="FLUX.2 Klein: foundry" width="280"><br><sub><b>FLUX.2 Klein</b>: 10 seconds on one GPU</sub></td>
<td><a href="studio/web/showcase/vfx_clean_plate.mp4"><img src="studio/web/showcase/vfx_clean_plate.webp" alt="LTX-2.5 VFX: clean plate" width="280"></a><br><sub><b>LTX-2.5 VFX</b>: the violinist painted out, no mask</sub></td>
</tr></table>

<sub>Every image above is a real, unedited, AI-generated output from this repo's workflows. Prompt, time and peak VRAM are on each tile in the app.</sub>

<div align="center">

![The Create page: a draggable 3D wall of real renders](docs/img/hero.webp)

<sub>That wall is video from this studio's own renders, curved around you in three.js. Drag it. Click any shot to see how it was made.</sub>

</div>

### See inside every shot
Open **Pro** and the exact ComfyUI graph appears in 3D, with data flowing along its wires. Click a node for a plain-language explanation. During a render it lights up node by node. The same graph runs when you press Generate, and you can copy it into ComfyUI.

![The real graph in 3D](docs/img/pro.jpg)

### A crew you can talk to
**Comfy Prime** greets you, learns your name, and drives the studio for you, but never starts a render without your say. 46 specialists answer questions **only from notes, and show the quote**; this needs a local language model, and our tests stub it. Push to talk with local Whisper, hear replies in local Kokoro voices. Nothing leaves your machine.

![Comfy Prime and the crew](docs/img/crew.jpg)

### Model families, each with its own backend
95 families are wired, and 80 have a render on record. They run from **Stable Diffusion 1.5, SDXL and SD3** through **FLUX, Wan, HunyuanVideo, Mochi, LTX and MiniMax H3**, plus 3D, audio and utility models. Each has its own isolated ComfyUI instance with its own custom nodes and model view, started on demand behind a VRAM check and stopped when idle. Each family shows its state: rendered, ready, or what to download. A family with no render on record is wired, not proven.

![Model families](docs/img/families.jpg)

### Designers
Whole concept sheets from a few choices: **Character, Fashion, Vehicle**, plus setting, animal, plant, hair, nails, furniture, costume and print-on-demand products. Original designs only: no brands, logos or real makes.

### AI video editing
Remove objects, upscale, slow motion, extend a clip, restyle with pose or depth, change the camera, fill and outpaint, edit by instruction, then cut it together on a timeline.

### Train: your pictures in, a LoRA out

The Train page drops or imports pictures, checks their captions, and trains a LoRA, through ComfyUI's own training nodes (`TrainLoraNode`) or an external trainer the page drives as a process. Each base says who trains it, what file it needs, its licence and whether it is **Proven** (a real run on record), **Not run** (everything is here, the first run is the test, and you tick a box to try it) or **missing pieces** (it names exactly which). The loss curve, speed and peak VRAM come from the run; a figure that was not measured is not shown. The result lands in the LoRA folder and in the page's LoRA search, with a same-seed A/B against the base.

Short runs prove the plumbing, and the page says so. In our proofs the LoRA usually changed a picture close to its training set and did little for the trigger word alone on a new subject. Some were weak, and the page's example says which.

The word check covers captions, file names, the LoRA name, the trigger and the test prompt. **Pictures are not checked: there is no image classifier yet**, so training needs a tick that you own or have rights to the pictures and that no real person's likeness is trained without consent. This is not a safety guarantee. ComfyUI's node saves only at the end, so a cancel or crash loses that run; Continue adds steps to a finished LoRA without the optimizer's state. External trainers save as they go, show their own samples and can resume from their last save.

**Installing ai-toolkit (for FLUX.1 dev, Qwen-Image 2.1, HiDream-O1, LTX-2.5 and MiniMax H3) or SimpleTuner (for Music 3):** nothing is installed for you. Clone https://github.com/ostris/ai-toolkit, make a Python 3.12 venv, install a CUDA build of torch and then `requirements.txt`, and set `STUDIO_TRAINER_AI_TOOLKIT_DIR` and `STUDIO_TRAINER_AI_TOOLKIT_PYTHON` (for SimpleTuner, install it in its own venv and set `STUDIO_TRAINER_SIMPLETUNER_PYTHON`). The page shows these steps on any base that needs it. We write the job file from our own templates in `studio/train_configs` and give the trainer a folder of links, so it never writes into your model folders. It may fetch tokenizer and config files from Hugging Face. `STUDIO_TRAIN_WRAP` puts a command in front of the trainer, for a machine that shares its GPU through a queue. `STUDIO_TRAIN_PROVE=<base id>` lets one base have its first run without the page's tick.

### World Kit and Virtual Set
**World Kit** keeps one library of `.glb` places, props and characters with real scale and colliders, and exports a Godot pack. The place maker, looks, library and export ran here on the CPU with Blender, and the prop maker ran from a mesh. Describe an invented person and the character maker makes a sheet, checks it, and builds a rigged body with motions: it ran here on real models. The figure wears the sheet's clothes, hair and colour; its back and sides are the model's guess. Word checks and a picture check run on every character; the page says what they cannot catch. Other steps that need a model are written and tested with fakes, but have not run on a real model.

**Virtual Set** blocks a shot in a real-scale 3D place and steers a video model with what Blender renders. The passes ran on the CPU, and modes A, B, C and D have each rendered once on one street shot. Wan, a pose pass and Qwen keyframes have not run. World Kit and Virtual Set need extra downloads the installer does not fetch yet; the page says what is missing.

### Motion: words in, a body moving
Make a character move from words with Kimodo and put the clip on a rigged World Kit character, make a person follow a performance, animate a portrait, lip-sync a clip, capture motion from video into a rig. Each route shows only what rendered here, with its seed, time, peak VRAM, licence and faults. Anything that shows a person asks you to confirm they are invented or gave permission, runs word and picture checks, and marks the result as AI-generated. Those checks can't tell a real person from an invented one: that part is your word, and it stays with the file.

### Sampling Lab and the RES4LYF page
**Sampling Lab** explains samplers and schedulers in plain words, with 44 real renders on SDXL, SD 1.5 and SD 3.5 and measurements of ComfyUI's core code. The atlas entries for third-party packs are read from their source, not run. The SD 3.5 renders were decoded with a preview VAE, so they are not final quality.

**RES4LYF** is a credit page for ClownsharkBatwing's pack, which we don't ship. Run separately, of 154 nodes checked, 92 rendered, 14 ran, 44 errored and 4 were skipped or refused. The rest of the pack was not tried.

### ComfyUniversity
Learn ComfyUI by doing it, in tracks from your first wire to reading the sampler's source: graphs, samplers, noise and latents, guidance, conditioning, ControlNet and depth, LoRA training, video, audio, 3D, custom nodes, debugging, VRAM, and vetting node packs. Each lesson has a graph you can download and open, a lab that runs in the browser with no GPU, a Python lab you can run on your CPU from the page, a quiz, and a section on what commonly goes wrong. Each one lists what we checked against ComfyUI's source, a run or official docs, and what we could not check. Every graph passes ComfyUI's own validation, the ones that need no model were really executed, and the browser's schedulers and solvers are tested against ComfyUI's real functions. Each lesson carries a mark worked out from the data: *second reader checked* if an independent audit has tried to prove it wrong and fixed what it found, or *author-checked, second read pending* if not. Second reads found and fixed real errors, and they sample each lesson's riskiest claims rather than prove it, so a few mistakes may remain. The page counts both marks and the errors fixed. Most lessons have not been run against a real model on a GPU, and they say so. Progress stays in your browser.

### Atlas: the history of generative AI
More than 130 models across 8 eras, from the first VAEs and GANs to today: what each was, why it mattered, its licence, whether it runs here, and a button to use it.

### Recipes and processes
**Recipes** chain models into one click and pass each output along to the next model. All 10 flagships have been rendered. The library of 818 (657 prompt recipes and 161 LoRA settings) passes an offline format check. 701 of its recipes show a result we rendered here (487 pictures, 141 clips, 48 sounds, 25 3D models), each from one run. Without rendering, the page can also read each recipe against your ComfyUI's nodes and your model files. On our box 765 passed that; most of the other 53 are LoRA cards that still wait on a graph or a file. **Processes** lists 97 methods, most with guides. Many guides were written for the earlier studio and say so at the top. Most entries open a real tool or family page here today; the rest are marked Coming soon.

### Apps: every graph in one place
The 18 studio graphs, the recipes, 53 family templates and ComfyUI's own app templates when that package is installed, searchable, each one click from its form. If a graph needs a model you don't have, its page says what to download.

### It reads your box
The installer and planner look at your GPU, RAM and disk and offer what fits: GPU, offload, or not on this machine. **Calibrate** runs a small test render of seven goals, twice each, and shows the cold and warm seconds on this box. It does not measure VRAM, and the planner does not use the result yet. The crew's own LLM is picked by tier, from a 2B model on a CPU to a 27B model on a big card, with exact GGUF files and settings. Choose **stable or nightly** ComfyUI at install.

### Runs your way
- **Press Download:** each app shows what it needs and fetches only that. No 500 GB surprise.
- **Attach your ComfyUI:** already have one? Point the studio at it.
- **Set and forget:** schedule creations with cron, on idle only.
- **On your phone:** add it to your home screen over Tailscale, with private HTTPS and a QR code. Your GPU does the work.
- **Comfy SDK:** the default is your local ComfyUI. With the `sdk` extra installed, set `STUDIO_BACKEND=sdk` to send the same graphs through Comfy's official SDK, to Comfy Cloud, a deployment or your own proxy. Cloud and deployments spend Comfy credits. Uploads and the Create button still need a local ComfyUI. This path is tested against a stubbed SDK, not yet against a live server.

### 544 custom nodes, including a new V3 pack
Audited by reading the code: 158 do real work on images, latents, audio or files, or call a service. 262 are honest utilities (maths, text, config) and 102 build a plan or a payload for something else; those load no model and render nothing. 22 do not work on real ComfyUI inputs yet ([list](docs/NODES.md#node-reference)). Node ids that changed are in [NODE_RENAMES](docs/NODE_RENAMES.md). The `PSN_` nodes load in about 0.07 s thanks to lazy imports. The new V3 flagship pack has seven nodes for your own graphs; the studio's built-in graphs don't use them yet. The main ones:

| Node | What it does |
|---|---|
| **VRAM Gate** | Stops a graph with a plain reason when free VRAM is too low, instead of crashing mid-render |
| **Director Prompt** | Pick a camera move and its own controls appear; composes the whole shot |
| **Recast Prompt** | Writes the reference-tagged swap instruction for H3 |
| **Shot List** | Grows one slot per shot, then expands into a render subgraph for each |
| **Latent Inspector** | Look inside a latent: channel grid, PCA colour, histograms, stats |
| **Graph Proof** | Saves a hash and the settings next to every output |

More in [docs/NODES.md](docs/NODES.md).

## How it fits together

```mermaid
flowchart LR
  U["You: desktop or phone"] --> S["Studio: FastAPI + Preact + three.js, no build step"]
  S --> C["Your ComfyUI"]
  S --> F["Family backends, one per model family"]
  S --> L["Local LLM: vLLM, llama.cpp or Ollama"]
  S --> V["Local voice: Kokoro + Whisper"]
  S -. "optional, one setting" .-> K["Comfy SDK: own server, Cloud or deployment"]
  C --> O["Outputs + the graph that made them"]
  F --> O
  L --> A["Prime and the crew, answering from cited notes"]
  A --> S
```

| Folder | What lives there |
|---|---|
| `studio/` | The app: API, goals, recipes, crew, university, designers |
| `studio/web/` | The front end: Preact, htm and three.js, vendored, with no build step |
| `workflows/` | The API-format ComfyUI graphs behind every app |
| `psn_nodes/` | The custom node pack |
| `psn/` | Family instances, agents, connectors |
| `tests/` | More than 4,000 tests |

## Credits

**Made by Parametric Paradigm.**

**Made on one box:** NVIDIA RTX PRO 6000 Blackwell Workstation Edition (96 GB), AMD Ryzen 9 9950X 16-Core Processor (32 threads), 123 GB RAM, 4 TB NVMe, Ubuntu 24.04.5 LTS. Every render in this repo came from that one machine, except the samples marked as coming from ComfyUI's library.

Built with [ComfyUI](https://github.com/comfyanonymous/ComfyUI). Recast builds on the method published by Comfy-Org in `comfy-openjutsu` and Akatz Labs' H3 Character Swap. Thanks to every team that releases open weights: see [docs/CREDITS.md](docs/CREDITS.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Licence

Powered by MiniMax H3. **AGPL-3.0-or-later.** Use it, fork it, improve it. If you ship or host a changed version, you share your source too. See [LICENSE](LICENSE). Models keep their own licences.
