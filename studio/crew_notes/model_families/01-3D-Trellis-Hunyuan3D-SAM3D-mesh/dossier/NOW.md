# 3D runners and models: state on 2026-11-01

Where this file and older notes in this folder disagree, this file and STATE.md win. They come from the source and stored run records. [code: studio/model3d.py:1-2] [run: studio/model3d_proof.json]

## How to read the proof

The 3D proof file records one run per model on the test machine, dated 2026-11-01, looked at by a person in a turntable. It is not a benchmark and not a promise for other machines. A model with no row shows "not run". [code: studio/model3d.py:26-29, studio/model3d.py:46] [run: studio/model3d_proof.json] [test: tests/worldkit/test_model3d.py]

The 3D page lists 10 models, each run one of three ways: a family template on its own ComfyUI, a small runner in its own process, or a third-party tool. A model is offered only when its files are present. Results land in the output folder's 3d folder as .glb or .bvh. [code: studio/model3d.py:1-2, studio/model3d.py:11-22, studio/model3d.py:50-52, studio/model3d.py:142-146]

## Models that ran

TRELLIS.2 (family template trellis2_image_to_mesh): ran, 253.1 s, peak 18.2 GiB, seed 1380548294, on a bear cut-out with baked PBR. Detailed shape with a 4K bake. Lit from the side, the fur reads pale. Licence MIT. [run: studio/model3d_proof.json] [code: studio/model3d.py:12]

Hunyuan3D 2 (family template 3d_hunyuan3d_image_to_model): ran, 30.3 s, peak 5.8 GiB, seed 1953971077, on a bear on white. Clean shape, no colour. Earlier black-background runs built a wall behind the bear, so cut-outs now go on white. [run: studio/model3d_proof.json] [code: studio/model3d.py:13, studio/worldkit/jobs.py:82-89]

Hunyuan3D-2.1's other record is the proof table: the same image template at 45.8 s, multiview at 25.1 s and multiview turbo at 35.2 s. So two timings exist for one template. Template 3d_hunyuan3d-v2.1 has no recorded render. [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv, studio/family_status.json]

TripoSplat (family template): ran, 50.2 s, seed 286194226, on a bear cut-out, giving a Gaussian splat and a clip, not a mesh. Its 5.5 GiB peak is from an earlier mug run, not this run. Real from every side, a little blotchy on the back. [run: studio/model3d_proof.json] [code: studio/model3d.py:16]

TripoSR (runner triposr_image.py): ran, 19.0 s, peak 3.5 GiB, no seed, on a bear cut-out, with vertex colour. Fast, soft shape, recognisable from all sides. Licence MIT. [run: studio/model3d_proof.json] [code: studio/model3d.py:15]

Shap-E (runner shap_e_text.py): ran, 41.8 s, peak 4.5 GiB, seed 7, from the words "a wooden chair". A believable small chair from words alone. Licence MIT. [run: studio/model3d_proof.json] [code: studio/model3d.py:18]

MoGe 2 (family template 3d_moge_perspective_to_mesh): ran, 20.2 s, peak 1.8 GiB, no seed, on a room photo. One-sided relief with a hole behind anything in front. On a dark product shot with glass it gave scattered fragments. The panorama template has no recorded render. [run: studio/model3d_proof.json, studio/family_status.json] [code: studio/model3d.py:17]

MoGe's row in the proof table is a different thing: moge_3_vitg weights used inside a Moss-Image graph at 30.5 s. The mesh template lists moge_2_vitl_normal weights. Do not read the table row as proof of the mesh template. [run: studio/crew_notes/evidence/model_proof_2026-11-01.tsv, studio/family_status.json]

SAM 3D Body (template utility_sam3d_body): ran, 105.6 s, no peak recorded, seed 278454302, on a generated clip of a walking figure, giving a pose file as a stick-figure GLB. It is in the proof file but not on the 3D page's model list. [run: studio/model3d_proof.json] [code: studio/model3d.py:11-22]

SkinTokens (tool): ran, 42.2 s, peak 4.5 GiB, on TripoSR's bear mesh: 36 bones, and a pose test moved 52533 of 226530 vertices. Skin weights tear in a hard pose on this rough mesh. Looked at, not a finished rig. Licence MIT. [run: studio/model3d_proof.json] [code: studio/model3d.py:19]

Kimodo (tool): ran, 42.2 s, peak 16.1 GiB, seed 7, from words: walk forward, then wave. 150 frames, 78 joints, the hips travel about 6 m and the hand comes up. Looked at as a stick figure, not on a character. Its time equals SkinTokens' to the tenth, which was not checked further. [run: studio/model3d_proof.json] [code: studio/model3d.py:21]

AniGen (tool): ran, 190.7 s, peak 10.9 GiB, seed 42, on a bear cut-out: 33 bones with weights on every vertex. A hard test pose stretches it badly. Looked at, not a finished rig. [run: studio/model3d_proof.json] [code: studio/model3d.py:20]

## Wired, never rendered

SAM 3D Objects is wired and has no recorded run in this studio. It is on the 3D page, runs as a tool, needs a cut-out and shows "not run". Its gate assumes a 32 GB peak, which is not measured here. World Kit tries it first when its files are ready. [code: studio/model3d.py:14, studio/model3d.py:117-122, studio/worldkit/tools.py:15, studio/worldkit/capabilities.py:80] [run: studio/family_status.json]

Pixal3D is wired only as a World Kit prop route and is not on the 3D page's list. Its family record says the server starts and no template validates, with no render on record. Its guide says untested. [code: studio/worldkit/capabilities.py:33, studio/worldkit/capabilities.py:80] [run: studio/family_status.json] [docs: studio/processes/3d-pixal3d.md]

UniRig is labelled "not wired: weights only, no runner here". Its server starts and no template validates. Rigging here uses SkinTokens or AniGen. [code: studio/worldkit/capabilities.py:45] [run: studio/family_status.json]

HY-Motion, HunyuanWorld, InstantMesh, MIDI-3D, PartCrafter and Stable-Fast-3D have a family record only: server starts, no template validates, no render, no runner. PartCrafter's record also names a failed pack import, ComfyUI-TripoSG. [run: studio/family_status.json] [code: studio/model3d.py:11-22]

Matrix-3D has no proof of its own. An earlier test ran Wan 2.2 5B, which reads none of Matrix-3D's weights, so it proved nothing about this model. No runner exists for its panorama video and LRM checkpoints. [run: studio/family_status.json] [code: scripts/record_family_renders.py:2]

## What a runner needs

3D runners run with the studio's own Python in a separate process, with an 1800 s limit, after a VRAM check. Nothing is evicted. The output file decides success. Each needs its Python packages in that environment: torch and trimesh for both, diffusers and transformers for Shap-E, omegaconf for TripoSR. [code: studio/model3d.py:72-78, studio/worldkit/runners/shap_e_text.py:18-20, studio/worldkit/runners/shap_e_text.py:38, studio/worldkit/runners/triposr_image.py:34]

The Shap-E runner needs prior and renderer files under 3d/shap-e and text_encoders/clip-vit-large-patch14.safetensors, because it reads CLIP ViT-L/14 from there. Defaults: 64 steps, guidance 15, seed 7, frame size 64. It stops on an empty mesh. [code: studio/worldkit/capabilities.py:40, studio/worldkit/runners/shap_e_text.py:2, studio/worldkit/runners/shap_e_text.py:39-42, studio/worldkit/runners/shap_e_text.py:49]

The TripoSR runner needs _complete_pipelines/TripoSR/checkpoints/model.ckpt and the upstream tsr package folder, set by STUDIO_TOOL_TRIPOSR, by default inside a copy of a node pack in the pack library. It takes a 512 px input, puts a cut-out at 85% of the frame, and extracts at resolution 256. It takes no seed. [code: studio/worldkit/capabilities.py:39, studio/worldkit/capabilities.py:94, studio/worldkit/runners/triposr_image.py:49-58, studio/worldkit/runners/triposr_image.py:61, studio/worldkit/runners/triposr_image.py:70]

3D tools each need their own folder and launcher: run_sam3d.sh, run_skintokens.sh, run_anigen.sh and run_kimodo.sh, each with its own virtual environment, plus weights listed by size. Limits are 1800 s, 900 s, 1500 s and 2400 s. The readiness check names a launcher that points at a missing folder. [code: studio/worldkit/capabilities.py:98-101, studio/worldkit/capabilities.py:105-119, studio/worldkit/tools.py:15-16]

3D family templates are checked by the family's own list of model files and run on that family's instance, with its VRAM gate. A template's LoadImage takes a name in the instance's input folder, and the studio copies the picture there, on white if it has a cut-out. [code: studio/worldkit/capabilities.py:139-149, studio/worldkit/jobs.py:4, studio/worldkit/jobs.py:92-107]

## VRAM gates against measured peaks

3D gates add a 4 GB floor to an assumed peak. Assumed peaks: TripoSR 4.0, Shap-E 4.0, SkinTokens 6.0, AniGen 11.0, Kimodo 17.0, SAM 3D Objects 32.0. Shap-E's assumed 4.0 is below its measured 4.5 GiB, so its gate is slightly optimistic. The others sit at or above their measured peak. [code: studio/model3d.py:15, studio/model3d.py:18, studio/worldkit/tools.py:15, psn/instances.py:13, studio/worldkit/blender.py:116] [run: studio/model3d_proof.json]

## glb.py

The glb.py reader checks and counts a .glb with the standard library. inspect_glb reports meshes, primitives, vertices and triangles. facts reads only the file's head, for World Kit validation: nodes, meshes, skins, joints, animations and colliders named -colonly, -convcolonly or -col. [code: studio/glb.py:167-175, studio/glb.py:403, studio/glb.py:405-425] [test: tests/studio_lanes/test_glb.py, tests/worldkit/test_glb_rigmap_validate.py]

The glb.py list_glb walks a folder, skips symlinks and anything outside the root, and returns the 50 newest .glb files. The 3D page and World Kit both use it. [code: studio/glb.py:360-397, studio/server.py:364-367, studio/worldkit/api.py:333-341]

## Limits of the 3D page

3D page jobs are held in memory, so a restart loses the record, and there is no cancel route. A seed sent to a family template is not passed on, so a family run does not take the page's seed. Text jobs go through the word check, and pictures are not checked by what they show. [code: studio/model3d.py:9, studio/model3d.py:81-84, studio/model3d.py:94-97, studio/model3d.py:138-153]

3D results do not know their real size when made from one picture, as the page says. Only World Kit cleanup gives a real scale. The page's sample meshes are the project's own test builds: a knot prop, two places and a Hunyuan3D bear with no texture. [code: studio/web/studio3d.js:121, studio/worldkit/makers/prop.py:173-188] [run: studio/web/mesh_art/index.json]

## Chains that have not run whole

3D models in World Kit have not run as a whole chain. Picture to prop through a model and the character chain are tested with fakes, and the runs above were single steps from the 3D page or the family watcher. No rigged person made from a saved character is on record. [docs: studio/processes/world-kit.md] [test: tests/worldkit/test_character_maker.py, tests/worldkit/test_prop_maker.py]

## Final session findings, 2026-11-03

Three statements in the 2026-11-01 part of this file are out of date: SAM 3D Objects has now run, UniRig is now wired with two recorded runs, and HY-Motion and HunyuanWorld each have a render. The paragraphs below give the records. [docs: studio/crew_notes/model_families/01-3D-Trellis-Hunyuan3D-SAM3D-mesh/dossier/NOW.md:39, studio/crew_notes/model_families/01-3D-Trellis-Hunyuan3D-SAM3D-mesh/dossier/NOW.md:43, studio/crew_notes/model_families/01-3D-Trellis-Hunyuan3D-SAM3D-mesh/dossier/NOW.md:45] [run: studio/model3d_proof.json:102-121]

### Runs added since the first proof

SAM 3D Objects ran on 2026-11-01 through its tool on a bear cut-out and its mask: 210.0 s, peak 21.7 GiB, seed 42, giving a mesh plus a splat. Good overall shape with fur detail; the colour is uneven, pale on one side and brown on the other. Its gate still assumes a 32 GB peak, well above the measured one. [run: studio/model3d_proof.json:102-111] [code: studio/worldkit/tools.py:17, studio/model3d.py:14]

UniRig is now on the 3D page as a rig job run by its own tool, with a 1500 s limit and an assumed 8.0 GB peak. It turns a mesh into a rigged GLB. [code: studio/model3d.py:19, studio/model3d.py:112, studio/worldkit/tools.py:17-18, studio/worldkit/tools.py:127-132]

UniRig's first run, on 2026-11-01, used TripoSR's bear mesh, the same one SkinTokens rigged: 129.2 s, peak 5.9 GiB, seed 12345, 31 bones. A pose test moved 98,912 of 226,530 vertices and bent with less tearing than SkinTokens, with some stretch at the neck. One mesh only. [run: studio/model3d_proof.json:112-121]

UniRig's second run, on 2026-11-02, rigged TRELLIS.2's textured bear: 195.9 s, peak 5.9 GiB, seed 12345, 36 bones on a 555,011-vertex mesh. Bending the four lowest chains in Blender moved 405,190 vertices. The legs swing cleanly; the fur stretches and smears at the hips, and the belly lifts with the front legs. MIT. [run: studio/family_status.json]

HY-Motion 1.0 (template hymotion_t2m_preview) turns a sentence into a body motion through Aero-Ex's HY-Motion nodes from a hardened copy, with Qwen3-8B and CLIP-L reading the words. The pack wants Qwen3-8B as one file, so the repo's five bf16 shards were joined with no tensor changes; the text encoder runs on the CPU. The sampler also needs Tencent's wooden mannequin data. [code: studio/family_templates/index.json, psn/instances.py:59, psn/instances.py:64, psn/instances.py:78-80]

HY-Motion's run on 2026-11-02, on the family's own instance: walk forward, stop, raise both arms and wave. 59.6 s, peak 4.9 GiB, seed 20261102, 4 seconds at 30 fps as a skeleton preview. A natural walk with arm swing, a stop, and both arms raised high; it never waves, the arms rise and hold. Two runs with the same seed gave different walks. Licence: Tencent Hunyuan, not for the EU, UK or South Korea, and over 1 million monthly users needs a licence. [run: studio/family_status.json]

HunyuanWorld's panorama stage (template hunyuanworld_pano_t2i) runs its PanoDiT-Text LoRA on FLUX.1-dev through core nodes, 1920x960, guidance 30, 50 steps, on its own instance. The 3D world stages are not on the test machine. [code: studio/family_templates/index.json] [run: studio/family_status.json]

HunyuanWorld's run on 2026-11-02 (40.7 s, peak 35.6 GiB, seed 20261102) made an alpine valley that wraps the full 360 with a level horizon. Faults: the mist never appears, the look is more illustration than photo, and a faint vertical line shows where the edges meet (mean edge difference 3.8 against 1.5 between neighbouring columns), because ComfyUI's sampler has no circular padding. FLUX.1-dev is non-commercial; the LoRA's Tencent licence excludes the EU, UK and South Korea. [run: studio/family_status.json] [code: studio/family_templates/index.json]

### 3D families with no render, and InstantMesh, which now has one

InstantMesh rendered on 2026-11-03, after Zero123++ v1.2 and DINO ViT-B/16 were fetched: 67.1 s, 22.8 GiB peak for the process, seed 20261102; the six views and the GLB turntable were looked at. MIDI-3D, PartCrafter, Stable-Fast-3D and Matrix-3D still record why they have no render (checked 2026-11-02). MIDI-3D lacks its transformer and VAE, and has no runner. PartCrafter lacks its VAE and its pack, ComfyUI-TripoSG, fails to import. Stable-Fast-3D needs the sf3d package with compiled parts, which means a pip change to the studio venv. Matrix-3D has no runner for its pipeline. [run: studio/family_status.json]

### Mesh clean-up, downloads and framing

The 3D page now has a Mesh tools section listing core ComfyUI's own mesh nodes: WeldVertices first, then DecimateMesh, RemeshMesh, FillHoles, MeshSmoothNormals, UnwrapMesh and others. On 2026-11-02 a clean-up of the Hunyuan3D sample went from 181,548 faces to 6,612 for a budget of 8,000 in 2.5 s. Two more runs gave 6,547 and 6,588, so the budget is a ceiling, not an exact count. Flipped triangles remain as speckles on the legs. [run: studio/web/mesh_tools.json:60] [code: studio/web/mesh_tools.json:2-45, studio/web/studio3d.js:93-96] [test: tests/test_geometry_math.py]

ComfyUI-GeometryPack, which adds booleans, alpha wrap and self-intersection repair, was read but not installed or run: it installs through its own installer, which pip-installs other packages and downloads a separate environment. ComfyMath-NG ran in Pack Lab only and is not part of the install. [code: studio/web/mesh_tools.json:62-75] [test: tests/test_geometry_math.py]

3D downloads on the Recipes page were wrong until 2026-11-02. Every World Kit run names its mesh mesh_asset.glb, and the build searched the whole output folder by that name, so several recipes shared one file. Each download now comes from its own run's folder. A test fails if two recipes share a download, and GLB downloads stay under about 1.5 MB; the Gaussian splat has no reducer and keeps its size. [test: tests/test_recipe_renders.py:154-160] [claim: studio commit 767f3ffe, 2026-11-02]

Web copies of meshes that store every triangle on its own (TripoSR, Hunyuan3D, SAM 3D, SkinTokens, Shap-E) came out shattered when decimated. They are now welded and smoothed before decimating, and each was compared with its turntable. [claim: studio commit 767f3ffe, 2026-11-02]

World Kit turntables now fit the camera to the asset's bounding sphere with a 12% margin, so the fit holds at every step of the orbit; flat assets are looked down on, and the near clip follows the distance. The frame no longer hints at size; the page's Real scale tag shows that. [code: studio/worldkit/blender_scripts/_fit.py:1-12] [test: tests/worldkit/test_turntable_fit.py]

SAM 3D Body's captured motion can now go onto a rig. Its BVH names joints joint_001 to joint_126; the studio finds the body's joints by position in the first frame, renames them to the names the motion fit reads, levels the clip and turns it to face forward. [code: studio/worldkit/mhr_bvh.py:1, studio/worldkit/mhr_bvh.py:83-84] [test: tests/worldkit/test_mhr_bvh.py]
